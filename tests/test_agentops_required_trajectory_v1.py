"""Source conformance and all-case tests; no native/SDK/model execution."""
import ast
from collections.abc import Mapping
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from interoperability import agentops_required_trajectory_v1 as metric


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "external/agentops-c806b7f1/agents/python/evals/required_trajectory.py"
EXPECTED = ROOT / "runs/upstream-agentops-cases/v1/evaluator/expectations.json"


def source_functions():
    # Execute only the two named pure function definitions. No original module
    # imports, evaluator adapters, SDK, app, tool functions or model is run.
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                and node.name in {"contains_required", "required_tools_in_order"}]
    if {node.name for node in selected} != {"contains_required", "required_tools_in_order"}:
        raise AssertionError("Original pure matcher definitions are not unique")
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    namespace = {"Mapping": Mapping}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[future, *selected], type_ignores=[])), str(SOURCE), "exec"), namespace)
    return namespace


class RequiredTrajectoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = source_functions()
        cls.cases = json.loads(EXPECTED.read_text(encoding="utf-8"))["cases"]

    def original_order(self, actual, expected):
        actual_objects = [SimpleNamespace(name=item["name"], args=item.get("args")) for item in actual]
        expected_objects = [SimpleNamespace(name=item["name"], args=item.get("args")) for item in expected]
        return self.original["required_tools_in_order"](actual_objects, expected_objects)

    def test_scalar_and_nested_subset_conforms_to_original_source(self):
        values = [None, False, True, 0, 1, 1.0, 2, "", "x", [], [1], [True], {}, {"x": ""}, {"x": 1},
                  {"x": {"a": 2}}, {"x": [1, {"a": "b"}]}, {"x": [1, {"a": "b", "optional": 3}], "extra": 0}]
        for actual in values:
            for required in values:
                with self.subTest(actual=actual, required=required):
                    self.assertEqual(metric.contains_required(actual, required), self.original["contains_required"](actual, required))

    def test_boolean_numeric_type_boundary(self):
        self.assertFalse(metric.contains_required(True, 1))
        self.assertFalse(metric.contains_required(0, False))
        self.assertTrue(metric.contains_required(1.0, 1))

    def test_missing_empty_argument_default_matches_only_empty(self):
        self.assertTrue(metric.contains_required({"service": "inventory"}, {"service": "inventory", "query": ""}))
        self.assertFalse(metric.contains_required({"service": "inventory", "query": "error"}, {"service": "inventory", "query": ""}))
        self.assertFalse(metric.contains_required({}, {"query": None}))

    def test_lists_are_equal_length_with_recursive_required_subsets(self):
        self.assertTrue(metric.contains_required([{"x": 1, "extra": 2}], [{"x": 1}]))
        self.assertFalse(metric.contains_required([1, 2], [1]))

    def test_original_subsequence_conformance_with_extras_and_duplicates(self):
        variants = [[], [{"name": "a", "args": {}}], [{"name": "b", "args": {}}],
                    [{"name": "a", "args": {"x": 1}}, {"name": "b", "args": None}],
                    [{"name": "a", "args": {}}, {"name": "a", "args": {"x": 1}}, {"name": "b", "args": {}}],
                    [{"name": "b", "args": {}}, {"name": "a", "args": {"x": 1}}]]
        for actual in variants:
            for required in variants:
                self.assertEqual(metric.required_tools_in_order(actual, required)["matches"], self.original_order(actual, required))

    def test_all_21_original_cases_and_22_turns_preserve_metric_semantics(self):
        self.assertEqual(len(self.cases), 21)
        self.assertEqual(sum(len(case["conversation"]) for case in self.cases), 22)
        for case in self.cases:
            observed = []
            for turn in case["conversation"]:
                required = deepcopy(turn["intermediate_data"]["tool_uses"])
                for call in required:
                    call.setdefault("args", {})["optional_test_argument"] = "extra"
                observed.append({"invocation_id": "native-" + turn["invocation_id"], "intermediate_data": {"tool_uses": [
                    {"name": "additional_read", "args": {}}, *required]}})
            result = metric.score_invocations(observed, case["conversation"])
            self.assertEqual(result["overall_score"], 1.0, case["eval_id"])
            self.assertFalse(result["native_source_case_qualification"])
            self.assertFalse(result["full_task_grade_assigned"])
            for actual, expected in zip(observed, case["conversation"]):
                self.assertTrue(self.original_order(actual["intermediate_data"]["tool_uses"], expected["intermediate_data"]["tool_uses"]))

    def test_each_source_case_missing_required_call_fails_metric(self):
        for case in self.cases:
            observed = deepcopy(case["conversation"])
            observed[0]["intermediate_data"]["tool_uses"] = observed[0]["intermediate_data"]["tool_uses"][1:]
            result = metric.score_invocations(observed, case["conversation"])
            self.assertEqual(result["overall_eval_status"], "failed", case["eval_id"])

    def test_answer_reference_does_not_make_the_metric_pass(self):
        reference = deepcopy(self.cases[0]["conversation"])
        actual = deepcopy(reference)
        actual[0]["intermediate_data"]["tool_uses"] = []
        self.assertEqual(metric.score_invocations(actual, reference)["overall_score"], 0.0)
        actual[0]["intermediate_data"] = deepcopy(reference[0]["intermediate_data"])
        actual[0]["final_response"] = {"parts": [{"text": "Wrong answer with correct calls."}]}
        result = metric.score_invocations(actual, reference)
        self.assertEqual(result["overall_score"], 1.0)
        self.assertFalse(result["answer_grounding_assessed"])

    def test_same_event_batch_and_partial_duplicates_are_not_causal_checks(self):
        events = [{"invocation_id": "i", "author": "agent", "partial": True, "content": {"parts": [
            {"function_call": {"id": "call-a", "name": "a", "args": {}}},
            {"function_call": {"id": "call-b", "name": "b", "args": {}}}]}},
            {"invocation_id": "i", "author": "agent", "content": {"parts": [
                {"function_call": {"id": "call-a", "name": "a", "args": {}}}]}}]
        actual = metric.invocations_from_events(events)
        calls = metric.get_all_tool_calls(actual[0]["intermediate_data"])
        self.assertEqual([call["name"] for call in calls], ["a", "b", "a"])
        expected = [{"intermediate_data": {"tool_uses": [{"name": "a", "args": {}}, {"name": "b", "args": {}}]}}]
        result = metric.score_invocations(actual, expected)
        self.assertEqual(result["overall_score"], 1.0)
        self.assertTrue(result["batch_array_order_can_satisfy_metric"])
        self.assertFalse(result["awaited_dependencies_proven"])

    def test_invocation_order_is_first_seen_not_uuid_or_timestamp_sort(self):
        events = [{"invocation_id": "z", "author": "user", "timestamp": 200, "content": {"parts": [{"text": "turn one"}]}},
                  {"invocation_id": "z", "author": "agent", "timestamp": 200, "content": {"parts": [{"function_call": {"name": "a", "args": {}}}]}},
                  {"invocation_id": "a", "author": "agent", "timestamp": 100, "content": {"parts": [{"function_call": {"name": "b", "args": {}}}]}}]
        output = metric.invocations_from_events(events)
        self.assertEqual([item["invocation_id"] for item in output], ["z", "a"])
        self.assertEqual([len(metric.get_all_tool_calls(item["intermediate_data"])) for item in output], [1, 1])

    def test_function_response_ids_never_substitute_for_required_calls(self):
        actual = [{"intermediate_data": {"invocation_events": [{"content": {"parts": [{"function_response": {"name": "a", "response": {"ok": True}}}]}}]}}]
        expected = [{"intermediate_data": {"tool_uses": [{"name": "a", "args": {}}]}}]
        self.assertEqual(metric.score_invocations(actual, expected)["overall_score"], 0.0)

    def test_invocation_count_mismatch_is_rejected_not_averaged_away(self):
        with self.assertRaises(ValueError):
            metric.score_invocations([], self.cases[-1]["conversation"])

    def test_empty_invocations_preserve_unassigned_original_result(self):
        result = metric.score_invocations([], [])
        self.assertIsNone(result["overall_score"])
        self.assertIsNone(result["overall_eval_status"])

    def test_input_objects_remain_unchanged(self):
        original = deepcopy(self.cases[-1]["conversation"])
        before = json.dumps(original, sort_keys=True)
        metric.score_invocations(original, original)
        self.assertEqual(json.dumps(original, sort_keys=True), before)

    def test_selected_indices_and_first_missing_are_explicit(self):
        result = metric.required_tools_in_order([{"name": "extra"}, {"name": "a"}], [{"name": "a"}, {"name": "b"}])
        self.assertEqual(result, {"matches": False, "matched_actual_indices": [1], "first_unmatched_required_index": 1})

    def test_unsupported_representations_and_nonfinite_numbers_rejected(self):
        for value in ({"tool_uses": [], "invocation_events": []}, {"tool_uses": "invalid"},
                      {"invocation_events": [{"content": {"parts": [{"functionCall": {"name": "a"}}]}}]}):
            with self.assertRaises(ValueError):
                metric.get_all_tool_calls(value)
        with self.assertRaises(ValueError):
            metric.required_tools_in_order([{"name": "a", "args": {"x": float("inf")}}], [])


if __name__ == "__main__":
    unittest.main()
