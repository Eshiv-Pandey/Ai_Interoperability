"""Previously unexecuted pure planning CLI paths; no original/client/model use."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/ap2_hp_reference_client_v1.py"
NONCE = "a" * 32
CONTRACT = {"catalog_search": "coffee maker", "user_email": "declared-demo@example.test",
            "currency": "USD", "max_amount_cents": 10000}


class ReferencePlanningCliTests(unittest.TestCase):
    def invoke(self, raw):
        with tempfile.TemporaryDirectory(prefix="ap2-pure-cli-test-") as directory:
            input_path = Path(directory) / "planning-input.json"
            input_path.write_text(raw, encoding="utf-8")
            result = subprocess.run([sys.executable, "-I", "-S", "-B", str(CLI), "--input", str(input_path),
                "--message-id", NONCE], capture_output=True, check=False)
        self.assertEqual(result.stderr, b"")
        return result.returncode, json.loads(result.stdout)

    def test_successful_initial_plan_exact_public_message_without_native_dispatch(self):
        code, value = self.invoke(json.dumps({"contract": CONTRACT, "observations": []}))
        self.assertEqual(code, 0)
        self.assertEqual(value["next_phase"], "catalog")
        self.assertFalse(value["native_execution_enabled"])
        self.assertFalse(value["next_action"]["dispatch_eligible"])
        self.assertEqual(value["next_action"]["endpoint"], "http://localhost:8001/a2a/merchant_agent")
        self.assertEqual(value["next_action"]["message"], {
            "kind": "message", "messageId": NONCE, "role": "agent", "parts": [
                {"kind": "text", "text": "Find products that match the user's request."},
                {"kind": "data", "data": {"catalog_search": "coffee maker"}},
                {"kind": "data", "data": {"risk_data": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...fake_risk_data"}},
                {"kind": "data", "data": {"shopping_agent_id": "trusted_shopping_agent"}},
            ]})
        self.assertEqual(value["observations"], [])
        self.assertIsNone(value["aggregate_task_grade"])

    def test_duplicate_json_keys_refused_before_phase_construction(self):
        raw = '{"contract":' + json.dumps(CONTRACT) + ',"contract":' + json.dumps(CONTRACT) + ',"observations":[]}'
        code, value = self.invoke(raw)
        self.assertEqual(code, 2)
        self.assertEqual(value["status"], "planning_input_refused")
        self.assertIn("Duplicate JSON key", value["reason"])
        self.assertIsNone(value["refused_phase"])
        self.assertEqual(value["accepted_supplied_phases"], 0)
        self.assertFalse(value["native_execution_enabled"])

    def test_nonfinite_json_number_refused_before_phase_construction(self):
        raw = json.dumps({"contract": {**CONTRACT, "max_amount_cents": float("nan")}, "observations": []})
        code, value = self.invoke(raw)
        self.assertEqual(code, 2)
        self.assertEqual(value["status"], "planning_input_refused")
        self.assertIn("Nonfinite JSON number", value["reason"])
        self.assertIsNone(value["refused_phase"])
        self.assertEqual(value["accepted_supplied_phases"], 0)
        self.assertFalse(value["native_execution_enabled"])


if __name__ == "__main__":
    unittest.main()
