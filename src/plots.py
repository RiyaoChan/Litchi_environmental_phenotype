"""Nonmodel QC graphics; never render invalid dates as a real phenology timeline."""
from __future__ import annotations

import calendar
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

from .data_ingest import EVENTS,TRANSITIONS
from .io_utils import write_csv


def create_descriptive_figures(root,events,master,weather,transitions,cfg):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,
                         'axes.spines.top':False,'axes.spines.right':False,
                         'axes.titleweight':'bold','savefig.facecolor':'white'})
    output=root/'results/figures'
    def save(fig,name):
        fig.savefig(output/(name+'.png'),dpi=170,bbox_inches='tight')
        fig.savefig(output/(name+'.pdf'),bbox_inches='tight',
                    metadata={'CreationDate':None,'ModDate':None,'Creator':'Litchi V2 audit pipeline'})
        plt.close(fig)

    fig,ax=plt.subplots(figsize=(8.6,4.8),layout='constrained')
    tasks=list(TRANSITIONS)
    raw=[int(transitions[transitions.task==t].raw_endpoint_pair_present.sum()) for t in tasks]
    validated=[int(transitions[transitions.task==t].complete_date_pair.sum()) for t in tasks]
    x=np.arange(3)
    ax.bar(x-.18,raw,.34,color='#bbc7d3',label='Raw numeric endpoint pairs (not validated)')
    ax.bar(x+.18,validated,.34,color='#167d77',label='Validated complete date pairs')
    for i,(n,v) in enumerate(zip(raw,validated)):
        ax.text(i-.18,n+.25,str(n),ha='center',weight='bold')
        ax.text(i+.18,.35,str(v),ha='center',weight='bold',color='#167d77')
    ax.set(xticks=x,xticklabels=['P1: flush to panicle','P2: panicle to full bloom','P3: full bloom to maturity'],
           ylim=(0,18),ylabel='Orchard-season records',title='Date gate: raw records are not model-ready samples')
    ax.legend(frameon=False,loc='upper left')
    ax.grid(axis='y',alpha=.18)
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
           title='Phenology input status (not an event timeline)')
    plt.setp(ax.get_xticklabels(),rotation=40,ha='right')
    ax.legend(handles=[Patch(color=c,label=l) for c,l in zip(colors,['Missing','Unvalidated date / year conflict','Qualitative only','Validated date'])],
              loc='upper center',bbox_to_anchor=(.5,-.20),ncol=2,frameon=False)
    save(fig,'Fig02_phenology_input_status')

    fig,axes=plt.subplots(1,5,figsize=(15.6,4.4),sharey=True,layout='constrained')
    monthly=[]
    for ax,year in zip(axes,range(2022,2027)):
        dates=[pd.Timestamp(year-1,m,1) for m in [10,11,12]]+[pd.Timestamp(year,m,1) for m in range(1,7)]
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
        ax.set(title=f'Harvest {year}',xticks=np.arange(9),xticklabels=['Oct','Nov','Dec','Jan','Feb','Mar','Apr','May','Jun'],
               yticks=np.arange(4),yticklabels=['Haikou temperature','Haikou rainfall','Lingshui temperature','Lingshui rainfall'])
        plt.setp(ax.get_xticklabels(),rotation=90)
    fig.suptitle('Usable daily weather by month: flowering and fruit development are unobserved',weight='bold',fontsize=13)
    fig.colorbar(im,ax=axes,location='bottom',shrink=.62,label='Valid days / calendar days (0 = no usable observations)',pad=.10)
    write_csv(root/'results/descriptive/weather_monthly_coverage.csv',monthly)
    save(fig,'Fig03_weather_availability')

    fig,axes=plt.subplots(1,3,figsize=(12.8,4.8),layout='constrained')
    styles={'normal':('o','#167d77'),'disaster':('*','#c74440'),'review':('^','#cb8f2e'),'year_conflict':('s','#7965a2')}
    for ax,(orchard,g) in zip(axes,master.groupby('orchard_id',sort=True)):
        for row in g.itertuples():
            kind='year_conflict' if row.year_protocol_conflict else 'disaster' if row.typhoon_damage==1 else 'review' if row.damage_review_reason else 'normal'
            marker,color=styles[kind]
            y=row.final_yield_kg_per_mu
            ax.scatter([row.harvest_year],[y],marker=marker,s=115 if kind=='disaster' else 65,
                       edgecolor=color,facecolor='none' if kind=='year_conflict' else color,zorder=3)
            ax.annotate(f'{y:.0f}',(row.harvest_year,y),xytext=(0,8),textcoords='offset points',ha='center',fontsize=9)
        ax.set(title=orchard,xticks=range(2022,2027),xticklabels=['2022','2023','2024','2025','2026*'],
               ylim=(-90,2100),xlim=(2021.6,2026.4),xlabel='Source-labeled harvest year')
        ax.grid(axis='y',alpha=.2)
    axes[0].set_ylabel('Reported yield (kg / mu)')
    handles=[Line2D([0],[0],marker=m,color='none',markeredgecolor=c,markerfacecolor='none' if k=='year_conflict' else c,
                    label=l,markersize=8) for (k,(m,c)),l in zip(styles.items(),['Normal candidate','Bannei disaster: true zero','Damage status under review','Year conflicts with protocol'])]
    fig.legend(handles=handles,loc='outside lower center',ncol=2,frameon=False)
    fig.suptitle('Observed yield only — no fitted or counterfactual predictions\n*2026 is preserved from source A39; protocol says 2025',fontsize=12,weight='bold')
    save(fig,'Fig04_yield_by_orchard_year')
    (output/'FIGURE_CAPTIONS.md').write_text('''# 图注与缺失图说明

- Fig01_data_gate_counts：原始数值端点与经完整日期校验样本数比较。14/13/13不是通过闸门的训练样本。
- Fig02_phenology_input_status：15个果园—产季的事件数据状态；没有将错误日期画成真实时间轴。
- Fig03_weather_availability：各产季上一年10月至当年6月的温度/降水日覆盖率；缺测不画为0℃或0毫米。
- Fig04_yield_by_orchard_year：原表亩产及方案确认的2025办内0产量；2026年份冲突和其他损伤待核实以独立符号标注，不连接为已确认时间趋势。

四图同时提供PNG/PDF。未生成真实物候时间轴、气象事件叠加、LOYO散点、温度响应、窗口预测比较、灾害反事实或情景图：相关日期/模型被闸门阻止，不能用示意数据替代实验结果。
''',encoding='utf-8')
