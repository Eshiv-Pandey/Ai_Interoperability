"""Additive binding of final V5 analyzer/integration controls and protocol.

Read-only owned stdlib checks; no original SDK/application/provider or network.
"""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PREVIOUS = ROOT / "runs/ap2-native-shopper-provider-development/v5/independent-prospective-review-v1"
SPEC = importlib.util.spec_from_file_location("_previous_V5_source_review", PREVIOUS / "review_prospective_v1.py")
H = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(H)
OUTPUT = Path(__file__).resolve().parent / "review.json"


def main():
    H.need(not OUTPUT.exists(), "exclusive_additive_review_required")
    previous = json.loads((PREVIOUS / "review.json").read_bytes())
    H.need(previous["status"] == "reviewed_for_one_bounded_adaptive_development_allocation"
           and not previous["material_consistency_questions"], "previous_scope_review_not_accepted")
    changed = {"scripts/analyze_ap2_native_shopper_provider_v5.py",
        "tests/test_ap2_native_shopper_provider_v5_analysis_integration.py",
        "docs/research/ap2-native-shopper-provider-protocol-v5.md"}
    current = []
    for source in previous["reviewed_sources"]:
        row = H.identity(ROOT / source["path"])
        if source["path"] not in changed:
            H.need(row == source, "previously_reviewed_unmodified_source_changed")
        current.append(row)
    expected = {"scripts/analyze_ap2_native_shopper_provider_v5.py": "57e8f78cd151ae332f4bdf4b8cbb162837c882909be035394fd67c3e636275d6",
        "tests/test_ap2_native_shopper_provider_v5_analysis_integration.py": "70be15fce72c04075d589b07f139c865676df08056a02d6375e8ff2f1d1eed73"}
    for name, sha in expected.items():
        H.need(H.identity(ROOT / name)["sha256"] == sha, "final_reviewed_analysis_source_changed")
    receipt_name = "runs/ap2-native-shopper-provider-development/v5/analysis-integration-controls-v1/result.json"
    receipt = json.loads((ROOT / receipt_name).read_bytes())
    H.need(receipt["schema_version"] == "ap2-native-shopper-v5-analysis-integration-controls/1"
        and receipt["status"] == "passed" and receipt["returncode"] == 0 and receipt["tests_run"] == 16
        and receipt["source_before"] == receipt["source_after"]
        and receipt["original_application_calls"] == receipt["provider_calls"] == 0,
        "final_integration_control_outcome_or_source_binding_differs")
    for source in receipt["source_after"]:
        H.need(H.identity(ROOT / source["path"]) == source, "integrated_control_source_no_longer_current")
    runner = H.load("scripts/run_ap2_native_shopper_provider_v5.py", "_V5_final_binding_runner")
    analyzer = H.load("scripts/analyze_ap2_native_shopper_provider_v5.py", "_V5_final_binding_analyzer")
    plan = runner.check_plan(H.BASE)
    H.need(analyzer.check_plan(H.PreparedRead(), plan) == plan, "final_analyzer_fails_actual_prepared_plan")
    H.need(H.identity(H.BASE / "plan.json") == previous["prepared_plan"], "prepared_plan_was_rewritten")
    for source in previous["prepared_files"]:
        H.need(H.identity(ROOT / source["path"]) == source, "prepared_source_snapshot_was_rewritten")
    source = (ROOT / "scripts/analyze_ap2_native_shopper_provider_v5.py").read_text(encoding="utf-8")
    H.need("any(value is not True for value in closed_clients)" in source,
           "closed_client_flags_do_not_have_exact_boolean_check")
    protocol = (ROOT / "docs/research/ap2-native-shopper-provider-protocol-v5.md").read_text(encoding="utf-8")
    H.need("At this protocol's initial software checkpoint" in protocol,
           "protocol_initial_status_not_marked_historical")
    H.need(current == [H.identity(ROOT / row["path"]) for row in current], "sources_changed_during_binding")
    result = {"schema_version": "ap2-native-shopper-provider-V5-independent-prospective-source-review/2",
        "status": "reviewed_for_one_bounded_adaptive_development_allocation",
        "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
        "previous_full_source_and_bounds_review": H.identity(PREVIOUS / "review.json"),
        "previous_reviewer_source": H.identity(PREVIOUS / "review_prospective_v1.py"),
        "reviewed_sources": current, "prepared_plan": previous["prepared_plan"],
        "prepared_sources_unchanged": True, "actual_prepared_plan_analyzer_check_passed": True,
        "final_full_analyzer_integration_controls": H.identity(ROOT / receipt_name), "integration_controls_passed": 16,
        "declared_case": previous["declared_case"], "declared_case_denominator": 1,
        "limits": previous["limits"], "material_consistency_questions": [],
        "final_delta_findings": [
            "The real prepared source identity dictionary schema is checked exactly; the regression rejects bare SHA strings.",
            "Exactly two remote-client closure flags must each be literal True; integers 1 and missing/malformed flags are refused.",
            "Sixteen constructed full-analyzer controls cover actual preparation shape, preflight absence, source/fact types, session/event identity and actor diagnostic schema/bytes/counters/limits. They are not live observations.",
            "Current protocol explicitly describes its initial no-review/no-dispatch status as a historical checkpoint; later records must identify exact sources and allocation.",
            "Guard, worker, runner, workflow and prepared source bytes retain the earlier independently read execution/bounds scope. No extra case, quota or provider action is added."
        ],
        "inherited_scope_findings": previous["scope_findings"],
        "new_application_SDK_provider_solver_checker_calls_by_review": 0,
        "new_network_or_transport_control_executions_by_review": 0, "live_dispatch_by_review": False,
        "human_scientific_review": False, "percentage_credit_claimed": False,
        "reviewer_source": H.identity(Path(__file__))}
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "final_integration_controls": 16,
                     "actual_plan_check": True, "new_provider_calls": 0}))


if __name__ == "__main__":
    main()
