"""Observed cross-year phenology, weather coverage, and honest LOYO baselines."""
from __future__ import annotations

import calendar
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

from .data_ingest import EVENTS, TRANSITIONS
from .io_utils import write_csv

EVENT_STYLE={
    'autumn_flush_mature':('Flush mature','s','#287d68'),
    'inflorescence_emergence':('Panicle','D','#b27a1f'),
    'full_bloom':('Full bloom','o','#a9528b'),
    'maturity':('Maturity','^','#446fa6'),
}
ORCHARD_STYLE={'bannei':('Bannei','o','#197d76'),
               'hongming':('Hongming','^','#ab6c24'),
               'luhong':('Luhong','s','#625da0')}


def create_descriptive_figures(root,events,master,weather,transitions,cfg,predictions=None):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,
                         'axes.spines.top':False,'axes.spines.right':False,
                         'axes.titleweight':'bold','savefig.facecolor':'white'})
    output=root/'results/figures'
    def save(fig,name):
        fig.savefig(output/(name+'.png'),dpi=170,bbox_inches='tight')
        fig.savefig(output/(name+'.pdf'),bbox_inches='tight',
                    metadata={'CreationDate':None,'ModDate':None,'Creator':'Litchi V2 audit pipeline'})
        plt.close(fig)

    fig,ax=plt.subplots(figsize=(9.3,4.8),layout='constrained')
    x=np.arange(3)
    for delta,column,color,label in [(-.25,'complete_date_pair','#aab9c7','All complete date pairs'),
                                    (0,'main_complete_date_pair','#197d76','Main-analysis date pairs'),
                                    (.25,'model_eligible','#bd7841','Complete-weather main samples')]:
        values=[int(transitions[transitions.task==t][column].sum()) for t in TRANSITIONS]
        ax.bar(x+delta,values,.23,color=color,label=label,zorder=2)
        for i,value in enumerate(values):
            ax.text(i+delta,value+.25,str(value),ha='center',weight='bold',color=color if value==0 else '#26323b')
    ax.set(xticks=x,xticklabels=['P1: flush to panicle','P2: panicle to full bloom','P3: full bloom to maturity'],
           ylim=(0,20),ylabel='Orchard-season records',title='Dates resolved; continuous weather remains the limiting input')
    ax.legend(frameon=False,loc='upper right',fontsize=9)
    ax.grid(axis='y',alpha=.18,zorder=0)
    save(fig,'Fig01_data_gate_counts')

    event_order=list(EVENTS.values())
    season_order=master.sort_values(['orchard_id','harvest_year']).season_id.tolist()
    short=['Flush mature','White tip','Panicle','Initial bloom','Full bloom','End bloom',
           'Fruit set','Drop 1','Drop 2','Preharvest drop','Color break','Maturity']
    matrix=[]
    for season in season_order:
        orchard,year=season.rsplit('_',1)
        subset=events[(events.orchard_id==orchard)&(events.harvest_year==int(year))].set_index('event_name')
        matrix.append([3 if row.qc_flag=='ok' else 0 if row.qc_flag=='missing' else 2 if row.qc_flag=='qualitative_not_date' else 1 for _,row in subset.reindex(event_order).iterrows()])
    fig,ax=plt.subplots(figsize=(11.6,7.1),layout='constrained')
    colors=['#f0f2f5','#e9b263','#b2bdca','#197d76']
    ax.imshow(matrix,cmap=ListedColormap(colors),norm=BoundaryNorm([-.5,.5,1.5,2.5,3.5],4),aspect='auto')
    ax.set(xticks=np.arange(12),xticklabels=short,yticks=np.arange(len(season_order)),yticklabels=season_order,
           title='Phenology status after A-column harvest-year normalization')
    plt.setp(ax.get_xticklabels(),rotation=40,ha='right')
    ax.legend(handles=[Patch(color=c,label=l) for c,l in zip(colors,['Missing','Unresolved date','Qualitative only','Validated seasonal date'])],
              loc='upper center',bbox_to_anchor=(.5,-.20),ncol=2,frameon=False)
    save(fig,'Fig02_phenology_input_status')

    fig,axes=plt.subplots(1,5,figsize=(15.8,4.6),sharey=True,layout='constrained')
    monthly=[]
    for ax,year in zip(axes,range(2022,2027)):
        dates=[pd.Timestamp(year-1,m,1) for m in range(8,13)]+[pd.Timestamp(year,m,1) for m in range(1,7)]
        z=[]
        for station,var in [('haikou_region_proxy','tmean_c'),('haikou_region_proxy','precip_mm'),('lingshui_region_proxy','tmean_c'),('lingshui_region_proxy','precip_mm')]:
            line=[]
            for month in dates:
                n=calendar.monthrange(month.year,month.month)[1]
                block=weather[(weather.station_id==station)&(weather.date.dt.year==month.year)&(weather.date.dt.month==month.month)]
                ratio=int(block[var].notna().sum())/n
                line.append(ratio)
                monthly.append({'harvest_year':year,'station_id':station,'variable':var,'calendar_month':month.strftime('%Y-%m'),'valid_days':int(block[var].notna().sum()),'expected_days':n,'coverage_ratio':ratio})
            z.append(line)
        im=ax.imshow(z,vmin=0,vmax=1,cmap='YlGnBu',aspect='auto')
        ax.axvline(4.5,color='#b27a1f',lw=1.5)
        ax.set(title=f'Harvest {year}',xticks=np.arange(11),xticklabels=['Aug','Sep','Oct','Nov','Dec','Jan','Feb','Mar','Apr','May','Jun'],
               yticks=np.arange(4),yticklabels=['Haikou temperature','Haikou rainfall','Lingshui temperature','Lingshui rainfall'])
        plt.setp(ax.get_xticklabels(),rotation=90)
    fig.suptitle('Daily weather coverage: previous Aug-Dec | harvest Jan-Jun',weight='bold',fontsize=13)
    fig.colorbar(im,ax=axes,location='bottom',shrink=.62,label='Valid days / calendar days (0 = no usable observations)',pad=.10)
    write_csv(root/'results/descriptive/weather_monthly_coverage.csv',monthly)
    save(fig,'Fig03_weather_availability')

    fig,axes=plt.subplots(1,3,figsize=(12.8,4.8),layout='constrained')
    styles={'normal':('o','#167d77'),'disaster':('*','#c74440'),'review':('^','#cb8f2e')}
    for ax,(orchard,g) in zip(axes,master.groupby('orchard_id',sort=True)):
        for row in g.itertuples():
            kind='disaster' if row.typhoon_damage==1 else 'review' if row.damage_review_reason else 'normal'
            marker,color=styles[kind]
            y=row.final_yield_kg_per_mu
            ax.scatter([row.harvest_year],[y],marker=marker,s=115 if kind=='disaster' else 65,color=color,zorder=3)
            ax.annotate(f'{y:.0f}',(row.harvest_year,y),xytext=(0,8),textcoords='offset points',ha='center',fontsize=9)
        ax.set(title=ORCHARD_STYLE[orchard][0],xticks=range(2022,2027),
               ylim=(-90,2100),xlim=(2021.6,2026.4),xlabel='Confirmed harvest year')
        ax.grid(axis='y',alpha=.2)
    axes[0].set_ylabel('Reported yield (kg / mu)')
    handles=[Line2D([0],[0],marker=m,color='none',markeredgecolor=c,markerfacecolor=c,
                    label=l,markersize=8) for (m,c),l in zip(styles.values(),['Normal candidate','Bannei disaster: true zero','Damage status under review'])]
    fig.legend(handles=handles,loc='outside lower center',ncol=3,frameon=False)
    fig.suptitle('Observed yield only: 2026 retained as confirmed by the user',fontsize=12,weight='bold')
    save(fig,'Fig04_yield_by_orchard_year')

    event_handles=[Line2D([0],[0],marker=m,color=c,linestyle='none',label=label,markersize=7)
                   for label,m,c in EVENT_STYLE.values()]
    fig,axes=plt.subplots(5,1,figsize=(13,10.4),layout='constrained')
    timeline=[]
    for ax,year in zip(axes,range(2022,2027)):
        for position,orchard in enumerate(ORCHARD_STYLE):
            season=master[master.season_id==f'{orchard}_{year}'].iloc[0]
            e=events[(events.orchard_id==orchard)&(events.harvest_year==year)].set_index('event_name')
            available=e.loc[list(EVENT_STYLE)].event_date.dropna()
            if season.phenology_main_eligible!=1:
                ax.axhspan(position-.35,position+.35,color='#edf0f3',zorder=0)
            if available.empty:
                ax.text(pd.Timestamp(year-1,11,1),position,'No quantitative event dates',va='center',color='#6b7781',fontsize=9)
            else:
                ax.plot([available.min(),available.max()],[position,position],color='#b9c2cb',lw=1.5,zorder=1)
            for event,(label,marker,color) in EVENT_STYLE.items():
                value=e.loc[event,'event_date']
                if pd.notna(value):
                    ax.scatter([value],[position],marker=marker,color=color,s=45,zorder=3)
                    timeline.append({'season_id':season.season_id,'event_name':event,'event_date':value,
                                     'phenology_main_eligible':season.phenology_main_eligible})
        ax.axvline(pd.Timestamp(year,1,1),color='#778695',lw=1,linestyle='--')
        ax.set(title=f'Harvest {year}',xlim=(pd.Timestamp(year-1,8,1),pd.Timestamp(year,6,1)),
               ylim=(2.55,-.55),yticks=range(3),yticklabels=[s[0] for s in ORCHARD_STYLE.values()])
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.grid(axis='x',alpha=.15)
    fig.suptitle('Observed phenology across calendar years (A column defines harvest season)',fontsize=13,weight='bold')
    fig.legend(handles=event_handles+[Patch(color='#edf0f3',label='Excluded from main analysis')],
               loc='outside lower center',ncol=5,frameon=False,fontsize=9)
    write_csv(root/'results/descriptive/phenology_timeline.csv',timeline)
    save(fig,'Fig05_phenology_timeline')

    if predictions is not None and not predictions.empty:
        fig,axes=plt.subplots(2,2,figsize=(10.6,9),layout='constrained')
        for ax,model in zip(axes.flat,['P1-B0','P1-B1','P2-B0','P3-B0']):
            group=predictions[predictions.model_id==model]
            low=min(group.observed_season_day.min(),group.predicted_season_day.min())-4
            high=max(group.observed_season_day.max(),group.predicted_season_day.max())+4
            ax.plot([low,high],[low,high],color='#8d98a3',linestyle='--',lw=1,zorder=0)
            for orchard,(label,marker,color) in ORCHARD_STYLE.items():
                g=group[group.orchard_id==orchard]
                ax.scatter(g.observed_season_day,g.predicted_season_day,marker=marker,color=color,s=60,alpha=.8,label=label)
            mae=group.error_days.abs().mean()
            ax.set(xlim=(low,high),ylim=(low,high),aspect='equal',
                   xlabel='Observed date: days from harvest Jan 01',ylabel='LOYO predicted date: same day scale',
                   title=f'{model} | n={len(group)} | MAE={mae:.2f} days')
            ax.grid(alpha=.15)
        handles,labels=axes[0,0].get_legend_handles_labels()
        fig.legend(handles,labels,loc='outside lower center',ncol=3,frameon=False)
        fig.suptitle('Historical baselines only - leave an entire harvest year out\nNot weather-driven models or prospective operational forecasts',fontsize=12,weight='bold')
        save(fig,'Fig06_baseline_cv_predictions')

    fig,axes=plt.subplots(2,2,figsize=(13.4,7.4),sharex=True,layout='constrained')
    grid=pd.date_range('2021-08-01','2022-06-01')
    overlay=[]
    for column,orchard in enumerate(['bannei','luhong']):
        station=cfg['orchards'][orchard]['station_id']
        daily=weather[weather.station_id==station].set_index('date').reindex(grid)
        ev=events[(events.orchard_id==orchard)&(events.harvest_year==2022)].set_index('event_name')
        for row,(variable,label,color) in enumerate([('tmean_c','Mean temperature (C)','#227d77'),('precip_mm','Rainfall (mm/day)','#597aaa')]):
            ax=axes[row,column]
            values=daily[variable]
            if row==0:
                ax.plot(grid,values,color=color,lw=1.1)
            else:
                ax.bar(grid,values,color=color,width=1,alpha=.85)
            missing_mask=values.isna().to_numpy()
            edges=np.diff(np.r_[False,missing_mask,False].astype(int))
            for start,end in zip(np.flatnonzero(edges==1),np.flatnonzero(edges==-1)):
                ax.axvspan(grid[start],grid[end-1]+pd.Timedelta(days=1),color='#edf0f3',zorder=-1)
            for event,(_,_,event_color) in EVENT_STYLE.items():
                date=ev.loc[event,'event_date']
                if pd.notna(date): ax.axvline(date,color=event_color,linestyle='--',lw=1)
            ax.set(ylabel=label,xlim=(grid[0],grid[-1]))
            ax.grid(axis='y',alpha=.15)
            if row==0: ax.set_title(f'{ORCHARD_STYLE[orchard][0]} / harvest 2022 / regional weather proxy')
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            for day,value in values.items():
                overlay.append({'orchard_id':orchard,'harvest_year':2022,'date':day,'variable':variable,'value':value})
    fig.suptitle('Observed weather with actual phenology boundaries: two representative seasons',fontsize=12,weight='bold')
    fig.legend(handles=event_handles+[Patch(color='#edf0f3',label='No valid daily weather')],
               loc='outside lower center',ncol=5,frameon=False,fontsize=9)
    write_csv(root/'results/descriptive/weather_overlay_2022.csv',overlay)
    save(fig,'Fig07_weather_phenology_overlay')
    (output/'FIGURE_CAPTIONS.md').write_text('''# 图注与未执行图说明

- Fig01_data_gate_counts：全部完整日期对14/13/13、主分析日期对各12、完整天气主样本各0。日期已修复，天气是当前限制。
- Fig02_phenology_input_status：15个果园—产季、180个事件栏位；147个日期按A列产季及原月日归年。定性值不当作日期。
- Fig03_weather_availability：上一年8月至当年6月的温度/降水日覆盖率；竖线分隔公历年，0覆盖不是0℃或0毫米。
- Fig04_yield_by_orchard_year：原表亩产及方案确认的2025办内0产量；2026已确认。红明损伤恢复待核实以三角形标记。
- Fig05_phenology_timeline：五个产季分别画真实公历时间轴，虚线为收获年1月1日；四个关键事件均取归一化实测日期。灰行表示非主分析资格，不表示日期有误；连线仅连接已知事件跨度，不填补缺失阶段。原始完整日期见phenology_timeline.csv。
- Fig06_baseline_cv_predictions：四种天气独立历史基线的整年LOYO预测，每模型12个主样本。坐标为相对收获年1月1日的日偏移；避免绝对年份造成虚假高相关。点可能重叠，逐样本结果见results/phenology。没有气象响应或区间性能结论。
- Fig07_weather_phenology_overlay：2022办内与鲁宏两个代表产季的区域天气及实际事件边界，灰色为无有效天气；缺测不补0、不插值、不跨缺口连接温度。其余产季完整覆盖清单见weather_missing_by_transition.csv。

七图同时提供PNG/PDF。未生成温度响应、累积量、窗口产量预测比较、灾害反事实或情景图：这些气象模型仍被天气闸门阻止，不用示意结果替代真实实验。
''',encoding='utf-8')
