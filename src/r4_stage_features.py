"""Partition-aware weather windows; W3 dates are recursively cross-fitted."""
from __future__ import annotations
import json
import math
import numpy as np
import pandas as pd

from .io_utils import write_csv,write_json,season_bound
from .r4_weather_loader import task_frame,settings
from .phenology_models import predict_fit,day_offset
from .reporting import markdown_table

KINDS=['W1-CALENDAR','W1-MEDIAN','W2-OBS','W3-PRED']
EVENTS=['autumn_flush_mature','inflorescence_emergence','full_bloom','maturity']


class WindowBuilder:
    def __init__(self,root,cfg,master,engine):
        self.root=root; self.cfg=cfg; self.master=master.copy(); self.engine=engine
        self.config=settings(root,cfg,'windows')
        self._chains={}; self._partitions={}; self._metrics={}

    def pool(self,years,task):
        return task_frame(self.master[self.master.harvest_year.isin(years)],task)

    def metric(self,years):
        key=tuple(sorted(years))
        if key not in self._metrics:
            frame=self.pool(key,'P1')
            if frame.empty: raise ValueError('No training phenology to select a common induction metric')
            self._metrics[key]=self.engine.fit(frame,'P1',weather_only=True,daily_only=True)['spec']
        return self._metrics[key]

    def chain(self,years,season):
        # Cache identity deliberately excludes all future observed event dates.
        key=(tuple(sorted(years)),season.season_id,str(season.autumn_flush_mature))
        if key in self._chains: return self._chains[key]
        dates=[season.autumn_flush_mature]; trace=[]
        for task in ['P1','P2','P3']:
            training=self.pool(years,task)
            if pd.isna(dates[-1]) or training.empty:
                dates.append(pd.NaT)
                trace.append({'task':task,'status':'missing_predicted_start_or_training_history','training_years':sorted(map(int,years))})
                continue
            fitted=self.engine.fit(training,task)
            test=pd.DataFrame([{'season_id':season.season_id,'orchard_id':season.orchard_id,
                                'harvest_year':season.harvest_year,'start_date':dates[-1]}])
            prediction=predict_fit(fitted,test,self.engine.weather).iloc[0]
            dates.append(prediction.predicted_event_date)
            trace.append({'task':task,'status':prediction.prediction_status,'model_id':fitted['spec']['model_id'],
                          'spec':fitted['spec'],'threshold':prediction.fitted_threshold,
                          'training_years':fitted['training_years'],'training_season_ids':fitted['training_season_ids']})
        self._chains[key]=(dates,trace)
        return dates,trace

    def boundaries(self,kind,years,season):
        trace=[]
        if kind=='W1-CALENDAR':
            bounds=[tuple(season_bound(x,int(season.harvest_year)) for x in pair) for pair in self.config['calendar'].values()]
        elif kind=='W2-OBS':
            dates=[season[e] for e in EVENTS]
            bounds=list(zip(dates[:-1],dates[1:]))
        elif kind=='W1-MEDIAN':
            data=self.master[self.master.harvest_year.isin(years)&self.master.phenology_main_eligible.eq(1)]
            local=data[data.orchard_id==season.orchard_id]
            dates=[]
            for event in EVENTS:
                fit=local[local[event].notna()]
                if fit.empty: fit=data[data[event].notna()]
                offsets=[day_offset(r[event],r.harvest_year) for _,r in fit.iterrows()]
                date=pd.Timestamp(int(season.harvest_year),1,1)+pd.Timedelta(days=math.floor(float(np.median(offsets))+.5)) if offsets else pd.NaT
                dates.append(date)
            bounds=list(zip(dates[:-1],dates[1:]))
        elif kind=='W3-PRED':
            dates,trace=self.chain(years,season)
            bounds=list(zip(dates[:-1],dates[1:]))
        else: raise ValueError(kind)
        return bounds,trace

    def row(self,kind,boundary_years,metric_years,season,role):
        bounds,trace=self.boundaries(kind,boundary_years,season)
        spec=self.metric(metric_years)
        row={'season_id':season.season_id,'orchard_id':season.orchard_id,'harvest_year':int(season.harvest_year),
             'window_type':kind,'role':role,'boundary_training_years':';'.join(map(str,sorted(boundary_years))),
             'metric_training_years':';'.join(map(str,sorted(metric_years))),
             'induction_metric_spec':json.dumps(spec,sort_keys=True),'chain_trace':json.dumps(trace,sort_keys=True),
             'feature_status':'complete','prediction_context':'realized_weather_conditional; W2_has_observed_future_boundaries'}
        for feature in self.config['continuous_features']+self.config['pheno_extension_features']: row[feature]=np.nan
        weather=self.engine.weather
        for label,(start,end) in zip(['induction','flowering','fruit_development'],bounds):
            row[label+'_start']=start; row[label+'_end']=end
            if pd.isna(start) or pd.isna(end) or end<=start or start<weather.origin or end>weather.end:
                row['feature_status']='invalid_or_unpredicted_boundary'
        if row['feature_status']!='complete': return row
        ind=weather.daily[season.orchard_id].loc[bounds[0][0]:bounds[0][1]]
        flower=weather.daily[season.orchard_id].loc[bounds[1][0]:bounds[1][1]]
        fruit=weather.daily[season.orchard_id].loc[bounds[2][0]:bounds[2][1]]
        row.update(induction_temperature_metric=weather.accumulation(season.orchard_id,spec,*bounds[0]),
                   induction_water_balance_mm=float((ind.precip_mm-ind.et0_mm).sum()),
                   flowering_precipitation_hours=float(flower.precipitation_hours.sum()),
                   flowering_radiation_mean=float(flower.shortwave_radiation_mj_m2.mean()),
                   fruit_gdd=float(np.maximum(0,fruit.tmean_c-self.config['gdd_reference_base_c']).sum()),
                   fruit_heat_days=int((fruit.tmax_c>self.config['heat_threshold_c']).sum()),
                   predicted_inflorescence_date_offset=day_offset(bounds[0][1],season.harvest_year),
                   predicted_full_bloom_date_offset=day_offset(bounds[1][1],season.harvest_year))
        if not all(np.isfinite(row[f]) for f in self.config['continuous_features']): row['feature_status']='nonfinite_feature'
        return row

    def partition(self,training,evaluation,kind):
        key=(tuple(sorted(training.season_id)),tuple(sorted(evaluation.season_id)),kind)
        if key in self._partitions:
            a,b=self._partitions[key]; return a.copy(),b.copy()
        years=sorted(map(int,training.harvest_year.unique()))
        rows=[]
        for role,frame in [('training',training),('evaluation',evaluation)]:
            for _,season in frame.iterrows():
                boundary_years=[y for y in years if y!=season.harvest_year] if kind=='W3-PRED' and role=='training' else years
                rows.append(self.row(kind,boundary_years,years,season,role))
        result=pd.DataFrame(rows)
        a=result[result.role=='training'].copy(); b=result[result.role=='evaluation'].copy()
        self._partitions[key]=(a,b)
        return a.copy(),b.copy()


def run_windows(root,cfg,master,engine):
    builder=WindowBuilder(root,cfg,master,engine)
    normal=master[master.yield_main_eligible.eq(1)&master.final_yield_kg_per_mu.notna()]
    frames=[]
    for year in sorted(normal.harvest_year.unique()):
        training=normal[normal.harvest_year!=year]; testing=normal[normal.harvest_year==year]
        for kind in KINDS:
            a,b=builder.partition(training,testing,kind)
            frame=pd.concat([a,b],ignore_index=True)
            frame['outer_holdout_year']=int(year); frames.append(frame)
    all_features=pd.concat(frames,ignore_index=True)
    target=root/cfg['outputs']/'windows'
    names=['W1_calendar_features','W1_median_features','W2_observed_features','W3_predicted_features']
    for kind,name in zip(KINDS,names): write_csv(target/(name+'.csv'),all_features[all_features.window_type==kind])
    evaluations=all_features[all_features.role=='evaluation']
    observed=evaluations[evaluations.window_type=='W2-OBS'].set_index('season_id')
    align=[]
    for r in evaluations.itertuples():
        ref=observed.loc[r.season_id]
        for stage in ['induction','flowering','fruit_development']:
            for edge in ['start','end']:
                value=getattr(r,stage+'_'+edge); true=ref[stage+'_'+edge]
                align.append({'season_id':r.season_id,'window_type':r.window_type,'boundary':stage+'_'+edge,
                              'window_date':value,'observed_date':true,
                              'boundary_error_days':(value-true).days if pd.notna(value) and pd.notna(true) else np.nan})
    write_csv(target/'window_alignment_diagnostics.csv',align)
    complete=evaluations.assign(complete=evaluations.feature_status.eq('complete')).groupby('window_type').agg(
        n_test_seasons=('season_id','size'),n_complete=('complete','sum')).reset_index()
    gate={'status':'pass' if all_features.feature_status.eq('complete').all() else 'partial',
          'evaluation_completeness':complete.to_dict('records'),
          'incomplete_training_rows':int(((all_features.role=='training')&(all_features.feature_status!='complete')).sum()),
          'P1_chain_status':'limited_primary_P1_weather_not_stably_validated',
          'W3_policy':'family_and_parameters_selected_only_within_current_calibration_years; recursive_predicted_starts',
          'yield_gate':'must_recheck_inner_partitions_too'}
    write_json(target/'window_gate.json',gate)
    (root/cfg['reports']/'05_DYNAMIC_WINDOW_REPORT.md').write_text(f'''# 四类窗口：边界与无泄漏构建

{markdown_table(complete)}

W1-CALENDAR为预注册固定月份；W1-MEDIAN只用当前训练划分的典型日期；W2-OBS使用真实未来物候，属于回顾性上限；W3-PRED按秋梢→预测抽穗→预测盛花→预测成熟串联。

所有外层训练行的W3均在该训练集内再留出其自身产季，边界训练年份与所用模型保存在chain_trace。验证行从未调用真实抽穗/盛花/成熟。各窗口在同一训练上下文使用同一个预注册诱导指标定义；气象与典型边界选择也需在产量内层划分重新计算。

当前P1气象模型未稳定优于历史基线，故W3为受限的混合历史/气象预测形式，不能称整链已验证。模型家族仍由当前训练年份内层验证选择，不从全体LOYO最佳模型倒灌，未达阈值边界标NA，不偷偷改用实测日期。

外层训练特征不完整行：{gate['incomplete_training_rows']}。产量必须再检查内层训练特征；四种窗口都具备日期不代表可直接发表产量性能。

以上窗口都使用已实现的ERA5天气，消除未来物候泄漏不等于解决未来天气未知问题。W2/W3是否比W1更有预测信息，要看后续相同样本、相同Ridge流程的留出误差，不能仅凭窗口不同认定更优。
''',encoding='utf-8')
    print('WINDOWS: '+json.dumps(gate,ensure_ascii=False),flush=True)
    return builder,all_features,gate
