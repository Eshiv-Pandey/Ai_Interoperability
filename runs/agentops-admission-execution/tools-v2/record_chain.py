"""Retain the single Windows invocation of the frozen Linux phase chain."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

stage = Path('runs/agentops-admission-execution/v3').resolve()
plan = json.loads((stage / 'stage-plan.json').read_bytes())
source = Path(__file__).with_name('run_chain.py').resolve()
mounted = str(source).replace('\\', '/')
mounted = '/mnt/' + mounted[0].lower() + mounted[2:]
output = stage / 'wsl-chain'
output.mkdir(exist_ok=False)
argv = ['wsl.exe', '-d', 'Ubuntu', '--', plan['reuse_root'] + '/external/runtime-agentops-linux-v7/venv/bin/python',
        '-B', mounted, '--workspace', plan['linux_workspace']]
record = {'argv': argv, 'started_at_utc': datetime.now(timezone.utc).isoformat()}
with (output / 'stdout.bin').open('xb') as stdout, (output / 'stderr.bin').open('xb') as stderr:
    child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr)
    record['pid'] = child.pid
    record['returncode'] = child.wait()
record['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
with (output / 'result.json').open('x', encoding='utf-8') as f:
    json.dump(record, f, indent=2)
print(json.dumps(record))
raise SystemExit(child.returncode)
