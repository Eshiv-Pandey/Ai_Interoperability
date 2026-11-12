"""Fail-closed checks for the retained original-study readiness checkpoint.

Only stdlib JSON/text/hash reads are performed. Passing this validator is not
semantic gold validation, human review, route qualification, or permission to run.
The checker is deliberately specific to the current unqualified snapshot.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any


class ReadinessError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReadinessError(message)


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_path(root: Path, name: str) -> Path:
    require(type(name) is str and name and "\\" not in name, "noncanonical input path")
    p = PurePosixPath(name)
    require(not p.is_absolute() and ":" not in name and ".." not in p.parts,
            f"input path escapes workspace: {name}")
    resolved = (root / name).resolve()
    require(resolved.is_relative_to(root.resolve()), f"resolved input escapes workspace: {name}")
    return resolved


def false(value: Any, label: str) -> None:
    require(value is False, f"unqualified flag promoted or mistyped: {label}")


def zero(value: Any, label: str) -> None:
    require(type(value) is int and value == 0, f"zero eligibility count promoted or mistyped: {label}")


def index(records: list[dict[str, Any]], key: str, expected: int) -> dict[str, dict[str, Any]]:
    require(type(records) is list and len(records) == expected, f"wrong {key} record count")
    result = {r[key]: r for r in records}
    require(len(result) == expected, f"duplicate {key} records")
    return result


PROFILES = {
    "agentops_native_confirmation": ("native", None),
    "agentops_amir_B1_B2_B3": ("mcp_client_to_a2a_agent", "AmirK-S/a2a-to-mcp@58eff9da469bccdc432bf164662727947de646b4"),
    "agentops_mg_B4_B5_B6": ("mcp_client_to_a2a_agent", "mgcrea/mcp-a2a@c4d9d3c57c1746abbf9f6aadd3a9912d464eb1f5"),
    "agentops_mg_B7_configured": ("mcp_client_to_a2a_agent", "mgcrea/mcp-a2a@c4d9d3c57c1746abbf9f6aadd3a9912d464eb1f5"),
    "ap2_original_native_scripted_V2": ("native", None),
    "ap2_original_native_shopper_V4": ("native", None),
    "ap2_amir_typed": ("mcp_client_to_a2a_agent", "AmirK-S/a2a-to-mcp@58eff9da469bccdc432bf164662727947de646b4"),
    "ap2_mg_typed_raw": ("mcp_client_to_a2a_agent", "mgcrea/mcp-a2a@c4d9d3c57c1746abbf9f6aadd3a9912d464eb1f5"),
    "ap2_skillmap_source_lead": ("mcp_client_to_a2a_agent", "shashikanth-gs/a2a-mcp-skillmap@f1c6a69174df31c819c862ce72fd2344430dd7d3"),
}


def validate_topology_control(plan: dict[str, Any]) -> dict[str, Any]:
    """Check a prospective four-stage placement grammar, never qualification.

    Each actor would need both source-qualified receiving and sending surfaces.
    Those are not established for the current original Workflow/bridges. A
    syntactically supported outgoing edge does not imply an inverse converter.
    """
    false(plan["execution_allowed"], "topology execution")
    false(plan["original_stage_surfaces_qualified"], "original stage surfaces")
    stages = plan["stage_ids"]
    require(type(stages) is list and len(stages) == 4 and len(set(stages)) == 4,
            "minimal topology needs four distinct fixed stages")
    require(type(plan["horizon"]) is int and plan["horizon"] > 0, "invalid fixed horizon")
    require(plan["task_id"] and plan["initial_state_sha256"], "task/state must be bound")
    variants = plan["variants"]
    require(len(variants) == 3 and {v["crossing_count"] for v in variants} == {1, 2, 3},
            "preserve one/two/three paired counts")
    for variant in variants:
        edges = variant["edges"]
        require(len(edges) == 3, "four stages need three ordered edges")
        actual = 0
        for i, edge in enumerate(edges):
            require((edge["from_stage"], edge["to_stage"]) == (stages[i], stages[i + 1]),
                    "placement changes fixed stage order")
            if edge["delivery"] == "reference":
                require(edge.get("profile_id") is None, "reference edge must not smuggle bridge")
                continue
            require(edge["delivery"] == "bridge", "unknown delivery")
            profile = edge["profile_id"]
            require(profile in PROFILES and PROFILES[profile][0] == "mcp_client_to_a2a_agent",
                    "unregistered or non-bridge profile")
            require(profile == plan["profile_id"], "paired variants change converter")
            require(edge["from_surface"] == "mcp_client" and edge["to_surface"] == "a2a_agent",
                    "unsupported inverse or changed bridge direction")
            actual += 1
        require(type(variant["crossing_count"]) is int and actual == variant["crossing_count"],
                "crossing count differs from actual placements")
    return {"placement_grammar_valid": True, "original_route_qualified": False,
            "execution_allowed": False, "qualified_crossing_cells": 0}


def validate(root: Path, inventory: dict[str, Any]) -> dict[str, Any]:
    checks: list[str] = []
    require(inventory["schema_version"] == "study-readiness-audit-checkpoint/2", "wrong snapshot schema")
    require(inventory["status"] == "incomplete_post_V1_readiness_checkpoint", "checkpoint completion relabelled")
    bound = index(inventory["exact_input_bindings"], "path", 103)
    for name, item in bound.items():
        path = local_path(root, name)
        require(type(item["bytes"]) is int and item["bytes"] == path.stat().st_size,
                f"bound file length changed: {name}")
        require(item["sha256"] == digest(path), f"bound file hash changed: {name}")
    checks.append("all_103_exact_input_bindings")

    public: dict[str, tuple[str, dict[str, Any], int]] = {}
    gold: dict[str, dict[str, Any]] = {}
    for domain in ("agentops", "ap2"):
        for projection in ("application", "evaluator"):
            name = f"benchmark/tasks-v1/{domain}/{projection}.json"
            require(name in bound, f"bank binding missing: {name}")
            bank = read_json(local_path(root, name))
            rows = index(bank["records"], "id", 34)
            require(collections.Counter(r["split"] for r in rows.values()) ==
                    {"development": 6, "calibration": 4, "held_out": 24}, "bank split allocation changed")
            for i, row in enumerate(bank["records"]):
                if projection == "application":
                    require(row["id"] not in public, "domain candidate overlap")
                    public[row["id"]] = (domain, row, i)
                else:
                    gold[row["id"]] = row
    rows = index(inventory["records"], "id", 68)
    require(set(rows) == set(public) == set(gold), "candidate lost or invented")
    table = read_json(local_path(root, "benchmark/qualification-v1/proposal-2/candidate-table.json"))
    current = index(table["records"], "id", 68)
    mechanical = index(read_json(local_path(root,
        "runs/ci-agentops-governed-app-reference-v4/retained-42887519756-1/extracted/evaluation.json"))["cases"], "case_id", 34)
    historical = index(read_json(local_path(root, "benchmark/tasks-v2/agentops/execution-readiness.json"))["records"], "id", 34)
    source_names: set[str] = set()
    for case_id, row in rows.items():
        domain, original, ordinal = public[case_id]
        expected = current[case_id]
        for field in ("template_family", "distinct_obligation"):
            require(row[field] == original[field], f"candidate obligation changed: {case_id}")
        require(row["domain"] == domain and row["original_split"] == original["split"],
                f"development/holdout relabelling: {case_id}")
        require(row["public_record_binding"] == {"path": f"benchmark/tasks-v1/{domain}/application.json",
                "json_pointer": f"/records/{ordinal}"}, "public source join changed")
        require(row["source_citations"] == gold[case_id]["source_refs"], "source citation removed or changed")
        for ref in row["source_citations"].values():
            path = local_path(root, ref["path"])
            require(ref["path"] in bound and ref["sha256"] == bound[ref["path"]]["sha256"],
                    "unbound or stale source citation")
            start, end = ref["lines"]
            require(type(start) is int and type(end) is int and 1 <= start <= end <=
                    len(path.read_text(encoding="utf-8").splitlines()), "source range invalid")
            source_names.add(ref["path"])
        require(row["execution_class"] == expected["execution_class"] and
                row["retained_semantic_disposition"] == expected["disposition"], "reference or boundary scope promoted")
        require(row["retained_reference_status"] == expected["reference"]["historical_mechanical_status"],
                "historical outcome replaced")
        for field in ("candidate_specific_gaps", "next_reference_control"):
            counterpart = "next_reference_check" if field == "next_reference_control" else field
            require(row[field] == expected[counterpart], f"candidate-specific gap removed: {case_id}")
        require(row["common_unclosed_gates"] == expected["common_gaps"], "review/route/instance gap removed")
        require(row["human_review"] == "not_reviewed" and row["gold_status"] == "proposed_not_validated",
                "AI/numerical review promoted to semantic human gold")
        require(row["holdout_independence"] == "exposed_authoring_and_development_evidence_not_independent_holdout",
                "authored cases promoted to untouched holdout")
        for field in ("qualified_candidate", "confirmatory_execution_eligible", "source_to_model_qualified"):
            false(row[field], f"{case_id}/{field}")
        for field in ("qualified_path_count", "qualified_crossing_placement_count"):
            zero(row[field], f"{case_id}/{field}")
        if domain == "agentops":
            require(row["retained_mechanical_status"] == mechanical[case_id]["status"] and
                    row["retained_failed_checks"] == [c["name"] for c in mechanical[case_id]["checks"] if not c["passed"]] and
                    row["historical_readiness_disposition"] == historical[case_id]["execution_disposition"],
                    "historical preparation/mechanical census changed")
        if case_id in {"agentops-h09-workflow-select-target", "agentops-h10-workflow-override-conflict"}:
            overlay = row["later_development_overlay"]
            false(overlay["qualifies_original_task"], "Workflow final insufficient")
            require(overlay["status"] == "original_direct_ADK_four_stage_execution_observed_but_final_task_insufficient" and
                    overlay["historical_table_preserved"] is True and overlay["source"] in bound and
                    overlay["evidence"] in bound, "later Workflow failure promoted or removed")
        else:
            require("later_development_overlay" not in row, "invented later qualification")
    checks.append("all_68_source_bound_splits_obligations_and_unqualified_semantics")

    second = read_json(local_path(root, "benchmark/qualification-v1/proposal-2/second-instance-application.json"))
    smap = index(second["records"], "candidate_id", 48)
    require(set(smap) == {i for i, (_, r, _) in public.items() if r["split"] == "held_out"}, "second family count changed")
    for case_id, row in rows.items():
        if case_id not in smap:
            require("second_instance" not in row, "development candidate gained held-out instance")
            continue
        original = smap[case_id]
        require(row["second_instance"] == {k: original.get(k) for k in
                ("id", "status", "variation", "specific_blocker", "qualified", "execution_allowed")},
                "second recipe/refusal changed")
    second_gold = read_json(local_path(root, "benchmark/qualification-v1/proposal-2/second-instance-evaluator-private.json"))
    for record in second_gold["records"]:
        for ref in record["source_refs"].values():
            require(ref["path"] in bound and ref["sha256"] == bound[ref["path"]]["sha256"], "second source stale")
            a, b = ref["lines"]
            require(type(a) is int and type(b) is int and 1 <= a <= b <=
                    len(local_path(root, ref["path"]).read_text(encoding="utf-8").splitlines()), "second source range")
            source_names.add(ref["path"])
    require(len(source_names) == 51, "source coverage changed")
    for domain in ("agentops", "ap2"):
        authored = sum(r["domain"] == domain and r["status"] == "second_source_bound_candidate_recipe_authored"
                       for r in second["records"])
        require(inventory["second_instance_counts"][domain] == {"slots": 24, "authored_source_recipes": authored,
                "specific_refusals": 24 - authored, "qualified_instances": 0}, "second instance count inflated")
    require(inventory["source_authored_recipe_counts"] == {"first_held_out_slots": 48, "second_held_out_slots": 25,
            "total_authored_slot_recipes": 73, "boundary_only_authored_slot_recipes": 12,
            "authored_non_boundary_slot_recipes": 61, "qualification_is_not_implied": True}, "recipe totals inflated")
    checks.append("51_source_files_and_25_authored_23_refused_second_slots")

    allocation = read_json(local_path(root, "benchmark/qualification-v1/proposal-2/study-allocation.json"))
    require(inventory["original_allocation"] == allocation["scope"], "original allocation narrowed")
    for stored, original, count in (("planned_task_slots", "task_slots", 96),
            ("planned_base_path_cells", "path_cells", 288), ("planned_crossing_subset_slots", "crossing_subset_slots", 24),
            ("planned_extra_crossing_cells", "crossing_cells", 96)):
        require(inventory[stored] == allocation[original] and len(inventory[stored]) == count,
                f"original allocation or disabled placements changed: {stored}")
    for value in inventory["eligible_confirmatory_counts"].values():
        zero(value, "confirmatory aggregate")
    require(set(inventory["eligible_confirmatory_counts"]) == {"candidates", "held_out_tasks", "base_path_cells",
            "extra_crossing_cells", "independent_held_out_tasks", "human_reviewed_bank_candidates"}, "eligibility denominator removed")
    checks.append("original_96_288_24_96_unqualified_disabled_slots")

    profiles = index(inventory["routes"], "id", 9)
    require(set(profiles) == set(PROFILES), "invented or missing route")
    for name, row in profiles.items():
        require((row["observed_direction"], row["implementation_pin"]) == PROFILES[name], "bridge direction or implementation changed")
        false(row["full_study_qualified"], name)
        require(row["supported_original_study_crossing_placements"] == [], "unqualified crossings promoted")
        require(row["inverse_conversion_established_for_selected_profile"] is
                (None if row["observed_direction"] == "native" else False), "invented inverse converter")
        require(row["evidence_file"] in bound, "route evidence unbound")
    checks.append("pinned_outgoing_profiles_without_invented_inverse_or_crossings")

    for summary in inventory["candidate_counts_by_domain_split"]:
        subset = [r for r in rows.values() if r["domain"] == summary["domain"] and r["original_split"] == summary["original_split"]]
        require(summary["candidates"] == len(subset) and summary["semantic_dispositions"] ==
                dict(collections.Counter(r["retained_semantic_disposition"] for r in subset)) and
                summary["execution_classes"] == dict(collections.Counter(r["execution_class"] for r in subset)),
                "domain/split reference census inflated")
        for field in ("qualified_candidates", "human_reviewed_candidates", "independent_heldout_candidates",
                      "confirmatory_execution_eligible_candidates"):
            zero(summary[field], field)
    require(len(inventory["candidate_counts_by_domain_split"]) == 6 and
            len({(r["domain"], r["original_split"]) for r in inventory["candidate_counts_by_domain_split"]}) == 6,
            "missing domain/split census")
    require(set(inventory["authorization"]) == {"provider_calls", "original_runtime_calls", "experiments_dispatched",
            "git_mutations", "paper_or_global_status_changes", "new_validator_implemented"}, "authorization limits removed")
    for key, value in inventory["authorization"].items():
        false(value, key) if key == "new_validator_implemented" else zero(value, key)
    require(inventory["human_review_scope"]["two_human_bank_review_not_satisfied"] is True and
            inventory["human_review_scope"]["AI_review_not_human_review"] is True, "human-review limits erased")
    require(len(inventory["source_to_model_obligations"]) == 9 and all(r["status"] ==
            "unqualified_for_prescribed_full_study" for r in inventory["source_to_model_obligations"]), "model gaps promoted")
    checks.append("derived_census_zero_eligibility_and_runtime_gold_human_limits")
    return {"schema_version": "study-readiness-validation/2", "status": "passed_snapshot_binding_and_fail_closed_checks",
            "checks": checks, "checks_passed": len(checks), "bound_files": len(bound), "cited_source_files": len(source_names),
            "candidates": len(rows), "qualified_confirmatory_tasks": 0, "qualified_crossing_cells": 0,
            "semantic_gold_validated": False, "human_review": False, "provider_calls": 0, "original_runtime_calls": 0,
            "full_task_oracle_complete": False,
            "limits": "Structural/source-binding qualification only. Original task semantics, human gold, holdout, runtime and crossing qualification remain open."}


def write_exclusive(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "refusing existing validation output")
    result = validate(args.root, read_json(args.inventory))
    result["inventory_sha256"] = digest(args.inventory)
    result["validator_sha256"] = digest(Path(__file__))
    write_exclusive(args.output, result)
    print(json.dumps({"status": result["status"], "checks_passed": result["checks_passed"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
