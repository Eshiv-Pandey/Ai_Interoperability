"""Check v11 shutdown observations without executing archived application code.

Task/effect semantics come from the unchanged v10 checker. Diagnostic coverage
is separate: a complete shutdown observation cannot repair an incomplete task
continuation, and a stack location does not establish the cause of a stall.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path

from check_agentops_bridge_v1 import check_case
from check_agentops_effect_v2 import decode_json, seed_snapshot

PHASES = ('asyncio_run_entered', 'teardown_watchdog_armed',
          'coroutine_finished', 'asyncio_run_exited')
MAX_DIAGNOSTIC_BYTES = 8 * 1024 * 1024
DELAY_SECONDS = 5.0


def require(condition, message):
    if not condition:
        raise ValueError(message)


def timestamp(value):
    require(type(value) is str, 'Expected a timestamp string')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(parsed.tzinfo is not None, 'Timestamp requires timezone')
    return parsed


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def stack(value):
    require(type(value) is list, 'Stack must be a list')
    for frame in value:
        require(type(frame) is dict and set(frame) == {'file', 'line', 'function'},
                'Stack records only source locations')
        require(type(frame['file']) is str and bool(frame['file'])
                and type(frame['function']) is str and bool(frame['function'])
                and integer(frame['line'], 1), 'Valid stack source location')


def threads(value):
    require(type(value) is list and bool(value), 'Thread snapshot must be nonempty')
    identities = []
    for row in value:
        require(type(row) is dict and set(row) == {'ident', 'daemon', 'alive', 'stack'},
                'Thread records only identity, flags and stack')
        require(integer(row['ident'], 1) and type(row['daemon']) is bool
                and type(row['alive']) is bool, 'Valid thread identity and flags')
        stack(row['stack'])
        identities.append(row['ident'])
    require(len(set(identities)) == len(identities), 'Unique thread identities')


def tasks(value):
    require(type(value) is list and bool(value), 'Task snapshot must be nonempty')
    for row in value:
        require(type(row) is dict and set(row) == {'current', 'done', 'cancelling', 'stack'},
                'Task records only flags and stack')
        require(type(row['current']) is bool and type(row['done']) is bool
                and integer(row['cancelling']), 'Valid task flags')
        stack(row['stack'])
    require(sum(row['current'] for row in value) == 1, 'Exactly one current diagnostic task')


def read_bytes(path, case_dir, files, limit=None):
    require(path.resolve().is_relative_to(case_dir.resolve()), 'Diagnostic path escaped case')
    require(not path.is_symlink(), 'No diagnostic evidence symlink')
    if limit is not None:
        require(path.stat().st_size <= limit, 'Diagnostic file exceeds frozen byte limit')
    raw = path.read_bytes()
    files.append({'path': path.relative_to(case_dir).as_posix(), 'bytes': len(raw),
                  'sha256': hashlib.sha256(raw).hexdigest()})
    return raw


def validate_diagnostics(case_dir: Path, case_check: dict):
    """Validate observations; never upgrade the unchanged semantic outcome."""
    case_dir = Path(case_dir)
    report = {'schema_version': 'agentops-shutdown-diagnostic-check/1',
              'valid': False, 'complete': False, 'classification': 'unknown_or_partial',
              'validation_errors': [], 'observation_gaps': [], 'files': [],
              'case_outcome': case_check.get('outcome'),
              'case_strict_success': case_check.get('strict_success') is True,
              'root_cause_established': False, 'scientific_gate_credit_added': 0}
    errors, gaps, files = (report[name] for name in ('validation_errors', 'observation_gaps', 'files'))
    try:
        result = decode_json(read_bytes(case_dir / 'result.json', case_dir, files))
        process = decode_json(read_bytes(case_dir / 'service-process.json', case_dir, files))
        require(result.get('schema_version') == 'agentops-bridge-case-result/1', 'Case result schema')
        if case_check.get('case_id') is not None:
            require(result.get('case_id') == case_check['case_id'], 'Case identity binding')
        report['case_id'] = result.get('case_id')
        pid = process.get('pid')
        require(integer(pid, 2), 'Owned service PID')
        begin, end = timestamp(result['started_at_utc']), timestamp(result['finished_at_utc'])
        require(begin <= end, 'Controller observation interval')
        require(type(result.get('forced_service_stop')) is bool, 'Explicit forced-stop flag')
        code = result.get('service_returncode')
        require(code is None or type(code) is int, 'Service return code')
        directory = case_dir / 'service/shutdown-diagnostics'
        require(not directory.is_symlink(), 'No diagnostic directory symlink')
        event_path, trace_path = directory / 'lifecycle.jsonl', directory / 'teardown-stacks.txt'
        if not event_path.exists():
            gaps.append('lifecycle_file_missing')
            events = []
        else:
            raw = read_bytes(event_path, case_dir, files, MAX_DIAGNOSTIC_BYTES)
            if raw and not raw.endswith(b'\n'):
                gaps.append('lifecycle_final_newline_missing')
            events = [decode_json(line) for line in raw.splitlines()]
            if not events:
                gaps.append('lifecycle_empty')
        trace = None
        if not trace_path.exists():
            gaps.append('trace_file_missing')
        else:
            trace = read_bytes(trace_path, case_dir, files, MAX_DIAGNOSTIC_BYTES).decode('utf-8')

        phase_indices, sequences, clocks, stamps = [], [], [], []
        diagnostic_errors = []
        by_phase = {}
        common = {'schema_version', 'sequence', 'pid', 'monotonic_ns', 'at_utc', 'phase', 'diagnostic_errors'}
        extra = {'asyncio_run_entered': set(), 'teardown_watchdog_armed': {'seconds'},
                 'coroutine_finished': {'tasks', 'threads'},
                 'asyncio_run_exited': {'outcome', 'threads'}}
        for event in events:
            require(type(event) is dict and event.get('schema_version') == 'agentops-shutdown-event/2',
                    'Diagnostic event schema')
            phase = event.get('phase')
            require(phase in PHASES and phase not in by_phase, 'Known unique diagnostic phase')
            require(set(event) <= common | extra[phase]
                    and common - {'diagnostic_errors'} <= set(event), 'Exact diagnostic event fields')
            require(event['pid'] == pid and type(event['pid']) is int, 'Diagnostic event owned PID binding')
            require(integer(event['sequence'], 1) and integer(event['monotonic_ns']), 'Diagnostic sequence and clock')
            stamp = timestamp(event['at_utc'])
            require(begin <= stamp <= end, 'Diagnostic event within controller interval')
            phase_indices.append(PHASES.index(phase))
            sequences.append(event['sequence'])
            clocks.append(event['monotonic_ns'])
            stamps.append(stamp)
            event_errors = event.get('diagnostic_errors', [])
            require(type(event_errors) is list, 'Explicit diagnostic errors list')
            for error in event_errors:
                require(type(error) is dict and set(error) == {'stage', 'error_type'}
                        and all(type(value) is str and value for value in error.values()),
                        'Diagnostic errors contain stage and error type only')
                diagnostic_errors.append(error)
            # Guarded collection failures may leave these fields absent. Such
            # a record is incomplete, never a complete empty task/thread set.
            missing = extra[phase] - set(event)
            if missing:
                require(bool(event_errors), 'Missing diagnostic fields require recorded collection error')
                gaps.append(phase + ':snapshot_fields_missing')
            if phase == 'teardown_watchdog_armed' and 'seconds' in event:
                require(type(event['seconds']) in (int, float) and event['seconds'] == DELAY_SECONDS,
                        'Exact prospective diagnostic delay')
            if 'threads' in event:
                threads(event['threads'])
            if 'tasks' in event:
                tasks(event['tasks'])
            if 'outcome' in event:
                require(event['outcome'] in ('returned', 'raised'), 'Explicit asyncio outcome')
            by_phase[phase] = event
        require(phase_indices == sorted(set(phase_indices)), 'Lifecycle phases are ordered')
        require(all(a < b for a, b in zip(sequences, sequences[1:])), 'Lifecycle sequence strictly increases')
        require(all(a < b for a, b in zip(clocks, clocks[1:])), 'Lifecycle monotonic clock strictly increases')
        require(stamps == sorted(stamps), 'Lifecycle UTC ordering')
        if sequences != list(range(1, len(sequences) + 1)):
            gaps.append('lifecycle_sequence_gap')
        if diagnostic_errors:
            gaps.append('diagnostic_operations_failed')
        report.update(phases=list(by_phase), diagnostic_errors=diagnostic_errors,
                      timeout_trace_observed=bool(trace and trace.startswith('Timeout (0:00:05)!')
                                                  and 'Thread ' in trace and '\n  File ' in trace))
        if trace:
            require(trace.count('Timeout (') <= 1, 'One-shot diagnostic emits at most one timeout dump')
            if not report['timeout_trace_observed'] or not trace.endswith('\n'):
                gaps.append('timeout_trace_unrecognized_or_partial')
        for phase in PHASES[:3]:
            if phase not in by_phase:
                gaps.append('phase_missing:' + phase)
        service_result = case_dir / 'service/service-result.json'
        if service_result.exists() and 'coroutine_finished' in by_phase:
            service = decode_json(read_bytes(service_result, case_dir, files))
            require(timestamp(service['finished_at_utc']) <= timestamp(by_phase['coroutine_finished']['at_utc']),
                    'Service routine result precedes coroutine-finished observation')
        if 'asyncio_run_exited' in by_phase:
            report['classification'] = ('post_asyncio_process_survival' if result['forced_service_stop'] else
                                        'asyncio_run_' + by_phase['asyncio_run_exited']['outcome'])
            if code is None:
                gaps.append('service_exit_unconfirmed')
        else:
            if (all(phase in by_phase for phase in PHASES[:3]) and result['forced_service_stop']
                    and report['timeout_trace_observed']):
                report['classification'] = 'asyncio_teardown_stall_observed'
                armed = timestamp(by_phase['teardown_watchdog_armed']['at_utc'])
                require((end - armed).total_seconds() >= DELAY_SECONDS,
                        'Timeout traceback requires elapsed prospective delay')
            else:
                gaps.append('phase_missing:asyncio_run_exited')
                if not all(phase in by_phase for phase in PHASES[:3]):
                    report['classification'] = 'incomplete_before_supported_boundary'
                elif result['forced_service_stop']:
                    report['classification'] = 'forced_stop_without_teardown_trace'
        if report['classification'] == 'asyncio_teardown_stall_observed' and code is None:
            gaps.append('service_exit_unconfirmed')
    except FileNotFoundError as error:
        gaps.append('missing_evidence_file:' + Path(error.filename).name)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError, UnicodeError) as error:
        errors.append(type(error).__name__ + ': ' + str(error))
    report['valid'] = not errors
    report['complete'] = report['valid'] and not gaps
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', type=Path, required=True)
    parser.add_argument('--seed-db', type=Path, default=Path(__file__).resolve().parents[1] /
                        'external/agentops-c806b7f1/agents/data/incidents.db')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Preserve prior diagnostic checks')
    semantic = check_case(args.case, seed_snapshot(args.seed_db))
    diagnostic = validate_diagnostics(args.case, semantic)
    report = {'schema_version': 'agentops-bridge-diagnostic-case-check/1',
              'case': semantic, 'diagnostic': diagnostic,
              'strict_success': semantic['strict_success'], 'root_cause_established': False,
              'scientific_gate_credit_added': 0}
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if semantic['valid'] and diagnostic['valid'] else 1)
