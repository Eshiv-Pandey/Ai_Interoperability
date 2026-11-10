"""Constructed software checks; no original AP2, provider or key access."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import marshal
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/ap2_reference_development_v2.py"
SPEC = importlib.util.spec_from_file_location("ap2_reference_development_v2_tests_subject", SCRIPT)
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)


class DevelopmentSoftwareTests(unittest.TestCase):
    def test_child_environment_removes_all_provider_secrets_and_cloud_configuration(self):
        supplied = {"SystemRoot": "C:/Windows", "PATH": "C:/Python313",
                    "GOOGLE_API_KEY": "constructed-test-secret",
                    "GEMINI_API_KEY": "another-constructed-secret",
                    "GOOGLE_APPLICATION_CREDENTIALS": "private.json",
                    "OPENAI_API_KEY": "constructed-secret",
                    "ANTHROPIC_API_KEY": "constructed-secret",
                    "GOOGLE_CLOUD_PROJECT": "billing-project", "UNRELATED_TOKEN": "opaque"}
        result = subject.child_environment(Path("C:/owned/profile"), supplied)
        self.assertEqual(result["SystemRoot"], "C:/Windows")
        self.assertEqual(result["PAYMENT_METHOD"], "CARD")
        self.assertEqual(result["GOOGLE_GENAI_USE_VERTEXAI"], "false")
        self.assertTrue(all(key not in result for key in supplied if "KEY" in key or "TOKEN" in key))
        self.assertNotIn("GOOGLE_APPLICATION_CREDENTIALS", result)
        self.assertNotIn("GOOGLE_CLOUD_PROJECT", result)

    def test_extraction_preserves_complete_code_object_and_defaults(self):
        raw = b"def original(value, suffix='source'):\n    return value + suffix\n"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "original.py"
            path.write_bytes(raw)
            ns, identities = subject.extract_functions(path, ["original"], {},
                                                       hashlib.sha256(raw).hexdigest())
            expected = next(code for code in compile(raw, str(path), "exec", dont_inherit=True).co_consts
                            if isinstance(code, types.CodeType))
            self.assertEqual(marshal.dumps(ns["original"].__code__), marshal.dumps(expected))
            self.assertEqual(ns["original"]("value"), "valuesource")
            self.assertEqual(ns["original"].__defaults__, ("source",))
            self.assertEqual(identities["original"]["first_line"], 1)

    def test_changed_source_refused_before_any_function_is_created(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "source.py"
            path.write_text("def call():\n    return 'changed'\n", encoding="utf-8")
            namespace = {}
            with self.assertRaises(subject.DevelopmentError):
                subject.extract_functions(path, ["call"], namespace, "0" * 64)
            self.assertNotIn("call", namespace)

    def test_extraction_refuses_decorator_without_executing_it(self):
        raw = b"@untrusted_decorator\ndef call():\n    return 1\n"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "source.py"
            path.write_bytes(raw)
            with self.assertRaises(subject.DevelopmentError):
                subject.extract_functions(path, ["call"], {}, hashlib.sha256(raw).hexdigest())

    def test_immediate_coroutine_keeps_return_and_exception(self):
        async def completes():
            return {"actual": 7}
        sentinel = RuntimeError("constructed-error")
        async def fails():
            raise sentinel
        self.assertEqual(subject.immediate(completes()), {"actual": 7})
        with self.assertRaises(RuntimeError) as outcome:
            subject.immediate(fails())
        self.assertIs(outcome.exception, sentinel)

    def test_external_async_wait_refused_and_coroutine_closed(self):
        closed = []
        class Pauses:
            def __await__(self):
                yield object()
        async def waits():
            try:
                await Pauses()
            finally:
                closed.append(True)
        with self.assertRaises(subject.DevelopmentError):
            subject.immediate(waits())
        self.assertEqual(closed, [True])

    def test_consumed_output_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "new"
            subject.allocate_output(target)
            marker = target / "marker"
            marker.write_text("retained", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                subject.allocate_output(target)
            self.assertEqual(marker.read_text(), "retained")

    def test_duplicate_and_nonfinite_json_refused(self):
        for raw in (b'{"status":true,"status":false}', b'{"limit":NaN}', b'{"limit":Infinity}'):
            with self.assertRaises(subject.DevelopmentError):
                subject.strict_json(raw)

    def test_status_helper_output_allowlist_does_not_echo_unknown_fields(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            helper = root / subject.SETUP_REL
            helper.parent.mkdir()
            helper.write_text("# constructed helper", encoding="utf-8")
            outcome = types.SimpleNamespace(returncode=0, stdout=json.dumps({
                "configured": True, "path": "C:/outside/credentials/gemini-api-key.dpapi",
                "secret": "constructed-secret"}).encode(), stderr=b"")
            with patch.object(subject, "SETUP_SHA", hashlib.sha256(helper.read_bytes()).hexdigest()), \
                    patch.object(subject.shutil, "which", return_value="C:/Windows/powershell.exe"):
                with self.assertRaises(subject.DevelopmentError):
                    subject.secure_status(root, run=lambda *args, **kwargs: outcome)

    def test_metadata_projection_excludes_provider_body_headers_and_payload(self):
        receipt = {"schema_version": "gemini-model-metadata-access/1",
                   "requested_model": subject.MODEL, "content_generation_requested": False,
                   "probe_source_sha256": "a4c4378311d93a03bb29e0d89500dd4efbd8525cf66c54e95d773ad9a5ee3498",
                   "finished_at_utc": "2026-11-10T12:00:00+00:00",
                   "status": "metadata_access_confirmed", "http_status": 200,
                   "request_attempted": True,
                   "headers": {"x-goog-api-key": "constructed-secret"},
                   "body": "provider-body", "request_payload": "private-input",
                   "free_tier_or_billing_verified": True, "generation_quota_verified": True}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "receipt.json"
            path.write_text(json.dumps(receipt), encoding="utf-8")
            projection = subject.metadata_summary(path)
            self.assertFalse(projection["free_tier_or_billing_verified"])
            self.assertFalse(projection["generation_quota_verified"])
            encoded = json.dumps(projection)
            self.assertNotIn("constructed-secret", encoded)
            self.assertNotIn("provider-body", encoded)
            self.assertNotIn("private-input", encoded)

    def test_metadata_free_text_status_refused(self):
        receipt = {"schema_version": "gemini-model-metadata-access/1",
                   "requested_model": subject.MODEL, "content_generation_requested": False,
                   "probe_source_sha256": "a4c4378311d93a03bb29e0d89500dd4efbd8525cf66c54e95d773ad9a5ee3498",
                   "finished_at_utc": "2026-11-10T12:00:00+00:00",
                   "status": "untrusted free text", "http_status": 200}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "receipt.json"
            path.write_text(json.dumps(receipt), encoding="utf-8")
            with self.assertRaises(subject.DevelopmentError):
                subject.metadata_summary(path)

    def test_cleanup_rejects_unowned_directory_and_preserves_its_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / "agent_provider_signing_key.pem"
            marker.write_text("constructed-owned-elsewhere", encoding="utf-8")
            result = subject.cleanup_profile(root)
            self.assertFalse(result["complete"])
            self.assertTrue(marker.exists())

    def test_postcapture_rejects_source_binding_changed_after_parent_preparation(self):
        actual = {"events_sha256": "a" * 64}
        declared = {"events_sha256": "b" * 64}
        with self.assertRaises(subject.DevelopmentError) as outcome:
            subject.validate_capture_copies(Path("unused"), actual, declared)
        self.assertEqual(str(outcome.exception), "postcapture_source_changed_since_plan")

    def test_postcapture_rejects_altered_retained_copy_and_accepts_exact_copies(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            inputs = output / "retained-inputs"
            inputs.mkdir()
            mapping = {"source-plan.json": "plan_sha256", "source-result.json": "result_sha256",
                       "source-events.jsonl": "events_sha256", "source-runner.py": "executed_runner_sha256"}
            binding = {}
            for filename, key in mapping.items():
                raw = ("constructed-" + filename).encode()
                (inputs / filename).write_bytes(raw)
                binding[key] = hashlib.sha256(raw).hexdigest()
            subject.validate_capture_copies(output, binding, dict(binding))
            (inputs / "source-events.jsonl").write_bytes(b"changed")
            with self.assertRaises(subject.DevelopmentError) as outcome:
                subject.validate_capture_copies(output, binding, dict(binding))
            self.assertEqual(str(outcome.exception), "postcapture_retained_copy_changed")


if __name__ == "__main__":
    unittest.main()
