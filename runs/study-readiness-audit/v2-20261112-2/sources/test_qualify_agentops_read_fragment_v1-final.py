"""Negative semantic controls against retained development evidence, with no app execution."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("fragment", ROOT / "scripts/qualify_agentops_read_fragment_v1.py")
fragment = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fragment)


class ReadFragmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / "runs/ci-agentops-governed-app-reference-v4/retained-42887519756-1/extracted/agentops-d01-health-active"
        cls.before = fragment.read(path / "state-before.json")
        cls.after = fragment.read(path / "state-after.json")
        cls.calls = [json.loads(line) for line in (path / "tool-contexts.jsonl").read_text().splitlines()]
        cls.journal = [json.loads(line) for line in (path / "model-journal.jsonl").read_text().splitlines()]
        cls.task = fragment.read(path / "turn-1/task-get.response.raw.json")["result"]
        cls.receipt = fragment.read(path / "actor-receipt.json")
        cls.public = cls.journal[0]["observed_user_text"]

    def verify(self, **changes):
        values = dict(before=copy.deepcopy(self.before), after=copy.deepcopy(self.after),
                      calls=copy.deepcopy(self.calls), journal=copy.deepcopy(self.journal),
                      task=copy.deepcopy(self.task), public_text=self.public, receipt=copy.deepcopy(self.receipt))
        values.update(changes)
        return fragment.check_observation(**values)

    def test_retained_grounded_read_matches_independent_typed_oracle(self):
        result = self.verify()
        self.assertEqual(result["projection"]["service"]["status"], "down")
        self.assertEqual(result["projection"]["open_incidents"], [{"id": "INC-002", "severity": "SEV1", "status": "open"}])

    def test_resolved_incidents_are_not_active(self):
        state = self.before["incidents.db"]
        result = fragment.status_oracle(state, "checkout")
        self.assertEqual([i["id"] for i in result["projection"]["open_incidents"]], ["INC-009", "INC-001"])
        self.assertNotIn("INC-006", [i["id"] for i in result["projection"]["open_incidents"]])

    def test_normalization_does_not_fuzzy_match_service(self):
        state = self.before["incidents.db"]
        self.assertEqual(fragment.status_oracle(state, " INVENTORY ")["normalized_name"], "inventory")
        self.assertEqual(fragment.status_oracle(state, "inventories")["branch"], "missing_service")
        self.assertEqual(fragment.status_oracle(state, "inventory service")["branch"], "invalid_slug")

    def test_correct_prose_without_observed_tool_read_is_rejected(self):
        with self.assertRaises(fragment.FragmentError):
            self.verify(calls=[])

    def test_correct_prose_without_terminal_read_result_is_rejected(self):
        journal = copy.deepcopy(self.journal)
        for content in journal[1]["request"]["contents"]:
            content["parts"] = [p for p in content["parts"] if not p.get("function_response")]
        with self.assertRaises(fragment.FragmentError):
            self.verify(journal=journal)

    def test_terminal_with_foreign_call_id_is_rejected(self):
        journal = copy.deepcopy(self.journal)
        for content in journal[1]["request"]["contents"]:
            for part in content["parts"]:
                if part.get("function_response"):
                    part["function_response"]["id"] = "foreign-read"
        with self.assertRaises(fragment.FragmentError):
            self.verify(journal=journal)

    def test_correct_terminal_with_business_write_is_rejected(self):
        after = copy.deepcopy(self.after)
        after["incidents.db"]["services"][0]["status"] = "operational"
        with self.assertRaises(fragment.FragmentError):
            self.verify(after=after)

    def test_completed_mirror_with_foreign_context_is_rejected(self):
        task = copy.deepcopy(self.task)
        task["contextId"] = "foreign-context"
        with self.assertRaises(fragment.FragmentError):
            self.verify(task=task)

    def test_foreign_task_in_same_context_is_rejected(self):
        task = copy.deepcopy(self.task)
        task["id"] = "foreign-task-in-same-session"
        with self.assertRaises(fragment.FragmentError):
            self.verify(task=task)

    def test_unknown_incident_status_is_outside_complete_fragment(self):
        state = copy.deepcopy(self.before["incidents.db"])
        state["incidents"][0]["status"] = "parked"
        with self.assertRaises(fragment.FragmentError):
            fragment.status_oracle(state, "inventory")

    def test_missing_business_table_cannot_be_assumed_empty(self):
        state = copy.deepcopy(self.before["incidents.db"])
        del state["audit_log"]
        with self.assertRaises(fragment.FragmentError):
            fragment.status_oracle(state, "inventory")

    def test_duplicate_incident_identity_is_rejected(self):
        state = copy.deepcopy(self.before["incidents.db"])
        state["incidents"].append(copy.deepcopy(state["incidents"][0]))
        with self.assertRaises(fragment.FragmentError):
            fragment.status_oracle(state, "inventory")


if __name__ == "__main__":
    unittest.main()
