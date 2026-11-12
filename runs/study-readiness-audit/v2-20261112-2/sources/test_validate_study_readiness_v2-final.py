"""Adversarial controls for the source-bound readiness snapshot and topology grammar."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("readiness", ROOT / "scripts/validate_study_readiness_v2.py")
readiness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(readiness)


def topology():
    stages = ["observe", "investigate", "review", "report"]
    variants = []
    for count in (1, 2, 3):
        edges = []
        for i in range(3):
            edge = {"from_stage": stages[i], "to_stage": stages[i + 1],
                    "delivery": "bridge" if i < count else "reference", "profile_id": None}
            if i < count:
                edge.update(profile_id="agentops_mg_B7_configured", from_surface="mcp_client", to_surface="a2a_agent")
            edges.append(edge)
        variants.append({"crossing_count": count, "edges": edges})
    return {"execution_allowed": False, "original_stage_surfaces_qualified": False,
            "task_id": "development-topology-control-only", "initial_state_sha256": "0" * 64,
            "horizon": 4, "stage_ids": stages, "profile_id": "agentops_mg_B7_configured", "variants": variants}


class SnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = readiness.read_json(ROOT / "runs/study-readiness-audit/v2-20261112-1/inventory.json")
        # Hash actual inputs once; mutations below change claims, never source files.
        # The separate CLI receipt independently performs uncached live hashing.
        cls.actual_hashes = {str((ROOT / b["path"]).resolve()): readiness.digest(ROOT / b["path"])
                             for b in cls.original["exact_input_bindings"]}

    def setUp(self):
        self.inventory = copy.deepcopy(self.original)

    def verify(self):
        with mock.patch.object(readiness, "digest", side_effect=lambda p: self.actual_hashes[str(p.resolve())]):
            return readiness.validate(ROOT, self.inventory)

    def reject(self):
        with self.assertRaises(readiness.ReadinessError):
            self.verify()

    def test_current_snapshot_passes_without_semantic_credit(self):
        result = self.verify()
        self.assertEqual(result["qualified_confirmatory_tasks"], 0)
        self.assertFalse(result["full_task_oracle_complete"])
        self.assertFalse(result["human_review"])

    def test_development_cannot_be_relabelled_holdout(self):
        self.inventory["records"][0]["original_split"] = "held_out"
        self.reject()

    def test_ai_review_cannot_be_promoted_to_human_gold(self):
        self.inventory["records"][0]["human_review"] = "approved_by_parallel_AI_reviewers"
        self.reject()

    def test_qualifying_false_flag_as_zero_is_rejected(self):
        self.inventory["records"][0]["qualified_candidate"] = 0
        self.reject()

    def test_zero_count_as_false_is_rejected(self):
        self.inventory["eligible_confirmatory_counts"]["held_out_tasks"] = False
        self.reject()

    def test_duplicate_candidate_is_rejected(self):
        self.inventory["records"][-1] = copy.deepcopy(self.inventory["records"][0])
        self.reject()

    def test_boundary_control_cannot_become_full_shopper(self):
        row = next(r for r in self.inventory["records"] if r["id"] == "ap2-ho-019")
        row["execution_class"] = "original_shopper_workflow"
        self.reject()

    def test_refused_second_slot_cannot_gain_recipe(self):
        row = next(r for r in self.inventory["records"] if r.get("second_instance", {}).get("specific_blocker"))
        row["second_instance"]["status"] = "second_source_bound_candidate_recipe_authored"
        self.reject()

    def test_native_positive_cannot_enable_unqualified_study_cell(self):
        self.inventory["planned_base_path_cells"][0]["execution_allowed"] = True
        self.reject()

    def test_crossing_subset_cannot_be_selected_after_outcomes(self):
        self.inventory["planned_crossing_subset_slots"][0]["instance_id"] = self.inventory["planned_task_slots"][0]["id"]
        self.reject()

    def test_route_cannot_claim_inverse_conversion(self):
        self.inventory["routes"][1]["inverse_conversion_established_for_selected_profile"] = True
        self.reject()

    def test_route_direction_cannot_reverse(self):
        self.inventory["routes"][1]["observed_direction"] = "a2a_agent_to_mcp_client"
        self.reject()

    def test_reference_non_success_cannot_be_promoted(self):
        self.inventory["records"][0]["retained_semantic_disposition"] = "complete_human_gold_validated"
        self.reject()

    def test_stale_source_hash_is_rejected(self):
        binding = next(b for b in self.inventory["exact_input_bindings"] if b["path"].endswith("/models.py"))
        binding["sha256"] = "f" * 64
        self.reject()

    def test_citation_cannot_disagree_with_bound_source(self):
        self.inventory["records"][0]["source_citations"]["normalize_slug"]["sha256"] = "f" * 64
        self.reject()

    def test_workspace_escape_is_rejected(self):
        self.inventory["exact_input_bindings"][0]["path"] = "../other/source.json"
        self.reject()

    def test_completed_checkpoint_relabel_is_rejected(self):
        self.inventory["status"] = "full_study_complete"
        self.reject()

    def test_missing_eligibility_denominator_is_rejected(self):
        del self.inventory["eligible_confirmatory_counts"]["held_out_tasks"]
        self.reject()

    def test_missing_provider_authorization_limit_is_rejected(self):
        del self.inventory["authorization"]["provider_calls"]
        self.reject()

    def test_later_workflow_execution_cannot_become_success(self):
        row = next(r for r in self.inventory["records"] if r["id"] == "agentops-h09-workflow-select-target")
        row["later_development_overlay"]["qualifies_original_task"] = True
        self.reject()


class GrammarTests(unittest.TestCase):
    def test_valid_outgoing_grammar_is_still_disabled(self):
        result = readiness.validate_topology_control(topology())
        self.assertTrue(result["placement_grammar_valid"])
        self.assertFalse(result["original_route_qualified"])
        self.assertFalse(result["execution_allowed"])

    def test_inverse_edge_rejected(self):
        plan = topology()
        plan["variants"][2]["edges"][1].update(from_surface="a2a_agent", to_surface="mcp_client")
        with self.assertRaises(readiness.ReadinessError):
            readiness.validate_topology_control(plan)

    def test_two_role_graph_cannot_stand_for_four_stages(self):
        plan = topology()
        plan["stage_ids"] = ["sender", "receiver"]
        with self.assertRaises(readiness.ReadinessError):
            readiness.validate_topology_control(plan)

    def test_count_must_match_placed_bridge_edges(self):
        plan = topology()
        plan["variants"][1]["edges"][1] = copy.deepcopy(plan["variants"][0]["edges"][1])
        with self.assertRaises(readiness.ReadinessError):
            readiness.validate_topology_control(plan)

    def test_same_converter_must_be_used_across_counts(self):
        plan = topology()
        plan["variants"][2]["edges"][0]["profile_id"] = "agentops_amir_B1_B2_B3"
        with self.assertRaises(readiness.ReadinessError):
            readiness.validate_topology_control(plan)

    def test_grammar_cannot_authorize_execution(self):
        plan = topology()
        plan["execution_allowed"] = True
        with self.assertRaises(readiness.ReadinessError):
            readiness.validate_topology_control(plan)

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(readiness.ReadinessError):
            json.loads('{"qualified":false,"qualified":true}', object_pairs_hook=readiness.unique_object)

    def test_output_overwrite_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "result.json"
            readiness.write_exclusive(output, {"first": True})
            with self.assertRaises(FileExistsError):
                readiness.write_exclusive(output, {"second": True})
            self.assertEqual(readiness.read_json(output), {"first": True})


if __name__ == "__main__":
    unittest.main()
