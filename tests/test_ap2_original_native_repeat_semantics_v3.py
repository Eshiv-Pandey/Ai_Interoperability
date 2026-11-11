"""Constructed controls for retained V3 failure and absence interpretation."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import analyze_ap2_original_native_repeat_v3 as analyzer


def early_case():
    return {"caller_error": {"message": "503 UNAVAILABLE: high demand; state=<TaskState.failed: 'failed'>"},
            "actor_result_present": True, "original_call_started_count": 1, "original_call_terminal_count": 1,
            "original_call_phases": ["catalog"], "original_call_return_count": 0,
            "original_call_errors": [{"phase": "catalog", "error_type": "RuntimeError"}],
            "initial_task": None, "final_task": None, "repeat_task": None, "repeat_event": None,
            "otp_request": None, "explicit_human_reply": None, "public_tasks": []}


def failed_provider():
    return [{"http_status": 503, "error": {"code": 503, "status": "UNAVAILABLE", "message": "high demand"},
             "reported_total_tokens": None}]


class RepeatSemanticControls(unittest.TestCase):
    def test_external_error_propagation_is_distinct_from_task_read(self):
        observed = analyzer.failure_observation(early_case(), failed_provider())
        self.assertEqual(observed["failure_disposition"], "received_provider_error_propagated_before_payment_prerequisite")
        self.assertTrue(observed["original_failed_task_repr_embedded_in_error"])
        self.assertTrue(observed["public_error_text_is_not_a_tasks_get_observation"])

    def test_unrelated_provider_error_is_not_assigned_to_original_error(self):
        provider = failed_provider()
        provider[0]["error"]["message"] = "independent transport failure"
        observed = analyzer.failure_observation(early_case(), provider)
        self.assertFalse(observed["provider_error_embedded_in_original_tool_error"])
        self.assertEqual(observed["failure_disposition"], "original_catalog_error_before_payment_prerequisite")

    def test_missing_actor_or_unfinished_call_cannot_prove_absence(self):
        for field, value in (("actor_result_present", False), ("original_call_terminal_count", 0)):
            case = early_case()
            case[field] = value
            observed = analyzer.failure_observation(case, failed_provider())
            self.assertFalse(observed["no_payment_prerequisite_or_repeat_observed"])
            self.assertIsNone(observed["failure_disposition"])

    def test_actual_repeat_capture_prevents_early_failure_disposition(self):
        case = early_case()
        case["repeat_event"] = {"kind": "public-repeat-observation"}
        observed = analyzer.failure_observation(case, failed_provider())
        self.assertFalse(observed["no_payment_prerequisite_or_repeat_observed"])
        self.assertIsNone(observed["failure_disposition"])

    def test_retained_actor_read_mismatch_is_not_hidden(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            analysis = analyzer.public.Analysis(root)
            folder = analysis.capture / "execution/cases" / analyzer.CASE_ID
            (folder / "caller").mkdir(parents=True)
            actor = {"schema_version": "ap2-owned-public-scripted-continuation/2", "case_id": analyzer.CASE_ID,
                     "public_human_facts": analyzer.facts(), "grade": None, "evaluator_or_private_journal_inputs": [],
                     "original_business_calls": [], "actor_public_events": [], "public_task_reads": [{"phase": "forged"}],
                     "public_pending_task": None, "public_final_task": None}
            raw = json.dumps(actor).encode()
            (folder / "caller/result.json").write_bytes(raw)
            (folder / "caller/actor-public-events.jsonl").write_bytes(b"")
            analysis.members = {"execution/cases/" + analyzer.CASE_ID + "/caller/result.json": analyzer.public.digest(raw),
                                "execution/cases/" + analyzer.CASE_ID + "/caller/actor-public-events.jsonl": analyzer.public.digest(b"")}
            analysis.case(analyzer.facts(), {"status": "executed_returned"})
            self.assertTrue(any("actor_reads_differ_from_raw_read_terminals" in reason for reason in analysis.issues))


if __name__ == "__main__":
    unittest.main()
