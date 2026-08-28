"""Verify the last implemented R4 stage; optional reproducibility rerun."""
import argparse
import csv
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
expected_scientific_stop=args.stage=='r4-yield' and run.returncode==2
if run.returncode!=0 and not expected_scientific_stop:
    print(run.stdout.decode('utf-8',errors='replace'),run.stderr.decode('utf-8',errors='replace'))
    raise SystemExit(run.returncode)
(root/'results/r4/logs/pipeline_stdout.log').write_bytes(run.stdout)
(root/'results/r4/logs/pipeline_stderr.log').write_bytes(run.stderr)
def snapshot():
    paths=sorted(p for folder in ['results/r4','reports/r4'] for p in (root/folder).rglob('*')
                 if p.is_file() and ('logs' not in p.parts or p.name=='environment.json'))
    return {p.relative_to(root).as_posix():sha256(p) for p in paths}
before=snapshot()
same=None
if args.repeat:
    again=subprocess.run(command,cwd=root,capture_output=True)
    if again.returncode!=run.returncode: raise RuntimeError('Rebuild exit mismatch')
    same=before==snapshot()
    if not same:
        after=snapshot()
        print('Changed artifacts:',[p for p in sorted(set(before)|set(after)) if before.get(p)!=after.get(p)])
xml=root/'results/r4/logs/pytest.xml'
tests=subprocess.run([sys.executable,'-m','pytest','-q','-ra','--junitxml='+str(xml)],cwd=root,capture_output=True)
print(tests.stdout.decode('utf-8',errors='replace'),tests.stderr.decode('utf-8',errors='replace'))
cases=ET.parse(xml).findall('.//testcase')
skipped=sum(c.find('skipped') is not None for c in cases)
failed=sum(c.find('failure') is not None or c.find('error') is not None for c in cases)
freeze_r4(root,cfg)
visual_pass=None
if args.stage=='r4-all':
    qa_path=root/'results/r4/logs/visual_qa.json'
    if qa_path.exists():
        qa=json.loads(qa_path.read_text(encoding='utf-8'))
        with (root/'results/r4/figures/figure_manifest.csv').open(encoding='utf-8-sig',newline='') as stream:
            pages=len(list(csv.DictReader(stream)))
        visual_pass=(qa['status']=='pass' and qa['reviewed_pages']==list(range(1,pages+1))
                     and qa['page_count']==pages and sha256(root/qa['pdf_path'])==qa['pdf_sha256'])
    else: visual_pass=False
result={'stage':args.stage,'pipeline_exit_code':run.returncode,'pytest_passed':len(cases)-skipped-failed,
        'pytest_skipped':skipped,'pytest_failed':failed,'pytest_exit_code':tests.returncode,
        'reproducible':same,'compared_files':len(before),'source_hashes_verified':True,
        'visual_qa_current_pdf_matches_reviewed_hash':visual_pass}
write_json(root/'results/r4/logs/verification.json',result)
print(json.dumps(result,ensure_ascii=False,indent=2))
raise SystemExit(0 if tests.returncode==0 and same is not False and visual_pass is not False else 1)
