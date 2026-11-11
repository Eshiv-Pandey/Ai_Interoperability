"""Build V13 only from actual completed retained allocation and analysis.

Stdlib file reads only. Frozen V11 remains unchanged. Missing/refused/unclosed
cells and non-evaluable pairs retain their denominators; no scientific gold
or original native-launch qualification is inferred.
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
NATIVE = ("reference", "conventional", "recovery", "shared", "recovery_shared")
BRIDGES = ("amir_typed", "mg_typed", "mg_raw")
ARMS = NATIVE + BRIDGES
VERIFIED_NATIVE = "original_application_capture_verified"
VERIFIED_BRIDGE = "original_bridge_initiation_capture_verified"
V11 = ROOT / "paper/working-draft-v11.md"
V12_DIAGNOSTIC = ROOT / "runs/ap2-native-bridge-development/v12/preallocation-failure-42915964952-1/result.json"
GUIDE = ROOT / "docs/research/paper-artifact-guide-v13.md"


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


def error_free(row):
    return row["evaluation_status"] == VERIFIED_NATIVE and row["purchase_completed"] \
        and not row.get("source_errors") and row.get("actor_error_type") is None


def bind_native(analysis_path, base):
    analysis_path, base = analysis_path.resolve(), base.resolve()
    need(analysis_path.is_relative_to(ROOT / "runs/ap2-native-bridge-development/v13")
         and base.is_relative_to(ROOT / "runs/ap2-native-bridge-development/v13"), "actual_V13_retained_paths_required")
    run = read(base / "github-run.json")
    need(run["status"] == "completed"
         and type(run["id"]) is int and type(run["run_attempt"]) is int
         and re.fullmatch(rf"retained-{run['id']}-[1-9][0-9]*", base.name), "actual_completed_V13_allocation_required")
    analysis = read(analysis_path)
    need(analysis["schema_version"] == "ap2-v13-native-bridge-development-analysis/1"
         and analysis["status"] == "analyzed_all_allocated_cells" and analysis["run_id"] == run["id"]
         and analysis["run_attempt"] == run["run_attempt"] and analysis["head_sha"] == run["head_sha"],
         "actual_V13_analysis_run_or_source_identity_changed")
    need(analysis["workflow_conclusion"] == run["conclusion"], "actual_workflow_conclusion_must_be_retained")
    evaluation_path = base / "extracted/independent-evaluation/result.json"
    matrix = base / "extracted/matrix"
    evaluation, manifest, allocation, execution = [read(path) for path in (evaluation_path,
        matrix / "public-manifest.json", matrix / "allocation-manifest.json", matrix / "execution-results.json")]
    need(analysis["evidence"][0] == record(evaluation_path), "actual_evaluation_must_be_first_analysis_binding")
    for item in analysis["evidence"]:
        need(record(ROOT / item["path"]) == item, "analysis_evidence_changed:" + item["path"])
    archive_records = verify_archive(base, [ROOT / item["path"] for item in analysis["evidence"]])
    need(manifest["schema_version"] == "ap2-native-bridge-development-matrix/13"
         and tuple(row["id"] for row in manifest["arms"]) == ARMS and len(manifest["cases"]) == 13
         and analysis["native_payment_tool_cells"] == 65 and analysis["bridge_initiation_cells"] == 39,
         "V13_native_bridge_authored_case_partition_required")
    expected = [(case["id"], arm["id"]) for case in manifest["cases"] for arm in manifest["arms"]]
    need(len(expected) == len(set(expected)) == 104, "all104_unique_public_cell_identities_required")
    for document in (allocation, execution, evaluation):
        need(document["declared_cells"] == len(document["cells"]) == 104
             and [(row["case_id"], row["arm_id"]) for row in document["cells"]] == expected,
             "ordered_actual_allocation_execution_evaluation_census_changed")
    source_bindings = analysis["matrix_capture_source_bindings"]
    need(len(source_bindings) == 104 and [row["prefix"] for row in source_bindings]
         == ["matrix/cells/" + row["id"] for row in evaluation["cells"]], "all104_source_capture_statuses_required")
    for row, source in zip(evaluation["cells"], source_bindings):
        if row["evaluation_status"] in (VERIFIED_NATIVE, VERIFIED_BRIDGE):
            need(source["complete_owned_source_capture"] is True and not source["source_binding_errors"]
                 and not source["missing_captured_components"] and source["verified_captured_components"] == len(allocation["owned_components"]),
                 "verified_capture_cannot_use_invalid_or_missing_source_copies")
    current = {(row["case_id"], row["arm_id"]): row for row in evaluation["cells"]}
    dispatches = {(row["case_id"], row["arm_id"]): row for row in execution["cells"]}
    summaries = {}
    for arm in ARMS:
        rows = [row for row in evaluation["cells"] if row["arm_id"] == arm]
        for row in rows:
            need(type(row["purchase_completed"]) is bool and row["returncode"] == dispatches[row["case_id"], arm]["returncode"],
                 "actual_purchase_or_closing_process_outcome_required")
            need(not row["purchase_completed"] or row["evaluation_status"] == VERIFIED_NATIVE,
                 "nonverified_or_bridge_cell_cannot_be_a_purchase")
        summaries[arm] = {"allocated_cells": 13,
            "closed_process_outcomes": sum(type(row["returncode"]) is int for row in rows),
            "verified_captures": sum(row["evaluation_status"] in (VERIFIED_NATIVE, VERIFIED_BRIDGE) for row in rows),
            "purchase_observations": sum(row["purchase_completed"] for row in rows),
            "error_free_owned_cell_purchase_observations": sum(error_free(row) for row in rows),
            "error_free_zero_returncode_no_violation_purchase_observations": sum(error_free(row)
                and row["returncode"] == 0 and not row.get("safety_violations") for row in rows),
            "evaluation_statuses": dict(Counter(row["evaluation_status"] for row in rows))}
        for field, value in summaries[arm].items():
            if field != "verified_captures":
                need(analysis["arm_summaries"][arm][field] == value, "raw_actual_arm_census_differs_from_analysis")
    prior_path = ROOT / analysis["evidence"][1]["path"]
    prior = read(prior_path)
    old = {(row["case_id"], row["arm_id"]): row for row in prior["cells"]}
    pairs = analysis["paired_ASGI_TCP_purchase_indicators"]
    expected_pairs = [(case, arm) for case, arm in expected if arm in NATIVE]
    need(len(pairs) == 65 and [(row["case_id"], row["arm_id"]) for row in pairs] == expected_pairs,
         "all65_ordered_actual_transport_pairs_required")
    for pair in pairs:
        key = pair["case_id"], pair["arm_id"]
        previous, now = old[key], current[key]
        evaluable = previous["evaluation_status"] == now["evaluation_status"] == VERIFIED_NATIVE
        need(pair["comparison_evaluable"] == evaluable and pair["ASGI_purchase_observed"] == previous["purchase_completed"]
             and pair["TCP_purchase_observed"] == now["purchase_completed"]
             and pair["ASGI_error_free_owned_cell_purchase_observed"] == error_free(previous)
             and pair["TCP_error_free_owned_cell_purchase_observed"] == error_free(now)
             and pair["same_purchase_indicator"] == (previous["purchase_completed"] == now["purchase_completed"] if evaluable else None),
             "transport_pair_not_raw_same_case_evidence")
    unresolved = sum(not pair["comparison_evaluable"] for pair in pairs)
    changes = sum(pair["comparison_evaluable"] and pair["same_purchase_indicator"] is False for pair in pairs)
    need(analysis["unresolved_ASGI_TCP_pairs"] == unresolved and analysis["ASGI_TCP_purchase_indicator_changes"] == changes,
         "transport_pair_unknown_or_change_count_differs")
    need(analysis["human_gold_validated"] is False and analysis["original_server_launch_qualification_claimed"] is False
         and analysis["bridge_continuation_success_inferred"] is False and analysis["whole_original_study_completed"] is False,
         "V13_analysis_cannot_establish_original_scientific_qualification")
    return {"run": run, "analysis": analysis, "base": base, "summaries": summaries,
        "statuses": dict(Counter(row["evaluation_status"] for row in evaluation["cells"])),
        "changes": changes, "unresolved": unresolved,
        "records": [record(analysis_path)] + archive_records + analysis["evidence"]
            + [record(ROOT / "docs/research/ap2-native-bridge-development-analysis-v13.md")]
            + [record(base / name) for name in ("independent-raw-review-v1.py", "independent-raw-review-v1.json",
                "independent-dispatch-safety-review-v1.py", "independent-dispatch-safety-review-v1.json")]}


def bind_inherited():
    provenance = read(ROOT / "paper/working-draft-v11.provenance.json")
    audit = read(ROOT / "paper/working-draft-v11.audit.json")
    need(provenance["paper_sha256"] == record(V11)["sha256"] and audit["passed"] is True,
         "audited_frozen_V11_manuscript_required")
    for item in provenance["inputs"]:
        need(record(ROOT / item["path"]) == item, "frozen_V11_input_changed:" + item["path"])
    for item in audit["inputs"]:
        need(record(ROOT / item["path"]) == item, "frozen_V11_audit_binding_changed")
    diagnostic = read(V12_DIAGNOSTIC)
    need(diagnostic["status"] == "failed_before_actual_cell_allocation"
         and diagnostic["actual_allocated_cell_census"] is None and diagnostic["actual_transport_pair_census"] is None,
         "V12_preallocation_failure_cannot_be_a_104cell_census")
    for item in diagnostic["evidence"]:
        need(record(ROOT / item["path"]) == item, "V12_preallocation_diagnostic_input_changed")
    records = provenance["inputs"] + diagnostic["evidence"]
    records += [record(path) for path in (V11, ROOT / "paper/working-draft-v11.provenance.json",
        ROOT / "paper/working-draft-v11.audit.json", V12_DIAGNOSTIC,
        ROOT / "docs/research/ap2-native-bridge-development-analysis-v12.md", GUIDE)]
    return records


def native_section(bound):
    rows = ["| Arm | Allocated | Closed process outcomes | Verified captures | Purchases | Error-free owned-cell purchases | Error-free, zero-exit/no-violation purchases |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for arm in ARMS:
        s = bound["summaries"][arm]
        rows.append(f"| {arm} | 13 | {s['closed_process_outcomes']} | {s['verified_captures']} | {s['purchase_observations']} | {s['error_free_owned_cell_purchase_observations']} | {s['error_free_zero_returncode_no_violation_purchase_observations']} |")
    statuses = ["| Actual V13 evaluation status | Cells |", "| --- | ---: |"]
    statuses += [f"| {status} | {count} |" for status, count in sorted(bound["statuses"].items())]
    native = sum(bound["summaries"][arm]["verified_captures"] for arm in NATIVE)
    bridges = sum(bound["summaries"][arm]["verified_captures"] for arm in BRIDGES)
    return f"""### 8.11. Separately retained V13 native and bridge development allocation

The [actual V13 hosted allocation]({bound['run']['html_url']}) completed with
workflow conclusion `{bound['run']['conclusion']}` and retains all
104 prospective matrix slots: 65 original payment-tool cells and 39 repeated
legal bridge initiation slots across the same 13 authored cases. This separate
allocation verifies {native}/65 native captures and {bridges}/39 bridge
initiation captures. Failed, missing, refused and unclosed outcomes remain in
their original denominators. A missing or refused capture supplies no native
performance or task-success-rate observation.

**Table V13A. Actual matrix outcomes; each arm has denominator 13.**

{chr(10).join(rows)}

Purchase, error-free owned-cell purchase and zero-exit/no-violation purchase
remain separate indicators. A receipt before a retained duplicate-call error
or admission-refusal suffix is not unconditional original-task or human-gold
success. The stricter process indicator additionally requires return code zero
and no retained safety violations; it also establishes no human gold.

**Table V13S. Complete actual status census.**

{chr(10).join(statuses)}

All 65 same-case ASGI/TCP pairs remain present. The actual comparison reports
{bound['changes']} changed purchase indicators among evaluable pairs and
{bound['unresolved']} non-evaluable pairs. No equality or transport-success
inference follows for a non-evaluable pair. These are separate development
allocations with disclosed offline fixtures, rather than an equal-budget
held-out or live-provider experiment.

The 39 bridge slots repeat legal public initiation routes. They do not become
39 independent tasks, successful OTP/fault continuations or a whole-interface
non-support result. Owned Uvicorn/loopback TCP observations remain distinct
from the original native launcher, full ADK shopper, provider quality, financial
settlement and whole-route/source-to-model qualification. The actual analysis
binds the V13 guard-policy helper, both V2 diagnostic helpers and all captured
runner/helper copies; invalid source copies in refused cells remain explicit
and do not become verified source evidence.
The [actual V13 analysis](../{bound['records'][0]['path']}) binds every reported
cell, source-capture status, same-case pair and retained archive identity.

V12 is a distinct preallocation failure. Its completed archive has no actual
matrix or smoke allocation; the [V12 diagnostic](../docs/research/ap2-native-bridge-development-analysis-v12.md)
retains a missing outgoing-source fixture in a constructed control. Its public
104-slot plan creates neither 104 evaluated failures nor 65 actual transport
pairs. The earlier V11 matrix remained unexecuted after its failed smoke capture.

The registered 96-task, 288-path-cell and 96-crossing study, 68 original
candidate records, held-out gold/near misses, unchanged bridge eligibility,
distinct-method novelty, common-cost utility evidence and accountable human
scientific review remain unresolved. Neither this successor nor a workflow
exit revises the original scope or claims publication readiness.

"""


def build(analysis_path, base):
    bound = bind_native(analysis_path, base)
    inputs = bind_inherited()
    text = V11.read_text(encoding="utf-8")
    title = text.splitlines()[0]
    need(text.count("## 9. Discussion") == 1, "frozen_V11_layout_changed")
    text = text.replace("Research manuscript, version 11, 11 November 2026.", "Research manuscript, version 13, 11 November 2026.", 1)
    opening = """This successor preserves the
audited V7 development studies and integrates the separately reviewed V2
lossless proof codec, its fresh hosted reproduction, and the actual retained
V11 smoke failure with all 104 missing matrix cells."""
    need(opening in text, "frozen_V11_opening_anchor_changed")
    text = text.replace(opening, """This successor preserves the
audited V11 manuscript, lossless V2 proof codec and historical failed attempts,
and integrates the actual separately retained V13 development allocation.
Earlier V11 matrix execution was blocked by failed smoke verification; V12
failed during constructed controls before real allocation.""", 1)
    text = text.replace("paper-artifact-guide-v11.md", "paper-artifact-guide-v13.md")
    old = """A separately retained owned-TCP allocation adds 65 original payment-tool
cells and 39 repeated legal bridge initiation prefixes, retaining all
104 allocated outcomes and every unresolved continuation. Owned TCP serving
does not establish the original native-launcher qualification."""
    need(old in text, "frozen_V11_abstract_transport_anchor_missing")
    native = sum(bound["summaries"][arm]["verified_captures"] for arm in NATIVE)
    bridge = sum(bound["summaries"][arm]["verified_captures"] for arm in BRIDGES)
    text = text.replace(old, f"""The earlier V11 owned-TCP matrix remained unexecuted after a failed smoke
capture; all 104 matrix observations are missing and all 65 native transport
pairs are non-evaluable. V12 failed during constructed controls before actual
allocation, so it supplies no matrix or transport-pair census. A separate
retained V13 allocation verifies {native}/65 native payment-tool captures and
{bridge}/39 repeated legal bridge initiation captures, retaining every adverse
outcome. Owned TCP serving does not establish original native-launcher,
provider, whole-task or human-gold qualification.""", 1)
    text = text.replace("## 9. Discussion", native_section(bound) + "## 9. Discussion", 1)
    need(text.splitlines()[0] == title, "registered_title_changed")
    inputs += bound["records"] + [record(Path(__file__)),
        record(ROOT / "scripts/verify_ap2_native_bridge_development_v13.py")]
    inputs = list({row["path"]: row for row in inputs}.values())
    provenance = {"schema_version": "paper-v13-evidence-bound-build/1", "built_utc": datetime.now(timezone.utc).isoformat(),
        "registered_title": title[2:], "inputs": inputs, "paper_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "native_run_id": bound["run"]["id"], "native_run_attempt": bound["run"]["run_attempt"],
        "native_workflow_conclusion": bound["run"]["conclusion"],
        "native_declared_cells": 104, "native_payment_tool_cells": 65, "repeated_bridge_initiation_cells": 39,
        "native_arm_summaries": bound["summaries"], "native_status_counts": bound["statuses"],
        "native_ASGI_TCP_unresolved_pairs": bound["unresolved"], "native_ASGI_TCP_changed_purchase_indicators": bound["changes"],
        "original_study_tasks": 96, "original_study_paths": 288, "original_study_crossings": 96,
        "original_full_scope_revised": False, "full_manuscript_drafted": True, "full_original_study_complete": False,
        "publication_ready": False, "human_scientific_review": False, "new_App_model_solver_evaluator_provider_calls": 0}
    return text, provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-analysis", type=Path, required=True)
    parser.add_argument("--native-base", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    args = parser.parse_args()
    output, provenance = args.output.resolve(), args.provenance.resolve()
    need(output == ROOT / "paper/working-draft-v13.md" and provenance == ROOT / "paper/working-draft-v13.provenance.json"
         and not output.exists() and not provenance.exists(), "fresh_owned_V13_manuscript_artifacts_required")
    text, value = build(args.native_analysis, args.native_base)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
    with provenance.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": "actual_V13_evidence_bound_manuscript_built", "run_id": value["native_run_id"]}))


if __name__ == "__main__":
    main()
