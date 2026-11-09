"""Focused synthetic integration checks; no old suite or native execution."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from interoperability.agentops_source_case_assessment_v2 import assess_source_case as assess_v2
from interoperability.agentops_source_case_assessment_v3 import assess_source_case as assess_v3
from interoperability.agentops_answer_schema_v1 import SOURCE_BINDINGS


class CompleteLaneIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "tests/test_agentops_source_case_assessment_v2.py"
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != "ab85c95a06df6fcc266a8fa6f92db7ec45c510a660e33501ecde83779c061202":
            raise ValueError("Frozen integrated fixture differs")
        cls.fixture = types.ModuleType("frozen_v2_integrated_fixture_builders")
        cls.fixture.__file__ = str(path)
        exec(compile(raw, str(path), "exec"), cls.fixture.__dict__)
        cls.apps = json.loads((ROOT / "runs/upstream-agentops-cases/v1/application/cases.json").read_bytes())["cases"]
        cls.refs = json.loads((ROOT / "runs/upstream-agentops-cases/v1/evaluator/expectations.json").read_bytes())["cases"]
        cls.obligations = json.loads((ROOT / "docs/research/upstream-agentops-grading-obligations-v1.json").read_bytes())["case_obligations"]

    def build(self):
        app, ref, obligation = deepcopy(self.apps[0]), deepcopy(self.refs[0]), deepcopy(self.obligations[0])
        report = self.fixture.synthetic_report(app, ref)
        call = report["calls"][0]
        event = call["events"][0]
        event["partial"] = False
        event["content"]["parts"][0]["function_call"]["id"] = "SYNTHETIC-inventory-call"
        call["events"].insert(1, {
            "id": "SYNTHETIC-inventory-reply", "invocation_id": event["invocation_id"], "author": event["author"],
            "content": {"role": "model", "parts": [{"function_response": {
                "id": "SYNTHETIC-inventory-call", "name": "get_service_status", "response": {
                    "service": {"name": "inventory", "description": "SYNTHETIC service", "status": "down", "owner": "SYNTHETIC team"},
                    "open_incidents": []}}}]},
        })
        self.values = [report, app, ref, obligation, self.fixture.context_boundaries(obligation)]
        self.events = call["events"]
        self.fixture.rebuild_events(report)

    def assess(self, function, **optional):
        self.fixture.rebuild_events(self.values[0])
        return function(*self.values, expected_native_user_id=self.fixture.USER,
                        expected_native_session_id=self.fixture.SESSION, **optional)

    def bindings(self):
        for event in self.events:
            event["author"] = "agentops_agent"
            event["node_info"] = {"path": ""}
        return {"schema_version": "agentops-answer-extraction-bindings/1", "family": "core",
                "selection_profile": "complete_model_text_after_node_tools_v1", "source_bindings": deepcopy(SOURCE_BINDINGS),
                "turns": [{"turn_index": 1, "native_invocation_id": self.events[0]["invocation_id"],
                           "source_invocation_label": self.values[1]["conversation"][0]["invocation_id"],
                           "nodes": {"answer": {"author": "agentops_agent", "node_path": "", "branch": None}}}]}

    def assert_unaffected(self, before, after):
        for field in ("configured_metric", "sampled_effects", "memory_reply_profile_selection", "answer_schema",
                      "native_invocation_ids", "journal_receipt_identity"):
            self.assertEqual(after[field], before[field])
        for field in ("aggregate_task_pass_assigned", "benchmark_grade_proven", "native_qualification_established",
                      "native_source_case_qualification", "full_task_grade_assigned", "state_effects_proven"):
            self.assertFalse(after[field])

    def test_complete_inventory_preserves_delegated_metric_state_memory_and_pending_answer(self):
        self.build()
        before = self.assess(assess_v2)
        supplied = deepcopy(self.values)
        after = self.assess(assess_v3)
        self.assert_unaffected(before, after)
        self.assertEqual(after["separate_assessments"], before["separate_assessments"])
        self.assertEqual(self.values, supplied)
        self.assertFalse(after["supplied_bindings_withheld_due_to_partial"])

    def test_partial_call_and_reply_correct_only_stronger_lanes_without_changing_metric(self):
        for ordinal in (0, 1):
            with self.subTest(ordinal=ordinal):
                self.build()
                self.events[ordinal]["partial"] = True
                before = self.assess(assess_v2)
                self.assertEqual(before["separate_assessments"]["response"]["status"], "supported")
                after = self.assess(assess_v3)
                self.assert_unaffected(before, after)
                self.assertEqual(after["separate_assessments"]["response"]["status"], "unknown")
                self.assertEqual(after["configured_metric"]["overall_eval_status"], "passed")
                self.assertEqual(len(after["partial_tool_observation_refs"]), 1)

    def test_optional_extraction_abstains_on_partial_instead_of_preserving_old_direct_reader(self):
        self.build()
        bindings = self.bindings()
        self.events[1]["partial"] = True
        before = self.assess(assess_v2)
        after = self.assess(assess_v3, source_extraction_bindings=bindings)
        self.assert_unaffected(before, after)
        self.assertTrue(after["supplied_bindings_withheld_due_to_partial"])
        self.assertIn("frozen answer reader", after["source_extraction_not_assessed_reason"])
        self.assertEqual(after["separate_assessments"]["answer"]["status"], "pending")
        self.assertEqual(after["separate_assessments"]["schema"]["status"], "pending")

    def test_complete_optional_extraction_preserves_observed_answer_and_pending_semantics(self):
        self.build()
        bindings = self.bindings()
        before = self.assess(assess_v2, source_extraction_bindings=bindings)
        after = self.assess(assess_v3, source_extraction_bindings=bindings)
        self.assert_unaffected(before, after)
        self.assertEqual(after["answer_schema"]["turns"][0]["answer_extraction"]["answer"]["status"], "observed")
        self.assertEqual(after["answer_schema"]["turns"][0]["semantic_manual_assessment"]["status"], "pending")
        self.assertFalse(after["supplied_bindings_withheld_due_to_partial"])

    def test_projection_and_native_context_rejections_are_preserved(self):
        self.build()
        self.values[3]["turns"][0]["original_metric"]["expected_calls"][0]["args"]["name"] = "SYNTHETIC-other"
        with self.assertRaises(ValueError): self.assess(assess_v3)
        self.build()
        self.values[4]["turns"][0]["native_session_id"] = "SYNTHETIC-foreign"
        with self.assertRaises(ValueError): self.assess(assess_v3)


if __name__ == "__main__":
    unittest.main()
