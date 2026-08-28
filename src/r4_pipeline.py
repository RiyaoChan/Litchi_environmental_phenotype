"""R4 orchestration; never rewrites legacy analysis outputs."""
from __future__ import annotations
import json
from .r4_weather_loader import audit


def run_r4(root,cfg,stage):
    gate,daily,hourly,master=audit(root,cfg)
    print(json.dumps(gate,ensure_ascii=False,indent=2),flush=True)
    if gate['status']!='pass': return 2
    if stage=='r4-qc': return 0
    raise NotImplementedError('Downstream V3 phases follow committed Phase 0; no fabricated completion status')
