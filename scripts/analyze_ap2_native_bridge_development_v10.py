"""Analyze a real retained V10 allocation without executing actors or evaluators.

Archive/run/source identities and every allocated cell are checked before any
output is created. A failed smoke can leave 104 missing cells and 65 unresolved
transport pairs; those are retained, not measured task failures.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "Eshiv-Pandey/Ai_Interoperability"
PUBLIC = ROOT / "benchmark/ap2-native-bridge-development-v10/application.json"
ACTOR = ROOT / "scripts/ap2_reference_development_v10.py"
ORCHESTRATOR = ROOT / "scripts/run_ap2_native_bridge_matrix_v10.py"
EVALUATOR = ROOT / "scripts/evaluate_ap2_native_bridge_matrix_v10.py"
PRIVATE = ROOT / "benchmark/ap2-native-bridge-development-v10/evaluator.json"
PREVIOUS = ROOT / "runs/ap2-reference-development/v5/retained-42881390576-2"
PREVIOUS_ARCHIVE_SHA = "7efb2a74e0b6da56613575ed2517ddaee8f37f3c73a5cf58e4789d65e6e273b9"
NATIVE = ("reference", "conventional", "recovery", "shared", "recovery_shared")
BRIDGES = ("amir_typed", "mg_typed", "mg_raw")
ARMS = NATIVE + BRIDGES
VERIFIED_NATIVE = "original_application_capture_verified"
VERIFIED_BRIDGE = "original_bridge_initiation_capture_verified"
MISSING = "missing_or_pre_execution_failure_retained"
PARTIAL = "partial_allocation_capture_unclosed_and_retained"
REFUSED = "independent_evaluation_refused"
STATUSES = {VERIFIED_NATIVE, VERIFIED_BRIDGE, MISSING, PARTIAL, REFUSED}
IDENTITY_KEYS = ("index", "id", "case_id", "arm_id")
POLICY_KEYS = ("id", "recover", "shared_admission", "inspect_public_task", "apply_received_fault")


def need(condition, label):
    if not condition:
        raise ValueError(label)


def parse(raw):
    def unique(pairs):
        value = {}
        for key, child in pairs:
            need(key not in value, "duplicate_JSON_key")
            value[key] = child
        return value

    def nonfinite(value):
        raise ValueError("nonfinite_JSON_value:" + value)

    return json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)


def identity(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def record(path):
    path = Path(path).resolve()
    need(path.is_relative_to(ROOT) and path.is_file(), "workspace_evidence_file_required")
    return {"path": path.relative_to(ROOT).as_posix(), **identity(path.read_bytes())}


def file_identity(path):
    digest, size = hashlib.sha256(), 0
    with Path(path).open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
            size += len(block)
    return {"bytes": size, "sha256": digest.hexdigest()}


def retained_archive(base):
    """Verify saved GitHub metadata and exact API-digest-bound archive bytes."""
    base = Path(base).resolve()
    need(base.is_relative_to(ROOT / "runs") and base.is_dir(), "workspace_retained_base_required")
    run = parse((base / "github-run.json").read_bytes())
    receipt = parse((base / "retention.json").read_bytes())
    need(type(run.get("id")) is int and type(run.get("run_attempt")) is int
         and run["id"] > 0 and run["run_attempt"] > 0 and run["status"] == "completed",
         "actual_completed_GitHub_run_required")
    # The final local suffix names a transfer allocation, not GitHub run_attempt.
    # A failed first download can require retained-<same run>-2 at run_attempt 1.
    plan = parse((base / "plan.json").read_bytes())
    need(re.fullmatch(rf"retained-{run['id']}-([1-9][0-9]*)", base.name) is not None
         and plan["run_id"] == run["id"] and plan["repository"] == REPOSITORY
         and plan["application_rerun"] is False
         and run["html_url"] == f"https://github.com/{REPOSITORY}/actions/runs/{run['id']}",
         "retained_transfer_allocation_or_repository_identity_changed")
    need(receipt["status"] == "retained" and receipt["run_id"] == run["id"]
         and receipt["head_sha"] == run["head_sha"]
         and receipt["workflow_conclusion"] == run["conclusion"]
         and re.fullmatch(r"[a-f0-9]{40}", run["head_sha"]), "retention_run_or_revision_mismatch")
    archive_path = base / "artifact.zip"
    need(not archive_path.is_symlink(), "archive_link_refused")
    actual = file_identity(archive_path)
    need(actual["bytes"] <= 250_000_000 and actual == {
        "bytes": receipt["archive_bytes"], "sha256": receipt["archive_sha256"]}
        and receipt["api_digest"] == "sha256:" + actual["sha256"]
        and receipt["digest_matches_api"] is True, "archive_or_API_digest_mismatch")
    artifacts = parse((base / "github-artifacts.json").read_bytes())["artifacts"]
    selected = [row for row in artifacts if row["id"] == receipt["artifact_id"]]
    need(len(selected) == 1, "saved_API_artifact_identity_missing_or_duplicated")
    artifact = selected[0]
    need(artifact["name"] == receipt["artifact_name"]
         and artifact["digest"] == receipt["api_digest"] and artifact["size_in_bytes"] == actual["bytes"]
         and artifact["workflow_run"]["id"] == run["id"]
         and artifact["workflow_run"]["head_sha"] == run["head_sha"], "artifact_not_bound_to_saved_run")
    evidence = [record(base / name) for name in ("github-run.json", "github-artifacts.json", "retention.json", "plan.json")]
    evidence.append({"path": archive_path.relative_to(ROOT).as_posix(), **actual})
    return base, run, receipt, evidence


def archived_json(archive, base, member, evidence):
    parts = PurePosixPath(member)
    need(not parts.is_absolute() and ".." not in parts.parts and "\\" not in member,
         "canonical_archive_member_required")
    raw = archive.read(member)
    need(len(raw) <= 16 * 1024 * 1024, "analysis_JSON_byte_bound")
    path = base / "extracted" / member
    need(path.is_file() and not path.is_symlink() and path.read_bytes() == raw,
         "extracted_evidence_differs_from_actual_archive")
    evidence.append(record(path))
    return parse(raw)


def expected_cells(manifest):
    need(manifest["schema_version"] == "ap2-native-bridge-development-matrix/10"
         and manifest["declared_cells"] == 104 and manifest["provider_requests_allowed"] == 0
         and len(manifest["cases"]) == 13 and tuple(row["id"] for row in manifest["arms"]) == ARMS,
         "original_V10_104_cell_13_case_eight_arm_scope_required")
    need(len({row["id"] for row in manifest["cases"]}) == 13, "duplicate_case_identity")
    return [{"index": index, "id": case["id"] + "--" + arm["id"],
             "case_id": case["id"], "arm_id": arm["id"]}
            for index, (case, arm) in enumerate((case, arm)
                for case in manifest["cases"] for arm in manifest["arms"])]


def error_free_purchase(row):
    return row["evaluation_status"] == VERIFIED_NATIVE and row["purchase_completed"] \
        and not row.get("source_errors") and row.get("actor_error_type") is None


def validate_matrix(manifest, allocation, execution, evaluation):
    """Check ordered identities, closing outcomes and non-overstated cell classes."""
    expected = expected_cells(manifest)
    need(allocation["schema_version"] == "ap2-native-bridge-allocation/10"
         and execution["schema_version"] == "ap2-native-bridge-execution/10"
         and evaluation["schema_version"] == "ap2-independent-native-bridge-matrix-evaluation/10",
         "V10_allocation_execution_evaluation_schemas_required")
    for document in (allocation, execution, evaluation):
        need(document["declared_cells"] == 104 and len(document["cells"]) == 104,
             "allocated_denominator_changed")
        need([{key: row[key] for key in IDENTITY_KEYS} for row in document["cells"]] == expected,
             "ordered_cell_identity_index_or_arm_changed")
    need(allocation["native_cells"] == 65 and allocation["bridge_initiation_cells"] == 39
         and allocation["all_missing_or_failed_cells_remain_in_denominator"] is True,
         "native_bridge_allocation_classes_changed")
    need(allocation["provider_requests_allowed"] == execution["provider_requests_allowed"] == 0
         and allocation["source_bank_task_qualification_established"] is False
         and allocation["native_qualification_established"] is False
         and allocation["whole_route_non_support_inference_allowed"] is False
         and evaluation["human_gold_validated"] is False
         and evaluation["source_bank_task_qualification_established"] is False
         and evaluation["native_qualification_established"] is False
         and evaluation["whole_route_non_support_inference_allowed"] is False,
         "development_allocation_cannot_assert_provider_gold_or_full_route_qualification")
    cells = evaluation["cells"]
    for dispatch, row in zip(execution["cells"], cells):
        need(row["returncode"] == dispatch["returncode"]
             and row["allocation_status"] == dispatch["allocation_status"]
             and (row["returncode"] is None or type(row["returncode"]) is int)
             and (dispatch["returncode"] is None or type(dispatch["returncode"]) is int),
             "evaluation_not_bound_to_closed_dispatch_outcome")
        status, arm = row["evaluation_status"], row["arm_id"]
        need(status in STATUSES and type(row["purchase_completed"]) is bool,
             "explicit_known_evaluation_status_and_purchase_indicator_required")
        need(not row["purchase_completed"] or status == VERIFIED_NATIVE,
             "unverified_or_bridge_cell_cannot_be_a_purchase")
        if status in (VERIFIED_NATIVE, VERIFIED_BRIDGE):
            need(type(row["returncode"]) is int and row.get("native_tcp_capture_verified") is True
                 and row.get("original_native_server_launch_qualification_established") is False,
                 "verified_capture_requires_closed_process_and_owned_TCP_scope")
            need(type(row.get("safety_violations")) is list
                 and all(type(item) is str for item in row["safety_violations"]),
                 "explicit_capture_safety_findings_required")
            need(row["native_qualification_established"] is False
                 and row["source_bank_task_qualification_established"] is False
                 and row["whole_route_non_support_inference_allowed"] is False,
                 "verified_capture_overstates_native_gold_or_whole_route_scope")
        if status == VERIFIED_NATIVE:
            need(arm in NATIVE and type(row.get("source_errors")) is list
                 and row.get("provider_requests") == 0, "native_capture_class_or_provider_scope_changed")
        if status == VERIFIED_BRIDGE:
            need(arm in BRIDGES and row["bridge_route"] == arm
                 and row["bridge_continuation_unrealized_and_retained"] is True
                 and row["repeated_bridge_prefix_and_initiation_slot"] is True
                 and row["post_initiation_case_fault_or_OTP_branch_exercised"] is False,
                 "bridge_initiation_upgraded_to_continuation_or_fault_execution")
        if status == PARTIAL:
            need(row["returncode"] is None and row.get("closing_actor_process_outcome_unknown") is True,
                 "partial_capture_cannot_be_closed_or_successful")
    totals = {
        "verified_captures": sum(row["evaluation_status"] in (VERIFIED_NATIVE, VERIFIED_BRIDGE) for row in cells),
        "verified_native_cells": sum(row["evaluation_status"] == VERIFIED_NATIVE for row in cells),
        "verified_legal_bridge_initiation_cells": sum(row["evaluation_status"] == VERIFIED_BRIDGE for row in cells),
        "bridge_unrealized_continuations_retained": sum(row.get("bridge_continuation_unrealized_and_retained", False) for row in cells),
        "verified_purchases": sum(row["purchase_completed"] for row in cells),
        "evaluation_refusals": sum(row["evaluation_status"] == REFUSED for row in cells),
        "missing_cells": sum(row["evaluation_status"] == MISSING for row in cells),
        "partial_unclosed_allocation_cells": sum(row["evaluation_status"] == PARTIAL for row in cells),
        "safety_violations": sum(len(row.get("safety_violations", [])) for row in cells),
    }
    need(all(type(value) is int for value in evaluation["totals"].values())
         and evaluation["totals"] == totals, "published_evaluator_totals_not_raw_cell_census")
    return expected, totals


def summaries(cells):
    result = {}
    for arm in ARMS:
        group = [row for row in cells if row["arm_id"] == arm]
        result[arm] = {
            "allocated_cells": len(group),
            "closed_process_outcomes": sum(type(row["returncode"]) is int for row in group),
            "purchase_observations": sum(row["purchase_completed"] for row in group),
            "error_free_owned_cell_purchase_observations": sum(error_free_purchase(row) for row in group),
            "error_free_zero_returncode_no_violation_purchase_observations": sum(
                error_free_purchase(row) and row["returncode"] == 0 and not row["safety_violations"] for row in group),
            "evaluation_statuses": dict(sorted(Counter(row["evaluation_status"] for row in group).items())),
            "safety_violations": sum(len(row.get("safety_violations", [])) for row in group),
            "actual_original_payment_posts": sum(row.get("actual_original_payment_posts", 0) for row in group),
            "actual_MCP_initiation_tool_errors": sum(row.get("actual_mcp_tool_error", False) for row in group),
            "interpretation": "Repeated bridge initiation prefixes; later OTP/fault continuations unrealized"
                if arm in BRIDGES else "Owned TCP/Uvicorn original payment-tool development cells",
        }
    return result


def analyze(base):
    base, run, receipt, retained_evidence = retained_archive(base)
    need(receipt["artifact_name"] == "ap2-native-tcp-legal-bridge-initiation-development-v10",
         "actual_V10_native_bridge_artifact_required")
    matrix_evidence = []
    with zipfile.ZipFile(base / "artifact.zip") as archive:
        names = archive.namelist()
        need(len(names) == len(set(names)), "duplicate_archive_member_refused")
        evaluation, manifest, allocation, execution = [archived_json(archive, base, member, matrix_evidence)
            for member in ("independent-evaluation/result.json", "matrix/public-manifest.json",
                           "matrix/allocation-manifest.json", "matrix/execution-results.json")]
        need(archive.read("matrix/public-manifest.json") == PUBLIC.read_bytes()
             and allocation["public_manifest"] == identity(PUBLIC.read_bytes()),
             "prospective_public_manifest_byte_binding_changed")
        need(archive.read("matrix/source-orchestrator.py") == ORCHESTRATOR.read_bytes(),
             "actual_orchestrator_source_changed")
        need(allocation["runner"] == identity(ACTOR.read_bytes()), "allocated_actor_source_changed")
        components = ast.literal_eval(next(node.value for node in ast.parse(ACTOR.read_bytes()).body
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
            and target.id == "OWNED_COMPONENTS" for target in node.targets)))
        need(type(components) is tuple and set(allocation["owned_components"]) == set(components),
             "prospective_helper_membership_changed")
        need(all(identity((ROOT / name).read_bytes()) == expected
                 for name, expected in allocation["owned_components"].items()),
             "prospective_helper_source_bytes_changed")
        need(evaluation["independent_evaluator_sha256"] == identity(EVALUATOR.read_bytes())["sha256"]
             and evaluation["private_expectations_sha256"] == identity(PRIVATE.read_bytes())["sha256"],
             "independent_evaluator_or_expectation_source_changed")
        expected, totals = validate_matrix(manifest, allocation, execution, evaluation)
        smoke = []
        for arm in ("conventional",) + BRIDGES:
            member = "smoke/" + arm + "/result.json"
            if member in names:
                result = archived_json(archive, base, member, matrix_evidence)
                row = {"arm_id": arm, "worker_returncode": result["returncode"],
                       "separate_from_matrix_denominator": True}
                failure = "smoke/" + arm + "/worker-failure.json"
                if failure in names:
                    row["worker_failure"] = archived_json(archive, base, failure, matrix_evidence)
                smoke.append(row)
    previous_base, previous_run, previous_receipt, previous_evidence = retained_archive(PREVIOUS)
    need(previous_receipt["archive_sha256"] == PREVIOUS_ARCHIVE_SHA and previous_run["id"] == 42881390576
         and previous_run["run_attempt"] == 1, "fixed_historical_ASGI_allocation_required")
    old_evidence = []
    with zipfile.ZipFile(previous_base / "artifact.zip") as archive:
        previous = archived_json(archive, previous_base, "independent-evaluation/result.json", old_evidence)
        old_manifest = archived_json(archive, previous_base, "matrix/public-manifest.json", old_evidence)
    need(manifest["cases"] == old_manifest["cases"] and manifest["source_pin"] == old_manifest["source_pin"],
         "transport_pair_case_or_source_semantics_changed")
    need(tuple(row["id"] for row in old_manifest["arms"]) == NATIVE
         and [{key: row[key] for key in POLICY_KEYS} for row in manifest["arms"][:5]]
             == [{key: row[key] for key in POLICY_KEYS} for row in old_manifest["arms"]],
         "transport_pair_native_policy_semantics_changed")
    old_expected = [(case["id"], arm) for case in manifest["cases"] for arm in NATIVE]
    need(previous["declared_cells"] == len(previous["cells"]) == 65
         and [(row["case_id"], row["arm_id"]) for row in previous["cells"]] == old_expected,
         "historical_ASGI_65_cell_order_changed")
    older = {(row["case_id"], row["arm_id"]): row for row in previous["cells"]}
    paired = []
    for row in evaluation["cells"]:
        if row["arm_id"] not in NATIVE:
            continue
        prior = older[row["case_id"], row["arm_id"]]
        need(type(prior["purchase_completed"]) is bool, "historical_purchase_indicator_must_be_explicit")
        evaluable = prior["evaluation_status"] == row["evaluation_status"] == VERIFIED_NATIVE
        paired.append({"case_id": row["case_id"], "arm_id": row["arm_id"],
            "ASGI_purchase_observed": prior["purchase_completed"], "TCP_purchase_observed": row["purchase_completed"],
            "ASGI_error_free_owned_cell_purchase_observed": error_free_purchase(prior),
            "TCP_error_free_owned_cell_purchase_observed": error_free_purchase(row),
            "comparison_evaluable": evaluable,
            "same_purchase_indicator": prior["purchase_completed"] == row["purchase_completed"] if evaluable else None,
            "TCP_evaluation_status": row["evaluation_status"], "TCP_source_errors": row.get("source_errors", []),
            "whole_original_task_success_inferred": False})
    need(len(paired) == 65, "all_native_transport_pairs_must_be_retained")
    evidence = matrix_evidence[:1] + old_evidence[:1] + matrix_evidence[1:] + old_evidence[1:]
    evidence += retained_evidence + previous_evidence
    evidence += [record(path) for path in (PUBLIC, ACTOR, ORCHESTRATOR, EVALUATOR, PRIVATE, Path(__file__))]
    evidence += [record(ROOT / name) for name in components]
    evidence = list({row["path"]: row for row in evidence}.values())
    return {"schema_version": "ap2-v10-native-bridge-development-analysis/1", "status": "analyzed_all_allocated_cells",
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "run_id": run["id"], "run_attempt": run["run_attempt"],
        "workflow_conclusion": run["conclusion"], "head_sha": run["head_sha"], "evidence": evidence,
        "declared_cells": 104, "native_payment_tool_cells": 65, "bridge_initiation_cells": 39,
        "distinct_authored_public_cases": 13, "independent_task_count_is_not_cell_count": True,
        "arm_summaries": summaries(evaluation["cells"]), "totals_reconstructed_from_cells": totals,
        "separate_smoke_worker_outcomes": smoke, "paired_ASGI_TCP_purchase_indicators": paired,
        "ASGI_TCP_purchase_indicator_changes": sum(row["comparison_evaluable"] and not row["same_purchase_indicator"] for row in paired),
        "unresolved_ASGI_TCP_pairs": sum(not row["comparison_evaluable"] for row in paired),
        "all_missing_or_failed_cells_retained": True, "new_actor_evaluator_solver_checker_or_provider_calls": 0,
        "human_gold_validated": False, "original_server_launch_qualification_claimed": False,
        "bridge_continuation_success_inferred": False, "whole_original_study_completed": False,
        "limits": ["Missing or unexecuted cells are not measured zero-percent task-success trials.",
                   "Same-case ASGI/TCP outcomes come from separate development allocations with disclosed offline fixtures.",
                   "39 bridge initiation slots repeat 13 authored prefixes; later OTP and case faults remain unrealized.",
                   "Purchase observations can precede an actor/source suffix error; both counts remain separate.",
                   "This analysis rechecks archived evaluation counts and source/run identities, not every raw application semantic judgment.",
                   "No provider utility, human gold, full 96-task study, whole-route non-support or canonical-launch qualification is inferred."]}


def self_check():
    """Exercise denominator tamper rejection on constructed in-memory documents."""
    from copy import deepcopy
    manifest = parse(PUBLIC.read_bytes())
    base = ROOT / "runs/ap2-native-bridge-development/v8/retained-42897325489-1/extracted"
    allocation, execution, evaluation = [parse((base / name).read_bytes()) for name in (
        "matrix/allocation-manifest.json", "matrix/execution-results.json", "independent-evaluation/result.json")]
    for document in (allocation, execution, evaluation):
        document["schema_version"] = document["schema_version"].removesuffix("8") + "10"
    validate_matrix(manifest, allocation, execution, evaluation)
    mutations = {
        "reordered_evaluation": lambda docs: docs[2]["cells"].reverse(),
        "duplicated_evaluation_identity": lambda docs: docs[2]["cells"].__setitem__(1, deepcopy(docs[2]["cells"][0])),
        "missing_purchase_invented": lambda docs: docs[2]["cells"][0].__setitem__("purchase_completed", True),
        "closing_returncode_invented": lambda docs: docs[2]["cells"][0].__setitem__("returncode", 0),
        "denominator_changed": lambda docs: docs[0].__setitem__("declared_cells", 105),
        "native_bridge_partition_changed": lambda docs: docs[0].__setitem__("native_cells", 64),
        "aggregate_capture_invented": lambda docs: docs[2]["totals"].__setitem__("verified_captures", 1),
    }
    rejected = []
    for name, change in mutations.items():
        documents = deepcopy([allocation, execution, evaluation])
        change(documents)
        try:
            validate_matrix(manifest, *documents)
        except ValueError:
            rejected.append(name)
    need(len(rejected) == len(mutations), "constructed_tamper_control_was_accepted")
    return {"constructed_controls_passed": 1 + len(rejected), "rejected_mutations": rejected,
            "actual_V10_execution_or_analysis_claimed": False, "new_application_or_provider_calls": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        need(args.base is None and args.output is None, "self_check_cannot_create_actual_analysis")
        print(json.dumps(self_check()))
        return 0
    need(args.base is not None and args.output is not None, "actual_base_and_fresh_output_required")
    output = args.output.resolve()
    need(output.is_relative_to(ROOT / "runs") and output.suffix == ".json" and not output.exists(),
         "fresh_workspace_analysis_JSON_output_required")
    result = analyze(args.base)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "run_id": result["run_id"],
                      "totals": result["totals_reconstructed_from_cells"],
                      "unresolved_ASGI_TCP_pairs": result["unresolved_ASGI_TCP_pairs"],
                      "output": output.relative_to(ROOT).as_posix()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
