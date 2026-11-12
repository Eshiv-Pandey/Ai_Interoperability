"""Focused arithmetic reanalysis of existing method/contribution evidence.

Stdlib reads only. No admission solver, codec, checker, application, SDK,
provider, original worker or downloaded code is imported or executed.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent / "reanalysis.json"
METHODS = ("baseline", "direct_pruned", "candidate", "shared_lift")
METRICS = ("cpu_total_ns", "outer_wall_ns", "peak_rss_bytes")
BINDINGS = {}


def need(value, reason):
    if not value:
        raise ValueError(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def read(name):
    path = ROOT / name
    raw = path.read_bytes()
    BINDINGS[name] = {"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    return raw


def document(name):
    return json.loads(read(name))


def conclusive(arm):
    result = arm["execution"]["result"]
    return arm["valid_result"] is True and arm["certificate_valid"] is True and result["decision"] in {"supported", "unsupported"}


def main():
    need(not OUTPUT.exists(), "fresh_reanalysis_output_required")
    budgets, raw_high = [], {}
    families = {}
    for budget in (32, 256, 4096, 100000):
        name = f"runs/shared-lifting-scaling/v3-20261110-1/budget-{budget}/results.jsonl"
        rows = [json.loads(line) for line in read(name).splitlines()]
        need(len(rows) == len({row["case_id"] for row in rows}) == 66, "complete_unique_core_profile_census_required")
        counts = {method: Counter() for method in METHODS}
        shared_pair, original_pair = Counter(), Counter()
        for row in rows:
            need(set(row["algorithms"]) == set(METHODS), "fixed_core_methods_required")
            families[row["case_id"]] = row["family"]
            flags = {}
            for method, arm in row["algorithms"].items():
                result = arm["execution"]["result"]
                counts[method][result["decision"]] += 1
                flags[method] = conclusive(arm)
                if flags[method]:
                    counts[method]["certified"] += 1
                    counts[method]["proof_bytes"] += len(canonical(result["certificate"]))
                else:
                    need(result["decision"] == "unknown" and result["certificate"] is None, "nonconclusive_core_outcome_not_retained_unknown")
                counts[method]["work_units"] += result["stats"]["work_units"]
            for candidate, counter in (("shared_lift", shared_pair), ("candidate", original_pair)):
                counter[("both" if flags[candidate] and flags["direct_pruned"] else "candidate_only" if flags[candidate]
                    else "direct_only" if flags["direct_pruned"] else "neither")] += 1
        budgets.append({"budget": budget, "profiles": 66, "method_totals": {key: dict(value) for key, value in counts.items()},
            "shared_vs_goal_direct": dict(shared_pair), "original_refinement_vs_goal_direct": dict(original_pair)})
        if budget == 100000:
            raw_high = {row["case_id"]: row for row in rows}
    need(all(row["shared_vs_goal_direct"].get("candidate_only", 0) == 0 for row in budgets), "shared_only_certification_unexpected")
    cache_name = "runs/shared-cache-ablation/read-review-42879031721-1/case-methods.csv"
    cache = list(csv.DictReader(read(cache_name).decode("utf-8").splitlines()))
    need(len(cache) == len({(row["budget"], row["case_id"], row["method"]) for row in cache}) == 1584,
         "complete_unique_cache_allocation_required")
    cache_high = {}
    for method in sorted({row["method"] for row in cache}):
        rows = [row for row in cache if row["method"] == method and row["budget"] == "100000"]
        need(len(rows) == 66, "complete_high_allowance_cache_profiles_required")
        cache_high[method] = {"profiles": 66, "certified": sum(row["certified"] == "True" for row in rows),
            "work_units": sum(int(row["work_units"]) for row in rows),
            "proof_bytes": sum(int(row["proof_bytes"]) for row in rows if row["certified"] == "True"),
            "prefix_hits": sum(int(row["prefix_cache_hits"]) for row in rows),
            "relation_hits": sum(int(row["relation_cache_hits"]) for row in rows)}
    codec = document("docs/research/refutation-prefix-dag-comparison-v2.json")
    need(codec["all_exact_round_trips"] is True and codec["selected_unsupported_certificate_count"] == len(codec["rows"]) == 26,
         "complete_codec_subset_required")
    codec_rows = []
    for row in codec["rows"]:
        original = raw_high[row["case_id"]]["algorithms"]["shared_lift"]
        direct = raw_high[row["case_id"]]["algorithms"]["direct_pruned"]
        need(conclusive(original) and conclusive(direct)
             and original["execution"]["result"]["decision"] == direct["execution"]["result"]["decision"] == "unsupported",
             "codec_case_not_same_conclusive_negative_subset")
        for arm, prefix in ((original, "old"), (direct, "direct")):
            raw = canonical(arm["execution"]["result"]["certificate"])
            need(len(raw) == row[prefix + "_bytes"] and hashlib.sha256(raw).hexdigest() == row[prefix + "_certificate_sha256"],
                 "original_or_direct_codec_certificate_identity_differs")
        need(row["restored_certificate_sha256"] == row["old_certificate_sha256"]
             and row["exact_ordered_object_and_canonical_byte_round_trip"] is True
             and row["new_semantic_checker_call"] is False, "codec_roundtrip_scope_differs")
        codec_rows.append(row)
    codec_groups = {}
    for name, rows in (("all_26", codec_rows), ("excluding_scale_0031", [row for row in codec_rows if row["case_id"] != "scale-0031"]),
                      ("excluding_both_shrinking_cases", [row for row in codec_rows if row["case_id"] not in {"scale-0031", "scale-0023"}])):
        old, dag, direct = (sum(row[key + "_bytes"] for row in rows) for key in ("old", "dag", "direct"))
        codec_groups[name] = {"cases": len(rows), "old_bytes": old, "dag_bytes_inherited_from_bound_codec_receipt": dag,
            "direct_bytes": direct, "dag_minus_old_bytes": dag - old, "dag_minus_direct_bytes": dag - direct,
            "dag_smaller_than_old_cases": sum(row["dag_bytes"] < row["old_bytes"] for row in rows),
            "dag_smaller_than_direct_cases": sum(row["dag_bytes"] < row["direct_bytes"] for row in rows)}
    full_shared = budgets[-1]["method_totals"]["shared_lift"]["proof_bytes"]
    full_direct = budgets[-1]["method_totals"]["direct_pruned"]["proof_bytes"]
    composed = full_shared - codec_groups["all_26"]["old_bytes"] + codec_groups["all_26"]["dag_bytes_inherited_from_bound_codec_receipt"]
    all_proofs = {"accepted_profiles": 54, "original_shared_all_proof_bytes": full_shared,
        "composed_bytes_if_all_26_negative_proofs_use_retained_DAG_sizes": composed, "direct_all_proof_bytes": full_direct,
        "composed_minus_direct_bytes": composed - full_direct, "arithmetic_composition_not_new_encoded_run": True}
    audit_base = "runs/common-cost-development/v1/read-audit-42927208534-3/"
    audit = document(audit_base + "result.json")
    need(audit["status"] == "passed_read_only_archive_receipt_and_physical_cost_audit", "prior_physical_cost_audit_not_passed")
    raw = read(audit_base + "cells.jsonl")
    exported = next(row for row in audit["exports"] if row["path"] == "cells.jsonl")
    need({"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()} == {key: exported[key] for key in ("bytes", "sha256")},
         "physical_cells_not_bound_to_prior_audit")
    cells = [json.loads(line) for line in raw.splitlines()]
    need(len(cells) == len({row["cell"]["id"] for row in cells}) == 1650, "all_physical_allocations_required")
    grouped = defaultdict(list)
    for row in cells:
        grouped[(row["cell"]["profile_id"], row["cell"]["method_id"])].append(row)
    methods = sorted({key[1] for key in grouped})
    need(len(grouped) == 330 and len(methods) == 5, "all_five_methods_and_66_profiles_required")
    for rows in grouped.values():
        need({row["cell"]["repeat"] for row in rows} == {0, 1, 2, 3, 4}
             and {row["cell"]["position"] for row in rows} == {0, 1, 2, 3, 4}, "balanced_five_repeat_position_coverage_required")
    eligible, unknown = [], []
    profiles = sorted({key[0] for key in grouped})
    physical_rows = []
    for profile in profiles:
        every = [row for method in methods for row in grouped[(profile, method)]]
        valid = all(row["status"] == "certified" and row["certificate_valid"] is True
            and row["independent_solver_logical_cap_nonbinding"] is True
            and row["cpu_limit_nonbinding_from_lifetime_observation"] is True
            and row["wall_limit_nonbinding_from_outer_observation"] is True for row in every)
        if not valid:
            need(all(row["status"] == "unknown" for row in every), "excluded_physical_profile_not_uniform_unknown")
            unknown.append(profile)
            continue
        need(len({row["decision"] for row in every}) == 1, "physical_profile_decision_contradiction")
        eligible.append(profile)
        item = {"profile_id": profile, "family": families[profile], "decision": every[0]["decision"], "dependent_repeats": 5}
        for metric in METRICS:
            shared = median(row["resources"][metric] for row in grouped[(profile, "shared_lift")])
            direct = median(row["resources"][metric] for row in grouped[(profile, "goal_pruned_direct")])
            need(shared > 0 and direct > 0, "positive_physical_cost_required")
            item[metric] = {"shared_median": shared, "direct_median": direct, "shared_over_direct": shared / direct}
        physical_rows.append(item)
    need(len(eligible) == 54 and len(unknown) == 12, "fixed_physical_eligible_and_unknown_profiles_required")
    physical_groups = {}
    for family in ("all_eligible", *sorted(set(families.values()))):
        rows = physical_rows if family == "all_eligible" else [row for row in physical_rows if row["family"] == family]
        if not rows:
            continue
        physical_groups[family] = {"profiles": len(rows), "descriptive_only": True,
            "metrics": {metric: {"median_shared_over_direct": median(row[metric]["shared_over_direct"] for row in rows),
                "minimum": min(row[metric]["shared_over_direct"] for row in rows), "maximum": max(row[metric]["shared_over_direct"] for row in rows),
                "shared_lower": sum(row[metric]["shared_over_direct"] < 1 for row in rows),
                "equal": sum(row[metric]["shared_over_direct"] == 1 for row in rows),
                "shared_higher": sum(row[metric]["shared_over_direct"] > 1 for row in rows)} for metric in METRICS}}
    read(Path(__file__).relative_to(ROOT).as_posix())
    value = {"schema_version": "method-contribution-focused-retained-reanalysis/1", "status": "passed_focused_retained_arithmetic_checks",
        "created_utc": datetime.now(timezone.utc).isoformat(), "core_budgets": budgets, "cache_high_allowance_totals": cache_high,
        "codec_subset_sensitivity": codec_groups, "codec_all_accepted_proof_arithmetic": all_proofs,
        "physical_allocation_statuses": dict(Counter(row["status"] for row in cells)),
        "physical_eligible_profiles": eligible, "physical_unknown_profiles_excluded_from_ratios": unknown,
        "physical_shared_over_direct_descriptive_groups": physical_groups, "physical_per_profile": physical_rows,
        "input_identities": list(BINDINGS.values()), "new_solver_codec_checker_application_SDK_provider_or_worker_executions": 0,
        "fresh_semantic_validation_claimed": False, "human_review_claimed": False, "percentage_credit_claimed": False,
        "limits": ["Uses unchanged retained method outputs and prior audited physical-cell exports; it is not a fresh capture authenticity audit or semantic checker run.",
            "DAG encoded bytes/roundtrip outcomes are inherited from the exact bound codec receipt; original and direct proof bytes/hashes are freshly checked.",
            "Excluding stress/shrinking cases is a disclosed post hoc descriptive sensitivity, not a revised primary denominator or population inference.",
            "Five physical repeats are dependent and profiles are related authored development cases; no inference interval or general speed ranking is produced."]}
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": value["status"], "core_profiles_per_budget": 66, "physical_allocations": 1650,
        "codec_negative_cases": 26, "new_solver_or_provider_calls": 0}))


if __name__ == "__main__":
    main()
