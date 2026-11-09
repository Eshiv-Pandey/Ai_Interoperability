"""Independent adversarial checks for the bounded public pending-state adapter.

All observations in this file are authored software fixtures, not live evidence.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from interoperability import pending_admission as adapter
from interoperability import refinement, refinement_oracle

NOW = 100
URL = 'http://127.0.0.1:9100/'


def tool_call(name, arguments):
    return {'method': 'tools/call', 'params': {'name': name, 'arguments': arguments}}


def observation(seq, observed_at, request, body):
    return {'seq': seq, 'observed_at': observed_at, 'request': request, 'body': body}


def authored_snapshot():
    rationale = 'Inventory is down and INC-002 matches the service-down runbook.'
    raw_call = {'id': 'confirmation-A', 'name': 'adk_request_confirmation',
                'args': {'originalFunctionCall': {'id': 'restart-A', 'name': 'restart_service',
                                                 'args': {'name': 'inventory'}},
                         'toolConfirmation': {'confirmed': False}}}
    raw_task = {'id': 'task-A', 'contextId': 'context-A',
                'status': {'state': 'TASK_STATE_INPUT_REQUIRED', 'message': {
                    'parts': [{'metadata': {'adk_type': 'function_call'}, 'data': raw_call}]}}}
    tools = [{'name': 'a2a_request', 'inputSchema': {
        'type': 'object', 'properties': {'url': {'type': 'string'},
          'method': {'type': 'string', 'enum': ['GetTask', 'SendMessage']},
          'params': {'type': 'object', 'additionalProperties': {}}},
        'required': ['url', 'method'], 'additionalProperties': False},
        'annotations': {'readOnlyHint': False, 'destructiveHint': True}}]
    body = lambda value: {'structuredContent': value}
    answer = {'id': 'confirmation-A', 'name': 'adk_request_confirmation',
              'response': {'confirmed': True, 'payload': {'rationale': rationale}}}
    return {'schema_version': 'agentops-pending-admission/1', 'id': 'authored-pending-A',
            'route': {'arm': 'B7', 'agent_base_url': URL},
            'deployment': {'origin': URL.rstrip('/'), 'header_mode': 'version-header',
                           'serializer': 'mgcrea-raw-jsonrpc/1',
                           'service_contract': 'agentops-inventory-confirmation-fixture/1'},
            'observations': {
                'tools': observation(1, 94, {'method': 'tools/list', 'params': {}}, {'tools': tools}),
                'discovery': observation(2, 95, tool_call('a2a_discover_agent', {'url': URL}),
                    body({'url': URL, 'card': {'interfaces': [{'url': URL, 'protocol': 'JSONRPC'}]}})),
                'initial': observation(3, 96,
                    tool_call('a2a_send_message', {'url': URL, 'text': 'Restart inventory.'}),
                    body({'task': {'id': 'task-A', 'context_id': 'context-A'}})),
                'pending': observation(4, 97,
                    tool_call('a2a_get_task', {'task_id': 'task-A', 'history_length': 100, 'refresh': True}),
                    body({'id': 'task-A', 'context_id': 'context-A', 'state': 'input_required'})),
                'raw': observation(5, 98,
                    tool_call('a2a_request', {'url': URL, 'method': 'GetTask',
                                             'params': {'id': 'task-A', 'historyLength': 100}}),
                    body({'jsonrpc': '2.0', 'id': 7, 'result': raw_task}))},
            'rationale': rationale,
            'proposed_call': tool_call('a2a_request', {'url': URL, 'method': 'SendMessage', 'params': {
                'message': {'messageId': 'agentops-public-confirmation', 'role': 'ROLE_USER',
                            'taskId': 'task-A', 'contextId': 'context-A',
                            'parts': [{'data': answer, 'metadata': {'adk_type': 'function_response'}}]}}}),
            'valid_until': 110}


def raw_task(snapshot):
    return snapshot['observations']['raw']['body']['structuredContent']['result']


def public_confirmation(snapshot):
    return raw_task(snapshot)['status']['message']['parts'][0]['data']


def proposed_message(snapshot):
    return snapshot['proposed_call']['params']['arguments']['params']['message']


class PendingAdmission(unittest.TestCase):
    def assert_no_dispatch(self, snapshot, now=NOW):
        result = adapter.admit_pending(snapshot, now)
        summary = {key: result.get(key) for key in ('status', 'decision', 'reason', 'error')}
        self.assertFalse(result['dispatch_permitted'], summary)
        self.assertIsNone(result['request'], summary)
        self.assertEqual(result['decision'], 'unknown', summary)
        return result

    def test_public_association_builds_a_conditional_checked_witness(self):
        snapshot = authored_snapshot()
        original = deepcopy(snapshot)
        profile = adapter.build_profile(snapshot, NOW)
        self.assertEqual(profile['schema_version'], 'recipe-continuation/1')
        self.assertFalse(profile['coverage']['complete'])
        self.assertFalse(profile['model']['evidence']['complete'])
        result = adapter.admit_pending(snapshot, NOW)
        self.assertEqual(result['decision'], 'supported', result)
        self.assertTrue(result['certificate_valid'], result)
        self.assertTrue(result['dispatch_permitted'], result)
        self.assertEqual(result['request'], snapshot['proposed_call'])
        self.assertEqual(snapshot, original)
        self.assertTrue(refinement_oracle.check_certificate(result['profile'], result['result'], NOW))

    def test_missing_public_confirmation_id_does_not_get_guessed_from_proposal(self):
        snapshot = authored_snapshot()
        del public_confirmation(snapshot)['id']
        self.assert_no_dispatch(snapshot)

    def test_json_text_tool_results_use_the_same_public_associations(self):
        snapshot = authored_snapshot()
        for name, row in snapshot['observations'].items():
            if name != 'tools':
                row['body'] = {'content': [{'type': 'text', 'text': json.dumps(row['body']['structuredContent'])}]}
        result = adapter.admit_pending(snapshot, NOW)
        self.assertEqual(result['decision'], 'supported', result.get('reason'))
        self.assertTrue(result['certificate_valid'])
        self.assertEqual(result['request'], snapshot['proposed_call'])

    def test_ambiguous_duplicate_keys_and_tool_errors_do_not_supply_public_facts(self):
        for mutation in ('duplicate_key', 'error', 'invalid_json'):
            snapshot = authored_snapshot()
            row = snapshot['observations']['raw']
            payload = json.dumps(row['body']['structuredContent'])
            if mutation == 'duplicate_key':
                payload = payload.replace('"jsonrpc": "2.0"', '"jsonrpc": "1.0", "jsonrpc": "2.0"')
            elif mutation == 'invalid_json':
                payload = '{bad json}'
            row['body'] = {'content': [{'type': 'text', 'text': payload}]}
            if mutation == 'error':
                row['body']['isError'] = True
            with self.subTest(mutation=mutation):
                self.assert_no_dispatch(snapshot)

    def test_unmodeled_schema_constraints_abstain_instead_of_being_ignored(self):
        snapshot = authored_snapshot()
        snapshot['observations']['tools']['body']['tools'][0]['inputSchema']['allOf'] = [
            {'properties': {'method': {'enum': ['GetTask']}}}]
        self.assert_no_dispatch(snapshot)

    def test_multiple_confirmation_parts_are_ambiguous(self):
        for same_id in (True, False):
            snapshot = authored_snapshot()
            parts = raw_task(snapshot)['status']['message']['parts']
            other = deepcopy(parts[0])
            if not same_id:
                other['data']['id'] = 'confirmation-B'
            parts.append(other)
            with self.subTest(same_id=same_id):
                self.assert_no_dispatch(snapshot)

    def test_task_and_context_bindings_cannot_be_swapped_between_observations(self):
        for source, field in (('initial', 'id'), ('initial', 'context_id'),
                              ('pending', 'id'), ('pending', 'context_id'),
                              ('raw', 'id'), ('raw', 'contextId')):
            snapshot = authored_snapshot()
            value = snapshot['observations'][source]['body']['structuredContent']
            if source == 'initial':
                value = value['task']
            elif source == 'raw':
                value = value['result']
            value[field] = 'unrelated-B'
            with self.subTest(source=source, field=field):
                self.assert_no_dispatch(snapshot)

    def test_observation_request_must_target_the_returned_task(self):
        for source in ('pending', 'raw'):
            snapshot = authored_snapshot()
            args = snapshot['observations'][source]['request']['params']['arguments']
            if source == 'pending':
                args['task_id'] = 'unrelated-B'
            else:
                args['params']['id'] = 'unrelated-B'
            with self.subTest(source=source):
                self.assert_no_dispatch(snapshot)

    def test_nested_status_message_cannot_reassign_the_confirmation(self):
        for field in ('taskId', 'contextId'):
            snapshot = authored_snapshot()
            raw_task(snapshot)['status']['message'][field] = 'unrelated-B'
            with self.subTest(field=field):
                self.assert_no_dispatch(snapshot)

    def test_tools_list_errors_cannot_supply_admission_permissions(self):
        for field, value in (('isError', True), ('error', {'code': -32603, 'message': 'failed'})):
            snapshot = authored_snapshot()
            snapshot['observations']['tools']['body'][field] = value
            with self.subTest(field=field):
                self.assert_no_dispatch(snapshot)

    def test_raw_rpc_envelope_requires_a_valid_response_identifier(self):
        for identifier in ({'id': 7}, [7], True):
            snapshot = authored_snapshot()
            snapshot['observations']['raw']['body']['structuredContent']['id'] = identifier
            with self.subTest(identifier=identifier):
                self.assert_no_dispatch(snapshot)

    def test_both_pending_views_must_still_be_input_required(self):
        for source in ('pending', 'raw'):
            snapshot = authored_snapshot()
            if source == 'pending':
                snapshot['observations'][source]['body']['structuredContent']['state'] = 'working'
            else:
                raw_task(snapshot)['status']['state'] = 'TASK_STATE_WORKING'
            with self.subTest(source=source):
                self.assert_no_dispatch(snapshot)

    def test_confirmation_must_name_exact_unconfirmed_inventory_operation(self):
        for field, value in (('operation', 'delete_service'), ('target', 'billing'), ('confirmed', True)):
            snapshot = authored_snapshot()
            args = public_confirmation(snapshot)['args']
            if field == 'operation':
                args['originalFunctionCall']['name'] = value
            elif field == 'target':
                args['originalFunctionCall']['args']['name'] = value
            else:
                args['toolConfirmation']['confirmed'] = value
            with self.subTest(field=field):
                self.assert_no_dispatch(snapshot)

    def test_stale_future_and_overlong_observation_windows_do_not_dispatch(self):
        for now, until, observed in ((111, 110, 98), (100, 110, 101), (100, 120, 98)):
            snapshot = authored_snapshot()
            snapshot['valid_until'] = until
            snapshot['observations']['raw']['observed_at'] = observed
            with self.subTest(now=now, until=until, observed=observed):
                self.assert_no_dispatch(snapshot, now)

    def test_ordered_observation_sequence_and_clock_are_required(self):
        for field, value in (('seq', 4), ('observed_at', 96)):
            snapshot = authored_snapshot()
            snapshot['observations']['raw'][field] = value
            with self.subTest(field=field):
                self.assert_no_dispatch(snapshot)

    def test_read_only_or_missing_raw_method_prevents_dispatch(self):
        for mutation in ('hint', 'method', 'duplicate', 'missing'):
            snapshot = authored_snapshot()
            tools = snapshot['observations']['tools']['body']['tools']
            if mutation == 'hint':
                tools[0]['annotations']['readOnlyHint'] = True
            elif mutation == 'method':
                tools[0]['inputSchema']['properties']['method']['enum'] = ['GetTask']
            elif mutation == 'duplicate':
                tools.append(deepcopy(tools[0]))
            else:
                tools.clear()
            with self.subTest(mutation=mutation):
                self.assert_no_dispatch(snapshot)

    def test_declared_raw_argument_schema_cannot_be_ignored(self):
        for mutation in ('params_type', 'unexpected_required', 'url_enum'):
            snapshot = authored_snapshot()
            schema = snapshot['observations']['tools']['body']['tools'][0]['inputSchema']
            if mutation == 'params_type':
                schema['properties']['params'] = {'type': 'string'}
            elif mutation == 'unexpected_required':
                schema['required'].append('authorization')
                schema['properties']['authorization'] = {'type': 'string'}
            else:
                schema['properties']['url']['enum'] = ['http://127.0.0.1:9999/']
            with self.subTest(mutation=mutation):
                self.assert_no_dispatch(snapshot)

    def test_header_configuration_must_apply_to_discovered_endpoint_origin(self):
        for mutation in ('mode', 'unknown', 'configured_origin', 'card_origin'):
            snapshot = authored_snapshot()
            if mutation == 'mode':
                snapshot['deployment']['header_mode'] = 'passthrough'
            elif mutation == 'unknown':
                snapshot['deployment']['header_mode'] = 'unknown'
            elif mutation == 'configured_origin':
                snapshot['deployment']['origin'] = 'http://127.0.0.1:9999'
            else:
                snapshot['observations']['discovery']['body']['structuredContent']['card']['interfaces'][0]['url'] = 'http://127.0.0.1:9999/'
            with self.subTest(mutation=mutation):
                self.assert_no_dispatch(snapshot)

    def test_unknown_serializer_or_service_contract_cannot_establish_completion(self):
        for field in ('serializer', 'service_contract'):
            snapshot = authored_snapshot()
            snapshot['deployment'][field] = 'unmodeled'
            with self.subTest(field=field):
                self.assert_no_dispatch(snapshot)

    def test_whitespace_or_overlong_rationale_is_not_a_valid_fixture_confirmation(self):
        for rationale in ('   \t\n', 'x' * 501):
            snapshot = authored_snapshot()
            snapshot['rationale'] = rationale
            proposed_message(snapshot)['parts'][0]['data']['response']['payload']['rationale'] = rationale
            with self.subTest(length=len(rationale)):
                self.assert_no_dispatch(snapshot)

    def test_proposed_request_cannot_change_public_associations_or_payload(self):
        for field in ('taskId', 'contextId', 'callId', 'name', 'rationale', 'part_type'):
            snapshot = authored_snapshot()
            message = proposed_message(snapshot)
            data = message['parts'][0]['data']
            if field in ('taskId', 'contextId'):
                message[field] = 'unrelated-B'
            elif field == 'callId':
                data['id'] = 'unrelated-B'
            elif field == 'name':
                data['name'] = 'different_function'
            elif field == 'rationale':
                data['response']['payload']['rationale'] = 'different public choice'
            else:
                message['parts'] = [{'text': json.dumps(data)}]
            with self.subTest(field=field):
                self.assert_no_dispatch(snapshot)

    def test_low_budget_never_authorizes_a_request(self):
        result = adapter.admit_pending(authored_snapshot(), NOW, budget=1)
        self.assertEqual(result['decision'], 'unknown')
        self.assertFalse(result['dispatch_permitted'])
        self.assertIsNone(result['request'])

    def test_solver_mutation_does_not_authorize_and_cannot_mutate_snapshot(self):
        snapshot = authored_snapshot()
        original = deepcopy(snapshot)
        evaluate = refinement.evaluate
        def mutate(profile, now, budget=None):
            profile['id'] += '-mutated'
            return evaluate(profile, now, budget)
        with patch.object(adapter.refinement, 'evaluate', side_effect=mutate):
            self.assert_no_dispatch(snapshot)
        self.assertEqual(snapshot, original)

    def test_forged_certificate_and_checker_failure_do_not_dispatch(self):
        evaluate = refinement.evaluate
        def forge(profile, now, budget=None):
            result = evaluate(profile, now, budget)
            result['certificate']['steps'][0]['request'] = {'forged': True}
            return result
        with patch.object(adapter.refinement, 'evaluate', side_effect=forge):
            self.assert_no_dispatch(authored_snapshot())
        with patch.object(adapter.refinement_oracle, 'check_certificate', return_value=False):
            self.assert_no_dispatch(authored_snapshot())

    def test_certificate_from_a_different_snapshot_cannot_be_reused(self):
        first = authored_snapshot()
        old_result = refinement.evaluate(adapter.build_profile(first, NOW), NOW)
        second = deepcopy(first)
        second['rationale'] += ' Confirmed by the current fixture operator.'
        proposed_message(second)['parts'][0]['data']['response']['payload']['rationale'] = second['rationale']
        with patch.object(adapter.refinement, 'evaluate', return_value=old_result):
            self.assert_no_dispatch(second)


if __name__ == '__main__':
    unittest.main()
