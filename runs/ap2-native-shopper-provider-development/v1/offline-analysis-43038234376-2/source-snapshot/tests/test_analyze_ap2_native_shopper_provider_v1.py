"""Constructed offline evidence-integrity controls, never actual run results."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('native_shopper_analysis_controls', ROOT / 'scripts/analyze_ap2_native_shopper_provider_v1.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
FACTS = {'initial_request': 'fixture initial request', 'maximum_budget_USD': 100, 'otp_response': '123'}


class MemoryRead:
    def __init__(self, members):
        self.members = members

    def raw(self, name, optional=False):
        if optional:
            return self.members.get(name)
        return self.members[name]

    def rows(self, name):
        return [json.loads(line) for line in self.raw(name, optional=True).splitlines()] if self.raw(name, optional=True) else []


def visible(prompt, turn=0):
    return {'turn': turn, 'event': {'author': 'shopper', 'content': {'role': 'model', 'parts': [{'text': prompt}]}}}


def conversation(prompt, turn=0):
    return [{'turn': 0, 'role': 'user', 'text': FACTS['initial_request']},
            {'turn': turn, 'role': 'model', 'author': 'shopper', 'text': prompt}]


def decision(prompt, category='otp', reply='123', turn=0):
    return {'turn': turn, 'visible_prompt_sha256': M.digest(prompt.encode())['sha256'],
            'session_or_tool_state_used': False, 'reply': {'category': category, 'text': reply}}


class PublicEvidenceControls(unittest.TestCase):
    def test_original_ADK_error_event_is_retained_without_becoming_visible_conversation(self):
        row = {'turn': 0, 'event': {'author': 'root_agent', 'errorMessage': 'Maximum retries exhausted.', 'customMetadata': {'error_type': 'ServerError'}}}
        result = M.public_analysis([row], [], [], [], FACTS)
        self.assertEqual(len(result['raw_ADK_error_events']), 1)
        self.assertEqual(result['visible_model_messages'], [])
        self.assertEqual(result['business_call_count'], 0)

    def test_raw_visible_text_mismatch_is_detected(self):
        result = M.public_analysis([visible('raw answer')], conversation('different answer'), [], [], FACTS)
        self.assertIn('visible_conversation_and_raw_ADK_final_text_differ', result['consistency_questions'])

    def test_thought_and_function_parts_never_become_visible_text(self):
        event = {'author': 'shopper', 'content': {'role': 'model', 'parts': [{'text': 'private reasoning', 'thought': True}, {'text': 'visible answer'}]}}
        self.assertEqual(M.visible_text(event), 'visible answer')
        event['content']['parts'].append({'functionCall': {'name': 'find_products', 'args': {}}})
        self.assertEqual(M.visible_text(event), '')

    def test_partial_and_code_execution_output_are_excluded(self):
        event = visible('partial')['event']
        event['partial'] = True
        self.assertEqual(M.visible_text(event), '')
        event['actions'] = {'skipSummarization': True}
        self.assertEqual(M.visible_text(event), 'partial')
        event['partial'] = False
        event['content']['parts'].append({'codeExecutionResult': {'output': 'raw'}})
        self.assertEqual(M.visible_text(event), 'partial')
        event['actions'] = {}
        self.assertEqual(M.visible_text(event), '')
        event['content']['parts'][-1] = {'codeExecutionResult': {}}
        self.assertEqual(M.visible_text(event), '')

    def test_missing_raw_tool_terminal_is_detected(self):
        event = {'turn': 0, 'event': {'author': 'shopper', 'content': {'parts': [{'functionCall': {'name': 'find_products', 'id': 'fixture-call', 'args': {}}}]}}}
        result = M.public_analysis([event], [], [], [], FACTS)
        self.assertIn('raw_ADK_function_call_response_census_differs', result['consistency_questions'])

    def test_equal_tool_census_does_not_hide_response_before_call_or_reused_ID(self):
        def tool(kind):
            return {'turn': 0, 'event': {'author': 'shopper', 'content': {'parts': [{kind: {'name': 'find_products', 'id': 'fixture-call', 'args': {}, 'response': {}}}]}}}
        result = M.public_analysis([tool('functionResponse'), tool('functionCall')], [], [], [], FACTS)
        self.assertIn('raw_ADK_function_response_precedes_or_lacks_call', result['consistency_questions'])
        self.assertNotIn('raw_ADK_function_call_response_census_differs', result['consistency_questions'])
        result = M.public_analysis([tool('functionCall'), tool('functionResponse')] * 2, [], [], [], FACTS)
        self.assertIn('raw_ADK_function_call_identity_reused', result['consistency_questions'])

    def test_proposed_undelivered_reply_is_not_consent(self):
        prompt = 'Please enter the OTP?'
        result = M.public_analysis([visible(prompt)], conversation(prompt), [decision(prompt)], [], FACTS)
        self.assertEqual(len(result['actor_proposed_replies']), 1)
        self.assertEqual(result['actor_delivered_replies'], [])

    def test_generic_input_required_never_corroborates_OTP_authorization(self):
        for prompt in ('Additional input is required. What would you like to do?', 'We are waiting for an OTP.'):
            with self.subTest(prompt=prompt):
                result = M.public_analysis([visible(prompt)], conversation(prompt), [decision(prompt)], [], FACTS)
                self.assertEqual(result['behavior_observations'][0]['kind'], 'OTP_reply_without_exact_frozen_fact_or_visible_request')

    def test_explicit_visible_OTP_request_and_delivery_are_corroborated(self):
        prompt = 'Please enter the OTP sent to your device.'
        users = conversation(prompt) + [{'turn': 1, 'role': 'user', 'text': '123'}]
        result = M.public_analysis([visible(prompt)], users, [decision(prompt)], [], FACTS)
        self.assertEqual(result['behavior_observations'], [])
        self.assertEqual(result['actor_delivered_replies'][0]['delivered_turn'], 1)

    def test_visible_price_is_checked_independently_of_actor_record(self):
        prompt = '1. Shoes USD 120, Cart ID fixture. Which item would you like?'
        recorded = decision(prompt, 'cart-selection', 'first option')
        recorded['reply']['visible_price_check'] = {'currency': 'USD', 'visible_amount': '20', 'maximum_budget_USD': 100, 'exchange_rate_or_hidden_state_used': False}
        result = M.public_analysis([visible(prompt)], conversation(prompt), [recorded], [], FACTS)
        self.assertEqual(result['behavior_observations'][0]['kind'], 'actor_price_record_not_independently_bound_to_visible_USD_amount')

    def test_narrow_visible_price_grammar_rejects_malformed_and_foreign_values(self):
        self.assertEqual(str(M.displayed_price('1. Shoes USD 55.99, Cart ID fixture\n2. Other USD 120, Cart ID later', 100, True)), '55.99')
        self.assertEqual(str(M.displayed_price('Cart summary:\nShoes USD 55.99\nShipping USD 10\nGrand total: USD 65.99\nPlease confirm?', 100, False)), '65.99')
        for text in ('1. Shoes CAD $20', '1. Shoes USD 1e3', '1. Shoes USD 20-30', '1. Shoes USD 12,3456', '0. Shoes USD 20\n1. Other USD 20', 'Header\n1. Shoes USD 20', '(1) Shoes USD 20', '1. Shoes USD 20\n1. Other USD 30'):
            with self.subTest(text=text):
                self.assertIsNone(M.displayed_price(text, 100, True))
        for text in ('Grand total: USD 20 plus tax', 'Order total: CAD $20', 'Order total: USD 20\nTotal due: USD 30'):
            with self.subTest(text=text):
                self.assertIsNone(M.displayed_price(text, 100, False))

    def test_receipt_requires_original_success_shape_and_has_no_settlement_claim(self):
        receipt = {'status': 'Success', 'iss': 'fixture issuer', 'iat': 7, 'reference': 'r', 'payment_id': 'p', 'psp_confirmation_id': 'psp', 'network_confirmation_id': 'network'}
        result = M.public_analysis([], [], [], [('fixture-session', {'id': 'fixture', 'state': {'payment_receipt': {'root': receipt}}})], FACTS)
        self.assertEqual(result['unique_success_receipt_records'], 1)
        self.assertFalse(result['retained_receipts'][0]['signature_or_settlement_proven'])
        receipt['iss'] = ''
        result = M.public_analysis([], [], [], [('fixture-session', {'id': 'fixture', 'state': {'payment_receipt': receipt}})], FACTS)
        self.assertEqual(result['unique_success_receipt_records'], 1)
        receipt['iat'] = True
        result = M.public_analysis([], [], [], [('fixture-session', {'id': 'fixture', 'state': {'payment_receipt': receipt}})], FACTS)
        self.assertEqual(result['unique_success_receipt_records'], 0)
        self.assertEqual(M.public_analysis([], [], [], [], FACTS)['unique_success_receipt_records'], 0)

    def test_first_displayed_cart_is_joined_without_assuming_original_catalog_order(self):
        prompt = '1. Shoes USD 20, Cart ID displayed-first\n2. Shoes USD 30, Cart ID catalog-first\nWhich item would you purchase?'
        carts = [{'cart_id': 'catalog-first', 'amount': 30, 'currency': 'USD'}, {'cart_id': 'displayed-first', 'amount': 20, 'currency': 'USD'}]
        def event(turn, part):
            return {'turn': turn, 'event': {'author': 'shopper', 'content': {'parts': [part]}}}
        events = [event(0, {'functionResponse': {'name': 'find_products', 'id': 'find', 'response': {'result': carts}}}),
                  visible(prompt), event(1, {'functionCall': {'name': 'select_cart', 'id': 'select', 'args': {'cart_id': 'displayed-first'}}}),
                  event(1, {'functionResponse': {'name': 'select_cart', 'id': 'select', 'response': {'result': 'Cart displayed-first selected.'}}})]
        delivered = [{'category': 'cart-selection', 'decision_turn': 0, 'delivered_turn': 1, 'visible_prompt': prompt, 'visible_price_check': {'visible_amount': '20'}}]
        snapshots = [('fixture-session', {'state': {'chosen_cart_id': 'displayed-first'}})]
        result = M.catalog_analysis(events, delivered, snapshots)['records'][0]
        for key in ('unique_displayed_ID_in_preceding_original_catalog', 'visible_amount_and_original_cart_currency_amount_match', 'select_cart_argument_matches_first_displayed_ID', 'original_selection_success_text_matches_displayed_ID', 'chosen_cart_state_matches_displayed_ID'):
            self.assertTrue(result[key], key)
        self.assertFalse(result['displayed_order_assumed_to_equal_catalog_order'])
        events[2]['event']['content']['parts'][0]['functionCall']['args']['cart_id'] = 'catalog-first'
        result = M.catalog_analysis(events, delivered, snapshots)['records'][0]
        self.assertFalse(result['select_cart_argument_matches_first_displayed_ID'])


class ProviderEvidenceControls(unittest.TestCase):
    def fixture(self, payload, status=200, changed_hash=False, close=True, start=True):
        request = b'{"fixture":"request"}'
        response = json.dumps(payload).encode()
        rows = []
        if start:
            rows.append({'phase': 'started', 'allocation': 1, 'time': '2026-01-01T00:00:00+00:00', 'request': M.digest(request)})
        if close:
            rows.append({'phase': 'finished', 'allocation': 1, 'http_status': status, 'response': M.digest(b'changed' if changed_hash else response)})
        return MemoryRead({'execution/provider/ledger.jsonl': b'\n'.join(json.dumps(row).encode() for row in rows),
                           'execution/provider/001.request.json': request, 'execution/provider/001.response.json': response})

    def test_failed_response_without_usage_remains_unmeasured(self):
        result = M.provider_analysis(self.fixture({'error': {'code': 503}}, 503), {'provider': {'upstream_allocations': 1}})
        self.assertEqual(result['failed_responses_missing_or_invalid_usage'], 1)
        self.assertEqual(result['allocations_with_unmeasured_usage'], 1)
        self.assertFalse(result['fully_measured'])
        self.assertFalse(result['unknown_usage_is_zero'])

    def test_response_hash_mismatch_prevents_token_use(self):
        result = M.provider_analysis(self.fixture({'usageMetadata': {'totalTokenCount': 12}}, changed_hash=True), {'provider': {'upstream_allocations': 1}})
        self.assertIn('provider_response_ledger_digest_differs', result['consistency_questions'])
        self.assertEqual(result['known_reported_tokens'], 0)
        self.assertEqual(result['allocations_with_unmeasured_usage'], 1)

    def test_success_zero_bool_and_missing_usage_are_unmeasured(self):
        for value in (0, True, None):
            with self.subTest(value=value):
                result = M.provider_analysis(self.fixture({'usageMetadata': {'totalTokenCount': value}}), {'provider': {'upstream_allocations': 1}})
                self.assertFalse(result['fully_measured'])
                self.assertEqual(result['successful_responses_missing_or_invalid_usage'], 1)

    def test_known_usage_is_reported_and_unclosed_usage_is_separate(self):
        result = M.provider_analysis(self.fixture({'usageMetadata': {'totalTokenCount': 12}, 'modelVersion': 'fixture-model'}), {'provider': {'upstream_allocations': 1}})
        self.assertTrue(result['fully_measured'])
        self.assertEqual(result['known_reported_tokens'], 12)
        result = M.provider_analysis(self.fixture({}, close=False), {'provider': {'upstream_allocations': 1}})
        self.assertEqual(result['unclosed_allocation_ids'], [1])
        self.assertEqual(result['allocations_with_unmeasured_usage'], 1)

    def test_terminal_without_opening_is_detected(self):
        result = M.provider_analysis(self.fixture({'usageMetadata': {'totalTokenCount': 12}}, start=False), {'provider': {'upstream_allocations': 0}})
        self.assertIn('provider_terminal_without_opening_allocation', result['consistency_questions'])

    def test_runtime_record_is_bound_to_result_and_plan_versions(self):
        plan = {'versions': {'fixture-sdk': '1'}, 'source_stage_sha256': 'fixture-stage', 'original_windows_environment_sha256': 'fixture-env'}
        runtime = {'required_original_versions': plan['versions'], 'distributions': plan['versions'], 'source_stage_sha256': 'fixture-stage', 'original_windows_environment_sha256': 'fixture-env', 'files': {}}
        raw = json.dumps(runtime).encode()
        result = M.runtime_analysis(MemoryRead({'execution/portable-runtime.json': raw}), plan, {'portable_runtime_sha256': M.digest(raw)['sha256']})
        self.assertEqual(result['consistency_questions'], [])
        self.assertFalse(result['runtime_package_bytes_independently_retained'])
        result = M.runtime_analysis(MemoryRead({'execution/portable-runtime.json': raw}), plan, {'portable_runtime_sha256': 'changed'})
        self.assertIn('result_and_retained_portable_runtime_digest_differ', result['consistency_questions'])


class ArchiveEvidenceControls(unittest.TestCase):
    def make_fixture(self, base):
        raw = b'constructed fixture only'
        archive = base / 'artifact.zip'
        with zipfile.ZipFile(archive, 'w') as zipped:
            zipped.writestr('fixture.txt', raw)
        archive_record = M.digest(archive.read_bytes())
        (base / 'retention.json').write_text(json.dumps({'run_id': 7, 'head_sha': 'fixture-head', 'archive_bytes': archive_record['bytes'], 'archive_sha256': archive_record['sha256'], 'api_digest': 'sha256:' + archive_record['sha256'], 'extracted_files': 1}))
        (base / 'github-run.json').write_text(json.dumps({'id': 7, 'head_sha': 'fixture-head', 'status': 'completed'}))
        (base / 'extracted-manifest.json').write_text(json.dumps({'files': [{'path': 'fixture.txt', **M.digest(raw)}]}))
        (base / 'extracted').mkdir()
        (base / 'extracted/fixture.txt').write_bytes(raw)

    def test_archive_and_member_hashes_are_both_bound(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            self.make_fixture(base)
            retained = M.Retained(base, 7, 'fixture-head')
            self.assertEqual(retained.raw('fixture.txt'), b'constructed fixture only')
            (base / 'extracted/fixture.txt').write_bytes(b'changed extracted file')
            with self.assertRaisesRegex(ValueError, 'retained_member_digest_differs'):
                retained.raw('fixture.txt')

    def test_forged_manifest_cannot_change_archived_member_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            self.make_fixture(base)
            manifest = {'files': [{'path': 'fixture.txt', **M.digest(b'forged')}]}
            (base / 'extracted-manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'archive_and_extracted_manifest_digest_differs'):
                M.Retained(base, 7, 'fixture-head')


if __name__ == '__main__':
    unittest.main()
