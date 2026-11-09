"""Actual captured development traces plus explicitly controlled mutations.

Mutations are semantic validation controls, never claims of natural bridge bugs.
"""

import copy
import hashlib
import json
import unittest
from pathlib import Path

from interoperability import baseline, oracle
from interoperability.wire_projection import ProjectionError, project_trace


ROOT = Path(__file__).resolve().parents[1]
CAPTURES = [
    "runs/wire-observation/amirk_a2a_to_mcp-2026-10-23T20-02-10-750Z-3828/runtime.json",
    "runs/wire-observation/mgcrea_mcp_a2a-2026-10-23T20-06-37-342Z-9536/runtime.json",
]
EXPECTED = "development-destination = Paris"


def captured(index):
    return json.loads((ROOT / CAPTURES[index]).read_text(encoding="utf-8"))


def replace_response(exchange, response):
    """Labelled derivative, never written back to actual wire evidence."""
    raw = json.dumps(response, ensure_ascii=False, separators=(",", ":"))
    exchange["response"].update(raw=raw, json=response, sha256=hashlib.sha256(raw.encode()).hexdigest())


class WireProjection(unittest.TestCase):
    def test_real_captures_have_only_observed_edges_and_incomplete_evidence(self):
        for i in range(2):
            trace = captured(i)
            projection = project_trace(trace, EXPECTED)
            model = projection["manifest"]
            self.assertFalse(model["evidence"]["complete"])
            self.assertEqual(model["evidence"]["observed_at"], model["evidence"]["valid_until"])
            self.assertEqual(model["horizon"], len(projection["events"]) - 1)
            self.assertEqual(len(model["transitions"]), model["horizon"])
            result = baseline.evaluate(model, projection["analysis_clock"])
            self.assertEqual(result["decision"], "supported")
            self.assertEqual(oracle.evaluate(model, projection["analysis_clock"])["decision"], "supported")
            self.assertTrue(oracle.check_certificate(model, result, projection["analysis_clock"]))
            self.assertEqual(baseline.evaluate(model, projection["analysis_clock"] + 1)["decision"], "unknown")

    def test_modern_answer_ack_does_not_invent_completed(self):
        projection = project_trace(captured(0), EXPECTED)
        answer = next(x for x in projection["events"] if x["operation"] == "tasks/update")
        self.assertNotIn("status", answer["observable_fields"])
        self.assertNotIn("artifact_contains_expected", answer["observable_fields"])

    def test_nested_completed_result_is_actual_public_evidence(self):
        projection = project_trace(captured(0), EXPECTED)
        completed = next(x for x in projection["events"] if x["operation"] == "tasks/get" and x["observable_fields"].get("status") == "completed")
        self.assertTrue(completed["observable_fields"]["artifact_contains_expected"])
        self.assertIn("returned_context_reference", completed["observable_fields"])

    def test_mirror_ack_and_history_do_not_become_completed_artifact(self):
        projection = project_trace(captured(1), EXPECTED)
        acknowledgements = [x for x in projection["events"] if x["evidence_source"] == "send-acknowledgement"]
        self.assertEqual(acknowledgements[-1]["observable_fields"]["status"], "input_required")
        mirrors = [x for x in projection["events"] if x["evidence_source"] == "local-mirror"]
        waiting = next(x for x in mirrors if x["observable_fields"].get("status") == "input_required")
        self.assertFalse(waiting["observable_fields"]["artifact_contains_expected"])

    def test_partial_capture_cannot_prove_unsupported(self):
        trace = captured(1)
        trace["exchanges"] = [x for x in trace["exchanges"] if x["exchange_id"] not in ("mcp-8", "mcp-9")]
        trace["provenance"]["controlled_derivative"] = "Remove observed completed continuation"
        projection = project_trace(trace, EXPECTED)
        self.assertEqual(baseline.evaluate(projection["manifest"], projection["analysis_clock"])["decision"], "unknown")

    def test_unmet_text_goal_is_unknown_in_partial_graph(self):
        projection = project_trace(captured(1), "not delivered in the fixture")
        self.assertEqual(baseline.evaluate(projection["manifest"], projection["analysis_clock"])["decision"], "unknown")

    def test_wrong_request_response_pair_is_rejected_even_with_valid_hash(self):
        trace = captured(1)
        x = trace["exchanges"][-1]
        response = copy.deepcopy(x["response"]["json"])
        response["id"] = 999
        replace_response(x, response)
        with self.assertRaisesRegex(ProjectionError, "correlation"):
            project_trace(trace, EXPECTED)

    def test_raw_declared_and_hash_corruption_are_rejected(self):
        trace = captured(1)
        trace["exchanges"][-1]["response"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ProjectionError, "SHA-256"):
            project_trace(trace, EXPECTED)
        trace = captured(1)
        trace["exchanges"][-1]["response"]["json"]["id"] = 999
        with self.assertRaisesRegex(ProjectionError, "disagree"):
            project_trace(trace, EXPECTED)

    def test_cross_run_and_duplicate_ids_are_rejected(self):
        trace = captured(1)
        trace["exchanges"][-1]["run_id"] = "unrelated execution"
        with self.assertRaisesRegex(ProjectionError, "Cross-run"):
            project_trace(trace, EXPECTED)
        trace = captured(1)
        trace["exchanges"][-1]["exchange_id"] = trace["exchanges"][0]["exchange_id"]
        with self.assertRaisesRegex(ProjectionError, "duplicate exchange"):
            project_trace(trace, EXPECTED)

    def test_foreign_returned_context_remains_foreign(self):
        trace = captured(1)
        for x in trace["exchanges"]:
            if x["exchange_id"] not in ("mcp-8", "mcp-9"):
                continue
            response = copy.deepcopy(x["response"]["json"])
            body = json.loads(response["result"]["content"][0]["text"])
            body["context_id"] = "foreign-context"
            response["result"]["content"][0]["text"] = json.dumps(body)
            replace_response(x, response)
        projection = project_trace(trace, EXPECTED)
        self.assertEqual(list(projection["manifest"]["states"].values())[-1]["returned_context_reference"], "foreign-context")
        self.assertEqual(baseline.evaluate(projection["manifest"], projection["analysis_clock"])["decision"], "unknown")

    def test_history_cannot_substitute_for_artifact_body(self):
        trace = captured(1)
        for x in trace["exchanges"]:
            if x["exchange_id"] not in ("mcp-8", "mcp-9"):
                continue
            response = copy.deepcopy(x["response"]["json"])
            body = json.loads(response["result"]["content"][0]["text"])
            body["artifacts"] = []
            body["history"].append({"text": EXPECTED, "role": "agent"})
            response["result"]["content"][0]["text"] = json.dumps(body)
            replace_response(x, response)
        projection = project_trace(trace, EXPECTED)
        self.assertEqual(baseline.evaluate(projection["manifest"], projection["analysis_clock"])["decision"], "unknown")

    def test_contradictory_nested_task_binding_is_rejected(self):
        trace = captured(0)
        x = next(x for x in trace["exchanges"] if x["exchange_id"] == "mcp-8")
        response = copy.deepcopy(x["response"]["json"])
        response["result"]["result"]["structuredContent"]["taskHandle"] = "tk_foreign"
        replace_response(x, response)
        with self.assertRaisesRegex(ProjectionError, "Contradictory"):
            project_trace(trace, EXPECTED)

    def test_missing_artifact_body_stays_unknown(self):
        trace = captured(0)
        for x in trace["exchanges"]:
            if x["exchange_id"] not in ("mcp-8", "mcp-9"):
                continue
            response = copy.deepcopy(x["response"]["json"])
            payload = response["result"]["result"] if x["exchange_id"] == "mcp-8" else response["result"]
            payload["content"] = []
            replace_response(x, response)
        projection = project_trace(trace, EXPECTED)
        self.assertNotIn("artifact_contains_expected", projection["events"][-1]["observable_fields"])
        self.assertEqual(baseline.evaluate(projection["manifest"], projection["analysis_clock"])["decision"], "unknown")

    def test_delivery_complete_without_task_result_is_not_logical_success(self):
        trace = captured(0)
        trace["exchanges"] = [x for x in trace["exchanges"] if x["exchange_id"] != "mcp-9"]
        x = next(x for x in trace["exchanges"] if x["exchange_id"] == "mcp-8")
        response = copy.deepcopy(x["response"]["json"])
        del response["result"]["result"]
        replace_response(x, response)
        projection = project_trace(trace, EXPECTED)
        self.assertNotIn("status", projection["events"][-1]["observable_fields"])
        self.assertEqual(baseline.evaluate(projection["manifest"], projection["analysis_clock"])["decision"], "unknown")

    def test_delivered_error_is_not_a_lifecycle_contradiction_or_success(self):
        trace = captured(0)
        x = next(x for x in trace["exchanges"] if x["exchange_id"] == "mcp-8")
        response = copy.deepcopy(x["response"]["json"])
        response["result"]["result"]["isError"] = True
        response["result"]["result"]["structuredContent"]["status"] = "failed"
        replace_response(x, response)
        with self.assertRaisesRegex(ProjectionError, "delivery completion is not task success"):
            project_trace(trace, EXPECTED)

    def test_cancel_action_cannot_be_silently_removed_from_observed_horizon(self):
        trace = captured(1)
        x = next(x for x in trace["exchanges"] if x["exchange_id"] == "mcp-6")
        request = copy.deepcopy(x["request"]["json"])
        request["params"]["name"] = "a2a_cancel_task"
        raw = json.dumps(request, separators=(",", ":"))
        x["request"].update(raw=raw, json=request, sha256=hashlib.sha256(raw.encode()).hexdigest())
        with self.assertRaisesRegex(ProjectionError, "Cancellation needs"):
            project_trace(trace, EXPECTED)

    def test_exact_a2a_state_cannot_contradict_ordinary_success_label(self):
        trace = captured(0)
        x = next(x for x in trace["exchanges"] if x["exchange_id"] == "mcp-8")
        response = copy.deepcopy(x["response"]["json"])
        response["result"]["result"]["structuredContent"]["a2aState"] = "TASK_STATE_FAILED"
        replace_response(x, response)
        with self.assertRaisesRegex(ProjectionError, "pinned status mapping"):
            project_trace(trace, EXPECTED)


if __name__ == "__main__":
    unittest.main()
