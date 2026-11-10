"""Build manuscript V8 only from a real retained native/bridge analysis.

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

ROOT = Path(__file__).resolve().parents[1]
V7 = ROOT / "paper/working-draft-v7.md"
METHOD = ROOT / "docs/research/method-contribution-assessment-v2.json"
CODE_PEER = ROOT / "docs/research/method-contribution-code-peer-v1.json"
SEMANTIC = ROOT / "runs/ci-agentops-governed-app-reference-v4/retained-42887519756-1/independent-semantic-peer-review-v1.json"
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
    raw = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


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
    need(analysis["schema_version"] == "ap2-v8-native-bridge-development-analysis/1"
         and analysis["status"] == "analyzed_all_allocated_cells", "actual_native_analysis_required")
    records = analysis["evidence"]
    need(records and records[0] == record(evaluation_path), "analysis_not_bound_to_actual_retained_evaluation")
    for item in records:
        need(record(ROOT / item["path"]) == item, "analysis_input_digest_changed")
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
    need((matrix / "public-manifest.json").read_bytes() == (ROOT / "benchmark/ap2-native-bridge-development-v8/application.json").read_bytes(), "prospective_public_manifest_changed")
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
                   "evaluation_statuses": dict(Counter(row["evaluation_status"] for row in group))}
        for key, value in summary.items():
            need(analysis["arm_summaries"][arm][key] == value, "analysis_arm_summary_not_raw_cell_census")
        summary["closed_process_outcomes"] = sum(executions[row["case_id"], arm]["returncode"] is not None for row in group)
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
                record(matrix / "public-manifest.json"), record(matrix / "allocation-manifest.json"), record(matrix / "execution-results.json")]}


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
    rows = ["| Arm | Allocated cases | Closed process outcomes | Purchase observations | Error-free owned-cell purchases |",
            "| --- | ---: | ---: | ---: | ---: |"]
    for arm in ARMS:
        row = summaries[arm]
        rows.append(f"| {arm} | 13 | {row['closed_process_outcomes']} | {row['purchase_observations']} | {row['error_free_owned_cell_purchase_observations']} |")
    statuses = ["| Retained evaluation status | Cells |", "| --- | ---: |"]
    statuses.extend(f"| {name} | {count} |" for name, count in sorted(bound["status_counts"].items()))
    analysis_path = bound["records"][0]["path"]
    return f"""### 8.9. Original payment tools over owned TCP and legal bridge initiation

The retained [hosted allocation]({bound['run']['html_url']}) supplies
104 allocated cells: 65 original payment-tool cells and 39 repeated legal
bridge initiation prefixes on the same 13 authored public cases. The latter
are three legal route variants, not 39 independently qualified tasks or
executed later case-specific fault/OTP continuations. Every failed, missing,
unclosed or refused cell stays in its original allocation and status.

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


def build(native_analysis, native_base):
    bound = evidence(native_analysis, native_base)
    records = semantic_inputs()
    text = V7.read_text(encoding="utf-8")
    need(text.splitlines()[0] == TITLE and text.count("## 9. Discussion") == 1, "registered_title_or_frozen_layout_changed")
    text = text.replace("Research manuscript, version 7, 11 November 2026.", "Research manuscript, version 8, 11 November 2026.", 1)
    text = text.replace("paper-artifact-guide-v7.md", "paper-artifact-guide-v8.md")
    abstract_end = "superiority, native AP2 qualification or held-out live-model generalization."
    need(abstract_end in text, "frozen_abstract_scope_anchor_missing")
    text = text.replace(abstract_end, abstract_end + "\nA separately retained owned-TCP allocation adds 65 original payment-tool\ncells and 39 repeated legal bridge initiation prefixes, retaining all\n104 allocated outcomes and every unresolved continuation. Owned TCP serving\ndoes not establish the original native-launcher qualification.", 1)
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
    text = text.replace("## 9. Discussion", native_section(bound) + "## 9. Discussion", 1)
    need(text.splitlines()[0] == TITLE and "version 8" in text and "native-launcher qualification" in text, "final_title_scope_required")
    inputs = [record(V7), record(Path(__file__))] + records + bound["records"]
    provenance = {"schema_version": "paper-v8-evidence-bound-build/1", "built_utc": datetime.now(timezone.utc).isoformat(),
                  "inputs": inputs, "native_run_id": bound["run"]["id"], "native_run_attempt": bound["run"]["run_attempt"],
                  "registered_title": TITLE[2:], "original_full_scope_revised": False,
                  "native_declared_cells": 104, "native_payment_tool_cells": 65, "repeated_bridge_initiation_cells": 39,
                  "native_arm_summaries": bound["summaries"], "native_status_counts": bound["status_counts"],
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
    need(output.parent == ROOT / "paper" and "v8" in output.name and provenance.parent == ROOT / "paper"
         and "v8" in provenance.name and not output.exists() and not provenance.exists(), "fresh_owned_v8_artifacts_required")
    text, receipt = build(args.native_analysis, args.native_base)
    # Validate everything before either reviewable artifact is written.
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    with provenance.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(receipt, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": "local_v8_draft_built_from_real_retained_evidence", "output": str(output),
                      "native_run_id": receipt["native_run_id"], "cells": 104}))


if __name__ == "__main__":
    main()
