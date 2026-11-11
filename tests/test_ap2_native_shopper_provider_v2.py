"""Constructed V2 sender/drain controls; no SDK, app, listener or provider."""
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('native_shopper_provider_v2_controls', ROOT / 'scripts/run_ap2_native_shopper_provider_v2.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
B, H = M.B, M.B.H
RAW = b'{"contents":[{"role":"user","parts":[{"text":"constructed fixture only"}]}]}'


def response(tokens=7, status=200):
    return status, json.dumps({'usageMetadata': {'totalTokenCount': tokens}}).encode()


class BoundaryControls(unittest.TestCase):
    def test_live_sender_only_changes_timeout_and_preserves_path_body_header(self):
        class Reply:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, count):
                self.count = count
                return b'fixture'
        reply, calls = Reply(), []
        class Opener:
            def open(self, request, timeout):
                calls.append((request, timeout))
                return reply
        with tempfile.TemporaryDirectory() as temporary:
            boundary = B.ProviderBoundary(Path(temporary) / 'provider', 'constructed-key-only', mode='live')
            with mock.patch.object(B.urllib.request, 'build_opener', return_value=Opener()):
                self.assertEqual(boundary._send_live(RAW), (200, b'fixture'))
            request, timeout = calls[0]
            self.assertEqual(timeout, 120)
            self.assertEqual(request.full_url, H.API_ORIGIN + H.API_PATH)
            self.assertEqual(request.data, RAW)
            self.assertEqual(request.get_header('X-goog-api-key'), 'constructed-key-only')
            self.assertEqual(reply.count, H.MAX_RESPONSE_BYTES + 1)

    def test_same_call_budget_has_no_unaccounted_retry(self):
        clock = [0.0]
        def sleep(seconds): clock[0] += seconds
        with tempfile.TemporaryDirectory() as temporary:
            boundary = B.ProviderBoundary(Path(temporary) / 'provider', 'fixture', send=lambda raw: response(1), clock=lambda: clock[0], sleeper=sleep)
            for _ in range(80):
                self.assertEqual(boundary.request(H.API_PATH, RAW, H.SYNTHETIC_KEY)[0], 200)
            self.assertEqual(boundary.request(H.API_PATH, RAW, H.SYNTHETIC_KEY)[0], 429)
            self.assertEqual(boundary.calls, 80)
            self.assertEqual(boundary.usage_tokens, 80)
            self.assertEqual(clock[0], 79 * 6)
            census = M.V1.all_response_usage(boundary.output)
            self.assertTrue(census['fully_measured'])
            self.assertEqual(census['known_reported_tokens'], 80)

    def test_same_total_request_byte_bound_stops_before_allocation(self):
        with tempfile.TemporaryDirectory() as temporary:
            boundary = B.ProviderBoundary(Path(temporary) / 'provider', 'fixture', send=lambda raw: response(), sleeper=lambda seconds: None)
            body = json.dumps({'contents': [], 'padding': 'x' * 100_100}).encode()
            self.assertEqual(boundary.request(H.API_PATH, body, H.SYNTHETIC_KEY)[0], 200)
            self.assertEqual(boundary.request(H.API_PATH, body, H.SYNTHETIC_KEY)[0], 429)
            self.assertEqual(boundary.calls, 1)
            self.assertEqual(boundary.request_bytes, len(body))

    def test_postresponse_usage_stop_preserves_inherited_threshold(self):
        with tempfile.TemporaryDirectory() as temporary:
            boundary = B.ProviderBoundary(Path(temporary) / 'provider', 'fixture', send=lambda raw: response(100_001))
            self.assertEqual(boundary.request(H.API_PATH, RAW, H.SYNTHETIC_KEY)[0], 200)
            self.assertEqual(boundary.request(H.API_PATH, RAW, H.SYNTHETIC_KEY)[0], 429)
            self.assertEqual(boundary.calls, 1)
            self.assertEqual(boundary.usage_tokens, 100_001)

    def test_transport_timeout_is_captured_once_and_failed_usage_stays_unknown(self):
        def sender(raw): raise TimeoutError('constructed timeout')
        with tempfile.TemporaryDirectory() as temporary:
            boundary = B.ProviderBoundary(Path(temporary) / 'provider', 'fixture', send=sender)
            self.assertEqual(boundary.request(H.API_PATH, RAW, H.SYNTHETIC_KEY)[0], 502)
            self.assertEqual(boundary.request(H.API_PATH, RAW, H.SYNTHETIC_KEY)[0], 429)
            census = M.V1.all_response_usage(boundary.output)
            self.assertEqual(census['upstream_allocations'], 1)
            self.assertEqual(census['failed_responses_missing_or_invalid_usage'], 1)
            self.assertFalse(census['fully_measured'])
            self.assertFalse(census['unknown_usage_is_zero'])

    def test_adverse_received_body_is_preserved(self):
        raw_response = b'{"error":{"code":503,"message":"constructed adverse body"}}'
        with tempfile.TemporaryDirectory() as temporary:
            boundary = B.ProviderBoundary(Path(temporary) / 'provider', 'fixture', send=lambda raw: (503, raw_response))
            self.assertEqual(boundary.request(H.API_PATH, RAW, H.SYNTHETIC_KEY), (503, raw_response))
            self.assertEqual((boundary.output / '000.response.json').read_bytes(), raw_response)
            self.assertEqual(M.V1.all_response_usage(boundary.output)['failed_responses_missing_or_invalid_usage'], 1)

    def test_success_without_usage_stops_and_remains_unmeasured(self):
        with tempfile.TemporaryDirectory() as temporary:
            boundary = B.ProviderBoundary(Path(temporary) / 'provider', 'fixture', send=lambda raw: (200, b'{"fixture":"no usage"}'))
            self.assertEqual(boundary.request(H.API_PATH, RAW, H.SYNTHETIC_KEY)[0], 200)
            self.assertEqual(boundary.request(H.API_PATH, RAW, H.SYNTHETIC_KEY)[0], 429)
            self.assertEqual(M.V1.all_response_usage(boundary.output)['successful_responses_missing_or_invalid_usage'], 1)

    def test_wrong_key_path_and_payload_never_allocate(self):
        with tempfile.TemporaryDirectory() as temporary:
            boundary = B.ProviderBoundary(Path(temporary) / 'provider', 'fixture', send=lambda raw: self.fail('no send expected'))
            for path, raw, key in ((H.API_PATH, RAW, 'wrong'), ('/other-model', RAW, H.SYNTHETIC_KEY), (H.API_PATH, b'{}', H.SYNTHETIC_KEY)):
                self.assertEqual(boundary.request(path, raw, key)[0], 400)
            self.assertEqual(boundary.calls, 0)

    def test_drain_waits_for_terminal_then_freezes_before_summary(self):
        entered, release = threading.Event(), threading.Event()
        def sender(raw):
            entered.set()
            if not release.wait(3): raise AssertionError('fixture release missing')
            return response(9)
        with tempfile.TemporaryDirectory() as temporary:
            boundary = B.ProviderBoundary(Path(temporary) / 'provider', 'fixture', send=sender)
            worker = threading.Thread(target=boundary.request, args=(H.API_PATH, RAW, H.SYNTHETIC_KEY))
            worker.start()
            self.assertTrue(entered.wait(3))
            release_timer = threading.Timer(0.02, release.set)
            release_timer.start()
            drain = boundary.drain_and_freeze(3)
            worker.join(3)
            release_timer.join(3)
            self.assertFalse(worker.is_alive())
            self.assertTrue(drain['all_handlers_completed'])
            self.assertTrue(drain['capture_frozen'])
            self.assertEqual(M.V1.all_response_usage(boundary.output)['known_reported_tokens'], 9)
            self.assertEqual(boundary.request(H.API_PATH, RAW, H.SYNTHETIC_KEY)[0], 429)
            self.assertEqual(boundary.calls, 1)

    def test_drain_deadline_preserves_open_unknown_and_prevents_late_writes(self):
        entered, release = threading.Event(), threading.Event()
        results = []
        def sender(raw):
            entered.set()
            if not release.wait(3): raise AssertionError('fixture release missing')
            return response(19)
        with tempfile.TemporaryDirectory() as temporary:
            boundary = B.ProviderBoundary(Path(temporary) / 'provider', 'fixture', send=sender)
            worker = threading.Thread(target=lambda: results.append(boundary.request(H.API_PATH, RAW, H.SYNTHETIC_KEY)))
            worker.start()
            self.assertTrue(entered.wait(3))
            drain = boundary.drain_and_freeze(0)
            frozen = {path.name: path.read_bytes() for path in boundary.output.iterdir()}
            self.assertFalse(drain['all_handlers_completed'])
            census = M.V1.all_response_usage(boundary.output)
            self.assertEqual(census['unclosed_allocation_ids'], [0])
            self.assertEqual(census['allocations_with_unmeasured_usage'], 1)
            release.set()
            worker.join(3)
            self.assertFalse(worker.is_alive())
            self.assertEqual(results[0][0], 503)
            self.assertEqual({path.name: path.read_bytes() for path in boundary.output.iterdir()}, frozen)
            self.assertEqual(boundary.usage_tokens, 0)
            self.assertEqual(boundary.successful_responses, 0)
            self.assertEqual(boundary.calls, 1)

    def test_queued_handler_at_deadline_does_not_allocate_after_gate_close(self):
        entered, release = threading.Event(), threading.Event()
        def sender(raw):
            entered.set()
            if not release.wait(3): raise AssertionError('fixture release missing')
            return response()
        with tempfile.TemporaryDirectory() as temporary:
            boundary = B.ProviderBoundary(Path(temporary) / 'provider', 'fixture', send=sender)
            first = threading.Thread(target=boundary.request, args=(H.API_PATH, RAW, H.SYNTHETIC_KEY))
            second = threading.Thread(target=boundary.request, args=(H.API_PATH, RAW, H.SYNTHETIC_KEY))
            first.start()
            self.assertTrue(entered.wait(3))
            second.start()
            with boundary._capture:
                self.assertTrue(boundary._capture.wait_for(lambda: boundary._active_handlers == 2, timeout=3))
            boundary.drain_and_freeze(0)
            release.set()
            first.join(3)
            second.join(3)
            self.assertFalse(first.is_alive() or second.is_alive())
            self.assertEqual(boundary.calls, 1)
            self.assertEqual(M.V1.all_response_usage(boundary.output)['unclosed_allocation_ids'], [0])

    def test_close_during_pacing_cannot_allocate_a_following_call(self):
        pacing, release = threading.Event(), threading.Event()
        def sleep(seconds):
            pacing.set()
            if not release.wait(3): raise AssertionError('fixture pacing release missing')
        with tempfile.TemporaryDirectory() as temporary:
            boundary = B.ProviderBoundary(Path(temporary) / 'provider', 'fixture', send=lambda raw: response(), clock=lambda: 0, sleeper=sleep)
            boundary.request(H.API_PATH, RAW, H.SYNTHETIC_KEY)
            worker = threading.Thread(target=boundary.request, args=(H.API_PATH, RAW, H.SYNTHETIC_KEY))
            worker.start()
            self.assertTrue(pacing.wait(3))
            boundary.drain_and_freeze(0)
            release.set()
            worker.join(3)
            self.assertFalse(worker.is_alive())
            self.assertEqual(boundary.calls, 1)
            self.assertEqual(M.V1.all_response_usage(boundary.output)['unclosed_allocation_ids'], [])

    def test_drain_rejects_unbounded_wait(self):
        with tempfile.TemporaryDirectory() as temporary:
            boundary = B.ProviderBoundary(Path(temporary) / 'provider', 'fixture', send=lambda raw: response())
            for seconds in (-1, 151):
                with self.assertRaisesRegex(ValueError, 'bounded_provider_drain_required'):
                    boundary.drain_and_freeze(seconds)


class ProspectivePlanControls(unittest.TestCase):
    def test_v2_plan_changes_only_declared_owned_timeout_lifecycle_and_case_metadata(self):
        before, after = M.V1.fixed_plan_fields(), M.fixed_plan_fields()
        for key in before:
            if key not in {'schema_version', 'limits', 'public_human_facts'}:
                self.assertEqual(before[key], after[key], key)
        for key in before['limits']:
            if key != 'request_timeout_seconds':
                self.assertEqual(before['limits'][key], after['limits'][key], key)
        for key in before['public_human_facts']:
            if key != 'case_id':
                self.assertEqual(before['public_human_facts'][key], after['public_human_facts'][key], key)
        self.assertEqual(after['limits']['request_timeout_seconds'], 120)
        self.assertEqual(after['allocated_task_count'], 1)
        self.assertFalse(after['human_gold_qualified'])
        self.assertFalse(after['original_genai_Client_replaced'])

    def test_prepared_sources_and_model_timeout_fields_are_frozen(self):
        with tempfile.TemporaryDirectory() as temporary:
            plan_dir = Path(temporary) / 'plan'
            M.prepare(plan_dir)
            M.check_plan(plan_dir)
            plan = json.loads((plan_dir / 'plan.json').read_bytes())
            plan['limits']['request_timeout_seconds'] = 121
            (plan_dir / 'plan.json').write_text(json.dumps(plan))
            with self.assertRaisesRegex(ValueError, 'prospective_fixed_plan'):
                M.check_plan(plan_dir)


if __name__ == '__main__':
    unittest.main()
