"""Independently reconstruct retained phase/profile costs; stdlib reads only."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "runs/common-cost-development/v1"
PHASE_NAMES = ("profile_source_load_and_guard", "solver_import_and_evaluate", "solver_result_serialization", "independent_checker_import_and_check", "solver_result_output")
METHODS = ("goal_pruned_direct", "original_refinement", "shared_lift")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reconstruct():
    exported_path = BASE / "read-audit-42927208534-3/cells.jsonl"
    audit = read(exported_path.with_name("result.json"))
    exported_identity = next(r for r in audit["exports"] if r["path"] == "cells.jsonl")
    assert digest(exported_path) == exported_identity["sha256"] and exported_path.stat().st_size == exported_identity["bytes"]
    cells = [json.loads(line) for line in exported_path.read_text(encoding="utf-8").splitlines()]
    assert len(cells) == 1650
    raw, raw_files = {}, 0
    for exported in cells:
        identity = exported["cell"]
        path = BASE / "retained-42927208534-1/extracted/cells" / identity["id"]
        indexed = {Path(r["path"]).name: r for r in exported["retained_raw_files"]}
        for name in ("after.json", "reply.json"):
            source = path / name
            assert digest(source) == indexed[name]["sha256"] and source.stat().st_size == indexed[name]["bytes"]
            raw_files += 1
        after, reply = read(path / "after.json"), read(path / "reply.json")
        assert after["cell"] == reply["cell"] == identity
        assert after["phase_resources"] == reply["phase_resources"] == exported["phase_resources"]
        assert after["resources"] == exported["resources"]
        assert after["status"] == exported["status"] and after["certificate_valid"] == exported["certificate_valid"]
        for phase in after["phase_resources"].values():
            assert all(type(phase[k]) is int and phase[k] >= 0 for k in ("cpu_ns", "wall_ns"))
        key = (identity["profile_id"], identity["method_id"], identity["repeat"])
        assert key not in raw
        raw[key] = after
    all_profiles = sorted({key[0] for key in raw})
    profiles = []
    for profile in all_profiles:
        cells_for_profile = [raw[profile, method, repeat] for method in METHODS for repeat in range(5)]
        if all(r["status"] == "certified" and r["certificate_valid"] is True for r in cells_for_profile):
            profiles.append(profile)
    assert len(profiles) == 54
    phases, physical, per_profile_physical = {}, {}, []
    for method in METHODS:
        records = []
        for profile in profiles:
            attempts = [raw[profile, method, repeat] for repeat in range(5)]
            row = {"profile_id": profile}
            for phase in PHASE_NAMES:
                row[phase] = {clock: median(a["phase_resources"][phase][clock] for a in attempts) for clock in ("cpu_ns", "wall_ns")}
            row["full_child_cpu_ns"] = median(a["resources"]["cpu_total_ns"] for a in attempts)
            row["full_minus_recorded_phase_cpu_ns"] = median(a["resources"]["cpu_total_ns"] - sum(a["phase_resources"][p]["cpu_ns"] for p in PHASE_NAMES) for a in attempts)
            records.append(row)
        phases[method] = {"profile_count": 54, "per_profile": records,
                          "descriptive_median_across_profile_phase_medians": {p: {clock: median(r[p][clock] for r in records) for clock in ("cpu_ns", "wall_ns")} for p in PHASE_NAMES},
                          "median_full_child_cpu_ns": median(r["full_child_cpu_ns"] for r in records),
                          "median_full_minus_recorded_phase_cpu_ns": median(r["full_minus_recorded_phase_cpu_ns"] for r in records)}
    for profile in profiles:
        row = {"profile_id": profile}
        for field in ("cpu_total_ns", "outer_wall_ns", "peak_rss_bytes"):
            goal = median(raw[profile, "goal_pruned_direct", repeat]["resources"][field] for repeat in range(5))
            original = median(raw[profile, "original_refinement", repeat]["resources"][field] for repeat in range(5))
            row[field] = {"goal_median": goal, "original_median": original, "original_over_goal_ratio": original / goal}
        per_profile_physical.append(row)
    for field in ("cpu_total_ns", "outer_wall_ns", "peak_rss_bytes"):
        ratios = [r[field]["original_over_goal_ratio"] for r in per_profile_physical]
        physical[field] = {"median_original_over_goal_pruned_direct": median(ratios), "observed_profile_ratio_min": min(ratios), "observed_profile_ratio_max": max(ratios), "original_lower_equal_higher": [sum(r < 1 for r in ratios), sum(r == 1 for r in ratios), sum(r > 1 for r in ratios)]}
    audited_profiles = {r["profile_id"]: r for r in audit["paired_profile_costs"]["goal_pruned_direct__original_refinement"]["per_profile"]}
    assert set(audited_profiles) == set(profiles)
    for row in per_profile_physical:
        for field in ("cpu_total_ns", "outer_wall_ns", "peak_rss_bytes"):
            assert audited_profiles[row["profile_id"]][field]["left_median"] == row[field]["goal_median"]
            assert audited_profiles[row["profile_id"]][field]["right_median"] == row[field]["original_median"]
    return phases, physical, per_profile_physical, raw_files


def compare(result, phases, physical):
    assert result["allocated_cells_retained"] == 1650 and result["comparison_profiles"] == 54 and result["paired_repeats"] == 5
    assert result["physical_original_vs_goal_pruned_direct"] == physical
    assert set(result["phase_description"]) == set(METHODS)
    for method in METHODS:
        expected = phases[method]
        actual = deepcopy(result["phase_description"][method])
        actual["per_profile"] = sorted(actual["per_profile"], key=lambda r: r["profile_id"])
        assert actual == expected
    assert result["new_solver_checker_application_or_provider_calls"] == 0


def main():
    path = BASE / "phase-description-v1/result.json"
    result = read(path)
    phases, physical, per_profile, raw_files = reconstruct()
    compare(result, phases, physical)
    controls = []
    for name, mutate in (
        ("changed_original_profile_cpu_refused", lambda r: r["phase_description"]["original_refinement"]["per_profile"][0]["solver_import_and_evaluate"].update(cpu_ns=1)),
        ("changed_original_goal_ratio_refused", lambda r: r["physical_original_vs_goal_pruned_direct"]["cpu_total_ns"].update(median_original_over_goal_pruned_direct=1)),
        ("dropped_phase_profile_refused", lambda r: r["phase_description"]["shared_lift"]["per_profile"].pop()),
    ):
        modified = deepcopy(result)
        mutate(modified)
        try:
            compare(modified, phases, physical)
        except AssertionError:
            controls.append(name)
        else:
            raise AssertionError(name + " unexpectedly accepted")
    output = path.with_name("independent-phase-review-v1.json")
    assert not output.exists()
    review = {"schema_version": "independent-retained-cost-phase-review/1", "status": "all_original_goal_cost_and_phase_rows_verified", "allocated_cells": 1650, "raw_after_reply_files_verified": raw_files, "profiles": 54, "paired_repeats": 5,
              "phase_profile_records_verified": 162, "physical_original_vs_goal_pruned_direct": physical, "per_profile_original_goal_costs": per_profile,
              "phase_summaries": {m: {k: v for k, v in data.items() if k != "per_profile"} for m, data in phases.items()},
              "constructed_controls_passed": controls, "new_solver_checker_actor_application_or_provider_calls": 0,
              "input_result_sha256": digest(path), "reviewer_source_sha256": digest(Path(__file__)),
              "limits": result["limits"], "interpretation": "Original full-worker CPU and wall are lower on53/54 profiles; shared lifting retains an adverse cost result. Phase import+evaluation/checking and about40-42ms unassigned lifetime CPU are descriptive, not warmed-process cost or causal attribution."}
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(review, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in review.items() if k not in {"per_profile_original_goal_costs", "phase_summaries", "limits"}}))


if __name__ == "__main__":
    main()
