"""One-shot captured-source focused harness validation, not a scaling matrix."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[2]


def now():
    return datetime.now(timezone.utc).isoformat()


def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')


def record(path, root):
    raw = path.read_bytes()
    return {'path': path.relative_to(root).as_posix(), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    workspace = RUN / 'workspace'
    workspace.mkdir(exist_ok=False)
    paths = sorted((ROOT / 'src/interoperability').glob('*.py')) + [ROOT / 'tests' / name for name in (
        'test_benchmark_resources_v1.py', 'test_shared_lifting_comparison_v3.py', 'test_direct_goal_pruned_v2.py')]
    sources = [record(path, ROOT) for path in paths]
    for path in paths:
        target = workspace / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as handle:
            handle.write(path.read_bytes())
    commands = [[sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', pattern, '-v']
                for pattern in ('test_benchmark_resources_v1.py', 'test_shared_lifting_comparison_v3.py')]
    write(RUN / 'plan.json', {'schema_version': 'shared-comparison-focused-validation/1', 'created_at': now(),
        'sources': sources, 'runner': record(Path(__file__), RUN), 'commands': commands,
        'cwd': str(workspace), 'timeout_seconds_per_command': 600, 'matrix': False, 'live_application': False})
    executions = []
    for index, argv in enumerate(commands):
        start = time.perf_counter_ns()
        entry = {'argv': argv, 'started_at': now(), 'returncode': None, 'timed_out': False}
        out, err = RUN / f'{index}-stdout.bin', RUN / f'{index}-stderr.bin'
        with out.open('xb') as stdout, err.open('xb') as stderr:
            try:
                result = subprocess.run(argv, cwd=workspace, stdin=subprocess.DEVNULL, stdout=stdout,
                                        stderr=stderr, timeout=600)
                entry['returncode'] = result.returncode
            except subprocess.TimeoutExpired:
                entry['timed_out'] = True
        entry.update(finished_at=now(), wall_ns=time.perf_counter_ns() - start,
                     stdout=record(out, RUN), stderr=record(err, RUN))
        match = re.search(rb'Ran (\d+) tests?', err.read_bytes())
        entry['tests_reported'] = int(match.group(1)) if match else None
        executions.append(entry)
    unchanged = sources == [record(path, ROOT) for path in paths]
    captured = sources == [record(workspace / row['path'], workspace) for row in sources]
    result = {'schema_version': 'shared-comparison-focused-validation-result/1',
        'status': 'passed' if all(e['returncode'] == 0 for e in executions) and unchanged and captured else 'failed',
        'finished_at': now(), 'executions': executions, 'original_sources_unchanged': unchanged,
        'captured_sources_unchanged': captured, 'matrix_executed': False, 'live_application_executed': False,
        'claim_limit': 'Focused software tests and two-profile temporary run/replay; no scientific comparison.'}
    write(RUN / 'result.json', result)
    print(json.dumps(result))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
