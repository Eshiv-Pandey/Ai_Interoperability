"""Independent, outcome-neutral checks of retained AgentOps bridge observations.

This module reads captured entities and SQLite snapshots. It never imports the
bridge driver, service fixture, application or SDK, and never starts a process.
Evidence integrity and strict task success are separate outputs: an observed
RPC failure or completed task without its required effect is still evidence.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path

from check_agentops_effect_v2 import at_utc, db_value, decode_json, require, same, seed_snapshot
from check_agentops_socket_policy_v1 import check_policy

RATIONALE = 'Inventory is down and INC-002 matches the service-down runbook.'
START_TEXT = 'Restart inventory.'
LITERAL_CONFIRMATION = 'Yes, confirm the inventory restart. Rationale: ' + RATIONALE


def _headers(rows):
    require(type(rows) is list, 'Header list')
    result = {}
    for row in rows:
        require(type(row) is list and len(row) == 2 and all(type(v) is str for v in row),
                'Header pair')
        name, value = row
        require(bool(name) and name.strip() == name and '\r' not in name + value
                and '\n' not in name + value, 'Header syntax')
        result.setdefault(name.lower(), []).append(value)
    return result


def _single_header(headers, name):
    values = headers.get(name, [])
    require(len(values) <= 1, 'Ambiguous ' + name)
    return values[0] if values else None


def _sse_payloads(body):
    text = body.decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n')
    require(text.endswith('\n\n'), 'SSE ends inside an event')
    messages, data = [], []
    for line in text.split('\n'):
        if line == '':
            if data:
                messages.append('\n'.join(data).encode('utf-8'))
                data = []
        elif not line.startswith(':'):
            field, _, value = line.partition(':')
            if field == 'data':
                data.append(value[1:] if value.startswith(' ') else value)
            else:
                require(field in ('event', 'id', 'retry'), 'Unexpected SSE field')
    require(not data and bool(messages), 'Empty or incomplete SSE response')
    return messages


def _sse_messages(body):
    return [decode_json(raw) for raw in _sse_payloads(body)]


def parse_asgi_exchange(directory, expected_sequence=None):
    """Validate retained ASGI entity bytes; preserve protocol errors as outcomes.

    ASGI chunks are application body boundaries, not TCP/HTTP chunk framing.
    Incomplete transport records remain partial and cannot establish success.
    """
    record = decode_json((directory / 'exchange.json').read_bytes())
    require(record.get('schema_version') == 'agentops-asgi-exchange/1', 'ASGI exchange schema')
    require(type(record.get('sequence')) is int and 1 <= record['sequence'] <= 256, 'ASGI sequence')
    if expected_sequence is not None:
        require(record['sequence'] == expected_sequence, 'ASGI directory/sequence binding')
    require(type(record.get('method')) is str and type(record.get('path')) is str
            and type(record.get('http_version')) is str, 'ASGI request scope')
    query = base64.b64decode(record['query_string'], validate=True)
    request_headers = _headers(record['request_headers'])
    response_headers = _headers(record.get('response_headers', []))
    request_raw = (directory / 'request.body.bin').read_bytes()
    response_raw = (directory / 'response.body.bin').read_bytes()
    require(record.get('request_bytes') == len(request_raw) and type(record.get('request_bytes')) is int
            and record.get('response_bytes') == len(response_raw) and type(record.get('response_bytes')) is int,
            'ASGI recorded entity byte counts')
    for name in ('request_body_complete', 'response_body_complete'):
        require(type(record.get(name)) is bool, 'Explicit ASGI completion flag')
    require(record.get('response_status') is None or type(record['response_status']) is int
            and 100 <= record['response_status'] <= 599, 'ASGI response status')
    chunks = record.get('response_chunks')
    require(type(chunks) is list, 'ASGI response chunks')
    offset = 0
    for index, chunk in enumerate(chunks):
        require(type(chunk) is dict and type(chunk.get('bytes')) is int and chunk['bytes'] >= 0
                and type(chunk.get('more_body')) is bool, 'ASGI chunk shape')
        require(chunk.get('sha256') == hashlib.sha256(response_raw[offset:offset + chunk['bytes']]).hexdigest(),
                'ASGI response chunk hash')
        offset += chunk['bytes']
        if index < len(chunks) - 1:
            require(chunk['more_body'] is True, 'ASGI bytes after closed response')
    require(sum(chunk['bytes'] for chunk in chunks) == len(response_raw), 'ASGI response byte count')
    require(record['response_body_complete'] is bool(chunks and not chunks[-1]['more_body']),
            'ASGI final chunk/completion binding')
    if record['response_body_complete']:
        require(record['response_status'] is not None, 'Completed response has status')
    length = _single_header(request_headers, 'content-length')
    if length is not None and record['request_body_complete']:
        require(length.isdigit() and int(length) == len(request_raw), 'ASGI request content length')
    length = _single_header(response_headers, 'content-length')
    if length is not None and record['response_body_complete']:
        require(length.isdigit() and int(length) == len(response_raw), 'ASGI response content length')
    before = decode_json((directory / 'before.snapshot.json').read_bytes())
    after = decode_json((directory / 'after.snapshot.json').read_bytes())
    require(type(before.get('monotonic_ns')) is int and type(after.get('monotonic_ns')) is int
            and before['monotonic_ns'] < after['monotonic_ns'], 'ASGI snapshot clock ordering')
    require(at_utc(before['observed_at_utc']) <= at_utc(record['started_at_utc'])
            <= at_utc(record['finished_at_utc']) <= at_utc(after['observed_at_utc']),
            'ASGI exchange inside snapshots')
    for boundary in (before, after):
        require(boundary['database']['path'] == 'state/incidents.db'
                and boundary['database']['path_base'] == 'run', 'Isolated domain snapshot path')
        db_value(boundary['database'])
    complete = record['request_body_complete'] and record['response_body_complete']
    protocol_errors = []
    request, responses = None, []
    if request_raw and record['request_body_complete']:
        try:
            request = decode_json(request_raw)
        except (ValueError, UnicodeError) as error:
            protocol_errors.append('request JSON: ' + str(error))
    if record['response_body_complete']:
        try:
            media = (_single_header(response_headers, 'content-type') or '').split(';', 1)[0].strip()
            if media == 'text/event-stream':
                responses = _sse_messages(response_raw)
            elif media == 'application/json':
                responses = [decode_json(response_raw)]
            else:
                protocol_errors.append('non-JSON/SSE response: ' + media)
        except (ValueError, UnicodeError) as error:
            protocol_errors.append('response entity: ' + str(error))
    if isinstance(request, dict) and request.get('jsonrpc') == '2.0' and 'id' in request:
        for reply in responses:
            if not isinstance(reply, dict) or reply.get('jsonrpc') != '2.0':
                protocol_errors.append('response is not a JSON-RPC envelope')
            elif reply.get('id') != request['id']:
                # Retain an error with null ID as an observed server response;
                # it supplies no successful matching RPC result.
                protocol_errors.append('response/request RPC ID mismatch')
    return {'record': record, 'request': request, 'responses': responses,
            'before': before, 'after': after, 'complete': complete,
            'query': query.decode('ascii'), 'request_headers': request_headers,
            'response_headers': response_headers, 'protocol_errors': protocol_errors,
            'request_bytes': len(request_raw), 'response_bytes': len(response_raw)}


def classify_effect(seed, boundaries, original, confirmation, service=None):
    """Classify database effects without assuming that an observed arm succeeds.

    confirmation identifies the actual legal continuation's service-clock
    boundary, or is None when no continuation was sent. It does not assert
    that arbitrary text became a typed FunctionResponse.
    """
    require(type(boundaries) is list and bool(boundaries), 'Effect snapshots present')
    ordered = sorted(boundaries, key=lambda row: row['monotonic_ns'])
    ticks = [row['monotonic_ns'] for row in ordered]
    require(all(type(value) is int for value in ticks) and len(ticks) == len(set(ticks)),
            'Distinct effect snapshot clocks')
    values = [db_value(row['database']) for row in ordered]
    initial = db_value(seed)
    final = values[-1]
    deviations = []
    if not same(values[0], initial):
        deviations.append('initial_domain_differs_from_seed')
    changed = [index for index, value in enumerate(values) if not same(value, initial)]
    report = {'classification': 'unchanged' if not changed else 'unexpected_domain_change',
              'effect_matches_contract': False, 'domain_changed': bool(changed),
              'new_audit_rows': len(final['tables']['audit_log']) - len(initial['tables']['audit_log']),
              'approval_observed': False, 'deviations': deviations,
              'final_inventory_status': next((row['status'] for row in final['tables']['services']
                                              if row['name'] == 'inventory'), None)}
    if not changed:
        return report
    if confirmation is None:
        deviations.append('domain_effect_without_continuation')
    else:
        require(type(confirmation.get('before_monotonic_ns')) is int, 'Continuation snapshot clock')
        at_utc(confirmation['started_at_utc'])
        if any(ticks[index] <= confirmation['before_monotonic_ns'] for index in changed):
            deviations.append('domain_effect_before_continuation')
    audits = final['tables']['audit_log']
    if len(audits) != 1:
        deviations.append('not_exactly_one_final_audit_row')
        return report
    audit = audits[0]
    context_id = original.get('context_id') if isinstance(original, dict) else None
    if type(context_id) is not str or not context_id:
        deviations.append('original_context_unavailable')
        return report
    expected_fields = {'id': 1, 'schema_version': 1, 'actor': 'agentops-agent',
        'approved_by': 'A2A_USER_' + context_id, 'rationale': RATIONALE,
        'context_summary': 'service inventory was down; open incidents: INC-002',
        'session_id': context_id, 'action': 'restart_service', 'target': 'inventory',
        'detail': 'service restarted and marked operational (mock)'}
    if not all(same(audit.get(key), value) for key, value in expected_fields.items()):
        deviations.append('audit_attribution_or_action_mismatch')
    invocation = audit.get('invocation_id')
    if type(invocation) is not str or not invocation:
        deviations.append('audit_invocation_unavailable')
    if confirmation is not None:
        try:
            audit_time = at_utc(audit['ts'])
            if not (at_utc(confirmation['started_at_utc']).replace(microsecond=0) <= audit_time
                    <= at_utc(ordered[changed[0]]['observed_at_utc'])):
                deviations.append('audit_time_outside_continuation_interval')
        except (ValueError, KeyError):
            deviations.append('invalid_audit_time')
    expected = copy.deepcopy(initial)
    target = [row for row in expected['tables']['services'] if row['name'] == 'inventory']
    require(len(target) == 1 and target[0]['status'] == 'down', 'Seed inventory target')
    target[0]['status'] = 'operational'
    expected['tables']['audit_log'] = [audit]
    expected['tables']['sqlite_sequence'] = [{'name': 'audit_log', 'seq': 1}]
    if not same(final, expected):
        deviations.append('additional_or_missing_domain_changes')
    if any(not same(value, initial) and not same(value, expected) for value in values):
        deviations.append('intermediate_unexpected_domain_change')
    if any(same(values[index], initial) for index in range(changed[0], len(values))):
        deviations.append('domain_effect_reverted')
    seen = service.get('seen_contexts', []) if isinstance(service, dict) else []
    expected_before = ['A2A_USER_' + context_id, context_id, invocation, False]
    expected_after = ['A2A_USER_' + context_id, context_id, invocation, True]
    before_indices = [index for index, value in enumerate(seen) if same(value, expected_before)]
    after_indices = [index for index, value in enumerate(seen) if same(value, expected_after)]
    report['approval_observed'] = bool(before_indices and after_indices
                                       and min(before_indices) < max(after_indices))
    if not report['approval_observed']:
        deviations.append('matching_guarded_approval_not_observed')
    report['effect_matches_contract'] = not deviations
    if not deviations:
        report['classification'] = 'expected_single_effect'
    return report


def _task_views(reply):
    """Read canonical and legacy task-bearing results, retaining their bindings."""
    if not isinstance(reply, dict) or reply.get('jsonrpc') != '2.0' or 'error' in reply:
        return []
    result = reply.get('result')
    if not isinstance(result, dict):
        return []
    values = []
    if 'status' in result and ('id' in result or 'taskId' in result):
        values.append(result)
    for key in ('task', 'statusUpdate', 'artifactUpdate'):
        if isinstance(result.get(key), dict):
            values.append(result[key])
    return [{'task_id': value.get('taskId', value.get('id')), 'context_id': value.get('contextId'),
             'state': value.get('status', {}).get('state'), 'value': value} for value in values]


def _confirmation_calls(view):
    status = view['value'].get('status', {})
    message = status.get('message', {}) if isinstance(status, dict) else {}
    return [part['data'] for part in message.get('parts', []) if isinstance(part, dict)
            and part.get('metadata', {}).get('adk_type') == 'function_call'
            and isinstance(part.get('data'), dict)
            and part['data'].get('name') == 'adk_request_confirmation']


def _state_name(value):
    return value.removeprefix('TASK_STATE_').lower().replace('-', '_') if isinstance(value, str) else None


def _texts(value):
    if isinstance(value, list):
        return [text for item in value for text in _texts(item)]
    if isinstance(value, dict):
        return ([value['text']] if type(value.get('text')) is str else []) + [
            text for key, item in value.items() if key != 'text' for text in _texts(item)]
    return []


def check_service(service_dir, seed):
    """Classify every retained ASGI attempt, using only evaluator-final for final origin truth."""
    report = {'schema_version': 'agentops-bridge-service-check/1', 'valid': False,
              'complete': False, 'strict_success': False, 'validation_errors': [],
              'observation_gaps': [], 'policy_deviations': [], 'original': None,
              'confirmation': None, 'continuation_attempted': False,
              'approval_representation': None, 'final_state': None,
              'task_completed': False, 'effect': None, 'rpc_outcomes': [],
              'claim_limit': 'Bounded captured attempts only; no whole-interface non-support or C1 claim'}
    errors, gaps, deviations = (report[key] for key in
                                ('validation_errors', 'observation_gaps', 'policy_deviations'))
    exchanges = []
    try:
        service = decode_json((service_dir / 'service-result.json').read_bytes())
        require(service.get('schema_version') == 'agentops-http-service/1'
                and service.get('observer_version') == 3, 'Bridge service observer schema')
        ready = decode_json((service_dir / 'service-ready.json').read_bytes())
        port = ready['port']
        require(type(port) is int and 1024 <= port <= 65535, 'Service listener port')
        directories = sorted((service_dir / 'wire').iterdir())
        require(all(path.is_dir() and not path.is_symlink() and path.name == f'{index:06d}'
                    for index, path in enumerate(directories, 1)), 'Contiguous ASGI directory enumeration')
        require(type(service.get('asgi_requests')) is int
                and service['asgi_requests'] == len(directories) <= 256, 'Complete ASGI request count')
        for index, directory in enumerate(directories, 1):
            exchanges.append(parse_asgi_exchange(directory, index))
        terminal_boundaries = []
        for filename in ('final.snapshot.json', 'terminal.snapshot.json'):
            path = service_dir / filename
            if path.is_file():
                boundary = decode_json(path.read_bytes())
                require(boundary['database']['path'] == 'state/incidents.db'
                        and boundary['database']['path_base'] == 'run', 'Final isolated snapshot path')
                db_value(boundary['database'])
                terminal_boundaries.append(boundary)
            else:
                gaps.append(filename.removesuffix('.json') + '_missing')
        if terminal_boundaries:
            require(all(type(row.get('monotonic_ns')) is int for row in terminal_boundaries), 'Final snapshot clocks')
            if exchanges and min(row['monotonic_ns'] for row in terminal_boundaries) <= max(
                    exchange['after']['monotonic_ns'] for exchange in exchanges):
                deviations.append('final_domain_snapshot_precedes_wire_completion')
            if len(terminal_boundaries) == 2:
                require(terminal_boundaries[0]['monotonic_ns'] < terminal_boundaries[1]['monotonic_ns'],
                        'Final and terminal snapshot order')
                require(at_utc(service['finished_at_utc']) <= at_utc(terminal_boundaries[1]['observed_at_utc']),
                        'Terminal snapshot follows stopped service')
                if not same(db_value(terminal_boundaries[0]['database']), db_value(terminal_boundaries[1]['database'])):
                    deviations.append('domain_changed_during_shutdown')
        report['asgi_requests'] = len(exchanges)
        report['model_double_calls'] = service.get('model_double_calls')
        require(type(service.get('seen_contexts')) is list, 'Guarded-context observations')
        if not exchanges:
            gaps.append('no_http_observations')
        if service.get('status') != 'stopped' or service.get('watchdog_expired'):
            gaps.append('service_did_not_stop_cleanly')
        if service.get('capture_errors'):
            gaps.append('service_reported_capture_errors')
        if service.get('network_errors'):
            deviations.append('unexpected_service_network_operation')
        try:
            report['socket_policy'] = check_policy(service['socket_policy'], listener_port=port)
        except (ValueError, KeyError, TypeError) as error:
            deviations.append('socket_policy: ' + str(error))
        require(same(service.get('network_errors'), service['socket_policy'].get('unexpected')),
                'Service/socket network record binding')
        for exchange in exchanges:
            record, request = exchange['record'], exchange['request']
            if not exchange['complete'] or record.get('error') or record.get('snapshot_error'):
                gaps.append('partial_http_exchange:' + str(record['sequence']))
            if record['method'] not in ('GET', 'POST') or record['path'] not in ('/', '/.well-known/agent-card.json'):
                deviations.append('unplanned_http_method_or_path:' + str(record['sequence']))
            if exchange['query']:
                deviations.append('unplanned_query_string:' + str(record['sequence']))
            for problem in exchange['protocol_errors']:
                gaps.append('protocol:' + str(record['sequence']) + ':' + problem)
            if isinstance(request, dict):
                report['rpc_outcomes'].append({'sequence': record['sequence'], 'method': request.get('method'),
                    'id': request.get('id'), 'http_status': record['response_status'],
                    'errors': [reply['error'] for reply in exchange['responses']
                               if isinstance(reply, dict) and 'error' in reply]})
        sends = [exchange for exchange in exchanges if isinstance(exchange['request'], dict)
                 and exchange['request'].get('method') in
                 ('SendMessage', 'SendStreamingMessage', 'message/send', 'message/stream')]
        report['send_profiles'] = [{'sequence': exchange['record']['sequence'],
            'rpc_id': exchange['request'].get('id'),
            'method': exchange['request'].get('method'),
            'version_headers': exchange['request_headers'].get('a2a-version', []),
            'configuration_present': 'configuration' in exchange['request'].get('params', {}),
            'configuration': exchange['request'].get('params', {}).get('configuration'),
            'message': exchange['request'].get('params', {}).get('message')}
            for exchange in sends]
        if not sends:
            gaps.append('no_initial_send')
        else:
            first = sends[0]
            message = first['request'].get('params', {}).get('message', {})
            parts = message.get('parts', [])
            if not (len(parts) == 1 and parts[0].get('text') == START_TEXT and not message.get('taskId')):
                deviations.append('initial_message_differs_from_fixed_start')
            views = [view for reply in first['responses'] for view in _task_views(reply)]
            original = next(({'task_id': view['task_id'], 'context_id': view['context_id']}
                             for view in views if all(type(view[key]) is str and view[key]
                                                     for key in ('task_id', 'context_id'))), None)
            report['original'] = original
            if original is None:
                gaps.append('original_task_binding_not_observed')
            else:
                for view in views:
                    if not all(view[key] == original[key] for key in ('task_id', 'context_id')):
                        deviations.append('initial_stream_contains_other_task')
                continuations = sends[1:]
                report['continuation_attempted'] = bool(continuations)
                if len(continuations) > 1:
                    deviations.append('more_than_one_continuation_send')
                continuation = continuations[0] if continuations else None
                calls = []
                for exchange in exchanges:
                    if continuation is not None and exchange['record']['sequence'] >= continuation['record']['sequence']:
                        continue
                    for reply in exchange['responses']:
                        for view in _task_views(reply):
                            if all(view[key] == original[key] for key in ('task_id', 'context_id')):
                                for call in _confirmation_calls(view):
                                    if not any(same(call, known) for known in calls):
                                        calls.append(call)
                if len(calls) == 1 and type(calls[0].get('id')) is str and calls[0]['id']:
                    report['confirmation'] = calls[0]
                    if not same(calls[0].get('args', {}).get('originalFunctionCall'), {
                            'id': 'restart-inventory-call', 'name': 'restart_service', 'args': {'name': 'inventory'}}):
                        deviations.append('origin_confirmation_names_other_action')
                else:
                    gaps.append('unique_origin_confirmation_not_observed')
                confirmation_boundary = None
                if continuation is not None:
                    confirmation_boundary = {'started_at_utc': continuation['record']['started_at_utc'],
                                             'before_monotonic_ns': continuation['before']['monotonic_ns']}
                    report['continuation_sequence'] = continuation['record']['sequence']
                    message = continuation['request'].get('params', {}).get('message', {})
                    if message.get('taskId') != original['task_id'] or message.get('contextId') != original['context_id']:
                        deviations.append('continuation_original_binding_mismatch')
                    parts = message.get('parts', [])
                    if len(parts) == 1 and isinstance(parts[0], dict):
                        part = parts[0]
                        expected = None if report['confirmation'] is None else {
                            'id': report['confirmation']['id'], 'name': 'adk_request_confirmation',
                            'response': {'confirmed': True, 'payload': {'rationale': RATIONALE}}}
                        if isinstance(part.get('data'), dict):
                            report['approval_representation'] = 'data'
                            if expected is None or not same(part['data'], expected) or part.get('metadata') != {'adk_type': 'function_response'}:
                                deviations.append('structured_confirmation_mismatch')
                        elif type(part.get('text')) is str:
                            report['approval_representation'] = 'literal_text'
                            if part['text'] != LITERAL_CONFIRMATION:
                                try:
                                    value = decode_json(part['text'])
                                    require(expected is not None and same(value, expected), 'Text confirmation object')
                                    report['approval_representation'] = 'json_text'
                                except (ValueError, TypeError):
                                    deviations.append('text_confirmation_differs_from_fixed_inputs')
                        else:
                            deviations.append('unplanned_confirmation_part')
                    else:
                        deviations.append('unplanned_confirmation_parts')
                boundaries = [exchange[key] for exchange in exchanges for key in ('before', 'after')] + terminal_boundaries
                report['effect'] = classify_effect(seed, boundaries, original, confirmation_boundary, service)
                finals = [exchange for exchange in exchanges if isinstance(exchange['request'], dict)
                          and exchange['request'].get('id') == 'evaluator-final']
                if len(finals) != 1:
                    gaps.append('one_evaluator_final_read_not_observed')
                else:
                    final = finals[0]
                    report['evaluator_final_started_at_utc'] = final['record']['started_at_utc']
                    if final['request'].get('method') != 'GetTask' or final['request'].get('params') != {'id': original['task_id']}:
                        deviations.append('evaluator_read_targets_other_task')
                    final_views = [view for reply in final['responses'] for view in _task_views(reply)
                                   if view['state'] is not None]
                    if len(final_views) != 1:
                        gaps.append('authoritative_final_task_not_observed')
                    else:
                        view = final_views[0]
                        if not all(view[key] == original[key] for key in ('task_id', 'context_id')):
                            deviations.append('final_original_binding_mismatch')
                        report['final_state'] = _state_name(view['state'])
                        report['task_completed'] = report['final_state'] == 'completed'
                        report['final_text'] = _texts(view['value'])
                    if continuation is not None and final['record']['sequence'] <= continuation['record']['sequence']:
                        deviations.append('final_read_precedes_continuation')
        if report['effect'] is None and exchanges:
            boundaries = [exchange[key] for exchange in exchanges for key in ('before', 'after')] + terminal_boundaries
            report['effect'] = classify_effect(seed, boundaries, report['original'], None, service)
    except FileNotFoundError as error:
        gaps.append('missing_evidence_file:' + Path(error.filename).name)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError, UnicodeError) as error:
        errors.append(type(error).__name__ + ': ' + str(error))
    report['valid'] = not errors
    report['complete'] = report['valid'] and not gaps
    report['strict_success'] = bool(report['complete'] and not deviations and report['task_completed']
                                    and report['effect'] and report['effect']['effect_matches_contract'])
    return report


def _raw_entity(value):
    require(type(value) is dict, 'Captured entity record')
    raw = base64.b64decode(value['base64'], validate=True)
    require(type(value.get('bytes')) is int and value['bytes'] == len(raw)
            and value.get('sha256') == hashlib.sha256(raw).hexdigest(), 'Captured entity bytes/hash')
    return raw


def _select(value, path):
    require(type(path) is list, 'Public provenance path')
    for key in path:
        if type(key) is int:
            require(type(value) is list and 0 <= key < len(value), 'Public provenance list index')
        else:
            require(type(key) is str and type(value) is dict and key in value, 'Public provenance object key')
        value = value[key]
    return value


def resolve_public_source(source, events):
    require(type(source) is dict and type(source.get('seq')) is int, 'Public provenance event')
    event = events.get(source['seq'])
    require(event is not None and event.get('kind') == 'mcp-message'
            and event.get('direction') == 'bridge_to_client', 'Binding source is a received MCP message')
    value = _select(decode_json(_raw_entity(event['raw'])), source['path'])
    if 'decode' in source:
        require(source['decode'] == 'json-text' and type(value) is str, 'Declared public JSON text')
        value = _select(decode_json(value), source['decoded_path'])
    else:
        require('decoded_path' not in source, 'Undeclared public text decoding')
    return value


def check_client(client_dir, service_report=None):
    """Verify public-MCP provenance and fixed legal inputs, independently of effects."""
    report = {'schema_version': 'agentops-bridge-client-check/1', 'valid': False, 'complete': False,
              'validation_errors': [], 'observation_gaps': [], 'policy_deviations': [],
              'public_bindings': {}, 'answer_attempted': False, 'answer_representation': None}
    errors, gaps, deviations = (report[key] for key in
                                ('validation_errors', 'observation_gaps', 'policy_deviations'))
    try:
        config = decode_json((client_dir / 'config.json').read_bytes())
        result = decode_json((client_dir / 'result.json').read_bytes())
        require(config.get('schema_version') == 'agentops-bridge-client-config/1'
                and result.get('schema_version') == 'agentops-bridge-client-result/1', 'Client envelope schemas')
        arm = config.get('arm')
        require(arm in ('B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7') and result.get('arm') == arm, 'Client arm binding')
        require(config.get('rationale') == RATIONALE, 'Frozen rationale')
        report['arm'], report['status'] = arm, result.get('status')
        require(result.get('strict_success') is None, 'Client must not promote its own outcome')
        raw_journal = (client_dir / 'mcp.jsonl').read_bytes()
        lines = raw_journal.splitlines()
        if raw_journal and not raw_journal.endswith(b'\n'):
            gaps.append('truncated_client_journal')
            lines = lines[:-1]
        rows = [decode_json(line) for line in lines]
        events, messages, binding_rows, binding_events = {}, {}, [], {}
        previous_tick = -1
        for index, event in enumerate(rows, 1):
            require(event.get('schema_version') == 'agentops-bridge-client-event/1'
                    and event.get('seq') == index and type(event.get('seq')) is int, 'Client event sequence/schema')
            tick = event.get('monotonic_ns')
            require(type(tick) is str and tick.isdigit() and int(tick) > previous_tick, 'Client monotonic clock')
            previous_tick = int(tick)
            at_utc(event['at_utc'])
            events[index] = event
            if 'raw' in event:
                _raw_entity(event['raw'])
            if event['kind'] == 'mcp-message':
                require(event.get('direction') in ('client_to_bridge', 'bridge_to_client'), 'MCP direction')
                raw = _raw_entity(event['raw'])
                message = decode_json(raw)
                require(type(message) is dict and message.get('jsonrpc') == '2.0', 'MCP JSON-RPC entity')
                require(same(event.get('parsed'), message), 'MCP convenience JSON differs from bytes')
                framing = event.get('framing')
                if framing == 'stdio-line':
                    require(raw.endswith(b'\n') and raw.count(b'\n') == 1, 'Complete single MCP stdio line')
                else:
                    require(framing in ('http-body', 'sse-data-derived'), 'Known MCP entity framing')
                    source = events.get(event.get('source_http_seq'))
                    expected_kind = 'http-request' if event['direction'] == 'client_to_bridge' else 'http-response'
                    require(source is not None and source['kind'] == expected_kind
                            and source.get('operation_id') == event.get('operation_id'), 'MCP HTTP source linkage')
                    parent_raw = _raw_entity(source['raw'])
                    if framing == 'http-body':
                        require(raw == parent_raw, 'MCP HTTP entity bytes')
                    else:
                        require(source.get('complete') is True, 'Derived SSE message from complete response')
                        require(raw in _sse_payloads(parent_raw),
                                'MCP SSE message derived from received body')
                messages[index] = message
            elif event['kind'] == 'public-binding':
                name, value, source = (event.get(key) for key in ('name', 'value', 'source'))
                require(type(name) is str and bool(name) and type(value) is str and bool(value), 'Public binding scalar')
                require(source['seq'] < index and same(resolve_public_source(source, events), value),
                        'Public binding equals earlier received value')
                if name in ('confirmation_call_id', 'confirmation_call_name'):
                    prior = events[source['seq']]
                    field = 'id' if name == 'confirmation_call_id' else 'name'
                    if arm in ('B1', 'B2'):
                        path = source['path']
                        require(prior.get('phase') == 'pending_origin_get' and len(path) == 4
                                and path[:2] == ['result', 'content'] and type(path[2]) is int and path[3] == 'text'
                                and source.get('decode') == 'json-text' and source.get('decoded_path') == [field],
                                'Amir confirmation binding from pending tagged public content')
                        block = _select(messages[source['seq']], path[:-1])
                        meta = block.get('_meta', {}).get('io.github.amirk-s/a2a', {})
                        require(block.get('type') == 'text' and meta.get('partKind') == 'data'
                                and meta.get('metadata', {}).get('adk_type') == 'function_call',
                                'Amir public confirmation data tag')
                    elif arm in ('B5', 'B6', 'B7'):
                        require(prior.get('phase') == 'public_raw_get', 'Raw confirmation from permitted public read')
                        body = messages[source['seq']].get('result', {})
                        if isinstance(body.get('structuredContent'), dict):
                            root = body['structuredContent']
                            require(source['path'][:2] == ['result', 'structuredContent'] and 'decode' not in source,
                                    'Raw confirmation structured source')
                            path = source['path'][2:]
                        else:
                            root = decode_json(body['content'][0]['text'])
                            require(source['path'] == ['result', 'content', 0, 'text'] and source.get('decode') == 'json-text',
                                    'Raw confirmation JSON-text source')
                            path = source.get('decoded_path', [])
                        require(len(path) == 7 and path[:4] == ['result', 'status', 'message', 'parts']
                                and type(path[4]) is int and path[5:] == ['data', field], 'Raw confirmation data source path')
                        raw_task = root.get('result', {})
                        part = _select(root, path[:5])
                        require(raw_task.get('id') == report['public_bindings'].get('task_id')
                                and raw_task.get('contextId') == report['public_bindings'].get('context_id')
                                and part.get('metadata', {}).get('adk_type') == 'function_call', 'Raw public original confirmation association')
                    else:
                        deviations.append('unplanned_confirmation_binding_for_arm')
                if name in report['public_bindings']:
                    require(report['public_bindings'][name] == value, 'Public binding changed')
                report['public_bindings'][name] = value
                binding_events[name] = event
                binding_rows.append({'name': name, 'value': value, 'source': source})
            elif event['kind'] == 'http-response' and event.get('complete') is not True:
                gaps.append('partial_mcp_http_response:' + str(index))
            elif event['kind'] in ('mcp-parse-error', 'stdio-trailing-bytes', 'child-error'):
                gaps.append(event['kind'] + ':' + str(index))
        retained_bindings = result.get('bindings', binding_rows if result.get('status') == 'client_failed' else None)
        if 'truncated_client_journal' in gaps and type(retained_bindings) is list:
            retained_bindings = retained_bindings[:len(binding_rows)]
        require(retained_bindings == binding_rows,
                'Terminal public bindings equal journal')
        if arm not in ('B1', 'B2', 'B3'):
            chunk_bytes = b''.join(_raw_entity(row['raw']) for row in rows
                                   if row['kind'] == 'stdio-chunk' and row.get('direction') == 'bridge_to_client')
            interpreted_bytes = b''.join(_raw_entity(row['raw']) for row in rows
                if row['kind'] == 'mcp-message' and row.get('direction') == 'bridge_to_client'
                or row['kind'] in ('mcp-parse-error', 'stdio-trailing-bytes'))
            require(chunk_bytes.startswith(interpreted_bytes) if 'truncated_client_journal' in gaps else
                    chunk_bytes == interpreted_bytes, 'Complete bridge stdout byte coverage')
        operations = [row for row in rows if row['kind'] == 'operation-start']
        require(len({row['operation_id'] for row in operations}) == len(operations), 'Unique operation identifiers')
        for operation in operations:
            terminal = [row for row in rows if row['kind'] in ('operation-complete', 'operation-error')
                        and row.get('operation_id') == operation['operation_id']]
            if len(terminal) != 1:
                gaps.append('missing_terminal_operation:' + str(operation['operation_id']))
                continue
            require(terminal[0]['seq'] > operation['seq'], 'Operation terminal order')
            if terminal[0]['kind'] == 'operation-error':
                require(type(terminal[0].get('error')) is str and bool(terminal[0]['error']), 'Retained operation error')
            else:
                response_seq = terminal[0].get('reply_seq')
                if operation.get('notification'):
                    require(response_seq is None, 'Notification has no fabricated reply')
                else:
                    response = events.get(response_seq)
                    require(response is not None and response.get('direction') == 'bridge_to_client'
                            and response_seq < terminal[0]['seq']
                            and messages[response_seq].get('id') == operation['operation_id'],
                            'Completed operation binds received RPC reply')
        outgoing = [(events[seq], message) for seq, message in messages.items()
                    if events[seq]['direction'] == 'client_to_bridge']
        operation_by_id = {row['operation_id']: row for row in operations}
        known_phases = {'initialize': ('initialize', None), 'initialized': ('notifications/initialized', None),
            'discover_profile': ('server/discover', None), 'discover_full_tools': ('tools/list', None),
            'discover_agent': ('tools/call', 'a2a_discover_agent'),
            'initial_typed_send': ('tools/call', 'a2a_send_message'),
            'pending_origin_get': ('tools/call', 'a2a_get_task'),
            'final_origin_get': ('tools/call', 'a2a_get_task'),
            'public_raw_get': ('tools/call', 'a2a_request'), 'pending_tasks_form': ('tasks/get', None),
            'post_answer_tasks_get': ('tasks/get', None),
            'typed_answer': ('tools/call', 'a2a_send_message'), 'tasks_answer': ('tasks/update', None),
            'mrtr_answer': ('tools/call', 'a2a_send_message'), 'raw_answer': ('tools/call', 'a2a_request')}
        arm_phases = {'discover_profile': ('B1', 'B2', 'B3'), 'discover_agent': ('B4', 'B5', 'B6', 'B7'),
            'initialize': ('B4', 'B5', 'B6', 'B7'), 'initialized': ('B4', 'B5', 'B6', 'B7'),
            'public_raw_get': ('B5', 'B6', 'B7'), 'raw_answer': ('B5', 'B6', 'B7'),
            'typed_answer': ('B1', 'B4'), 'tasks_answer': ('B2',), 'pending_tasks_form': ('B2',),
            'post_answer_tasks_get': ('B2',), 'mrtr_answer': ('B3',)}
        starts = []
        for event, message in outgoing:
            phase = event.get('phase')
            operation = operation_by_id.get(event.get('operation_id'))
            require(operation is not None and operation['seq'] < event['seq']
                    and operation.get('phase') == phase and operation.get('method') == message.get('method'),
                    'Outbound request binds earlier operation')
            require('id' not in message if operation.get('notification') else
                    message.get('id') == operation['operation_id'], 'Outbound request identifier')
            if phase not in known_phases:
                deviations.append('unplanned_public_operation:' + str(phase))
                continue
            method, tool = known_phases[phase]
            params = message.get('params', {})
            if phase in arm_phases and arm not in arm_phases[phase]:
                deviations.append('public_operation_outside_arm:' + phase)
            if message.get('method') != method or tool is not None and params.get('name') != tool:
                deviations.append('public_operation_method_mismatch:' + phase)
            if arm in ('B1', 'B2', 'B3'):
                capabilities = {'extensions': {'io.modelcontextprotocol/tasks': {}}} if arm == 'B2' else {
                    'elicitation': {}} if arm == 'B3' else {}
                expected_meta = {'io.modelcontextprotocol/protocolVersion': '2026-07-28',
                    'io.modelcontextprotocol/clientCapabilities': capabilities,
                    'io.modelcontextprotocol/clientInfo': {'name': 'AgentOps-public-control', 'version': '1.0.0'}}
                http = events.get(event.get('source_http_seq'), {})
                headers = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream',
                           'MCP-Protocol-Version': '2026-07-28', 'Mcp-Method': method}
                if method == 'tools/call':
                    headers['Mcp-Name'] = params.get('name')
                elif method.startswith('tasks/'):
                    headers['Mcp-Name'] = params.get('taskId')
                if (params.get('_meta') != expected_meta or http.get('headers') != headers
                        or http.get('url') != config.get('amir_endpoint') or http.get('method') != 'POST'):
                    deviations.append('amir_negotiation_or_http_profile_mismatch')
            if phase in ('pending_origin_get', 'final_origin_get'):
                binding = 'task_handle' if arm in ('B1', 'B2', 'B3') else 'task_id'
                expected = {'agent': config['agent_alias'], 'taskHandle': report['public_bindings'].get(binding),
                            'historyLength': 100} if binding == 'task_handle' else {
                            'task_id': report['public_bindings'].get(binding), 'history_length': 100, 'refresh': True}
                if params.get('arguments') != expected:
                    deviations.append('public_origin_read_argument_mismatch')
                if binding not in binding_events or binding_events[binding]['seq'] >= event['seq']:
                    deviations.append('origin_read_uses_unobserved_binding:' + binding)
            if phase in ('pending_tasks_form', 'post_answer_tasks_get') and params.get('taskId') != report['public_bindings'].get('task_handle'):
                deviations.append('tasks_read_uses_other_handle')
            if phase == 'public_raw_get' and params.get('arguments') != {
                    'url': config['agent_base_url'], 'method': 'GetTask',
                    'params': {'id': report['public_bindings'].get('task_id'), 'historyLength': 100}}:
                deviations.append('public_raw_read_argument_mismatch')
            if phase == 'initial_typed_send':
                starts.append(event)
                expected = ({'agent': config['agent_alias'], 'text': START_TEXT} if arm in ('B1', 'B2', 'B3') else
                            {'url': config['agent_base_url'], 'text': START_TEXT})
                if params.get('arguments') != expected:
                    deviations.append('public_initial_arguments_differ')
        if len(starts) != 1:
            gaps.append('one_public_initial_send_not_observed')
        answers = [(event, message) for event, message in outgoing
                   if event.get('phase') in ('typed_answer', 'tasks_answer', 'mrtr_answer', 'raw_answer')]
        report['answer_attempted'] = bool(answers)
        if len(answers) > 1:
            deviations.append('more_than_one_public_answer')
        if bool(result.get('answer_sent', False)) != bool(answers):
            gaps.append('declared_answer_not_fully_observed')
        bindings = report['public_bindings']
        if service_report and service_report.get('original'):
            for key in ('task_id', 'context_id'):
                if key in bindings and bindings[key] != service_report['original'][key]:
                    deviations.append('public_original_' + key + '_mismatch')
            call = service_report.get('confirmation')
            if 'confirmation_call_id' in bindings and (call is None or bindings['confirmation_call_id'] != call.get('id')):
                deviations.append('public_confirmation_differs_from_original')
        if answers:
            answer_event, answer = answers[0]
            params = answer.get('params', {})
            arguments = params.get('arguments', {})
            used_names = []
            text = None
            if arm in ('B1', 'B4'):
                require(answer.get('method') == 'tools/call' and params.get('name') == 'a2a_send_message', 'Typed answer tool')
                used_names = ['task_handle', 'context_handle'] if arm == 'B1' else ['task_id', 'context_id']
                expected = ({'agent': config['agent_alias'], 'taskHandle': bindings.get('task_handle'),
                             'contextHandle': bindings.get('context_handle')} if arm == 'B1' else
                            {'url': config['agent_base_url'], 'task_id': bindings.get('task_id'),
                             'context_id': bindings.get('context_id')})
                text = arguments.get('text')
                if not same(arguments, dict(expected, text=text)):
                    deviations.append('typed_answer_argument_mismatch')
            elif arm in ('B2', 'B3'):
                form = result.get('form', {})
                form_event = events.get(form.get('source_seq'))
                require(form_event is not None and form_event.get('direction') == 'bridge_to_client'
                        and form_event['seq'] < answer_event['seq'], 'Earlier received public form')
                body = messages[form_event['seq']].get('result', {})
                requests = body.get('inputRequests', {})
                require(type(requests) is dict and len(requests) == 1, 'One public input form')
                key, request = next(iter(requests.items()))
                properties = request.get('params', {}).get('requestedSchema', {}).get('properties', {})
                require(request.get('method') == 'elicitation/create' and request.get('params', {}).get('mode') == 'form'
                        and type(properties) is dict and len(properties) == 1, 'Public form shape')
                field, shape = next(iter(properties.items()))
                require(shape.get('type') == 'string' and form.get('request_key') == key and form.get('field') == field,
                        'Form response key/field binding')
                responses = params.get('inputResponses', {})
                text = responses.get(key, {}).get('content', {}).get(field)
                if not same(responses, {key: {'action': 'accept', 'content': {field: text}}}):
                    deviations.append('public_form_acceptance_mismatch')
                if arm == 'B2':
                    used_names = ['task_handle']
                    if answer.get('method') != 'tasks/update' or params.get('taskId') != bindings.get('task_handle'):
                        deviations.append('tasks_answer_binding_mismatch')
                else:
                    used_names = ['request_state']
                    if (answer.get('method') != 'tools/call' or params.get('name') != 'a2a_send_message'
                            or params.get('requestState') != bindings.get('request_state')
                            or arguments != {'agent': config['agent_alias'], 'text': START_TEXT}):
                        deviations.append('mrtr_replay_binding_mismatch')
            else:
                used_names = ['task_id', 'context_id', 'confirmation_call_id', 'confirmation_call_name']
                require(answer.get('method') == 'tools/call' and params.get('name') == 'a2a_request', 'Raw answer tool')
                data = {'id': bindings.get('confirmation_call_id'), 'name': 'adk_request_confirmation',
                        'response': {'confirmed': True, 'payload': {'rationale': RATIONALE}}}
                expected = {'url': config['agent_base_url'], 'method': 'SendMessage', 'params': {'message': {
                    'messageId': 'agentops-public-confirmation', 'role': 'ROLE_USER',
                    'taskId': bindings.get('task_id'), 'contextId': bindings.get('context_id'),
                    'parts': [{'data': data, 'metadata': {'adk_type': 'function_response'}}]}}}
                if not same(arguments, expected):
                    deviations.append('raw_answer_argument_mismatch')
                report['answer_representation'] = 'data'
            if text is not None:
                call_id = bindings.get('confirmation_call_id')
                if call_id is None:
                    if text != LITERAL_CONFIRMATION:
                        deviations.append('unbound_text_differs_from_literal_fallback')
                    report['answer_representation'] = 'literal_text'
                else:
                    used_names.extend(['confirmation_call_id', 'confirmation_call_name'])
                    data = {'id': call_id, 'name': 'adk_request_confirmation',
                            'response': {'confirmed': True, 'payload': {'rationale': RATIONALE}}}
                    expected_text = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
                    if text != expected_text:
                        deviations.append('text_differs_from_canonical_public_confirmation')
                    report['answer_representation'] = 'json_text'
            elif arm in ('B1', 'B2', 'B3', 'B4'):
                deviations.append('text_answer_missing')
            for name in used_names:
                if name not in binding_events or binding_events[name]['seq'] >= answer_event['seq']:
                    deviations.append('answer_uses_unobserved_binding:' + name)
            if 'confirmation_call_name' in used_names and bindings.get('confirmation_call_name') != 'adk_request_confirmation':
                deviations.append('wrong_public_confirmation_name')
        elif result.get('status') in ('public_binding_not_observed', 'public_task_binding_not_observed',
                                      'no_public_mrtr_continuation', 'pending_observation_bound_reached',
                                      'pending_read_error', 'initial_state_not_pending', 'client_failed'):
            gaps.append('continuation_not_attempted:' + str(result['status']))
        else:
            gaps.append('no_public_continuation')
        child = result.get('child')
        if not isinstance(child, dict) or child.get('clean_exit') is not True:
            gaps.append('bridge_child_not_cleanly_exited')
        else:
            cleanup_rows = [row for row in rows if row['kind'] == 'child-cleanup']
            exit_rows = [row for row in rows if row['kind'] == 'child-exit']
            if not cleanup_rows or not exit_rows:
                gaps.append('child_exit_or_cleanup_receipt_missing')
            else:
                require(len(cleanup_rows) == len(exit_rows) == 1, 'Child exit and cleanup receipts')
            require(len(cleanup_rows) <= 1 and len(exit_rows) <= 1, 'Unique child termination receipts')
        if isinstance(child, dict) and child.get('clean_exit') is True and cleanup_rows and exit_rows:
            recorded_cleanup = {key: value for key, value in cleanup_rows[0].items()
                                if key not in ('schema_version', 'seq', 'at_utc', 'monotonic_ns', 'kind')}
            require(same(recorded_cleanup, child), 'Terminal child receipt equals journal')
            require(not child.get('forced_kill') and child.get('exit', {}).get('code') == 0
                    and child.get('exit', {}).get('signal') is None
                    and child['exit'] == {key: exit_rows[0].get(key) for key in ('code', 'signal', 'at_utc')},
                    'Clean exit agrees with observed child termination')
            start_rows = [row for row in rows if row['kind'] == 'child-start']
            if len(start_rows) != 1:
                gaps.append('one_bridge_child_start_not_observed')
            else:
                start = start_rows[0]
                require(type(start.get('pid')) is int and start['pid'] > 0
                        and start['seq'] < exit_rows[0]['seq'] < cleanup_rows[0]['seq'], 'Bridge child lifecycle order')
                require(all(start.get(key) == child.get(key) for key in ('pid', 'command', 'args', 'cwd', 'started_at_utc')),
                        'Bridge child start/cleanup process binding')
                require(all(start.get(key) == config.get('bridge', {}).get(key) for key in ('command', 'args', 'cwd')),
                        'Bridge child matches configured process')
        report['mcp_events'] = len(rows)
        report['public_confirmation_observed'] = 'confirmation_call_id' in bindings
    except FileNotFoundError as error:
        gaps.append('missing_evidence_file:' + Path(error.filename).name)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError, UnicodeError) as error:
        errors.append(type(error).__name__ + ': ' + str(error))
    report['valid'] = not errors
    report['complete'] = report['valid'] and not gaps
    return report


def check_native_client(client_dir, service_report):
    """Bind direct SDK observations and the declared profile to authoritative ASGI bytes."""
    report = {'schema_version': 'agentops-native-profile-client-check/1', 'valid': False,
              'complete': False, 'validation_errors': [], 'observation_gaps': [],
              'policy_deviations': [], 'public_bindings': {}}
    errors, gaps, deviations = (report[key] for key in
                                ('validation_errors', 'observation_gaps', 'policy_deviations'))
    try:
        config = decode_json((client_dir / 'config.json').read_bytes())
        result = decode_json((client_dir / 'result.json').read_bytes())
        require(config.get('schema_version') == 'agentops-native-profile-client-config/1'
                and result.get('schema_version') == 'agentops-native-profile-client-result/1', 'Native client schemas')
        profile, representation = config.get('profile'), config.get('representation')
        require(profile in ('amir-sync', 'amir-stream', 'mg-poll', 'mg-raw-no-header', 'mg-raw-header')
                and representation in ('literal', 'json-text', 'data')
                and result.get('profile') == profile and result.get('representation') == representation,
                'Native profile binding')
        require(not profile.startswith('mg-raw') or representation == 'data', 'Frozen raw representation')
        require(config.get('rationale') == RATIONALE and result.get('strict_success') is None, 'Native scope')
        report.update(profile=profile, representation=representation, status=result.get('status'))
        raw = (client_dir / 'sdk.jsonl').read_bytes()
        lines = raw.splitlines()
        if raw and not raw.endswith(b'\n'):
            gaps.append('truncated_native_journal')
            lines = lines[:-1]
        rows = [decode_json(line) for line in lines]
        events, bindings, binding_events = {}, [], {}
        previous_tick = -1
        pending_call = None
        calls = []
        for index, event in enumerate(rows, 1):
            require(event.get('schema_version') == 'agentops-native-profile-event/1'
                    and type(event.get('seq')) is int and event['seq'] == index, 'Native event sequence/schema')
            tick = event.get('monotonic_ns')
            require(type(tick) is str and tick.isdigit() and int(tick) > previous_tick, 'Native event clock')
            previous_tick = int(tick)
            at_utc(event['at_utc'])
            events[index] = event
            if 'raw' in event:
                raw_entity = _raw_entity(event['raw'])
                if 'parsed' in event:
                    require(same(decode_json(raw_entity), event['parsed']), 'Native raw convenience JSON')
            if event['kind'] == 'public-binding':
                name, value, source = (event.get(key) for key in ('name', 'value', 'source'))
                require(type(name) is str and bool(name) and type(value) is str and bool(value), 'Native binding scalar')
                prior_event = events.get(source.get('seq'))
                require(prior_event is not None and prior_event['seq'] < index and prior_event['kind'] == 'sdk-result'
                        and same(_select(prior_event, source['path']), value), 'Native binding from earlier SDK result')
                if name in ('task_id', 'context_id'):
                    require(prior_event.get('phase') == 'start' and prior_event.get('action') == 'send'
                            and source['path'] == ['value', 'id' if name == 'task_id' else 'contextId'],
                            'Native original binding from initial SDK result')
                elif name in ('confirmation_call_id', 'confirmation_call_name'):
                    path = source['path']
                    require(prior_event.get('phase') == 'get-pending' and prior_event.get('action') == 'get'
                            and len(path) == 8 and path[:4] == ['value', 'status', 'message', 'parts']
                            and type(path[4]) is int and path[4] >= 0
                            and path[5:] == ['content', 'value', 'id' if name == 'confirmation_call_id' else 'name'],
                            'Native confirmation binding from public pending part')
                    part = _select(prior_event, path[:5])
                    require(part.get('metadata', {}).get('adk_type') == 'function_call'
                            and part.get('content', {}).get('$case') == 'data', 'Native public function-call part')
                else:
                    deviations.append('unplanned_native_binding:' + name)
                if name in report['public_bindings']:
                    require(report['public_bindings'][name] == value, 'Native binding changed')
                report['public_bindings'][name] = value
                binding_events[name] = event
                bindings.append({'name': name, 'value': value, 'source': source})
            elif event['kind'] == 'sdk-call':
                if pending_call is not None:
                    gaps.append('native_sdk_call_without_terminal:' + str(pending_call['seq']))
                pending_call = event
                calls.append(event)
            elif event['kind'] in ('sdk-result', 'sdk-error'):
                require(pending_call is not None and all(event.get(key) == pending_call.get(key)
                        for key in ('phase', 'action')), 'Native SDK terminal matches earlier call')
                if event['kind'] == 'sdk-error':
                    require(type(event.get('error')) is str and bool(event['error']), 'Retained native SDK error')
                pending_call = None
            elif event['kind'] == 'raw-http-response' and event.get('complete') is not True:
                gaps.append('partial_native_raw_response')
        if pending_call is not None:
            gaps.append('native_sdk_call_without_terminal:' + str(pending_call['seq']))
        retained_bindings = result.get('bindings', bindings if result.get('status') == 'client_failed' else None)
        if 'truncated_native_journal' in gaps and type(retained_bindings) is list:
            retained_bindings = retained_bindings[:len(bindings)]
        require(retained_bindings == bindings,
                'Native terminal bindings equal journal')
        original, call = service_report.get('original'), service_report.get('confirmation')
        for key in ('task_id', 'context_id'):
            if key in report['public_bindings'] and (original is None or report['public_bindings'][key] != original[key]):
                deviations.append('native_public_' + key + '_differs_from_wire')
        if 'confirmation_call_id' in report['public_bindings'] and (
                call is None or report['public_bindings']['confirmation_call_id'] != call.get('id')):
            deviations.append('native_confirmation_differs_from_wire')
        allowed = {'start': 'send', 'get-pending': 'get', 'get-completed': 'get',
                   'resume-raw' if profile.startswith('mg-raw') else 'resume': 'rawSend' if profile.startswith('mg-raw') else 'send'}
        for event in calls:
            if allowed.get(event.get('phase')) != event.get('action'):
                deviations.append('unplanned_native_sdk_call:' + str(event.get('phase')))
            if event.get('action') == 'get' and event.get('arguments') != report['public_bindings'].get('task_id'):
                deviations.append('native_get_uses_other_task')
        starts = [event for event in calls if event.get('phase') == 'start']
        if len(starts) != 1:
            gaps.append('one_native_initial_call_not_observed')
        resumes = [event for event in calls if event.get('phase') in ('resume', 'resume-raw')]
        if result.get('answer_attempts', len(resumes) if result.get('status') == 'client_failed' else None) != len(resumes):
            gaps.append('native_answer_count_differs_from_journal')
        if len(resumes) != 1:
            gaps.append('one_native_continuation_not_observed')
        else:
            resume = resumes[0]
            for name in ('task_id', 'context_id', 'confirmation_call_id', 'confirmation_call_name'):
                if name not in binding_events or binding_events[name]['seq'] >= resume['seq']:
                    deviations.append('native_resume_uses_unobserved_binding:' + name)
            if report['public_bindings'].get('confirmation_call_name') != 'adk_request_confirmation':
                deviations.append('native_confirmation_name_mismatch')
            call_bindings = [binding_events.get(name, {}).get('source', {})
                             for name in ('confirmation_call_id', 'confirmation_call_name')]
            if call_bindings[0].get('seq') != call_bindings[1].get('seq') or (
                    call_bindings[0].get('path', [])[:-1] != call_bindings[1].get('path', [])[:-1]):
                deviations.append('native_confirmation_fields_from_different_parts')
            if result.get('public_original') != {key: report['public_bindings'].get(key) for key in ('task_id', 'context_id')}:
                deviations.append('native_result_original_binding_mismatch')
        sends = service_report.get('send_profiles', [])
        if len(sends) != 2:
            gaps.append('two_native_send_requests_not_observed')
        else:
            expected_method = 'SendStreamingMessage' if profile == 'amir-stream' else 'SendMessage'
            for index, send in enumerate(sends):
                if send['method'] != expected_method:
                    deviations.append('native_send_method_mismatch')
                raw_resume = index == 1 and profile.startswith('mg-raw')
                expected_headers = [] if profile == 'mg-raw-no-header' and index == 1 else ['1.0']
                if send['version_headers'] != expected_headers:
                    deviations.append('native_version_header_mismatch')
                expected_configuration = (None if raw_resume else
                    {'acceptedOutputModes': ['text/plain', 'application/json'], 'returnImmediately': True}
                    if profile.startswith('mg-') else {})
                actual_configuration = send.get('configuration')
                if send.get('configuration_present') is not (not raw_resume):
                    deviations.append('native_configuration_presence_mismatch')
                if actual_configuration != expected_configuration:
                    deviations.append('native_polling_configuration_mismatch')
                source_calls = starts if index == 0 else resumes
                if len(source_calls) != 1:
                    continue
                args = source_calls[0].get('arguments')
                bindings = report['public_bindings']
                data = {'id': bindings.get('confirmation_call_id'), 'name': 'adk_request_confirmation',
                        'response': {'confirmed': True, 'payload': {'rationale': RATIONALE}}}
                text = (START_TEXT if index == 0 else LITERAL_CONFIRMATION if representation == 'literal'
                        else json.dumps(data, separators=(',', ':'), ensure_ascii=False))
                data_part = index == 1 and representation == 'data'
                native_part = {'content': {'$case': 'data' if data_part else 'text', 'value': data if data_part else text},
                               'filename': '', 'mediaType': '' if data_part else 'text/plain'}
                wire_part = {'data': data, 'metadata': {'adk_type': 'function_response'}} if data_part else {
                    'text': text, 'mediaType': 'text/plain'}
                if data_part:
                    native_part['metadata'] = {'adk_type': 'function_response'}
                arg_message = args.get('params', {}).get('message', {}) if raw_resume and isinstance(args, dict) else args
                message_id = arg_message.get('messageId') if isinstance(arg_message, dict) else None
                if type(message_id) is not str or not message_id:
                    deviations.append('native_message_identifier_missing')
                expected_message = {'messageId': message_id, 'role': 'ROLE_USER', 'parts': [wire_part]}
                if index == 1:
                    expected_message.update(taskId=bindings.get('task_id'), contextId=bindings.get('context_id'))
                if send.get('message') != expected_message:
                    deviations.append('native_wire_message_differs_from_fixed_input')
                if raw_resume:
                    expected_args = {'params': {'message': expected_message},
                                     'version': '1.0' if profile == 'mg-raw-header' else None}
                else:
                    expected_args = dict(expected_message, role=1, parts=[native_part], extensions=[], referenceTaskIds=[],
                                         taskId=bindings.get('task_id') if index else '',
                                         contextId=bindings.get('context_id') if index else '')
                if not same(args, expected_args):
                    deviations.append('native_sdk_arguments_differ_from_fixed_input')
            expected_representation = {'literal': 'literal_text', 'json-text': 'json_text', 'data': 'data'}[representation]
            if service_report.get('approval_representation') != expected_representation:
                deviations.append('native_wire_representation_mismatch')
            if profile.startswith('mg-raw') and len(resumes) == 1:
                raw_requests = [event for event in rows if event['kind'] == 'raw-http-request']
                raw_responses = [event for event in rows if event['kind'] == 'raw-http-response']
                if len(raw_requests) != 1 or len(raw_responses) != 1:
                    gaps.append('one_native_raw_exchange_not_observed')
                else:
                    request, response = raw_requests[0], raw_responses[0]
                    require(resumes[0]['seq'] < request['seq'] < response['seq'], 'Raw native request/response order')
                    request_body = decode_json(_raw_entity(request['raw']))
                    expected_headers = {'content-type': 'application/json'}
                    if profile == 'mg-raw-header':
                        expected_headers['A2A-Version'] = '1.0'
                    if (request.get('method') != 'POST' or request.get('url') != config.get('agent_base_url')
                            or request.get('headers') != expected_headers
                            or request_body != {'jsonrpc': '2.0', 'id': sends[1]['rpc_id'], 'method': 'SendMessage',
                                'params': resumes[0].get('arguments', {}).get('params')}):
                        deviations.append('native_raw_request_differs_from_invocation_or_wire')
        if result.get('status') == 'client_failed':
            gaps.append('native_client_failed')
        report['sdk_events'] = len(rows)
    except FileNotFoundError as error:
        gaps.append('missing_evidence_file:' + Path(error.filename).name)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError, UnicodeError) as error:
        errors.append(type(error).__name__ + ': ' + str(error))
    report['valid'] = not errors
    report['complete'] = report['valid'] and not gaps
    return report


def check_owned_group(receipt, expected_pgid):
    """Validate a retained /proc group inspection; never inspect or signal a process."""
    if receipt is None:
        return False
    require(type(receipt) is dict and receipt.get('schema_version') == 'agentops-owned-process-group/1',
            'Owned process group schema')
    require(type(expected_pgid) is int and expected_pgid > 1 and receipt.get('pgid') == expected_pgid,
            'Owned process group matches launched process')
    for name in ('initially_empty', 'final_empty', 'forced_cleanup'):
        require(type(receipt.get(name)) is bool, 'Explicit group cleanup flag')
    for name in ('members', 'final_members', 'snapshots', 'signals', 'errors'):
        require(type(receipt.get(name)) is list, 'Group cleanup list')
    snapshots = receipt['snapshots']
    ticks = [row.get('monotonic_ns') for row in snapshots]
    require(all(type(tick) is int for tick in ticks) and ticks == sorted(set(ticks)), 'Group snapshot clock order')
    if snapshots:
        require(snapshots[0].get('phase') == 'initial' and snapshots[0].get('members') == receipt['members']
                and snapshots[-1].get('members') == receipt['final_members'], 'Group members bind snapshots')
    require(receipt['forced_cleanup'] is any(row.get('sent') is True for row in receipt['signals']),
            'Forced group cleanup binds sent signals')
    clean = bool(receipt['initially_empty'] and receipt['final_empty'] and not receipt['forced_cleanup']
                 and not receipt['errors'])
    if clean:
        require(len(snapshots) == 1 and snapshots[0].get('errors') == [] and not receipt['members']
                and not receipt['final_members'] and not receipt['signals'], 'Clean group inspection contains no surviving members or signals')
    return clean


def check_case(case_dir, seed):
    """Combine public input, origin task, effects and terminal process evidence."""
    report = {'schema_version': 'agentops-bridge-case-check/1', 'valid': False, 'complete': False,
              'strict_success': False, 'validation_errors': [], 'observation_gaps': [],
              'policy_deviations': [], 'qualified_second_domain': False, 'scientific_gate_credit_added': 0}
    errors, gaps, deviations = (report[key] for key in
                                ('validation_errors', 'observation_gaps', 'policy_deviations'))
    try:
        result = decode_json((case_dir / 'result.json').read_bytes())
        require(result.get('schema_version') == 'agentops-bridge-case-result/1', 'Case result schema')
        report.update(case_id=result.get('case_id'), kind=result.get('kind'), status=result.get('status'))
        if result.get('status') == 'skipped':
            require(type(result.get('reason')) is str and bool(result['reason']), 'Retained skipped-case reason')
            gaps.append('case_not_executed:' + result['reason'])
        else:
            plan = decode_json((case_dir / 'plan.json').read_bytes())
            require(plan.get('schema_version') == 'agentops-bridge-case-plan/1'
                    and plan.get('case_id') == result.get('case_id')
                    and plan.get('kind') == result.get('kind') in ('native', 'bridge'), 'Case plan/result binding')
            config_raw = (case_dir / 'client-config.json').read_bytes()
            config = decode_json(config_raw)
            require((case_dir / 'client/config.json').read_bytes() == config_raw, 'Exact prepared/executed client config')
            require(plan['client_config']['sha256'] == hashlib.sha256(config_raw).hexdigest()
                    and plan['client_config']['bytes'] == len(config_raw), 'Prepared client config digest')
            require(config.get('agent_base_url') == f'http://127.0.0.1:{plan["port"]}/', 'Prepared origin URL')
            service_report = check_service(case_dir / 'service', seed)
            report['service'] = service_report
            if plan['kind'] == 'bridge':
                require(config.get('arm') == plan['case_id'], 'Prepared bridge arm')
                client_report = check_client(case_dir / 'client', service_report)
            else:
                require(config.get('profile') == plan.get('profile')
                        and config.get('representation') == plan.get('representation'), 'Prepared native profile')
                client_report = check_native_client(case_dir / 'client', service_report)
            report['client'] = client_report
            for prefix, child in (('service', service_report), ('client', client_report)):
                errors.extend(prefix + ':' + value for value in child['validation_errors'])
                gaps.extend(prefix + ':' + value for value in child['observation_gaps'])
                deviations.extend(prefix + ':' + value for value in child['policy_deviations'])
            if result.get('service_returncode') != 0 or result.get('forced_service_stop') is not False:
                gaps.append('service_shutdown_not_clean')
            if result.get('client_returncode') != 0 or result.get('client_timed_out') is not False:
                gaps.append('client_did_not_finish_cleanly')
            receipt = decode_json((case_dir / 'client-process.json').read_bytes())
            require(all(receipt.get(source) == result.get(target) for source, target in (
                        ('returncode', 'client_returncode'), ('timed_out', 'client_timed_out'),
                        ('forced_kill', 'client_forced_kill'))), 'Client process receipt/result binding')
            if receipt.get('forced_kill') is not False or receipt.get('cleanup_errors'):
                gaps.append('client_process_cleanup_not_clean')
            require(at_utc(receipt['started_at_utc']) <= at_utc(receipt['finished_at_utc']), 'Client process receipt ordering')
            require(receipt.get('owned_group') == result.get('client_group_cleanup'), 'Client group receipt/result binding')
            if not check_owned_group(receipt.get('owned_group'), receipt.get('pid')):
                gaps.append('client_owned_group_not_initially_clean')
            service_process = decode_json((case_dir / 'service-process.json').read_bytes())
            if not check_owned_group(result.get('service_group_cleanup'), service_process.get('pid')):
                gaps.append('service_owned_group_not_initially_clean')
            if service_report.get('evaluator_final_started_at_utc') and not (
                    at_utc(receipt['finished_at_utc']) <= at_utc(service_report['evaluator_final_started_at_utc'])):
                deviations.append('evaluator_read_precedes_client_exit')
            if result.get('cleanup_errors'):
                gaps.append('coordinator_cleanup_errors')
            if result.get('source_unchanged_after') is not True:
                deviations.append('source_integrity_not_preserved')
            require(result.get('live_model_calls') == 0 and result.get('research_gate_credit_added') == 0,
                    'Case resource/claim scope')
            evaluator = result.get('evaluator_query', {})
            require(evaluator.get('grader_only') is True and evaluator.get('available_to_client') is False,
                    'Evaluator data excluded from client')
            if service_report.get('original') and evaluator.get('executed'):
                require(all(evaluator.get(key) == value for key, value in service_report['original'].items()),
                        'Evaluator original binding')
            report['task_completed'] = service_report['task_completed']
            report['effect_classification'] = (service_report.get('effect') or {}).get('classification', 'unknown')
            report['strict_success'] = bool(service_report['strict_success'] and client_report['complete']
                                            and not errors and not gaps and not deviations)
    except FileNotFoundError as error:
        gaps.append('missing_evidence_file:' + Path(error.filename).name)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError, UnicodeError) as error:
        errors.append(type(error).__name__ + ': ' + str(error))
    report['valid'] = not errors
    report['complete'] = report['valid'] and not gaps
    if not report['complete']:
        report['strict_success'] = False
    report['outcome'] = ('strict_success' if report['strict_success'] else
                         'unknown_or_partial' if not report['complete'] else
                         'completed_without_required_effect' if report.get('task_completed')
                         and report.get('effect_classification') == 'unchanged' else
                         'observed_non_success')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', type=Path, required=True)
    parser.add_argument('--seed-db', type=Path, default=Path(__file__).resolve().parents[1] /
                        'external/agentops-c806b7f1/agents/data/incidents.db')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Preserve prior bridge checks')
    result = check_case(args.case, seed_snapshot(args.seed_db))
    with args.output.open('x', encoding='utf-8') as output:
        json.dump(result, output, indent=2)
        output.write('\n')
    print(json.dumps(result, indent=2))
    # A completely recorded non-success is not a checker process failure.
    raise SystemExit(0 if result['valid'] else 1)
