"""Independent claim/provenance audit of a real evidence-bound V11 manuscript.

Only stdlib file reads. Does not import the builder, actor or any evaluator.
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
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ("reference", "conventional", "recovery", "shared", "recovery_shared")
BRIDGES = ("amir_typed", "mg_typed", "mg_raw")


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


def audit(draft_path, provenance_path, native_analysis_path, native_base):
    text = draft_path.read_text(encoding="utf-8")
    flat = re.sub(r"\s+", " ", text)
    provenance, analysis = read(provenance_path), read(native_analysis_path)
    run = read(native_base / "github-run.json")
    evaluation_path = native_base / "extracted/independent-evaluation/result.json"
    evaluation = read(evaluation_path)
    execution = read(native_base / "extracted/matrix/execution-results.json")
    manifest = read(native_base / "extracted/matrix/public-manifest.json")
    allocation = read(native_base / "extracted/matrix/allocation-manifest.json")
    cells = evaluation["cells"]
    checks = []
    def check(name, value, evidence):
        checks.append({"id": name, "passed": bool(value), "evidence": evidence})
    title = (ROOT / "paper/working-draft-v7.md").read_text(encoding="utf-8").splitlines()[0]
    check("registered_title_and_full_original_scope_preserved", text.splitlines()[0] == title
          and provenance["registered_title"] == title[2:] and provenance["original_full_scope_revised"] is False,
          title)
    check("draft_bound_to_current_build_provenance", hashlib.sha256(text.encode()).hexdigest() == provenance["paper_sha256"], identify(draft_path))
    check("all_build_inputs_still_match_exact_bytes", all(identify(ROOT / item["path"]) == item for item in provenance["inputs"]), len(provenance["inputs"]))
    check("actual_retained_run_identity", run["status"] == "completed" and run["id"] == provenance["native_run_id"]
          and run["run_attempt"] == provenance["native_run_attempt"]
          and native_base.name == f"retained-{run['id']}-{run['run_attempt']}" and run["html_url"] in text,
          {"id": run["id"], "attempt": run["run_attempt"]})
    check("analysis_bound_to_actual_evaluation", analysis["schema_version"] == "ap2-v11-native-bridge-development-analysis/1"
          and analysis["status"] == "analyzed_all_allocated_cells" and analysis["evidence"][0] == identify(evaluation_path),
          identify(native_analysis_path))
    check("every_analysis_source_still_matches_exact_bytes",
          all(identify(ROOT / item["path"]) == item for item in analysis["evidence"]), len(analysis["evidence"]))
    check("actual_completed_API_archive_selected_extraction_binding",
          archived_evidence_matches(native_base, [ROOT / item["path"] for item in analysis["evidence"]]),
          identify(native_base / "artifact.zip"))
    expected = [(case["id"], arm["id"]) for case in manifest["cases"] for arm in manifest["arms"]]
    check("104_cells_65_native_39_bridge_13_cases_all_retained", len(cells) == len(set(expected)) == 104
          and [(row["case_id"], row["arm_id"]) for row in cells] == expected
          and [(row["case_id"], row["arm_id"]) for row in execution["cells"]] == expected
          and [(row["case_id"], row["arm_id"]) for row in allocation["cells"]] == expected
          and tuple(row["id"] for row in manifest["arms"]) == NATIVE + BRIDGES
          and len(manifest["cases"]) == 13 and analysis["native_payment_tool_cells"] == 65 and analysis["bridge_initiation_cells"] == 39,
          {"allocated": len(cells), "native": sum(row["arm_id"] in NATIVE for row in cells), "bridge": sum(row["arm_id"] in BRIDGES for row in cells)})
    processes = {(row["case_id"], row["arm_id"]): row for row in execution["cells"]}
    table_checks = []
    expected_arm_table = []
    for arm in NATIVE + BRIDGES:
        rows = [row for row in cells if row["arm_id"] == arm]
        closed = sum(processes[row["case_id"], arm]["returncode"] is not None for row in rows)
        purchases = sum(row.get("purchase_completed") is True for row in rows)
        error_free = sum(row.get("purchase_completed") is True and not row.get("source_errors") and row.get("actor_error_type") is None for row in rows)
        strict = sum(row.get("purchase_completed") is True and not row.get("source_errors") and row.get("actor_error_type") is None
                     and row["returncode"] == 0 and not row.get("safety_violations") for row in rows)
        table = f"| {arm} | 13 | {closed} | {purchases} | {error_free} | {strict} |"
        expected_arm_table.append(table)
        table_checks.append(table in text and analysis["arm_summaries"][arm]["purchase_observations"] == purchases
                            and analysis["arm_summaries"][arm]["error_free_owned_cell_purchase_observations"] == error_free
                            and analysis["arm_summaries"][arm]["error_free_zero_returncode_no_violation_purchase_observations"] == strict
                            and analysis["arm_summaries"][arm]["closed_process_outcomes"] == closed)
    check("every_native_and_bridge_table_indicator_recomputed", all(table_checks), {"arm_rows": len(table_checks)})
    section = text.split("**Table NT.", 1)[1].split("**Table NS.", 1)[0]
    actual_arm_table = [row for row in section.splitlines() if any(row.startswith("| " + arm + " |") for arm in NATIVE + BRIDGES)]
    check("exact_eight_arm_numerical_table_without_duplicate_or_invented_rows", actual_arm_table == expected_arm_table,
          {"expected_rows": len(expected_arm_table), "actual_rows": len(actual_arm_table)})
    statuses = dict(Counter(row["evaluation_status"] for row in cells))
    check("every_failed_unknown_missing_unclosed_status_retained", sum(statuses.values()) == 104
          and all(f"| {name} | {count} |" in text for name, count in statuses.items())
          and provenance["native_status_counts"] == statuses, statuses)
    verified_native = sum(row["evaluation_status"] == "original_application_capture_verified" for row in cells)
    verified_bridge = sum(row["evaluation_status"] == "original_bridge_initiation_capture_verified" for row in cells)
    check("actual_capture_counts_and_no_failed_smoke_performance_inference",
          f"{verified_native}/65 native payment-tool captures" in flat and f"{verified_bridge}/39 bridge initiation captures" in flat
          and "Missing or refused captures supply no native performance evidence" in flat
          and "not measurements of native payment-tool or bridge throughput, latency, success probability or provider quality" in flat,
          {"verified_native": verified_native, "verified_bridge": verified_bridge})
    pairs = analysis["paired_ASGI_TCP_purchase_indicators"]
    prior_path = ROOT / analysis["evidence"][1]["path"]
    prior = read(prior_path)
    old_cells = {(row["case_id"], row["arm_id"]): row for row in prior["cells"]}
    new_cells = {(row["case_id"], row["arm_id"]): row for row in cells}
    expected_pairs = [(case, arm) for case, arm in expected if arm in NATIVE]
    reconstructed = {}
    for key in expected_pairs:
        old, new = old_cells[key], new_cells[key]
        evaluable = old["evaluation_status"] == new["evaluation_status"] == "original_application_capture_verified"
        reconstructed[key] = {"comparison_evaluable": evaluable,
                              "ASGI_purchase_observed": old["purchase_completed"],
                              "TCP_purchase_observed": new["purchase_completed"],
                              "ASGI_error_free_owned_cell_purchase_observed": old["evaluation_status"] == "original_application_capture_verified"
                                  and old["purchase_completed"] and not old.get("source_errors") and old.get("actor_error_type") is None,
                              "TCP_error_free_owned_cell_purchase_observed": new["evaluation_status"] == "original_application_capture_verified"
                                  and new["purchase_completed"] and not new.get("source_errors") and new.get("actor_error_type") is None,
                              "same_purchase_indicator": old["purchase_completed"] == new["purchase_completed"] if evaluable else None}
    pair_fields = tuple(next(iter(reconstructed.values())))
    pair_identity = [(row["case_id"], row["arm_id"]) for row in pairs]
    check("all65_pairs_independently_match_both_original_evaluations", len(pairs) == 65
          and len(set(pair_identity)) == 65 and set(pair_identity) == set(expected_pairs)
          and all({field: row[field] for field in pair_fields} == reconstructed[row["case_id"], row["arm_id"]] for row in pairs),
          {"prior_evaluation": identify(prior_path), "current_evaluation": identify(evaluation_path), "pairs": len(pairs)})
    changed = sum(row["comparison_evaluable"] and row["same_purchase_indicator"] is False for row in reconstructed.values())
    unresolved = sum(not row["comparison_evaluable"] for row in reconstructed.values())
    check("all65_pairs_and_unresolved_outcomes_disclosed", len(pairs) == 65
          and analysis["ASGI_TCP_purchase_indicator_changes"] == changed and analysis["unresolved_ASGI_TCP_pairs"] == unresolved
          and f"{changed} changed purchase indicators" in flat and f"{unresolved} unresolved pairs" in flat
          and "An unresolved pair has no equality or transport-success inference" in flat,
          {"pairs": len(pairs), "changes": changed, "unresolved": unresolved})
    verified_bridges = [row for row in cells if row["arm_id"] in BRIDGES and row["evaluation_status"] == "original_bridge_initiation_capture_verified"]
    check("bridge_prefixes_not_full_fault_or_OTP_tasks", all(row["bridge_continuation_unrealized_and_retained"] is True
          and row["post_initiation_case_fault_or_OTP_branch_exercised"] is False and not row["purchase_completed"] for row in verified_bridges)
          and "not 39 independently qualified tasks" in flat and "not an equal-budget held-out or live-model trial" in flat,
          {"verified_bridge_prefixes": len(verified_bridges)})
    check("owned_TCP_not_original_native_launcher_qualification", "does not establish qualification of the original native server launcher" in flat
          and "owned bootstrap" in flat and "loopback TCP sockets" in flat
          and "For capture-verified cells" in flat and "only where the native capture is verified" in flat
          and analysis["original_server_launch_qualification_claimed"] is False,
          "Exact observed original Apps served by owned Uvicorn, original launcher remains unqualified.")
    check("purchase_and_error_free_indicators_remain_separate", "Purchase and error-free owned-cell purchase remain separate indicators" in flat
          and "neither indicator alone is unconditional original task/gold success" in flat,
          "Suffix errors must not become whole-task successes.")
    check("method_meter_cost_asymmetry_and_no_general_novelty_upgrade", "not equal CPU or hardware budgets" in flat
          and "direct language's key serialization and domain-key construction" in flat
          and "do not alone establish a new CEGAR, memoization or constraint-pruning principle" in flat,
          "Mechanics comparison and declared costs are distinct from novelty/practical speed.")
    check("AgentOps_d03_decision_gap_and_both_historical_failures", "agentops-d03-restart-pause" in text
          and "not a validated evidence-supported remediation choice" in flat
          and "The two historical failures remain failed" in flat
          and "agentops-h19-resolved-remediation-stop" in text and "agentops-h24-persistence-redaction" in text
          and "makes no save call and recalls zero notes" in flat,
          "No retrospective gold or success upgrade.")
    prior_ap2 = read(ROOT / "runs/ap2-reference-development/v5/retained-42881390576-2/extracted/independent-evaluation/result.json")
    prior_counts = {arm: sum(row["purchase_completed"] for row in prior_ap2["cells"] if row["arm_id"] == arm) for arm in NATIVE}
    numeric = read(ROOT / "runs/ap2-reference-development/v5/retained-42881390576-2/numeric-peer-review-v1.json")
    check("frozen_ASGI36_purchases_vs31_error_free_owned_captures_preserved",
          list(prior_counts.values()) == [11, 3, 10, 3, 9] and sum(prior_counts.values()) == 36
          and numeric["total_strict_error_free_owned_cell_purchases"] == 31
          and "31/65 error-free owned-cell purchases" in flat and "36 purchase observations" in flat,
          {"purchase_counts": prior_counts, "error_free_owned": 31})
    codec_base = ROOT / "runs/ci-refutation-prefix-dag-v2/retained-42910442359-1"
    comparison = read(ROOT / "docs/research/refutation-prefix-dag-comparison-v2.json")
    peer = read(ROOT / "docs/research/refutation-prefix-dag-peer-review-v2.json")
    appendix_audit = read(ROOT / "paper/refutation-prefix-dag-appendix-v2.audit.json")
    reproduction = read(codec_base / "extracted/result.json")
    rows = reproduction["rows"]
    aggregate = {key: sum(row[key] for row in rows) for key in ("old_bytes", "dag_bytes", "direct_bytes")}
    aggregate.update({"smaller": sum(row["dag_bytes"] < row["old_bytes"] for row in rows),
                      "larger": sum(row["dag_bytes"] > row["old_bytes"] for row in rows),
                      "equal": sum(row["dag_bytes"] == row["old_bytes"] for row in rows)})
    expected_codec = {"old_bytes": 15128, "dag_bytes": 11918, "direct_bytes": 7760, "smaller": 2, "larger": 24, "equal": 0}
    check("all26_codec_bytes_and_growth_counts_independently_recomputed_from_receipt_rows",
          len(rows) == len({row["case_id"] for row in rows}) == 26 and aggregate == expected_codec
          and comparison["aggregate"] == peer["retained_comparison"]["aggregate"] == reproduction["aggregate"] == aggregate
          and "| All 26 unsupported cases | 15,128 bytes | 11,918 bytes | 7,760 bytes |" in text
          and "Two DAG proofs shrink and 24 grow; none tie" in flat
          and "The direct proof remains smaller in aggregate" in flat,
          aggregate)
    retained = ROOT / comparison["input"]["path"]
    raw_rows = [json.loads(line) for line in retained.read_text(encoding="utf-8").splitlines()]
    negatives = {row["case_id"]: row for row in raw_rows if row["algorithms"]["shared_lift"]["execution"]["result"]["decision"] == "unsupported"}
    raw_size_checks = []
    serializer = dict(sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    for row in rows:
        old = negatives[row["case_id"]]["algorithms"]["shared_lift"]["execution"]["result"]["certificate"]
        direct = negatives[row["case_id"]]["algorithms"]["direct_pruned"]["execution"]["result"]["certificate"]
        old_raw, direct_raw = json.dumps(old, **serializer).encode(), json.dumps(direct, **serializer).encode()
        raw_size_checks.append(len(old_raw) == row["old_bytes"] and len(direct_raw) == row["direct_bytes"]
            and hashlib.sha256(old_raw).hexdigest() == row["old_certificate_sha256"]
            and hashlib.sha256(direct_raw).hexdigest() == row["direct_certificate_sha256"]
            and row["restored_certificate_sha256"] == row["old_certificate_sha256"])
    check("all26_old_and_direct_sizes_match_actual_unchanged_retained_certificates",
          len(raw_rows) == 66 and set(negatives) == {row["case_id"] for row in rows} and all(raw_size_checks),
          {"retained_rows": len(raw_rows), "selected": len(negatives), "source": identify(retained)})
    check("codec_appendix_peer_and_fresh_archive_hashes_current",
          appendix_audit["appendix"] == identify(ROOT / "paper/refutation-prefix-dag-appendix-v2.md")
          and all(identify(ROOT / item["path"]) == item for item in appendix_audit["evidence_fingerprints"])
          and archived_evidence_matches(codec_base, [codec_base / "extracted/result.json", codec_base / "extracted/controls.stderr"]),
          identify(codec_base / "artifact.zip"))
    controls = (codec_base / "extracted/controls.stderr").read_text(encoding="utf-8")
    codec_run = read(codec_base / "github-run.json")
    check("fresh31_constructed_controls_all26_roundtrips_and_three_defect_fixes_scoped",
          comparison["tests_passed"] == 31 and re.search(r"Ran 31 tests in [0-9.]+s\s+OK\s*$", controls)
          and codec_run["status"] == "completed" and codec_run["conclusion"] == "success" and codec_run["html_url"] in text
          and reproduction["passed"] is True and all(row["exact_ordered_object_and_canonical_byte_round_trip"] for row in rows)
          and len(peer["resolved_v1_findings"]) == 3
          and all(row["v2_status"].startswith("fixed_and_independently_") for row in peer["resolved_v1_findings"])
          and "oversized integer conversion, unbounded extra-field traversal and missing complete-input-envelope size checks" in flat,
          {"tests": 31, "round_trips": 26, "fixed_v1_defects": 3, "run_id": codec_run["id"]})
    check("codec_semantic_evidence_inherited_no_solver_checker_speed_novelty_upgrade",
          reproduction["new_admission_solver_calls"] == reproduction["new_semantic_checker_calls"] == 0
          and comparison["novelty_established"] is False and comparison["faster_checker_established"] is False
          and "Existing semantic-checker outcomes are inherited evidence" in flat
          and "They establish no solver, checker, memory, latency, admission-coverage or business-utility improvement" in flat
          and "separate default codec allowance of 2,000,000 operations" in flat and "100,000-unit allowance" in flat,
          "Byte counts and constructed controls do not become speed, utility or scientific approval.")
    history_checks = []
    for version, run_id in ((8, 42897325489), (9, 42902256098), (10, 42905259371)):
        old_base = ROOT / f"runs/ap2-native-bridge-development/v{version}/retained-{run_id}-1"
        old_eval = read(old_base / "extracted/independent-evaluation/result.json")
        failure = read(old_base / "extracted/smoke/conventional/worker-failure.json")
        history_checks.append(old_eval["declared_cells"] == len(old_eval["cells"]) == 104
            and old_eval["totals"]["missing_cells"] == 104 and old_eval["totals"]["verified_captures"] == 0
            and f"| V{version} ({run_id}) | 104/104 | 0 | `{failure['error_type']}` |" in text)
    check("frozen_V8_V9_V10_failures_keep_full104denominators", all(history_checks), {"allocations": 3, "missing_each": 104})
    check("full96task288path96crossing_study_and_human_novelty_review_unresolved",
          provenance["original_study_tasks"] == provenance["original_study_crossings"] == 96
          and provenance["original_study_paths"] == 288 and provenance["publication_ready"] is False
          and provenance["full_original_study_complete"] is False and provenance["human_scientific_review"] is False
          and "96 tasks, three paths (288 path cells) and 96 crossing observations" in flat
          and "accountable human novelty/feasibility/scientific review remain unresolved" in flat,
          {"tasks": 96, "paths": 288, "crossings": 96, "human_review": False})
    smoke_base = native_base / "extracted/smoke/conventional"
    worker, outcome, separation = (read(smoke_base / name) for name in ("result.json", "application-outcome.json", "actor-input-separation.json"))
    guards = [json.loads(line) for line in (smoke_base / "actor-guard-denials.jsonl").read_text(encoding="utf-8").splitlines()]
    stages = [json.loads(line) for line in (smoke_base / "worker-stages.jsonl").read_text(encoding="utf-8").splitlines()]
    guard_census = dict(Counter(row["guard_code"] for row in guards))
    check("actual_smoke_actor_zero_exit_not_native_capture_or_task_success",
          worker["returncode"] == 0 and worker["native_qualification_established"] is False
          and outcome["decision"] == "prefix_incomplete" and outcome["error_type"] == "A2AClientHTTPError"
          and outcome["final_task"] is None and len(stages) == 9
          and guard_census == {"actor_private_evaluator_or_saved_credential_read_denied": 1,
              "native_actor_unowned_network_operation_denied": 2, "native_actor_unallocated_descendant_process_denied": 1}
          and len(guards) == separation["guard_diagnostic_rows"] == 4
          and "no final task" in flat and "There is no completed smoke-evaluation result" in flat
          and "An actor exit code of zero does not establish capture verification, task success or native qualification" in flat
          and "not a measured zero-percent task-success trial" in flat
          and archived_evidence_matches(native_base, [smoke_base / name for name in ("result.json", "application-outcome.json",
              "actor-input-separation.json", "actor-guard-denials.jsonl", "worker-stages.jsonl")]),
          {"actor_returncode": worker["returncode"], "outcome": outcome["decision"], "stage_rows": len(stages), "guard_census": guard_census})
    evaluator = (ROOT / "scripts/evaluate_ap2_native_bridge_matrix_v11.py").read_text(encoding="utf-8")
    check("actual_guard_counts_violate_unchanged_evaluator_gate",
          separation["denials"]["private_reads_blocked"] == 1
          and separation["denials"]["external_network_operations_blocked"] == 2
          and separation["denials"]["unallocated_descendant_processes_blocked"] == 1
          and "separation['denials']['external_network_operations_blocked'] == 0" in evaluator
          and "separation['denials']['unallocated_descendant_processes_blocked'] == 0" in evaluator
          and "native_unexpected_private_network_or_process_guard_interference" in evaluator
          and "native_unexpected_private_network_or_process_guard_interference" in text,
          "Source-bound failed-smoke rejection condition; no evaluator rerun or matrix purchase grade.")
    targets = re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text)
    broken = []
    for target in targets:
        parsed = urlparse(target)
        if not parsed.scheme:
            path = (draft_path.parent / unquote(parsed.path)).resolve()
            if not path.is_relative_to(ROOT) or not path.exists():
                broken.append(target)
    check("all_local_manuscript_links_resolve", not broken, {"broken": broken, "links": len(targets)})
    check("no_future_run_or_template_placeholder", not re.search(r"\{\{[^}]+\}\}|<actual-(?:analysis|retained)|TODO.*native", text), "Publication is built only after actual evidence exists.")
    return {"schema_version": "paper-v11-independent-claim-provenance-audit/1", "reviewed_utc": datetime.now(timezone.utc).isoformat(),
            "passed": all(row["passed"] for row in checks), "checks": checks,
            "inputs": [identify(path) for path in (draft_path, provenance_path, native_analysis_path, evaluation_path, Path(__file__))],
            "human_scientific_review": False, "new_App_model_solver_provider_calls": 0,
            "limits": ["Independent manuscript claim/census/provenance review, not independent human novelty review, full task qualification, provider quality, source-to-model completeness or publication approval."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--native-analysis", type=Path, required=True)
    parser.add_argument("--native-base", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.parent != ROOT / "paper" or not output.name.startswith("working-draft-v11.audit") or output.suffix != ".json" or output.exists():
        raise ValueError("fresh_owned_v11_audit_output_required")
    value = audit(args.draft.resolve(), args.provenance.resolve(), args.native_analysis.resolve(), args.native_base.resolve())
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"passed": value["passed"], "failed_checks": [row["id"] for row in value["checks"] if not row["passed"]]}))
    raise SystemExit(0 if value["passed"] else 1)


if __name__ == "__main__":
    main()
