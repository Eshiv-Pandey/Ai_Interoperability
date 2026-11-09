"""Export a completed fresh allocation while retaining Windows invocation bytes."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--stage', type=Path, required=True)
args = parser.parse_args()
stage = args.stage.resolve()
plan = json.loads((stage / 'stage-plan.json').read_bytes())
destination = stage / 'export'
if destination.exists():
    raise FileExistsError('Do not overwrite an export')
mounted = str(destination).replace('\\', '/')
mounted = '/mnt/' + mounted[0].lower() + mounted[2:]
argv = ['wsl.exe', '-d', 'Ubuntu', '--', plan['reuse_root'] + '/external/runtime-agentops-linux-v7/venv/bin/python',
        '-B', plan['linux_workspace'] + '/scripts/export_agentops_admission_v1.py',
        '--workspace', plan['linux_workspace'], '--output', mounted]
output = stage / 'wsl-export'
output.mkdir(exist_ok=False)
record = {'argv': argv, 'started_at_utc': datetime.now(timezone.utc).isoformat()}
with (output / 'stdout.bin').open('xb') as stdout, (output / 'stderr.bin').open('xb') as stderr:
    child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr)
    record['pid'] = child.pid
    record['returncode'] = child.wait()
record['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
with (output / 'result.json').open('x', encoding='utf-8') as stream:
    json.dump(record, stream, indent=2)
print(json.dumps(record))
sys.exit(child.returncode)
