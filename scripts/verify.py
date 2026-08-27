"""Run allowed stages twice and record real pytest/reproducibility outcomes."""
from pathlib import Path
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.io_utils import sha256,write_json

root=Path(__file__).resolve().parents[1]
command=[sys.executable,'-m','src.cli','all','--config','configs/base.yaml']
first=subprocess.run(command,cwd=root,capture_output=True)
if first.returncode!=2:
    print(first.stdout.decode(errors='replace'),first.stderr.decode(errors='replace'))
    raise SystemExit('Expected explicit data-gate exit 2')
paths=sorted([p for folder in ['data/processed','results/qc','results/figures','reports']
              for p in (root/folder).glob('*') if p.is_file()])
before={p.relative_to(root).as_posix():sha256(p) for p in paths}
second=subprocess.run(command,cwd=root,capture_output=True)
after={p.relative_to(root).as_posix():sha256(p) for p in paths}
xml=root/'results/logs/pytest.xml'
tests=subprocess.run([sys.executable,'-m','pytest','-q','-ra','--junitxml='+str(xml)],cwd=root,capture_output=True)
output=tests.stdout.decode('utf-8',errors='replace')+tests.stderr.decode('utf-8',errors='replace')
(root/'results/logs/pytest_output.log').write_text(output,encoding='utf-8')
print(output)
tree=ET.parse(xml)
cases=tree.findall('.//testcase')
xfail=sum(c.find('skipped') is not None and c.find('skipped').attrib.get('type')=='pytest.xfail' for c in cases)
skip=sum(c.find('skipped') is not None for c in cases)-xfail
failed=sum(c.find('failure') is not None or c.find('error') is not None for c in cases)
verification={'pipeline_command':'python -m src.cli all --config configs/base.yaml',
              'pipeline_exit_codes':[first.returncode,second.returncode],
              'blocked_exit_is_expected':True,'pytest_exit_code':tests.returncode,
              'pytest_passed':len(cases)-xfail-skip-failed,'pytest_failed':failed,
              'pytest_skipped':skip,'pytest_expected_failed':xfail,
              'expected_failure_reason':'A39 protocol=2025 but source=2026; preserved and blocked',
              'skipped_scope':'train-only preprocessing, W3 cross-fitting, scenario no-refit: not implemented because Stop 1',
              'reproducible_outputs_identical':before==after,
              'compared_file_count':len(before),'changed_files':[p for p in before if before[p]!=after[p]]}
write_json(root/'results/logs/verification.json',verification)
print(json.dumps(verification,ensure_ascii=False,indent=2))
raise SystemExit(0 if tests.returncode==0 and before==after and second.returncode==2 else 1)
