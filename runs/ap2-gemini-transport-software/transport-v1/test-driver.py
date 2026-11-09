"""Once-only constructed transport checks, with no SDK or native imports.

All quota evidence and client classes below are synthetic. The audit hook
denies socket operations and child launches. No genuine guard is installed.
"""
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "runs/ap2-gemini-transport-software/transport-v1"
ACCOUNTING = ROOT / "src/interoperability/ap2_hp_gemini_usage_v1.py"
TRANSPORT = ROOT / "src/interoperability/ap2_hp_gemini_transport_v1.py"
NOW = "2026-10-30T16:00:00+00:00"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def finite(coroutine):
    """Drive only an immediately completing synthetic coroutine; no event loop."""
    try:
        coroutine.send(None)
    except StopIteration as done:
        return done.value
    finally:
        coroutine.close()
    raise AssertionError("Synthetic coroutine suspended unexpectedly")


def load(raw, path, name):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(raw, str(path), "exec", dont_inherit=True), module.__dict__)
    return module


def main():
    if OUTPUT.exists():
        raise ValueError("Consumed transport allocation cannot be rerun")
    paths = {"accounting-core.py": ACCOUNTING, "transport.py": TRANSPORT,
             "test-driver.py": Path(__file__).resolve()}
    before = {name: path.read_bytes() for name, path in paths.items()}
    OUTPUT.mkdir(parents=True)
    for name, raw in before.items():
        (OUTPUT / name).write_bytes(raw)
    plan = {"schema_version": "ap2-hp-gemini-transport-software/1",
            "source_hashes": {name: digest(raw) for name, raw in before.items()},
            "scope": "Constructed clients and synthetic local quota ledgers only",
            "provider_requests": 0, "sdk_imports": 0, "original_application_imports": 0,
            "genuine_native_guard_installed": False, "actual_quota_reserved": False}
    (OUTPUT / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    def deny(event, arguments):
        if event.startswith("socket.") or event in {"subprocess.Popen", "os.system", "os.spawn", "os.posix_spawn", "os.exec"}:
            raise RuntimeError("Transport software capture denies network and process launch")
    sys.addaudithook(deny)
    accounting = load(before["accounting-core.py"], ACCOUNTING, "constructed_accounting")
    transport = load(before["transport.py"], TRANSPORT, "constructed_transport")

    class Checks(unittest.TestCase):
        def setUp(self):
            self.directory = OUTPUT / self._testMethodName
            self.directory.mkdir()
            evidence = self.directory / "synthetic-evidence.txt"
            evidence.write_text("SYNTHETIC. NOT PROVIDER EVIDENCE OR HUMAN REVIEW.\n", encoding="utf-8")
            self.policy = {"schema_version": accounting.POLICY_SCHEMA, "model": accounting.MODEL,
                "project_alias": "synthetic", "run_id": "a" * 32, "configuration_sha256": "b" * 64,
                "observed_at_utc": NOW, "expires_at_utc": "2026-10-30T17:00:00+00:00",
                "billing_mode": "reviewed_free_tier",
                "allowance_evidence": [{"path": str(evidence), "sha256": digest(evidence.read_bytes())}],
                "remaining_total_tokens": 1000, "remaining_day_requests": 20,
                "requests_per_minute": 100, "input_tokens_per_minute": 10000,
                "initial_minute_requests": 0, "initial_minute_input_tokens": 0,
                "full_input_upper_bound": 100, "maximum_output_upper_bound": 20,
                **{key: True for key in accounting.VERIFIED}}
            self.ledger = self.directory / "ledger.sqlite"
            self.guards = []
            self.sent = []
            self.before_send = None
            owner = self
            class Request:
                def __init__(self, url=transport.ENDPOINT, method="POST", content=b'{"synthetic":true}'):
                    self.url, self.method, self.content = url, method, content
            class Response:
                def __init__(self, status=200, document=None):
                    self.status_code, self.closed = status, False
                    self.read_error = self.close_error = None
                    self.document = {"usageMetadata": {"promptTokenCount": 45,
                        "candidatesTokenCount": 10, "totalTokenCount": 55}} if document is None else document
                def read(self):
                    if self.read_error is not None:
                        raise self.read_error
                    return json.dumps(self.document).encode()
                def close(self):
                    self.closed = True
                    if self.close_error is not None:
                        raise self.close_error
            class SyncClient:
                def _send_single_request(self, request):
                    if owner.before_send is not None:
                        owner.before_send(request)
                    owner.sent.append(request)
                    if isinstance(self.outcome, BaseException):
                        raise self.outcome
                    return self.outcome
            class ApiClient:
                def _request_once(self, request, stream=False):
                    result = None
                    for _ in range(self.transmissions):
                        result = self._httpx_client._send_single_request(request)
                    return result
                async def _async_request_once(self, request, stream=False):
                    raise AssertionError("Synthetic original async SDK must never execute")
            class AsyncClient:
                async def _send_single_request(self, request):
                    owner.sent.append(request)
                    return request
            class AioRequest:
                async def send(self, connection):
                    owner.sent.append(self)
                    return connection
            self.Request, self.Response = Request, Response
            self.Sync, self.Api, self.Async, self.Aio = SyncClient, ApiClient, AsyncClient, AioRequest
            self.originals = [(cls, name, cls.__dict__[name]) for cls, name in (
                (self.Sync, "_send_single_request"), (self.Async, "_send_single_request"),
                (self.Aio, "send"), (self.Api, "_request_once"), (self.Api, "_async_request_once"))]

        def tearDown(self):
            for guard in self.guards:
                self.assertTrue(guard.restore(), "Constructed class restoration must complete")
            self.assertIsNone(transport._INVOCATION.get())

        def bind(self, **kwargs):
            initialized = accounting.create_ledger(self.ledger, self.policy, now=NOW)
            guard = transport.ProviderGuard(accounting, self.ledger, initialized["policy_sha256"],
                "merchant", 100, clock=lambda: NOW, **kwargs)
            self.guards.append(guard)
            guard.bind_classes(self.Api, self.Sync, self.Async, self.Aio)
            client = self.Api()
            client.vertexai, client.transmissions = False, 1
            client._httpx_client = self.Sync()
            client._httpx_client.outcome = self.Response()
            self.guard, self.client = guard, client
            return client

        def count(self):
            with sqlite3.connect(self.ledger) as db:
                return db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]

        def test_committed_reservation_precedes_original_transmission(self):
            client = self.bind()
            request = self.Request()
            def inspect(actual):
                self.assertIs(actual, request)
                with sqlite3.connect(self.ledger) as db:
                    row = db.execute("SELECT request_digest,charged_total,state FROM attempts").fetchone()
                    self.assertEqual(row, (digest(request.content), 120, "reserved_unknown_usage"))
                    self.assertEqual(db.execute("SELECT kind FROM events").fetchone()[0], "reserved_before_attempt")
            self.before_send = inspect
            response = client._httpx_client.outcome
            self.assertIs(client._request_once(request), response)
            self.assertIs(self.sent[0], request)
            self.assertEqual(self.guard.records[-1]["charged_total_tokens"], 55)
            self.assertEqual(self.guard.records[-1]["reported_total_tokens"], 55)

        def test_every_inner_transmission_has_its_own_reservation(self):
            client = self.bind()
            client.transmissions = 3
            observed = []
            self.before_send = lambda request: observed.append(self.count())
            client._request_once(self.Request())
            self.assertEqual(observed, [1, 2, 3])
            self.assertEqual(self.count(), 3)

        def test_repeated_sdk_invocations_restore_context(self):
            client = self.bind()
            for _ in range(2):
                client._request_once(self.Request())
                self.assertIsNone(transport._INVOCATION.get())
            self.assertEqual(self.count(), 2)

        def test_quota_denial_occurs_before_sender(self):
            self.policy["remaining_day_requests"] = 2
            client = self.bind()
            client._request_once(self.Request())
            with self.assertRaises(accounting.UsageRefused):
                client._request_once(self.Request())
            self.assertEqual(len(self.sent), 1)
            self.assertEqual(self.count(), 1)

        def test_unknown_usage_returns_original_response_and_stops_retry(self):
            client = self.bind()
            response = client._httpx_client.outcome = self.Response(document={"synthetic": True})
            self.assertIs(client._request_once(self.Request()), response)
            self.assertEqual(self.guard.records[-1]["charged_total_tokens"], 120)
            with self.assertRaises(accounting.UsageRefused):
                client._request_once(self.Request())
            self.assertEqual(len(self.sent), 1)

        def test_deep_json_is_unknown_usage_preserving_response(self):
            client = self.bind()
            response = client._httpx_client.outcome
            response.read = lambda: b"[" * 2000 + b"0" + b"]" * 2000
            self.assertIs(client._request_once(self.Request()), response)
            self.assertEqual(self.guard.records[-1]["charged_total_tokens"], 120)
            with self.assertRaises(accounting.UsageRefused):
                client._request_once(self.Request())
            self.assertEqual(len(self.sent), 1)

        def test_429_returns_original_response_and_stops_retry(self):
            client = self.bind()
            response = client._httpx_client.outcome = self.Response(status=429)
            self.assertIs(client._request_once(self.Request()), response)
            with self.assertRaises(accounting.UsageRefused):
                client._request_once(self.Request())
            self.assertEqual(len(self.sent), 1)

        def test_original_sender_exception_identity_and_charge_are_preserved(self):
            client = self.bind()
            original = client._httpx_client.outcome = RuntimeError("constructed original failure")
            with self.assertRaises(RuntimeError) as raised:
                client._request_once(self.Request())
            self.assertIs(raised.exception, original)
            self.assertEqual(self.guard.records[-1]["charged_total_tokens"], 120)
            with self.assertRaises(accounting.UsageRefused):
                client._request_once(self.Request())

        def test_read_failure_closes_response_preserving_original_error(self):
            client = self.bind()
            response = client._httpx_client.outcome
            original = response.read_error = RuntimeError("constructed read failure")
            with self.assertRaises(RuntimeError) as raised:
                client._request_once(self.Request())
            self.assertIs(raised.exception, original)
            self.assertTrue(response.closed)
            self.assertEqual(self.guard.records[-1]["charged_total_tokens"], 120)

        def test_cleanup_failure_cannot_replace_read_failure(self):
            client = self.bind()
            response = client._httpx_client.outcome
            original = response.read_error = RuntimeError("constructed read failure")
            response.close_error = ValueError("constructed close failure")
            with self.assertRaises(RuntimeError) as raised:
                client._request_once(self.Request())
            self.assertIs(raised.exception, original)
            self.assertTrue(response.closed)
            self.assertTrue(self.guard.halt_path.exists())
            self.assertTrue(self.guard.disabled)

        def test_reconciliation_failure_preserves_response_and_halts(self):
            client = self.bind()
            original = accounting.record_provider_result
            def broken(*args, **kwargs):
                raise OSError("constructed reconciliation failure")
            accounting.record_provider_result = broken
            try:
                self.assertIs(client._request_once(self.Request()), client._httpx_client.outcome)
                with self.assertRaises(transport.TransportRefused):
                    client._request_once(self.Request())
            finally:
                accounting.record_provider_result = original
            self.assertEqual(len(self.sent), 1)
            with sqlite3.connect(self.ledger) as db:
                self.assertEqual(db.execute("SELECT charged_total FROM attempts").fetchone()[0], 120)

        def test_unrelated_http_passthrough_preserves_request_and_response(self):
            client = self.bind()
            request = self.Request(url="http://127.0.0.1:8123/synthetic")
            response = client._httpx_client.outcome
            self.assertIs(client._httpx_client._send_single_request(request), response)
            self.assertIs(self.sent[0], request)
            self.assertEqual(self.count(), 0)

        def test_provider_request_outside_sdk_context_refuses(self):
            client = self.bind()
            with self.assertRaises(transport.TransportRefused):
                client._httpx_client._send_single_request(self.Request())
            self.assertEqual(self.sent, [])
            self.assertEqual(self.count(), 0)

        def test_endpoint_method_and_body_bounds_refuse_before_send(self):
            client = self.bind()
            for request in (self.Request(url=transport.ENDPOINT + "?synthetic=true"),
                            self.Request(method="GET"), self.Request(content=b"x" * 101),
                            self.Request(content="not bytes")):
                with self.assertRaises(transport.TransportRefused):
                    client._request_once(request)
            self.assertEqual(self.sent, [])
            self.assertEqual(self.count(), 0)

        def test_streaming_and_vertex_profiles_refuse_before_send(self):
            client = self.bind()
            with self.assertRaises(transport.TransportRefused):
                client._request_once(self.Request(), stream=True)
            client.vertexai = True
            with self.assertRaises(transport.TransportRefused):
                client._request_once(self.Request())
            self.assertEqual(self.sent, [])
            self.assertEqual(self.count(), 0)

        def test_unreviewed_client_refuses_before_send(self):
            def reject(client):
                raise transport.TransportRefused("constructed custom-client refusal")
            client = self.bind(client_check=reject)
            with self.assertRaises(transport.TransportRefused):
                client._request_once(self.Request())
            self.assertEqual(self.sent, [])

        def test_async_sdk_refuses_without_running_original(self):
            client = self.bind()
            with self.assertRaises(transport.TransportRefused):
                finite(client._async_request_once(self.Request()))
            self.assertEqual(self.sent, [])

        def test_async_httpx_provider_refuses_and_unrelated_passes(self):
            self.bind()
            client = self.Async()
            with self.assertRaises(transport.TransportRefused):
                finite(client._send_single_request(self.Request()))
            request = self.Request(url="https://example.invalid/synthetic")
            self.assertIs(finite(client._send_single_request(request)), request)
            self.assertEqual(self.sent, [request])

        def test_aiohttp_provider_refuses_and_unrelated_passes(self):
            self.bind()
            request = self.Aio()
            request.url = transport.ENDPOINT
            with self.assertRaises(transport.TransportRefused):
                finite(request.send(object()))
            request.url = "https://example.invalid/synthetic"
            connection = object()
            self.assertIs(finite(request.send(connection)), connection)
            self.assertEqual(self.sent, [request])

        def test_provider_host_families_and_lookalikes(self):
            for url in (transport.ENDPOINT, "https://aiplatform.googleapis.com/x",
                        "https://us-central1-aiplatform.googleapis.com/x",
                        "https://us-central1.aiplatform.googleapis.com/x"):
                self.assertTrue(transport.provider_url(url))
            self.assertFalse(transport.provider_url("https://generativelanguage.googleapis.com.example.invalid/x"))

        def test_restore_keeps_authority_on_foreign_patch(self):
            self.bind()
            owned = self.Sync.__dict__["_send_single_request"]
            foreign = lambda client, request: request
            self.Sync._send_single_request = foreign
            self.assertFalse(self.guard.restore())
            self.assertIs(self.Sync._send_single_request, foreign)
            self.assertTrue(self.guard.report()["patch_authority_retained"])
            self.Sync._send_single_request = owned
            self.assertTrue(self.guard.restore())
            for cls, name, original in self.originals:
                self.assertIs(cls.__dict__[name], original)

        def test_missing_native_evidence_refuses_before_sdk_import(self):
            original = transport.importlib.import_module
            imported = []
            def reject(name):
                imported.append(name)
                raise AssertionError("SDK import must be unreachable")
            transport.importlib.import_module = reject
            try:
                result = transport.install_guard(plan={}, service={}, configuration_sha256="b" * 64)
            finally:
                transport.importlib.import_module = original
            self.assertFalse(result["installed"])
            self.assertEqual(imported, [])
            self.assertIsNone(transport._LIVE_GUARD)

        def test_duplicate_install_refusal_does_not_release_existing_lease(self):
            self.bind()
            transport._LIVE_GUARD = self.guard
            owned = self.Api.__dict__["_request_once"]
            try:
                result = transport.install_guard(plan={}, service={}, configuration_sha256="b" * 64)
                self.assertFalse(result["installed"])
                self.assertIs(transport._LIVE_GUARD, self.guard)
                self.assertIs(self.Api.__dict__["_request_once"], owned)
                self.assertEqual(len(self.guard.patches), 5)
            finally:
                transport._LIVE_GUARD = None

        def test_compiled_method_identity_detects_source_tampering(self):
            path = self.directory / "synthetic-client.py"
            raw = b"class Synthetic:\n    def send(self, request):\n        return request\n"
            path.write_bytes(raw)
            module = load(raw, path, "synthetic_identity")
            original = module.Synthetic.__dict__["send"]
            self.assertIs(transport.verify_method(module.Synthetic, "send", path, raw), original)
            tampered = raw.replace(b"return request", b"return None")
            with self.assertRaises(transport.TransportRefused):
                transport.verify_method(module.Synthetic, "send", path, tampered)

        def test_exception_table_tampering_cannot_match_source(self):
            path = self.directory / "synthetic-exception-client.py"
            raw = b"class Synthetic:\n    def send(self, request):\n        try:\n            return request\n        finally:\n            self.finished = True\n"
            path.write_bytes(raw)
            module = load(raw, path, "synthetic_exception_identity")
            function = module.Synthetic.__dict__["send"]
            self.assertTrue(function.__code__.co_exceptiontable)
            transport.verify_method(module.Synthetic, "send", path, raw)
            function.__code__ = function.__code__.replace(co_exceptiontable=b"")
            with self.assertRaises(transport.TransportRefused):
                transport.verify_method(module.Synthetic, "send", path, raw)

        def test_unverified_native_construction_refuses_selected_profile(self):
            self.assertFalse(transport.NATIVE_CLIENT_CONSTRUCTION_VERIFIED)
            original = transport.importlib.import_module
            def reject(name):
                raise AssertionError("Unverified native client construction cannot import SDK")
            transport.importlib.import_module = reject
            try:
                result = transport.install_guard(plan={"model": transport.MODEL},
                    service={"role": "merchant"}, configuration_sha256="b" * 64)
            finally:
                transport.importlib.import_module = original
            self.assertFalse(result["installed"])
            self.assertFalse(result["native_client_construction_verified"])

    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    (OUTPUT / "stdout.txt").write_text(stream.getvalue(), encoding="utf-8")
    unchanged = {name: path.read_bytes() == before[name] and (OUTPUT / name).read_bytes() == before[name]
                 for name, path in paths.items()}
    receipt = {**plan, "status": "passed" if result.wasSuccessful() and all(unchanged.values()) else "failed",
               "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
               "skips": len(result.skipped), "original_and_copied_inputs_unchanged": unchanged,
               "synthetic_quota_fixtures_only": True, "native_qualification_established": False}
    (OUTPUT / "result.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
