"""Adversarial constructed controls; no evidence writes or original calls."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("qualification_validator_owned", HERE / "validate_qualification_v1.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class QualificationControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = validator.load_bundle(HERE / "proposal-1")

    def reject(self, mutate, reason):
        bundle = copy.deepcopy(self.base)
        mutate(bundle)
        with self.assertRaisesRegex(validator.Invalid, reason):
            validator.validate(bundle)

    @staticmethod
    def row(bundle, case_id):
        return next(r for r in bundle["candidate-table.json"]["records"] if r["id"] == case_id)

    def test_full_candidate_and_scope_validation(self):
        self.assertEqual(validator.validate(self.base)["qualified_tasks"], 0)

    def test_public_gold_leak_refused(self):
        self.reject(lambda b: b["application.json"]["records"][0].update({"gold": "correct"}), "evaluator field leaked")

    def test_dropped_or_duplicated_candidate_refused(self):
        self.reject(lambda b: b["application.json"]["records"].pop(), "lost/duplicated candidates")

    def test_original_obligation_narrowing_refused(self):
        self.reject(lambda b: b["evaluator-private.json"]["records"][0]["answer_contract"]["expected_order"].clear(), "source answer/alternative/near-miss obligation changed")

    def test_d03_mechanical_proposal_not_promoted_to_justified_decision(self):
        self.reject(lambda b: self.row(b, "agentops-d03-restart-pause").update({"disposition": "fixed_reference_obligation_observed"}), "candidate disposition inflated")

    def test_missing_decision_precondition_not_erased(self):
        self.reject(lambda b: self.row(b, "agentops-d03-restart-pause")["candidate_specific_gaps"].clear(), "d03 unsupported decision promoted")

    def test_ap2_generic_prefix_not_promoted_to_purchase(self):
        self.reject(lambda b: self.row(b, "ap2-dev-001")["reference"]["raw_summaries"][0].update({"original_purchase_observed": True}), "unobserved continuation/purchase credited")

    def test_boundary_control_not_replaced_by_full_shopper(self):
        self.reject(lambda b: self.row(b, "ap2-ho-022").update({"execution_class": "original_shopper_workflow"}), "boundary control replaced full shopper")

    def test_retained_actual_answer_not_rebound_by_local_summary(self):
        self.reject(lambda b: self.row(b, "agentops-d01-health-active")["reference"]["raw_summary"]["tasks"][0]["answer_text"].append("invented evidence"), "raw task/answer changed")

    def test_exposed_authoring_not_relabelled_holdout(self):
        self.reject(lambda b: self.row(b, "ap2-ho-001").update({"held_out_status": "untouched_holdout"}), "relabelled as untouched holdout")

    def test_new_allocation_requires_owner_coordination(self):
        self.reject(lambda b: b["next-reference-plan.json"]["records"][0].update({"execution_allowed": True}), "uncoordinated allocation")

    def test_missing_second_instance_not_replaced_by_same_fixture(self):
        self.reject(lambda b: b["study-allocation.json"]["task_slots"][1].update({"recipe_status": "authored_base_recipe_pending_independent_review"}), "silently replaced by replay")

    def test_path_and_crossing_denominators_not_reduced(self):
        self.reject(lambda b: b["study-allocation.json"]["path_cells"].pop(), "288 path cells collapsed")
        self.reject(lambda b: b["study-allocation.json"]["crossing_cells"].pop(), "96 crossing cells collapsed")

    def test_unproved_inverse_or_composed_bridge_not_invented(self):
        self.reject(lambda b: b["study-allocation.json"]["path_cells"][1].update({"route_binding": "invented inverse converter"}), "unsupported bridge placement invented")

    def test_strict_scope_count_types(self):
        self.reject(lambda b: b["candidate-table.json"]["scope"].update({"qualified_tasks": False}), "original scope changed")

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaisesRegex(validator.Invalid, "duplicate JSON key"):
            json.loads('{"qualified":false,"qualified":true}', object_pairs_hook=validator.unique_object)

    def test_second_instance_proposal_complete_with_refused_slots(self):
        bundle = validator.load_bundle(HERE / "proposal-2")
        self.assertEqual(validator.validate(bundle)["qualified_tasks"], 0)

    def test_unrealized_second_recipe_not_invented(self):
        bundle = validator.load_bundle(HERE / "proposal-2")
        row = next(r for r in bundle["second-instance-application.json"]["records"] if r["candidate_id"] == "ap2-ho-018")
        row["public"] = {"task": "invented successful receipt"}
        with self.assertRaisesRegex(validator.Invalid, "unsupported/unrealized second recipe invented"):
            validator.validate(bundle)

    def test_second_instance_public_gold_leak_refused(self):
        bundle = validator.load_bundle(HERE / "proposal-2")
        bundle["second-instance-application.json"]["records"][0]["proposed_answer"] = "private answer"
        with self.assertRaisesRegex(validator.Invalid, "private answer leaked"):
            validator.validate(bundle)


if __name__ == "__main__":
    unittest.main()
