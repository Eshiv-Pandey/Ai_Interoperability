"""Bind the independent V2 helper safety read review to its actual local receipt.

This is a stdlib read review only. No restoration, audit subprocess, application,
SDK, provider, solver, evaluator or checker is executed by this reviewer.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "runs/v1-release-paper/independent-v2-read-review-20261112-1"
GUIDE = "docs/research/paper-v15-offline-restoration-guide-v2.md"
GUIDE_SNAPSHOT = "runs/v1-release-paper/exact-inputs-v2-local-20261112-1/executed-guide-v2.md"


def need(value, message):
    if not value:
        raise ValueError(message)


def identity(name):
    path = ROOT / name
    need(path.is_file() and not path.is_symlink(), "regular_review_input_required")
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while raw := stream.read(262144):
            digest.update(raw)
            size += len(raw)
    return {"path": name, "bytes": size, "sha256": digest.hexdigest()}


def executed_identity(name):
    if name != GUIDE:
        return identity(name)
    original = identity(GUIDE_SNAPSHOT)
    original["path"] = GUIDE
    need((ROOT / GUIDE).read_bytes() == (ROOT / GUIDE_SNAPSHOT).read_bytes().replace(
        b"Python 3.10 or later", b"Python 3.12 or later"), "guide_correction_is_not_exact_minimum_version_change")
    return original


def load(name):
    return json.loads((ROOT / name).read_bytes())


def main():
    need(not OUTPUT.exists(), "fresh_review_allocation_required")
    controls_name = "runs/v1-release-paper/controls-v2-20261112-1/result.json"
    local_name = "runs/v1-release-paper/exact-inputs-v2-local-20261112-1/result.json"
    controls, local = load(controls_name), load(local_name)
    need(controls["schema_version"] == "v15-paper-restoration-constructed-controls/2"
         and controls["status"] == "passed_observed_unittest_controls" and controls["tests"] == 10
         and controls["exit_code"] == controls["errors"] == controls["failures"] == controls["skips"] == 0
         and controls["constructed_controls_are_not_actual_paper_results"] is True
         and controls["positive_restoration_fixture_uses_mock_audit"] is True,
         "constructed_control_receipt_scope_or_outcome_differs")
    for source in controls["sources"]:
        need(executed_identity(source["path"]) == source, "current_source_differs_from_tested_controls")
    need(local["schema_version"] == "v15-exact-paper-input-restoration-verification/2"
         and local["status"] == "passed_exact_V15_paper_inputs_and_read_audit"
         and local["phase"] == "complete" and local["all_required_input_bytes_verified"] == 3468
         and local["existing_exact_required_inputs"] == 3468
         and local["missing_required_input_count"] == local["restored_required_input_count"] == 0
         and local["source_group_count"] == len(local["archives"]) == 20
         and local["needed_archive_member_count"] == 3245
         and local["needed_archive_member_bytes"] == 69361556
         and local["all_source_preflight_passed_before_evidence_mutation"] is True
         and local["sealed_paper_and_V1_V2_package_sources_unchanged"] is True
         and local["new_application_SDK_provider_solver_checker_or_evaluator_executions"] == 0
         and local["full_extraction_or_runtime_qualification"] is False
         and local["existing_files_overwritten"] is False,
         "actual_local_V2_receipt_or_scope_differs")
    need(local["package_sources_before"] == local["package_sources_after"], "package_source_snapshots_differ")
    for source in local["package_sources_after"]:
        need(executed_identity(source["path"]) == source, "current_package_differs_from_local_check")
    command = local["paper_read_audit_command"]
    need(command["returncode"] == 0 and command["timed_out"] is False
         and command["argv"][1:5] == ["-I", "-S", "-B", "paper/audit_draft_v15.py"]
         and command["log_byte_limit_each"] == 1048576
         and all(row["retained_bytes"] <= 1048576 for row in command["logs"]),
         "actual_pinned_read_auditor_command_binding_differs")
    audit_record = local["fresh_paper_audit"]
    need(identity(audit_record["path"]) == audit_record, "actual_audit_identity_differs")
    audit = load(audit_record["path"])
    need(audit["passed"] is True and audit["checks_passed"] == 19, "actual_V15_read_audit_not_passed")
    clean_base = "runs/v1-release-paper/clean-47439ff5-v2-1/"
    clean_name, context_name = clean_base + "result.json", clean_base + "context.json"
    clean, context = load(clean_name), load(context_name)
    need(clean["status"] == "passed_exact_V15_paper_inputs_and_read_audit"
         and clean["all_required_input_bytes_verified"] == 3468
         and clean["existing_exact_required_inputs"] == 463
         and clean["missing_required_input_count"] == clean["restored_required_input_count"] == 3005
         and clean["restored_member_count"] == 2995 and clean["restored_archive_count"] == 10
         and len(clean["restored_required_inputs"]) == 3005
         and clean["all_source_preflight_passed_before_evidence_mutation"] is True
         and clean["package_sources_before"] == clean["package_sources_after"],
         "fresh_checkout_restoration_receipt_differs")
    need(context["checkout_head_before_execution"] == "47439ff5ff6a40b7a5553c90780da57ab79149a7"
         and context["initial_git_status_porcelain"] == "" and context["returncode"] == 0
         and context["python_version"].startswith("3.13.1")
         and context["new_original_application_or_provider_calls"] == 0,
         "fresh_checkout_context_differs")
    for source in clean["package_sources_after"]:
        need(executed_identity(source["path"]) == source, "fresh_checkout_executed_package_differs")
    for source in load(clean_base + "manifest.json")["files"]:
        need(identity(source["path"]) == source, "copied_fresh_receipt_or_log_identity_differs")
    clean_audit = clean["fresh_paper_audit"]
    need(identity(clean_audit["path"]) == clean_audit and load(clean_audit["path"])["passed"] is True
         and load(clean_audit["path"])["checks_passed"] == 19, "fresh_checkout_audit_identity_or_outcome_differs")
    provenance = load("paper/working-draft-v15.provenance.json")
    inputs = {row["path"]: {key: row[key] for key in ("path", "bytes", "sha256")} for row in provenance["inputs"]}
    need(len(inputs) == 3468, "exact_original_input_census_required")
    restored = clean["restored_required_inputs"]
    need(len({row["path"] for row in restored}) == 3005, "restored_input_paths_not_unique")
    for row in restored:
        need({key: row[key] for key in ("path", "bytes", "sha256")} == inputs.get(row["path"]),
             "fresh_restored_input_not_same_frozen_provenance_identity")
    clean_command = clean["paper_read_audit_command"]
    need(clean_command == load(clean_base + "paper-read-audit.command.json")
         and clean_command["returncode"] == 0 and clean_command["timed_out"] is False
         and clean_command["argv"][1:5] == ["-I", "-S", "-B", "paper/audit_draft_v15.py"],
         "fresh_checkout_pinned_auditor_command_differs")
    report = {
        "schema_version": "v15-restoration-V2-independent-safety-read-review/1",
        "status": "helper_safety_read_local_and_fresh_restoration_receipts_verified",
        "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
        "sources": controls["sources"], "controls_receipt": identity(controls_name),
        "actual_local_receipt": identity(local_name), "actual_local_read_audit": audit_record,
        "constructed_controls": 10, "actual_local_exact_required_inputs": 3468,
        "actual_local_restored_inputs": 0, "actual_local_source_groups": 20,
        "actual_local_selected_member_count": 3245, "actual_local_selected_member_bytes": 69361556,
        "actual_local_read_audit_checks": 19, "material_consistency_questions": [],
        "actual_fresh_checkout_receipt": identity(clean_name), "actual_fresh_checkout_context": identity(context_name),
        "actual_fresh_checkout_read_audit": clean_audit, "actual_fresh_restored_inputs": 3005,
        "actual_fresh_restored_members": 2995, "actual_fresh_restored_archives": 10,
        "fresh_execution_head": context["checkout_head_before_execution"],
        "executed_guide_snapshot": identity(GUIDE_SNAPSHOT), "published_guide": identity(GUIDE),
        "fresh_restoration_observed_by_root_tools_and_bound_as_retained_evidence": True,
        "independent_fresh_checkout_restoration_observed_by_this_reviewer": False,
        "new_executions_by_this_reviewer": {"restoration": 0, "auditor_subprocess": 0,
            "application": 0, "SDK": 0, "provider": 0, "solver": 0, "evaluator": 0, "checker": 0},
        "safety_read_findings": [
            "All source archives and selected needed-member hashes are preflighted globally before any evidence publication.",
            "Frozen provenance/census/package identities bind the required paths and the unchanged stdlib V15 read auditor.",
            "Portable names, linked-path refusal, resolve-alias refusal, filesystem spellings and exclusive creation protect evidence targets.",
            "All ZIP central names/types/sizes/compression/membership and prefix conflicts are checked; unneeded SDK payloads are not extracted.",
            "Whole archive/part identities and bounded selected-member streaming precede exclusive publication; existing required drift is refused.",
            "The ten constructed controls visibly mark their mocked positive auditor and are distinct from the actual local 19-check audit.",
            "The local receipt verifies an already complete checkout and provides no actual missing-input restoration credit.",
            "The pure read auditor has no subprocess/importlib/application execution; helper subprocess timeout and log limits cover that command."
        ],
        "scope_limit": "Independent source safety read and identity-bound inspection of local and root-observed fresh V2 restoration receipts; reviewer performs no restoration or runtime execution. Original research/scientific/human qualification is not claimed.",
        "review_source": identity("scripts/review_v15_paper_restoration_v2.py"),
    }
    OUTPUT.mkdir(parents=True)
    with (OUTPUT / "review.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": report["status"], "actual_local_read_audit_checks": 19,
                      "actual_local_restored_inputs": 0}))


if __name__ == "__main__":
    main()
