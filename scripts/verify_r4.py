"""Verify the last implemented R4 stage; optional reproducibility rerun."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.io_utils import load_config,sha256,write_json
from src.r4_weather_loader import freeze_r4

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--stage',default='r4-qc')
parser.add_argument('--repeat',action='store_true')
args=parser.parse_args()
_,cfg=load_config(root/'configs/r4_experiment_v3.yaml')
freeze_r4(root,cfg)
command=[sys.executable,'-m','src.cli',args.stage,'--config','configs/r4_experiment_v3.yaml']
run=subprocess.run(command,cwd=root,capture_output=True)
if run.returncode not in [0,2]:
    print(run.stdout.decode('utf-8',errors='replace'),run.stderr.decode('utf-8',errors='replace'))
    raise SystemExit(run.returncode)
paths=sorted(p for folder in ['results/r4','reports/r4'] for p in (root/folder).rglob('*') if p.is_file() and 'logs' not in p.parts)
before={p.relative_to(root).as_posix():sha256(p) for p in paths}
same=None
if args.repeat:
    again=subprocess.run(command,cwd=root,capture_output=True)
    if again.returncode!=run.returncode: raise RuntimeError('Rebuild exit mismatch')
    same=before=={p.relative_to(root).as_posix():sha256(p) for p in paths}
xml=root/'results/r4/logs/pytest.xml'
tests=subprocess.run([sys.executable,'-m','pytest','-q','-ra','--junitxml='+str(xml)],cwd=root,capture_output=True)
print(tests.stdout.decode('utf-8',errors='replace'),tests.stderr.decode('utf-8',errors='replace'))
cases=ET.parse(xml).findall('.//testcase')
skipped=sum(c.find('skipped') is not None for c in cases)
failed=sum(c.find('failure') is not None or c.find('error') is not None for c in cases)
freeze_r4(root,cfg)
result={'stage':args.stage,'pipeline_exit_code':run.returncode,'pytest_passed':len(cases)-skipped-failed,
        'pytest_skipped':skipped,'pytest_failed':failed,'pytest_exit_code':tests.returncode,
        'reproducible':same,'compared_files':len(paths),'source_hashes_verified':True}
write_json(root/'results/r4/logs/verification.json',result)
print(json.dumps(result,ensure_ascii=False,indent=2))
raise SystemExit(0 if tests.returncode==0 and same is not False else 1)
