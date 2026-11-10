"""Constructed admission/ordering controls, with no original AP2 imports."""
from __future__ import annotations

import asyncio
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from interoperability import ap2_hp_durable_observer_v1 as durable
from interoperability import ap2_pending_admission_v4 as admission

spec = importlib.util.spec_from_file_location('_ap2_development_v4', ROOT / 'scripts/ap2_reference_development_v4.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
NOW = 1_900_000_000


def fixture():
    challenge = {'type': 'otp', 'display_text': 'Constructed issuer challenge.(Demo only hint: the code is 123)'}
    task = {'kind': 'task', 'id': 'constructed-original-merchant', 'contextId': 'constructed-original-context',
            'status': {'state': 'input-required', 'message': {
                'kind': 'message', 'role': 'agent', 'messageId': 'constructed-challenge-message',
                'contextId': 'constructed-original-context', 'taskId': 'constructed-nested-processor-reference',
                'metadata': None, 'extensions': None, 'referenceTaskIds': None,
                'parts': [{'kind': 'text', 'text': 'Constructed challenge request', 'metadata': None},
                          {'kind': 'data', 'data': {'challenge': challenge}, 'metadata': None}]}}}
    caller = {'initiate_payment_task_id': task['id'], 'shopping_context_id': task['contextId'],
              'payment_mandate_sdjwt': 'constructed-already-held-payment',
              'checkout_mandate_sdjwt': 'constructed-already-held-checkout', 'risk_data': 'constructed-held-risk'}
    message = {'kind': 'message', 'role': 'agent', 'messageId': 'constructed-original-builder-message',
               'taskId': task['id'], 'contextId': task['contextId'], 'metadata': None, 'extensions': None,
               'referenceTaskIds': None, 'parts': [{'kind': 'text', 'text': admission.TEXT, 'metadata': None}]}
    for key, value in [(admission.PAYMENT, caller['payment_mandate_sdjwt']),
                       ('shopping_agent_id', 'trusted_shopping_agent'), ('challenge_response', '123'),
                       ('risk_data', caller['risk_data']), (admission.CHECKOUT, caller['checkout_mandate_sdjwt'])]:
        message['parts'].append({'kind': 'data', 'data': {key: value}, 'metadata': None})
    prepared = admission.prepare_profile(task, caller, message, '123', NOW)
    return task, caller, message, prepared


def raw_request(message):
    return admission.encoded({'jsonrpc': '2.0', 'id': 'constructed-actual-sdk-rpc-id', 'method': 'message/send',
                              'params': {'message': admission.wire_message(message)}})


class ProfileControls(unittest.TestCase):
    def test_positive_incomplete_model_has_independently_checked_exact_original_request(self):
        task, caller, message, prepared = fixture()
        receipt = admission.evaluate_prepared(prepared, NOW)
        self.assertTrue(receipt['dispatch_permitted'])
        self.assertTrue(receipt['certificate_valid'])
        certificate = receipt['solver_result']['certificate']
        self.assertEqual(certificate['kind'], 'recipe-path')
        self.assertEqual(certificate['transition_ids'], [admission.EDGE])
        self.assertEqual(certificate['steps'][0]['request']['message'], message)
        self.assertEqual(certificate['profile_sha256'], admission.refinement.digest(prepared['profile']))
        self.assertFalse(prepared['profile']['coverage']['complete'])
        self.assertFalse(prepared['profile']['model']['evidence']['complete'])
        self.assertFalse(receipt['actual_task_completion_established_by_certificate'])
        self.assertFalse(receipt['whole_route_non_support_inference_allowed'])
        self.assertEqual(prepared['pending_task'], task)
        self.assertEqual(prepared['original_request']['message'], message)
        self.assertEqual(caller['payment_mandate_sdjwt'], 'constructed-already-held-payment')

    def test_nested_processor_reference_cannot_replace_merchant_continuation_authority(self):
        task, caller, message, prepared = fixture()
        self.assertEqual(prepared['profile']['initial_bindings']['merchant_task_id'], task['id'])
        message['taskId'] = task['status']['message']['taskId']
        with self.assertRaisesRegex(ValueError, 'authority_mismatch'):
            admission.prepare_profile(task, caller, message, '123', NOW)

    def test_demo_123_must_be_uniquely_offered_in_the_actual_public_challenge(self):
        task, caller, message, _ = fixture()
        for display in ['Please enter your private code', '(Demo only hint: the code is 456)',
                        '(Demo only hint: the code is 123)(Demo only hint: the code is 123)']:
            changed = deepcopy(task)
            changed['status']['message']['parts'][1]['data']['challenge']['display_text'] = display
            with self.subTest(display=display), self.assertRaisesRegex(ValueError, '123_not_uniquely_offered'):
                admission.prepare_profile(changed, caller, message, '123', NOW)
        with self.assertRaisesRegex(ValueError, 'response_not_the_public_demo_recipe'):
            admission.prepare_profile(task, caller, message, '456', NOW)

    def test_duplicate_or_non_otp_public_challenge_is_refused(self):
        task, caller, message, _ = fixture()
        duplicate = deepcopy(task)
        duplicate['status']['message']['parts'].append(deepcopy(duplicate['status']['message']['parts'][1]))
        with self.assertRaisesRegex(ValueError, 'unique_public_challenge'):
            admission.prepare_profile(duplicate, caller, message, '123', NOW)
        task['status']['message']['parts'][1]['data']['challenge']['type'] = 'private-code'
        with self.assertRaisesRegex(ValueError, 'unmodeled_public_challenge'):
            admission.prepare_profile(task, caller, message, '123', NOW)

    def test_actual_pending_state_and_context_are_required(self):
        task, caller, message, _ = fixture()
        for mutation in [('state', 'completed'), ('context', 'unrelated-context')]:
            changed = deepcopy(task)
            if mutation[0] == 'state':
                changed['status']['state'] = mutation[1]
            else:
                changed['status']['message']['contextId'] = mutation[1]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                admission.prepare_profile(changed, caller, message, '123', NOW)

    def test_caller_task_and_context_substitution_are_refused(self):
        task, caller, message, _ = fixture()
        for key in ('initiate_payment_task_id', 'shopping_context_id'):
            changed = dict(caller, **{key: 'unrelated-held-value'})
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'caller_pending_authority_mismatch'):
                admission.prepare_profile(task, changed, message, '123', NOW)

    def test_request_cannot_substitute_mandates_risk_or_shopping_identity(self):
        task, caller, message, _ = fixture()
        for index in (1, 2, 4, 5):
            changed = deepcopy(message)
            key = next(iter(changed['parts'][index]['data']))
            changed['parts'][index]['data'][key] = 'invented-value'
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, 'caller_value_mismatch'):
                admission.prepare_profile(task, caller, changed, '123', NOW)

    def test_original_falsey_risk_omission_is_preserved_and_debug_data_is_not_added(self):
        task, caller, message, _ = fixture()
        caller['risk_data'] = ''
        del message['parts'][4]
        prepared = admission.prepare_profile(task, caller, message, '123', NOW)
        receipt = admission.evaluate_prepared(prepared, NOW)
        self.assertTrue(receipt['dispatch_permitted'])
        self.assertEqual(receipt['solver_result']['certificate']['steps'][0]['request']['message'], message)
        message['parts'].append({'kind': 'data', 'data': {'debug_mode': False}, 'metadata': None})
        with self.assertRaisesRegex(ValueError, 'part_count_mismatch'):
            admission.prepare_profile(task, caller, message, '123', NOW)

    def test_unknown_work_budget_result_is_retained_and_cannot_dispatch(self):
        prepared = fixture()[3]
        receipt = admission.evaluate_prepared(prepared, NOW, budget=1)
        self.assertEqual(receipt['decision'], 'unknown')
        self.assertEqual(receipt['solver_result']['reason'], 'work_budget_exhausted')
        self.assertIsNone(receipt['solver_result']['certificate'])
        self.assertFalse(receipt['certificate_valid'])
        self.assertFalse(receipt['dispatch_permitted'])
        self.assertFalse(receipt['whole_route_non_support_inference_allowed'])

    def test_checker_rejection_cannot_be_bypassed_by_supported_solver_label(self):
        prepared = fixture()[3]
        with patch.object(admission.refinement_oracle, 'check_certificate', return_value=False):
            receipt = admission.evaluate_prepared(prepared, NOW)
        self.assertEqual(receipt['solver_result']['decision'], 'supported')
        self.assertFalse(receipt['dispatch_permitted'])
        self.assertEqual(receipt['refusal_reason'], 'independent_certificate_check_failed')

    def test_tampered_witness_argument_request_or_clock_is_independently_rejected(self):
        prepared = fixture()[3]
        result = admission.evaluate_prepared(prepared, NOW)['solver_result']
        mutations = [lambda r: r['certificate']['steps'][0]['args'].update(otp_response='456'),
                     lambda r: r['certificate']['steps'][0]['request']['message'].update(taskId='wrong-task'),
                     lambda r: r['certificate'].update(checked_at=NOW - 1),
                     lambda r: r['certificate'].update(profile_sha256='0' * 64)]
        for index, mutate in enumerate(mutations):
            changed = deepcopy(result)
            mutate(changed)
            with self.subTest(index=index), self.assertRaises(ValueError):
                admission.verify_supported(prepared['profile'], changed, prepared['original_request'], NOW)

    def test_raw_request_matches_actual_builder_with_only_optional_nulls_removed(self):
        task, _, message, prepared = fixture()
        receipt = admission.evaluate_prepared(prepared, NOW)
        raw = raw_request(message)
        binding = admission.bind_raw_request(prepared, receipt, raw, NOW + 1)
        self.assertEqual(binding['original_merchant_task_id'], task['id'])
        self.assertEqual(binding['original_message_id'], message['messageId'])
        self.assertEqual(binding['raw_request']['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertTrue(binding['independent_checker_rechecked_at_dispatch'])
        self.assertEqual(admission.wire_message({'parts': [{'kind': 'data', 'metadata': None, 'data': {'explicit_null': None}}]}),
                         {'parts': [{'kind': 'data', 'data': {'explicit_null': None}}]})

    def test_raw_task_context_message_or_mandate_substitution_is_refused(self):
        _, _, message, prepared = fixture()
        receipt = admission.evaluate_prepared(prepared, NOW)
        for field in ('taskId', 'contextId', 'messageId'):
            changed = deepcopy(message)
            changed[field] = 'unrelated-actual-request'
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'raw_request_differs'):
                admission.bind_raw_request(prepared, receipt, raw_request(changed), NOW)
        changed = deepcopy(message)
        changed['parts'][1]['data'][admission.PAYMENT] = 'invented-payment'
        with self.assertRaisesRegex(ValueError, 'raw_request_differs'):
            admission.bind_raw_request(prepared, receipt, raw_request(changed), NOW)

    def test_expiry_and_changed_profile_stop_raw_dispatch(self):
        _, _, message, prepared = fixture()
        receipt = admission.evaluate_prepared(prepared, NOW)
        with self.assertRaises(ValueError):
            admission.bind_raw_request(prepared, receipt, raw_request(message), NOW + 16)
        prepared['profile']['initial_bindings']['merchant_task_id'] = 'changed-after-check'
        with self.assertRaisesRegex(ValueError, 'input_or_profile_changed'):
            admission.bind_raw_request(prepared, receipt, raw_request(message), NOW)

    def test_raw_duplicate_keys_bool_rpc_ids_and_unknown_fields_do_not_pass(self):
        _, _, message, prepared = fixture()
        receipt = admission.evaluate_prepared(prepared, NOW)
        duplicate = b'{"jsonrpc":"2.0","id":"a","id":"b"}'
        with self.assertRaisesRegex(ValueError, 'duplicate_json_key'):
            admission.bind_raw_request(prepared, receipt, duplicate, NOW)
        payload = admission.decode_json(raw_request(message))
        payload['id'] = True
        with self.assertRaisesRegex(ValueError, 'unmodeled_raw'):
            admission.bind_raw_request(prepared, receipt, admission.encoded(payload), NOW)
        changed = deepcopy(message)
        changed['unexpected'] = None
        with self.assertRaisesRegex(ValueError, 'raw_request_differs'):
            admission.bind_raw_request(prepared, receipt, raw_request(changed), NOW)

    def test_frozen_v3_runner_tests_and_documentation_remain_exact(self):
        expected = {'scripts/ap2_reference_development_v3.py': '14f61944715d44cb1c43e76b65500992ec1470d441c5874a1ebf2af29a0395ad',
                    'tests/test_ap2_reference_development_v3.py': '2008e68060f562d2592aea263e2090f2e23fdda871f26a1dc06cbe85cab7ebf6',
                    'docs/research/ap2-reference-development-v3.md': '31f7f92d6d06082fe14999022a2d164e3eb69aff5c0ae10779645cac4bb0d8db'}
        for name, sha in expected.items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), sha)


class BoundaryControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.output = Path(self.temporary.name).resolve()
        self.recorder = durable.DurableRecorder.allocate(self.output / 'observations',
                                                        {'merchant_raw': 'raw_asgi', 'merchant_public': 'public'})
        self.task, self.caller, self.message, self.prepared = fixture()
        self.public_records = []
        self.current_task = self.task

        async def constructed_app(scope, receive, send):
            request = admission.decode_json((await receive())['body'])
            await send({'type': 'http.response.start', 'status': 200, 'headers': []})
            await send({'type': 'http.response.body', 'body': admission.encoded({
                'jsonrpc': '2.0', 'id': request['id'], 'result': self.current_task})})
        self.wrapper = durable.RawAsgiCapture(constructed_app, self.recorder.sink('merchant_raw'))
        start = deepcopy(self.message)
        start['messageId'] = 'constructed-original-start-message'
        start['taskId'] = None
        start['parts'] = [{'kind': 'text', 'text': 'Constructed original payment start', 'metadata': None}]
        self._public(0, 'attempt', start)
        self._exchange(raw_request(start))
        self._public(0, 'returned', self.task)
        self.boundary = runner.AdmissionBoundary(self.output, self.recorder, admission, durable, clock=lambda: NOW)

    def tearDown(self):
        self.wrapper.finish()
        self.recorder.finish_stream('merchant_public', {'source_complete': True, 'active_operations': 0,
                                                       'attempted_records': len(self.public_records)})
        if not self.recorder.sealed:
            self.recorder.publish(allow_incomplete=True)
        self.recorder.close()
        self.temporary.cleanup()

    def _public(self, call, boundary, value):
        row = {'sequence': len(self.public_records), 'call': call, 'boundary': boundary,
               'operation': 'send_a2a_message', 'endpoint': admission.MERCHANT, 'public_value': deepcopy(value)}
        self.public_records.append(row)
        self.recorder.sink('merchant_public')(row)

    def _exchange(self, raw):
        async def receive():
            return {'type': 'http.request', 'body': raw, 'more_body': False}
        async def send(_):
            return None
        scope = {'type': 'http', 'method': 'POST', 'path': '/a2a/merchant_agent',
                 'headers': [(b'x-a2a-extensions', admission.EXTENSION.encode())]}
        asyncio.run(self.wrapper(scope, receive, send))

    def test_real_durable_prefix_and_raw_exchange_bind_admission_before_constructed_send(self):
        self.boundary.begin(self.task, self.caller, self.message, '123')
        self.assertFalse(self.boundary.dispatched)
        self.assertTrue((self.boundary.path / 'admission-before-send.json').exists())
        self.assertEqual(self.boundary.receipt['pending_raw_binding']['challenge_message_task_reference'],
                         'constructed-nested-processor-reference')
        self._public(1, 'attempt', self.message)
        raw = raw_request(self.message)
        self.boundary.authorize_raw(raw)
        self.current_task = deepcopy(self.task)
        self.current_task['status']['state'] = 'completed'  # constructed checker control only
        self._exchange(raw)
        self._public(1, 'returned', self.current_task)
        self.assertTrue(self.boundary.finish(self.public_records))
        observed = admission.decode_json((self.boundary.path / 'observed-continuation.json').read_bytes())
        self.assertTrue(observed['actual_original_task_completed'])
        self.assertEqual(observed['original_merchant_task_id'], self.task['id'])
        self.assertGreaterEqual(observed['raw_continuation_first_global_index'],
                                self.boundary.dispatch['journal_checkpoint_before_dispatch']['events'])

    def test_admission_failure_retains_unknown_result_and_sends_nothing(self):
        evaluate = admission.shared_lift.evaluate
        with patch.object(admission.shared_lift, 'evaluate', side_effect=lambda p, n, budget: evaluate(p, n, budget=1)):
            with self.assertRaisesRegex(ValueError, 'checker_refused'):
                self.boundary.begin(self.task, self.caller, self.message, '123')
        result = admission.decode_json((self.boundary.path / 'solver-result.json').read_bytes())
        self.assertEqual(result['decision'], 'unknown')
        self.assertFalse(self.boundary.dispatched)
        self.assertTrue((self.boundary.path / 'admission-refusal.json').exists())

    def test_artifact_tamper_before_dispatch_is_refused_and_retained(self):
        self.boundary.begin(self.task, self.caller, self.message, '123')
        (self.boundary.path / 'profile.json').write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'artifact_changed'):
            self.boundary.authorize_raw(raw_request(self.message))
        self.assertFalse(self.boundary.dispatched)
        self.assertTrue((self.boundary.path / 'raw-dispatch-refusal.json').exists())

    def test_once_only_admission_and_raw_dispatch_reject_replays(self):
        self.boundary.begin(self.task, self.caller, self.message, '123')
        with self.assertRaisesRegex(ValueError, 'once_only'):
            self.boundary.begin(self.task, self.caller, self.message, '123')
        self._public(1, 'attempt', self.message)
        self.boundary.authorize_raw(raw_request(self.message))
        with self.assertRaisesRegex(ValueError, 'once_only'):
            self.boundary.authorize_raw(raw_request(self.message))

    def test_owned_subclass_returns_the_same_original_builder_object_after_admission(self):
        message, calls = self.message, []
        class ConstructedOriginal:
            def _payment_message(self, response=None, resume=False):
                calls.append((response, resume))
                return message
        adapted = runner.make_admitted_coordinator(ConstructedOriginal, self.boundary)()
        adapted.bindings = SimpleNamespace(merchant=SimpleNamespace(
            calls=[{'error': None, 'public_result': self.task}], serializer=deepcopy))
        adapted.context = SimpleNamespace(state=self.caller)
        self.assertIs(adapted._payment_message('123', resume=True), message)
        self.assertEqual(calls, [('123', True)])
        self.assertTrue(self.boundary.receipt['certificate_valid'])
        self.assertFalse(self.boundary.dispatched)


if __name__ == '__main__':
    unittest.main()
