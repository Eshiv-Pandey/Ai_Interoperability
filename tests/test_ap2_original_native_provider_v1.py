"""Constructed provider-ledger and isolation controls; no original app/provider."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
import sys
import venv
from unittest import mock

PATH = Path(__file__).resolve().parents[1] / 'scripts/run_ap2_original_native_provider_v1.py'
SPEC = importlib.util.spec_from_file_location('ap2_native_provider_owned', PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

PAYLOAD = b'{"contents":[{"parts":[{"text":"public fixture"}]}]}'
RESPONSE = json.dumps({'candidates': [{'content': {'parts': [{'functionCall': {'name': 'access_check', 'args': {}}}]}}],
                       'usageMetadata': {'totalTokenCount': 17}}).encode()


class ProviderTests(unittest.TestCase):
    def boundary(self, folder, send=None, **kwargs):
        return MODULE.ProviderBoundary(Path(folder) / 'provider', '', mode='fixture',
                   send=send or (lambda raw: (200, RESPONSE)), interval=0, **kwargs)

    def test_exact_path_and_synthetic_downstream_key_reject_without_send(self):
        with tempfile.TemporaryDirectory() as folder:
            sends = []
            boundary = self.boundary(folder, lambda raw: sends.append(raw))
            for path, key in ((MODULE.API_PATH + '?key=anything', MODULE.SYNTHETIC_KEY),
                              ('/v1beta/models/other:generateContent', MODULE.SYNTHETIC_KEY),
                              (MODULE.API_PATH, 'real-key-disallowed')):
                self.assertEqual(boundary.request(path, PAYLOAD, key)[0], 400)
            self.assertEqual(sends, [])
            self.assertEqual(boundary.calls, 0)

    def test_concurrent_calls_share_exact_eighty_allocation_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            boundary = self.boundary(folder)
            results = []
            threads = [threading.Thread(target=lambda: results.append(boundary.request(MODULE.API_PATH, PAYLOAD, MODULE.SYNTHETIC_KEY)[0])) for _ in range(84)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            self.assertEqual(results.count(200), 80)
            self.assertEqual(results.count(429), 4)
            ledger = [json.loads(line) for line in (boundary.output / 'ledger.jsonl').read_text().splitlines()]
            self.assertEqual(len(ledger), 160)
            self.assertEqual({r['allocation'] for r in ledger}, set(range(80)))
            self.assertTrue(all([r['phase'] for r in ledger if r['allocation'] == i] == ['started', 'finished'] for i in range(80)))

    def test_upstream_429_is_retained_and_all_later_calls_stay_local(self):
        with tempfile.TemporaryDirectory() as folder:
            sends = []
            adverse = b'{"error":{"code":429,"message":"resource exhausted"}}'
            def send(raw):
                sends.append(raw)
                return 429, adverse
            boundary = self.boundary(folder, send)
            self.assertEqual(boundary.request(MODULE.API_PATH, PAYLOAD, MODULE.SYNTHETIC_KEY), (429, adverse))
            self.assertEqual(boundary.request(MODULE.API_PATH, PAYLOAD, MODULE.SYNTHETIC_KEY)[0], 429)
            self.assertEqual(len(sends), 1)
            self.assertEqual((boundary.output / '000.response.json').read_bytes(), adverse)
            self.assertTrue(boundary.failed)

    def test_transport_error_closes_consumed_allocation_without_exception_text(self):
        with tempfile.TemporaryDirectory() as folder:
            def send(raw):
                raise OSError('this could contain a secret')
            boundary = self.boundary(folder, send)
            self.assertEqual(boundary.request(MODULE.API_PATH, PAYLOAD, MODULE.SYNTHETIC_KEY)[0], 502)
            ledger = (boundary.output / 'ledger.jsonl').read_text()
            self.assertIn('OSError', ledger)
            self.assertNotIn('this could contain', ledger)
            self.assertEqual(boundary.calls, 1)
            self.assertTrue(boundary.stopped)

    def test_non_json_http_failure_body_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            boundary = self.boundary(folder, lambda raw: (403, b'<html>Actual refusal</html>'))
            self.assertEqual(boundary.request(MODULE.API_PATH, PAYLOAD, MODULE.SYNTHETIC_KEY), (403, b'<html>Actual refusal</html>'))
            self.assertTrue(boundary.stopped)

    def test_model_smoke_must_observe_exact_forced_tool(self):
        with tempfile.TemporaryDirectory() as folder:
            boundary = self.boundary(folder)
            result = MODULE.smoke(boundary)
            self.assertTrue(result['forced_tool_observed'])
            self.assertEqual(result['calls'], 1)
            self.assertFalse(result['independent_provider_capacity_verified'])
        with tempfile.TemporaryDirectory() as folder:
            boundary = self.boundary(folder, lambda raw: (200, b'{"candidates":[]}'))
            self.assertFalse(MODULE.smoke(boundary)['forced_tool_observed'])
            self.assertTrue(boundary.stopped)

    def test_request_and_observed_usage_caps_prevent_additional_sends(self):
        with tempfile.TemporaryDirectory() as folder:
            boundary = self.boundary(folder)
            boundary.request_bytes = MODULE.MAX_TOTAL_REQUEST_BYTES - len(PAYLOAD) + 1
            self.assertEqual(boundary.request(MODULE.API_PATH, PAYLOAD, MODULE.SYNTHETIC_KEY)[0], 429)
            self.assertEqual(boundary.calls, 0)
        with tempfile.TemporaryDirectory() as folder:
            boundary = self.boundary(folder)
            boundary.usage_tokens = MODULE.MAX_TOTAL_USAGE_TOKENS
            self.assertEqual(boundary.request(MODULE.API_PATH, PAYLOAD, MODULE.SYNTHETIC_KEY)[0], 429)

    def test_real_secret_is_scrubbed_and_never_passed_to_native_or_caller(self):
        with tempfile.TemporaryDirectory() as folder:
            secret = 'PRIVATE_PROVIDER_TOKEN_0123'
            boundary = MODULE.ProviderBoundary(Path(folder) / 'provider', secret, mode='live', interval=0,
                        send=lambda raw: (200, json.dumps({'echo': secret, 'usageMetadata': {}}).encode()))
            boundary.request(MODULE.API_PATH, PAYLOAD, MODULE.SYNTHETIC_KEY)
            for file in boundary.output.iterdir():
                self.assertNotIn(secret.encode(), file.read_bytes())
            with mock.patch.dict(os.environ, {'GOOGLE_API_KEY': secret, 'HTTP_PROXY': 'http://bad', 'GOOGLE_APPLICATION_CREDENTIALS': '/secret.json'}):
                service = MODULE.child_environment(Path(folder), Path(folder), 'http://127.0.0.1:9999')
                caller = MODULE.child_environment(Path(folder), Path(folder), 'http://127.0.0.1:9999', caller=True)
            self.assertEqual(service['GOOGLE_API_KEY'], MODULE.SYNTHETIC_KEY)
            self.assertNotIn('GOOGLE_API_KEY', caller)
            self.assertNotIn('GOOGLE_APPLICATION_CREDENTIALS', service)
            self.assertNotIn('HTTP_PROXY', service)

    def test_archive_scanner_rejects_private_key_secret_and_credential_names(self):
        for name, raw, secret in [('bad.txt', b'-----BEGIN PRIVATE KEY-----', ''),
                                  ('bad.key', b'anything', ''), ('bad.txt', b'the-real-secret', 'the-real-secret')]:
            with tempfile.TemporaryDirectory() as folder:
                (Path(folder) / name).write_bytes(raw)
                with self.assertRaisesRegex(ValueError, 'unsafe_retained'):
                    MODULE.archive_safety(Path(folder), secret)

    def test_five_explicit_public_facts_keep_wrong_absent_fault_and_repeat(self):
        rows = MODULE.task_facts()
        self.assertEqual(len(rows), 5)
        self.assertEqual(len({r['case_id'] for r in rows}), 5)
        self.assertEqual(rows[1]['otp_response'], 'wrong-human-reply')
        self.assertIsNone(rows[2]['otp_response'])
        self.assertEqual(rows[3]['fault'], 'other_original_context')
        self.assertTrue(rows[4]['repeat_after_completed'])
        self.assertTrue(all('gold' not in r and 'expected_answer' not in r for r in rows))

    def test_six_second_pacing_is_shared_and_accounts_actual_start_time(self):
        with tempfile.TemporaryDirectory() as folder:
            times, current = [], [0.0]
            def sleep(delay):
                times.append(delay)
                current[0] += delay
            boundary = MODULE.ProviderBoundary(Path(folder) / 'provider', '', mode='fixture',
                        send=lambda raw: (200, RESPONSE), clock=lambda: current[0], sleeper=sleep)
            boundary.request(MODULE.API_PATH, PAYLOAD, MODULE.SYNTHETIC_KEY)
            boundary.request(MODULE.API_PATH, PAYLOAD, MODULE.SYNTHETIC_KEY)
            self.assertEqual(times, [6.0])

    def test_redirect_handler_never_follows_alternate_authority(self):
        self.assertIsNone(MODULE.NoRedirect().redirect_request(None, None, 307, None, None, 'https://evil.test/'))

    def test_fixture_without_explicit_owned_sender_is_refused_before_network(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, 'explicit_owned_response_function'):
                MODULE.ProviderBoundary(Path(folder) / 'provider', '', mode='fixture')

    def test_interrupted_provider_allocation_gets_terminal_ledger_record(self):
        with tempfile.TemporaryDirectory() as folder:
            def send(raw):
                raise KeyboardInterrupt()
            boundary = self.boundary(folder, send)
            self.assertEqual(boundary.request(MODULE.API_PATH, PAYLOAD, MODULE.SYNTHETIC_KEY)[0], 502)
            rows = [json.loads(line) for line in (boundary.output / 'ledger.jsonl').read_text().splitlines()]
            self.assertEqual([row['phase'] for row in rows], ['started', 'finished'])
            self.assertEqual(rows[1]['transport_error_type'], 'KeyboardInterrupt')

    def test_unknown_success_usage_stops_later_calls_without_inventing_zero_cost(self):
        with tempfile.TemporaryDirectory() as folder:
            boundary = self.boundary(folder, lambda raw: (200, b'{"candidates":[]}'))
            self.assertEqual(boundary.request(MODULE.API_PATH, PAYLOAD, MODULE.SYNTHETIC_KEY)[0], 200)
            self.assertEqual(boundary.summary()['responses_with_unknown_usage'], 1)
            self.assertTrue(boundary.stopped)
            self.assertEqual(boundary.request(MODULE.API_PATH, PAYLOAD, MODULE.SYNTHETIC_KEY)[0], 429)
            self.assertEqual(boundary.calls, 1)

    def test_actual_fresh_venv_subprocess_retains_prefix_and_caller_version_contract(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            runtime = root / 'venv'
            venv.EnvBuilder(with_pip=False).create(runtime)
            python = runtime / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
            site = runtime / ('Lib/site-packages' if os.name == 'nt' else f'lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages')
            report = root / 'pip-report.json'
            report.write_text('{"install": []}')
            output = root / 'evidence'
            output.mkdir()
            path, sha = MODULE.portable_runtime(python.absolute(), site, report, output, {})
            manifest = json.loads(path.read_bytes())
            self.assertEqual(Path(manifest['root']).resolve(), runtime.resolve())
            self.assertEqual(manifest['python_version'], sys.version.split()[0])
            self.assertEqual(manifest['python_version_string'], sys.version)
            self.assertEqual(sha, MODULE.digest(path.read_bytes())['sha256'])

    def test_failed_runtime_preflight_retains_all_five_unexecuted_without_provider(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            plan = root / 'plan'
            plan.mkdir()
            value = {**MODULE.fixed_plan_fields(), 'sources': {}, 'x402_sources': {}, 'versions': {}, 'facts': MODULE.task_facts(),
                     'owned_sources': {name: MODULE.digest((MODULE.ROOT / name).read_bytes()) for name in MODULE.OWNED}}
            (plan / 'plan.json').write_text(json.dumps(value))
            with mock.patch.object(MODULE, 'source_records', return_value={}), \
                 mock.patch.object(MODULE, 'x402_source_records', return_value={}), \
                 mock.patch.object(MODULE, 'expected_versions', return_value={}), \
                 mock.patch.dict(os.environ, {'GOOGLE_API_KEY': 'OWNED_TEST_CREDENTIAL_NEVER_FORWARDED'}), \
                 mock.patch.object(MODULE, 'ProviderBoundary') as sender:
                MODULE.execute(plan, root / 'execution', root / 'missing-python', root / 'missing-site', root / 'missing-report', 'live')
            sender.assert_not_called()
            result = json.loads((root / 'execution/result.json').read_bytes())
            self.assertEqual(result['unexecuted_count'], 5)
            self.assertEqual(result['provider']['upstream_allocations'], 0)
            self.assertEqual({r['status'] for r in result['cases']}, {'unexecuted'})

    def test_changed_frozen_limits_and_scientific_flags_refuse_before_execution(self):
        for key, value in [('limits', {'upstream_calls_including_smoke': 999}),
                           ('human_gold_qualified', True), ('source_stage_sha256', 'wrong-source-hash')]:
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                plan = root / 'plan'
                plan.mkdir()
                row = {**MODULE.fixed_plan_fields(), key: value}
                (plan / 'plan.json').write_text(json.dumps(row))
                with self.assertRaisesRegex(ValueError, 'fixed_bounds_bindings_or_qualification_changed'):
                    MODULE.execute(plan, root / 'execution', root / 'python', root / 'site', root / 'report', 'live')
                self.assertFalse((root / 'execution').exists())

    def test_cleanup_errors_are_retained_without_losing_later_processes(self):
        class Process:
            pid, returncode = 123, None
            def poll(self):
                return None
            def terminate(self):
                raise OSError('owned cleanup failure')
            def kill(self):
                raise OSError('owned kill failure')
        rows = MODULE.stop_processes([Process(), Process()])
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r['cleanup_error_type'] == 'OSError:OSError' and r['reaped'] is False for r in rows))


if __name__ == '__main__':
    unittest.main()
