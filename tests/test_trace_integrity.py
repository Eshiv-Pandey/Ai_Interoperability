import json
import tempfile
import unittest
from pathlib import Path

from interoperability.cli import run_development
from interoperability.manifest import digest
from test_baseline import tiny_model


class DevelopmentTraceIntegrity(unittest.TestCase):
    def test_keeps_exact_runtime_manifest_and_actual_checked_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.json"
            model = tiny_model()
            source.write_text(json.dumps(model), encoding="utf-8")
            output = root / "trace.jsonl"
            summary = run_development([source], output, now=20)
            rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(summary["agreements"], 1)
            self.assertEqual(rows[0]["experiment_kind"], "authored-development")
            self.assertEqual(rows[1]["runtime_manifest"], model)
            self.assertEqual(rows[1]["model_sha256"], digest(model))
            self.assertTrue(rows[1]["certificate_valid"])
            self.assertEqual(rows[2]["cases"], 1)
            self.assertGreaterEqual(rows[1]["baseline_ns"], 0)

    def test_refuses_overwriting_existing_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.json"
            source.write_text(json.dumps(tiny_model()), encoding="utf-8")
            output = root / "trace.jsonl"
            output.write_text("original evidence", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "overwrite"):
                run_development([source], output, now=20)
            self.assertEqual(output.read_text(encoding="utf-8"), "original evidence")

    def test_development_runner_cannot_label_wire_data_as_authored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.json"
            model = tiny_model()
            model["provenance"]["kind"] = "wire-derived"
            source.write_text(json.dumps(model), encoding="utf-8")
            output = root / "trace.jsonl"
            with self.assertRaisesRegex(ValueError, "authored-development"):
                run_development([source], output, now=20)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
