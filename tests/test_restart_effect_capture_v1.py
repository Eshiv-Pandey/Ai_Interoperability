"""Synthetic selection/manifest regressions; no archive or effect execution."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("effect_capture", ROOT / "scripts/capture_restart_effect_example_v1.py")
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)


def encoded(value):
    return json.dumps(value).encode("utf-8")


class EffectCaptureTests(unittest.TestCase):
    def setUp(self):
        self.identity = {"app_name": "agentops-agent", "user_id": "user", "session_id": "session", "invocation_id": "invocation"}
        action = {"id": "action", "name": "restart_service", "args": {"name": "inventory"}}
        confirmation = {"id": "confirmation", "name": "adk_request_confirmation", "args": {
            "originalFunctionCall": deepcopy(action), "toolConfirmation": {"confirmed": False}}}
        approval = {"id": "confirmation", "name": "adk_request_confirmation", "response": {
            "confirmed": True, "payload": {"rationale": "Inventory is down and INC-002 matches the service-down runbook."}}}
        entries = [
            ("call", "function_call", action, "agent"),
            ("confirmation", "function_call", confirmation, "agent"),
            ("pending", "function_response", {"id": "action", "name": "restart_service", "response": {"error": "confirmation required"}}, "agent"),
            ("approval", "function_response", approval, "user"),
            ("executed", "function_response", {"id": "action", "name": "restart_service", "response": {"audit": {}}}, "agent"),
        ]
        self.rows = [{**self.identity, "event_id": event, "part_index": 0, "kind": kind,
                      "function_id": function["id"], "function": function, "author": author}
                     for event, kind, function, author in entries]
        self.report = {"pairs": [self.pair(row) for row in self.rows]}
        message = {"taskId": "task", "contextId": "context", "parts": [
            {"metadata": {"adk_type": "function_response"}, "data": approval}]}
        self.view = {"records": [{"capture_sequence": 3, "rpc_method": "SendMessage", "request": {"params": {"message": message}}}]}

    def pair(self, row):
        return {**self.identity, "task_id": "task", "context_id": "context",
                "matched_raw_event_id": row["event_id"], "matched_raw_part_index": row["part_index"],
                "matched_raw_invocation_id": row["invocation_id"]}

    def files(self):
        return {"inputs/raw/function-observations.json": encoded(self.rows),
                "inputs/public/observations.json": encoded(self.view),
                **{f"inputs/public/wire/000003/{name}": b"{}" for name in (
                    "before.snapshot.json", "after.snapshot.json", "exchange.json")}}

    def test_selects_actual_approval_sequence_and_bound_original_call(self):
        args, association = capture.select_fixture(self.files(), self.report)
        self.assertEqual(association["approval_sequence"], 3)
        self.assertTrue(association["supplied_confirmation_payload_links_checked"])
        self.assertEqual(args[2]["original_function_call"], self.rows[0]["function"])
        self.assertEqual(args[3], self.identity)

    def test_confirmation_cannot_bind_another_action(self):
        self.rows[1]["function"]["args"]["originalFunctionCall"]["args"]["name"] = "another-service"
        with self.assertRaisesRegex(ValueError, "does not bind"):
            capture.select_fixture(self.files(), self.report)

    def test_approval_cannot_substitute_confirmation_id(self):
        self.rows[1]["function_id"] = self.rows[1]["function"]["id"] = "another-confirmation"
        with self.assertRaisesRegex(ValueError, "matching confirmation call"):
            capture.select_fixture(self.files(), self.report)

    def test_approval_request_cannot_replace_original_task(self):
        self.view["records"][0]["request"]["params"]["message"]["taskId"] = "another-task"
        with self.assertRaisesRegex(ValueError, "actual linked approval request"):
            capture.select_fixture(self.files(), self.report)

    def test_duplicate_confirmation_is_ambiguous(self):
        duplicate = {**deepcopy(self.rows[1]), "event_id": "duplicate-confirmation"}
        self.rows.append(duplicate)
        self.report["pairs"].append(self.pair(duplicate))
        with self.assertRaisesRegex(ValueError, "matching confirmation call"):
            capture.select_fixture(self.files(), self.report)

    def test_manifest_boolean_byte_count_is_rejected(self):
        receipt = {"schema_version": "agentops-event-binding/1", "status": "passed",
                   **{name: True for name in ("inputs_unchanged", "implementation_unchanged", "captured_files_unchanged", "input_manifests_verified")},
                   "files": [{"path": "fixture.bin", "bytes": True, "sha256": capture._digest(b"x")["sha256"]}]}
        with self.assertRaisesRegex(ValueError, "manifest digest"):
            capture.check_manifest({"fixture.bin": b"x", "result.json": encoded(receipt)})


if __name__ == "__main__":
    unittest.main()
