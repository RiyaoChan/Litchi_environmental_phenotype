"""Nested year validation with partition-specific regeneration of W1-M/W3."""
from __future__ import annotations
import json
import numpy as np
import pandas as pd

from .io_utils import write_csv,write_json
from .r4_weather_loader import settings
from .yield_models import fit_ridge,predict_ridge,historical_yield_predict
from .reporting import markdown_table

MODEL_KIND={'Y-W1C':'W1-CALENDAR','Y-W1M':'W1-MEDIAN','Y-W2O':'W2-OBS',
            'Y-W3P':'W3-PRED','Y-W3P+PHENO':'W3-PRED'}


def yield_metrics(group):
    error=group.predicted_yield-group.observed_yield
    r=float(group.observed_yield.rank().corr(group.predicted_yield.rank())) if group.observed_yield.nunique()>1 and group.predicted_yield.nunique()>1 else np.nan
    mae=float(error.abs().mean())
    return {'n_predictions':len(group),'MAE_kg_mu':mae,'RMSE_kg_mu':float(np.sqrt(np.mean(error**2))),
            'median_AE_kg_mu':float(error.abs().median()),'mean_bias_kg_mu':float(error.mean()),
            'Spearman_r':r,'normalized_MAE':mae/float(group.observed_yield.mean()),
            'negative_predictions':int(group.predicted_yield.lt(0).sum())}


class YieldValidator:
    def __init__(self,root,cfg,builder):
        self.root=root; self.cfg=cfg; self.builder=builder
        self.config=settings(root,cfg,'yield')
        self.lineage=[]; self.candidate_rows=[]; self.parameter_rows=[]; self.fit_models={}

    def columns(self,model):
        w=self.builder.config
        columns=(w['pheno_extension_base_features']+w['pheno_extension_features']) if model=='Y-W3P+PHENO' else w['continuous_features']
        if len(columns)>self.config['max_continuous_features']: raise ValueError('Too many continuous features')
        return columns

    def partition(self,train,test,model,context):
        a,b=self.builder.partition(train,test,MODEL_KIND[model])
        for row in pd.concat([a,b],ignore_index=True).itertuples():
            self.lineage.append({'context':context,'model_id':model,'season_id':row.season_id,'role':row.role,
                'partition_training_years':';'.join(map(str,sorted(train.harvest_year.unique()))),
                'boundary_training_years':row.boundary_training_years,'metric_training_years':row.metric_training_years,
                'chain_trace':row.chain_trace,'feature_status':row.feature_status})
        if not a.feature_status.eq('complete').all() or not b.feature_status.eq('complete').all():
            raise ValueError('Incomplete windows in '+context)
        return a,b

    def tune(self,training,model,context):
        splits=[]
        for year in sorted(training.harvest_year.unique()):
            tr=training[training.harvest_year!=year]; va=training[training.harvest_year==year]
            if tr.empty: raise ValueError('Insufficient years for nested yield tuning')
            a,b=self.partition(tr,va,model,context+'_inner_'+str(year))
            splits.append((tr,va,a,b))
        scores=[]; columns=self.columns(model); categories=list(self.cfg['orchards'])
        for alpha in self.config['alpha_candidates']:
            errors=[]
            for tr,va,a,b in splits:
                fit=fit_ridge(a,tr,columns,alpha,categories)
                predicted=predict_ridge(fit,b)
                observed=b[['season_id']].merge(va[['season_id','final_yield_kg_per_mu']],on='season_id').final_yield_kg_per_mu.to_numpy()
                errors.extend(np.abs(predicted-observed).tolist())
            score=float(np.mean(errors)); scores.append(score)
            self.candidate_rows.append({'context':context,'model_id':model,'alpha':alpha,'inner_MAE_kg_mu':score,
                'training_years':';'.join(map(str,sorted(training.harvest_year.unique())))})
        return self.config['alpha_candidates'][int(np.argmin(scores))]

    def run_cohort(self,cohort,data,models,rolling=False):
        predictions=[]; statuses=[]
        if data.season_id.duplicated().any(): raise ValueError('Duplicate independent season')
        if data.season_id.eq('bannei_2025').any(): raise ValueError('Bannei 2025 zero yield must not enter normal fit')
        validations=['LOYO','rolling'] if rolling else ['LOYO']
        for validation in validations:
            for model in models:
                model_predictions=[]; model_statuses=[]
                for year in sorted(data.harvest_year.unique()):
                    if validation=='rolling' and year not in [2024,2025,2026]: continue
                    train=data[data.harvest_year<year] if validation=='rolling' else data[data.harvest_year!=year]
                    test=data[data.harvest_year==year]
                    context=f'{cohort}_{validation}_outer_{year}'
                    try:
                        if model=='Y-B0':
                            order=test; predicted=historical_yield_predict(train,test)
                            fit={'training_years':sorted(map(int,train.harvest_year.unique())),
                                 'training_season_ids':sorted(train.season_id.tolist()),'kind':'training_orchard_median'}
                        else:
                            a,b=self.partition(train,test,model,context)
                            alpha=self.tune(train,model,context)
                            fit=fit_ridge(a,train,self.columns(model),alpha,list(self.cfg['orchards']))
                            predicted=predict_ridge(fit,b)
                            order=b[['season_id']].merge(test,on='season_id',validate='one_to_one')
                            self.parameter_rows.append({'cohort':cohort,'validation':validation,'holdout_year':int(year),
                                'model_id':model,'alpha':alpha,'continuous_feature_count':len(fit['columns']),
                                'features':';'.join(fit['columns']),'scaler_mean':json.dumps(fit['mean']),
                                'scaler_scale':json.dumps(fit['scale']),'coefficient':json.dumps(fit['coefficient']),
                                'training_years':';'.join(map(str,fit['training_years']))})
                        fit_id=context+'_'+model; self.fit_models[fit_id]=fit
                        for (_,row),value in zip(order.iterrows(),predicted):
                            model_predictions.append({'cohort':cohort,'validation':validation,'model_id':model,
                                'holdout_year':int(year),'season_id':row.season_id,'orchard_id':row.orchard_id,
                                'harvest_year':int(row.harvest_year),'observed_yield':row.final_yield_kg_per_mu,
                                'predicted_yield':float(value),'error_kg_mu':float(value-row.final_yield_kg_per_mu),
                                'fit_id':fit_id,'training_years':';'.join(map(str,fit['training_years'])),
                                'training_season_ids':';'.join(fit['training_season_ids']),
                                'prediction_context':'realized_weather_conditional; W2_retrospective_oracle; no_observed_future_pheno_in_W3'})
                        model_statuses.append({'cohort':cohort,'validation':validation,'model_id':model,'holdout_year':int(year),
                                              'status':'executed','reason':'complete_partition_features'})
                    except ValueError as error:
                        model_statuses.append({'cohort':cohort,'validation':validation,'model_id':model,'holdout_year':int(year),
                                              'status':'blocked','reason':str(error)})
                # Keep partial runs in the prediction audit, but never call their LOYO MAE a matched main comparison.
                predictions.extend(model_predictions); statuses.extend(model_statuses)
        return pd.DataFrame(predictions),pd.DataFrame(statuses)


def summarize(predictions,statuses):
    rows=[]
    for (cohort,validation,model),status in statuses.groupby(['cohort','validation','model_id'],sort=True):
        group=predictions[(predictions.cohort==cohort)&(predictions.validation==validation)&(predictions.model_id==model)]
        complete=status.status.eq('executed').all()
        if group.empty:
            rows.append({'cohort':cohort,'validation':validation,'model_id':model,'status':'blocked','n_predictions':0})
            continue
        base=predictions[(predictions.cohort==cohort)&(predictions.validation==validation)&(predictions.model_id=='Y-B0')&predictions.season_id.isin(group.season_id)]
        measured=yield_metrics(group)
        rows.append({'cohort':cohort,'validation':validation,'model_id':model,'status':'complete' if complete else 'partial_not_matched_main',
                     **measured,'baseline_MAE_same_seasons_kg_mu':yield_metrics(base)['MAE_kg_mu'],
                     'delta_MAE_same_seasons_kg_mu':measured['MAE_kg_mu']-yield_metrics(base)['MAE_kg_mu']})
    return pd.DataFrame(rows)


def assess_yield(comparison,predictions):
    main=comparison[(comparison.cohort=='MAIN')&(comparison.validation=='LOYO')].set_index('model_id')
    reasons=[]; checks={}
    required=['Y-B0','Y-W1C','Y-W1M','Y-W2O','Y-W3P']
    complete=all(m in main.index and main.loc[m,'status']=='complete' for m in required)
    if not complete: reasons.append('one_or_more_required_models_lack_complete_nested_partitions')
    if complete:
        sample=predictions[(predictions.cohort=='MAIN')&(predictions.validation=='LOYO')]
        losses=sample.assign(ae=sample.error_kg_mu.abs()).groupby(['model_id','harvest_year']).ae.mean().unstack(0)
        checks={'W3_lower_pooled_MAE_than_B0':bool(main.loc['Y-W3P','MAE_kg_mu']<main.loc['Y-B0','MAE_kg_mu']),
                'W3_nonworse_years_than_W1C':int((losses['Y-W3P']<=losses['Y-W1C']).sum()),
                'W3_nonworse_years_than_W1M':int((losses['Y-W3P']<=losses['Y-W1M']).sum())}
        if not checks['W3_lower_pooled_MAE_than_B0']: reasons.append('W3_does_not_improve_historical_yield_baseline')
        if checks['W3_nonworse_years_than_W1C']<3 or checks['W3_nonworse_years_than_W1M']<3:
            reasons.append('W3_not_nonworse_than_both_calendar_controls_in_majority_of_years')
    return {'formal_yield_comparison_complete':complete,'Y_W3P_success':complete and not reasons,'checks':checks,'reasons':reasons,
            'forecast_scope':'conditional_on_realized_reanalysis_weather; not operational forecast'}


def run_yield(root,cfg,master,builder):
    normal=master[master.yield_main_eligible.eq(1)&master.final_yield_kg_per_mu.notna()].copy()
    base_pass=len(normal)>=cfg['yield_min_seasons'] and normal.harvest_year.nunique()>=cfg['yield_min_years']
    if not base_pass: raise ValueError('Normal-year yield sample gate failed')
    validator=YieldValidator(root,cfg,builder)
    all_predictions=[]; all_status=[]
    pred,status=validator.run_cohort('MAIN',normal,validator.config['models'],rolling=True)
    all_predictions.append(pred); all_status.append(status)
    for cohort,extra in validator.config['sensitivities'].items():
        data=pd.concat([normal,master[master.season_id.isin(extra)]],ignore_index=True)
        pred,status=validator.run_cohort(cohort,data,validator.config['models'],rolling=False)
        all_predictions.append(pred); all_status.append(status)
    predictions=pd.concat(all_predictions,ignore_index=True); statuses=pd.concat(all_status,ignore_index=True)
    comparison=summarize(predictions,statuses); gate=assess_yield(comparison,predictions)
    gate.update(normal_eligible_seasons=len(normal),normal_eligible_years=int(normal.harvest_year.nunique()),sample_gate_pass=True)
    target=root/cfg['outputs']/'yield'
    write_csv(target/'cv_predictions.csv',predictions); write_csv(target/'model_comparison.csv',comparison)
    write_csv(target/'execution_by_fold.csv',statuses); write_csv(target/'alpha_candidate_scores.csv',validator.candidate_rows)
    write_csv(target/'parameters_by_fold.csv',validator.parameter_rows); write_csv(target/'feature_partition_manifest.csv',validator.lineage)
    write_json(target/'fitted_models.json',validator.fit_models); write_json(target/'yield_gate.json',gate)
    folds=[{'cohort':c,'validation':v,'model_id':m,'holdout_year':int(y),**yield_metrics(g)} for (c,v,m,y),g in predictions.groupby(['cohort','validation','model_id','holdout_year'])]
    orchards=[{'cohort':c,'validation':v,'model_id':m,'orchard_id':o,**yield_metrics(g)} for (c,v,m,o),g in predictions.groupby(['cohort','validation','model_id','orchard_id'])]
    write_csv(target/'fold_metrics.csv',folds); write_csv(target/'orchard_metrics.csv',orchards)
    secondary=[{'target':name,'normal_n_nonmissing':int(normal[name].notna().sum()),'normal_n_total':len(normal),
                 'status':'descriptive_only_no_additional_model_search'} for name in validator.config['secondary_targets']]
    write_csv(target/'secondary_target_missingness.csv',secondary)
    main=comparison[(comparison.cohort=='MAIN')&(comparison.validation=='LOYO')]
    (root/cfg['reports']/'06_YIELD_MODEL_REPORT.md').write_text(f'''# 正常产量：相同算法、分区重建特征

正常主样本{len(normal)}个、{normal.harvest_year.nunique()}年；办内2025和红明2025/2026不入主训练。主目标kg/亩，树类行不是独立样本。

## 主LOYO比较

{markdown_table(main)}

partial_not_matched_main的模型只保留审计记录，不可拿其子集误差与完整主样本比较。未达阈值或缺物候造成特征不可用时，不填真实未来日期、不插补。

## 产量验证闸门

{json.dumps(gate,ensure_ascii=False,indent=2)}

所有Ridge共用训练均值/标准差缩放与同一alpha网格；每次内层按年验证重新生成窗口。W3训练行还会排除自身产季的物候校准数据。最多六个连续指标+果园编码；PHENO扩展用四个天气指标+两个预测日期。负预测不截断，单独计数，不能解释为可部署生产值。

## 前向滚动和恢复样本敏感性

{markdown_table(comparison[~((comparison.cohort=='MAIN')&(comparison.validation=='LOYO'))])}

滚动早期仅两训练年时，W3在内层的再交叉拟合可能没有历史，须标blocked而非用未来年补齐。红明2026没有定量物候，W2/W3敏感性可能被缺日期阻止，必须与可执行的固定窗口敏感性分开解读。恢复敏感性仅增加相应产量行，主物候校准资格不偷偷改变。2025办内绝收始终排除。

窗口优劣只能看共同完整样本的held-out误差；W2是回顾性上限。即使W3优于基线，输入仍是已实现ERA5天气，只支持条件预测，不等于实际发行日拥有未来天气预报。次级/代理目标只报告完整度，未新增一轮自动模型搜索。
''',encoding='utf-8')
    print('YIELD: '+main[['model_id','status','n_predictions','MAE_kg_mu']].to_json(orient='records'),flush=True)
    print('YIELD GATE: '+json.dumps(gate,ensure_ascii=False),flush=True)
    return predictions,comparison,gate
