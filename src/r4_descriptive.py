"""Prespecified descriptive summaries; no outcome-guided threshold selection."""
import pandas as pd
from .io_utils import write_csv
from .phenology_models import primary_candidates
from .r4_weather_loader import TASK_EVENTS
from .reporting import markdown_table


def describe(root,cfg,master,weather):
    durations=[]; summaries=[]
    for season in master.itertuples():
        for task,(start_name,end_name) in TASK_EVENTS.items():
            start,end=getattr(season,start_name),getattr(season,end_name)
            valid=pd.notna(start) and pd.notna(end) and end>start
            durations.append({'season_id':season.season_id,'orchard_id':season.orchard_id,'harvest_year':season.harvest_year,
                'task':task,'start_date':start,'end_date':end,'duration_days':(end-start).days if valid else None,
                'phenology_main_eligible':season.phenology_main_eligible,'complete_pair':valid})
            if not valid or task not in ['P1','P2','P3']: continue
            w=weather.daily[season.orchard_id].loc[start:end]
            row={'season_id':season.season_id,'task':task,'expected_days':(end-start).days+1,'actual_days':len(w),
                 'tmean_c_mean':w.tmean_c.mean(),'tmin_c_min':w.tmin_c.min(),'precip_mm_sum':w.precip_mm.sum(),
                 'et0_mm_sum':w.et0_mm.sum(),'P_minus_ET0_mm':(w.precip_mm-w.et0_mm).sum(),
                 'precipitation_hours':w.precipitation_hours.sum(),'shortwave_radiation_mean':w.shortwave_radiation_mj_m2.mean()}
            specs=primary_candidates('P1',weather.config) if task=='P1' else [{'model_id':task,'kind':'gdd','temperature':10}]
            for s in specs:
                if s['kind'] in ['duration','calendar','triangular_hour']: continue
                name=s['model_id']+'_'+s.get('variable','temperature')+'_'+str(s['temperature'])
                row[name]=weather.accumulation(season.orchard_id,s,start,end)
            summaries.append(row)
    durations=pd.DataFrame(durations)
    write_csv(root/cfg['outputs']/'descriptive/stage_duration.csv',durations)
    write_csv(root/cfg['outputs']/'descriptive/stage_weather_summary.csv',summaries)
    summary=durations[durations.complete_pair].groupby('task').duration_days.agg(['count','median','min','max']).reset_index()
    (root/cfg['reports']/'01_R4_DESCRIPTIVE_REPORT.md').write_text(f'''# R4气象—物候描述

{markdown_table(summary)}

这些表仅总结真实阶段和全部预注册低温候选，不用全数据选阈值。包含灾害/恢复样本的描述不改变主训练资格。P1/P2/P3主分析各12个终点；小时记录不增加独立样本量。

主气象为果园定位ERA5再分析，不能称为实测站气象。持续时间是不包含首日的日期差，天气累计按两端包含计算，所以天气日数等于持续天数+1。图表将在最终图集汇总，未用示意曲线替代实验输出。
''',encoding='utf-8')
    return durations
