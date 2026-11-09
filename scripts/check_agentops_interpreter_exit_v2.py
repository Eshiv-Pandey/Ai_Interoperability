"""Read-only interpreter-exit evidence validation, independent of the observer.

``valid`` means the retained diagnostic and process records agree. ``complete``
also requires clean process exit and every expected exit boundary. A coherent
forced shutdown can be valid but never complete. Neither a traceback nor these
markers establish a subsystem root cause or replace the process receipt.
Early setup failures lacking these required files are reported invalid and
incomplete; this checker does not synthesize a lifecycle for an unstarted app.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath

from check_agentops_startup_v1 import diagnostic_launch


PHASES = ('interpreter_exit_observer_installed', 'entrypoint_boundary',
          'interpreter_exit_watchdog_armed', 'interpreter_exit_watchdog_unavailable',
          'atexit_early_boundary', 'atexit_late_boundary')
COMPLETE_PHASES = [PHASES[i] for i in (0, 1, 2, 4, 5)]


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _epoch_ns(value):
    stamp = datetime.fromisoformat(value)
    _require(stamp.tzinfo is not None, 'Lifecycle window needs timezone-aware timestamps')
    delta = stamp.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return ((delta.days * 86400 + delta.seconds) * 1_000_000_000
            + delta.microseconds * 1000)


def validate_interpreter_exit(case_dir: Path) -> dict:
    """Validate retained files only; do not write, signal, import or execute app code."""
    case_dir = Path(case_dir)
    report = {'schema_version': 'agentops-interpreter-exit-check/2',
              'valid': False, 'complete': False, 'validation_errors': [],
              'completion_blockers': [], 'files': [], 'phases': [],
              'root_cause_established': False, 'scientific_gate_credit_added': 0,
              'claim_limit': 'Passive Python exit locations and process-bound lifecycle only; '
                             'no specific subsystem cause or application success established.'}

    def raw(name, limit=2_000_000):
        path = case_dir / name
        _require(path.stat().st_size <= limit, 'Diagnostic file exceeds bound: ' + name)
        data = path.read_bytes()
        report['files'].append({'path': name, 'bytes': len(data),
                                'sha256': hashlib.sha256(data).hexdigest()})
        return data

    def load(name):
        return json.loads(raw(name))

    def block(condition, message):
        if condition:
            report['completion_blockers'].append(message)

    try:
        process = load('service-process.json')
        result = load('result.json')
        service = load('service/service-result.json')
        stop = load('service/stop-requested.json')
        events = [json.loads(line) for line in raw(
            'service/interpreter-exit-diagnostics/lifecycle.jsonl').splitlines()]
        trace = raw('service/interpreter-exit-diagnostics/interpreter-exit-stacks.txt', 16_000_000)
        old = [json.loads(line) for line in raw('service/shutdown-diagnostics/lifecycle.jsonl').splitlines()]
        pid, argv = process['pid'], process['argv']
        _require(type(pid) is int and pid > 1, 'Invalid service PID')
        _require(type(argv) is list and all(type(x) is str for x in argv), 'Invalid service argv')
        launch = diagnostic_launch(case_dir, process)
        delay = launch['exit_seconds']
        report['launch'] = launch
        started, finished = _epoch_ns(result['started_at_utc']), _epoch_ns(result['finished_at_utc'])
        _require(started < finished and started <= _epoch_ns(process['started_at_utc']) <= finished,
                 'Service process receipt lies outside case window')
        # The process receipt is written after Popen, so its timestamp can be
        # later than an unusually fast first child event. The case window and
        # PID bind those events without assuming that scheduling cannot race.
        _require(started <= _epoch_ns(stop['requested_at_utc']) <= finished,
                 'Stop request lies outside case window')
        _require(started <= _epoch_ns(service['finished_at_utc']) <= finished,
                 'Service result lies outside case window')
        _require(events and events[0]['phase'] == PHASES[0], 'Missing observer installation marker')
        previous_tick, previous_rank, previous_errors = -1, -1, []
        armed = False
        by_phase = {}
        for sequence, event in enumerate(events, 1):
            phase = event['phase']
            _require(phase in PHASES and phase not in by_phase, 'Unknown or duplicate lifecycle phase')
            rank = PHASES.index(phase)
            _require(rank > previous_rank, 'Lifecycle phases are out of order')
            _require(event['schema_version'] == 'agentops-interpreter-exit-event/1'
                     and type(event['sequence']) is int and event['sequence'] == sequence
                     and type(event['pid']) is int and event['pid'] == pid,
                     'Lifecycle schema, sequence or PID mismatch')
            tick, epoch = event['monotonic_ns'], event['at_epoch_ns']
            _require(type(tick) is int and tick > previous_tick
                     and type(epoch) is int and started <= epoch <= finished,
                     'Lifecycle timestamps are unordered or outside case window')
            errors = event['diagnostic_errors']
            _require(type(errors) is list and errors[:len(previous_errors)] == previous_errors
                     and all(type(e) is dict and set(e) == {'stage', 'error_type'}
                             and all(type(v) is str for v in e.values()) for e in errors),
                     'Malformed or noncumulative diagnostic errors')
            if phase == 'entrypoint_boundary':
                _require(event['boundary'] in ('asyncio_observer', 'service_imports')
                         and event['outcome'] in ('returned', 'raised'), 'Invalid entrypoint boundary')
            if phase == 'interpreter_exit_watchdog_armed':
                _require('entrypoint_boundary' in by_phase and type(event['seconds']) in (int, float)
                         and event['seconds'] == delay
                         and event['repeat'] is True and event['exit'] is False,
                         'Watchdog configuration differs from passive launch contract')
                armed = True
            if phase == 'interpreter_exit_watchdog_unavailable':
                _require(not armed and 'entrypoint_boundary' in by_phase,
                         'Watchdog cannot be both armed and unavailable')
            _require(type(event['watchdog_armed']) is bool and event['watchdog_armed'] == armed,
                     'Lifecycle watchdog state is inconsistent')
            by_phase[phase] = event
            previous_tick, previous_rank, previous_errors = tick, rank, errors
        report['phases'] = [e['phase'] for e in events]
        report['pid'] = pid
        report['diagnostic_errors'] = previous_errors
        report['timeout_trace_observed'] = b'Timeout' in trace
        report['trace_bytes'] = len(trace)
        report['trace_timestamps_available'] = False
        report['trace_interpretation'] = ('Read the captured stack locations with the lifecycle markers; '
                                          'trace blocks do not carry timestamps proving their order relative to markers.')

        old_by_phase = {}
        previous_old = -1
        for event in old:
            _require(event['schema_version'] == 'agentops-shutdown-event/2'
                     and type(event['pid']) is int and event['pid'] == pid,
                     'Asyncio lifecycle does not bind the service process')
            _require(type(event['monotonic_ns']) is int and event['monotonic_ns'] > previous_old,
                     'Asyncio lifecycle is unordered')
            _require(event['phase'] not in old_by_phase, 'Duplicate asyncio phase')
            old_by_phase[event['phase']] = event
            previous_old = event['monotonic_ns']
        entry, exit_event = old_by_phase.get('asyncio_run_entered'), old_by_phase.get('asyncio_run_exited')
        boundary = by_phase.get('entrypoint_boundary', {})
        if entry is not None:
            _require(events[0]['monotonic_ns'] < entry['monotonic_ns'],
                     'Observer was not installed before asyncio entry')
        if boundary.get('boundary') == 'asyncio_observer':
            _require(entry is not None and exit_event is not None
                     and exit_event['monotonic_ns'] < boundary['monotonic_ns']
                     and exit_event['outcome'] == boundary['outcome'],
                     'Post-asyncio handoff precedes or contradicts asyncio exit')

        child = result['service_child_cleanup']
        _require(child['schema_version'] == 'agentops-owned-child-finish/1'
                 and type(child['pid']) is int and child['pid'] == pid and child['argv'] == argv,
                 'Owned child cleanup does not bind exact service PID/argv')
        code = child['returncode']
        _require(code is None or type(code) is int, 'Invalid child return code')
        _require(result['service_returncode'] == code
                 and (result['service_returncode'] is None or type(result['service_returncode']) is int),
                 'Case return code differs from reaped child')
        _require(type(child['graceful_timeout']) is bool and type(child['reaped_before_group_check']) is bool,
                 'Invalid owned-child completion flags')
        _require(child['reaped_before_group_check'] == (code is not None),
                 'Reaping assertion contradicts child return code')
        requests = child['signal_requests']
        _require(type(requests) is list and [r['signal'] for r in requests] in
                 ([], ['SIGTERM'], ['SIGTERM', 'SIGKILL'])
                 and all(type(r['method_returned']) is bool for r in requests), 'Invalid child signal requests')
        group = child['owned_group']
        _require(result['service_group_cleanup'] == (group or {}), 'Case group cleanup differs from child receipt')
        if group is not None:
            _require(child['reaped_before_group_check']
                     and group['schema_version'] == 'agentops-owned-process-group/1'
                     and type(group['pgid']) is int and group['pgid'] == pid,
                     'Group check lacks confirmed parent reaping or correct group')
            _require(all(type(group[k]) is bool for k in ('initially_empty', 'final_empty', 'forced_cleanup')),
                     'Invalid group cleanup flags')
            _require(all(type(group[k]) is list for k in ('members', 'final_members', 'snapshots', 'signals', 'errors')),
                     'Invalid group cleanup lists')
            _require(type(group['members']) is list and type(group['final_members']) is list
                     and group['initially_empty'] == (not group['members'] and not group['errors'])
                     and group['final_empty'] == (not group['final_members'] and not group['errors']),
                     'Group emptiness contradicts its members or errors')
            snapshots = group['snapshots']
            _require(all(type(row) is dict and type(row.get('monotonic_ns')) is int
                         and row['monotonic_ns'] >= 0 and type(row.get('phase')) is str
                         and type(row.get('members')) is list and type(row.get('errors')) is list
                         and all(type(error) is str for error in row['errors']) for row in snapshots),
                     'Invalid retained group snapshot')
            ticks = [row['monotonic_ns'] for row in snapshots]
            _require(ticks == sorted(set(ticks)), 'Group snapshot clocks are unordered or duplicated')
            if snapshots:
                _require(snapshots[0]['phase'] == 'initial' and snapshots[0]['members'] == group['members']
                         and snapshots[-1]['members'] == group['final_members'],
                         'Group member summaries do not bind initial and final snapshots')
            signals = group['signals']
            _require(all(type(row) is dict and row.get('signal') in ('SIGTERM', 'SIGKILL')
                         and type(row.get('sent')) is bool and type(row.get('monotonic_ns')) is int
                         and row['monotonic_ns'] >= 0 for row in signals), 'Invalid retained group signal')
            _require(group['forced_cleanup'] == any(row['sent'] for row in signals),
                     'Forced group cleanup does not bind recorded sent signals')
            if group['initially_empty'] and group['final_empty'] and not group['forced_cleanup'] and not group['errors']:
                _require(len(snapshots) == 1 and snapshots[0]['errors'] == []
                         and not group['members'] and not group['final_members'] and not signals,
                         'Clean group receipt requires one actual empty initial snapshot and no signals')
        else:
            # A group-inspection exception can follow successful Popen reaping.
            # The reaping flag does not claim that inspection itself completed.
            _require(not child['reaped_before_group_check'] or bool(child['errors']),
                     'Missing group report after reaping has no recorded error')
        forced = bool(child['graceful_timeout'] or requests or (group or {}).get('forced_cleanup'))
        _require(type(result['forced_service_stop']) is bool and result['forced_service_stop'] == forced,
                 'Forced-service flag suppresses or invents cleanup intervention')
        child_errors, group_errors = child['errors'], (group or {}).get('errors', [])
        _require(all(type(v) is list and all(type(e) is str for e in v)
                     for v in (child_errors, group_errors, result['cleanup_errors'])), 'Invalid cleanup error records')
        _require(set(child_errors + group_errors) <= set(result['cleanup_errors']),
                 'Case cleanup errors omit owned-child/group errors')

        block(report['phases'] != COMPLETE_PHASES, 'Expected exit lifecycle is incomplete')
        block(bool(previous_errors), 'Diagnostic operations reported errors')
        block(bool(trace), 'Post-asyncio watchdog output requires investigation')
        block(boundary.get('boundary') != 'asyncio_observer' or boundary.get('outcome') != 'returned',
              'Asyncio observer did not return normally')
        block(any(e.get('diagnostic_errors') for e in old), 'Asyncio diagnostic operations reported errors')
        block(code != 0 or forced, 'Service did not exit cleanly without intervention')
        block(bool(child_errors or group_errors or result['cleanup_errors']), 'Cleanup reported errors')
        block(group is None or not group['initially_empty'] or not group['final_empty'] or group['forced_cleanup'],
              'Owned service group was not already empty after parent exit')
        block(service['status'] != 'stopped' or bool(service.get('capture_errors') or service.get('network_errors')),
              'ASGI service did not record an error-free stop')
        if exit_event is not None:
            block(_epoch_ns(stop['requested_at_utc']) > _epoch_ns(exit_event['at_utc']),
                  'Asyncio finished before the recorded stop request')
        report['process_exit'] = {'returncode': code, 'forced_service_stop': forced,
                                  'graceful_timeout': child['graceful_timeout'],
                                  'signal_request_count': len(requests),
                                  'reaped_before_group_check': child['reaped_before_group_check']}
        report['valid'] = True
        report['complete'] = not report['completion_blockers']
    except (OSError, ValueError, KeyError, TypeError, IndexError, OverflowError) as error:
        report['validation_errors'].append(type(error).__name__ + ': ' + str(error))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', type=Path)
    args = parser.parse_args()
    result = validate_interpreter_exit(args.case)
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result['valid'] and result['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
