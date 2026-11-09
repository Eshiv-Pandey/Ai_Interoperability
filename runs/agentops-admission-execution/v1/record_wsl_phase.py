"""Retain Windows-to-WSL invocation bytes separately from Linux phase evidence."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--stage', type=Path, required=True)
parser.add_argument('--phase', required=True)
args = parser.parse_args()
stage = args.stage.resolve()
plan = json.loads((stage / 'stage-plan.json').read_bytes())
driver = str(Path(__file__).with_name('execute_phase.py').resolve()).replace('\\', '/')
driver = '/mnt/' + driver[0].lower() + driver[2:]
argv = ['wsl.exe', '-d', 'Ubuntu', '--', plan['reuse_root'] + '/external/runtime-agentops-linux-v7/venv/bin/python',
        '-B', driver, '--workspace', plan['linux_workspace'], '--phase', args.phase]
output = stage / ('wsl-' + args.phase)
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
