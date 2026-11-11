"""Independent read-only census, source and claim audit of V13 manuscript.

Imports no builder, application, evaluator, solver, provider or guard helper.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlparse
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ("reference", "conventional", "recovery", "shared", "recovery_shared")
BRIDGES = ("amir_typed", "mg_typed", "mg_raw")
ARMS = NATIVE + BRIDGES
VERIFIED_NATIVE = "original_application_capture_verified"
VERIFIED_BRIDGE = "original_bridge_initiation_capture_verified"


def read(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate_json_key")
            result[key] = value
        return result
    def invalid(_):
        raise ValueError("nonfinite_json")
    return json.loads(path.read_bytes(), object_pairs_hook=unique, parse_constant=invalid)

def identify(path):
    path = path.resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("evidence_outside_workspace")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for raw in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(raw)
            digest.update(raw)
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": size, "sha256": digest.hexdigest()}

def archived_evidence_matches(base, selected):
    """Independent API/archive/extraction join; no builder is imported."""
    run, retention = read(base / "github-run.json"), read(base / "retention.json")
    archive = identify(base / "artifact.zip")
    if (run["status"] != "completed" or retention["status"] != "retained"
            or retention["run_id"] != run["id"] or retention["head_sha"] != run["head_sha"]
            or retention["workflow_conclusion"] != run["conclusion"]
            or retention["archive_bytes"] != archive["bytes"] or retention["archive_sha256"] != archive["sha256"]
            or retention["api_digest"] != "sha256:" + archive["sha256"] or not retention["digest_matches_api"]):
        return False
    artifacts = read(base / "github-artifacts.json")["artifacts"]
    rows = [row for row in artifacts if row["id"] == retention["artifact_id"]]
    if len(rows) != 1 or (rows[0]["digest"] != retention["api_digest"]
            or rows[0]["size_in_bytes"] != archive["bytes"] or rows[0]["name"] != retention["artifact_name"]
            or rows[0]["workflow_run"]["id"] != run["id"] or rows[0]["workflow_run"]["head_sha"] != run["head_sha"]):
        return False
    manifest = read(base / "extracted-manifest.json")["files"]
    identities = {row["path"]: (row["bytes"], row["sha256"]) for row in manifest}
    if len(identities) != len(manifest):
        return False
    with zipfile.ZipFile(base / "artifact.zip") as zipped:
        if len(zipped.namelist()) != len(set(zipped.namelist())):
            return False
        for path in selected:
            path = path.resolve()
            if path.is_relative_to((base / "extracted").resolve()):
                name = path.relative_to(base / "extracted").as_posix()
                raw = zipped.read(name)
                if identities.get(name) != (len(raw), hashlib.sha256(raw).hexdigest()) or path.read_bytes() != raw:
                    return False
    return True


def error_free(row):
    return row["evaluation_status"] == VERIFIED_NATIVE and row["purchase_completed"] \
        and not row.get("source_errors") and row.get("actor_error_type") is None


def audit(draft_path, provenance_path, analysis_path, base):
    draft = draft_path.read_text(encoding="utf-8")
    flat = re.sub(r"\s+", " ", draft)
    provenance, analysis = read(provenance_path), read(analysis_path)
    run = read(base / "github-run.json")
    evaluation_path = base / "extracted/independent-evaluation/result.json"
    evaluation = read(evaluation_path)
    manifest = read(base / "extracted/matrix/public-manifest.json")
    allocation = read(base / "extracted/matrix/allocation-manifest.json")
    execution = read(base / "extracted/matrix/execution-results.json")
    cells = evaluation["cells"]
    checks = []
    def check(name, condition, evidence):
        checks.append({"id": name, "passed": bool(condition), "evidence": evidence})
    original = (ROOT / "paper/working-draft-v11.md").read_text(encoding="utf-8")
    check("registered_title_and_original_scope_preserved", draft.splitlines()[0] == original.splitlines()[0]
          and provenance["registered_title"] == original.splitlines()[0][2:]
          and provenance["original_full_scope_revised"] is False, original.splitlines()[0])
    check("current_draft_and_all_build_inputs_bound", provenance["schema_version"] == "paper-v13-evidence-bound-build/1"
          and provenance["paper_sha256"] == identify(draft_path)["sha256"]
          and all(identify(ROOT / item["path"]) == item for item in provenance["inputs"]), len(provenance["inputs"]))
    verifier = ROOT / "scripts/verify_ap2_native_bridge_development_v13.py"
    guide = (ROOT / "docs/research/paper-artifact-guide-v13.md").read_text(encoding="utf-8")
    analysis_doc = (ROOT / "docs/research/ap2-native-bridge-development-analysis-v13.md").read_text(encoding="utf-8")
    check("source_bound_readonly_existing_analysis_reproduction_documented",
          identify(verifier) in provenance["inputs"]
          and "verify_ap2_native_bridge_development_v13.py --verify-existing" in guide
          and "verify_ap2_native_bridge_development_v13.py --verify-existing" in analysis_doc
          and "created_at_utc" in guide and "created_at_utc" in analysis_doc,
          "Successor verifier preserves existing analysis bytes and ignores only the new creation timestamp.")
    check("actual_completed_V13_run_and_conclusion", run["status"] == "completed"
          and run["id"] == provenance["native_run_id"] and run["run_attempt"] == provenance["native_run_attempt"]
          and run["id"] == analysis["run_id"] and run["run_attempt"] == analysis["run_attempt"]
          and run["head_sha"] == analysis["head_sha"] and run["html_url"] in draft,
          {"run_id": run["id"], "attempt": run["run_attempt"], "head_sha": run["head_sha"], "conclusion": run["conclusion"]})
    check("workflow_conclusion_retained_without_scientific_exclusion", provenance["native_workflow_conclusion"] == run["conclusion"]
          and analysis["workflow_conclusion"] == run["conclusion"] and f"workflow conclusion `{run['conclusion']}`" in flat,
          "Completed failed/mixed allocations remain eligible when actual matrix records exist.")
    check("source_bound_actual_V13_analysis_and_archive", analysis["schema_version"] == "ap2-v13-native-bridge-development-analysis/1"
          and analysis["status"] == "analyzed_all_allocated_cells" and analysis["evidence"][0] == identify(evaluation_path)
          and all(identify(ROOT / item["path"]) == item for item in analysis["evidence"])
          and archived_evidence_matches(base, [ROOT / item["path"] for item in analysis["evidence"]]),
          identify(base / "artifact.zip"))
    expected = [(case["id"], arm["id"]) for case in manifest["cases"] for arm in manifest["arms"]]
    check("all104ordered_cells65native39bridge13cases_retained", len(set(expected)) == len(expected) == 104
          and tuple(row["id"] for row in manifest["arms"]) == ARMS and len(manifest["cases"]) == 13
          and all(document["declared_cells"] == len(document["cells"]) == 104
              and [(row["case_id"], row["arm_id"]) for row in document["cells"]] == expected
              for document in (allocation, execution, evaluation))
          and sum(row["arm_id"] in NATIVE for row in cells) == 65
          and sum(row["arm_id"] in BRIDGES for row in cells) == 39,
          {"allocated": len(cells), "native": 65, "bridge": 39, "authored_cases": 13})
    actual_statuses = dict(Counter(row["evaluation_status"] for row in cells))
    known = {VERIFIED_NATIVE, VERIFIED_BRIDGE, "missing_or_pre_execution_failure_retained",
             "partial_allocation_capture_unclosed_and_retained", "independent_evaluation_refused"}
    check("no_invented_status_or_nonverified_purchase", set(actual_statuses).issubset(known)
          and all(type(row["purchase_completed"]) is bool and (not row["purchase_completed"] or row["evaluation_status"] == VERIFIED_NATIVE)
                  for row in cells), actual_statuses)
    dispatch = {(row["case_id"], row["arm_id"]): row for row in execution["cells"]}
    check("actual_closing_process_outcomes_match_dispatch", all(row["returncode"] == dispatch[row["case_id"], row["arm_id"]]["returncode"]
          and (row["returncode"] is None or type(row["returncode"]) is int) for row in cells), len(cells))
    expected_table, recomputed = [], {}
    for arm in ARMS:
        rows = [row for row in cells if row["arm_id"] == arm]
        counts = {"allocated_cells": 13, "closed_process_outcomes": sum(type(row["returncode"]) is int for row in rows),
            "verified_captures": sum(row["evaluation_status"] in (VERIFIED_NATIVE, VERIFIED_BRIDGE) for row in rows),
            "purchase_observations": sum(row["purchase_completed"] for row in rows),
            "error_free_owned_cell_purchase_observations": sum(error_free(row) for row in rows),
            "error_free_zero_returncode_no_violation_purchase_observations": sum(error_free(row)
                and row["returncode"] == 0 and not row.get("safety_violations") for row in rows),
            "evaluation_statuses": dict(Counter(row["evaluation_status"] for row in rows))}
        recomputed[arm] = counts
        expected_table.append(f"| {arm} | 13 | {counts['closed_process_outcomes']} | {counts['verified_captures']} | {counts['purchase_observations']} | {counts['error_free_owned_cell_purchase_observations']} | {counts['error_free_zero_returncode_no_violation_purchase_observations']} |")
    section = draft.split("**Table V13A.", 1)[1].split("**Table V13S.", 1)[0]
    actual_table = [line for line in section.splitlines() if any(line.startswith("| " + arm + " |") for arm in ARMS)]
    check("all_eight_arm_table_counts_independently_reconstructed", actual_table == expected_table
          and "| Error-free, zero-exit/no-violation purchases |" in section
          and provenance["native_arm_summaries"] == recomputed
          and all(analysis["arm_summaries"][arm][field] == value for arm, counts in recomputed.items()
              for field, value in counts.items() if field != "verified_captures"), recomputed)
    status_section = draft.split("**Table V13S.", 1)[1].split("All 65 same-case", 1)[0]
    actual_rows = [line for line in status_section.splitlines() if line.startswith("| ")
                   and not line.startswith(("| Actual V13", "| ---"))]
    expected_rows = [f"| {status} | {count} |" for status, count in sorted(actual_statuses.items())]
    check("exact104status_table_keeps_missing_refused_failed_unclosed", actual_rows == expected_rows
          and sum(actual_statuses.values()) == 104 and provenance["native_status_counts"] == actual_statuses, actual_statuses)
    prior_path = ROOT / analysis["evidence"][1]["path"]
    prior = read(prior_path)
    old = {(row["case_id"], row["arm_id"]): row for row in prior["cells"]}
    current = {(row["case_id"], row["arm_id"]): row for row in cells}
    expected_pairs = [(case, arm) for case, arm in expected if arm in NATIVE]
    pairs = analysis["paired_ASGI_TCP_purchase_indicators"]
    fields = ("ASGI_purchase_observed", "TCP_purchase_observed", "ASGI_error_free_owned_cell_purchase_observed",
              "TCP_error_free_owned_cell_purchase_observed", "comparison_evaluable", "same_purchase_indicator")
    reconstructed = {}
    for key in expected_pairs:
        previous, now = old[key], current[key]
        evaluable = previous["evaluation_status"] == now["evaluation_status"] == VERIFIED_NATIVE
        reconstructed[key] = {"ASGI_purchase_observed": previous["purchase_completed"], "TCP_purchase_observed": now["purchase_completed"],
            "ASGI_error_free_owned_cell_purchase_observed": error_free(previous), "TCP_error_free_owned_cell_purchase_observed": error_free(now),
            "comparison_evaluable": evaluable,
            "same_purchase_indicator": previous["purchase_completed"] == now["purchase_completed"] if evaluable else None}
    check("all65purchase_and_errorfree_pairs_reconstructed_from_both_evaluations", len(pairs) == 65
          and [(row["case_id"], row["arm_id"]) for row in pairs] == expected_pairs
          and all({field: row[field] for field in fields} == reconstructed[row["case_id"], row["arm_id"]] for row in pairs),
          {"pairs": len(pairs), "prior_evaluation": identify(prior_path)})
    unresolved = sum(not row["comparison_evaluable"] for row in reconstructed.values())
    changes = sum(row["comparison_evaluable"] and row["same_purchase_indicator"] is False for row in reconstructed.values())
    check("unresolved_pairs_and_actual_indicator_changes_disclosed", analysis["unresolved_ASGI_TCP_pairs"] == unresolved
          and analysis["ASGI_TCP_purchase_indicator_changes"] == changes
          and provenance["native_ASGI_TCP_unresolved_pairs"] == unresolved
          and f"{changes} changed purchase indicators among evaluable pairs" in flat
          and f"{unresolved} non-evaluable pairs" in flat
          and "No equality or transport-success inference follows for a non-evaluable pair" in flat,
          {"changes": changes, "non_evaluable": unresolved})
    components = allocation["owned_components"]
    mandatory = {"scripts/ap2_native_guard_policy_v13.py", "scripts/print_ap2_owned_cell_diagnostics_v2.py",
                 "scripts/run_ap2_cell_with_safe_diagnostics_v2.py"}
    check("new_guard_and_diagnostic_sources_exactly_bound", mandatory.issubset(components)
          and all({key: identify(ROOT / name)[key] for key in ("bytes", "sha256")} == expected for name, expected in components.items()),
          {"components": len(components), "mandatory": sorted(mandatory)})
    source_checks = []
    source_rows = analysis["matrix_capture_source_bindings"]
    for row, source in zip(cells, source_rows):
        if row["evaluation_status"] not in (VERIFIED_NATIVE, VERIFIED_BRIDGE):
            continue
        location = base / "extracted/matrix/cells" / row["id"]
        plan = read(location / "plan.json")
        exact = plan["owned_components"] == components and (location / "source-runner.py").read_bytes() == (ROOT / "scripts/ap2_reference_development_v13.py").read_bytes()
        exact = exact and all({key: identify(location / "owned-source" / name)[key] for key in ("bytes", "sha256")} == value for name, value in components.items())
        source_checks.append(exact and source["complete_owned_source_capture"] is True
            and not source["source_binding_errors"] and not source["missing_captured_components"]
            and source["verified_captured_components"] == len(components))
    check("verified_native_and_bridge_captures_have_exact_archived_runner_helper_sources", len(source_rows) == 104
          and [row["prefix"] for row in source_rows] == ["matrix/cells/" + row["id"] for row in cells]
          and all(source_checks), {"verified_source_captures": len(source_checks), "allocated_source_statuses": len(source_rows)})
    bridges = [row for row in cells if row["evaluation_status"] == VERIFIED_BRIDGE]
    check("bridge_initiations_not_full_fault_OTP_or_independent_tasks", all(row["bridge_continuation_unrealized_and_retained"] is True
          and row["repeated_bridge_prefix_and_initiation_slot"] is True
          and row["post_initiation_case_fault_or_OTP_branch_exercised"] is False and not row["purchase_completed"] for row in bridges)
          and "They do not become 39 independent tasks" in flat, {"verified_bridge_initiations": len(bridges)})
    check("purchase_suffix_and_stricter_process_indicator_do_not_become_gold", "Purchase, error-free owned-cell purchase and zero-exit/no-violation purchase remain separate indicators" in flat
          and "not unconditional original-task or human-gold success" in flat and "it also establishes no human gold" in flat,
          "Adverse suffix/process findings retained.")
    abstract = re.sub(r"\s+", " ", draft.split("## Abstract", 1)[1].split("## 1. Introduction", 1)[0])
    check("abstract_plainly_retains_unexecuted_V11_and_preallocation_V12", "V11 owned-TCP matrix remained unexecuted after a failed smoke capture" in abstract
          and "V12 failed during constructed controls before actual allocation" in abstract
          and "no matrix or transport-pair census" in abstract,
          "Planned slots are not silently described as executed experiments.")
    diagnostic = read(ROOT / "runs/ap2-native-bridge-development/v12/preallocation-failure-42915964952-1/result.json")
    check("V12_preallocation_diagnostic_has_no_synthetic104rows_or65pairs", diagnostic["status"] == "failed_before_actual_cell_allocation"
          and diagnostic["actual_allocated_cell_census"] is None and diagnostic["actual_transport_pair_census"] is None
          and all(identify(ROOT / item["path"]) == item for item in diagnostic["evidence"])
          and "neither 104 evaluated failures nor 65 actual transport pairs" in flat,
          {"actual_cells": None, "actual_pairs": None, "public_plan_only": 104})
    check("native_provider_fulltask_human_and_fullstudy_claim_limits_preserved", analysis["human_gold_validated"] is False
          and analysis["original_server_launch_qualification_claimed"] is False and analysis["bridge_continuation_success_inferred"] is False
          and provenance["publication_ready"] is False and provenance["human_scientific_review"] is False
          and provenance["full_original_study_complete"] is False and provenance["original_study_tasks"] == 96
          and provenance["original_study_paths"] == 288 and provenance["original_study_crossings"] == 96
          and "accountable human scientific review remain unresolved" in flat,
          {"tasks": 96, "paths": 288, "crossings": 96, "publication_ready": False, "human_review": False})
    check("no_drafting_application_evaluator_solver_or_provider_execution", provenance["new_App_model_solver_evaluator_provider_calls"] == 0,
          "Only stdlib file reads by builder and independent auditor.")
    broken, link_count = [], 0
    for path in (draft_path, ROOT / "docs/research/paper-artifact-guide-v13.md"):
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            link_count += 1
            parsed = urlparse(target)
            if not parsed.scheme:
                local = (path.parent / unquote(parsed.path)).resolve()
                if not local.is_relative_to(ROOT) or not local.exists():
                    broken.append(target)
    check("all_local_manuscript_and_guide_links_resolve", not broken, {"links": link_count, "broken": broken})
    check("no_future_run_or_template_placeholders_in_manuscript", not re.search(r"\{\{[^}]+\}\}|<actual-(?:analysis|retained|run)|TODO.*native", draft),
          "Manuscript generated only from actual completed source-bound evidence.")
    return {"schema_version": "paper-v13-independent-census-source-claim-audit/1", "reviewed_utc": datetime.now(timezone.utc).isoformat(),
        "passed": all(row["passed"] for row in checks), "checks": checks,
        "inputs": [identify(path) for path in (draft_path, provenance_path, analysis_path, evaluation_path,
            ROOT / "docs/research/paper-artifact-guide-v13.md", Path(__file__))],
        "new_application_evaluator_solver_checker_or_provider_calls": 0, "human_scientific_review": False,
        "limits": ["Independent numerical/source/claim audit, not accountable human scientific review or publication approval."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--native-analysis", type=Path, required=True)
    parser.add_argument("--native-base", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.parent != ROOT / "paper" or not output.name.startswith("working-draft-v13.audit") or output.suffix != ".json" or output.exists():
        raise ValueError("fresh_owned_V13_audit_output_required")
    value = audit(args.draft.resolve(), args.provenance.resolve(), args.native_analysis.resolve(), args.native_base.resolve())
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"passed": value["passed"], "failed_checks": [row["id"] for row in value["checks"] if not row["passed"]]}))
    raise SystemExit(0 if value["passed"] else 1)


if __name__ == "__main__":
    main()
