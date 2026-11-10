"""Build manuscript V11 only from a real retained native/bridge analysis.

No application, actor, evaluator, solver, provider or network is executed.
The frozen V7 draft remains unchanged. Missing/failed/unknown allocated cells
stay in their original denominators and never become qualified tasks.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
V7 = ROOT / "paper/working-draft-v7.md"
METHOD = ROOT / "docs/research/method-contribution-assessment-v2.json"
CODE_PEER = ROOT / "docs/research/method-contribution-code-peer-v1.json"
SEMANTIC = ROOT / "runs/ci-agentops-governed-app-reference-v4/retained-42887519756-1/independent-semantic-peer-review-v1.json"
CODEC_BASE = ROOT / "runs/ci-refutation-prefix-dag-v2/retained-42910442359-1"
CODEC_COMPARISON = ROOT / "docs/research/refutation-prefix-dag-comparison-v2.json"
CODEC_PEER = ROOT / "docs/research/refutation-prefix-dag-peer-review-v2.json"
CODEC_APPENDIX = ROOT / "paper/refutation-prefix-dag-appendix-v2.md"
CODEC_AUDIT = ROOT / "paper/refutation-prefix-dag-appendix-v2.audit.json"
GUIDE = ROOT / "docs/research/paper-artifact-guide-v11.md"
HISTORICAL = ((8, 42897325489), (9, 42902256098), (10, 42905259371))
NATIVE = ("reference", "conventional", "recovery", "shared", "recovery_shared")
BRIDGES = ("amir_typed", "mg_typed", "mg_raw")
ARMS = NATIVE + BRIDGES
VERIFIED_NATIVE = "original_application_capture_verified"
VERIFIED_BRIDGE = "original_bridge_initiation_capture_verified"
TITLE = "# Benchmarking Framework for LLM-Based Agent Interoperability: Measuring Interoperability Loss Across Heterogeneous Agent Boundaries"


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def read(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result, "duplicate_json_key")
            result[key] = value
        return result
    def invalid(value):
        raise ValueError("nonfinite_json:" + value)
    return json.loads(path.read_bytes(), object_pairs_hook=unique, parse_constant=invalid)


def record(path):
    path = path.resolve()
    need(path.is_relative_to(ROOT), "evidence_outside_workspace")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for raw in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(raw)
            digest.update(raw)
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": size, "sha256": digest.hexdigest()}


def verify_archive(base, selected):
    """Bind the completed API receipt, real archive and selected extracted bytes."""
    run = read(base / "github-run.json")
    retention = read(base / "retention.json")
    archive_path = base / "artifact.zip"
    archive_record = record(archive_path)
    need(retention["status"] == "retained" and retention["run_id"] == run["id"]
         and retention["head_sha"] == run["head_sha"]
         and retention["workflow_conclusion"] == run["conclusion"], "completed_retention_identity_required")
    need(retention["archive_bytes"] == archive_record["bytes"]
         and retention["archive_sha256"] == archive_record["sha256"]
         and retention["api_digest"] == "sha256:" + archive_record["sha256"]
         and retention["digest_matches_api"] is True, "real_archive_API_digest_mismatch")
    artifacts = read(base / "github-artifacts.json")["artifacts"]
    matches = [row for row in artifacts if row["id"] == retention["artifact_id"]]
    need(len(matches) == 1 and matches[0]["name"] == retention["artifact_name"]
         and matches[0]["digest"] == retention["api_digest"]
         and matches[0]["size_in_bytes"] == archive_record["bytes"]
         and matches[0]["workflow_run"]["id"] == run["id"]
         and matches[0]["workflow_run"]["head_sha"] == run["head_sha"], "API_artifact_not_actual_run")
    manifest_path = base / "extracted-manifest.json"
    manifest = read(manifest_path)
    entries = {row["path"]: row for row in manifest["files"]}
    need(len(entries) == len(manifest["files"]), "duplicate_extracted_manifest_member")
    with zipfile.ZipFile(archive_path) as archive:
        need(len(archive.namelist()) == len(set(archive.namelist())), "duplicate_archive_member")
        for path in selected:
            path = path.resolve()
            if not path.is_relative_to((base / "extracted").resolve()):
                continue
            member = path.relative_to(base / "extracted").as_posix()
            raw = archive.read(member)
            actual = {"path": member, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
            need(entries.get(member) == actual and path.read_bytes() == raw, "selected_archive_extraction_mismatch:" + member)
    return [record(base / name) for name in ("github-run.json", "retention.json", "github-artifacts.json", "extracted-manifest.json", "artifact.zip")]


def evidence(native_analysis, native_base):
    analysis_path, base = native_analysis.resolve(), native_base.resolve()
    need(base.is_relative_to(ROOT / "runs") and analysis_path.is_relative_to(ROOT / "runs"), "actual_retained_paths_required")
    github_path = base / "github-run.json"
    run = read(github_path)
    need(type(run.get("id")) is int and type(run.get("run_attempt")) is int and run["status"] == "completed", "real_completed_run_receipt_required")
    need(base.name == f"retained-{run['id']}-{run['run_attempt']}" and "/actions/runs/" + str(run["id"]) in run["html_url"], "retained_run_identity_mismatch")
    evaluation_path = base / "extracted/independent-evaluation/result.json"
    matrix = base / "extracted/matrix"
    evaluation, manifest, allocation, execution, analysis = (read(path) for path in
        (evaluation_path, matrix / "public-manifest.json", matrix / "allocation-manifest.json", matrix / "execution-results.json", analysis_path))
    need(analysis["schema_version"] == "ap2-v11-native-bridge-development-analysis/1"
         and analysis["status"] == "analyzed_all_allocated_cells", "actual_native_analysis_required")
    records = analysis["evidence"]
    need(records and records[0] == record(evaluation_path), "analysis_not_bound_to_actual_retained_evaluation")
    for item in records:
        need(record(ROOT / item["path"]) == item, "analysis_input_digest_changed")
    archive_records = verify_archive(base, [ROOT / item["path"] for item in records])
    need(analysis["declared_cells"] == evaluation["declared_cells"] == manifest["declared_cells"]
         == allocation["declared_cells"] == execution["declared_cells"] == 104, "104_cell_denominator_required")
    need(analysis["native_payment_tool_cells"] == 65 and analysis["bridge_initiation_cells"] == 39
         and analysis["distinct_authored_public_cases"] == len(manifest["cases"]) == 13, "65_native_39_repeated_bridge_classes_required")
    need(tuple(row["id"] for row in manifest["arms"]) == ARMS, "original_eight_arm_classes_required")
    expected = [(case["id"], arm["id"]) for case in manifest["cases"] for arm in manifest["arms"]]
    need(len(set(expected)) == 104, "distinct_allocated_cell_ids_required")
    for rows in (allocation["cells"], execution["cells"], evaluation["cells"]):
        need([(row["case_id"], row["arm_id"]) for row in rows] == expected, "allocation_execution_evaluation_order_changed")
    need({key: allocation["public_manifest"][key] for key in ("bytes", "sha256")}
         == {key: record(matrix / "public-manifest.json")[key] for key in ("bytes", "sha256")}, "retained_public_manifest_binding")
    need((matrix / "public-manifest.json").read_bytes() == (ROOT / "benchmark/ap2-native-bridge-development-v11/application.json").read_bytes(), "prospective_public_manifest_changed")
    summaries, status_counts = {}, Counter()
    executions = {(row["case_id"], row["arm_id"]): row for row in execution["cells"]}
    for arm in ARMS:
        group = [row for row in evaluation["cells"] if row["arm_id"] == arm]
        need(len(group) == 13, "every_arm_retains_13_cases")
        for row in group:
            status = row["evaluation_status"]
            need(type(status) is str and type(row["purchase_completed"]) is bool, "explicit_cell_outcome_required")
            if status not in (VERIFIED_NATIVE, VERIFIED_BRIDGE):
                need(not row["purchase_completed"], "unverified_cell_cannot_be_a_purchase")
            if status in (VERIFIED_NATIVE, VERIFIED_BRIDGE):
                need(row.get("native_tcp_capture_verified") is True
                     and row.get("original_native_server_launch_qualification_established") is False, "owned_TCP_scope_required")
                need(executions[row["case_id"], arm]["returncode"] is not None, "verified_cell_without_closed_process")
            need(row["returncode"] == executions[row["case_id"], arm]["returncode"], "evaluated_execution_process_outcome_changed")
            if arm in BRIDGES and status == VERIFIED_BRIDGE:
                need(not row["purchase_completed"] and row["bridge_continuation_unrealized_and_retained"] is True
                     and row["repeated_bridge_prefix_and_initiation_slot"] is True
                     and row["post_initiation_case_fault_or_OTP_branch_exercised"] is False, "bridge_prefix_must_not_become_fault_or_task_success")
            need(not (arm in NATIVE and status == VERIFIED_BRIDGE)
                 and not (arm in BRIDGES and status == VERIFIED_NATIVE), "source_class_label_mismatch")
        summary = {"allocated_cells": 13,
                   "purchase_observations": sum(row["purchase_completed"] for row in group),
                   "error_free_owned_cell_purchase_observations": sum(row["purchase_completed"] and not row.get("source_errors")
                       and row.get("actor_error_type") is None for row in group),
                   "error_free_zero_returncode_no_violation_purchase_observations": sum(row["purchase_completed"]
                       and not row.get("source_errors") and row.get("actor_error_type") is None and row["returncode"] == 0
                       and not row.get("safety_violations") for row in group),
                   "closed_process_outcomes": sum(type(executions[row["case_id"], arm]["returncode"]) is int for row in group),
                   "evaluation_statuses": dict(Counter(row["evaluation_status"] for row in group))}
        for key, value in summary.items():
            need(analysis["arm_summaries"][arm][key] == value, "analysis_arm_summary_not_raw_cell_census")
        summaries[arm] = summary
        status_counts.update(summary["evaluation_statuses"])
    prior_record = records[1]
    prior = read(ROOT / prior_record["path"])
    prior_index = {(row["case_id"], row["arm_id"]): row for row in prior["cells"]}
    paired = analysis["paired_ASGI_TCP_purchase_indicators"]
    expected_native = {(case, arm) for case, arm in expected if arm in NATIVE}
    need(len(paired) == 65 and {(row["case_id"], row["arm_id"]) for row in paired} == expected_native, "65_original_ASGI_TCP_pairs_required")
    current = {(row["case_id"], row["arm_id"]): row for row in evaluation["cells"]}
    for pair in paired:
        key = pair["case_id"], pair["arm_id"]
        old, new = prior_index[key], current[key]
        evaluable = old["evaluation_status"] == new["evaluation_status"] == VERIFIED_NATIVE
        need(pair["comparison_evaluable"] == evaluable
             and pair["ASGI_purchase_observed"] == old["purchase_completed"]
             and pair["TCP_purchase_observed"] == new["purchase_completed"]
             and pair["ASGI_error_free_owned_cell_purchase_observed"] == (old["evaluation_status"] == VERIFIED_NATIVE
                 and old["purchase_completed"] and not old.get("source_errors") and old.get("actor_error_type") is None)
             and pair["TCP_error_free_owned_cell_purchase_observed"] == (new["evaluation_status"] == VERIFIED_NATIVE
                 and new["purchase_completed"] and not new.get("source_errors") and new.get("actor_error_type") is None)
             and pair["same_purchase_indicator"] == (old["purchase_completed"] == new["purchase_completed"] if evaluable else None), "ASGI_TCP_pair_not_actual_same_case_outcomes")
    changes = sum(row["comparison_evaluable"] and row["same_purchase_indicator"] is False for row in paired)
    unresolved = sum(not row["comparison_evaluable"] for row in paired)
    need(analysis["ASGI_TCP_purchase_indicator_changes"] == changes
         and analysis["unresolved_ASGI_TCP_pairs"] == unresolved, "pair_denominator_or_unknowns_changed")
    need(analysis["original_server_launch_qualification_claimed"] is False
         and analysis["bridge_continuation_success_inferred"] is False and analysis["human_gold_validated"] is False,
         "analysis_overclaims_native_bridge_or_gold_scope")
    return {"analysis": analysis, "run": run, "base": base, "evaluation_path": evaluation_path,
            "summaries": summaries, "status_counts": dict(status_counts), "changes": changes,
            "unresolved": unresolved, "records": [record(analysis_path), record(github_path), record(evaluation_path),
                record(matrix / "public-manifest.json"), record(matrix / "allocation-manifest.json"), record(matrix / "execution-results.json")]
                + archive_records + records, "verified_native": sum(row["evaluation_status"] == VERIFIED_NATIVE for row in evaluation["cells"]),
            "verified_bridge": sum(row["evaluation_status"] == VERIFIED_BRIDGE for row in evaluation["cells"])}


def inherited_and_codec_inputs():
    ledger = read(ROOT / "paper/claim-ledger-v7.json")
    need(ledger["draft"] == record(V7) and ledger["human_scientific_review_claimed"] is False
         and ledger["original_full_study_scope_complete"] is False, "frozen_v7_claim_scope_changed")
    for item in ledger["evidence"]:
        need(record(ROOT / item["path"]) == item, "frozen_v7_evidence_digest_changed")
    comparison, peer, appendix_audit = map(read, (CODEC_COMPARISON, CODEC_PEER, CODEC_AUDIT))
    need(appendix_audit["appendix"] == record(CODEC_APPENDIX)
         and appendix_audit["audit_outcome"] == "numeric_and_codec_scope_claims_match"
         and appendix_audit["scientific_approval"] is False, "codec_appendix_audit_not_current")
    for item in appendix_audit["evidence_fingerprints"]:
        need(record(ROOT / item["path"]) == item, "codec_appendix_source_digest_changed")
    need(comparison["selected_unsupported_certificate_count"] == 26 and comparison["tests_passed"] == 31
         and comparison["new_admission_solver_runs"] == comparison["new_semantic_checker_runs_on_retained_cases"] == 0
         and comparison["novelty_established"] is False and comparison["faster_checker_established"] is False,
         "codec_control_count_or_claim_scope_changed")
    expected = {"old_bytes": 15128, "dag_bytes": 11918, "direct_bytes": 7760, "smaller": 2, "larger": 24, "equal": 0}
    need(comparison["aggregate"] == peer["retained_comparison"]["aggregate"] == expected,
         "codec_comparison_and_independent_peer_disagree")
    rows = peer["retained_comparison"]["rows"]
    need(len(rows) == 26 and len({row["case_id"] for row in rows}) == 26
         and all(row["exact_ordered_object_and_canonical_byte_round_trip"] and not row["new_semantic_checker_call"] for row in rows),
         "all26_exact_codec_roundtrips_required")
    need({key: sum(row[key] for row in rows) for key in ("old_bytes", "dag_bytes", "direct_bytes")}
         == {key: expected[key] for key in ("old_bytes", "dag_bytes", "direct_bytes")}, "codec_byte_aggregate_not_all26rows")
    need(len(peer["resolved_v1_findings"]) == 3 and all(row["v2_status"].startswith("fixed_and_independently_")
         for row in peer["resolved_v1_findings"]), "three_frozen_v1_defects_must_remain_disclosed")
    reproduction_path = CODEC_BASE / "extracted/result.json"
    reproduction = read(reproduction_path)
    need(reproduction["passed"] is True and reproduction["cases"] == 26 and reproduction["aggregate"] == expected
         and reproduction["new_admission_solver_calls"] == reproduction["new_semantic_checker_calls"] == 0,
         "fresh_codec_reproduction_does_not_match")
    for item in reproduction["inputs"]:
        need(record(ROOT / item["path"]) == item, "fresh_codec_reproduction_source_changed")
    run = read(CODEC_BASE / "github-run.json")
    need(run["status"] == "completed" and run["conclusion"] == "success", "fresh_codec_CI_not_completed_success")
    controls_path = CODEC_BASE / "extracted/controls.stderr"
    controls = controls_path.read_text(encoding="utf-8")
    need(re.search(r"Ran 31 tests in [0-9.]+s\s+OK\s*$", controls), "fresh_hosted_31_codec_controls_not_passed")
    records = verify_archive(CODEC_BASE, [reproduction_path, controls_path])
    records += [record(path) for path in (ROOT / "paper/claim-ledger-v7.json", ROOT / "paper/draft-audit-v7-1.json",
        ROOT / "docs/research/paper-v7-counterreview-v1.json", ROOT / "docs/research/manuscript-v7-fresh-checkout-results-v1.md",
        ROOT / "runs/ci-manuscript-v7/retained-42891705471-1/extracted/audit.json",
        CODEC_COMPARISON, CODEC_PEER, CODEC_APPENDIX, CODEC_AUDIT, reproduction_path, controls_path, GUIDE)]
    records += ledger["evidence"] + appendix_audit["evidence_fingerprints"] + reproduction["inputs"]
    return records, {"aggregate": expected, "tests_passed": 31, "cases": 26, "fresh_hosted_run_id": run["id"], "fresh_hosted_url": run["html_url"]}


def historical_inputs():
    rows, records = [], []
    for version, run_id in HISTORICAL:
        base = ROOT / f"runs/ap2-native-bridge-development/v{version}/retained-{run_id}-1"
        path = base / "extracted/independent-evaluation/result.json"
        evaluation = read(path)
        status_counts = dict(Counter(row["evaluation_status"] for row in evaluation["cells"]))
        need(evaluation["declared_cells"] == len(evaluation["cells"]) == 104
             and evaluation["totals"]["missing_cells"] == 104 and evaluation["totals"]["verified_captures"] == 0,
             "frozen_adverse_native_allocations_changed")
        failure_path = base / "extracted/smoke/conventional/worker-failure.json"
        failure = read(failure_path)
        rows.append({"version": version, "run_id": run_id, "missing_cells": 104, "verified_captures": 0,
                     "error_type": failure["error_type"], "reason": failure["reason"], "evaluation_statuses": status_counts})
        records += [record(path), record(failure_path), record(base / "extracted/smoke/conventional/result.json")]
    records += [record(ROOT / name) for name in ("docs/research/ap2-v8-actual-smoke-failure-peer-audit-v1.json",
        "docs/research/ap2-v9-actual-stage-failure-peer-audit-v1.json", "docs/research/ap2-v11-real-ca-ci-peer-review-v2.json",
        "docs/research/ap2-v11-final-source-freshness-peer-v1.json")]
    freshness = read(ROOT / "docs/research/ap2-v11-final-source-freshness-peer-v1.json")
    need(freshness["passed"] is True and freshness["final_14_source_hashes_match"] is True
         and freshness["new_application_or_provider_calls"] == 0, "v11_static_freshness_control_missing")
    return records, rows


def actual_smoke_inputs(bound):
    base = bound["base"]
    need(bound["run"]["conclusion"] == "failure" and bound["verified_native"] == bound["verified_bridge"] == 0
         and bound["unresolved"] == 65 and bound["status_counts"] == {"missing_or_pre_execution_failure_retained": 104},
         "actual_v11_failed_smoke_and_missing_matrix_required")
    smoke = base / "extracted/smoke/conventional"
    paths = [smoke / name for name in ("result.json", "application-outcome.json", "actor-input-separation.json",
                                      "actor-guard-denials.jsonl", "worker-stages.jsonl")]
    worker, outcome, separation = map(read, paths[:3])
    denials = [json.loads(line) for line in paths[3].read_text(encoding="utf-8").splitlines()]
    stages = [json.loads(line) for line in paths[4].read_text(encoding="utf-8").splitlines()]
    counts = dict(Counter(row["guard_code"] for row in denials))
    expected = {"actor_private_evaluator_or_saved_credential_read_denied": 1,
                "native_actor_unowned_network_operation_denied": 2,
                "native_actor_unallocated_descendant_process_denied": 1}
    need(worker["returncode"] == 0 and worker["native_qualification_established"] is False
         and outcome["decision"] == "prefix_incomplete" and outcome["error_type"] == "A2AClientHTTPError"
         and outcome["final_task"] is None and outcome["source_bank_task_qualification_established"] is False,
         "actual_v11_smoke_outcome_not_bound")
    need(counts == expected and len(denials) == separation["guard_diagnostic_rows"] == 4 and len(stages) == 9
         and separation["denials"]["private_reads_blocked"] == 1
         and separation["denials"]["external_network_operations_blocked"] == 2
         and separation["denials"]["unallocated_descendant_processes_blocked"] == 1,
         "actual_v11_smoke_guard_and_stage_counts_changed")
    evaluator_path = ROOT / "scripts/evaluate_ap2_native_bridge_matrix_v11.py"
    evaluator = evaluator_path.read_text(encoding="utf-8")
    need("'native_unexpected_private_network_or_process_guard_interference'" in evaluator
         and "separation['denials']['external_network_operations_blocked'] == 0" in evaluator
         and "separation['denials']['unallocated_descendant_processes_blocked'] == 0" in evaluator,
         "actual_guard_interference_rejection_source_missing")
    doc = ROOT / "docs/research/ap2-native-bridge-development-analysis-v11.md"
    need(doc.exists(), "actual_source_bound_smoke_diagnostic_required")
    records = verify_archive(base, paths) + [record(path) for path in paths + [evaluator_path, doc]]
    return records, {"worker_returncode": 0, "application_decision": "prefix_incomplete", "error_type": "A2AClientHTTPError",
                     "final_task": None, "stage_rows": 9, "guard_rows": 4, "network_denials": 2,
                     "process_denials": 1, "expected_private_read_probe_denials": 1,
                     "separate_from_matrix_denominator": True, "native_qualification": False}


def semantic_inputs():
    method, code, semantic = read(METHOD), read(CODE_PEER), read(SEMANTIC)
    need(method["status"] == "evidence_bound_assessment_complete_original_method_and_full_study_unresolved"
         and method["original_distinct_method_objective_preserved"] is True and method["scope_revision_performed"] is False,
         "full_original_method_scope_must_be_preserved")
    need(code["assessment"]["new_general_algorithmic_principle_established"] is False
         and code["assessment"]["shared_lifting_superiority_established"] is False, "code_peer_claim_limits_required")
    need(semantic["candidate_denominator"] == 34 and semantic["mechanical_complete_recipes_reviewed"] == 20
         and semantic["historical_status_counts_preserved"] == {"observed_reference_recipe": 20,
             "observed_partial_reference_recipe": 10, "unsupported_public_recipe": 2, "checks_failed": 2}
         and semantic["complete_recipe_decision_quality_gaps"] == ["agentops-d03-restart-pause"], "AgentOps_semantic_historical_failure_limits_required")
    return [record(METHOD), record(CODE_PEER), record(SEMANTIC)]


def native_section(bound):
    summaries = bound["summaries"]
    rows = ["| Arm | Allocated cases | Closed process outcomes | Purchase observations | Error-free owned-cell purchases | Zero-exit/no-violation purchases |",
            "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for arm in ARMS:
        row = summaries[arm]
        rows.append(f"| {arm} | 13 | {row['closed_process_outcomes']} | {row['purchase_observations']} | {row['error_free_owned_cell_purchase_observations']} | {row['error_free_zero_returncode_no_violation_purchase_observations']} |")
    statuses = ["| Retained evaluation status | Cells |", "| --- | ---: |"]
    statuses.extend(f"| {name} | {count} |" for name, count in sorted(bound["status_counts"].items()))
    analysis_path = bound["records"][0]["path"]
    capture_statement = (
        f"This allocation verifies {bound['verified_native']}/65 native payment-tool captures and "
        f"{bound['verified_bridge']}/39 bridge initiation captures. "
        "Missing or refused captures supply no native performance evidence."
    )
    return f"""### 8.9. Original payment tools over owned TCP and legal bridge initiation

The retained [hosted allocation]({bound['run']['html_url']}) supplies
104 allocated cells: 65 original payment-tool cells and 39 repeated legal
bridge initiation prefixes on the same 13 authored public cases. The latter
are three legal route variants, not 39 independently qualified tasks or
executed later case-specific fault/OTP continuations. Every failed, missing,
unclosed or refused cell stays in its original allocation and status.

{capture_statement}

For capture-verified cells, the owned bootstrap binds the exact observed
original applications to loopback TCP sockets and serves them with Uvicorn.
HTTPX performs real TCP dispatch in those cells. This removes the in-process
ASGI transport intervention only where the native capture is verified, while
retaining owned offline model/prefix fixtures and process guards.
It does not establish qualification of the original native server launcher,
full ADK shopper, live provider, financial settlement or whole-route support.

**Table NT. Original allocated outcomes; each arm has denominator 13.**

{chr(10).join(rows)}

Purchase and error-free owned-cell purchase remain separate indicators. A
receipt can precede a retained duplicate-call or admission-refusal suffix;
neither indicator alone is unconditional original task/gold success.
The additional zero-exit/no-violation indicator also requires a zero process
return code and no retained safety violations; it still supplies no human gold.

**Table NS. All retained statuses, including adverse outcomes.**

{chr(10).join(statuses)}

The same-case ASGI/TCP comparison retains all 65 native pairs. It observes
{bound['changes']} changed purchase indicators among evaluable pairs and
{bound['unresolved']} unresolved pairs. An unresolved pair has no equality or
transport-success inference. Separate development allocations are compared;
this is not an equal-budget held-out or live-model trial.

Legal bridge calls preserve each bridge's actual public tool schema, original
card and observed response. No DataPart/header parameter, source task/context
handle or inverse Task is invented to make the bridge succeed. Reported
initiation/discovery responses and errors are route-specific observations;
an unrealized continuation does not prove whole-interface non-support.
The [retained analysis](../{analysis_path}) binds raw evaluated cells, source
classes, all eight arm summaries and each same-case pair.

"""


def codec_section(codec):
    # The separately audited appendix stays frozen; its source-bound body is reused.
    body = CODEC_APPENDIX.read_text(encoding="utf-8").split("It packages", 1)[1]
    return "### 7.6. Lossless refutation-prefix proof packaging\n\nIt packages" + body + f"""

A separate [fresh hosted reproduction]({codec['fresh_hosted_url']}) passes
all 31 constructed codec controls and recomputes all 26 retained round trips
and complete-wrapper byte counts from a clean checkout. The retained
[reproduction receipt](../{(CODEC_BASE / 'extracted/result.json').relative_to(ROOT).as_posix()})
records zero new admission-solver and semantic-checker calls on those retained
cases. Constructed controls and codec recomputation are separate processes;
neither supplies a new held-out application trial, faster checker or novelty
finding. The V1 defects and both V1/V2 review records remain preserved.

"""


def failure_and_scope_section(history, bound):
    table = ["| Frozen allocation | Missing cells / allocated | Verified captures | Smoke exception |",
             "| --- | ---: | ---: | --- |"]
    table += [f"| V{row['version']} ({row['run_id']}) | 104/104 | 0 | `{row['error_type']}` |" for row in history]
    return """### 8.10. Preserved native bootstrap failures and interpretation limits

The actual V11 conventional smoke worker exits zero and records nine stages,
but its application outcome is `prefix_incomplete` with `A2AClientHTTPError`
and no final task. The separate smoke capture records four guard denials:
two unowned-network operations, one unallocated descendant-process operation
and the expected private-evaluator-read probe. Those counts violate the
evaluator's required zero network/process-denial condition and trigger
`native_unexpected_private_network_or_process_guard_interference`.
There is no completed smoke-evaluation result. An actor exit code of zero
does not establish capture verification, task success or native qualification.
The [source-bound V11 diagnostic](../docs/research/ap2-native-bridge-development-analysis-v11.md)
retains the actual failure and its bounded caller diagnostics. The entire
matrix remains missing; its zero purchase observations are not a measured
zero-percent task-success trial.

The frozen predecessors each retain all 104 missing matrix cells after an
actual smoke failure. These are owned setup failures, not measurements of
native payment-tool or bridge throughput, latency, success probability or
provider quality. The smoke allocation is separate from the matrix denominator.

""" + "\n".join(table) + """

V8 records an actor-private/evaluator-or-saved-credential guard denial;
its capture does not identify the exact external-operation caller. V9 records
the undefined `append` stage-journal dependency before guard admission. V10
records rejected non-certificate, non-comment PEM content. Static V11 controls
verify the disclosed stage-prelude and real public-CA preparation changes;
they do not retroactively convert any predecessor into a successful capture.
Only the separately retained V11 allocation above supplies V11 cell outcomes.

The broader registered study remains 96 tasks, three paths (288 path cells)
and 96 crossing observations. These are unresolved prospective study
obligations, not denominators achieved by repeated development profiles or
bridge initiation prefixes. The 68 original candidate records, candidate-specific
gold and near misses, complete source-to-model alternatives, unchanged bridge
eligibility, a distinct method beyond the closest comparators, common-cost
utility evidence and accountable human novelty/feasibility/scientific review
remain unresolved. No scope revision or project-completion credit follows
from a successful build, a source hash, a codec test or this manuscript audit.

"""


def build(native_analysis, native_base):
    bound = evidence(native_analysis, native_base)
    records = semantic_inputs()
    additional_records, codec = inherited_and_codec_inputs()
    history_records, history = historical_inputs()
    smoke_records, smoke = actual_smoke_inputs(bound)
    text = V7.read_text(encoding="utf-8")
    need(text.splitlines()[0] == TITLE and text.count("## 9. Discussion") == 1, "registered_title_or_frozen_layout_changed")
    text = text.replace("Research manuscript, version 7, 11 November 2026.", "Research manuscript, version 11, 11 November 2026.", 1)
    old_opening = """This version adds the
separately executed constraint-pruned comparator, refreshed primary-source
references and original AP2 application development execution and a separately audited
shared-lifting admission-to-application continuation."""
    need(old_opening in text, "frozen_v7_opening_anchor_missing")
    text = text.replace(old_opening, """This successor preserves the
audited V7 development studies and integrates the separately reviewed V2
lossless proof codec, its fresh hosted reproduction, and the actual retained
V11 smoke failure with all 104 missing matrix cells.""", 1)
    text = text.replace("paper-artifact-guide-v7.md", "paper-artifact-guide-v11.md")
    abstract_end = "superiority, native AP2 qualification or held-out live-model generalization."
    need(abstract_end in text, "frozen_abstract_scope_anchor_missing")
    text = text.replace(abstract_end, abstract_end + "\nA separately retained owned-TCP allocation adds 65 original payment-tool\ncells and 39 repeated legal bridge initiation prefixes, retaining all\n104 allocated outcomes and every unresolved continuation. Owned TCP serving\ndoes not establish the original native-launcher qualification.", 1)
    text = text.replace("## 1. Introduction", "The lossless V2 proof codec restores all 26 retained negative certificates;\ncomplete-wrapper bytes change from 15,128 to 11,918, versus 7,760 for direct.\nTwo encoded proofs shrink and 24 grow. A separate hosted reproduction passes\n31 constructed codec controls. These are representation and reproducibility\nobservations without a new solver, checker-speed or novelty claim.\n\n## 1. Introduction", 1)
    method_paragraph = """The [method contribution assessment](../docs/research/method-contribution-assessment-v2.md)
and [independent static code peer](../docs/research/method-contribution-code-peer-v1.json)
support an executable finite admission/certificate and empirical artifact,
while leaving a distinct general method and qualified full study unresolved.
The direct comparator already supplies whole-frame relation caching,
remaining-horizon goal pruning and first-feasible goal return. Shared lifting
adds exact-prefix/current-history reuse and complete relation summaries while
retaining path-prefix refutation certificates. These implemented obligations
do not alone establish a new CEGAR, memoization or constraint-pruning principle.

"""
    text = text.replace("## 9. Discussion\n\n", "## 9. Discussion\n\n" + method_paragraph, 1)
    semantic_paragraph = """The [independent semantic peer](../docs/research/agentops-v4-semantic-peer-review-v1.md)
also separates mechanical recipe observation from remediation decision quality.
For `agentops-d03-restart-pause`, the actual unconfirmed proposal is observed,
but outage/crash-loop symptoms do not establish the runbook's understood-cause,
dependency/configuration, deployment and resource prerequisites. The proposal
boundary is not a validated evidence-supported remediation choice.
The two historical failures remain failed: `agentops-h19-resolved-remediation-stop`
preserves the full procedural body and actual resolved stop despite PII
redaction of its heading; `agentops-h24-persistence-redaction` makes no save
call and recalls zero notes. A successor correction requires a fresh capture,
not a retrospective upgrade of these failures.

"""
    text = text.replace("### 8.8. Original ADK shopper feasibility and remaining branches\n\n", semantic_paragraph + "### 8.8. Original ADK shopper feasibility and remaining branches\n\n", 1)
    meter_anchor = "**Comparator and meter scope.**"
    need(text.count(meter_anchor) == 1, "meter_scope_anchor_missing")
    meter_caveat = """Shared lifting explicitly charges canonical cache-key, payload and history
traversal; the direct language's key serialization and domain-key construction
do not carry comparable meter charges. Equal numerical allowances therefore
compare declared method-specific accounting policies, not equal CPU or hardware
budgets. The adverse coverage result cannot by itself establish practical
efficiency or a general speed ranking.

"""
    text = text.replace(meter_anchor, meter_caveat + meter_anchor, 1)
    text = text.replace("## 8. Admission followed by an original application effect", codec_section(codec) + "## 8. Admission followed by an original application effect", 1)
    text = text.replace("## 9. Discussion", native_section(bound) + failure_and_scope_section(history, bound) + "## 9. Discussion", 1)
    need(text.splitlines()[0] == TITLE and "version 11" in text and "native-launcher qualification" in text, "final_title_scope_required")
    inputs = [record(V7), record(Path(__file__))] + records + bound["records"] + additional_records + history_records + smoke_records
    inputs = list({item["path"]: item for item in inputs}.values())
    provenance = {"schema_version": "paper-v11-evidence-bound-build/1", "built_utc": datetime.now(timezone.utc).isoformat(),
                  "inputs": inputs, "native_run_id": bound["run"]["id"], "native_run_attempt": bound["run"]["run_attempt"],
                  "registered_title": TITLE[2:], "original_full_scope_revised": False,
                  "native_declared_cells": 104, "native_payment_tool_cells": 65, "repeated_bridge_initiation_cells": 39,
                  "native_arm_summaries": bound["summaries"], "native_status_counts": bound["status_counts"],
                  "codec": codec, "frozen_native_predecessors": history,
                  "actual_v11_separate_smoke": smoke, "native_ASGI_TCP_unresolved_pairs": bound["unresolved"],
                  "native_ASGI_TCP_evaluable_pairs": 65 - bound["unresolved"],
                  "original_study_tasks": 96, "original_study_paths": 288, "original_study_crossings": 96,
                  "publication_ready": False, "full_manuscript_drafted": True, "full_original_study_complete": False,
                  "new_App_model_solver_provider_calls": 0, "human_scientific_review": False,
                  "paper_sha256": hashlib.sha256(text.encode()).hexdigest()}
    return text, provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-analysis", type=Path, required=True)
    parser.add_argument("--native-base", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    args = parser.parse_args()
    output, provenance = args.output.resolve(), args.provenance.resolve()
    need(output == ROOT / "paper/working-draft-v11.md" and provenance == ROOT / "paper/working-draft-v11.provenance.json"
         and not output.exists() and not provenance.exists(), "fresh_owned_v11_artifacts_required")
    text, receipt = build(args.native_analysis, args.native_base)
    # Validate everything before either reviewable artifact is written.
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    with provenance.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(receipt, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": "local_v11_draft_built_from_real_retained_evidence", "output": str(output),
                      "native_run_id": receipt["native_run_id"], "cells": 104}))


if __name__ == "__main__":
    main()
