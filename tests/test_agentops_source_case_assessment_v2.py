"""SYNTHETIC integration of independent source-case observation lanes only."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
from interoperability.agentops_source_case_assessment_v2 import assess_source_case
from interoperability.agentops_answer_schema_v1 import SOURCE_BINDINGS
from test_agentops_source_case_assessment_v1 import USER, SESSION, synthetic_report, rebuild_events
from test_agentops_source_case_effects_v1 import boundaries, effects


def context_boundaries(obligation):
    result = boundaries(obligation)
    for turn in result["turns"]:
        turn["native_user_id"], turn["native_session_id"] = USER, SESSION
        for point in turn["samples"]:
            for row in point["memory"].get("notes", []): row["user_id"] = USER
    for row in result["retained_close"]["memory"].get("notes", []): row["user_id"] = USER
    return result


def memory_replies(report, expectation, boundary, changed_note=None, repeat_save=False):
    row = boundary["retained_close"]["memory"]["notes"][-1]
    note = {key: row[key] for key in ("ts", "incident_id", "note")}
    saved = deepcopy(note)
    if changed_note is not None: saved["note"] = changed_note
    for index, (call, reference) in enumerate(zip(report["calls"], expectation["conversation"]), 1):
        tool = deepcopy(reference["intermediate_data"]["tool_uses"][0]); tool["id"] = f"SYNTHETIC-tool-{index}"
        payload = {"saved": saved} if index == 1 else {"count": 1, "notes": [deepcopy(note)]}
        native = call["events"][0]["invocation_id"]
        def event(ordinal, part):
            return {"id": f"SYNTHETIC-memory-{index}-{ordinal}", "invocation_id": native, "author": "SYNTHETIC_AGENT",
                    "content": {"role": "model", "parts": [part]}}
        reply = {"function_response": {"id": tool["id"], "name": tool["name"], "response": payload}}
        call["events"] = [event(1, {"function_call": tool}), event(2, reply)]
        if repeat_save and index == 1: call["events"].append(event(3, deepcopy(reply)))
        call["events"].append(event(len(call["events"]) + 1, {"text": "SYNTHETIC observed answer."}))
    rebuild_events(report)


class IntegratedAssessmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.apps = json.loads((ROOT / "runs/upstream-agentops-cases/v1/application/cases.json").read_bytes())["cases"]
        cls.refs = json.loads((ROOT / "runs/upstream-agentops-cases/v1/evaluator/expectations.json").read_bytes())["cases"]
        cls.obligations = json.loads((ROOT / "docs/research/upstream-agentops-grading-obligations-v1.json").read_bytes())["case_obligations"]

    def fixture(self, index=0):
        app, ref, obligation = deepcopy(self.apps[index]), deepcopy(self.refs[index]), deepcopy(self.obligations[index])
        return synthetic_report(app, ref), app, ref, obligation, context_boundaries(obligation)

    def assess(self, values, **optional):
        return assess_source_case(*values, expected_native_user_id=USER, expected_native_session_id=SESSION, **optional)

    def memory_fixture(self):
        index = next(index for index, item in enumerate(self.obligations) if item["key"] == effects.MEMORY_KEY)
        return self.fixture(index)

    def test_all_21_cases_22_turns_preserve_metric_and_separate_missing_replies(self):
        self.assertEqual(len(self.apps), 21)
        self.assertEqual(sum(len(item["conversation"]) for item in self.apps), 22)
        for index in range(21):
            values = self.fixture(index); before = deepcopy(values)
            with self.subTest(case=values[1]["eval_id"]):
                result = self.assess(values)
                self.assertEqual(result["configured_metric"]["overall_score"], 1.0)
                self.assertEqual(result["reply_dependencies"]["reply_consistency_status"], "unknown")
                self.assertEqual(result["sampled_effects"]["business"]["status"], "consistent")
                self.assertEqual(result["sampled_effects"]["memory_structure"]["status"], "consistent")
                self.assertEqual(result["separate_assessments"]["answer"]["status"], "pending")
                self.assertEqual(values, before)
                for flag in ("aggregate_task_pass_assigned", "benchmark_grade_proven", "native_source_case_qualification",
                             "native_qualification_established", "full_task_grade_assigned", "state_effects_proven"):
                    self.assertIs(result[flag], False)

    def test_metric_pass_cannot_mask_required_tool_error_reply(self):
        values = self.fixture(); report = values[0]
        call = report["calls"][0]; event = call["events"][0]
        event["partial"] = False
        event["content"]["parts"][0]["function_call"]["id"] = "SYNTHETIC-error-tool"
        failure = {"id": "SYNTHETIC-error-reply", "invocation_id": event["invocation_id"], "author": "SYNTHETIC_AGENT",
                   "content": {"role": "model", "parts": [{"function_response": {"id": "SYNTHETIC-error-tool",
                       "name": "get_service_status", "response": {"error": "SYNTHETIC database failure"}}}]}}
        call["events"].insert(1, failure); rebuild_events(report)
        result = self.assess(values)
        self.assertEqual(result["configured_metric"]["overall_eval_status"], "passed")
        self.assertEqual(result["separate_assessments"]["response"]["status"], "inconsistent")
        self.assertFalse(result["aggregate_task_pass_assigned"])

    def test_obligation_expected_args_cannot_replace_original_reference(self):
        values = self.fixture(); obligation = values[3]
        obligation["turns"][0]["original_metric"]["expected_calls"][0]["args"]["name"] = "SYNTHETIC-other"
        with self.assertRaises(ValueError): self.assess(values)

    def test_required_reply_trajectory_must_match_original_expected_call(self):
        values = self.fixture()
        values[3]["turns"][0]["original_metric"]["required_trajectory"][0]["required_args"] = {}
        with self.assertRaises(ValueError): self.assess(values)

    def test_boolean_obligation_index_and_foreign_boundary_context_are_rejected(self):
        values = self.fixture(); values[3]["turns"][0]["turn_index"] = True
        with self.assertRaises(ValueError): self.assess(values)
        values = self.fixture(); values[4]["turns"][0]["native_session_id"] = "SYNTHETIC-foreign"
        with self.assertRaises(ValueError): self.assess(values)

    def test_missing_startup_remains_unknown_and_does_not_change_metric(self):
        values = self.fixture(); values[4].pop("startup")
        result = self.assess(values)
        self.assertEqual(result["sampled_effects"]["business"]["status"], "unknown")
        self.assertEqual(result["configured_metric"]["overall_score"], 1.0)

    def test_memory_unique_supported_replies_match_sampled_rows_without_sanitizer_credit(self):
        values = self.memory_fixture(); memory_replies(values[0], values[2], values[4])
        result = self.assess(values)
        self.assertEqual(result["memory_reply_profile_selection"]["status"], "selected_unique_supported_replies")
        self.assertEqual(result["sampled_effects"]["memory_save_reply"]["status"], "consistent")
        self.assertEqual(result["sampled_effects"]["memory_recall_reply"]["status"], "consistent")
        self.assertEqual(result["sampled_effects"]["sanitizer_fidelity"]["status"], "pending")
        self.assertEqual(len(result["memory_reply_profile_selection"]["reply_observation_refs"]), 2)

    def test_memory_changed_display_reply_is_inconsistent_without_changing_metric(self):
        values = self.memory_fixture(); memory_replies(values[0], values[2], values[4], changed_note="SYNTHETIC fabricated note")
        result = self.assess(values)
        self.assertEqual(result["sampled_effects"]["memory_save_reply"]["status"], "inconsistent")
        self.assertEqual(result["configured_metric"]["overall_eval_status"], "passed")

    def test_repeated_save_reply_is_retained_and_not_selected_as_unique(self):
        values = self.memory_fixture(); memory_replies(values[0], values[2], values[4], repeat_save=True)
        result = self.assess(values)
        self.assertEqual(result["memory_reply_profile_selection"]["status"], "unknown")
        self.assertEqual(len(result["reply_dependencies"]["turns"][0]["tool_replies"]), 2)
        self.assertEqual(result["sampled_effects"]["memory_save_reply"]["status"], "unknown")

    def test_partial_save_reply_is_not_used_as_complete_display_observation(self):
        values = self.memory_fixture(); memory_replies(values[0], values[2], values[4])
        values[0]["calls"][0]["events"][1]["partial"] = True; rebuild_events(values[0])
        result = self.assess(values)
        self.assertEqual(result["memory_reply_profile_selection"]["status"], "unknown")

    def test_partial_save_call_is_not_selected_as_a_complete_source_observation(self):
        values = self.memory_fixture(); memory_replies(values[0], values[2], values[4])
        values[0]["calls"][0]["events"][0]["partial"] = True; rebuild_events(values[0])
        result = self.assess(values)
        self.assertEqual(result["memory_reply_profile_selection"]["status"], "unknown")

    def test_original_sanitizer_fixture_only_applies_to_memory_case(self):
        with self.assertRaises(ValueError): self.assess(self.fixture(), original_sanitizer_fixture={})

    def test_explicit_extraction_profile_invokes_reviewed_optional_answer_api(self):
        values = self.fixture(); report = values[0]
        for event in report["calls"][0]["events"]:
            event["author"] = "agentops_agent"; event["node_info"] = {"path": ""}
        rebuild_events(report)
        bindings = {"schema_version": "agentops-answer-extraction-bindings/1", "family": "core",
                    "selection_profile": "complete_model_text_after_node_tools_v1", "source_bindings": deepcopy(SOURCE_BINDINGS),
                    "turns": [{"turn_index": 1, "native_invocation_id": report["calls"][0]["events"][0]["invocation_id"],
                               "source_invocation_label": values[1]["conversation"][0]["invocation_id"],
                               "nodes": {"answer": {"author": "agentops_agent", "node_path": "", "branch": None}}}]}
        result = self.assess(values, source_extraction_bindings=bindings)
        self.assertEqual(result["answer_schema"]["schema_version"], "agentops-answer-schema/1")
        self.assertEqual(result["answer_schema"]["turns"][0]["answer_extraction"]["answer"]["status"], "observed")
        self.assertEqual(result["answer_schema"]["turns"][0]["semantic_manual_assessment"]["status"], "pending")
        self.assertFalse(result["aggregate_task_pass_assigned"])


if __name__ == "__main__": unittest.main()
