"""Independent stdlib arithmetic review, retained after the inline inspection.

This source reads JSON/CSV and hashes bytes. It does not import or execute any
solver, codec, semantic checker, application, SDK, provider or prior analyzer.
The saved file was not a pre-execution or signed attestation. Review source
descriptions separately: this arithmetic program cannot prove general novelty.
"""
from pathlib import Path
from collections import Counter, defaultdict
from statistics import median
import hashlib
import json
import csv


def review(root):
    read = lambda n: json.loads((root / n).read_text())
    result = read("runs/method-contribution-assessment/v2-20261112-1/reanalysis.json")
    supplement = read("docs/research/method-contribution-assessment-v2-supplement-20261112.json")
    checks = []
    for label, items in (("reanalysis", result["input_identities"]),
                         ("supplement", supplement["evidence_identities"]),
                         ("supplement_reanalysis_inputs", supplement["focused_reanalysis_input_identities"])):
        for item in items:
            data = (root / item["path"]).read_bytes()
            assert len(data) == item["bytes"] and hashlib.sha256(data).hexdigest() == item["sha256"], item["path"]
        checks.append(f"{label}_all_hashes_match_{len(items)}")
    canonical = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":"),
                                         ensure_ascii=False, allow_nan=False).encode()
    high, families = {}, {}
    for claimed in result["core_budgets"]:
        budget = claimed["budget"]
        rows = [json.loads(line) for line in
                (root / f"runs/shared-lifting-scaling/v3-20261110-1/budget-{budget}/results.jsonl").read_text().splitlines()]
        assert len(rows) == 66 == len({row["case_id"] for row in rows})
        for method, totals in claimed["method_totals"].items():
            actual = Counter()
            for row in rows:
                arm = row["algorithms"][method]
                output = arm["execution"]["result"]
                actual[output["decision"]] += 1
                actual["work_units"] += output["stats"]["work_units"]
                accepted = arm["valid_result"] is True and arm["certificate_valid"] is True and output["decision"] in ("supported", "unsupported")
                if accepted:
                    actual["certified"] += 1
                    actual["proof_bytes"] += len(canonical(output["certificate"]))
                else:
                    assert output["decision"] == "unknown" and output["certificate"] is None
            assert dict(actual) == totals, (budget, method, actual, totals)
        for method, field in (("shared_lift", "shared_vs_goal_direct"),
                              ("candidate", "original_refinement_vs_goal_direct")):
            paired = Counter()
            for row in rows:
                accepted = lambda arm: arm["valid_result"] is True and arm["certificate_valid"] is True and arm["execution"]["result"]["decision"] in ("supported", "unsupported")
                own, direct = accepted(row["algorithms"][method]), accepted(row["algorithms"]["direct_pruned"])
                paired["both" if own and direct else "candidate_only" if own else "direct_only" if direct else "neither"] += 1
            assert dict(paired) == claimed[field]
        if budget == 100000:
            high = {row["case_id"]: row for row in rows}
            families = {row["case_id"]: row["family"] for row in rows}
    checks.append("all_four_budget_raw_counts_proof_bytes_work_and_paired_cells_match")
    codec = read("docs/research/refutation-prefix-dag-comparison-v2.json")
    assert len(codec["rows"]) == 26 == len({row["case_id"] for row in codec["rows"]})
    for row in codec["rows"]:
        for method, prefix in (("shared_lift", "old"), ("direct_pruned", "direct")):
            proof = high[row["case_id"]]["algorithms"][method]["execution"]["result"]["certificate"]
            data = canonical(proof)
            assert len(data) == row[prefix + "_bytes"]
            assert hashlib.sha256(data).hexdigest() == row[prefix + "_certificate_sha256"]
        assert row["restored_certificate_sha256"] == row["old_certificate_sha256"]
        assert row["exact_ordered_object_and_canonical_byte_round_trip"] is True
        assert row["new_semantic_checker_call"] is False
    shrinking = [row["case_id"] for row in codec["rows"] if row["dag_bytes"] < row["old_bytes"]]
    direct_wins = [{key: row[key] for key in ("case_id", "old_bytes", "dag_bytes", "direct_bytes")}
                   for row in codec["rows"] if row["dag_bytes"] < row["direct_bytes"]]
    assert set(shrinking) == {"scale-0023", "scale-0031"}
    for name, excluded in (("all_26", set()), ("excluding_scale_0031", {"scale-0031"}),
                            ("excluding_both_shrinking_cases", set(shrinking))):
        rows = [row for row in codec["rows"] if row["case_id"] not in excluded]
        claimed = result["codec_subset_sensitivity"][name]
        assert claimed["cases"] == len(rows)
        for key, field in (("old_bytes", "old_bytes"), ("dag_bytes", "dag_bytes_inherited_from_bound_codec_receipt"),
                           ("direct_bytes", "direct_bytes")):
            assert sum(row[key] for row in rows) == claimed[field]
        for field, left, right in (("dag_minus_old_bytes", "dag_bytes", "old_bytes"),
                                    ("dag_minus_direct_bytes", "dag_bytes", "direct_bytes")):
            assert sum(row[left] - row[right] for row in rows) == claimed[field]
        assert claimed["dag_smaller_than_old_cases"] == sum(row["dag_bytes"] < row["old_bytes"] for row in rows)
        assert claimed["dag_smaller_than_direct_cases"] == sum(row["dag_bytes"] < row["direct_bytes"] for row in rows)
    checks.append("all26_raw_original_direct_hashes_and_posthoc_subsets_match")
    cache = list(csv.DictReader((root / "runs/shared-cache-ablation/read-review-42879031721-1/case-methods.csv").read_text().splitlines()))
    for method, claimed in result["cache_high_allowance_totals"].items():
        rows = [row for row in cache if row["budget"] == "100000" and row["method"] == method]
        assert len(rows) == 66
        assert claimed == {"profiles": 66, "certified": sum(row["certified"] == "True" for row in rows),
            "work_units": sum(int(row["work_units"]) for row in rows),
            "proof_bytes": sum(int(row["proof_bytes"]) for row in rows if row["certified"] == "True"),
            "prefix_hits": sum(int(row["prefix_cache_hits"]) for row in rows),
            "relation_hits": sum(int(row["relation_cache_hits"]) for row in rows)}
    checks.append("cache_high_allowance_totals_match_raw_csv")
    data = (root / "runs/common-cost-development/v1/read-audit-42927208534-3/cells.jsonl").read_bytes()
    audit = read("runs/common-cost-development/v1/read-audit-42927208534-3/result.json")
    export = next(row for row in audit["exports"] if row["path"] == "cells.jsonl")
    assert len(data) == export["bytes"] and hashlib.sha256(data).hexdigest() == export["sha256"]
    cells = [json.loads(line) for line in data.splitlines()]
    assert len(cells) == 1650 == len({row["cell"]["id"] for row in cells})
    assert dict(Counter(row["status"] for row in cells)) == result["physical_allocation_statuses"] == {"certified": 1350, "unknown": 300}
    grouped = defaultdict(list)
    for row in cells:
        grouped[row["cell"]["profile_id"], row["cell"]["method_id"]].append(row)
    assert len(grouped) == 330
    for rows in grouped.values():
        assert len(rows) == 5 and {row["cell"]["repeat"] for row in rows} == set(range(5)) and {row["cell"]["position"] for row in rows} == set(range(5))
    for row in result["physical_per_profile"]:
        profile = row["profile_id"]
        assert row["family"] == families[profile]
        all_cells = [cell for (p, method), group in grouped.items() if p == profile for cell in group]
        assert len(all_cells) == 25 and all(cell["status"] == "certified" and cell["certificate_valid"] is True
            and cell["independent_solver_logical_cap_nonbinding"] is True
            and cell["cpu_limit_nonbinding_from_lifetime_observation"] is True
            and cell["wall_limit_nonbinding_from_outer_observation"] is True for cell in all_cells)
        for metric in ("cpu_total_ns", "outer_wall_ns", "peak_rss_bytes"):
            direct = median(cell["resources"][metric] for cell in grouped[profile, "goal_pruned_direct"])
            shared = median(cell["resources"][metric] for cell in grouped[profile, "shared_lift"])
            assert row[metric] == {"direct_median": direct, "shared_median": shared, "shared_over_direct": shared / direct}
    assert len(result["physical_per_profile"]) == len(result["physical_eligible_profiles"]) == 54
    assert len(result["physical_unknown_profiles_excluded_from_ratios"]) == 12
    for profile in result["physical_unknown_profiles_excluded_from_ratios"]:
        assert all(cell["status"] == "unknown" for (p, method), group in grouped.items() if p == profile for cell in group)
    for family, claimed in result["physical_shared_over_direct_descriptive_groups"].items():
        rows = [row for row in result["physical_per_profile"] if family == "all_eligible" or row["family"] == family]
        assert claimed["profiles"] == len(rows)
        for metric, values in claimed["metrics"].items():
            ratios = [row[metric]["shared_over_direct"] for row in rows]
            assert values == {"median_shared_over_direct": median(ratios), "minimum": min(ratios), "maximum": max(ratios),
                "shared_lower": sum(value < 1 for value in ratios), "equal": sum(value == 1 for value in ratios),
                "shared_higher": sum(value > 1 for value in ratios)}
    checks.append("all1650_audited_cost_cells_54eligible_12unknown_and_all_family_ratios_match")
    assert 27248 - 15128 + 11918 == 24038 and 24038 - 19880 == 4158
    assert result["percentage_credit_claimed"] is False and result["human_review_claimed"] is False
    assert result["fresh_semantic_validation_claimed"] is False and result["new_solver_codec_checker_application_SDK_provider_or_worker_executions"] == 0
    assert supplement["new_general_algorithmic_principle_established"] is False
    assert supplement["qualified_holdout_or_full_application_study"] is False and supplement["percentage_credit_claimed"] is False
    return {"status": "independent_read_only_arithmetic_scope_check_passed", "checks": checks,
            "direct_relative_codec_wins": direct_wins,
            "physical_ratios": result["physical_shared_over_direct_descriptive_groups"]["all_eligible"],
            "new_solver_codec_checker_provider_executions": 0}


if __name__ == "__main__":
    print(json.dumps(review(Path(__file__).resolve().parents[3]), indent=2))
