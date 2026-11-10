"""Bind the independent method assessment to existing source and evidence."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/research/method-contribution-assessment-v2.md"
OUTPUT = ROOT / "docs/research/method-contribution-assessment-v2.json"


def read(path):
    return json.loads((ROOT / path).read_bytes())


def record(path):
    raw = (ROOT / path).read_bytes()
    return {"path": path, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    if OUTPUT.exists():
        raise ValueError("fresh_assessment_output_required")
    numeric_path = "runs/ap2-reference-development/v5/retained-42881390576-2/numeric-peer-review-v1.json"
    peer_path = "runs/ap2-reference-development/v5/retained-42881390576-2/independent-peer-review-v1.json"
    adk_path = "runs/ap2-original-shopper-development/v7/retained-42886479185-1/independent-raw-peer-review-v1.json"
    cache_path = "runs/shared-cache-ablation/read-review-42879031721-1/result.json"
    agentops_path = "runs/ci-agentops-governed-app-reference-v4/retained-42887519756-1/independent-raw-state-census-v1.json"
    numeric, peer, adk, cache = map(read, (numeric_path, peer_path, adk_path, cache_path))
    if peer["disagreements"] or peer["source_gate_verified_cells"] != 65 or numeric["reviewed_cells"] != 65:
        raise ValueError("AP2 peer review incomplete")
    if numeric["total_verified_purchases"] != 36 or numeric["total_strict_error_free_owned_cell_purchases"] != 31:
        raise ValueError("AP2 observed outcomes differ")
    if adk["candidate_denominator"] != 34 or adk["complete_original_adk_prefixes"] != 29 or adk["actual_original_purchases"] != 0:
        raise ValueError("ADK observed outcomes differ")
    evidence = [
        "docs/research/final-literature-review-v1.md", "paper/references-v3.json", "paper/working-draft-v7.md",
        "docs/research/checkpoints.md", "docs/research/student-budget-experiment-design.md",
        "docs/research/implementation-novelty-gate.md", "docs/research/c1-callsite-factoring-screen-v1.md",
        "docs/research/direct-goal-pruning-fairness-v2.md", "docs/research/shared-lifting-scaling-results-v3.md",
        "docs/research/guard-pruned-comparator-v3.md", "docs/research/guard-pruned-comparison-results-v3.md",
        "src/interoperability/refinement.py", "src/interoperability/refinement_shared_lift_v2.py",
        "src/interoperability/refinement_oracle.py", "src/interoperability/direct_goal_pruned_v2.py",
        "src/interoperability/direct_guard_pruned_v3.py", "src/shared-lifting-pilot-final-review.md",
        numeric_path, peer_path, adk_path, cache_path, agentops_path,
        DOC.relative_to(ROOT).as_posix(), Path(__file__).resolve().relative_to(ROOT).as_posix(),
    ]
    text = DOC.read_text(encoding="utf-8")
    bad_links = []
    for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
        parsed = urlparse(target)
        if parsed.scheme:
            continue
        resolved = (DOC.parent / unquote(parsed.path)).resolve()
        if not resolved.is_relative_to(ROOT) or (resolved != OUTPUT and not resolved.exists()):
            bad_links.append(target)
    if bad_links:
        raise ValueError("assessment_links_do_not_resolve:" + repr(bad_links))
    data = {
        "schema_version": "independent-method-contribution-assessment/2",
        "reviewed_utc": datetime.now(timezone.utc).isoformat(), "author": "Codex AI, /root/agentops_task_bank",
        "status": "evidence_bound_assessment_complete_original_method_and_full_study_unresolved",
        "current_evidence_cutoff": "Manuscript v7, AP2 payment-tool v5, original ADK v7 and retained cache/guard studies",
        "supported_positioning": "Executable task-relative admission benchmark and negative mechanistic findings under disclosed finite/development assumptions",
        "potential_paper_contribution": "An honest research narrative; venue significance, originality, benchmark validity and acceptance remain scientific judgments",
        "original_distinct_method_objective_preserved": True, "original_two_domain_full_study_objective_preserved": True,
        "scope_revision_performed": False, "artifact_only_alternative_selected": False,
        "original_method_claim_established": False, "new_general_verification_principle_established": False,
        "shared_lifting_practical_superiority_established": False, "field_first_benchmark_or_source_issue_claim_established": False,
        "closest_mechanisms": [
            {"mechanism": "CEGAR/lazy symbolic witness refinement", "reference": 19,
             "source": "src/interoperability/refinement.py", "anchor": "_lift and exact-prefix _blocked/evaluate",
             "assessment": "Executable bounded adaptation; no demonstrated additional general refinement rule"},
            {"mechanism": "Memoization and stateful relational summaries", "reference": 21,
             "source": "src/interoperability/refinement_shared_lift_v2.py", "anchor": "_SharedLift._expand/lift/evaluate",
             "assessment": "Verified key/completeness/history obligations, not an invention of identical-input reuse"},
            {"mechanism": "Conservative constraint pruning", "reference": 20,
             "source": "src/interoperability/direct_guard_pruned_v3.py", "anchor": "_dependencies and _assignments",
             "assessment": "Definitely-false closed-guard pruning; no AC-3/fixpoint propagation"},
            {"mechanism": "Finite reachability, contracts and bounded checking", "references": [7, 8, 9, 10, 22],
             "source": "src/interoperability/direct_goal_pruned_v2.py", "anchor": "evaluate and check_certificate",
             "assessment": "Goal-cone-pruned memoized direct product is a credible same-input comparator"},
        ],
        "supported_claims": [
            {"id": "S1", "claim": "Implemented explicit finite recipe/contracts with correlated frames, atomic updates, three-valued decisions and independent checking",
             "boundary": "Software and semantic-interface artifact; no universal correctness or source-completeness proof"},
            {"id": "S2", "claim": "Same-evidence development comparisons and separately allocated stronger comparator/cache ablations",
             "five_method_cells": 1320, "profiles": 66, "allowances": 4,
             "cache_method_cells": cache["algorithm_cells"], "cache_policy_cells": cache["cache_policy_cells"],
             "boundary": "Related authored profiles reused across studies; cell counts are not independent tasks"},
            {"id": "S3", "claim": "Relation reuse does not compress the retained path-list proof and measured cache bookkeeping can erase charged-work savings",
             "stress_relation_checks": [1024, 16], "stress_charged_work": [5566, 14773], "stress_proof_bytes": [8895, 8895],
             "boundary": "This implementation/representation, not a CPU ranking or general symbolic-method lower bound"},
            {"id": "S4", "claim": "Correct admission/refusal differs from completed business utility",
             "AP2_cells": 65, "purchase_counts": peer["purchase_counts"], "purchases": 36, "error_free_owned_cell_purchases": 31,
             "shared_minus_recovery_purchase_difference": {"numerator": -7, "denominator": 13},
             "recovery_shared_minus_recovery_purchase_difference": {"numerator": -1, "denominator": 13},
             "boundary": "Unequal disclosed arm information, offline fixture and ASGI; not full ADK success or held-out live utility"},
            {"id": "S5", "claim": "Original source-bound generic-challenge loss, original ADK prefixes, wallet projection and reset observations",
             "candidate_denominator": 34, "ADK_prefixes": 29, "generic_adverse": 28, "purchases": 0,
             "boundary": "Unrealized original obligations stay unqualified; first-report/whole-interface non-support not established"},
        ],
        "adverse_and_counterbalancing_findings": {
            "shared_only_certified_profiles": [0, 0, 0, 0],
            "shared_direct_certified_at_256": [39, 54], "high_allowance_decisions_all_five_methods": {"supported": 28, "unsupported": 26, "unknown": 12},
            "original_refinement_direct_certified_at_32": [24, 20],
            "low_allowance_original_refinement_interpretation": "Real method-meter coverage win; no prespecified common-cost practical advantage or claim of direct dominance at every allowance",
            "guard_direct_work_at_100000": [4186, 3382],
            "cache_neither_prefix_relation_both_work_at_100000": [46278, 44432, 50150, 46840],
            "cache_direct_proof_bytes_at_100000": [27248, 19880],
        },
        "unresolved_claims": [
            {"id": "U1", "claim": "Distinct technical step beyond closest same-evidence mechanisms"},
            {"id": "U2", "claim": "Common end-to-end cost advantage or sound cross-invocation evidence reuse/invalidation"},
            {"id": "U3", "claim": "Complete source-to-model and two actual bridge/crossing qualification"},
            {"id": "U4", "claim": "Candidate-specific validated references/gold, untouched held-out study and equal-information utility"},
            {"id": "U5", "claim": "Accountable final novelty, feasibility, task/gold and scientific review beyond the supplied pilot-number review"},
        ],
        "remaining_original_method_work": [
            "Versioned distinctive pseudocode/property and same-evidence closest-method reduction test",
            "Explicit-assumption property proof and independent adversarial/certificate obligations",
            "Prespecified meaningful threshold/workload, optimized direct plus applicable symbolic/backward/contract/incremental comparisons and full cost accounting",
            "Independently qualified source-to-model alternatives, actual route/crossing directions and native controls on both eligible bridges",
            "All68 original candidates, reviewed gold/near-misses, unresolved branch completion and prospectively independent sealed evaluation material",
            "Preserved96-task/three-path/crossing allocation unless an explicit recorded scope decision changes it, complete frozen runs, independent reproduction and scientific review",
        ],
        "unimplemented_research_directions": ["Compact independently checked refutation DAG", "Proven exact quotient", "Sound dependency-bound evidence invalidation"],
        "directions_are_hypotheses_not_achieved_contributions": True,
        "targeted_literature_review_not_exhaustive": True, "Mackworth_fresh_full_body_review_not_claimed": True,
        "AgentOps_mechanical_census_not_semantic_gold": True, "supplied_pilot_review_not_final_novelty_or_gold_review": True,
        "new_application_solver_provider_or_external_experiment_calls": 0, "human_scientific_review": False,
        "all_local_assessment_links_resolve": True, "evidence": [record(path) for path in evidence],
    }
    OUTPUT.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": data["status"], "evidence_files": len(evidence), "supported_claims": len(data["supported_claims"]),
                      "unresolved_claims": len(data["unresolved_claims"]), "scope_revision_performed": False}))


if __name__ == "__main__":
    main()
