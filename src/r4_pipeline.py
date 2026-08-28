"""R4 orchestration; never rewrites legacy analysis outputs."""
from __future__ import annotations
import json
from .r4_weather_loader import audit,settings


def run_r4(root,cfg,stage):
    gate,daily,hourly,master=audit(root,cfg)
    print(json.dumps(gate,ensure_ascii=False,indent=2),flush=True)
    if gate['status']!='pass': return 2
    if stage=='r4-qc': return 0
    from .phenology_models import WeatherStore,PhenologyEngine
    from .r4_descriptive import describe
    model_cfg=settings(root,cfg,'phenology')
    weather=WeatherStore(daily,hourly,model_cfg)
    describe(root,cfg,master,weather)
    if stage=='r4-describe': return 0
    from .phenology_cv import run_task
    engine=PhenologyEngine(weather,model_cfg)
    for task in ['P1','P2','P3']:
        run_task(root,cfg,master,engine,task)
        if stage=='r4-'+task.lower() and task!='P3': return 0
    from .r4_sensitivity import white_tip,regional_daily,combined_report
    white_tip(root,cfg,master,engine)
    regional_daily(root,cfg,master,engine)
    combined_report(root,cfg)
    if stage=='r4-p3': return 0
    from .r4_stage_features import run_windows
    builder,features,window_gate=run_windows(root,cfg,master,engine)
    if stage=='r4-windows': return 0 if window_gate['status']=='pass' else 2
    if stage=='r4-all': return 2
    raise NotImplementedError('Later phases pending implementation after sequential phenology validation')
