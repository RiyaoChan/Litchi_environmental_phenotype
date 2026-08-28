"""Bounded auxiliary analyses after the registered primary comparisons."""
import pandas as pd
from .io_utils import write_csv
from .phenology_cv import cross_validate,metrics
from .phenology_models import WeatherStore,PhenologyEngine
from .r4_weather_loader import task_frame
from .reporting import markdown_table


def white_tip(root,cfg,master,engine):
    comparisons=[]; all_predictions=[]
    for task in ['P1A','P1B']:
        frame=task_frame(master,task)
        # Reuse only the generic duration baseline; no new weather-grid search.
        pred,_,_,_=cross_validate(frame,'P2',['P2-B0'],engine,'white_tip_'+task)
        pred['task']=task; pred['model_id']=task+'-B0'; all_predictions.append(pred)
        for validation,g in pred.groupby('validation'):
            comparisons.append({'task':task,'validation':validation,**metrics(g)})
    write_csv(root/cfg['outputs']/'phenology/white_tip_cv_predictions.csv',pd.concat(all_predictions,ignore_index=True))
    write_csv(root/cfg['outputs']/'phenology/white_tip_model_comparison.csv',comparisons)
    (root/cfg['reports']/'04_WHITE_TIP_EXPLORATORY_REPORT.md').write_text(f'''# 露白辅助任务：exploratory_only

{markdown_table(pd.DataFrame(comparisons))}

两段各有12个主分析完整日期对。沿用同一露白字段，但没有独立组织学花芽分化观测，不能把露白直接等同于真实诱导终点。P1主气象模型未稳定优于历史规律，所以仅运行两段历史持续天数基线，不再搜索新的温度响应，不阻塞P2/P3。
''',encoding='utf-8')


def regional_daily(root,cfg,master,engine):
    source=pd.read_csv(root/cfg['regional_sensitivity_daily'],parse_dates=['date'])
    copies=[]
    for orchard,station in [('bannei','haikou_region_proxy'),('hongming','haikou_region_proxy'),('luhong','lingshui_region_proxy')]:
        g=source[source.station_id==station].copy(); g['orchard_id']=orchard; copies.append(g)
    daily=pd.concat(copies,ignore_index=True)
    empty=pd.DataFrame(columns=['orchard_id','time','temperature_c'])
    other=PhenologyEngine(WeatherStore(daily,empty,engine.config),engine.config)
    frame=task_frame(master,'P1')
    pred,params,_,_=cross_validate(frame,'P1',['P1-B0','P1-D1','P1-D2'],other,'R3_regional_sensitivity')
    primary=pd.read_csv(root/cfg['outputs']/'phenology/P1_model_comparison.csv')
    comparisons=[]
    for (validation,model),g in pred.groupby(['validation','model_id']):
        ref=primary[(primary.validation==validation)&(primary.model_id==model)].iloc[0]
        comparisons.append({'validation':validation,'model_id':model,'n':len(g),'R3_proxy_MAE_days':metrics(g)['MAE_days'],
                            'R4_orchard_MAE_days':ref.MAE_days,'role':'auxiliary_only_R4_remains_primary'})
    write_csv(root/cfg['outputs']/'phenology/R3_vs_R4_daily_sensitivity.csv',comparisons)
    write_csv(root/cfg['outputs']/'phenology/R3_daily_cv_predictions.csv',pred)
    write_csv(root/cfg['outputs']/'phenology/R3_daily_parameters.csv',params)
    return pd.DataFrame(comparisons)


def combined_report(root,cfg):
    parts=[]
    for task in ['P2','P3']:
        comparison=pd.read_csv(root/cfg['outputs']/f'phenology/{task}_model_comparison.csv')
        diagnostic=pd.read_csv(root/cfg['outputs']/f'phenology/{task}_stability_diagnostics.csv')
        parts.append('## '+task+'\n\n'+markdown_table(comparison)+'\n\n'+markdown_table(diagnostic))
    (root/cfg['reports']/'03_P2_P3_PHENOLOGY_REPORT.md').write_text('# P2/P3：分阶段证据而非整链成功\n\n'+'\n\n'.join(parts)+
        '\n\nP2日热量模型若通过稳定性门槛，可进入对应条件情景；不将轻微汇总误差改善自动等同于稳健优越性。'
        'P3若改善依赖单一年份则保留负结果。R4日/小时数据为事后天气，不是业务天气预报。\n',encoding='utf-8')
