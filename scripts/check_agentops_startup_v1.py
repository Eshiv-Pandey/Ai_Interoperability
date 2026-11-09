"""Read-only binding of passive startup samples to the recorded v4 service.

Valid partial records are retained after readiness failure. Complete startup
observation requires a real matching readiness file, observed readiness and a
stopped monitor. It does not establish application completion or clean process
exit; the existing independent effect and process checks remain mandatory.
No observer or application code is imported and no signal/request is sent.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _epoch_ns(value):
    stamp = datetime.fromisoformat(value)
    _require(stamp.tzinfo is not None, 'Case window requires timezone-aware timestamps')
    delta = stamp.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return (delta.days * 86400 + delta.seconds) * 1_000_000_000 + delta.microseconds * 1000


def diagnostic_launch(case_dir, process):
    """Parse only the explicit v4 diagnostic launch; defaults equal the wrapper."""
    pid, argv = process['pid'], process['argv']
    _require(type(pid) is int and pid > 1, 'Invalid service PID')
    _require(type(argv) is list and all(type(x) is str for x in argv), 'Invalid service argv')
    _require(len(argv) in (7, 9, 11) and argv[1] == '-B' and argv[3] == '--output'
             and argv[5] == '--port' and argv[6] == '18764', 'Unexpected diagnostic service arguments')
    script = PurePosixPath(argv[2].replace('\\', '/'))
    output = PurePosixPath(argv[4].replace('\\', '/'))
    _require(script.name == 'serve_agentops_bridge_diagnostic_v4.py'
             and script.parts[-2] == 'scripts', 'Unexpected diagnostic service version')
    _require(output.parts[-4:] == ('runs', 'agentops-http-control', Path(case_dir).name, 'service')
             and output.parts[:-4] == script.parts[:-2], 'Service argv does not bind this case/workspace')
    values = {'--exit-watchdog-seconds': 5.0, '--startup-stack-seconds': 5.0}
    supplied = set()
    for option, raw in zip(argv[7::2], argv[8::2], strict=True):
        _require(option in values and option not in supplied, 'Unknown or duplicate diagnostic option')
        value = float(raw)
        _require(math.isfinite(value) and value > 0, 'Invalid diagnostic interval')
        values[option] = value
        supplied.add(option)
    return {'pid': pid, 'argv': argv, 'service_output': str(output), 'port': 18764,
            'exit_seconds': values['--exit-watchdog-seconds'],
            'startup_seconds': values['--startup-stack-seconds']}


def validate_startup(case_dir: Path) -> dict:
    case_dir = Path(case_dir)
    report = {'schema_version': 'agentops-startup-check/1', 'valid': False, 'complete': False,
              'validation_errors': [], 'completion_blockers': [], 'files': [], 'phases': [],
              'root_cause_established': False, 'application_success_established': False,
              'scientific_gate_credit_added': 0,
              'claim_limit': 'Passive process-bound startup locations; daemon scheduling and GIL availability '
                             'limit sampling. Missing samples do not prove absence of a stall.'}

    def raw(name, limit=2_000_000):
        path = case_dir / name
        _require(path.stat().st_size <= limit, 'Diagnostic file exceeds bound: ' + name)
        data = path.read_bytes()
        report['files'].append({'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        return data

    def load(name):
        return json.loads(raw(name))

    def block(condition, message):
        if condition:
            report['completion_blockers'].append(message)

    try:
        process, result = load('service-process.json'), load('result.json')
        launch = diagnostic_launch(case_dir, process)
        started, finished = _epoch_ns(result['started_at_utc']), _epoch_ns(result['finished_at_utc'])
        _require(started < finished and started <= _epoch_ns(process['started_at_utc']) <= finished,
                 'Service process receipt lies outside case window')
        events = [json.loads(line) for line in raw('service/startup-diagnostics/lifecycle.jsonl').splitlines()]
        trace = raw('service/startup-diagnostics/startup-stacks.txt', 16_000_000)
        _require(events and events[0]['phase'] == 'startup_observer_armed', 'Missing startup arming marker')
        previous_tick, previous_errors = -1, []
        monitor = ready = stopped = False
        captures, terminal = {}, {}
        pending = None
        common = {'schema_version', 'sequence', 'pid', 'monotonic_ns', 'at_epoch_ns', 'phase', 'diagnostic_errors'}
        extras = {'startup_observer_armed': {'interval_seconds', 'poll_seconds', 'capture_backend'},
                  'startup_monitor_started': set(), 'startup_stack_capture_started': {'capture', 'capture_monotonic_ns'},
                  'startup_stack_capture_completed': {'capture'}, 'startup_stack_capture_failed': {'capture'},
                  'readiness_observed': set(), 'startup_observer_stopped': {'reason', 'captures'}}
        ready_event = stop_event = None
        for sequence, event in enumerate(events, 1):
            phase = event['phase']
            _require(not stopped and phase in extras and set(event) == common | extras[phase],
                     'Unknown, malformed or post-stop startup event')
            _require(event['schema_version'] == 'agentops-startup-event/1'
                     and type(event['sequence']) is int and event['sequence'] == sequence
                     and type(event['pid']) is int and event['pid'] == launch['pid'], 'Startup schema, sequence or PID mismatch')
            tick, epoch = event['monotonic_ns'], event['at_epoch_ns']
            _require(type(tick) is int and tick > previous_tick and type(epoch) is int
                     and started <= epoch <= finished, 'Startup clocks are unordered or outside case window')
            errors = event['diagnostic_errors']
            _require(type(errors) is list and errors[:len(previous_errors)] == previous_errors
                     and all(type(e) is dict and set(e) == {'stage', 'error_type'}
                             and all(type(v) is str and v for v in e.values()) for e in errors),
                     'Malformed or noncumulative diagnostic errors')
            if phase == 'startup_observer_armed':
                _require(sequence == 1 and type(event['interval_seconds']) in (int, float)
                         and event['interval_seconds'] == launch['startup_seconds']
                         and type(event['poll_seconds']) in (int, float) and event['poll_seconds'] == 0.05
                         and event['capture_backend'] == 'daemon_dump_traceback', 'Startup configuration differs from v4 launch')
            elif phase == 'startup_monitor_started':
                _require(not monitor and sequence == 2, 'Duplicate or misplaced startup monitor')
                monitor = True
            elif phase == 'startup_stack_capture_started':
                number, captured = event['capture'], event['capture_monotonic_ns']
                _require(monitor and not ready and pending is None and type(number) is int
                         and number == len(captures) + 1 and type(captured) is int
                         and previous_tick < captured <= tick, 'Unbound or overlapping startup capture')
                captures[number] = captured
                pending = number
            elif phase in ('startup_stack_capture_completed', 'startup_stack_capture_failed'):
                number = event['capture']
                _require(type(number) is int and pending == number, 'Startup capture completion has no matching start')
                if phase.endswith('failed'):
                    _require(any(e['stage'] == 'dump_startup_stack' for e in errors), 'Failed sample has no retained diagnostic error')
                terminal[number] = phase
                pending = None
            elif phase == 'readiness_observed':
                _require(monitor and not ready and pending is None, 'Duplicate or misplaced startup readiness')
                ready, ready_event = True, event
            else:
                reason = event['reason']
                _require(pending is None and type(event['captures']) is int and event['captures'] == len(captures),
                         'Startup stop suppresses an unfinished capture or changes the count')
                _require(reason in ('readiness_observed', 'wrapper_finished', 'service_coroutine_finished',
                                    'daemon_construction_failed', 'daemon_start_failed', 'observer_failed'), 'Unknown startup stop reason')
                _require((reason == 'readiness_observed') == ready, 'Startup stop contradicts readiness marker')
                _require(monitor or (reason == 'daemon_construction_failed' and errors), 'Stop without a started monitor')
                if reason.endswith('failed'):
                    _require(errors, 'Failed monitor has no retained error')
                stopped, stop_event = True, event
            previous_tick, previous_errors = tick, errors
        headers = list(re.finditer(rb'^Startup traceback ([1-9][0-9]*); pid=([1-9][0-9]*); monotonic_ns=([0-9]+)\r?\n', trace, re.M))
        seen = set()
        _require(not trace or (headers and headers[0].start() == 0), 'Startup trace has no bound capture header')
        for index, header in enumerate(headers):
            number, pid, tick = map(int, header.groups())
            _require(number in captures and number not in seen and pid == launch['pid'] and tick == captures[number],
                     'Startup trace header does not bind its lifecycle capture')
            _require(number == index + 1, 'Startup trace captures are reordered or missing')
            seen.add(number)
            end = headers[index + 1].start() if index + 1 < len(headers) else len(trace)
            if terminal.get(number) == 'startup_stack_capture_completed':
                _require(b'File "' in trace[header.end():end], 'Completed startup capture lacks a Python stack location')
        _require(all(number in seen for number, phase in terminal.items() if phase.endswith('completed')),
                 'Completed startup sample is missing its trace')
        readiness_file = case_dir / 'service/service-ready.json'
        if readiness_file.exists():
            value = load('service/service-ready.json')
            _require(type(value['port']) is int and value['port'] == launch['port']
                     and PurePosixPath(value['state_dir'].replace('\\', '/')) == PurePosixPath(launch['service_output']) / 'state',
                     'Readiness file does not bind the service port/state directory')
            stamp = _epoch_ns(value['started_at_utc'])
            _require(started <= stamp <= finished and (ready_event is None or stamp <= ready_event['at_epoch_ns']),
                     'Readiness timestamp is outside case or after observation')
        else:
            _require(not ready, 'Observed readiness has no retained readiness file')
        for name in ('interpreter-exit-diagnostics', 'shutdown-diagnostics'):
            journal = f'service/{name}/lifecycle.jsonl'
            if not (case_dir / journal).exists():
                continue
            values = [json.loads(line) for line in raw(journal).splitlines()]
            _require(all(type(v['pid']) is int and v['pid'] == launch['pid'] for v in values), 'Other lifecycle has a different service PID')
            if values:
                _require(events[0]['monotonic_ns'] < values[0]['monotonic_ns'], 'Startup observer was not armed before service/exit observation')
            boundaries = [v for v in values if v['phase'] in ('teardown_watchdog_armed', 'entrypoint_boundary')]
            block(bool(stop_event and boundaries and stop_event['monotonic_ns'] >= boundaries[0]['monotonic_ns']),
                  'Startup monitor did not stop before the next diagnostic boundary')
        block(not monitor, 'Startup monitor entry is missing')
        block(not readiness_file.exists() or not ready, 'Matching service readiness was not observed')
        block(not stopped or (stop_event or {}).get('reason') != 'readiness_observed', 'Startup monitor did not stop on readiness')
        block(pending is not None, 'Startup sample was interrupted before completion')
        block(bool(previous_errors), 'Startup diagnostic operations reported errors')
        block(any(phase.endswith('failed') for phase in terminal.values()), 'Startup stack capture failed')
        report.update(valid=True, complete=not report['completion_blockers'], pid=launch['pid'],
                      phases=[e['phase'] for e in events], captures_started=len(captures),
                      captures_completed=sum(p.endswith('completed') for p in terminal.values()),
                      trace_bytes=len(trace), readiness_observed=ready, observer_stopped=stopped,
                      diagnostic_errors=previous_errors, launch=launch)
    except (OSError, ValueError, KeyError, TypeError, IndexError, OverflowError) as error:
        report['validation_errors'].append(type(error).__name__ + ': ' + str(error))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', type=Path)
    report = validate_startup(parser.parse_args().case)
    print(json.dumps(report, indent=2, allow_nan=False))
    raise SystemExit(0 if report['valid'] and report['complete'] else 1)
