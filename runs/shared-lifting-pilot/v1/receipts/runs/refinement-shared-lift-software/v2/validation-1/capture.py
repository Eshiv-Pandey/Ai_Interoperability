"""Once-only focused test receipt, running the captured source tree itself."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time


ALLOCATION = Path(__file__).resolve().parent
ROOT = ALLOCATION.parents[3]
SOURCES = (
    'src/interoperability/__init__.py',
    'src/interoperability/manifest.py',
    'src/interoperability/oracle.py',
    'src/interoperability/refinement.py',
    'src/interoperability/refinement_oracle.py',
    'src/interoperability/refinement_shared_lift_v2.py',
    'tests/test_refinement.py',
    'tests/test_refinement_shared_lift_v2.py',
)
PRESERVED = {
    'src/interoperability/refinement.py': '11175edcb99dbec231390ae767ba97dce2e919810844ed544a1ddd109f4b5b3b',
    'src/interoperability/refinement_oracle.py': 'b17feac87ed2972cd1a2c34557b653bdf231345e75a9ab8a919c0b4f1520477e',
    'src/interoperability/direct_goal_pruned_v2.py': '1fba2d0bd747f965056279bbda40b9c28f50f1200b7e9a6869f343ab6f64de51',
    'src/interoperability/direct_comparison_v2.py': '610c082233dcf44b58bb0b0bf68bfc4ca7fec307e380be21699ec3db39e60eb9',
    'tests/test_refinement.py': '114762ad6de4b9336f2c996fbf87e7366942485fb08e09e7b95c97790a0b0f08',
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def record(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': digest(raw)}


def write_json(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')


def main():
    if set(ALLOCATION.iterdir()) != {Path(__file__).resolve()}:
        raise RuntimeError('Allocation already consumed or contains unexpected files; use a new allocation')
    preserved_before = {name: record(ROOT / name) for name in PRESERVED}
    if any(preserved_before[name]['sha256'] != expected for name, expected in PRESERVED.items()):
        raise RuntimeError('Preserved dependency changed before capture')
    captured = ALLOCATION / 'source'
    captured.mkdir()
    source_records = {}
    for name in SOURCES:
        raw = (ROOT / name).read_bytes()
        destination = captured / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as stream:
            stream.write(raw)
        source_records[name] = {'bytes': len(raw), 'sha256': digest(raw)}
    command = [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests',
               '-p', 'test_refinement_shared_lift_v2.py', '-v']
    request = {
        'schema_version': 'shared-lift-software-capture/1',
        'scope': '23 authored focused software tests; no scaling matrix or live application run',
        'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'command': command, 'cwd': str(captured),
        'environment_overrides': {'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(captured / 'src')},
        'timeout_seconds': 120, 'sources': source_records,
        'preserved_before': preserved_before, 'capture_script': record(Path(__file__)),
        'python_version': sys.version, 'platform': platform.platform(),
    }
    write_json(ALLOCATION / 'request.json', request)
    environment = os.environ.copy()
    environment.update(request['environment_overrides'])
    started = time.perf_counter_ns()
    timed_out, returncode = False, None
    with (ALLOCATION / 'stdout.log').open('xb') as stdout, (ALLOCATION / 'stderr.log').open('xb') as stderr:
        try:
            returncode = subprocess.run(command, cwd=captured, env=environment,
                                        stdout=stdout, stderr=stderr, timeout=120, check=False).returncode
        except subprocess.TimeoutExpired:
            timed_out = True
    elapsed = time.perf_counter_ns() - started
    source_after = {name: record(captured / name) for name in SOURCES}
    workspace_after = {name: record(ROOT / name) for name in SOURCES}
    preserved_after = {name: record(ROOT / name) for name in PRESERVED}
    stderr_text = (ALLOCATION / 'stderr.log').read_text(encoding='utf-8')
    summary = re.search(r'Ran (\d+) tests in ([0-9.]+)s', stderr_text)
    count = int(summary.group(1)) if summary else None
    passed = (returncode == 0 and not timed_out and count == 23
              and stderr_text.rstrip().endswith('OK')
              and source_after == source_records == workspace_after
              and preserved_after == preserved_before)
    result = {
        'schema_version': 'shared-lift-software-capture/1', 'passed': passed,
        'completed_at_utc': datetime.now(timezone.utc).isoformat(),
        'returncode': returncode, 'timed_out': timed_out, 'test_count': count,
        'test_reported_seconds': float(summary.group(2)) if summary else None,
        'process_elapsed_ns': elapsed,
        'captured_source_unchanged': source_after == source_records,
        'workspace_source_unchanged': workspace_after == source_records,
        'preserved_dependencies_unchanged': preserved_after == preserved_before,
        'sources_after': source_after, 'workspace_after': workspace_after,
        'preserved_after': preserved_after,
        'logs': {name: record(ALLOCATION / name) for name in ('stdout.log', 'stderr.log')},
        'capture_script': record(Path(__file__)),
        'limits': ['Authored finite software cases only', 'No comparative performance inference',
                   'No held-out domain or native protocol qualification'],
    }
    write_json(ALLOCATION / 'result.json', result)
    print(json.dumps({'passed': passed, 'test_count': count, 'allocation': str(ALLOCATION)}))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
