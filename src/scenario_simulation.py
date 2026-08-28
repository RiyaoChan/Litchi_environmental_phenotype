"""Fixed-model, gate-controlled perturbations. This module never fits a model."""
from __future__ import annotations
import json
import numpy as np
import pandas as pd

from .io_utils import write_csv,write_json
from .phenology_models import WeatherStore,predict_fit
from .r4_weather_loader import task_frame,settings
from .yield_models import predict_ridge
from .reporting import markdown_table


def perturb_air_temperature(weather,delta):
    daily=pd.concat([frame.reset_index() for frame in weather.daily.values()],ignore_index=True)
    hourly=pd.concat([frame.reset_index() for frame in weather.hourly.values()],ignore_index=True)
    for variable in ['tmean_c','tmin_c','tmax_c']: daily[variable]=daily[variable]+delta
    hourly['temperature_c']=hourly.temperature_c+delta
    return WeatherStore(daily,hourly,weather.config)


def simulate_fixed_fit(fit,samples,weather,delta=0.0,delay_days=0):
    changed=samples.copy()
    changed['start_date']=changed.start_date+pd.Timedelta(days=delay_days)
    counter=perturb_air_temperature(weather,delta) if delta else weather
    return predict_fit(fit,changed,counter)


def stable_model(root,cfg,task):
    path=root/cfg['outputs']/'phenology'
    stable=pd.read_csv(path/f'{task}_stability_diagnostics.csv')
    allowed=set(stable.loc[stable.stable_superiority,'model_id'])
    comparison=pd.read_csv(path/f'{task}_model_comparison.csv')
    eligible=comparison[(comparison.validation=='LOYO')&comparison.model_id.isin(allowed)]
    if eligible.empty: return None
    return eligible.sort_values(['MAE_days','model_id']).iloc[0].model_id


def run_scenarios(root,cfg,master,engine,yield_gate):
    scenario_cfg=settings(root,cfg,'scenario')
    results=[]; statuses=[]
    for task in ['P1','P2','P3']:
        selected=stable_model(root,cfg,task)
        if selected is None:
            ids=['S1','S2','S3'] if task=='P1' else ['S4-'+task]
            statuses.extend({'experiment_id':x,'status':'blocked','reason':task+'_no_stable_weather_superiority'} for x in ids)
            continue
        stored=json.loads((root/cfg['outputs']/f'phenology/{task}_fitted_models.json').read_text(encoding='utf-8'))
        frame=task_frame(master,task)
        if task=='P1':
            scenarios=[('S1',t,0) for t in scenario_cfg['S1_temperature_offsets_c']]
            scenarios += [('S2',0,d) for d in scenario_cfg['S2_flush_delay_days']]
            scenarios += [('S3',t,d) for t,d in scenario_cfg['S3_joint']]
        else: scenarios=[('S4-'+task,t,0) for t in scenario_cfg['S4_temperature_offsets_c']]
        for sid,delta,delay in scenarios:
            for year,g in frame.groupby('harvest_year'):
                fit_id=f'main_{task}_{selected}_LOYO_{year}'
                fitted=stored[fit_id]
                before=json.dumps(fitted,sort_keys=True)
                reference=predict_fit(fitted,g,engine.weather).set_index('season_id')
                altered=simulate_fixed_fit(fitted,g,engine.weather,delta,delay).set_index('season_id')
                assert json.dumps(fitted,sort_keys=True)==before
                for row in g.itertuples():
                    a=reference.loc[row.season_id,'predicted_event_date']; b=altered.loc[row.season_id,'predicted_event_date']
                    results.append({'experiment_id':sid,'task':task,'model_id':selected,'fit_id':fit_id,
                        'season_id':row.season_id,'orchard_id':row.orchard_id,'harvest_year':int(year),
                        'temperature_shift_c':delta,'flush_start_delay_days':delay,'original_start_date':row.start_date,
                        'reference_predicted_date':a,'scenario_predicted_date':b,
                        'date_shift_days':(b-a).days if pd.notna(a) and pd.notna(b) else np.nan,
                        'prediction_status':altered.loc[row.season_id,'prediction_status'],
                        'parameters_refitted':False,'interpretation':'fixed_model_conditional_sensitivity_not_future_weather_forecast'})
        statuses.extend({'experiment_id':sid,'status':'executed','reason':'stable_'+selected+'_fixed_LOYO_fit'} for sid in sorted(set(s[0] for s in scenarios)))
    target=root/cfg['outputs']/'scenarios'
    frame=pd.DataFrame(results)
    write_csv(target/'phenology_scenarios.csv',frame)
    if not frame.empty:
        summary=frame.groupby(['experiment_id','task','temperature_shift_c','flush_start_delay_days']).date_shift_days.agg(['count','mean','median','min','max']).reset_index()
    else: summary=pd.DataFrame()
    write_csv(target/'scenario_summary.csv',summary)
    s5=[]
    if yield_gate.get('Y_W3P_success'):
        features=pd.read_csv(root/cfg['outputs']/'windows/W3_predicted_features.csv')
        features=features[features.role=='evaluation']
        fits=json.loads((root/cfg['outputs']/'yield/fitted_models.json').read_text(encoding='utf-8'))
        for _,row in features.iterrows():
            fit=fits[f'MAIN_LOYO_outer_{int(row.harvest_year)}_Y-W3P']
            one=row.to_frame().T
            reference=float(predict_ridge(fit,one)[0])
            fruit=engine.weather.daily[row.orchard_id].loc[row.fruit_development_start:row.fruit_development_end]
            for label in ['fruit_temperature_plus_1C','heat_days_plus_5_equivalent']:
                altered=one.copy()
                if label=='fruit_temperature_plus_1C':
                    altered['fruit_gdd']=float(np.maximum(0,fruit.tmean_c+1-10).sum())
                    altered['fruit_heat_days']=int((fruit.tmax_c+1>32).sum())
                else: altered['fruit_heat_days']=min(len(fruit),float(row.fruit_heat_days)+5)
                value=float(predict_ridge(fit,altered)[0])
                s5.append({'season_id':row.season_id,'scenario':label,'reference_yield':reference,
                           'scenario_yield':value,'difference_kg_mu':value-reference,
                           'scope':'exploratory_fixed_predicted_boundaries_and_fixed_ridge_not_full_chain_counterfactual'})
        statuses.append({'experiment_id':'S5-temperature-heat','status':'executed_exploratory','reason':'validated_Y-W3P; fixed predicted boundaries'})
        statuses.append({'experiment_id':'S5-rainfall-amount','status':'unsupported','reason':'registered predictor uses rainfall hours, not flowering rainfall amount; do not pretend zero identifies a physiological effect'})
    else: statuses.append({'experiment_id':'S5','status':'blocked','reason':'normal_Y-W3P_not_validated'})
    write_csv(target/'yield_scenarios.csv',s5,columns=['season_id','scenario','reference_yield','scenario_yield','difference_kg_mu','scope'])
    write_csv(target/'scenario_status.csv',statuses)
    write_json(target/'scenario_gate.json',{'statuses':statuses,'model_refits':0})
    (root/cfg['reports']/'08_SCENARIO_REPORT.md').write_text(f'''# 模型验证约束下的情景

{markdown_table(pd.DataFrame(statuses))}

## 实际获准的固定模型结果

{markdown_table(summary)}

变化=扰动后的预测日期−未扰动的预测日期，而不是减去实测日期；负值为提前。每个样本使用其LOYO训练折既有模型，不重新拟合参数。升温同步改变日均/最高/最低及小时气温，雨量、辐射、VPD、土壤湿度不改；这是受控输入敏感性，不是完整气候耦合模拟。

秋梢推迟只改累计起点，不删除或重写天气历史。对应模型未验证时不输出正式影响天数。P2情景以实际抽穗起点为条件，并不意味着整条秋梢→成熟链已验证。由于只有5年，不能把数值当确定生产预报。

若S5获准，只报告固定预测边界下的探索性Ridge特征扰动；增加5个高温日是特征级等价扰动，不是创造一段真实气象。主模型只有花期降雨小时数，花期雨量±20%的强度变化不直接对应该输入，故不把没有相应变量的模型解释成“降雨无效”。
''',encoding='utf-8')
    return pd.DataFrame(statuses),summary


def typhoon_reference(root,cfg,master,builder,yield_gate):
    row={'season_id':'bannei_2025','actual_yield_kg_mu':0,'normal_production_reference_kg_mu':np.nan,
         'reference_gap_kg_mu':np.nan,'status':'blocked_no_validated_normal_Y-W3P',
         'interpretation':'model_based_normal_production_reference_gap_not_causal_typhoon_loss'}
    if yield_gate.get('Y_W3P_success'):
        normal=master[master.yield_main_eligible.eq(1)&master.harvest_year.ne(2025)]
        case=master[master.season_id=='bannei_2025']
        _,features=builder.partition(normal,case,'W3-PRED')
        if features.feature_status.eq('complete').all():
            fits=json.loads((root/cfg['outputs']/'yield/fitted_models.json').read_text(encoding='utf-8'))
            fit=fits['MAIN_LOYO_outer_2025_Y-W3P']
            value=float(predict_ridge(fit,features)[0])
            row.update(normal_production_reference_kg_mu=value,reference_gap_kg_mu=value,
                       status='model_reference_only' if value>=0 else 'unsupported_negative_reference')
    write_csv(root/cfg['outputs']/'typhoon/bannei_2025_reference.csv',[row])
    (root/cfg['reports']/'07_TYPHOON_CASE_REPORT.md').write_text(f'''# 办内2025：外部灾害案例

{markdown_table(pd.DataFrame([row]))}

实际亩产0保留；未测单株产量、单果重、果数仍NA。它不进入正常产量训练，P1早期敏感性另行报告。2025-03-01是放弃投产决定日，不是台风发生时间。

只有正常W3产量模型获准后才计算上述条件参照，并留出整个2025年校准。差额不是因果台风损失：仅一个绝收案例、管理策略改变、缺少完整风害剂量信息。没有验证模型时NA不代表损失为0。
''',encoding='utf-8')
    return row
