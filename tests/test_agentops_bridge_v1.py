"""Constructed adversarial evidence for independent bridge/effect checking.

These tests do not launch a service or bridge and are not application outcomes.
"""
import copy
import base64
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import check_agentops_bridge_v1 as checker
from check_agentops_effect_v2 import seed_snapshot
from test_agentops_socket_policy_v1 import policy_fixture


def encoded(value):
    return json.dumps(value, separators=(',', ':')).encode('utf-8')


def task(state):
    value = {'id': 'original-task', 'contextId': 'original-context', 'status': {'state': state}}
    if state == 'TASK_STATE_INPUT_REQUIRED':
        value['status']['message'] = {'parts': [{'data': {
            'id': 'public-confirmation', 'name': 'adk_request_confirmation',
            'args': {'originalFunctionCall': {'id': 'restart-inventory-call', 'name': 'restart_service',
                                               'args': {'name': 'inventory'}}}},
            'metadata': {'adk_type': 'function_call'}}]}
    else:
        value['status']['message'] = {'parts': [{'text': 'Inventory restarted.'}]}
    return value


def successful_database(seed):
    value = copy.deepcopy(seed)
    next(row for row in value['tables']['services'] if row['name'] == 'inventory')['status'] = 'operational'
    value['tables']['audit_log'] = [{'id': 1, 'schema_version': 1, 'ts': '2026-10-27T00:00:32Z',
        'actor': 'agentops-agent', 'approved_by': 'A2A_USER_original-context', 'rationale': checker.RATIONALE,
        'context_summary': 'service inventory was down; open incidents: INC-002',
        'session_id': 'original-context', 'invocation_id': 'original-invocation', 'action': 'restart_service',
        'target': 'inventory', 'detail': 'service restarted and marked operational (mock)'}]
    value['tables']['sqlite_sequence'] = [{'name': 'audit_log', 'seq': 1}]
    return value


def snapshot(value, seconds):
    return {'observed_at_utc': f'2026-10-27T00:00:{seconds:02d}+00:00', 'monotonic_ns': seconds * 1000000000,
            'database': dict(copy.deepcopy(value), path='state/incidents.db', path_base='run')}


def write_exchange(directory, seq, request, response, before, after, *, sse=False):
    directory.mkdir(parents=True)
    request_raw = b'' if request is None else encoded(request)
    response_raw = (b'data: ' + encoded(response) + b'\n\n') if sse else encoded(response)
    (directory / 'request.body.bin').write_bytes(request_raw)
    (directory / 'response.body.bin').write_bytes(response_raw)
    record = {'schema_version': 'agentops-asgi-exchange/1', 'sequence': seq,
        'method': 'GET' if request is None else 'POST', 'path': '/.well-known/agent-card.json' if request is None else '/',
        'query_string': '', 'http_version': '1.1', 'request_headers': [['host', '127.0.0.1:19001'],
            ['content-length', str(len(request_raw))], ['a2a-version', '1.0']],
        'response_status': 200, 'response_headers': [['content-type', 'text/event-stream' if sse else 'application/json']],
        'request_body_complete': True, 'response_body_complete': True,
        'request_bytes': len(request_raw), 'response_bytes': len(response_raw),
        'response_chunks': [{'bytes': len(response_raw), 'sha256': hashlib.sha256(response_raw).hexdigest(), 'more_body': False}],
        'started_at_utc': f'2026-10-27T00:00:{seq * 10 + 1:02d}+00:00',
        'finished_at_utc': f'2026-10-27T00:00:{seq * 10 + 2:02d}+00:00'}
    (directory / 'exchange.json').write_bytes(encoded(record))
    (directory / 'before.snapshot.json').write_bytes(encoded(snapshot(before, seq * 10)))
    (directory / 'after.snapshot.json').write_bytes(encoded(snapshot(after, seq * 10 + 3)))


def write_service(service, seed, *, effect=True, literal=False):
    final = successful_database(seed) if effect else copy.deepcopy(seed)
    data = {'id': 'public-confirmation', 'name': 'adk_request_confirmation',
            'response': {'confirmed': True, 'payload': {'rationale': checker.RATIONALE}}}
    approval = {'text': checker.LITERAL_CONFIRMATION} if literal else {
        'data': data, 'metadata': {'adk_type': 'function_response'}}
    messages = [
        (None, {'name': 'AgentOps Agent'}, seed, seed),
        ({'jsonrpc': '2.0', 'id': 'start', 'method': 'SendMessage', 'params': {'message': {
            'messageId': 'm1', 'role': 'ROLE_USER', 'parts': [{'text': checker.START_TEXT}]}}},
         {'jsonrpc': '2.0', 'id': 'start', 'result': {'task': task('TASK_STATE_INPUT_REQUIRED')}}, seed, seed),
        ({'jsonrpc': '2.0', 'id': 'resume', 'method': 'SendMessage', 'params': {'message': {
            'messageId': 'm2', 'role': 'ROLE_USER', 'taskId': 'original-task', 'contextId': 'original-context',
            'parts': [approval]}}},
         {'jsonrpc': '2.0', 'id': 'resume', 'result': {'task': task('TASK_STATE_COMPLETED')}}, seed, final),
        ({'jsonrpc': '2.0', 'id': 'evaluator-final', 'method': 'GetTask', 'params': {'id': 'original-task'}},
         {'jsonrpc': '2.0', 'id': 'evaluator-final', 'result': task('TASK_STATE_COMPLETED')}, final, final),
    ]
    for seq, values in enumerate(messages, 1):
        write_exchange(service / 'wire' / f'{seq:06d}', seq, *values)
    (service / 'final.snapshot.json').write_bytes(encoded(snapshot(final, 50)))
    (service / 'terminal.snapshot.json').write_bytes(encoded(snapshot(final, 55)))
    (service / 'service-ready.json').write_bytes(encoded({'port': 19001}))
    (service / 'service-result.json').write_bytes(encoded({
        'schema_version': 'agentops-http-service/1', 'observer_version': 3, 'status': 'stopped',
        'finished_at_utc': '2026-10-27T00:00:54+00:00',
        'asgi_requests': 4, 'capture_errors': [], 'network_errors': [], 'model_double_calls': 2,
        'socket_policy': policy_fixture(port=19001),
        'seen_contexts': [['A2A_USER_original-context', 'original-context', 'original-invocation', flag]
                          for flag in ([False, True] if effect else [False])]}))


def entity(raw):
    return {'base64': base64.b64encode(raw).decode('ascii'), 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest()}


def clean_group(pgid):
    return {'schema_version': 'agentops-owned-process-group/1', 'pgid': pgid,
            'initially_empty': True, 'final_empty': True, 'forced_cleanup': False,
            'members': [], 'final_members': [], 'signals': [], 'errors': [],
            'snapshots': [{'phase': 'initial', 'monotonic_ns': 1, 'members': [], 'errors': []}]}


def write_client(client):
    client.mkdir(parents=True)
    config = {'schema_version': 'agentops-bridge-client-config/1', 'arm': 'B7',
              'agent_base_url': 'http://127.0.0.1:19001/', 'agent_alias': 'agentops', 'rationale': checker.RATIONALE,
              'bridge': {'command': '/usr/bin/node', 'args': ['synthetic-bridge.mjs'], 'cwd': '/synthetic'}}
    rows, bindings = [], []

    def emit(kind, **value):
        index = len(rows) + 1
        event = {'schema_version': 'agentops-bridge-client-event/1', 'seq': index,
                 'at_utc': '2026-10-27T00:00:00+00:00', 'monotonic_ns': str(index), 'kind': kind, **value}
        rows.append(event)
        return index

    def rpc(phase, method, params, value):
        operation = sum(row['kind'] == 'operation-start' for row in rows) + 1
        emit('operation-start', operation_id=operation, phase=phase, method=method, notification=False)
        request = {'jsonrpc': '2.0', 'id': operation, 'method': method, 'params': params}
        emit('mcp-message', direction='client_to_bridge', framing='stdio-line', phase=phase,
             operation_id=operation, raw=entity(encoded(request) + b'\n'), parsed=request)
        response = {'jsonrpc': '2.0', 'id': operation, 'result': {'structuredContent': value}}
        emit('stdio-chunk', direction='bridge_to_client', raw=entity(encoded(response) + b'\n'))
        seq = emit('mcp-message', direction='bridge_to_client', framing='stdio-line', phase=phase,
                   operation_id=operation, raw=entity(encoded(response) + b'\n'), parsed=response)
        emit('operation-complete', operation_id=operation, phase=phase, reply_seq=seq)
        return seq

    def bind(name, value, source_seq, path):
        binding = {'name': name, 'value': value, 'source': {'seq': source_seq, 'path': path}}
        bindings.append(binding)
        emit('public-binding', **binding)

    child_start = dict(config['bridge'], pid=12345, started_at_utc='2026-10-27T00:00:00+00:00', clean_exit=False)
    emit('child-start', **child_start)
    summary = {'id': 'original-task', 'context_id': 'original-context', 'state': 'input_required'}
    first = rpc('initial_typed_send', 'tools/call', {'name': 'a2a_send_message', 'arguments': {
        'url': config['agent_base_url'], 'text': checker.START_TEXT}}, {'task': summary})
    bind('task_id', 'original-task', first, ['result', 'structuredContent', 'task', 'id'])
    bind('context_id', 'original-context', first, ['result', 'structuredContent', 'task', 'context_id'])
    raw_get = rpc('public_raw_get', 'tools/call', {'name': 'a2a_request', 'arguments': {
        'url': config['agent_base_url'], 'method': 'GetTask', 'params': {'id': 'original-task', 'historyLength': 100}}},
        {'result': task('TASK_STATE_INPUT_REQUIRED')})
    source = ['result', 'structuredContent', 'result', 'status', 'message', 'parts', 0, 'data']
    bind('confirmation_call_id', 'public-confirmation', raw_get, source + ['id'])
    bind('confirmation_call_name', 'adk_request_confirmation', raw_get, source + ['name'])
    data = {'id': 'public-confirmation', 'name': 'adk_request_confirmation',
            'response': {'confirmed': True, 'payload': {'rationale': checker.RATIONALE}}}
    rpc('raw_answer', 'tools/call', {'name': 'a2a_request', 'arguments': {
        'url': config['agent_base_url'], 'method': 'SendMessage', 'params': {'message': {
            'messageId': 'agentops-public-confirmation', 'role': 'ROLE_USER', 'taskId': 'original-task',
            'contextId': 'original-context', 'parts': [{'data': data, 'metadata': {'adk_type': 'function_response'}}]}}}},
        {'result': {'task': task('TASK_STATE_COMPLETED')}})
    rpc('final_origin_get', 'tools/call', {'name': 'a2a_get_task', 'arguments': {
        'task_id': 'original-task', 'history_length': 100, 'refresh': True}}, dict(summary, state='completed'))
    exit_record = {'code': 0, 'signal': None, 'at_utc': '2026-10-27T00:00:00+00:00'}
    emit('child-exit', **exit_record)
    child = dict(child_start, clean_exit=True, exit=exit_record, finished_at_utc='2026-10-27T00:00:00+00:00')
    emit('child-cleanup', **child)
    result = {'schema_version': 'agentops-bridge-client-result/1', 'arm': 'B7', 'status': 'recorded',
              'strict_success': None, 'bindings': bindings, 'answer_sent': True, 'child': child}
    (client / 'config.json').write_bytes(encoded(config))
    (client / 'result.json').write_bytes(encoded(result))
    (client / 'mcp.jsonl').write_bytes(b''.join(encoded(row) + b'\n' for row in rows))
    return rows


def write_amir_client(client, arm, *, sse=False):
    client.mkdir(parents=True)
    config = {'schema_version': 'agentops-bridge-client-config/1', 'arm': arm,
              'agent_base_url': 'http://127.0.0.1:19001/', 'amir_endpoint': 'http://127.0.0.1:19002/mcp',
              'agent_alias': 'agentops', 'rationale': checker.RATIONALE,
              'bridge': {'command': '/usr/bin/node', 'args': ['synthetic-bridge.mjs'], 'cwd': '/synthetic'}}
    rows, bindings = [], []

    def emit(kind, **value):
        index = len(rows) + 1
        rows.append({'schema_version': 'agentops-bridge-client-event/1', 'seq': index,
                     'at_utc': '2026-10-27T00:00:00+00:00', 'monotonic_ns': str(index), 'kind': kind, **value})
        return index

    def rpc(phase, method, params, body):
        operation = sum(row['kind'] == 'operation-start' for row in rows) + 1
        emit('operation-start', operation_id=operation, phase=phase, method=method, notification=False)
        capabilities = {'extensions': {'io.modelcontextprotocol/tasks': {}}} if arm == 'B2' else {
            'elicitation': {}} if arm == 'B3' else {}
        meta = {'io.modelcontextprotocol/protocolVersion': '2026-07-28',
                'io.modelcontextprotocol/clientCapabilities': capabilities,
                'io.modelcontextprotocol/clientInfo': {'name': 'AgentOps-public-control', 'version': '1.0.0'}}
        message = {'jsonrpc': '2.0', 'id': operation, 'method': method, 'params': dict(params, _meta=meta)}
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream',
                   'MCP-Protocol-Version': '2026-07-28', 'Mcp-Method': method}
        if method == 'tools/call':
            headers['Mcp-Name'] = params['name']
        elif method.startswith('tasks/'):
            headers['Mcp-Name'] = params['taskId']
        source = emit('http-request', operation_id=operation, phase=phase, url=config['amir_endpoint'],
                      method='POST', headers=headers, raw=entity(encoded(message)))
        emit('mcp-message', direction='client_to_bridge', framing='http-body', phase=phase, operation_id=operation,
             source_http_seq=source, raw=entity(encoded(message)), parsed=message)
        message = {'jsonrpc': '2.0', 'id': operation, 'result': body}
        raw = encoded(message)
        source = emit('http-response', operation_id=operation, phase=phase, status=200, complete=True,
                      headers={'content-type': 'text/event-stream' if sse else 'application/json'},
                      raw=entity(b'data: ' + raw + b'\r\n\r\n' if sse else raw))
        seq = emit('mcp-message', direction='bridge_to_client', framing='sse-data-derived' if sse else 'http-body',
                   operation_id=operation, phase=phase, source_http_seq=source, raw=entity(raw), parsed=message)
        emit('operation-complete', operation_id=operation, phase=phase, reply_seq=seq)
        return seq

    def bind(name, value, seq, path, decoded_path=None):
        source = {'seq': seq, 'path': path}
        if decoded_path is not None:
            source.update(decode='json-text', decoded_path=decoded_path)
        binding = {'name': name, 'value': value, 'source': source}
        bindings.append(binding)
        emit('public-binding', **binding)

    child_start = dict(config['bridge'], pid=12345, started_at_utc='2026-10-27T00:00:00+00:00', clean_exit=False)
    emit('child-start', **child_start)
    call = {'id': 'public-confirmation', 'name': 'adk_request_confirmation'}
    body = {'structuredContent': {'taskHandle': 'tk-original', 'contextHandle': 'cx-original',
                                  'a2aState': 'TASK_STATE_INPUT_REQUIRED'},
            'content': [{'type': 'text', 'text': json.dumps(call), '_meta': {
                'io.github.amirk-s/a2a': {'partKind': 'data', 'metadata': {'adk_type': 'function_call'}}}}]}
    form = {'answer': {'method': 'elicitation/create', 'params': {'mode': 'form',
             'requestedSchema': {'type': 'object', 'properties': {'answer': {'type': 'string'}}, 'required': ['answer']}}}}
    original_args = {'agent': 'agentops', 'text': checker.START_TEXT}
    initial_body = ({'resultType': 'input_required', 'requestState': 'opaque-state', 'inputRequests': form} if arm == 'B3' else
                    {'taskId': 'tk-original', 'resultType': 'task'} if arm == 'B2' else body)
    first = rpc('initial_typed_send', 'tools/call', {'name': 'a2a_send_message', 'arguments': original_args}, initial_body)
    result = {'schema_version': 'agentops-bridge-client-result/1', 'arm': arm, 'status': 'recorded',
              'strict_success': None, 'bindings': bindings, 'answer_sent': True}
    data = dict(call, response={'confirmed': True, 'payload': {'rationale': checker.RATIONALE}})
    text = json.dumps(data, separators=(',', ':'))
    if arm == 'B3':
        bind('request_state', 'opaque-state', first, ['result', 'requestState'])
        result['form'] = {'source_seq': first, 'request_key': 'answer', 'field': 'answer'}
        rpc('mrtr_answer', 'tools/call', {'name': 'a2a_send_message', 'arguments': original_args,
            'requestState': 'opaque-state', 'inputResponses': {'answer': {'action': 'accept', 'content': {'answer': checker.LITERAL_CONFIRMATION}}}}, body)
    else:
        bind('task_handle', 'tk-original', first,
             ['result', 'taskId'] if arm == 'B2' else ['result', 'structuredContent', 'taskHandle'])
        pending = rpc('pending_origin_get', 'tools/call', {'name': 'a2a_get_task', 'arguments': {
            'agent': 'agentops', 'taskHandle': 'tk-original', 'historyLength': 100}}, body)
        bind('context_handle', 'cx-original', pending, ['result', 'structuredContent', 'contextHandle'])
        bind('confirmation_call_id', call['id'], pending, ['result', 'content', 0, 'text'], ['id'])
        bind('confirmation_call_name', call['name'], pending, ['result', 'content', 0, 'text'], ['name'])
        if arm == 'B2':
            pending_form = rpc('pending_tasks_form', 'tasks/get', {'taskId': 'tk-original'},
                               {'taskId': 'tk-original', 'status': 'input_required', 'inputRequests': form})
            result['form'] = {'source_seq': pending_form, 'request_key': 'answer', 'field': 'answer'}
            rpc('tasks_answer', 'tasks/update', {'taskId': 'tk-original',
                'inputResponses': {'answer': {'action': 'accept', 'content': {'answer': text}}}}, {'resultType': 'complete'})
            rpc('post_answer_tasks_get', 'tasks/get', {'taskId': 'tk-original'}, {'taskId': 'tk-original', 'status': 'complete'})
        else:
            rpc('typed_answer', 'tools/call', {'name': 'a2a_send_message', 'arguments': {
                'agent': 'agentops', 'text': text, 'taskHandle': 'tk-original', 'contextHandle': 'cx-original'}}, body)
    exit_record = {'code': 0, 'signal': None, 'at_utc': '2026-10-27T00:00:00+00:00'}
    emit('child-exit', **exit_record)
    result['child'] = dict(child_start, clean_exit=True, exit=exit_record, finished_at_utc='2026-10-27T00:00:00+00:00')
    emit('child-cleanup', **result['child'])
    (client / 'config.json').write_bytes(encoded(config))
    (client / 'result.json').write_bytes(encoded(result))
    (client / 'mcp.jsonl').write_bytes(b''.join(encoded(row) + b'\n' for row in rows))
    return rows


def write_native_client(client, profile='amir-sync', representation='data'):
    client.mkdir(parents=True)
    config = {'schema_version': 'agentops-native-profile-client-config/1', 'profile': profile,
              'representation': representation, 'rationale': checker.RATIONALE,
              'agent_base_url': 'http://127.0.0.1:19001/'}
    rows, bindings = [], []

    def emit(kind, **value):
        index = len(rows) + 1
        rows.append({'schema_version': 'agentops-native-profile-event/1', 'seq': index,
                     'at_utc': '2026-10-27T00:00:00+00:00', 'monotonic_ns': str(index), 'kind': kind, **value})
        return index

    def bind(name, value, seq, path):
        binding = {'name': name, 'value': value, 'source': {'seq': seq, 'path': ['value', *path]}}
        bindings.append(binding)
        emit('public-binding', **binding)

    data = {'id': 'public-confirmation', 'name': 'adk_request_confirmation',
            'response': {'confirmed': True, 'payload': {'rationale': checker.RATIONALE}}}
    public_task = {'id': 'original-task', 'contextId': 'original-context', 'status': {
        'state': 4, 'message': {'parts': [{'content': {'$case': 'data', 'value': {
            'id': 'public-confirmation', 'name': 'adk_request_confirmation'}},
            'metadata': {'adk_type': 'function_call'}}]}}}
    sent = []
    for index, text in enumerate((checker.START_TEXT, checker.LITERAL_CONFIRMATION if representation == 'literal'
                                  else json.dumps(data, separators=(',', ':')))):
        is_data = index == 1 and representation == 'data'
        part = {'content': {'$case': 'data' if is_data else 'text', 'value': data if is_data else text},
                'filename': '', 'mediaType': '' if is_data else 'text/plain'}
        wire_part = {'data': data, 'metadata': {'adk_type': 'function_response'}} if is_data else {
            'text': text, 'mediaType': 'text/plain'}
        if is_data:
            part['metadata'] = {'adk_type': 'function_response'}
        message = {'messageId': 'm' + str(index + 1), 'role': 1, 'parts': [part],
                   'taskId': 'original-task' if index else '', 'contextId': 'original-context' if index else '',
                   'extensions': [], 'referenceTaskIds': []}
        wire_message = {'messageId': message['messageId'], 'role': 'ROLE_USER', 'parts': [wire_part]}
        if index:
            wire_message.update(taskId='original-task', contextId='original-context')
        raw_resume = index == 1 and profile.startswith('mg-raw')
        args = {'params': {'message': wire_message}, 'version': '1.0' if profile == 'mg-raw-header' else None} if raw_resume else message
        phase, action = ('start', 'send') if not index else ('resume-raw', 'rawSend') if raw_resume else ('resume', 'send')
        emit('sdk-call', phase=phase, action=action, arguments=args)
        rpc_id = 'resume' if index else 'start'
        if raw_resume:
            payload = {'jsonrpc': '2.0', 'id': rpc_id, 'method': 'SendMessage', 'params': args['params']}
            headers = {'content-type': 'application/json'}
            if profile == 'mg-raw-header':
                headers['A2A-Version'] = '1.0'
            emit('raw-http-request', url=config['agent_base_url'], method='POST', headers=headers,
                 raw=entity(encoded(payload)), parsed=payload)
            emit('raw-http-response', complete=True, status=200, headers={'content-type': 'application/json'},
                 raw=entity(encoded({'jsonrpc': '2.0', 'id': rpc_id, 'result': {}})))
        reply = emit('sdk-result', phase=phase, action=action, value=public_task)
        sent.append({'sequence': 2 + index, 'rpc_id': rpc_id,
                     'method': 'SendStreamingMessage' if profile == 'amir-stream' else 'SendMessage',
                     'version_headers': [] if raw_resume and profile == 'mg-raw-no-header' else ['1.0'],
                     'configuration_present': not raw_resume,
                     'configuration': None if raw_resume else {'acceptedOutputModes': ['text/plain', 'application/json'],
                         'returnImmediately': True} if profile.startswith('mg-') else {},
                     'message': wire_message})
        if not index:
            bind('task_id', 'original-task', reply, ['id'])
            bind('context_id', 'original-context', reply, ['contextId'])
            emit('sdk-call', phase='get-pending', action='get', arguments='original-task')
            pending = emit('sdk-result', phase='get-pending', action='get', value=public_task)
            path = ['status', 'message', 'parts', 0, 'content', 'value']
            bind('confirmation_call_id', 'public-confirmation', pending, path + ['id'])
            bind('confirmation_call_name', 'adk_request_confirmation', pending, path + ['name'])
    emit('sdk-call', phase='get-completed', action='get', arguments='original-task')
    emit('sdk-result', phase='get-completed', action='get', value=public_task)
    result = {'schema_version': 'agentops-native-profile-client-result/1', 'profile': profile,
              'representation': representation, 'status': 'recorded', 'strict_success': None, 'bindings': bindings,
              'answer_attempts': 1, 'public_original': {'task_id': 'original-task', 'context_id': 'original-context'}}
    (client / 'config.json').write_bytes(encoded(config))
    (client / 'result.json').write_bytes(encoded(result))
    (client / 'sdk.jsonl').write_bytes(b''.join(encoded(row) + b'\n' for row in rows))
    service_report = {'original': result['public_original'], 'confirmation': {'id': 'public-confirmation'},
                      'send_profiles': sent, 'approval_representation': {
                          'literal': 'literal_text', 'json-text': 'json_text', 'data': 'data'}[representation]}
    return rows, service_report


class BridgeServiceChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed = seed_snapshot(ROOT / 'external/agentops-c806b7f1/agents/data/incidents.db')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='agentops-bridge-check-')
        self.addCleanup(self.temp.cleanup)
        self.service = Path(self.temp.name) / 'service'

    def mutate(self, relative, function):
        path = self.service / relative
        value = json.loads(path.read_bytes())
        function(value)
        path.write_bytes(encoded(value))

    def test_original_completion_and_exact_guarded_effect_succeed(self):
        write_service(self.service, self.seed)
        report = checker.check_service(self.service, self.seed)
        self.assertTrue(report['valid'], report)
        self.assertTrue(report['strict_success'], report)
        self.assertEqual(report['effect']['classification'], 'expected_single_effect')

    def test_completed_prose_without_effect_is_valid_non_success(self):
        write_service(self.service, self.seed, effect=False, literal=True)
        report = checker.check_service(self.service, self.seed)
        self.assertTrue(report['valid'], report)
        self.assertTrue(report['complete'], report)
        self.assertTrue(report['task_completed'])
        self.assertEqual(report['effect']['classification'], 'unchanged')
        self.assertFalse(report['strict_success'])

    def test_literal_text_cannot_be_assumed_incapable_of_correct_effect(self):
        write_service(self.service, self.seed, literal=True)
        report = checker.check_service(self.service, self.seed)
        self.assertTrue(report['strict_success'], report)
        self.assertEqual(report['approval_representation'], 'literal_text')

    def test_extra_domain_write_is_retained_but_rejects_success(self):
        write_service(self.service, self.seed)
        for relative in ('wire/000003/after.snapshot.json', 'wire/000004/before.snapshot.json', 'wire/000004/after.snapshot.json', 'final.snapshot.json', 'terminal.snapshot.json'):
            self.mutate(relative, lambda value: value['database']['tables']['incidents'][0].update(status='resolved'))
        report = checker.check_service(self.service, self.seed)
        self.assertTrue(report['valid'], report)
        self.assertFalse(report['strict_success'])
        self.assertIn('additional_or_missing_domain_changes', report['effect']['deviations'])

    def test_wrong_approver_rejects_success(self):
        write_service(self.service, self.seed)
        for relative in ('wire/000003/after.snapshot.json', 'wire/000004/before.snapshot.json', 'wire/000004/after.snapshot.json', 'final.snapshot.json', 'terminal.snapshot.json'):
            self.mutate(relative, lambda value: value['database']['tables']['audit_log'][0].update(approved_by='different-person'))
        report = checker.check_service(self.service, self.seed)
        self.assertTrue(report['valid'], report)
        self.assertFalse(report['strict_success'])
        self.assertIn('audit_attribution_or_action_mismatch', report['effect']['deviations'])

    def test_effect_before_approval_rejects_success(self):
        write_service(self.service, self.seed)
        self.mutate('wire/000002/after.snapshot.json',
                    lambda value: value.update(database=dict(successful_database(self.seed), path='state/incidents.db', path_base='run')))
        report = checker.check_service(self.service, self.seed)
        self.assertFalse(report['strict_success'])
        self.assertIn('domain_effect_before_continuation', report['effect']['deviations'])

    def test_truncated_capture_is_unknown_not_non_support(self):
        write_service(self.service, self.seed)
        self.mutate('wire/000003/exchange.json', lambda value: (
            value.update(response_body_complete=False), value['response_chunks'][-1].update(more_body=True)))
        report = checker.check_service(self.service, self.seed)
        self.assertTrue(report['valid'], report)
        self.assertFalse(report['complete'])
        self.assertFalse(report['strict_success'])
        self.assertIn('partial_http_exchange:3', report['observation_gaps'])

    def test_response_hash_mutation_is_invalid_evidence(self):
        write_service(self.service, self.seed)
        self.mutate('wire/000003/exchange.json', lambda value: value['response_chunks'][0].update(sha256='0' * 64))
        report = checker.check_service(self.service, self.seed)
        self.assertFalse(report['valid'])
        self.assertFalse(report['strict_success'])
        self.assertTrue(any('chunk hash' in error for error in report['validation_errors']))

    def test_rpc_error_is_an_observed_outcome(self):
        write_service(self.service, self.seed, effect=False)
        directory = self.service / 'wire/000003'
        request = json.loads((directory / 'request.body.bin').read_bytes())
        raw = encoded({'jsonrpc': '2.0', 'id': request['id'], 'error': {'code': -32009, 'message': 'version mismatch'}})
        (directory / 'response.body.bin').write_bytes(raw)
        self.mutate('wire/000003/exchange.json', lambda value: value.update(response_status=400,
            response_bytes=len(raw), response_chunks=[{'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'more_body': False}]))
        report = checker.check_service(self.service, self.seed)
        self.assertTrue(report['valid'], report)
        self.assertTrue(report['complete'], report)
        self.assertFalse(report['strict_success'])
        self.assertEqual(report['rpc_outcomes'][1]['errors'][0]['code'], -32009)

    def test_missing_terminal_snapshot_is_partial_evidence(self):
        write_service(self.service, self.seed)
        (self.service / 'terminal.snapshot.json').unlink()
        report = checker.check_service(self.service, self.seed)
        self.assertTrue(report['valid'], report)
        self.assertFalse(report['complete'])
        self.assertFalse(report['strict_success'])

    def test_shutdown_domain_change_is_retained_adverse_outcome(self):
        write_service(self.service, self.seed)
        self.mutate('terminal.snapshot.json', lambda value: value['database']['tables']['incidents'][0].update(status='resolved'))
        report = checker.check_service(self.service, self.seed)
        self.assertTrue(report['valid'], report)
        self.assertFalse(report['strict_success'])
        self.assertIn('domain_changed_during_shutdown', report['policy_deviations'])

    def test_effect_requires_matching_guarded_invocation(self):
        write_service(self.service, self.seed)
        self.mutate('service-result.json', lambda value: value['seen_contexts'][-1].__setitem__(2, 'other-invocation'))
        report = checker.check_service(self.service, self.seed)
        self.assertTrue(report['valid'], report)
        self.assertFalse(report['strict_success'])
        self.assertIn('matching_guarded_approval_not_observed', report['effect']['deviations'])


class PublicInputChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='agentops-public-check-')
        self.addCleanup(self.temp.cleanup)
        self.client = Path(self.temp.name) / 'client'
        self.rows = write_client(self.client)
        self.service_report = {'original': {'task_id': 'original-task', 'context_id': 'original-context'},
                               'confirmation': {'id': 'public-confirmation'}}

    def save(self):
        (self.client / 'mcp.jsonl').write_bytes(b''.join(encoded(row) + b'\n' for row in self.rows))

    def test_public_raw_confirmation_provenance_and_legal_input_pass(self):
        report = checker.check_client(self.client, self.service_report)
        self.assertTrue(report['valid'], report)
        self.assertTrue(report['complete'], report)
        self.assertEqual(report['policy_deviations'], [])
        self.assertTrue(report['public_confirmation_observed'])

    def test_binding_cannot_be_claimed_from_outgoing_request(self):
        binding = next(row for row in self.rows if row['kind'] == 'public-binding')
        outgoing = next(row for row in self.rows if row['kind'] == 'mcp-message' and row['direction'] == 'client_to_bridge')
        binding['source']['seq'] = outgoing['seq']
        self.save()
        report = checker.check_client(self.client, self.service_report)
        self.assertFalse(report['valid'])
        self.assertTrue(any('received MCP' in error for error in report['validation_errors']))

    def test_public_task_must_match_origin_task(self):
        self.service_report['original']['task_id'] = 'another-origin-task'
        report = checker.check_client(self.client, self.service_report)
        self.assertTrue(report['valid'], report)
        self.assertIn('public_original_task_id_mismatch', report['policy_deviations'])

    def test_raw_answer_with_wrong_context_rejects_input_qualification(self):
        answer = next(row for row in self.rows if row.get('phase') == 'raw_answer'
                      and row.get('direction') == 'client_to_bridge')
        answer['parsed']['params']['arguments']['params']['message']['contextId'] = 'other-context'
        answer['raw'] = entity(encoded(answer['parsed']) + b'\n')
        self.save()
        report = checker.check_client(self.client, self.service_report)
        self.assertTrue(report['valid'], report)
        self.assertIn('raw_answer_argument_mismatch', report['policy_deviations'])

    def test_uncovered_stdout_bytes_are_invalid_evidence(self):
        chunk = next(row for row in self.rows if row['kind'] == 'stdio-chunk')
        chunk['raw'] = entity(b'uncovered extra bytes\n')
        self.save()
        report = checker.check_client(self.client, self.service_report)
        self.assertFalse(report['valid'])
        self.assertTrue(any('stdout byte coverage' in error for error in report['validation_errors']))

    def test_json_text_provenance_is_decoded_from_actual_received_content(self):
        raw = encoded({'jsonrpc': '2.0', 'id': 7, 'result': {'content': [
            {'type': 'text', 'text': json.dumps({'id': 'visible-confirmation'})}]}}) + b'\n'
        source = {'seq': 1, 'path': ['result', 'content', 0, 'text'], 'decode': 'json-text', 'decoded_path': ['id']}
        events = {1: {'kind': 'mcp-message', 'direction': 'bridge_to_client', 'raw': entity(raw)}}
        self.assertEqual(checker.resolve_public_source(source, events), 'visible-confirmation')

    def test_amir_http_and_sse_public_paths(self):
        for arm in ('B1', 'B2', 'B3'):
            with self.subTest(arm=arm):
                client = Path(self.temp.name) / arm
                write_amir_client(client, arm, sse=True)
                report = checker.check_client(client, self.service_report)
                self.assertTrue(report['valid'], report)
                self.assertTrue(report['complete'], report)
                self.assertEqual(report['policy_deviations'], [])

    def test_mrtr_changed_request_state_rejects_qualification(self):
        client = Path(self.temp.name) / 'mrtr'
        rows = write_amir_client(client, 'B3')
        outgoing = next(row for row in rows if row.get('phase') == 'mrtr_answer' and row.get('direction') == 'client_to_bridge')
        outgoing['parsed']['params']['requestState'] = 'other-state'
        outgoing['raw'] = entity(encoded(outgoing['parsed']))
        rows[outgoing['source_http_seq'] - 1]['raw'] = outgoing['raw']
        (client / 'mcp.jsonl').write_bytes(b''.join(encoded(row) + b'\n' for row in rows))
        report = checker.check_client(client, self.service_report)
        self.assertTrue(report['valid'], report)
        self.assertIn('mrtr_replay_binding_mismatch', report['policy_deviations'])

    def test_derived_sse_bytes_must_match_source_entity(self):
        client = Path(self.temp.name) / 'sse'
        rows = write_amir_client(client, 'B1', sse=True)
        reply = next(row for row in rows if row.get('framing') == 'sse-data-derived')
        reply['raw'] = entity(encoded(reply['parsed']) + b' ')
        (client / 'mcp.jsonl').write_bytes(b''.join(encoded(row) + b'\n' for row in rows))
        report = checker.check_client(client, self.service_report)
        self.assertFalse(report['valid'])
        self.assertTrue(any('derived from received body' in error for error in report['validation_errors']))

    def whole_case(self):
        case = Path(self.temp.name) / 'case'
        seed = seed_snapshot(ROOT / 'external/agentops-c806b7f1/agents/data/incidents.db')
        write_service(case / 'service', seed)
        write_client(case / 'client')
        config = (case / 'client/config.json').read_bytes()
        (case / 'client-config.json').write_bytes(config)
        (case / 'plan.json').write_bytes(encoded({'schema_version': 'agentops-bridge-case-plan/1',
            'case_id': 'B7', 'kind': 'bridge', 'port': 19001,
            'client_config': {'bytes': len(config), 'sha256': hashlib.sha256(config).hexdigest()}}))
        (case / 'result.json').write_bytes(encoded({'schema_version': 'agentops-bridge-case-result/1',
            'case_id': 'B7', 'kind': 'bridge', 'status': 'recorded', 'service_returncode': 0,
            'forced_service_stop': False, 'client_returncode': 0, 'client_timed_out': False,
            'client_forced_kill': False,
            'client_group_cleanup': clean_group(40001), 'service_group_cleanup': clean_group(40002),
            'cleanup_errors': [], 'source_unchanged_after': True, 'live_model_calls': 0,
            'research_gate_credit_added': 0, 'evaluator_query': {'executed': True,
                'grader_only': True, 'available_to_client': False, 'task_id': 'original-task', 'context_id': 'original-context'}}))
        (case / 'client-process.json').write_bytes(encoded({'returncode': 0, 'timed_out': False,
            'pid': 40001, 'owned_group': clean_group(40001),
            'forced_kill': False, 'cleanup_errors': [], 'started_at_utc': '2026-10-27T00:00:00+00:00',
            'finished_at_utc': '2026-10-27T00:00:40+00:00'}))
        (case / 'service-process.json').write_bytes(encoded({'pid': 40002}))
        return case, seed

    def test_whole_case_requires_public_binding_and_effect(self):
        case, seed = self.whole_case()
        report = checker.check_case(case, seed)
        self.assertTrue(report['strict_success'], report)
        path = case / 'client/result.json'
        value = json.loads(path.read_bytes())
        value['bindings'][0]['value'] = 'invented-task'
        path.write_bytes(encoded(value))
        report = checker.check_case(case, seed)
        self.assertFalse(report['strict_success'])
        self.assertFalse(report['valid'])

    def test_whole_case_requires_process_receipt_to_agree(self):
        case, seed = self.whole_case()
        path = case / 'client-process.json'
        value = json.loads(path.read_bytes())
        value['forced_kill'] = True
        path.write_bytes(encoded(value))
        report = checker.check_case(case, seed)
        self.assertFalse(report['strict_success'])
        self.assertFalse(report['valid'])
        self.assertTrue(any('process receipt/result binding' in error for error in report['validation_errors']))

    def test_evaluator_read_must_follow_client_exit(self):
        case, seed = self.whole_case()
        path = case / 'client-process.json'
        value = json.loads(path.read_bytes())
        value['finished_at_utc'] = '2026-10-27T00:00:45+00:00'
        path.write_bytes(encoded(value))
        report = checker.check_case(case, seed)
        self.assertTrue(report['valid'], report)
        self.assertFalse(report['strict_success'])
        self.assertIn('evaluator_read_precedes_client_exit', report['policy_deviations'])

    def test_missing_client_receipt_is_partial_not_success(self):
        case, seed = self.whole_case()
        (case / 'client-process.json').unlink()
        report = checker.check_case(case, seed)
        self.assertTrue(report['valid'], report)
        self.assertFalse(report['complete'])
        self.assertFalse(report['strict_success'])

    def test_truncated_public_journal_is_partial_evidence(self):
        path = self.client / 'mcp.jsonl'
        path.write_bytes(path.read_bytes()[:-20])
        report = checker.check_client(self.client, self.service_report)
        self.assertTrue(report['valid'], report)
        self.assertFalse(report['complete'])
        self.assertIn('truncated_client_journal', report['observation_gaps'])


class NativeProfileChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='agentops-native-check-')
        self.addCleanup(self.temp.cleanup)
        self.client = Path(self.temp.name) / 'client'
        self.rows, self.service_report = write_native_client(self.client)

    def save(self):
        for index, row in enumerate(self.rows, 1):
            row['seq'], row['monotonic_ns'] = index, str(index)
        path = self.client / 'result.json'
        result = json.loads(path.read_bytes())
        result['bindings'] = [{key: row[key] for key in ('name', 'value', 'source')}
                              for row in self.rows if row['kind'] == 'public-binding']
        path.write_bytes(encoded(result))
        (self.client / 'sdk.jsonl').write_bytes(b''.join(encoded(row) + b'\n' for row in self.rows))

    def test_all_eleven_native_profiles_have_matching_public_inputs(self):
        matrix = [(profile, representation) for profile in ('amir-sync', 'amir-stream', 'mg-poll')
                  for representation in ('literal', 'json-text', 'data')]
        matrix += [('mg-raw-no-header', 'data'), ('mg-raw-header', 'data')]
        for index, (profile, representation) in enumerate(matrix):
            with self.subTest(profile=profile, representation=representation):
                client = Path(self.temp.name) / str(index)
                _, service = write_native_client(client, profile, representation)
                report = checker.check_native_client(client, service)
                self.assertTrue(report['valid'], report)
                self.assertTrue(report['complete'], report)
                self.assertEqual(report['policy_deviations'], [])

    def test_wrong_version_is_observed_profile_deviation(self):
        self.service_report['send_profiles'][1]['version_headers'] = []
        report = checker.check_native_client(self.client, self.service_report)
        self.assertTrue(report['valid'], report)
        self.assertIn('native_version_header_mismatch', report['policy_deviations'])

    def test_empty_raw_configuration_is_not_omitted_configuration(self):
        client = Path(self.temp.name) / 'raw'
        _, service = write_native_client(client, 'mg-raw-header')
        service['send_profiles'][1].update(configuration_present=True, configuration={})
        report = checker.check_native_client(client, service)
        self.assertTrue(report['valid'], report)
        self.assertIn('native_configuration_presence_mismatch', report['policy_deviations'])

    def test_changed_poll_configuration_is_profile_deviation(self):
        client = Path(self.temp.name) / 'poll'
        _, service = write_native_client(client, 'mg-poll')
        service['send_profiles'][0]['configuration']['returnImmediately'] = False
        report = checker.check_native_client(client, service)
        self.assertTrue(report['valid'], report)
        self.assertIn('native_polling_configuration_mismatch', report['policy_deviations'])

    def test_native_binding_cannot_come_from_outbound_call(self):
        binding = next(row for row in self.rows if row['kind'] == 'public-binding')
        binding['source'] = {'seq': 1, 'path': ['arguments', 'taskId']}
        self.save()
        report = checker.check_native_client(self.client, self.service_report)
        self.assertFalse(report['valid'])
        self.assertTrue(any('earlier SDK result' in error for error in report['validation_errors']))

    def test_native_confirmation_binding_after_resume_rejects_qualification(self):
        binding = next(row for row in self.rows if row.get('name') == 'confirmation_call_id')
        self.rows.remove(binding)
        self.rows.insert(len(self.rows) - 2, binding)
        self.save()
        report = checker.check_native_client(self.client, self.service_report)
        self.assertTrue(report['valid'], report)
        self.assertIn('native_resume_uses_unobserved_binding:confirmation_call_id', report['policy_deviations'])

    def test_native_invocation_must_use_bound_context(self):
        resume = next(row for row in self.rows if row['kind'] == 'sdk-call' and row['phase'] == 'resume')
        resume['arguments']['contextId'] = 'other-context'
        self.save()
        report = checker.check_native_client(self.client, self.service_report)
        self.assertTrue(report['valid'], report)
        self.assertIn('native_sdk_arguments_differ_from_fixed_input', report['policy_deviations'])

    def test_native_truncated_journal_is_partial_evidence(self):
        path = self.client / 'sdk.jsonl'
        path.write_bytes(path.read_bytes()[:-20])
        report = checker.check_native_client(self.client, self.service_report)
        self.assertTrue(report['valid'], report)
        self.assertFalse(report['complete'])
        self.assertIn('truncated_native_journal', report['observation_gaps'])

    def test_missing_native_result_is_partial_evidence(self):
        (self.client / 'result.json').unlink()
        report = checker.check_native_client(self.client, self.service_report)
        self.assertTrue(report['valid'], report)
        self.assertFalse(report['complete'])
        self.assertIn('missing_evidence_file:result.json', report['observation_gaps'])


if __name__ == '__main__':
    unittest.main()
