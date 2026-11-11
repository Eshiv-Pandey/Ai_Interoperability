"""Constructed controls for original native shopper ownership and user replies.

No original application, ADK, GenAI, native listener or provider is imported or
executed. Existing inherited provider controls cover unchanged proxy behavior.
"""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('native_shopper_controls', ROOT / 'scripts/run_ap2_native_shopper_provider_v1.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
W = M.W


class PublicActorControls(unittest.TestCase):
    def test_generic_input_required_never_injects_OTP(self):
        for prompt in ('Payment returned input_required.', 'Additional input is required. What would you like to do?',
                       'We are waiting for an OTP.', 'The receipt says OTP was accepted.'):
            with self.subTest(prompt=prompt):
                self.assertIsNone(W.public_reply(prompt, W.public_facts(), []))
        reply = W.public_reply('Please enter the OTP sent to your device.', W.public_facts(), [])
        self.assertEqual(reply, {'category': 'otp', 'text': '123'})

    def test_public_only_selections_consent_and_checkout_are_distinct(self):
        facts = W.public_facts()
        samples = (
            ('1. Walking shoe, Price $20, Cart ID demo-cart. Which item would you like to purchase?', 'cart-selection'),
            ('Would you prefer a digital wallet or enter the address manually?', 'wallet-choice'),
            ('I will access bugsbunny@gmail.com. Is that ok?', 'wallet-consent'),
            ('1. Visa card. Which payment method would you choose?', 'payment-selection'),
            ('Cart summary: walking shoes\nOrder total: USD 20\nPlease confirm this purchase.', 'checkout-confirmation'),
            ('Please provide your email?', 'email'))
        for prompt, category in samples:
            with self.subTest(category=category):
                reply = W.public_reply(prompt, facts, [])
                self.assertEqual(reply['category'], category)
                self.assertIsNone(W.public_reply(prompt, facts, [category]))
        self.assertIsNone(W.public_reply('Which item would you like?', facts, []))
        self.assertIsNone(W.public_reply('Which payment method do you prefer?', facts, []))

    def test_visible_first_option_enforces_USD_budget_and_refuses_uncertainty(self):
        facts = W.public_facts()
        accepted = '1. Walking shoes, USD 55.99, Cart ID demo. Which item would you like to purchase?'
        reply = W.public_reply(accepted, facts, [])
        self.assertEqual(reply['category'], 'cart-selection')
        self.assertEqual(reply['visible_price_check']['visible_amount'], '55.99')
        for amount in ('USD 120', '\u20ac45', '\u00a345', 'CAD $45', 'no price shown', 'USD 55.99 or USD 70'):
            prompt = '1. Walking shoes, ' + amount + ', Cart ID demo. Which item would you like to purchase?'
            with self.subTest(amount=amount):
                self.assertIsNone(W.public_reply(prompt, facts, []))
        choices = '1. Walking shoes USD 55.99, Cart ID first\n2. Sneakers USD 120, Cart ID second\nWhich item would you like to purchase?'
        self.assertEqual(W.public_reply(choices, facts, [])['visible_price_check']['visible_amount'], '55.99')

    def test_checkout_never_approves_overbudget_or_ambiguous_total(self):
        facts = W.public_facts()
        reply = W.public_reply('Cart summary: shoes\nOrder total: USD 55.99\nPlease confirm this purchase?', facts, [])
        self.assertEqual(reply['category'], 'checkout-confirmation')
        for summary in ('shoes USD 120\nOrder total: USD 120', 'shoes USD 55.99, shipping USD 10', 'shoes \u20ac55.99', 'no displayed amount',
                        'shoes USD99.99 plus tax', 'shoes USD90+20 shipping', 'Grand total: USD90+20 shipping', 'Grand total: MXN$45'):
            with self.subTest(summary=summary):
                self.assertIsNone(W.public_reply('Cart summary: ' + summary + '. Please confirm this purchase?', facts, []))
        total = 'Cart summary:\nShoes USD 55.99\nShipping USD 10\nGrand total: USD 65.99\nPlease confirm checkout?'
        self.assertEqual(W.public_reply(total, facts, [])['visible_price_check']['visible_amount'], '65.99')

    def test_foreign_dollar_labels_malformed_numbers_and_unsupported_ordinals_are_refused(self):
        facts = W.public_facts()
        for price in ('C$45', '$45 Canadian dollars', 'A$45', 'MXN$45', 'USD 12,3456', '1000,005 USD', 'USD 1e3', 'USD 100.01'):
            with self.subTest(price=price):
                cart = '1. Walking shoes ' + price + ', Cart ID first. Which item would you like to purchase?'
                checkout = 'Cart summary: shoes\nOrder total: ' + price + '\nPlease confirm this purchase?'
                self.assertIsNone(W.public_reply(cart, facts, []))
                self.assertIsNone(W.public_reply(checkout, facts, []))
        for choices in ('0. First USD120 Cart ID first\n1. Second USD55.99 Cart ID second',
                        '2. First USD120 Cart ID first\n3. Second USD55.99 Cart ID second',
                        '1. First USD55.99 Cart ID first\n1. Second USD120 Cart ID second'):
            with self.subTest(choices=choices):
                self.assertIsNone(W.public_reply(choices + '\nWhich item would you like to purchase?', facts, []))
        for price in ('USD 55.99', 'US$55.99', '$55.99', '100 USD'):
            with self.subTest(accepted_price=price):
                self.assertIsNotNone(W.public_reply('1. Walking shoes ' + price + ', Cart ID first. Which item would you like to purchase?', facts, []))

    def test_bullet_options_cannot_borrow_second_option_price(self):
        prompt = '- First shoes, price unavailable, Cart ID first\n- Second shoes USD55.99, Cart ID second\nWhich item would you like to purchase?'
        self.assertIsNone(W.public_reply(prompt, W.public_facts(), []))

    def test_spaced_MXN_qualifier_refuses_valid_cart_and_explicit_USD_checkout(self):
        cart = '1. Shoes MXN $45, Cart ID first. Which item?'
        checkout = 'Cart summary: shoes MXN $45\nOrder total: USD45\nPlease confirm checkout?'
        self.assertIsNone(W.public_reply(cart, W.public_facts(), []))
        self.assertIsNone(W.public_reply(checkout, W.public_facts(), []))

    def test_mixed_numbered_and_bullet_options_cannot_borrow_second_price(self):
        prompt = '1. First shoes, price unavailable, Cart ID first\n- Second shoes USD55.99, Cart ID second\nWhich item?'
        self.assertIsNone(W.public_reply(prompt, W.public_facts(), []))

    def test_parenthesized_options_cannot_borrow_second_option_price(self):
        prompt = '(1) First shoes, price unavailable, Cart ID first\n(2) Second shoes USD55.99, Cart ID second\nWhich item would you like to purchase?'
        self.assertIsNone(W.public_reply(prompt, W.public_facts(), []))

    def test_price_ranges_never_become_smaller_single_prices(self):
        for price in ('USD80-120', 'USD80 to120', 'USD80 to 120', 'USD80\u2013120', 'USD80 - USD120'):
            with self.subTest(price=price):
                cart = '1. Shoes ' + price + ', Cart ID first. Which item would you like to purchase?'
                checkout = 'Cart summary: shoes\nOrder total: ' + price + '\nPlease confirm checkout?'
                self.assertIsNone(W.public_reply(cart, W.public_facts(), []))
                self.assertIsNone(W.public_reply(checkout, W.public_facts(), []))

    def test_ambiguous_confirmation_and_OTP_question_is_refused(self):
        prompt = 'Cart summary: shoes $20. Please confirm checkout and enter the OTP?'
        self.assertIsNone(W.public_reply(prompt, W.public_facts(), []))

    def test_thought_and_tool_events_are_not_public_actor_prompts(self):
        def event(parts, final=True, author='root_agent', role='model'):
            return SimpleNamespace(author=author, content=SimpleNamespace(role=role, parts=parts),
                                   is_final_response=lambda: final)
        visible = SimpleNamespace(text='Please enter the OTP?', thought=False)
        thought = SimpleNamespace(text='We should ask for OTP internally.', thought=True)
        self.assertEqual(W.visible_final_text(event([thought, visible])), visible.text)
        self.assertEqual(W.visible_final_text(event([visible], final=False)), '')
        self.assertEqual(W.visible_final_text(event([visible], author='user', role='user')), '')
        internal = SimpleNamespace(text='Please enter the OTP?', thought=False, function_response=object())
        self.assertEqual(W.visible_final_text(event([internal])), '')


class OwnershipControls(unittest.TestCase):
    def test_worker_refuses_real_credentials_before_guard_or_application_import(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            facts = base / 'facts.json'
            facts.write_text(json.dumps(W.public_facts()), encoding='utf-8')
            with mock.patch.dict(os.environ, {'GOOGLE_API_KEY': 'constructed-real-like-key', 'GOOGLE_GENAI_USE_VERTEXAI': 'false'}), \
                    mock.patch.object(W, 'actor_guard', side_effect=AssertionError('unexpected_guard')), \
                    mock.patch.object(W, 'application', side_effect=AssertionError('unexpected_application')):
                with self.assertRaisesRegex(ValueError, 'synthetic_proxy_credential'):
                    W.execute(facts, base / 'output', base / 'source')
            self.assertFalse((base / 'output').exists())

    def test_missing_transport_response_and_unclosed_allocation_remain_unmeasured(self):
        with tempfile.TemporaryDirectory() as directory:
            provider = Path(directory)
            ledger = provider / 'ledger.jsonl'
            M.H.append(ledger, {'phase': 'started', 'allocation': 0})
            M.H.append(ledger, {'phase': 'finished', 'allocation': 0, 'http_status': 502,
                    'transport_error_type': 'OSError', 'response': M.H.digest(b'not retained')})
            M.H.append(ledger, {'phase': 'started', 'allocation': 1})
            M.H.append(provider / 'local-refusals.jsonl', {'status': 'no_upstream_call_budget_or_prior_failure'})
            census = M.all_response_usage(provider)
            self.assertEqual(census['upstream_allocations'], 2)
            self.assertEqual(census['terminal_responses'], 1)
            self.assertEqual(census['failed_responses_missing_or_invalid_usage'], 1)
            self.assertEqual(census['unclosed_allocation_ids'], [1])
            self.assertEqual(census['allocations_with_unmeasured_usage'], 2)
            self.assertIsNone(census['observations'][0]['known_reported_tokens'])
            self.assertFalse(census['fully_measured'])

    def test_all_response_census_retains_failed_and_successful_unknown_usage(self):
        payload = b'{"contents":[{"parts":[{"text":"constructed"}]}]}'
        outcomes = (
            (503, b'{"error":{"code":503,"message":"unavailable"}}', 0, 1),
            (200, b'{"candidates":[]}', 1, 0))
        for status, body, successful_unknown, failed_unknown in outcomes:
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory:
                boundary = M.H.ProviderBoundary(Path(directory) / 'provider', '', mode='fixture', interval=0,
                        send=lambda raw: (status, body))
                boundary.request(M.H.API_PATH, payload, M.H.SYNTHETIC_KEY)
                summary = M.accounted_summary(boundary)
                census = summary['all_response_usage']
                self.assertEqual(census['successful_responses_missing_or_invalid_usage'], successful_unknown)
                self.assertEqual(census['failed_responses_missing_or_invalid_usage'], failed_unknown)
                self.assertEqual(census['known_reported_tokens'], 0)
                self.assertIsNone(census['observations'][0]['known_reported_tokens'])
                self.assertFalse(census['fully_measured'])
                self.assertFalse(census['unknown_usage_is_zero'])

    def test_all_response_census_sums_exact_known_totals_and_rejects_hash_drift(self):
        payload = b'{"contents":[]}'
        responses = iter(((200, b'{"usageMetadata":{"totalTokenCount":17}}'),
                          (503, b'{"usageMetadata":{"totalTokenCount":3},"error":{"code":503}}')))
        with tempfile.TemporaryDirectory() as directory:
            boundary = M.H.ProviderBoundary(Path(directory) / 'provider', '', mode='fixture', interval=0,
                        send=lambda raw: next(responses))
            boundary.request(M.H.API_PATH, payload, M.H.SYNTHETIC_KEY)
            boundary.request(M.H.API_PATH, payload, M.H.SYNTHETIC_KEY)
            census = M.all_response_usage(boundary.output)
            self.assertEqual(census['known_reported_tokens'], 20)
            self.assertTrue(census['fully_measured'])
            (boundary.output / '001.response.json').write_bytes(b'{"usageMetadata":{"totalTokenCount":999}}')
            changed = M.all_response_usage(boundary.output)
            self.assertEqual(changed['known_reported_tokens'], 17)
            self.assertFalse(changed['fully_measured'])
            self.assertEqual(changed['consistency_questions'], ['response_digest_mismatch:1'])

    def test_private_source_copy_preserves_inputs_and_log_path_isolation(self):
        with tempfile.TemporaryDirectory(prefix='native-shopper-copy-control-') as directory:
            base = Path(directory)
            original, x402, work = base / 'original', base / 'x402', base / 'work'
            original.mkdir()
            x402.mkdir()
            work.mkdir()
            originals = {'code/sdk/python/ap2/sdk/mandate.py': b'original source',
                         'code/samples/python/src/roles/shopping_agent/agent.py': b'original root'}
            for name, raw in originals.items():
                target = original / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
            (x402 / 'module.py').write_bytes(b'original x402')
            plan = {'sources': {name: M.H.digest(raw) for name, raw in originals.items()},
                    'x402_sources': {'module.py': M.H.digest(b'original x402')}}
            with mock.patch.object(M.H, 'SOURCE', original), mock.patch.object(M.H, 'STAGE', base / 'manifest.json'):
                # The production x402 origin is STAGE.parent/a2a-x402.
                (base / 'a2a-x402').mkdir()
                (base / 'a2a-x402/module.py').write_bytes(b'original x402')
                roots = M.private_sources(work, plan)
            generated_log = roots['ap2'] / 'code/sdk/.logs/mandate_operations.log'
            generated_log.parent.mkdir(parents=True)
            generated_log.write_bytes(b'generated original operations')
            self.assertTrue(M.private_source_unchanged(roots, plan))
            self.assertFalse((original / 'code/sdk/.logs').exists())
            environment = M.original_environment(work, base / 'site', 'http://127.0.0.1:12345', roots)
            self.assertIn(str(roots['ap2'] / 'code/sdk/python'), environment['PYTHONPATH'])
            self.assertNotIn(str(original / 'code/sdk/python'), environment['PYTHONPATH'])
            self.assertEqual(environment['GOOGLE_API_KEY'], M.H.SYNTHETIC_KEY)
            (roots['ap2'] / next(iter(originals))).write_bytes(b'altered copy')
            self.assertFalse(M.private_source_unchanged(roots, plan))

    def test_preflight_failure_preserves_one_missing_task_and_no_provider_call(self):
        with tempfile.TemporaryDirectory(prefix='native-shopper-preflight-control-') as directory:
            base = Path(directory)
            plan_dir, output = base / 'plan', base / 'execution'
            M.prepare(plan_dir)
            with mock.patch.dict(os.environ, {'GOOGLE_API_KEY': 'constructed-not-provider-key'}), \
                    mock.patch.object(M.sys, 'platform', 'linux'), \
                    mock.patch.object(M.H, 'portable_runtime', side_effect=ValueError('constructed_runtime_failure')), \
                    mock.patch.object(M.H, 'ProviderBoundary', side_effect=AssertionError('unexpected_provider')):
                M.execute(plan_dir, output, base / 'python', base / 'site', base / 'pip.json', 'live')
            result = json.loads((output / 'result.json').read_bytes())
            self.assertEqual(result['allocated_task_count'], 1)
            self.assertEqual(result['unexecuted_count'], 1)
            self.assertEqual(result['provider']['upstream_allocations'], 0)
            self.assertEqual(result['cases'][0]['case_id'], W.public_facts()['case_id'])
            self.assertIsNone(result['whole_task_grade'])
            self.assertEqual(result['cases'], json.loads((output / 'opening.json').read_bytes())['prospective_cases'])

    def test_changed_facts_or_bound_runner_refuses_before_execution(self):
        with tempfile.TemporaryDirectory(prefix='native-shopper-plan-control-') as directory:
            plan_dir = Path(directory) / 'plan'
            M.prepare(plan_dir)
            plan = M.check_plan(plan_dir)
            self.assertFalse(plan['held_out_study'])
            self.assertFalse(plan['human_gold_qualified'])
            self.assertEqual(plan['limits']['maximum_total_request_bytes'], M.H.MAX_TOTAL_REQUEST_BYTES)
            plan['public_human_facts']['otp_response'] = 'invented_other_OTP'
            (plan_dir / 'plan.json').write_text(json.dumps(plan), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'prospective_fixed_plan'):
                M.check_plan(plan_dir)


if __name__ == '__main__':
    unittest.main()
