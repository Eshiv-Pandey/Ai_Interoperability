"""Once-only read-only pin probe; preserves output and does not alter networking."""
import base64
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'docs/research/source-evidence/agentops-screen-v1'
DEST.mkdir(parents=True, exist_ok=True)
OUTPUT = DEST / 'git-pin-probe-v1.json'
if OUTPUT.exists():
    raise SystemExit('Refusing to repeat or replace the pin probe.')
command = ['git', 'ls-remote', 'https://github.com/MLOps-Courses/agentops-open-course.git', 'refs/heads/main']
start = datetime.now(UTC).isoformat()
try:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=20, check=False)
    status = 'completed'
    returncode = result.returncode
    stdout, stderr = result.stdout, result.stderr
except subprocess.TimeoutExpired as error:
    status, returncode = 'timeout', None
    stdout, stderr = error.stdout or b'', error.stderr or b''
except OSError as error:
    status, returncode = 'launch-failed', None
    stdout, stderr = b'', repr(error).encode('utf-8')
record = {
    'schema_version': 'read-only-git-pin-probe/1',
    'started_at_utc': start,
    'finished_at_utc': datetime.now(UTC).isoformat(),
    'command': command,
    'status': status,
    'returncode': returncode,
    'stdout_base64': base64.b64encode(stdout).decode('ascii'),
    'stderr_base64': base64.b64encode(stderr).decode('ascii'),
    'stdout_sha256': hashlib.sha256(stdout).hexdigest(),
    'stderr_sha256': hashlib.sha256(stderr).hexdigest(),
    'stdout_utf8': stdout.decode('utf-8', errors='replace'),
    'stderr_utf8': stderr.decode('utf-8', errors='replace'),
    'limit': 'Public remote reference metadata only; no checkout, dependencies, application or model execution.'
}
with OUTPUT.open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
print(json.dumps({'status': status, 'returncode': returncode, 'stdout': record['stdout_utf8'], 'stderr': record['stderr_utf8'], 'record': str(OUTPUT)}, indent=2))
