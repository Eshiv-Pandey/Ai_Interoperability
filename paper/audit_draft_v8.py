"""Independent claim/provenance audit of a real evidence-bound V8 manuscript.

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
    raw = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


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
    check("analysis_bound_to_actual_evaluation", analysis["schema_version"] == "ap2-v8-native-bridge-development-analysis/1"
          and analysis["status"] == "analyzed_all_allocated_cells" and analysis["evidence"][0] == identify(evaluation_path),
          identify(native_analysis_path))
    check("every_analysis_source_still_matches_exact_bytes",
          all(identify(ROOT / item["path"]) == item for item in analysis["evidence"]), len(analysis["evidence"]))
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
    for arm in NATIVE + BRIDGES:
        rows = [row for row in cells if row["arm_id"] == arm]
        closed = sum(processes[row["case_id"], arm]["returncode"] is not None for row in rows)
        purchases = sum(row.get("purchase_completed") is True for row in rows)
        error_free = sum(row.get("purchase_completed") is True and not row.get("source_errors") and row.get("actor_error_type") is None for row in rows)
        table = f"| {arm} | 13 | {closed} | {purchases} | {error_free} |"
        table_checks.append(table in text and analysis["arm_summaries"][arm]["purchase_observations"] == purchases
                            and analysis["arm_summaries"][arm]["error_free_owned_cell_purchase_observations"] == error_free)
    check("every_native_and_bridge_table_indicator_recomputed", all(table_checks), {"arm_rows": len(table_checks)})
    statuses = dict(Counter(row["evaluation_status"] for row in cells))
    check("every_failed_unknown_missing_unclosed_status_retained", sum(statuses.values()) == 104
          and all(f"| {name} | {count} |" in text for name, count in statuses.items())
          and provenance["native_status_counts"] == statuses, statuses)
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
    return {"schema_version": "paper-v8-independent-claim-provenance-audit/1", "reviewed_utc": datetime.now(timezone.utc).isoformat(),
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
    if output.parent != ROOT / "paper" or "v8" not in output.name or output.exists():
        raise ValueError("fresh_owned_v8_audit_output_required")
    value = audit(args.draft.resolve(), args.provenance.resolve(), args.native_analysis.resolve(), args.native_base.resolve())
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"passed": value["passed"], "failed_checks": [row["id"] for row in value["checks"] if not row["passed"]]}))
    raise SystemExit(0 if value["passed"] else 1)


if __name__ == "__main__":
    main()
