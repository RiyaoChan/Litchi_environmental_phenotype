"""Outer harvest-year validation, forward-origin validation, and stability."""
from __future__ import annotations
import json
import numpy as np
import pandas as pd

from .phenology_models import day_offset,predict_fit,score_predictions
from .r4_weather_loader import task_frame
from .io_utils import write_csv,write_json
from .reporting import markdown_table


def metrics(rows):
    valid=rows[rows.predicted_event_date.notna()]
    errors=rows.absolute_error_score_days.to_numpy(dtype=float)
    observed=pd.Series([day_offset(r.end_date,r.harvest_year) for r in valid.itertuples()],dtype=float)
    predicted=pd.Series([day_offset(r.predicted_event_date,r.harvest_year) for r in valid.itertuples()],dtype=float)
    rank_r=float(observed.rank().corr(predicted.rank())) if observed.nunique()>1 and predicted.nunique()>1 else np.nan
    return {'n_samples':len(rows),'n_predictions':len(valid),'n_unreached_or_invalid':len(rows)-len(valid),
            'MAE_days':float(np.mean(errors)),'RMSE_days':float(np.sqrt(np.mean(errors**2))),
            'median_AE_days':float(np.median(errors)),'mean_bias_days':float(valid.error_days.mean()) if len(valid) else np.nan,
            'Spearman_r':rank_r,'MAE_valid_only_days':float(valid.error_days.abs().mean()) if len(valid) else np.nan}


def outer_splits(frame,validation,config):
    years=sorted(frame.harvest_year.unique())
    for year in years:
        if validation=='rolling' and year not in config['rolling_test_years']: continue
        training=frame[frame.harvest_year<year] if validation=='rolling' else frame[frame.harvest_year!=year]
        testing=frame[frame.harvest_year==year]
        if training.harvest_year.nunique()<2: continue
        yield int(year),training,testing


def cross_validate(frame,task,models,engine,cohort='main'):
    predictions=[]; parameter_rows=[]; candidate_rows=[]; fitted_models={}
    for validation in ['LOYO','rolling']:
        for year,train,test in outer_splits(frame,validation,engine.config):
            for model in models:
                fit=engine.fit(train,task,model)
                fit_id=f'{cohort}_{task}_{model}_{validation}_{year}'
                fitted_models[fit_id]=fit
                pred=predict_fit(fit,test,engine.weather)
                scored=score_predictions(test,pred,engine.config)
                scored['task']=task; scored['model_id']=model; scored['validation']=validation
                scored['holdout_year']=year; scored['cohort']=cohort; scored['fit_id']=fit_id
                scored['training_years']=';'.join(map(str,fit['training_years']))
                scored['training_season_ids']=';'.join(fit['training_season_ids'])
                scored['selected_spec']=json.dumps(fit['spec'],sort_keys=True)
                scored['prediction_context']='observed_stage_start_and_realized_reanalysis; not_operational_weather_forecast'
                predictions.append(scored)
                for orchard,threshold in fit['parameters'].items():
                    parameter_rows.append({'fit_id':fit_id,'validation':validation,'holdout_year':year,'model_id':model,
                        'orchard_id':orchard,'threshold':threshold,'spec':json.dumps(fit['spec'],sort_keys=True),
                        'inner_MAE_days':fit['inner_mae_days'],'training_years':';'.join(map(str,fit['training_years'])),
                        'fit_season_ids':';'.join(fit['fit_season_ids'][orchard]),'selection_mode':fit['selection_mode']})
                for candidate in fit['candidate_scores']:
                    candidate_rows.append({'fit_id':fit_id,'holdout_year':year,'validation':validation,'model_id':model,
                        'candidate_index':candidate['candidate_index'],'spec':json.dumps(candidate['spec'],sort_keys=True),
                        'inner_MAE_days':candidate['inner_mae_days'],'training_years':';'.join(map(str,fit['training_years']))})
    return pd.concat(predictions,ignore_index=True),pd.DataFrame(parameter_rows),pd.DataFrame(candidate_rows),fitted_models


def comparisons(predictions,task):
    rows=[]
    for (validation,model),g in predictions.groupby(['validation','model_id'],sort=True):
        base=predictions[(predictions.validation==validation)&(predictions.model_id==task+'-B0')]
        base_mae=metrics(base)['MAE_days']; measured=metrics(g)
        rows.append({'validation':validation,'model_id':model,**measured,
                     'delta_MAE_days':measured['MAE_days']-base_mae,
                     'relative_MAE_reduction_pct':100*(base_mae-measured['MAE_days'])/base_mae if base_mae else np.nan})
    return pd.DataFrame(rows)


def stability(predictions,parameters,task,config,seed):
    rows=[]
    main=predictions[predictions.validation=='LOYO']
    baseline=main[main.model_id==task+'-B0'].set_index('season_id')
    for model,group in main.groupby('model_id',sort=True):
        g=group.set_index('season_id')
        pair=pd.DataFrame({'year':g.harvest_year,'improvement':baseline.absolute_error_score_days-g.absolute_error_score_days})
        by_year=pair.groupby('year').improvement.mean()
        best_year=int(by_year.idxmax())
        remaining=pair[pair.year!=best_year].improvement.mean()
        rolling=predictions[(predictions.validation=='rolling')&(predictions.model_id==model)]
        rolling_base=predictions[(predictions.validation=='rolling')&(predictions.model_id==task+'-B0')]
        rolling_delta=metrics(rolling)['MAE_days']-metrics(rolling_base)['MAE_days'] if len(rolling) else np.nan
        specs=parameters[(parameters.validation=='LOYO')&(parameters.model_id==model)].drop_duplicates('fit_id')
        n_shapes=specs.spec.nunique()
        parameter_ok=not group.prediction_status.eq('invalid_zero_or_nonfinite_threshold').any()
        if model=='P1-H3': parameter_ok &= n_shapes<=config['stability']['max_h3_distinct_shapes_for_identifiable_claim']
        stable=(pair.improvement.mean()>0 and (by_year>=0).sum()>=config['stability']['min_nonworse_loyo_years']
                and remaining>0 and np.isfinite(rolling_delta) and rolling_delta<=0 and parameter_ok)
        rng=np.random.default_rng(seed); years=pair.year.unique()
        bootstrap=[]
        for _ in range(config['stability']['clustered_bootstrap_repetitions']):
            sample=np.concatenate([pair.loc[pair.year==y,'improvement'].to_numpy() for y in rng.choice(years,len(years),replace=True)])
            bootstrap.append(float(sample.mean()))
        lo,hi=np.quantile(bootstrap,[.025,.975])
        rows.append({'model_id':model,'MAE_improvement_vs_B0_days':float(pair.improvement.mean()),
                     'nonworse_loyo_years':int((by_year>=0).sum()),'best_improvement_holdout_year':best_year,
                     'improvement_without_best_year_days':float(remaining),
                     'fragile':bool(pair.improvement.mean()>0 and remaining<=0),
                     'rolling_delta_MAE_vs_B0_days':rolling_delta,'selected_specs_across_loyo':n_shapes,
                     'parameter_validity_check_pass':bool(parameter_ok),'stable_superiority':bool(stable),
                     'improvement_cluster_bootstrap_95_low_days':float(lo),'improvement_cluster_bootstrap_95_high_days':float(hi),
                     'uncertainty_note':'five_year_descriptive_cluster_bootstrap_not_independent_external_validation'})
    return pd.DataFrame(rows)


def write_task_report(root,cfg,task,comparison,stable,frame,extension_allowed):
    main=comparison[comparison.validation=='LOYO']
    roll=comparison[comparison.validation=='rolling']
    text=f'''# {task}：嵌套按年验证与前向滚动

主分析{len(frame)}个果园—产季，{frame.harvest_year.nunique()}年；同任务所有模型使用相同测试样本。每折内选择候选温度/形状，事件累计阈值只用训练样本。扩展进入条件：{extension_allowed}。

## LOYO留出预测

{markdown_table(main)}

## 前向滚动

{markdown_table(roll)}

## 稳定性与按年不确定性

{markdown_table(stable)}

stable_superiority需同时满足：汇总MAE更低、至少3个留出年不差、去掉最佳改善年仍更好、rolling方向不冲突、参数检查通过。表中最小误差只是候选集合内的最小值，不是额外独立验证后的赢家。五个年份自助区间仅为描述性不确定性。

小时指标从实际起点00:00按每小时温度计算，再聚合每日响应；这保持了首次越阈值日期，不能将日精度物候评价解释成小时精度实测。历史B0沿用同园训练持续天数中位数。累计到6月30日仍未达阈值，日期为NA且计预注册365天失败惩罚，未丢弃失败样本。

本任务的单阶段预测以已观测阶段起点为输入。W3将另行使用预测起点串联；不能把条件单阶段误差直接当完整链式误差。天气是事后ERA5再分析，不是当时可获得的未来天气预报。果园与品种混杂，不能据此作独立品种生理阈值比较。
'''
    name={'P1':'02_P1_PHENOLOGY_MODEL_REPORT.md','P2':'03_P2_PHENOLOGY_MODEL_REPORT.md','P3':'03_P3_PHENOLOGY_MODEL_REPORT.md'}[task]
    (root/cfg['reports']/name).write_text(text,encoding='utf-8')


def run_task(root,cfg,master,engine,task):
    frame=task_frame(master,task)
    models=engine.config[task]['models']
    predictions,parameters,candidates,fits=cross_validate(frame,task,models,engine)
    comparison=comparisons(predictions,task)
    main=comparison[comparison.validation=='LOYO'].set_index('model_id')
    weather_models=[m for m in models if not m.endswith(('B0','B1'))]
    extension_allowed=min(main.loc[m,'MAE_days'] for m in weather_models)<main.loc[task+'-B0','MAE_days']
    extension={'P1':'P1-W1','P2':'P2-M2','P3':'P3-M2'}[task]
    if extension_allowed:
        extra,p,c,f=cross_validate(frame,task,[extension],engine)
        predictions=pd.concat([predictions,extra],ignore_index=True)
        parameters=pd.concat([parameters,p],ignore_index=True); candidates=pd.concat([candidates,c],ignore_index=True)
        fits.update(f); comparison=comparisons(predictions,task)
    diagnostics=stability(predictions,parameters,task,engine.config,cfg['seed'])
    target=root/cfg['outputs']/'phenology'
    write_csv(target/f'{task}_cv_predictions.csv',predictions)
    write_csv(target/f'{task}_model_comparison.csv',comparison)
    write_csv(target/f'{task}_parameters_by_fold.csv',parameters)
    write_csv(target/f'{task}_candidate_scores.csv',candidates)
    write_csv(target/f'{task}_stability_diagnostics.csv',diagnostics)
    fold=[{'validation':v,'model_id':m,'holdout_year':int(y),**metrics(g)} for (v,m,y),g in predictions.groupby(['validation','model_id','holdout_year'])]
    orchard=[{'validation':v,'model_id':m,'orchard_id':o,**metrics(g)} for (v,m,o),g in predictions.groupby(['validation','model_id','orchard_id'])]
    write_csv(target/f'{task}_fold_metrics.csv',fold); write_csv(target/f'{task}_orchard_metrics.csv',orchard)
    write_json(target/f'{task}_fitted_models.json',fits)
    write_json(target/f'{task}_execution.json',{'task':task,'primary_models':models,'extension':extension,
                'extension_executed':bool(extension_allowed),'stable_weather_models':diagnostics.loc[diagnostics.stable_superiority,'model_id'].tolist()})
    write_task_report(root,cfg,task,comparison,diagnostics,frame,extension_allowed)
    if task=='P1':
        alternative=task_frame(master,task,'bannei_early_sensitivity')
        alt,ap,ac,af=cross_validate(alternative,task,models,engine,'bannei_early_sensitivity')
        sensitivity=[]
        for model in models:
            primary=predictions[(predictions.model_id==model)&(predictions.validation=='LOYO')]
            all_alt=alt[(alt.model_id==model)&(alt.validation=='LOYO')]
            common=all_alt[all_alt.season_id.isin(primary.season_id)]
            sensitivity.append({'model_id':model,'main_n':len(primary),'including_early_n':len(all_alt),
                'main_MAE_days':metrics(primary)['MAE_days'],'same_main_sample_sensitivity_MAE_days':metrics(common)['MAE_days'],
                'all_sensitivity_MAE_days':metrics(all_alt)['MAE_days']})
        write_csv(target/'P1_bannei_early_sensitivity.csv',sensitivity)
        write_csv(target/'P1_bannei_early_cv_predictions.csv',alt)
        write_csv(target/'P1_bannei_early_parameters.csv',ap)
        report=root/cfg['reports']/'02_P1_PHENOLOGY_MODEL_REPORT.md'
        report.write_text(report.read_text(encoding='utf-8')+'\n## 办内2025早期物候敏感性\n\n'+
            markdown_table(pd.DataFrame(sensitivity))+'\n\n仅增加早期物候，未将零产量加入正常产量拟合；共同12个样本与全部13个样本的误差分开报告。\n',encoding='utf-8')
    print(task+' LOYO: '+comparison[comparison.validation=='LOYO'][['model_id','MAE_days']].to_json(orient='records'),flush=True)
    return predictions,comparison,diagnostics
