"""Read-only verifier for a retained standalone admitted-client allocation.

This checks public/controller evidence and current source-byte correspondence.
It does not authenticate the journal, prove loaded-code identity, execute a
bridge, or verify application effects, hidden history or domain eligibility.
"""
from __future__ import annotations

import argparse
import base64
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from interoperability import pending_admission, refinement_oracle

PYTHON_SOURCES = ('pending_admission.py', 'refinement.py', 'refinement_oracle.py', 'manifest.py', 'oracle.py')
OBSERVATIONS = {'tools': 'discover_full_tools', 'discovery': 'discover_agent',
                'initial': 'initial_typed_send', 'pending': 'pending_origin_get', 'raw': 'public_raw_get'}
EVENT_SCHEMA = 'agentops-admitted-client-event/1'
META = {'schema_version', 'seq', 'at_utc', 'monotonic_ns', 'kind'}


class CheckError(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise CheckError(message)


def pairs(items):
    result = {}
    for key, value in items:
        need(key not in result, 'Duplicate JSON key: ' + key)
        result[key] = value
    return result


def bad_constant(value):
    raise CheckError('Non-JSON numeric constant: ' + value)


def decode(raw):
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=bad_constant)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def same(left, right):
    return canonical(left) == canonical(right)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def utc(value):
    need(type(value) is str, 'Missing UTC timestamp')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    need(parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0, 'Timestamp must be UTC')
    return parsed.timestamp()


def recorded_path(parent, *parts):
    need(type(parent) is str and bool(parent), 'Missing recorded absolute path')
    cls = PureWindowsPath if re.match(r'^[A-Za-z]:[\\/]', parent) or parent.startswith('\\\\') else PurePosixPath
    path = cls(parent)
    need(path.is_absolute(), 'Recorded path is not absolute')
    return str(path.joinpath(*parts))


def tool_call(name, arguments):
    return {'method': 'tools/call', 'params': {'name': name, 'arguments': arguments}}


def decoded_body(body):
    need(type(body) is dict and body.get('isError') is not True and body.get('isToolError') is not True,
         'Public recheck returned a tool error')
    if type(body.get('structuredContent')) is dict:
        return body['structuredContent']
    content = body.get('content')
    need(type(content) is list and bool(content) and type(content[0]) is dict
         and content[0].get('type') == 'text', 'Public JSON tool body missing')
    value = decode(content[0]['text'])
    need(type(value) is dict, 'Public JSON body is not an object')
    return value


def public_signature(observations):
    listed = observations['tools']['body']
    need(type(listed) is dict and type(listed.get('tools')) is list
         and 'error' not in listed and listed.get('isError') is not True, 'Invalid refreshed tools/list')
    discovery = decoded_body(observations['discovery']['body'])
    initial = decoded_body(observations['initial']['body'])['task']
    pending = decoded_body(observations['pending']['body'])
    raw = decoded_body(observations['raw']['body'])
    need(raw.get('jsonrpc') == '2.0' and type(raw.get('id')) in (str, int) and 'error' not in raw,
         'Invalid refreshed raw RPC envelope')
    normalize = lambda value: value.removeprefix('TASK_STATE_').replace('-', '_').lower()
    need(pending['id'] == initial['id'] and pending['context_id'] == initial['context_id']
         and normalize(pending['state']) == 'input_required', 'Refreshed typed association/state changed')
    task = raw['result']
    need(task['id'] == initial['id'] and task['contextId'] == initial['context_id']
         and normalize(task['status']['state']) == 'input_required', 'Refreshed raw association/state changed')
    return {'tools': listed['tools'], 'discovery': {'url': discovery.get('url'),
            'interfaces': discovery.get('card', {}).get('interfaces')},
            'task_id': initial['id'], 'context_id': initial['context_id'],
            'pending_state': normalize(pending['state']), 'raw_task': task}


def event_payload(event):
    # The current emitter spreads the payload after its envelope. The admission
    # receipt owns schema_version; child-exit owns at_utc. Preserve those fields.
    value = {key: item for key, item in event.items() if key not in META}
    if event['kind'] == 'admission-result':
        value['schema_version'] = event['schema_version']
    if event['kind'] == 'child-exit':
        value['at_utc'] = event['at_utc']
    return value


def check_client(client_dir, source_root=None, expected_sources=None):
    """Check fixed local files; optional source hashes add byte checks, not provenance."""
    directory = Path(client_dir).resolve()
    source_root = ROOT if source_root is None else Path(source_root).resolve()
    report = {'schema_version': 'agentops-admitted-client-check/1', 'status': 'failed',
              'client_scope_verified': False, 'errors': [], 'continuation_transport_attempts': 0,
              'continuation_stdin_write_completions': 0, 'admission_decision': None,
              'certificate_valid': None, 'public_task_final_state': None,
              'public_bindings': None,
              'source_receipt_matches': False, 'application_effect_verified': False,
              'loaded_source_fidelity_verified': False, 'journal_authenticated': False,
              'qualified_domain': False, 'files': [],
              'scope': 'Public MCP bytes, controller ordering, conditional admission certificate and recorded source-byte correspondence only'}
    read_files = {}

    def read(relative, parse=True):
        target = directory / relative
        need(target.is_file() and not target.is_symlink(), 'Missing/nonregular bundle file: ' + relative)
        raw = target.read_bytes()
        need(len(raw) <= 268435456, 'Bundle file exceeds operational checker bound')
        record = {'path': relative, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        read_files[relative] = record
        return decode(raw) if parse else raw

    try:
        config, result = read('config.json'), read('result.json')
        need(config.get('schema_version') == 'agentops-admitted-client-config/1', 'Wrong client config schema')
        need(result.get('schema_version') == 'agentops-admitted-client-result/1', 'Wrong client result schema')
        need(config.get('arm') in ('B5', 'B6', 'B7') and result.get('arm') == config['arm'], 'Wrong/mismatched admitted arm')
        need(type(config.get('admission')) is dict and 'output_dir' not in config['admission'], 'Invalid admission configuration')
        recorded_path(config.get('output_dir'))
        for key, maximum in (('budget', 10000000), ('timeout_ms', 30000)):
            value = config['admission'].get(key)
            need(type(value) is int and 0 < value <= maximum, 'Invalid configured admission bound: ' + key)
        for key, maximum in (('request_timeout_ms', 45000), ('poll_interval_ms', 2000),
                             ('poll_attempts', 60), ('total_timeout_ms', 300000), ('max_response_bytes', 33554432)):
            value = config.get('limits', {}).get(key)
            need(type(value) is int and 0 < value <= maximum, 'Invalid configured client bound: ' + key)
        need(result.get('strict_success') is None and result.get('live_effect_verified_by_client') is False,
             'Client makes an unsupported task/effect success claim')
        need(same(result.get('configured_limits'), config.get('limits')), 'Configured limits changed')
        events = [decode(line) for line in read('mcp.jsonl', False).splitlines()]
        need(bool(events), 'Empty public journal')
        by_seq, operations, stdout_pending = {}, {}, b''
        monotonic = -1
        incoming_frames = []
        for index, event in enumerate(events, 1):
            expected_schema = 'pending-admission-result/1' if event.get('kind') == 'admission-result' else EVENT_SCHEMA
            need(type(event) is dict and event.get('schema_version') == expected_schema and event.get('seq') == index,
                 'Invalid event schema or sequence')
            need(type(event.get('monotonic_ns')) is str and event['monotonic_ns'].isdigit(), 'Missing monotonic event clock')
            current = int(event['monotonic_ns'])
            need(current >= monotonic, 'Event monotonic clock moved backwards')
            monotonic = current
            utc(event.get('at_utc'))
            by_seq[index] = event
            kind = event.get('kind')
            if kind in ('stdio-chunk', 'mcp-message', 'mcp-parse-error', 'stdio-trailing-bytes'):
                entity = event.get('raw')
                need(type(entity) is dict and set(entity) == {'base64', 'bytes', 'sha256'}, 'Missing raw-byte entity')
                raw = base64.b64decode(entity['base64'], validate=True)
                need(type(entity['bytes']) is int and entity['bytes'] == len(raw)
                     and entity['sha256'] == hashlib.sha256(raw).hexdigest(), 'Raw-byte hash/length mismatch')
            if kind == 'stdio-chunk':
                need(event.get('direction') in ('bridge_to_client', 'bridge_stderr'), 'Unexpected chunk direction')
                if event['direction'] == 'bridge_to_client':
                    stdout_pending += raw
                    while b'\n' in stdout_pending:
                        line, stdout_pending = stdout_pending.split(b'\n', 1)
                        incoming_frames.append(line + b'\n')
            elif kind == 'operation-start':
                identifier = event.get('operation_id')
                need(type(identifier) is int and identifier > 0 and identifier not in operations, 'Duplicate/invalid operation ID')
                operations[identifier] = {'start': event}
            elif kind == 'mcp-message':
                need(event.get('framing') == 'stdio-line' and raw.endswith(b'\n'), 'Invalid MCP stdio framing')
                parsed = decode(raw)
                need(same(parsed, event.get('parsed')) and type(parsed) is dict and parsed.get('jsonrpc') == '2.0',
                     'Raw/parsed MCP mismatch')
                direction = event.get('direction')
                if direction == 'bridge_to_client':
                    need(bool(incoming_frames) and incoming_frames.pop(0) == raw, 'MCP reply differs from captured stdout')
                    identifier = parsed.get('id')
                    if 'method' in parsed:
                        need(event.get('operation_id') is None, 'Server notification linked to a client operation')
                        continue
                    need(type(identifier) is int and identifier in operations, 'Unassociated MCP response')
                    op = operations[identifier]
                    need('sent' in op and 'reply' not in op and event.get('operation_id') == identifier
                         and event.get('phase') == op['start']['phase'], 'Duplicate/mismatched MCP reply')
                    need(('result' in parsed) != ('error' in parsed), 'MCP response needs exactly result or error')
                    op['reply'] = event
                else:
                    need(direction == 'client_to_bridge', 'Unexpected MCP message direction')
                    identifier = event.get('operation_id')
                    need(type(identifier) is int and identifier in operations, 'Request lacks operation-start')
                    op = operations[identifier]
                    start = op['start']
                    need('sent' not in op and event.get('phase') == start['phase'] and parsed.get('method') == start['method'],
                         'Duplicate/mismatched outgoing request')
                    need(type(start.get('notification')) is bool and
                         (('id' not in parsed) if start['notification'] else type(parsed.get('id')) is int and parsed['id'] == identifier),
                         'Request/operation ID mismatch')
                    op['sent'] = event
            elif kind == 'stdio-written':
                identifier = event.get('operation_id')
                need(identifier in operations, 'Write lacks operation')
                op = operations[identifier]
                need('sent' in op and 'write' not in op and event.get('source_seq') == op['sent']['seq']
                     and event.get('bytes') == op['sent']['raw']['bytes'], 'Forged/duplicate completed write')
                op['write'] = event
            elif kind in ('operation-complete', 'operation-error'):
                identifier = event.get('operation_id')
                need(identifier in operations, 'Operation terminal lacks start')
                op = operations[identifier]
                need('terminal' not in op and event.get('phase') == op['start']['phase'], 'Duplicate/mismatched operation terminal')
                if kind == 'operation-complete':
                    need('write' in op, 'Completed operation lacks completed stdin write')
                    if op['start']['notification']:
                        need(event.get('reply_seq') is None, 'Notification has reply linkage')
                    else:
                        need('reply' in op and event.get('reply_seq') == op['reply']['seq']
                             and op['reply']['seq'] < index and 'error' not in op['reply']['parsed'], 'False successful operation')
                op['terminal'] = event
            elif kind == 'mcp-parse-error':
                need(bool(incoming_frames) and incoming_frames.pop(0) == raw, 'Parse error differs from captured stdout')
            elif kind == 'stdio-trailing-bytes':
                need(raw == stdout_pending, 'Trailing stdout bytes mismatch')
                stdout_pending = b''
        need(not incoming_frames and not stdout_pending, 'Captured stdout is missing parsed/trailing accounting')
        need(all('sent' in op and 'terminal' in op for op in operations.values()), 'Unfinished or omitted operation evidence')
        ordered = sorted(operations.values(), key=lambda op: op['start']['seq'])
        need([op['start']['operation_id'] for op in ordered] == list(range(1, len(ordered) + 1)), 'Operation ID accounting gap')
        phases = lambda phase: [op for op in ordered if op['start']['phase'] == phase]
        initial_ops = phases('initial_typed_send')
        need(len(initial_ops) <= 1, 'Initial task was sent more than once')
        task_id = None
        if initial_ops and 'reply' in initial_ops[0] and 'result' in initial_ops[0]['reply']['parsed']:
            task = decoded_body(initial_ops[0]['reply']['parsed']['result']).get('task', {})
            task_id = task.get('id')
            report['public_bindings'] = {'task_id': task_id, 'context_id': task.get('context_id')}
        for op in ordered:
            phase, request = op['start']['phase'], op['sent']['parsed']
            method, params = request.get('method'), request.get('params', {})
            if phase == 'initialize':
                need(method == 'initialize' and params.get('protocolVersion') == '2025-11-25', 'Wrong MCP initialization')
                continue
            if phase == 'initialized':
                need(method == 'notifications/initialized' and op['start']['notification'], 'Wrong initialization notification')
                continue
            need(not op['start']['notification'], 'Unexpected public notification')
            if phase in ('discover_full_tools', 'admission_recheck_tools'):
                expected = {'method': 'tools/list', 'params': {}}
            elif phase in ('discover_agent', 'admission_recheck_discovery'):
                expected = tool_call('a2a_discover_agent', {'url': config['agent_base_url']})
            elif phase == 'initial_typed_send':
                expected = tool_call('a2a_send_message', {'url': config['agent_base_url'], 'text': 'Restart inventory.'})
            elif phase in ('pending_origin_get', 'final_origin_get', 'admission_recheck_pending'):
                need(type(task_id) is str and bool(task_id), 'Read has no original public task association')
                expected = tool_call('a2a_get_task', {'task_id': task_id, 'history_length': 100, 'refresh': True})
            elif phase in ('public_raw_get', 'admission_recheck_raw'):
                need(type(task_id) is str and bool(task_id), 'Raw read has no original task association')
                expected = tool_call('a2a_request', {'url': config['agent_base_url'], 'method': 'GetTask',
                                                   'params': {'id': task_id, 'historyLength': 100}})
            elif phase == 'raw_answer':
                continue  # Exact independent witness equality checked below.
            else:
                raise CheckError('Unpermitted public operation: ' + str(phase))
            need(same({'method': method, 'params': params}, expected), 'Public request differs from allowed bound operation')

        audit = result.get('admission')
        need(type(audit) is dict and audit.get('schema_version') == 'agentops-admission-controller/1', 'Missing admission controller audit')
        need(audit.get('status') in ('not_reached', 'blocked', 'dispatched', 'dispatch_reserved'), 'Invalid controller audit status')
        need(audit.get('initial_forwarded_attempts') == len(initial_ops), 'Initial transport-attempt accounting mismatch')
        need(audit.get('atomic_server_state_lock') is False and audit.get('claimed_live_effect') is False,
             'Controller makes unsupported atomicity/effect claim')
        admission_events = [e for e in events if e['kind'] == 'admission-result']
        dispatch_events = [e for e in events if e['kind'] == 'admission-dispatch']
        block_events = [e for e in events if e['kind'] == 'admission-blocked']
        payload = event_payload
        need(same(audit.get('admissions'), [payload(e) for e in admission_events]), 'Admission result event/audit mismatch')
        need(same(audit.get('blocks'), [payload(e) for e in block_events]), 'Admission block event/audit mismatch')
        need(len(admission_events) <= 1 and len(dispatch_events) <= 1, 'Multiple one-shot admission/dispatch records')
        answers = phases('raw_answer')
        writes = sum('write' in op for op in answers)
        replies = sum(op['terminal']['kind'] == 'operation-complete' for op in answers)
        attempts = audit.get('continuation_forwarded_attempts')
        need(type(attempts) is int and 0 <= len(answers) <= attempts <= 1, 'Invalid transport-attempt count')
        need(result.get('answer_attempts') == attempts and result.get('answer_replies') == replies
             and audit.get('continuation_forwarded_replies') == replies, 'Continuation count mismatch')
        need(result.get('continuation_stdin_write_completions') == writes, 'False completed-stdin-write count')
        expected_sent = True if writes else None if attempts else False
        need(result.get('answer_sent') is expected_sent, 'answer_sent exceeds retained write evidence')
        report['continuation_transport_attempts'] = attempts
        report['continuation_stdin_write_completions'] = writes

        admission_dir = directory / 'admission'
        receipt = snapshot = None
        if admission_dir.exists():
            snapshot = read('admission/snapshot.json')
            execution, process = read('admission/execution.json'), read('admission/process.json')
            read('admission/stdout.bin', False); read('admission/stderr.bin', False)
            need(execution.get('schema_version') == process.get('schema_version') == 'agentops-admission-subprocess/1', 'Wrong subprocess schema')
            for key in ('executable', 'args', 'cwd', 'started_at_utc', 'timeout_ms', 'budget', 'snapshot_sha256'):
                need(same(execution.get(key), process.get(key)), 'Subprocess start/finish mismatch: ' + key)
            need(process.get('executable') == config['admission']['python']
                 and process.get('budget') == config['admission']['budget']
                 and process.get('timeout_ms') == config['admission']['timeout_ms'], 'Subprocess differs from admission configuration')
            need(process.get('snapshot_sha256') == digest(snapshot), 'Subprocess snapshot digest mismatch')
            args = process.get('args')
            need(type(args) is list and len(args) == 11 and args[:3] == ['-B', '-m', 'interoperability.pending_admission']
                 and args[3:4] == ['--input'] and args[5:6] == ['--output'] and args[7] == '--now' and args[9] == '--budget',
                 'Unexpected admission subprocess command')
            need(args[4] == recorded_path(config['output_dir'], 'admission', 'snapshot.json')
                 and args[6] == recorded_path(config['output_dir'], 'admission', 'result.json')
                 and args[10] == str(process['budget']), 'Admission subprocess path/budget mismatch')
            clock = int(args[8])
            need(str(clock) == args[8] and utc(process['finished_at_utc']) >= utc(process['started_at_utc']) >= clock,
                 'Admission subprocess clock mismatch')
            need(same(snapshot.get('route'), {'arm': config['arm'], 'agent_base_url': config['agent_base_url']})
                 and same(snapshot.get('deployment'), config['admission']['deployment'])
                 and snapshot.get('rationale') == config['rationale'], 'Snapshot differs from configuration')
            for name, phase in OBSERVATIONS.items():
                observed = snapshot['observations'][name]
                event = by_seq.get(observed['seq'])
                need(event is not None and event['kind'] == 'mcp-message' and event['direction'] == 'bridge_to_client'
                     and event['phase'] == phase, 'Snapshot observation lacks its public reply')
                op = operations[event['operation_id']]
                need(op['terminal']['kind'] == 'operation-complete' and same(observed['body'], event['parsed']['result'])
                     and same(observed['request'], {key: op['sent']['parsed'][key] for key in ('method', 'params')}),
                     'Snapshot public request/body differs from journal')
                need(type(observed['observed_at']) is int and int(utc(event['at_utc'])) <= observed['observed_at'] <= clock,
                     'Snapshot public observation clock mismatch')
            if (admission_dir / 'result.json').is_file():
                receipt = read('admission/result.json')
                need(receipt.get('schema_version') == 'pending-admission-result/1'
                     and receipt.get('snapshot_sha256') == digest(snapshot) and receipt.get('evaluation_clock') == clock,
                     'Admission result snapshot/clock mismatch')
                need(receipt.get('input_sha256') == read_files['admission/snapshot.json']['sha256'], 'Admission input file hash mismatch')
                need(receipt.get('application_requests') == 0 and receipt.get('application_completion_verified') is False,
                     'Admission subprocess makes live-effect claim')
                need(utc(process['started_at_utc']) <= utc(receipt['recorded_at_utc']) <= utc(process['finished_at_utc']),
                     'Admission receipt timestamp falls outside subprocess lifetime')
                hashes = receipt.get('source_sha256')
                need(type(hashes) is dict and set(hashes) == set(PYTHON_SOURCES), 'Admission source receipt is incomplete')
                for name, expected in hashes.items():
                    for root in {source_root, ROOT}:
                        need(hashlib.sha256((root / 'src/interoperability' / name).read_bytes()).hexdigest() == expected,
                             'Admission source bytes unavailable or changed: ' + name)
                report['source_receipt_matches'] = True
                report['admission_decision'] = receipt.get('decision')
                report['certificate_valid'] = receipt.get('certificate_valid')
                if receipt.get('profile') is not None:
                    rebuilt = pending_admission.build_profile(copy.deepcopy(snapshot), clock)
                    need(same(rebuilt, receipt['profile']), 'Retained profile differs from public-snapshot rebuild')
                    candidate_result = receipt.get('result')
                    if candidate_result is not None and candidate_result.get('decision') in ('supported', 'unsupported'):
                        valid = refinement_oracle.check_certificate(copy.deepcopy(rebuilt), copy.deepcopy(candidate_result), clock)
                        need(valid is True and receipt.get('certificate_valid') is True, 'Independent certificate rejection')
                    elif candidate_result is not None:
                        need(candidate_result.get('decision') == 'unknown' and candidate_result.get('certificate') is None,
                             'Invalid indeterminate candidate result')
                if admission_events:
                    event = admission_events[0]
                    expected = dict(receipt, receipt_path=recorded_path(config['output_dir'], 'admission', 'result.json'))
                    need(same(payload(event), expected), 'Controller admission differs from subprocess receipt')
                    need(process.get('returncode') == 0 and process.get('signal') is None
                         and process.get('timed_out') is False and process.get('output_limit_reached') is False
                         and 'error' not in process, 'Controller accepted failed admission subprocess')
                    need(utc(event['at_utc']) >= utc(process['finished_at_utc'])
                         and utc(event['at_utc']) >= utc(receipt['recorded_at_utc']), 'Admission event precedes subprocess result')
            else:
                need(not admission_events and attempts == 0, 'Missing accepted admission result file')
        else:
            need(not admission_events and not dispatch_events and attempts == 0, 'Dispatch/admission lacks subprocess artifacts')

        if dispatch_events or attempts:
            need(receipt is not None and len(admission_events) == len(dispatch_events) == 1,
                 'Dispatch lacks one retained admission and intent')
            need(receipt.get('status') == 'recorded' and receipt.get('decision') == 'supported'
                 and receipt.get('dispatch_permitted') is True and receipt.get('certificate_valid') is True,
                 'Continuation after failed/unknown/unsupported admission')
            event = dispatch_events[0]
            need(event['seq'] > admission_events[0]['seq'] and event.get('snapshot_sha256') == digest(snapshot)
                 and same(event.get('request'), receipt['request']), 'Dispatch intent is not the admitted witness')
            need(type(event.get('at')) is int and receipt['evaluation_clock'] <= event['at'] <= snapshot['valid_until']
                 and int(utc(event['at_utc'])) == event['at'], 'Dispatch observation expired or clock mismatched')
            certificate = receipt['result']['certificate']
            need(certificate.get('kind') == 'recipe-path' and len(certificate.get('steps', [])) == 1
                 and same(certificate['steps'][0]['request'], receipt['request'])
                 and same(receipt['request'], snapshot['proposed_call']), 'Witness/request/proposal linkage failed')
            rechecks = audit.get('rechecks')
            need(type(rechecks) is list and len(rechecks) == 1, 'Missing complete public recheck record')
            refreshed = rechecks[0]
            need(same(refreshed['initial'], snapshot['observations']['initial']), 'Recheck changed initial task')
            previous = admission_events[0]['seq']
            for name in ('tools', 'discovery', 'pending', 'raw'):
                checked = refreshed[name]
                observed = by_seq.get(checked['seq'])
                need(observed is not None and observed['kind'] == 'mcp-message'
                     and observed['phase'] == 'admission_recheck_' + name, 'Recheck lacks public reply')
                op = operations[observed['operation_id']]
                need(previous < op['start']['seq'] < observed['seq'] < op['terminal']['seq'] < event['seq']
                     and op['terminal']['kind'] == 'operation-complete', 'Recheck is not completed between admission and dispatch')
                need(same(checked['request'], snapshot['observations'][name]['request'])
                     and same(checked['body'], observed['parsed']['result'])
                     and same(checked['request'], {key: op['sent']['parsed'][key] for key in ('method', 'params')}),
                     'Recheck request/body mismatch')
                need(int(utc(observed['at_utc'])) <= checked['observed_at'] <= event['at'], 'Recheck clock mismatch')
                previous = op['terminal']['seq']
            need(same(public_signature(refreshed), public_signature(snapshot['observations'])), 'Public binding/state/schema changed before dispatch')
            for op in answers:
                need(event['seq'] < op['start']['seq'] and int(utc(op['start']['at_utc'])) <= snapshot['valid_until']
                     and same({key: op['sent']['parsed'][key] for key in ('method', 'params')}, receipt['request']),
                     'Actually dispatched request differs from valid witness')
        else:
            need(not answers and writes == 0, 'Unadmitted continuation was written')
        if audit.get('status') in ('blocked', 'not_reached'):
            need(attempts == 0 and writes == 0, 'Blocked controller forwarded a continuation')
        if audit.get('status') == 'dispatched':
            need(attempts == 1, 'Dispatched controller has no transport attempt')
        if receipt and receipt.get('decision') != 'supported':
            need(attempts == 0 and writes == 0 and receipt.get('dispatch_permitted') is False and receipt.get('request') is None,
                 'Unknown/unsupported receipt permitted dispatch')
        final_reads = [op for op in phases('final_origin_get') if op['terminal']['kind'] == 'operation-complete']
        if final_reads:
            value = decoded_body(final_reads[-1]['reply']['parsed']['result'])
            state = value.get('state')
            need(value.get('id') == task_id and value.get('context_id') == report['public_bindings']['context_id']
                 and result.get('final_state') == state, 'Final public task observation mismatch')
            report['public_task_final_state'] = state
        starts = [e for e in events if e['kind'] == 'child-start']
        cleanup = [e for e in events if e['kind'] == 'child-cleanup']
        exits = [e for e in events if e['kind'] == 'child-exit']
        need(len(starts) == len(cleanup) == 1 and same(payload(cleanup[0]), result.get('child')), 'Child cleanup/result mismatch')
        child = result['child']
        for key in ('command', 'args', 'cwd'):
            need(same(starts[0].get(key), config.get('bridge', {}).get(key)) and same(child.get(key), starts[0].get(key)),
                 'Bridge process/config linkage mismatch: ' + key)
        need(starts[0].get('pid') == child.get('pid') and starts[0]['started_at_utc'] == child['started_at_utc']
             and starts[0].get('clean_exit') is False and starts[0]['seq'] < cleanup[0]['seq'], 'Child lifecycle start linkage mismatch')
        need(utc(result['finished_at_utc']) >= utc(cleanup[0]['at_utc']) >= utc(child['started_at_utc']), 'Child lifecycle clock mismatch')
        need(len(exits) <= 1 and same(child.get('exit'), payload(exits[0]) if exits else None), 'Child exit linkage mismatch')
        if exits:
            need(starts[0]['seq'] < exits[0]['seq'] < cleanup[0]['seq'], 'Child exit order mismatch')
        need(all(starts[0]['seq'] < op['start']['seq'] < cleanup[0]['seq'] for op in ordered), 'Public operation outside client child lifetime')
        clean = not child.get('forced_kill') and child.get('exit', {}).get('code') == 0 and not child.get('exit', {}).get('signal') if child.get('exit') else False
        need(child.get('clean_exit') is clean, 'False clean-exit claim')
        need(not any(event['kind'] in ('output-limit', 'mcp-parse-error', 'stdio-trailing-bytes') for event in events),
             'Public byte capture is truncated, malformed or has an incomplete trailing frame')
        if expected_sources is not None:
            need(type(expected_sources) is dict, 'expected_sources must map relative source paths to SHA-256')
            for relative, expected in expected_sources.items():
                name = PurePosixPath(relative)
                need(not name.is_absolute() and '..' not in name.parts, 'Expected source must be root-relative')
                need(hashlib.sha256((source_root / relative).read_bytes()).hexdigest() == expected,
                     'Prospectively expected source differs: ' + relative)
            report['expected_source_bytes_match'] = True
        for relative, record in read_files.items():
            need(hashlib.sha256((directory / relative).read_bytes()).hexdigest() == record['sha256'], 'Input mutated during verification')
        report.update(status='verified', client_scope_verified=True, journal_events=len(events),
                      operations=len(operations), child_clean_exit=child['clean_exit'],
                      recorded_client_status=result.get('status'))
    except (CheckError, ValueError, TypeError, KeyError, IndexError, OSError, AttributeError) as error:
        report['errors'].append(f'{type(error).__name__}: {error}')
    report['files'] = list(read_files.values())
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client-dir', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, default=ROOT)
    parser.add_argument('--expected-sources', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error('refusing to overwrite existing check receipt')
    expected = decode(args.expected_sources.read_bytes()) if args.expected_sources else None
    result = check_client(args.client_dir, args.source_root, expected)
    result['checked_at_utc'] = datetime.now(timezone.utc).isoformat()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
    print(json.dumps({key: result[key] for key in ('status', 'client_scope_verified', 'continuation_stdin_write_completions', 'errors')}))
    return 0 if result['client_scope_verified'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
