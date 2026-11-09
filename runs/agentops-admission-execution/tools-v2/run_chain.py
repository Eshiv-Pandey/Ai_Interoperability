"""Run frozen phases sequentially in one WSL lifetime; never retry a phase."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--workspace', type=Path, required=True)
args = parser.parse_args()
root = args.workspace.resolve()
group = root / 'runs/agentops-admission-live-v1'
stage = json.loads((group / 'stage-manifest.json').read_bytes())
if str(root) != stage['linux_workspace']:
    raise ValueError('Stage allocation differs')
python = stage['reuse_root'] + '/external/runtime-agentops-linux-v7/venv/bin/python'
driver = root / 'scripts/execute_agentops_admission_phase_v2.py'
output = group / 'phase-chain'
output.mkdir(exist_ok=False)
(output / 'run_chain.py').write_bytes(Path(__file__).read_bytes())
commands = [{'phase': phase, 'argv': [python, '-B', str(driver), '--workspace', str(root), '--phase', phase]}
            for phase in ('preflight', 'launch', 'after')]
plan = {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'commands': commands,
        'driver_sha256': hashlib.sha256(driver.read_bytes()).hexdigest(),
        'chain_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'gate': 'Launch only after frozen preflight succeeds; one launch; after-inspection follows any launch outcome'}
with (output / 'plan.json').open('x', encoding='utf-8') as f:
    json.dump(plan, f, indent=2)
results = []
for command in commands:
    phase = command['phase']
    item = {**command, 'started_at_utc': datetime.now(timezone.utc).isoformat()}
    print('Starting frozen phase ' + phase, flush=True)
    with (output / (phase + '.stdout.bin')).open('xb') as stdout, (output / (phase + '.stderr.bin')).open('xb') as stderr:
        child = subprocess.Popen(command['argv'], cwd=root, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr)
        item['pid'] = child.pid
        item['returncode'] = child.wait()
    item['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
    results.append(item)
    print(phase + ' returned ' + str(item['returncode']), flush=True)
    if phase == 'preflight' and item['returncode'] != 0:
        break
report = {'status': 'phases_recorded', 'commands': results,
          'application_success': 'Read attempt/result.json; successful phase execution alone is not application success'}
with (output / 'result.json').open('x', encoding='utf-8') as f:
    json.dump(report, f, indent=2)
print(json.dumps(report), flush=True)
raise SystemExit(0 if len(results) == 3 and all(r['returncode'] == 0 for r in results) else 1)
