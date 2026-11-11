"""Validate proposals, evidence binding, exposure and preserved study coverage.

Stdlib-only review-artifact validator; never runs original actors/models or
supplies semantic human gold. Mutation controls are in-memory and do not edit
retained evidence.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
ARCHIVES = {
    "runs/ci-agentops-governed-app-reference-v4/retained-42887519756-1/artifact.zip": (27792865, "41b53dda0102e3f9cbea573b67b16cf053fd0615f7a71f36ad5202f444c3fcb4"),
    "runs/ap2-original-shopper-development/v7/retained-42886479185-1/artifact.zip": (40154700, "a0177b17d698f3d279537d938761dc125f9edb24a5796d869bf64e89cf087d8b"),
}


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object, parse_constant=lambda value: (_ for _ in ()).throw(Invalid(f"non-finite JSON number: {value}")))


def jsonl(path):
    return [json.loads(line, object_pairs_hook=unique_object) for line in path.read_text(encoding="utf-8").splitlines() if line]


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(256 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def pointer(value, path):
    require(path == "" or path.startswith("/"), "invalid JSON pointer")
    for component in path.split("/")[1:]:
        component = component.replace("~1", "/").replace("~0", "~")
        value = value[int(component)] if isinstance(value, list) else value[component]
    return value


def validate(bundle, root=ROOT):
    checks, verified = [], {}
    def mark(name):
        checks.append(name)
    def bound(item):
        name = item["path"]
        relative = PurePosixPath(name)
        require(not relative.is_absolute() and ".." not in relative.parts and ":" not in name and "\\" not in name, "binding path escapes workspace")
        target = (root / Path(name)).resolve()
        require(target.is_relative_to(root.resolve()), "binding resolved outside workspace")
        if name not in verified:
            require(target.is_file(), f"missing evidence: {name}")
            verified[name] = (target.stat().st_size, digest(target))
        require(type(item["bytes"]) is int and item["bytes"] == verified[name][0] and item["sha256"] == verified[name][1], f"changed bound evidence: {name}")
        return pointer(read(target), item["json_pointer"]) if item.get("json_pointer") else None

    public = bundle["application.json"]["records"]
    private = bundle["evaluator-private.json"]["records"]
    require(bundle["evaluator-private.json"]["gold_status"] == "proposed_not_validated", "private envelope gold promoted")
    table = bundle["candidate-table.json"]
    rows = table["records"]
    plans = bundle["next-reference-plan.json"]
    allocation = bundle["study-allocation.json"]
    originals, evaluators = {}, {}
    for domain in ("agentops", "ap2"):
        app = read(root / f"benchmark/tasks-v1/{domain}/application.json")
        ev = read(root / f"benchmark/tasks-v1/{domain}/evaluator.json")
        originals.update({r["id"]: (domain, r) for r in app["records"]})
        evaluators.update({r["id"]: r for r in ev["records"]})
    ids = set(originals)
    for label, records in (("public", public), ("private", private), ("qualification", rows), ("next reference", plans["records"])):
        require(len(records) == 68 and {r["id"] for r in records} == ids, f"{label} lost/duplicated candidates")
    mark("all_68_candidates_preserved_in_every_projection")
    require(dict(collections.Counter(r["split"] for r in public)) == {"development": 12, "calibration": 8, "held_out": 48}, "split counts changed")
    for record in public:
        domain, original = originals[record["id"]]
        require(set(record) == {"id", "domain", "split", "template_family", "public"}, "evaluator field leaked into public row")
        require(record == {"id": original["id"], "domain": domain, "split": original["split"], "template_family": original["template_family"], "public": original["public"]}, "public task/fixture changed or gold leaked")
    mark("exact_public_projection_and_no_evaluator_leakage")
    notes = read(root / "benchmark/qualification-v1/candidate-notes.json")
    pmap = {r["id"]: r for r in private}
    citation_files = {}
    for record in private:
        case_id = record["id"]
        original = evaluators[case_id]
        domain = originals[case_id][0]
        key = case_id.split("-", 2)[1] if domain == "agentops" else case_id.removeprefix("ap2-")
        require(record["gold_status"] == "proposed_not_validated" and record["human_review"] == "not_reviewed", "unsupported gold/review promotion")
        require(record["proposed_answer"] == notes[domain][key][0] and len(record["proposed_answer"]) > 20, "missing or changed concrete proposed answer")
        require(record["answer_contract"] == {k: original[k] for k in ("expected_facts", "expected_order", "expected_state", "reset", "legitimate_alternatives", "near_misses")}, "source answer/alternative/near-miss obligation changed")
        require(record["source_refs"] == original["source_refs"], "source refs changed")
        require(bound(record["source_record_binding"]) == original, "source evaluator join mismatch")
        for ref in record["source_refs"].values():
            name = ref["path"]
            if name not in citation_files:
                path = root / name
                require(digest(path) == ref["sha256"], f"source citation hash mismatch: {name}")
                citation_files[name] = len(path.read_text(encoding="utf-8").splitlines())
            start, end = ref["lines"]
            require(type(start) is int and type(end) is int and 1 <= start <= end <= citation_files[name], "source citation range invalid")
            require(ref["sha256"] == digest(root / name), "conflicting citation hashes")
    mark("all_68_concrete_proposed_answers_and_original_source_obligations_bound")
    for item in table["inputs"]:
        bound(item)
    for name, expected in ARCHIVES.items():
        require(name in verified and verified[name] == expected, f"original retained archive mismatch: {name}")
    mark("original_two_retained_archive_identities_and_all_input_bindings")
    ag_path = root / "runs/ci-agentops-governed-app-reference-v4/retained-42887519756-1"
    ap_path = root / "runs/ap2-original-shopper-development/v7/retained-42886479185-1"
    census = {r["case_id"]: r for r in read(ag_path / "independent-raw-state-census-v1.json")["cases"]}
    semantic = {r["case_id"]: r for r in read(ag_path / "independent-semantic-peer-review-v1.json")["cases"]}
    ap_eval = {r["candidate_id"]: r for r in read(ap_path / "extracted/independent-bank-evaluation/result.json")["candidates"]}
    for row in rows:
        case_id = row["id"]
        require(row["qualified"] is False and row["human_review"] == "not_reviewed" and row["gold_status"] == row["near_miss_status"] == "proposed_not_validated", "unsupported task/gold/near-miss promotion")
        require(row["held_out_status"] == "exposed_authoring_and_development_evidence_not_independent_holdout", "authored development relabelled as untouched holdout")
        require(row["route_status"] == "all_three_study_paths_unqualified" and len(row["common_gaps"]) == 4, "technical route/instance/review gap removed")
        original = originals[case_id][1]
        require(row["distinct_obligation"] == original["distinct_obligation"], "candidate scope narrowed")
        domain = originals[case_id][0]
        key = case_id.split("-", 2)[1] if domain == "agentops" else case_id.removeprefix("ap2-")
        require(row["next_reference_check"] == notes[domain][key][1], "candidate-specific next check missing")
        for item in row["reference"]["peer_bindings"]:
            bound(item)
        if domain == "agentops":
            c, s = census[case_id], semantic[case_id]
            raw = row["reference"]["raw_summary"]
            require(row["reference"]["historical_mechanical_status"] == c["retained_mechanical_status"] and row["reference"]["failed_checks"] == c.get("preserved_failed_checks", []), "historical failed/partial classification changed")
            require(row["reference"]["semantic_status"] == s["semantic_disposition"], "semantic limit removed")
            expected = {"observed_reference_recipe": "fixed_reference_obligation_observed", "observed_partial_reference_recipe": "partial_case", "unsupported_public_recipe": "bounded_unsupported_workflow", "checks_failed": "failed_reference_checks"}[c["retained_mechanical_status"]]
            if case_id == "agentops-d03-restart-pause":
                expected = "partial_decision_preconditions"
                require(any("understood cause" in g for g in row["candidate_specific_gaps"]), "d03 unsupported decision promoted")
            require(row["disposition"] == expected, "candidate disposition inflated")
            for item in raw["evidence"]:
                bound(item)
            require(len(raw["tasks"]) == c["observed_SDK_tasks"], "raw task denominator changed")
            if expected == "bounded_unsupported_workflow":
                require(raw["tasks"] == [] and raw["business_state_unchanged"] is None, "unexecuted workflow treated as unchanged execution")
            else:
                before, after = [read(ag_path / "extracted" / case_id / f"state-{name}.json") for name in ("before", "after")]
                require(raw["business_state_unchanged"] is (before["incidents.db"] == after["incidents.db"]), "business-state summary mismatch")
                contexts = jsonl(ag_path / "extracted" / case_id / "tool-contexts.jsonl")
                require(raw["actual_tool_calls"] == contexts, "raw actual tool/context summary changed")
                for task in raw["tasks"]:
                    actual = read(ag_path / "extracted" / case_id / f"turn-{task['turn']}" / "task-get.response.raw.json")["result"]
                    text = [p["text"] for a in actual.get("artifacts") or [] for p in a.get("parts") or [] if p.get("kind") == "text"]
                    require((task["task_id"], task["context_id"], task["state"], task["answer_text"]) == (actual["id"], actual["contextId"], actual["status"]["state"], text), "raw task/answer changed")
        else:
            result = ap_eval[case_id]
            require(row["reference"]["historical_mechanical_status"] == result["disposition"], "AP2 original classification changed")
            expected = {"candidate_source_obligation_observed_pending_human_gold": "fixed_reference_obligation_observed", "candidate_original_reset_pair_obligation_observed": "fixed_reference_reset_pair_observed", "candidate_required_otp_receipt_or_fault_branch_unrealized_after_original_generic_status": "partial_case", "prior_original_sdk_source_boundary_observed_not_new_full_shopper": "boundary_only"}[result["disposition"]]
            require(row["disposition"] == expected, "AP2 unrealized/boundary task inflated")
            require(len(row["reference"]["raw_summaries"]) == len(result.get("processes", [])), "AP2 process denominator changed")
            if expected == "boundary_only":
                require(row["execution_class"] == "original_source_boundary_control" and row["reference"]["prior_source_boundary_observation"] == result["prior_case"], "boundary control replaced full shopper or prior observation changed")
                bound(row["reference"]["raw_prior_binding"])
                prior = read(ap_path / "extracted/bank/prior-source-boundary-actor-output.json")
                require(next(c for c in prior["cases"] if c["id"] == case_id) == row["reference"]["prior_source_boundary_observation"] and prior["full_shopper_workflow_completed"] is False, "linked boundary raw observation mismatch")
            for raw in row["reference"]["raw_summaries"]:
                for item in raw["evidence"]:
                    bound(item)
                path = ap_path / "extracted/bank/cells" / raw["process_id"]
                events = jsonl(path / "original-adk-events.jsonl")
                calls = [p["functionCall"] for e in events for p in (e.get("content") or {}).get("parts") or [] if p.get("functionCall") and p["functionCall"]["name"] != "transfer_to_agent"]
                outcome = read(path / "shopper-outcome.json")
                state = read(path / "caller-final-state.json")
                require(raw["official_adk_events"] == len(events) and raw["actual_original_tool_order"] == [c["name"] for c in calls], "AP2 raw event/tool sequence mismatch")
                require(raw["actual_payment_tool_return"] == outcome["original_payment_tool_return"] and raw["terminal_reason"] == outcome["terminal_reason"], "AP2 generic status boundary rewritten")
                require(raw["otp_calls"] == sum(c["name"] == "initiate_payment_with_otp" for c in calls) == 0 and raw["original_purchase_observed"] is False and state.get("payment_receipt") is None, "AP2 unobserved continuation/purchase credited")
        require(row["disposition"].startswith("fixed_reference") or row["candidate_specific_gaps"], "explicit failed/partial/unsupported gap missing")
    mark("every_candidate_raw_outcome_and_semantic_limit_preserved")
    require(table["disposition_counts"] == dict(collections.Counter(r["disposition"] for r in rows)), "disposition aggregate mismatch")
    require(plans["provider_calls_allowed"] == 0 and type(plans["provider_calls_allowed"]) is int and plans["dispatch_allowed"] is False and plans["new_allocations_authorized_by_this_file"] is False, "plan authorizes unrequested execution")
    for plan in plans["records"]:
        require(plan["execution_allowed"] is False and plan["allocation"] is None and plan["requires_owner_coordination_before_new_allocation"] is True and plan["public_record_id"] == plan["expected_answer_record_id"] == plan["id"], "uncoordinated allocation or evaluator/public mismatch")
    mark("next_reference_harness_is_plan_only_no_model_calls_or_allocations")
    expected_scope = {"original_candidates": 68, "split_counts": {"development": 12, "calibration": 8, "held_out": 48}, "held_out_task_slots": 96, "path_cells": 288, "additional_crossing_cells": 96, "initial_episode_slots": 384, "qualified_tasks": 0, "independent_held_out_tasks": 0, "allocation_is_executable_study": False}
    for name, expected in expected_scope.items():
        require(table["scope"].get(name) == expected and allocation["scope"].get(name) == expected and type(table["scope"].get(name)) is type(expected) and type(allocation["scope"].get(name)) is type(expected), f"original scope changed: {name}")
    held = {r["id"] for r in public if r["split"] == "held_out"}
    expected_instances = {(candidate, ordinal) for candidate in held for ordinal in (1, 2)}
    second_public = bundle.get("second-instance-application.json")
    second_map = {}
    if second_public:
        second_private = bundle["second-instance-evaluator-private.json"]
        second_checks = bundle["second-instance-source-checks.json"]
        for artifact in (second_public, second_private, second_checks):
            require(artifact["second_instance_slots"] == artifact["template_families"] == 48 and artifact["source_recipe_authored"] == 25 and artifact["specific_refusals"] == 23 and artifact["qualified_instances"] == artifact["new_original_calls"] == 0, "second-instance counts or qualification changed")
        second_map = {r["candidate_id"]: r for r in second_public["records"]}
        second_gold = {r["candidate_id"]: r for r in second_private["records"]}
        require(len(second_public["records"]) == len(second_private["records"]) == len(second_checks["checks"]) == 48 and set(second_map) == set(second_gold) == held, "second-instance candidate/family denominator changed")
        allowed_agent = {"h01", "h02", "h03", "h04", "h05", "h06", "h07", "h08", "h11", "h12", "h17", "h19", "h22"}
        allowed_ap = {f"ho-{number:03}" for number in (1, 2, 3, 4, 5, 6, 19, 20, 21, 22, 23, 24)}
        for candidate, second in second_map.items():
            original_domain, original = originals[candidate]
            key = candidate.split("-", 2)[1] if original_domain == "agentops" else candidate.removeprefix("ap2-")
            expected_authored = key in (allowed_agent if original_domain == "agentops" else allowed_ap)
            require(set(second) == {"id", "candidate_id", "domain", "template_family", "instance_ordinal", "qualified", "execution_allowed", "status", "public", "specific_blocker"} | ({"variation"} if expected_authored else set()), "private answer leaked into second public instance")
            require(second["template_family"] == original["template_family"] and second["id"] == candidate + "--instance-2" and second["instance_ordinal"] == 2 and second["qualified"] is False and second["execution_allowed"] is False, "second instance relabelled template/qualified")
            gold = second_gold[candidate]
            require(gold["gold_status"] == "proposed_not_validated" and gold["qualified"] is False, "second-instance human gold promoted")
            require((second["public"] is not None) is expected_authored, "unsupported/unrealized second recipe invented")
            if expected_authored:
                require(second["status"] == "second_source_bound_candidate_recipe_authored" and second["specific_blocker"] is None and isinstance(gold["proposed_answer"], str), "authored second instance incomplete")
                require(second["public"] != original["public"], "same recipe replay counted as new instance")
            else:
                require(second["status"] == "second_instance_refused_pending_original_obligation" and gold["proposed_answer"] is None and second["specific_blocker"] == gold["specific_blocker"] and len(second["specific_blocker"]) > 20, "refused second instance lacks explicit blocker")
            for ref in gold["source_refs"].values():
                path = root / ref["path"]
                require(digest(path) == ref["sha256"], "second-instance source citation changed")
                start, end = ref["lines"]
                require(1 <= start <= end <= len(path.read_text(encoding="utf-8").splitlines()), "second-instance source citation range invalid")
        require(sum(r["public"] is not None for r in second_map.values()) == 25, "25 source-compatible second recipes changed")
        for name in ("second-instance-application.json", "second-instance-evaluator-private.json", "second-instance-source-checks.json"):
            source_binding = next(item for item in table["inputs"] if item["path"].endswith("/" + name))
            require(bundle[name] == read(root / source_binding["path"]), "second-instance proposal copy differs from bound source proposal")
        mark("all_48_second_slots_resolved_as_25_source_recipes_and_23_specific_refusals")
    slots = allocation["task_slots"]
    require(len(slots) == 96 and {(s["candidate_id"], s["instance_ordinal"]) for s in slots} == expected_instances and len({s["id"] for s in slots}) == 96, "96 task slots missing/duplicated")
    for slot in slots:
        require(slot["qualified"] is False and slot["execution_allowed"] is False, "unqualified task slot made executable")
        if slot["instance_ordinal"] == 2 and second_map:
            second = second_map[slot["candidate_id"]]
            require(slot["recipe_status"] == second["status"] and slot["specific_blocker"] == second["specific_blocker"] and slot["public_record_id"] == (second["id"] if second["public"] is not None else None), "second-instance recipe/refusal allocation mismatch")
        else:
            require(slot["recipe_status"] == ("authored_base_recipe_pending_independent_review" if slot["instance_ordinal"] == 1 else "second_source_bound_instance_recipe_not_authored"), "missing second instance silently replaced by replay")
            require(slot["public_record_id"] == (slot["candidate_id"] if slot["instance_ordinal"] == 1 else None), "second instance invented")
    paths = {"native_reference", "independent_bridge_1", "independent_bridge_2"}
    cells = allocation["path_cells"]
    require(len(cells) == 288 and {(c["instance_id"], c["path"]) for c in cells} == {(s["id"], p) for s in slots for p in paths}, "288 path cells collapsed")
    require(all(c["route_binding"] is None and c["crossing_placement"] is None and c["execution_allowed"] is False for c in cells), "unsupported bridge placement invented")
    subset = allocation["crossing_subset_slots"]
    require(len(subset) == 24 and len({s["id"] for s in subset}) == 24 and all(s["instance_id"] is None for s in subset), "crossing subset altered or selected after outcomes")
    crossings = allocation["crossing_cells"]
    require(len(crossings) == 96 and {(c["subset_slot"], c["path"], c["crossing_count"]) for c in crossings} == {(s["id"], p, n) for s in subset for p in paths - {"native_reference"} for n in (2, 3)}, "96 crossing cells collapsed")
    require(all(c["execution_allowed"] is False and c["composed_route_binding"] is None for c in crossings), "unqualified composed route made executable")
    mark("original_96_tasks_288_paths_96_crossings_preserved_with_explicit_gaps")
    return {"schema_version": "candidate-qualification-validation/1", "status": "passed_structural_source_retained_evidence_validation", "checks": checks, "checks_passed": len(checks), "source_files_checked": len(citation_files), "bound_files_checked": len(verified), "candidates": 68, "qualified_tasks": 0, "human_review": False, "new_original_calls": 0,
            "limits": ["Concrete proposed answers, alternatives and near misses remain AI-authored and human-unreviewed.", "This validator checks retained text/JSON and source binding, not experimental semantic gold or route qualification.", "96 slots preserve the original study; second-instance original references and all route/crossing bindings remain technical work."]}


def load_bundle(directory):
    bundle = {name: read(directory / name) for name in ("application.json", "evaluator-private.json", "candidate-table.json", "next-reference-plan.json", "study-allocation.json")}
    if (directory / "second-instance-application.json").exists():
        bundle.update({name: read(directory / name) for name in ("second-instance-application.json", "second-instance-evaluator-private.json", "second-instance-source-checks.json")})
    return bundle


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--proposal-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="Fresh audit JSON file")
    args = parser.parse_args()
    require(not args.output.exists(), "audit output already exists; refusing overwrite")
    result = validate(load_bundle(args.proposal_dir))
    result["validator_source_sha256"] = digest(Path(__file__).resolve())
    result["builder_source_sha256"] = digest(Path(__file__).resolve().with_name("build_qualification_v1.py"))
    result["second_instance_builder_source_sha256"] = digest(Path(__file__).resolve().with_name("build_second_instances_v1.py"))
    artifact_names = ["application.json", "evaluator-private.json", "candidate-table.json", "next-reference-plan.json", "study-allocation.json"]
    if (args.proposal_dir / "second-instance-application.json").exists():
        artifact_names += ["second-instance-application.json", "second-instance-evaluator-private.json", "second-instance-source-checks.json"]
    result["artifacts"] = [{"path": (args.proposal_dir / name).as_posix(), "sha256": digest(args.proposal_dir / name)} for name in artifact_names]
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
