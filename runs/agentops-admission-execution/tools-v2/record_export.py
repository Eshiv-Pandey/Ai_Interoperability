"""Export after the recorded phase chain ends; retain this invocation separately."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time

root = Path.cwd()
stage = root / 'runs/agentops-admission-execution/v3'
stage_plan = json.loads((stage / 'stage-plan.json').read_bytes())
output = stage / 'wsl-export'
output.mkdir(exist_ok=False)
record = {'started_at_utc': datetime.now(timezone.utc).isoformat(),
          'wait_for': 'wsl-chain/result.json', 'export_invoked': False}
deadline = time.monotonic() + 900
chain = None
while time.monotonic() < deadline:
    try:
        chain = json.loads((stage / 'wsl-chain/result.json').read_bytes())
        break
    except (FileNotFoundError, json.JSONDecodeError):
        time.sleep(0.25)
if chain is None or chain['returncode'] != 0:
    record.update(status='withheld', reason='Phase chain did not finish with successful command receipts')
else:
    def mounted(path):
        name = str(path.resolve()).replace('\\', '/')
        return '/mnt/' + name[0].lower() + name[2:]
    argv = ['wsl.exe', '-d', 'Ubuntu', '--', stage_plan['reuse_root'] + '/external/runtime-agentops-linux-v7/venv/bin/python',
            '-B', mounted(root / 'scripts/export_agentops_admission_v2.py'),
            '--workspace', stage_plan['linux_workspace'], '--output', mounted(stage / 'export')]
    record.update(argv=argv, export_invoked=True)
    with (output / 'stdout.bin').open('xb') as stdout, (output / 'stderr.bin').open('xb') as stderr:
        child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr)
        record['pid'] = child.pid
        record['returncode'] = child.wait()
    record['status'] = 'export_command_returned'
record['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
with (output / 'result.json').open('x', encoding='utf-8') as f:
    json.dump(record, f, indent=2)
print(json.dumps(record))
raise SystemExit(0 if record.get('export_invoked') and record.get('returncode') == 0 else 1)
