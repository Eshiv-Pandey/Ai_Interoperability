"""Focused synthetic regressions for partial stronger observations.

Reuses frozen v1 fixture builders once; its test suite is not executed.
No SDK, original application, service, model or credential is accessed.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from interoperability.agentops_reply_dependencies_v1 import assess_reply_dependencies as assess_v1
from interoperability.agentops_reply_dependencies_v2 import assess_reply_dependencies as assess_v2
from interoperability.agentops_required_trajectory_v1 import invocations_from_events, score_invocations

FROZEN_V1 = ROOT / "src/interoperability/agentops_reply_dependencies_v1.py"
FROZEN_FIXTURE = ROOT / "tests/test_agentops_reply_dependencies_v1.py"
FROZEN_HASHES = {
    FROZEN_V1: "ae70b1a5dd901d3e1b298e30258fd7b12f51cc3f461a3be5880da9c26eb102e3",
    FROZEN_FIXTURE: "62ceb590bdc212fa826656dc93d31b9fd3ed358d0bcec34379a357c0b497bd68",
}


class PartialObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for path, expected in FROZEN_HASHES.items():
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError("Frozen v1 source or fixture differs")
        cls.fixture = types.ModuleType("frozen_reply_v1_fixture_builders")
        cls.fixture.__file__ = str(FROZEN_FIXTURE)
        exec(compile(FROZEN_FIXTURE.read_bytes(), str(FROZEN_FIXTURE), "exec"), cls.fixture.__dict__)
        manifest = json.loads((ROOT / "docs/research/upstream-agentops-grading-obligations-v1.json").read_bytes())
        cls.obligations = manifest["case_obligations"]
        cls.by_name = {item["eval_id"]: item for item in cls.obligations}

    @classmethod
    def tearDownClass(cls):
        for path, expected in FROZEN_HASHES.items():
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError("Frozen v1 source or fixture changed")

    def build(self, name="inventory-status"):
        self.obligation = deepcopy(self.by_name[name])
        self.journal = self.fixture.synthetic_journal(self.obligation)
        self.events = self.journal["calls"][0]["events"]

    def assess(self, function):
        self.fixture.rebuild(self.journal)
        return function(self.journal, self.obligation,
                        expected_native_user_id=self.fixture.USER,
                        expected_native_session_id=self.fixture.SESSION)

    def test_sole_partial_call_cannot_supply_success_even_if_original_metric_passes(self):
        self.build()
        self.events[0]["partial"] = True
        self.assertEqual(self.assess(assess_v1)["reply_consistency_status"], "supported")
        result = self.assess(assess_v2)
        self.assertEqual(result["reply_consistency_status"], "unknown")
        self.assertTrue(result["turns"][0]["tool_calls"][0]["partial"])
        expected = [{"intermediate_data": {"tool_uses": self.obligation["turns"][0]["original_metric"]["expected_calls"]}}]
        metric = score_invocations(invocations_from_events(self.journal["ordered_events"]), expected)
        self.assertEqual(metric["overall_score"], 1.0)
        self.assertFalse(result["original_configured_metric_modified"])

    def test_sole_partial_success_reply_retains_shape_without_stronger_support(self):
        self.build()
        self.events[1]["partial"] = True
        self.assertEqual(self.assess(assess_v1)["reply_consistency_status"], "supported")
        result = self.assess(assess_v2)
        self.assertEqual(result["reply_consistency_status"], "unknown")
        self.assertEqual(result["turns"][0]["tool_replies"][0]["source_contract_classification"], "success_reply")
        self.assertTrue(result["turns"][0]["tool_replies"][0]["partial"])

    def test_partial_expected_missing_error_is_not_complete_resource_observation(self):
        obligation = next(item for item in self.obligations
                          if item["turns"][0]["original_metric"]["required_trajectory"][0]["reply_extra_assessment"]["classification"]
                          == "expected_missing_service_error")
        self.build(obligation["eval_id"])
        self.events[1]["partial"] = True
        self.assertEqual(self.assess(assess_v1)["reply_consistency_status"], "supported")
        self.assertEqual(self.assess(assess_v2)["reply_consistency_status"], "unknown")

    def test_partial_error_does_not_assign_terminal_reply_contradiction(self):
        self.build()
        self.events[1]["partial"] = True
        self.events[1]["content"]["parts"][0]["function_response"]["response"] = {"error": "SYNTHETIC incomplete error"}
        self.assertEqual(self.assess(assess_v1)["reply_consistency_status"], "inconsistent")
        self.assertEqual(self.assess(assess_v2)["reply_consistency_status"], "unknown")

    def test_partial_consumer_cannot_support_dependency_from_complete_earlier_reply(self):
        self.build("recommend-fix")
        self.events[2]["partial"] = True
        self.assertEqual(self.assess(assess_v1)["turns"][0]["dependency_assessments"][0]["status"], "supported")
        result = self.assess(assess_v2)
        self.assertEqual(result["turns"][0]["dependency_assessments"][0]["status"], "unknown")
        self.assertEqual(result["turns"][0]["required_reply_assessments"][0]["status"], "supported")

    def test_partial_producer_reply_cannot_support_complete_later_dependency(self):
        self.build("recommend-fix")
        self.events[1]["partial"] = True
        self.assertEqual(self.assess(assess_v1)["dependency_consistency_status"], "supported")
        self.assertEqual(self.assess(assess_v2)["dependency_consistency_status"], "unknown")

    def test_partial_diagnostic_call_cannot_supply_argument_consistency(self):
        self.build("recommend-fix")
        self.events[2]["partial"] = True
        self.assertEqual(self.assess(assess_v1)["argument_consistency_status"], "supported")
        self.assertEqual(self.assess(assess_v2)["argument_consistency_status"], "unknown")

    def test_partial_unfiltered_reply_cannot_justify_later_filtered_call(self):
        self.build("recommend-fix")
        self.events[3]["partial"] = True
        args = {"service": self.events[2]["content"]["parts"][0]["function_call"]["args"]["service"], "query": "error"}
        identifier = "SYNTHETIC-SUPPLEMENTAL-FILTER"
        self.events.extend([
            self.fixture.call_event("search_service_logs", args, identifier),
            self.fixture.reply_event("search_service_logs", self.fixture.payload("search_service_logs", args), identifier),
        ])
        self.assertEqual(self.assess(assess_v1)["argument_consistency_status"], "supported")
        self.assertEqual(self.assess(assess_v2)["argument_consistency_status"], "unknown")

    def test_partial_then_complete_same_id_remains_retained_ambiguous(self):
        self.build()
        partial = deepcopy(self.events[0])
        partial.pop("id")
        partial["partial"] = True
        self.events.insert(0, partial)
        result = self.assess(assess_v2)
        self.assertEqual(result["reply_consistency_status"], "unknown")
        self.assertEqual(len(result["turns"][0]["tool_calls"]), 2)
        self.assertEqual(result["turns"][0]["tool_replies"][0]["candidate_call_observation_indices"], [0, 1])
        self.assertFalse(result["partial_calls_deduplicated"])

    def test_false_null_and_unset_partial_flags_allow_complete_observations(self):
        for flag in (False, None, "unset"):
            with self.subTest(flag=flag):
                self.build()
                for event in self.events:
                    if flag == "unset": event.pop("partial")
                    else: event["partial"] = flag
                self.assertEqual(self.assess(assess_v2)["reply_consistency_status"], "supported")

    def test_complete_preexisting_all_case_fixtures_have_unchanged_lane_results(self):
        self.assertEqual(len(self.obligations), 21)
        self.assertEqual(sum(item["turn_count"] for item in self.obligations), 22)
        for obligation in self.obligations:
            with self.subTest(case=obligation["eval_id"]):
                self.build(obligation["eval_id"])
                before = self.assess(assess_v1)
                after = self.assess(assess_v2)
                self.assertEqual(after.pop("frozen_v1_source_sha256"), FROZEN_HASHES[FROZEN_V1])
                self.assertFalse(after.pop("partial_observations_can_supply_stronger_support"))
                self.assertEqual(after.pop("schema_version"), "agentops-reply-dependencies/2")
                before.pop("schema_version")
                self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
