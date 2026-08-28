"""Immutable R4 source takeover and fail-closed full-coverage checks."""
from __future__ import annotations

import itertools
import json
from pathlib import Path
import numpy as np
import pandas as pd
import yaml

from .io_utils import sha256, write_csv, write_json, assert_inputs_unchanged
from .reporting import markdown_table

R4_FOLDERS=['qc','descriptive','phenology','windows','yield','typhoon','scenarios','figures','logs']
TASK_EVENTS={'P1':('autumn_flush_mature','inflorescence_emergence'),
             'P2':('inflorescence_emergence','full_bloom'),
             'P3':('full_bloom','maturity'),
             'P1A':('autumn_flush_mature','white_tip'),
             'P1B':('white_tip','inflorescence_emergence')}


def settings(root,cfg,name):
    return yaml.safe_load((root/cfg[name+'_config']).read_text(encoding='utf-8'))


def freeze_r4(root,cfg):
    for folder in R4_FOLDERS: (root/cfg['outputs']/folder).mkdir(parents=True,exist_ok=True)
    (root/cfg['reports']).mkdir(parents=True,exist_ok=True)
    legacy=yaml.safe_load((root/cfg['legacy_config']).read_text(encoding='utf-8'))
    assert_inputs_unchanged(root,legacy)
    names=[cfg[k] for k in ['weather_main_daily','weather_main_hourly','weather_metadata',
                            'weather_dictionary','phenology_source','yield_source','protocol']]
    names.append(cfg['regional_sensitivity_daily'])
    manifest=[{'path':name,'sha256':sha256(root/name),'bytes':(root/name).stat().st_size} for name in names]
    path=root/'data/metadata/r4_input_hashes.json'
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8'))!=manifest:
            raise RuntimeError('R4 input changed since freeze; review and explicitly version the source, never silently re-freeze')
    else: write_json(path,manifest)
    return manifest


def read_weather(root,cfg):
    daily=pd.read_csv(root/cfg['weather_main_daily'],parse_dates=['date'])
    hourly=pd.read_csv(root/cfg['weather_main_hourly'],parse_dates=['time'])
    metadata=json.loads((root/cfg['weather_metadata']).read_text(encoding='utf-8'))
    return daily,hourly,metadata


def master_table(root,cfg):
    master=pd.read_csv(root/cfg['yield_source'])
    events=pd.read_csv(root/cfg['phenology_source'],parse_dates=['event_date'])
    if events.duplicated(['orchard_id','harvest_year','event_name']).any():
        raise ValueError('Duplicate event label: do not silently average source blocks')
    wide=events.pivot(index=['orchard_id','harvest_year'],columns='event_name',values='event_date').reset_index()
    # Source master already contains some event dates. Replace only this R4 derived copy.
    overlap=set(wide)-{'orchard_id','harvest_year'}
    master=master.drop(columns=[c for c in overlap if c in master]).merge(wide,on=['orchard_id','harvest_year'],validate='one_to_one')
    master=master.rename(columns={'station_id':'legacy_station_id'})
    master['weather_point_id']=master.orchard_id+'_orchard_era5'
    master['weather_role']=cfg['weather_role']
    return master.sort_values(['orchard_id','harvest_year']).reset_index(drop=True)


def task_frame(master,task,cohort='main'):
    start,end=TASK_EVENTS[task]
    allowed=master.phenology_main_eligible.eq(1)
    if cohort=='bannei_early_sensitivity': allowed|=master.phenology_sensitivity_eligible.eq(1)
    if cohort=='hongming_2025_sensitivity': allowed|=master.season_id.eq('hongming_2025')
    valid=master[start].notna()&master[end].notna()&(master[end]>master[start])
    result=master.loc[allowed&valid,['season_id','orchard_id','harvest_year',start,end]].copy()
    result=result.rename(columns={start:'start_date',end:'end_date'})
    result['duration_days']=(result.end_date-result.start_date).dt.days
    return result.reset_index(drop=True)


def audit(root,cfg):
    manifest=freeze_r4(root,cfg)
    daily,hourly,meta=read_weather(root,cfg)
    master=master_table(root,cfg)
    expected_d=pd.date_range(cfg['start_date'],cfg['end_date'],freq='D')
    expected_h=pd.date_range(cfg['start_date'],pd.Timestamp(cfg['end_date'])+pd.Timedelta(hours=23),freq='h')
    checks=[]
    def check(name,ok,detail): checks.append({'check':name,'pass':bool(ok),'detail':str(detail)})
    check('daily_row_count',len(daily)==cfg['daily_rows'],len(daily))
    check('hourly_row_count',len(hourly)==cfg['hourly_rows'],len(hourly))
    check('orchard_sets',set(daily.orchard_id)==set(hourly.orchard_id)==set(cfg['orchards']),sorted(daily.orchard_id.unique()))
    check('daily_unique',not daily.duplicated(['orchard_id','date']).any(),'orchard-date')
    check('hourly_unique',not hourly.duplicated(['orchard_id','time']).any(),'orchard-time')
    check('metadata_source',meta['source']['model']=='era5' and meta['source']['timezone']==cfg['timezone'],meta['source']['model'])
    grids=[]
    for orchard,coordinates in cfg['orchards'].items():
        d=daily[daily.orchard_id==orchard]; h=hourly[hourly.orchard_id==orchard]
        check(orchard+'_daily_continuity',pd.DatetimeIndex(d.date).sort_values().equals(expected_d),len(d))
        check(orchard+'_hourly_continuity',pd.DatetimeIndex(h.time).sort_values().equals(expected_h),len(h))
        for name,frame in [('daily',d),('hourly',h)]:
            check(orchard+'_'+name+'_coordinates',
                  np.allclose(frame.requested_latitude,coordinates[0],rtol=0,atol=cfg['coordinate_tolerance']) and
                  np.allclose(frame.requested_longitude,coordinates[1],rtol=0,atol=cfg['coordinate_tolerance']),coordinates)
            check(orchard+'_'+name+'_timezone',frame.timezone.eq(cfg['timezone']).all(),cfg['timezone'])
        point=meta['points'][orchard]
        grids.append({'orchard_id':orchard,'requested_latitude':coordinates[0],'requested_longitude':coordinates[1],
                      'grid_latitude':point['returned_grid_latitude'],'grid_longitude':point['returned_grid_longitude'],
                      'elevation_m':point['elevation_m'],'grid_distance_km':d.grid_distance_km.iloc[0]})
        for frame,name in [(d,'daily'),(h,'hourly')]:
            check(orchard+'_'+name+'_metadata_grid',
                  frame.grid_latitude.eq(point['returned_grid_latitude']).all() and frame.grid_longitude.eq(point['returned_grid_longitude']).all(),'returned API grid, not orchard coordinate')
    for frame,scale in [(daily,'daily'),(hourly,'hourly')]:
        values=frame[cfg['main_'+scale+'_variables']].to_numpy(dtype=float)
        check(scale+'_main_variables_finite',np.isfinite(values).all(),int((~np.isfinite(values)).sum()))
        humidity=[c for c in frame if c.startswith('relative_humidity')]
        soil=[c for c in frame if c.startswith('soil_moisture')]
        check(scale+'_humidity_range',frame[humidity].ge(0).all().all() and frame[humidity].le(100).all().all(),'0..100%')
        check(scale+'_soil_moisture_range',frame[soil].ge(0).all().all() and frame[soil].le(1).all().all(),'0..1 m3/m3')
        check(scale+'_nonnegative',frame[['precip_mm','rain_mm','et0_mm']].ge(0).all().all(),'precipitation, rain, ET0')
        vpd='vpd_max_kpa' if scale=='daily' else 'vpd_kpa'
        check(scale+'_vpd_range',frame[vpd].ge(0).all(),'VPD >= 0')
    check('temperature_order',((daily.tmin_c<=daily.tmean_c)&(daily.tmean_c<=daily.tmax_c)).all(),'tmin <= tmean <= tmax')
    pairs=[]
    for left,right in itertools.combinations(cfg['orchards'],2):
        a=daily[daily.orchard_id==left].set_index('date'); b=daily[daily.orchard_id==right].set_index('date')
        for variable in ['tmean_c','precip_mm']:
            pairs.append({'orchard_a':left,'orchard_b':right,'variable':variable,
                          'exactly_identical':a[variable].equals(b[variable]),
                          'mean_absolute_difference':float((a[variable]-b[variable]).abs().mean()),
                          'pearson_r':float(a[variable].corr(b[variable]))})
    daily_hourly=[]
    agg=hourly.assign(date=hourly.time.dt.normalize()).groupby(['orchard_id','date']).temperature_c.agg(['mean','min','max'])
    matched=daily.set_index(['orchard_id','date']).join(agg)
    for orchard,g in matched.groupby(level=0):
        error=g.tmean_c-g['mean']
        daily_hourly.append({'orchard_id':orchard,'mean_abs_tmean_difference_c':float(error.abs().mean()),
                             'max_abs_tmean_difference_c':float(error.abs().max()),'daily_hourly_days_compared':len(g)})
    check('daily_hourly_local_date_alignment',max(r['max_abs_tmean_difference_c'] for r in daily_hourly)<=cfg['daily_hourly_tmean_rounding_tolerance_c'],'API rounded daily vs 24 local hourly values; tolerance 0.1 C')
    check('master_unique',not master.season_id.duplicated().any(),len(master))
    check('a39_preserved_2026',not master.year_protocol_conflict.any(),'latest confirmed source authority remains 2026')
    check('bannei_disaster_excluded',master.loc[master.season_id.eq('bannei_2025'),'yield_main_eligible'].eq(0).all(),'zero yield retained')
    checks=pd.DataFrame(checks); grid=pd.DataFrame(grids)
    normal=master[master.yield_main_eligible.eq(1)&master.final_yield_kg_per_mu.notna()]
    gate={'status':'pass' if checks['pass'].all() else 'blocked','weather_role':cfg['weather_role'],
          'daily_rows':len(daily),'hourly_rows':len(hourly),'orchards':len(grid),'daily_days_per_orchard':len(expected_d),
          'hourly_times_per_orchard':len(expected_h),'timezone':cfg['timezone'],
          'main_phenology_samples':{task:len(task_frame(master,task)) for task in TASK_EVENTS},
          'normal_yield_candidates':len(normal),'normal_yield_years':sorted(map(int,normal.harvest_year.unique())),
          'independent_environment_unit':'orchard x harvest_year; not daily/hourly rows',
          'failed_checks':checks.loc[~checks['pass'],'check'].tolist(),'raw_sources_mutated':False,
          'yield_gate':'pending_nested_feature_completeness','source_manifest_files':len(manifest),
          'distinct_returned_grids':len(grid[['grid_latitude','grid_longitude']].drop_duplicates())}
    target=root/cfg['outputs']/'qc'
    write_csv(target/'data_integrity_checks.csv',checks)
    write_csv(target/'grid_identity.csv',grid)
    write_csv(target/'pairwise_weather_identity.csv',pairs)
    write_csv(target/'daily_hourly_consistency.csv',daily_hourly)
    write_csv(root/'data/processed/r4_orchard_season_master.csv',master)
    write_json(target/'analysis_gate_r4.json',gate)
    text=f'''# R4 Phase 0：精确坐标数据接管与闸门

状态：**{gate['status']}**。逐日{len(daily)}行，逐小时{len(hourly)}行；每园{len(expected_d)}日、{len(expected_h)}小时。覆盖{cfg['start_date']}至{cfg['end_date']}，本地时区{cfg['timezone']}。完整检查见data_integrity_checks.csv，不以文件行数替代连续性检查。

## 实际网格身份

{markdown_table(grid)}

{markdown_table(pd.DataFrame(pairs))}

请求坐标精确不等于网格空间分辨率达到果园尺度。三园落在{gate['distinct_returned_grids']}个返回网格；相邻园天气仍有空间相关性。数据必须称为“按果园坐标提取的ERA5网格再分析”，不能称现场气象站实测。API elevation是降尺度使用的返回高程，不能自动称为原生网格平均地形高度。[Open-Meteo官方说明](https://open-meteo.com/en/docs/historical-weather-api)

## 日小时对齐

{markdown_table(pd.DataFrame(daily_hourly))}

小时标签按API元数据的上海本地时间读取，不再重复加8小时；每日24小时温度均值与API日均的微小差异按0.1℃舍入容差核验。小时雨量是前一小时累计，不能把它解释为瞬时雨强。主实验沿用API日聚合的降水指标。

## 独立终点与资格

主分析P1/P2/P3各{len(task_frame(master,'P1'))}条；正常产量候选{len(normal)}个，{normal.harvest_year.nunique()}年。129240小时不是独立标签数。2025办内最终产量0，未测构成NA；办内2025、红明2025/2026不入正常产量主训练。沿用已确认A列跨年物候，不改月日、A39或原始文件。

## 下阶段

通过天气QC后先执行预注册候选的嵌套LOYO及前向滚动；产量仍须检查各折动态特征完整性。全部配置须先提交，不能看到外层结果后改候选网格。R4结果独立写入results/r4与reports/r4，不覆盖R2/R3。
'''
    (root/cfg['reports']/'00_R4_DATA_GATE_REPORT.md').write_text(text,encoding='utf-8')
    return gate,daily,hourly,master
