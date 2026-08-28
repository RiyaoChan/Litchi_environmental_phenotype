"""Publication-oriented PNG panels and one deterministic, reviewable PDF atlas."""
from __future__ import annotations
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

ORCHARDS={'bannei':('Bannei','o','#1c8177'),'hongming':('Hongming','^','#b8802c'),'luhong':('Luhong','s','#7162a6')}
EVENTS={'autumn_flush_mature':('Flush','#23826d'),'inflorescence_emergence':('Panicle','#b38029'),
        'full_bloom':('Full bloom','#a25488'),'maturity':('Maturity','#406fa4')}


def make_figures(root,cfg,master,weather):
    base=root/cfg['outputs']; out=base/'figures'
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,
                         'axes.spines.right':False,'axes.titleweight':'bold','savefig.facecolor':'white'})
    manifest=[]
    with PdfPages(out/'R4_FIGURE_ATLAS.pdf',metadata={'Title':'R4 V3 evidence-chain figures','Creator':'R4 V3 reproducible pipeline','CreationDate':None,'ModDate':None}) as pdf:
        def save(fig,name,caption):
            fig.savefig(out/(name+'.png'),dpi=160,bbox_inches='tight')
            pdf.savefig(fig,bbox_inches='tight'); plt.close(fig)
            manifest.append({'page':len(manifest)+1,'figure':name,'caption':caption})

        grid=pd.read_csv(base/'qc/grid_identity.csv')
        fig,(ax,flow)=plt.subplots(1,2,figsize=(12,6),gridspec_kw={'width_ratios':[1.1,1]},layout='constrained')
        for row in grid.itertuples():
            label,marker,color=ORCHARDS[row.orchard_id]
            ax.plot([row.requested_longitude,row.grid_longitude],[row.requested_latitude,row.grid_latitude],color=color,lw=1)
            ax.scatter(row.requested_longitude,row.requested_latitude,color=color,marker=marker,s=80,zorder=3)
            ax.scatter(row.grid_longitude,row.grid_latitude,color=color,marker='x',s=75,zorder=3)
            offset=(-80,-30) if row.orchard_id=='hongming' else (10,-12)
            ax.annotate(f'{label}\n{row.grid_distance_km:.1f} km to grid center',(row.requested_longitude,row.requested_latitude),xytext=offset,textcoords='offset points',fontsize=9)
        ax.set(xlabel='Longitude (E)',ylabel='Latitude (N)',xlim=(109.7,110.95),ylim=(18.2,20.2),title='Requested orchard points and returned ERA5 grids')
        ax.grid(alpha=.18)
        ax.legend(handles=[Line2D([0],[0],marker='o',color='none',markerfacecolor='#394954',label='Requested orchard'),
                           Line2D([0],[0],marker='x',color='#394954',linestyle='none',label='Returned grid center')],loc='lower right',frameon=False)
        flow.axis('off')
        labels=[('R4 daily + hourly reanalysis\n3 grids; 5 harvest years','#e5f1ef'),
                ('P1: flush to panicle\nWeather does not beat history','#faedcf'),
                ('P2: panicle to full bloom\nGDD has preliminary held-out support','#dceee8'),
                ('P3: full bloom to maturity\nSmall, fragile GDD improvement','#faedcf'),
                ('Four weather-window definitions\nNormal yield: exploratory evidence','#e6ebf4')]
        for i,(text,color) in enumerate(labels):
            y=.92-i*.195
            flow.text(.5,y,text,ha='center',va='center',fontsize=11,bbox={'boxstyle':'round,pad=.6','facecolor':color,'edgecolor':'#9eaab4'},transform=flow.transAxes)
            if i<4: flow.annotate('',xy=(.5,y-.115),xytext=(.5,y-.07),xycoords='axes fraction',arrowprops={'arrowstyle':'->','color':'#6b7780'})
        fig.suptitle('R4 evidence chain: precise requests do not mean on-site observations',fontsize=13,weight='bold')
        save(fig,'Figure_1_orchards_framework','三园精确请求点和实际ERA5返回网格，及当前证据链；坐标图不代表现场测绘。')

        for orchard,(label,_,_) in ORCHARDS.items():
            fig,axes=plt.subplots(5,1,figsize=(12.5,10),layout='constrained')
            for ax,year in zip(axes,range(2022,2027)):
                season=master[(master.orchard_id==orchard)&(master.harvest_year==year)].iloc[0]
                start=pd.Timestamp(year-1,8,1); end=pd.Timestamp(year,6,30)
                daily=weather.daily[orchard].loc[start:end]
                rain=ax.twinx(); rain.spines['right'].set_visible(True)
                rain.bar(daily.index,daily.precip_mm,width=1,color='#7896bc',alpha=.3)
                rain.set_ylim(0,max(150,float(daily.precip_mm.max())*1.15)); rain.set_ylabel('Rain (mm)',fontsize=8)
                ax.plot(daily.index,daily.tmean_c,color='#156c62',lw=1.05,zorder=3)
                ax.plot(daily.index,daily.tmin_c,color='#567780',lw=.75,alpha=.8,linestyle=':')
                for event,(_,color) in EVENTS.items():
                    if pd.notna(season[event]): ax.axvline(season[event],color=color,linestyle='--',lw=1)
                title=f'Harvest {year}'
                if season.phenology_main_eligible!=1: title+=' | excluded from primary calibration'
                ax.set(title=title,xlim=(start,end),ylim=(5,37),ylabel='Temp (C)')
                ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2)); ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                ax.grid(axis='y',alpha=.12)
            handles=[Line2D([0],[0],color='#156c62',label='Daily mean T'),Line2D([0],[0],color='#567780',linestyle=':',label='Daily minimum T'),Patch(color='#7896bc',alpha=.4,label='Rainfall')]
            handles += [Line2D([0],[0],color=c,linestyle='--',label=e) for e,c in EVENTS.values()]
            fig.legend(handles=handles,loc='outside lower center',ncol=7,frameon=False,fontsize=8)
            fig.suptitle(f'{label}: observed phenology with complete R4 weather, 2022-2026',fontsize=12,weight='bold')
            save(fig,'Fig_R4_01_phenology_weather_timeline_'+orchard,f'{label}五产季真实物候与日均/最低温、降水；无物候日期不补齐，不改变损伤资格。')

        p1=pd.read_csv(base/'phenology/P1_model_comparison.csv'); p1=p1[p1.validation=='LOYO']
        fig,ax=plt.subplots(figsize=(10.2,5.3),layout='constrained')
        colors=['#9ba9b7' if '-B' in m else '#318a81' if '-D' in m else '#7061a4' for m in p1.model_id]
        ax.barh(p1.model_id,p1.MAE_days,color=colors,height=.62)
        baseline=float(p1[p1.model_id=='P1-B0'].MAE_days.iloc[0]); ax.axvline(baseline,color='#4f5862',linestyle='--',lw=1)
        for index,row in enumerate(p1.itertuples()):
            suffix=f' | {int(row.n_predictions)}/{int(row.n_samples)} predicted' if row.n_predictions<row.n_samples else ''
            ax.text(row.MAE_days+.8,index,f'{row.MAE_days:.2f}'+suffix,va='center',fontsize=9)
        ax.invert_yaxis(); ax.set(xlim=(0,float(p1.MAE_days.max())*1.45),xlabel='LOYO mean absolute error score (days)',title='P1: daily and hourly weather do not outperform the duration baseline')
        ax.grid(axis='x',alpha=.12)
        fig.text(.01,-.03,'All models evaluated on the same 12 seasons. D2: two non-crossings receive the prespecified 365-day penalty.',fontsize=9)
        save(fig,'Figure_3_P1_model_MAE','同一12样本P1模型比较。D2有2个未达阈值，计预注册365天惩罚；不能把72.42天当10个成功预测的普通MAE。')

        pred=pd.read_csv(base/'phenology/P1_cv_predictions.csv',parse_dates=['start_date','end_date','predicted_event_date'])
        pred=pred[pred.validation=='LOYO']
        fig,axes=plt.subplots(1,3,figsize=(13.5,4.6),layout='constrained')
        for ax,model in zip(axes,['P1-B0','P1-D1','P1-H3']):
            g=pred[pred.model_id==model].copy()
            obs=np.array([(r.end_date-pd.Timestamp(r.harvest_year,1,1)).days for r in g.itertuples()])
            fitted=np.array([(r.predicted_event_date-pd.Timestamp(r.harvest_year,1,1)).days for r in g.itertuples()])
            lo=min(obs.min(),fitted.min())-6; hi=max(obs.max(),fitted.max())+6
            ax.plot([lo,hi],[lo,hi],color='#8995a2',ls='--',lw=1)
            for k,(r,x,y) in enumerate(zip(g.itertuples(),obs,fitted)):
                label,marker,color=ORCHARDS[r.orchard_id]
                ax.scatter(x,y,color=color,marker=marker,s=42,zorder=3)
                offset=[(5,5),(5,-12),(-22,7),(-22,-12)][k%4]
                if model=='P1-H3' and r.season_id=='luhong_2026': offset=(5,8)
                if model=='P1-H3' and r.season_id=='luhong_2022': offset=(5,4)
                ax.annotate(label[0]+str(r.harvest_year)[-2:],(x,y),xytext=offset,textcoords='offset points',fontsize=7,color=color)
            ax.set(xlim=(lo,hi),ylim=(lo,hi),aspect='equal',xlabel='Observed date offset from Jan 01',ylabel='Predicted date offset from Jan 01',title=model)
            ax.grid(alpha=.13)
        fig.suptitle('P1 held-out dates: B= Bannei, H= Hongming, L= Luhong; suffix = harvest year',fontsize=11,weight='bold')
        save(fig,'Fig_R4_02_P1_observed_vs_predicted','P1历史基线、最小误差日模型D1及小时模型H3逐样本留出日期；标注果园/年份，不将候选最小值称独立验证的赢家。')

        fits=json.loads((base/'phenology/P1_fitted_models.json').read_text(encoding='utf-8'))
        fit=fits['main_P1_P1-D1_LOYO_2024']
        fig,axes=plt.subplots(1,3,figsize=(13.5,4.4),layout='constrained')
        for ax,(orchard,(label,_,color)) in zip(axes,ORCHARDS.items()):
            row=master[(master.orchard_id==orchard)&master.harvest_year.eq(2024)].iloc[0]
            start=row.autumn_flush_mature; end=pd.Timestamp('2024-03-31'); dates=pd.date_range(start,end)
            inc=weather.increments(orchard,fit['spec']); vals=np.cumsum(inc[weather.index(start):weather.index(end)+1])
            ax.plot(dates,vals,color=color)
            ax.axhline(fit['parameters'][orchard],color='#505c68',linestyle=':',label='Training-only threshold')
            pr=pred[(pred.season_id==row.season_id)&(pred.model_id=='P1-D1')].iloc[0]
            ax.axvline(row.inflorescence_emergence,color='#ab548b',linestyle='--',label='Observed panicle')
            ax.axvline(pr.predicted_event_date,color='#347986',linestyle='-.',label='Held-out predicted panicle')
            ax.set(title=label+' | held out 2024',ylabel='Cumulative qualifying low-temperature days')
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2)); ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.grid(alpha=.13)
        handles,labels=axes[-1].get_legend_handles_labels(); fig.legend(handles,labels,loc='outside lower center',ncol=3,frameon=False)
        fig.suptitle('Illustrative 2024 holdout: P1-D1 accumulations, not a validated physiological mechanism',fontsize=11,weight='bold')
        save(fig,'Fig_R4_03_P1_cumulative_response_examples','固定展示2024留出折D1累计曲线，阈值来自其他年份；这是累积模型行为，不是荔枝真实生理阈值证明。')

        fig,axes=plt.subplots(2,2,figsize=(11.4,8),layout='constrained')
        for col,task in enumerate(['P2','P3']):
            table=pd.read_csv(base/f'phenology/{task}_model_comparison.csv'); table=table[table.validation=='LOYO']
            axes[0,col].bar(table.model_id,table.MAE_days,color=['#a0adb9','#278679','#9b83b7'])
            for i,value in enumerate(table.MAE_days): axes[0,col].text(i,value+.12,f'{value:.2f}',ha='center')
            axes[0,col].set(ylim=(0,9),ylabel='LOYO MAE (days)',title=task+(' | GDD preliminary support' if task=='P2' else ' | GDD improvement is fragile'))
            rows=pd.read_csv(base/f'phenology/{task}_cv_predictions.csv',parse_dates=['end_date','predicted_event_date'])
            rows=rows[(rows.validation=='LOYO')&(rows.model_id==task+'-M1')]
            obs=np.array([(r.end_date-pd.Timestamp(r.harvest_year,1,1)).days for r in rows.itertuples()])
            fitted=np.array([(r.predicted_event_date-pd.Timestamp(r.harvest_year,1,1)).days for r in rows.itertuples()])
            lo=min(obs.min(),fitted.min())-5; hi=max(obs.max(),fitted.max())+5
            ax=axes[1,col]; ax.plot([lo,hi],[lo,hi],color='#8a969f',ls='--')
            for i,r in enumerate(rows.itertuples()):
                label,marker,color=ORCHARDS[r.orchard_id]; ax.scatter(obs[i],fitted[i],color=color,marker=marker,s=50)
            ax.set(xlim=(lo,hi),ylim=(lo,hi),aspect='equal',xlabel='Observed date offset',ylabel='Predicted date offset',title=task+'-M1 | days from harvest Jan 01')
            ax.grid(alpha=.14)
        fig.suptitle('Later phenology: stage-specific evidence, not proof of an end-to-end forecast',fontsize=12,weight='bold')
        orchard_handles=[Line2D([0],[0],marker=m,color=c,linestyle='none',label=label) for label,m,c in ORCHARDS.values()]
        fig.legend(handles=orchard_handles,loc='outside lower center',ncol=3,frameon=False)
        save(fig,'Figure_5_P2_P3_thermal_time','P2/P3低参数GDD与历史基线及受限扩展；P2按方案稳定性检查通过，但5年自助区间仍跨0，不宣称显著性。P3改善脆弱。')

        window_files=['W1_calendar_features','W1_median_features','W2_observed_features','W3_predicted_features']
        example=[]
        for file in window_files:
            rows=pd.read_csv(base/'windows'/(file+'.csv'))
            example.append(rows[(rows.role=='evaluation')&(rows.season_id=='bannei_2024')].iloc[0])
        examples=pd.DataFrame(example)
        fig,(ax,heat)=plt.subplots(1,2,figsize=(13.5,5),gridspec_kw={'width_ratios':[1.4,1]},layout='constrained')
        stages=['induction','flowering','fruit_development']; colors=['#248574','#ae638e','#4c7ead']
        for i,(_,r) in enumerate(examples.iterrows()):
            for j,(stage,color) in enumerate(zip(stages,colors)):
                start=pd.Timestamp(r[stage+'_start']); end=pd.Timestamp(r[stage+'_end'])
                ax.plot([start,end],[i+(j-1)*.15]*2,color=color,lw=5,solid_capstyle='butt')
        ax.set(yticks=range(4),yticklabels=examples.window_type.tolist(),ylim=(3.55,-.55),title='Bannei 2024: held-out window boundaries')
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2)); ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.grid(axis='x',alpha=.14)
        columns=['induction_temperature_metric','induction_water_balance_mm','flowering_precipitation_hours','fruit_gdd','fruit_heat_days','flowering_radiation_mean']
        vals=examples[columns].to_numpy(dtype=float); sd=vals.std(axis=0); sd[sd==0]=1
        z=(vals-vals.mean(axis=0))/sd
        im=heat.imshow(z,cmap='RdBu_r',vmin=-2,vmax=2,aspect='auto')
        heat.set(yticks=range(4),yticklabels=examples.window_type.tolist(),xticks=range(6),xticklabels=['Induction\nmetric','Induction\nP-ET0','Flowering\nwet hours','Fruit\nGDD','Fruit\nheat days','Flowering\nradiation'],title='Feature differences in the same example')
        plt.setp(heat.get_xticklabels(),rotation=40,ha='right',fontsize=8)
        fig.colorbar(im,ax=heat,shrink=.7,label='Display-only column standardization')
        fig.legend(handles=[Line2D([0],[0],color=c,lw=5,label=s.replace('_',' ')) for s,c in zip(stages,colors)],loc='outside lower center',ncol=3,frameon=False)
        save(fig,'Figure_6_window_alignment','办内2024四窗口及特征差异。右图标准化仅供显示，绝不用于模型拟合；W2为真实未来物候上限，W3为训练折链式预测。')

        y=pd.read_csv(base/'yield/model_comparison.csv'); y=y[(y.cohort=='MAIN')&(y.validation=='LOYO')]
        fig,ax=plt.subplots(figsize=(10.6,5.5),layout='constrained')
        maximum=float(y.loc[y.status=='complete','MAE_kg_mu'].max())
        for i,row in enumerate(y.itertuples()):
            if row.status=='complete':
                color='#9daab7' if row.model_id=='Y-B0' else '#c2935f' if row.model_id=='Y-W2O' else '#2b887d'
                ax.barh(i,row.MAE_kg_mu,color=color,height=.6)
                ax.text(row.MAE_kg_mu+8,i,f'{row.MAE_kg_mu:.1f} | n={row.n_predictions}',va='center')
            else:
                ax.text(8,i,f'NOT COMPARABLE: {row.n_predictions}/12 predictions; inner partitions incomplete',va='center',color='#a14f48')
        ax.set(yticks=range(len(y)),yticklabels=y.model_id.tolist(),xlim=(0,maximum*1.3),ylim=(-.6,len(y)-.4),xlabel='Held-out MAE on all 12 main seasons (kg / mu)',title='Normal yield: no demonstrated advantage of observed dynamic windows')
        ax.invert_yaxis(); ax.grid(axis='x',alpha=.12)
        save(fig,'Figure_7_yield_comparison','只对共同完整12样本画可比较的产量MAE。W3的8样本子集不画成主性能柱，不用子集分数宣称优于基线。')

        scenarios=pd.read_csv(base/'scenarios/phenology_scenarios.csv',parse_dates=['reference_predicted_date','scenario_predicted_date'])
        if not scenarios.empty:
            s=scenarios[scenarios.task=='P2']
            if not s.empty:
                fig,ax=plt.subplots(figsize=(9.4,5),layout='constrained')
                for delta,g in s.groupby('temperature_shift_c'):
                    ax.boxplot([g.date_shift_days.dropna()],positions=[delta],widths=.25,showfliers=False,patch_artist=True,
                        boxprops={'facecolor':'#e4f0ec'},medianprops={'color':'#1d796f'},manage_ticks=False)
                    for i,r in enumerate(g.itertuples()):
                        _,marker,color=ORCHARDS[r.orchard_id]
                        ax.scatter(delta+(i%5-2)*.022,r.date_shift_days,marker=marker,color=color,s=32,zorder=3,alpha=.8)
                ax.axhline(0,color='#8d99a3',lw=1)
                ax.set(xticks=sorted(s.temperature_shift_c.unique()),xlabel='Air-temperature perturbation (C)',ylabel='Full-bloom date shift (days; negative = earlier)',
                       title='P2-only fixed-model temperature sensitivity\nConditional on the observed panicle date, not a complete-chain forecast')
                ax.grid(axis='y',alpha=.15)
                fig.legend(handles=orchard_handles,loc='outside lower center',ncol=3,frameon=False)
                save(fig,'Supplement_P2_temperature_sensitivity','仅P2获准的固定LOYO模型温度敏感性；负数是相对未扰动预测提前。点的微小横向错位仅用于显示，不是温度不确定性。P1暖冬×秋梢二维情景未获准。')
    write=pd.DataFrame(manifest)
    write.to_csv(out/'figure_manifest.csv',index=False,encoding='utf-8-sig',lineterminator='\n')
    (out/'FIGURE_CAPTIONS_ZH.md').write_text('# R4图注\n\n'+'\n\n'.join(f"第{r['page']}页 / {r['figure']}：{r['caption']}" for r in manifest)+
        '\n\n各图PNG与单一PDF图集对应。未生成未经验证的P1暖冬×秋梢推迟二维响应或台风因果损失图。\n',encoding='utf-8')
    return manifest
