"""Constructed canonical wire/effect evidence; these are not AgentOps 1.0 observations."""
import copy
import json
from pathlib import Path
import sys
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from agentops_protocol_wire_v1 import request_bytes, pending_task
from check_agentops_protocol_v1 import LABELS, check, parse_request
from check_agentops_effect_v2 import seed_snapshot
from test_agentops_http_control import fixtures, encoded, response
from test_agentops_socket_policy_v1 import policy_fixture


def canonical_event(value):
    row = copy.deepcopy(value)
    kind = row.pop('kind')
    row.pop('final', None)
    if kind == 'task':
        # Task uses id; taskId belongs to the streaming update arms.
        row.pop('taskId', None)
    if 'status' in row:
        row['status']['state'] = 'TASK_STATE_' + row['status']['state'].upper().replace('-', '_')
        if 'message' in row['status']:
            row['status']['message'].pop('kind', None)
            for part in row['status']['message']['parts']:
                part.pop('kind', None)
    if kind == 'artifact-update':
        # The older effect fixture deliberately omitted irrelevant artifact
        # contents; construct a minimal typed artifact for this software test.
        row.setdefault('artifact', {'artifactId': 'constructed-artifact', 'parts': [{'text': 'constructed content'}]})
        for part in row['artifact'].get('parts', []):
            part.pop('kind', None)
    return {dict(task='task', **{'status-update': 'statusUpdate', 'artifact-update': 'artifactUpdate'})[kind]: row}


def constructed_files(seed, case):
    profile = fixtures.authored_profile(seed)
    events = {name: [canonical_event(v) for v in profile['observations'][index]['results']]
              for name, index in (('start', 1), ('resume', 3))}
    port = 18762 if case == 'sync' else 18763
    method = 'SendMessage' if case == 'sync' else 'SendStreamingMessage'
    payloads = {}
    for name, index in (('start', 0), ('resume', 2)):
        payload = copy.deepcopy(profile['observations'][index]['payload'])
        payload['method'] = method
        message = payload['params']['message']
        message.pop('kind')
        message['role'] = 'ROLE_USER'
        for part in message['parts']:
            part.pop('kind')
        payloads[name] = payload
    for name in ('get-pending', 'get-completed'):
        payloads[name] = {'jsonrpc': '2.0', 'id': name, 'method': 'GetTask', 'params': {'id': 'authored-task'}}
    payloads['get-default'] = payloads['get-pending']
    payloads['resume-default'] = payloads['resume']
    files = {'plan.json': encoded({'schema_version': 'agentops-protocol-plan/1', 'case': case, 'port': port, 'sequence': list(LABELS)})}
    card = {'name': 'AgentOps Agent', 'version': '0.11.0', 'protocolVersion': '0.3',
            'capabilities': {'streaming': True}, 'supportedInterfaces': [{'url': f'http://127.0.0.1:{port}/', 'protocolBinding': 'JSONRPC'}],
            'skills': [{'id': v} for v in ('incident-triage', 'remediation')], 'defaultInputModes': ['text/plain'], 'defaultOutputModes': ['text/plain']}
    for i, label in enumerate(LABELS):
        version = None if label in ('card-default', 'get-default', 'resume-default') else '1.0'
        http_method = 'GET' if label.startswith('card-') else 'POST'
        files[label + '.request.bin'] = request_bytes(port, http_method, payloads.get(label), version)
        files[label + '.exchange.json'] = encoded({'label': label, 'port': port, 'method': http_method, 'version': version,
            'request_fully_sent': True, 'response_eof': True, 'status': 'captured',
            'started_at_utc': f'2026-10-26T00:00:{i * 3 + 1:02d}+00:00',
            'finished_at_utc': f'2026-10-26T00:00:{i * 3 + 2:02d}+00:00'})
        if label.startswith('card-'):
            reply = card
        elif label in ('get-default', 'resume-default'):
            reply = {'jsonrpc': '2.0', 'id': payloads[label]['id'], 'error': {'code': -32009, 'message': 'authored version rejection'}}
        elif label in ('start', 'resume'):
            if case == 'stream':
                body = b''.join(b'data: ' + encoded({'jsonrpc': '2.0', 'id': 'approval-' + label, 'result': r}) + b'\r\n\r\n'
                                for r in events[label])
                files[label + '.response.bin'] = response(body, 'text/event-stream', chunked=True)
                continue
            event = copy.deepcopy(events[label][-1]['statusUpdate'])
            event['id'] = event.pop('taskId')
            reply = {'jsonrpc': '2.0', 'id': 'approval-' + label, 'result': {'task': event}}
        else:
            state = 'TASK_STATE_INPUT_REQUIRED' if label == 'get-pending' else 'TASK_STATE_COMPLETED'
            reply = {'jsonrpc': '2.0', 'id': label, 'result': {'id': 'authored-task', 'contextId': 'authored-context', 'status': {'state': state}}}
        files[label + '.response.bin'] = response(encoded(reply))
    boundaries = []
    for i, label in enumerate(['before-card-default'] + ['after-' + v for v in LABELS]):
        db = copy.deepcopy(profile['observations'][0 if i < 7 else 3]['database'])
        db['path'] = 'state/incidents.db'
        if i >= 7:
            db['tables']['audit_log'][0]['ts'] = '2026-10-26T00:00:19Z'
        row = {'label': label, 'database': db, 'monotonic_ns': i + 1, 'observed_at_utc': f'2026-10-26T00:00:{i * 3:02d}+00:00'}
        files[label + '.snapshot.json'] = encoded(row)
        boundaries.append(row)
    files['boundaries.json'] = encoded(boundaries)
    files['service-result.json'] = encoded({'schema_version': 'agentops-http-service/1', 'observer_version': 2, 'status': 'stopped',
        'model_double_calls': 2, 'network_errors': [], 'socket_policy': policy_fixture(port=port),
        'seen_contexts': profile['final_test_locals']['seen_contexts']})
    return files


class ProtocolChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed = seed_snapshot(ROOT / 'external/agentops-c806b7f1/agents/data/incidents.db')

    def setUp(self):
        self.folder = ROOT / 'tmp' / ('constructed-protocol-' + uuid.uuid4().hex)
        self.folder.mkdir(parents=True)

    def write(self, files):
        for name, raw in files.items():
            (self.folder / name).write_bytes(raw)

    def test_both_constructed_profiles(self):
        for case in ('sync', 'stream'):
            self.write(constructed_files(self.seed, case))
            result = check(self.folder, self.seed)
            self.assertEqual(result['status'], 'passed')
            self.assertTrue(result['cards_equal'])
            self.assertFalse(result['bridge_qualification'])

    def test_literal_header_is_the_only_paired_request_difference(self):
        files = constructed_files(self.seed, 'sync')
        self.assertEqual(files['resume-default.request.bin'], files['resume.request.bin'].replace(b'A2A-Version: 1.0\r\n', b''))

    def test_invalid_transport_choices(self):
        for port, method, payload, version in [(80, 'GET', None, '1.0'), (18762, 'PUT', {}, '1.0'),
                (18762, 'GET', {}, '1.0'), (18762, 'POST', {}, '1.0\r\nAuthorization: x')]:
            with self.subTest(version=version), self.assertRaises(ValueError):
                request_bytes(port, method, payload, version)

    def test_header_mutations_rejected(self):
        files = constructed_files(self.seed, 'sync')
        original = files['resume.request.bin']
        for raw in [original.replace(b'A2A-Version: 1.0\r\n', b''),
                    original.replace(b'A2A-Version: 1.0', b'A2A-Version: 0.3'),
                    original.replace(b'A2A-Version: 1.0', b'A2A-Version: 1.0\r\nA2A-Version: 1.0'),
                    original.replace(b'A2A-Version: 1.0', b'Authorization: secret\r\nA2A-Version: 1.0')]:
            with self.assertRaises(ValueError):
                parse_request(raw, 18762, 'resume')

    def test_wrong_call_id_or_task_is_rejected(self):
        for before, after in [(b'authored-task', b'other-task'), (b'authored-context', b'other-context'),
                              (b'function_response', b'function_call')]:
            files = constructed_files(self.seed, 'sync')
            files['resume.request.bin'] = files['resume.request.bin'].replace(before, after)
            self.write(files)
            with self.assertRaises(ValueError):
                check(self.folder, self.seed)

    def test_wrong_negative_result_is_rejected(self):
        files = constructed_files(self.seed, 'sync')
        files['get-default.response.bin'] = response(encoded({'jsonrpc': '2.0', 'id': 'get-pending', 'result': {}}))
        self.write(files)
        with self.assertRaisesRegex(ValueError, 'version rejection'):
            check(self.folder, self.seed)

    def test_extra_or_unrelated_domain_write_is_rejected(self):
        files = constructed_files(self.seed, 'sync')
        boundaries = json.loads(files['boundaries.json'])
        for row in boundaries[7:]:
            row['database']['tables']['incidents'][0]['status'] = 'resolved'
            files[row['label'] + '.snapshot.json'] = encoded(row)
        files['boundaries.json'] = encoded(boundaries)
        self.write(files)
        with self.assertRaisesRegex(ValueError, 'only expected'):
            check(self.folder, self.seed)

    def test_early_effect_is_rejected(self):
        files = constructed_files(self.seed, 'sync')
        boundaries = json.loads(files['boundaries.json'])
        boundaries[6]['database'] = copy.deepcopy(boundaries[7]['database'])
        files['boundaries.json'] = encoded(boundaries)
        files['after-resume-default.snapshot.json'] = encoded(boundaries[6])
        self.write(files)
        with self.assertRaisesRegex(ValueError, 'pre-confirmation'):
            check(self.folder, self.seed)

    def test_unbound_stream_event_is_rejected(self):
        from agentops_http_bytes_v1 import decode_response, rpc_results
        for arm in ('task', 'statusUpdate', 'artifactUpdate'):
            for field in ('task', 'context'):
                with self.subTest(arm=arm, field=field):
                    files = constructed_files(self.seed, 'stream')
                    events = rpc_results(decode_response(files['start.response.bin'])[2], 'approval-start')
                    target = next(event[arm] for event in events if arm in event)
                    key = 'contextId' if field == 'context' else ('id' if arm == 'task' else 'taskId')
                    self.assertEqual(target[key], 'authored-' + field)
                    target[key] = 'wrong-' + field
                    body = b''.join(b'data: ' + encoded({'jsonrpc': '2.0', 'id': 'approval-start',
                        'result': event}) + b'\r\n\r\n' for event in events)
                    files['start.response.bin'] = response(body, 'text/event-stream')
                    self.write(files)
                    with self.assertRaisesRegex(ValueError, 'streamed events'):
                        check(self.folder, self.seed)

    def test_incomplete_capture_is_rejected(self):
        files = constructed_files(self.seed, 'sync')
        receipt = json.loads(files['start.exchange.json'])
        receipt['response_eof'] = False
        files['start.exchange.json'] = encoded(receipt)
        self.write(files)
        with self.assertRaisesRegex(ValueError, 'complete exchange'):
            check(self.folder, self.seed)

    def test_changed_approver_is_rejected(self):
        files = constructed_files(self.seed, 'sync')
        boundaries = json.loads(files['boundaries.json'])
        for row in boundaries[7:]:
            row['database']['tables']['audit_log'][0]['approved_by'] = 'someone-else'
            files[row['label'] + '.snapshot.json'] = encoded(row)
        files['boundaries.json'] = encoded(boundaries)
        self.write(files)
        with self.assertRaisesRegex(ValueError, 'attributed'):
            check(self.folder, self.seed)

    def test_network_attempt_is_rejected(self):
        files = constructed_files(self.seed, 'sync')
        service = json.loads(files['service-result.json'])
        service['network_errors'] = [{'event': 'socket.connect'}]
        files['service-result.json'] = encoded(service)
        self.write(files)
        with self.assertRaisesRegex(ValueError, 'offline clean'):
            check(self.folder, self.seed)

    def test_streaming_error_or_truncation_is_rejected(self):
        for body in [b'data: {"jsonrpc":"2.0","id":"approval-resume","error":{"code":-1}}\n\n', b'data: {}']:
            files = constructed_files(self.seed, 'stream')
            files['resume.response.bin'] = response(body, 'text/event-stream')
            self.write(files)
            with self.assertRaises(ValueError):
                check(self.folder, self.seed)


if __name__ == '__main__':
    unittest.main()
