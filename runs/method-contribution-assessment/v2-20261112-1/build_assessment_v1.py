"""Write the additive current-evidence contribution disposition from bound reads."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "docs/research/method-contribution-assessment-v2-supplement-20261112.json"


def identity(name):
    raw = (ROOT / name).read_bytes()
    return {"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    if OUTPUT.exists():
        raise ValueError("additive_disposition_must_not_overwrite")
    reanalysis_name = "runs/method-contribution-assessment/v2-20261112-1/reanalysis.json"
    reanalysis = json.loads((ROOT / reanalysis_name).read_bytes())
    if (reanalysis["status"] != "passed_focused_retained_arithmetic_checks"
            or reanalysis["new_solver_codec_checker_application_SDK_provider_or_worker_executions"] != 0):
        raise ValueError("passed_read_only_reanalysis_required")
    sources = ["docs/research/method-contribution-assessment-v2.md", "docs/research/method-contribution-assessment-v2.json",
        "docs/research/method-contribution-code-peer-v1.json", "docs/research/student-budget-experiment-design.md",
        "docs/research/shared-lifting-scaling-results-v3.md", "docs/research/guard-pruned-comparison-results-v3.md",
        "docs/research/shared-cache-ablation-results-v3.md", "docs/research/final-literature-review-v1.md",
        "docs/research/refutation-prefix-dag-v2.md", "docs/research/refutation-prefix-dag-comparison-v2.json",
        "docs/research/common-cost-results-v1.md", "paper/working-draft-v15.md", "paper/claim-ledger-v15.json",
        "src/interoperability/direct_goal_pruned_v2.py", "src/interoperability/direct_guard_pruned_v3.py",
        "src/interoperability/refinement.py", "src/interoperability/refinement_shared_lift_v2.py",
        "src/interoperability/refinement_oracle.py", "src/interoperability/refutation_prefix_dag_v2.py",
        "docs/research/method-contribution-assessment-v2-supplement-20261112.md", reanalysis_name,
        "runs/method-contribution-assessment/v2-20261112-1/analyze_retained_v1.py",
        "runs/method-contribution-assessment/v2-20261112-1/build_assessment_v1.py"]
    evidence = [identity(name) for name in sources]
    shared_only = [row["shared_vs_goal_direct"].get("candidate_only", 0) for row in reanalysis["core_budgets"]]
    value = {"schema_version": "method-contribution-assessment-v2-current-evidence-supplement/1",
        "status": "bounded_artifact_findings_supported_method_novelty_and_full_study_unresolved",
        "created_utc": datetime.now(timezone.utc).isoformat(), "author": "Codex AI /root/overnight_acceptance",
        "evidence_cutoff": "Sealed V15, lossless refutation-prefix DAG V2 and common-cost run42927208534; current V5 prospective diagnostics are not method-results evidence.",
        "predecessor_assessment_preserved": True, "original_distinct_method_and_two_domain_study_objective_preserved": True,
        "artifact_only_replacement_objective_selected": False, "percentage_credit_claimed": False,
        "new_general_algorithmic_principle_established": False, "novelty_impossibility_claimed": False,
        "human_scientific_review": False, "qualified_holdout_or_full_application_study": False,
        "scope_or_global_status_or_sealed_manuscript_edits": False,
        "supported_contribution": "Executable source-bound finite admission/certificate and empirical benchmark artifact separating relation reuse, proof representation, bounded unknowns and measured worker costs, with adverse results and reproducibility evidence retained.",
        "strongest_measured_same_evidence_comparator": {"source": "src/interoperability/direct_goal_pruned_v2.py",
            "features": ["goal-relevant bounded state/depth/whole-frame product", "complete whole-frame relation cache",
                "remaining-horizon safe goal-cone pruning", "first-feasible goal tuple return", "separate reconstructed negative product closure"],
            "guard_successor": "src/interoperability/direct_guard_pruned_v3.py",
            "not_all_applicable_symbolic_or_contract_systems_compared": True},
        "dispositions": [
            {"id": "distinct_general_admission_method", "disposition": "not_established",
             "reason": "Implemented bounded reachability/refinement, whole-input memoization and conservative guard pruning instantiate established mechanisms; identify a precise distinctive operation/property before a new algorithm claim."},
            {"id": "shared_lifting_certified_coverage_advantage", "disposition": "adverse_in_measured_development_suite",
             "shared_only_certified_by_budget_32_256_4096_100000": shared_only,
             "reason": "Shared-only certification is zero at every declared allowance; at256 shared39 versus direct54 of66. Method-specific charges do not establish equal physical effort."},
            {"id": "original_refinement_low_allowance_counterbalance", "disposition": "supported_under_declared_meters",
             "paired_at32": reanalysis["core_budgets"][0]["original_refinement_vs_goal_direct"],
             "reason": "Original refinement24 versus direct20, including4 refinement-only certificates, prevents a claim that direct dominates every method at every allowance."},
            {"id": "bounded_lossless_proof_packaging", "disposition": "implemented_and_bounded_size_findings_supported",
             "reason": "All26 retained negative objects roundtrip in bound codec evidence.24 wrappers grow; graph expansion delegates to the unchanged checker, so no directly compressed semantic-checking improvement is shown."},
            {"id": "codec_induced_direct_proof_advantage", "disposition": "not_established",
             "reason": "Two DAG wrappers are smaller than direct but their original prefix proofs were already smaller still. Aggregate DAG11918 versus direct7760 bytes remains adverse."},
            {"id": "common_physical_worker_cost_lane", "disposition": "completed_bounded_development_measurement",
             "reason": "All1650 allocated attempts remain retained, with1350certified and300unknown. Five position-balanced dependent repeats permit descriptive paired worker-cost medians, not population inference."},
            {"id": "shared_lifting_practical_superiority", "disposition": "adverse_on_all54_eligible_measured_profiles",
             "reason": "Shared median lifetime CPU, outer wall and peak RSS exceed goal-pruned direct for all54eligible profiles across every represented family. General performance rankings and unmeasured full workflow costs remain unqualified."},
            {"id": "amortized_cross_call_evidence_reuse", "disposition": "not_implemented_or_measured",
             "reason": "Current caches remain invocation-local. Source/profile/contract/principal/task/state/freshness dependency and invalidation correctness are not supplied by local memoization."},
            {"id": "artifact_evidence_pipeline_value", "disposition": "supported_at_declared_scope",
             "reason": "Independent certificate interfaces, all-case unknown/failure accounting, source/job/certificate identities and cross-platform deterministic reproduction make the adverse results reviewable. These engineering properties do not establish their own novelty or human review."},
            {"id": "source_model_route_gold_holdout_and_utility", "disposition": "unresolved_original_study_obligations",
             "reason": "Authored profile variants, byte audits, demo receipts and provider calls do not supply full source-to-model/route qualification, human gold, untouched holdout or equal-information application success."}],
        "focused_findings": {"codec_post_hoc_subset_sensitivity": reanalysis["codec_subset_sensitivity"],
            "all_accepted_proof_arithmetic_not_integrated_execution": reanalysis["codec_all_accepted_proof_arithmetic"],
            "physical_shared_over_direct_descriptive_groups": reanalysis["physical_shared_over_direct_descriptive_groups"],
            "physical_allocation_statuses": reanalysis["physical_allocation_statuses"]},
        "actionable_next_requirements": [
            {"id": "distinct_step_before_scaling", "priority": 1, "requires": "Versioned pseudocode, quantifiers and assumptions identifying a technical step absent from precise closest applicable product/refinement/summary/compression mechanisms; independent scientific challenge before another large sweep."},
            {"id": "compressed_semantic_checking", "priority": 2, "requires": "If pursuing checking advantage, prove full correlated state/frame/depth/profile/clock and prefix-coverage obligations in an independently reconstructive compressed checker; measure against expansion plus unchanged checking. Otherwise keep packaging-only wording."},
            {"id": "integrated_common_cost_ablation", "priority": 3, "requires": "Prospectively freeze integrated solver/encoder/decoder/checker resource accounting and workload. Compare optimized direct, unchanged refinement/shared, trie/suffix sharing and credible generic lossless compression; retain size increases, budget refusals and unknowns. Current common-cost run does not include the new codec arm."},
            {"id": "cross_call_invalidation", "priority": 4, "requires": "If pursuing reuse, implement and verify dependency/invalidation for source/profile, contract, principal/task namespace, state and evidence expiry; charge cold, warm and update costs against credible incremental direct."},
            {"id": "new_reviewed_discriminating_material", "priority": 5, "requires": "Create independently reviewed new development/adversarial cases varying repetition separately from correlation/uncertainty, then prospectively seal genuinely untouched evaluation material. Existing66profiles remain exposed development cases."},
            {"id": "qualified_application_confirmation", "priority": 6, "requires": "Preserve original source/route, human task/gold/near-miss,96task/288path-cell/96additionalcrossing and equal-information recovery/admission obligations. Grade all original goals and forbidden intermediate effects separately from valid admission/refusal."}],
        "independence_and_execution": {"static_source_and_retained_arithmetic_only": True,
            "new_solver_codec_checker_application_SDK_provider_or_worker_executions": 0,
            "new_external_literature_search_or_system_reproduction": False,
            "codec_semantic_acceptance_inherited_not_reexecuted": True,
            "physical_cells_inherited_from_exact_prior_audited_export": True,
            "post_hoc_sensitivity_not_new_primary_denominator": True},
        "evidence_identities": evidence, "focused_reanalysis_input_identities": reanalysis["input_identities"]}
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": value["status"], "dispositions": len(value["dispositions"]),
        "evidence_identities": len(evidence), "new_experiments": 0, "percentage_credit_claimed": False}))


if __name__ == "__main__":
    main()
