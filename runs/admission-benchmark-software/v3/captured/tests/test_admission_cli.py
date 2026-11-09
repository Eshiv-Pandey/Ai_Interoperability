import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from interoperability.admission_cli import run_admission


ROOT = Path(__file__).resolve().parents[1]
POSITIVE = ROOT / "examples/development/positive.json"


class AdmissionReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "receipt.json"

    def test_positive_receipt_has_checked_witness_and_cannot_be_overwritten(self):
        result = run_admission(POSITIVE, self.output, "baseline", 20)
        self.assertEqual(result["result"]["decision"], "supported")
        self.assertTrue(result["certificate_valid"])
        self.assertEqual(result["status"], "recorded")
        old = self.output.read_bytes()
        with self.assertRaisesRegex(ValueError, "overwrite"):
            run_admission(POSITIVE, self.output, "baseline", 20)
        self.assertEqual(old, self.output.read_bytes())

    def test_unknown_is_not_reported_as_an_independently_checked_certificate(self):
        result = run_admission(POSITIVE, self.output, "baseline", 4102444801)
        self.assertEqual(result["result"]["decision"], "unknown")
        self.assertIsNone(result["certificate_valid"])
        self.assertTrue(result["unknown_has_no_certificate"])

    def test_input_mutation_is_retained_as_failure_without_corrupting_input_record(self):
        original = json.loads(POSITIVE.read_bytes())

        def mutate(model, now):
            model["id"] = "tampered"
            return {"decision": "unknown", "certificate": None}

        method = (SimpleNamespace(evaluate=mutate), None, "finite-continuation/1")
        with patch("interoperability.admission_cli._method", return_value=method):
            result = run_admission(POSITIVE, self.output, "baseline", 20)
        self.assertEqual(result["status"], "failed")
        self.assertIn("mutated", result["error"])
        self.assertEqual(json.loads(self.output.read_bytes())["runtime_manifest"], original)

    def test_solver_error_is_an_error_record_not_an_unsupported_decision(self):
        def fail(model, now):
            raise RuntimeError("development solver failure")

        method = (SimpleNamespace(evaluate=fail), None, "finite-continuation/1")
        with patch("interoperability.admission_cli._method", return_value=method):
            result = run_admission(POSITIVE, self.output, "baseline", 20)
        self.assertEqual(result["status"], "failed")
        self.assertNotIn("result", result)
        self.assertIn("RuntimeError", result["error"])

    def test_duplicate_json_keys_are_input_errors(self):
        source = Path(self.temp.name) / "duplicate.json"
        source.write_text('{"id":"a","id":"b"}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            run_admission(source, self.output, "baseline", 20)
        self.assertFalse(self.output.exists())
