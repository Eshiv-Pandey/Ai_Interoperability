"""Publish V1 implementation status only from passed, scope-bound release evidence.

This leaves the original whole-project register and scientific gates unchanged.
It reads existing evidence and writes two new release records; no experiments,
application calls, provider calls or human reviews are performed.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE = "runs/overnight-acceptance/v1-20261111-1/acceptance.json"
PAPER = "runs/v1-release-paper/clean-47439ff5-v2-1/result.json"
CONTEXT = "runs/v1-release-paper/clean-47439ff5-v2-1/context.json"
WHOLE = "docs/research/project-completion-status-v1.json"
TARGET = ROOT / "docs/research/v1-release-status-20261112.json"
NOTE = ROOT / "docs/research/v1-release-status-20261112.md"
IDS = ("algorithm", "comparison", "analysis", "clean_reproduction", "agentops", "task_bank", "ap2", "paper")


def need(value, reason):
    if not value:
        raise ValueError(reason)


def read(path):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    need(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(ROOT), "regular_workspace_evidence_required")
    return json.loads(path.read_bytes())


def record(path):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    h, count = hashlib.sha256(), 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(262144), b""):
            count += len(block)
            h.update(block)
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": count, "sha256": h.hexdigest()}


def finalize(software_path):
    need(not TARGET.exists() and not NOTE.exists(), "existing_release_records_are_never_overwritten")
    before_whole = record(WHOLE)
    acceptance, paper, context, whole = [read(name) for name in (ACCEPTANCE, PAPER, CONTEXT, WHOLE)]
    software = read(software_path)
    need(acceptance["accepted_criteria"] == 7 and acceptance["total_criteria"] == 8
         and [row["id"] for row in acceptance["criteria"]] == list(IDS), "fixed_eight_implementation_criteria_required")
    for row in acceptance["criteria"]:
        expected = "pending_current_release_smoke" if row["id"] == "clean_reproduction" else "accepted"
        need(row["status"] == expected, "a_prior_fixed_criterion_is_not_accepted")
    need(software["status"] == "current_V1_software_Linux_qualification_verified"
         and software["run_id"] == 43079771054
         and software["head_sha"] == "577f34a82a32d3a891db2018a68823ba98f21e48"
         and software["archive_API_digest_and_all_members_verified"] is True
         and software["archive_members"] == 12999 and not software["material_consistency_questions"]
         and software["algorithm_comparisons"] == 1056 and software["reference_comparisons"] == 264
         and software["solver_certificate_rechecks"] == 683 and software["reference_certificate_rechecks"] == 172
         and software["eighth_release_software_criterion"] == "accepted_for_current_development_software_scope",
         "current_Linux_release_qualification_has_not_passed")
    need(paper["status"] == "passed_exact_V15_paper_inputs_and_read_audit"
         and paper["all_required_input_bytes_verified"] == 3468
         and paper["restored_required_input_count"] == 3005 and paper["restored_member_count"] == 2995
         and paper["restored_archive_count"] == 10 and paper["read_audit_checks_passed"] == 19
         and paper["sealed_paper_and_V1_V2_package_sources_unchanged"] is True
         and context["initial_git_status_porcelain"] == ""
         and context["checkout_head_before_execution"] == "47439ff5ff6a40b7a5553c90780da57ab79149a7",
         "actual_isolated_checkout_paper_restoration_has_not_passed")
    need(record(paper["fresh_paper_audit"]["path"]) == paper["fresh_paper_audit"], "fresh_paper_audit_bytes_changed")
    need(whole["whole_project_complete"] is False and whole["whole_project_progress_percent"] == 80,
         "original_whole_project_scope_or_estimate_changed")
    for key in ("whole_original_study_complete", "publication_ready", "human_gold_or_scientific_review"):
        need(software[key] is False, "scientific_or_human_review_credit_cannot_be_added")
    criteria = []
    for row in acceptance["criteria"]:
        evidence = list(row["evidence"])
        limit = row["claim_limit"]
        if row["id"] == "clean_reproduction":
            evidence.append(record(software_path)["path"])
            limit = "Fresh hosted Linux core/software proof at its recorded head; finite development profiles only. No application, provider, human-gold or full-study qualification."
        if row["id"] == "paper":
            evidence.extend((PAPER, CONTEXT, paper["fresh_paper_audit"]["path"]))
            limit = "Complete development manuscript and exact-input restoration from an initially clean checkout with the V15 read audit. Earlier numerical/semantic reviews are inherited after byte checks; final human scientific and publication decisions remain open."
        criteria.append({"id": row["id"], "criterion": row["criterion"], "weight": 12.5,
                         "status": "complete_for_declared_V1_scope", "evidence": evidence,
                         "claim_limit": limit})
    completed = datetime.now(timezone.utc)
    value = {"schema_version": "V1-implementation-development-paper-release/1",
             "completed_at_utc": completed.isoformat(), "deadline_utc": "2026-11-12T00:30:00+00:00",
             "completed_before_deadline": completed < datetime(2026, 11, 12, 0, 30, tzinfo=timezone.utc),
             "status": "complete_for_fixed_V1_implementation_and_development_paper_scope",
             "V1_complete": True, "V1_progress_percent": sum(row["weight"] for row in criteria),
             "accepted_criteria": 8, "total_criteria": 8, "criteria": criteria,
             "percentage_meaning": "Eight completed fixed implementation-delivery criteria; separate from the original whole research project.",
             "whole_original_research_project_complete": False, "whole_project_work_estimate_percent": 80,
             "whole_project_estimate_uncertainty_points": 10,
             "human_gold_or_final_scientific_review_complete": False, "publication_ready": False,
             "retained_checks": {"current_Linux_core_tests": 167, "extra_controls": 57, "owned_timeout_controls": 5,
                                 "core_algorithm_comparisons": 1056, "core_reference_comparisons": 264,
                                 "algorithm_certificates_rechecked": 683, "reference_certificates_rechecked": 172,
                                 "fresh_paper_input_hashes": 3468, "fresh_paper_read_checks": 19},
             "evidence_identities": [record(path) for path in (ACCEPTANCE, software_path, PAPER, CONTEXT,
                 paper["fresh_paper_audit"]["path"], "paper/working-draft-v15.md", "paper/claim-ledger-v15.json",
                 "paper/ap2-native-shopper-v4-development-addendum-v1.md", WHOLE, "scripts/finalize_v1_release_v1.py")],
             "remaining_original_research_requirements": ["Qualified source-to-model and two-domain crossing routes",
                 "Independent human task/gold, near-miss and scientific/contribution review", "Untouched holdout",
                 "Full 96-task, 288-path-cell and 96-additional-crossing study and independent reproduction"],
             "failures_and_unknowns_preserved": True,
             "AI_reviews_are_not_human_reviews": True, "new_application_or_provider_calls_by_finalizer": 0}
    need(record(WHOLE) == before_whole, "whole_project_register_changed_during_finalization")
    with TARGET.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
    prose = """# Completed V1 implementation and development-paper package

**V1: 100%, eight of eight fixed implementation criteria accepted.** This is the
executable prototype and development-paper package defined by the existing
delivery plan. The original whole research project remains approximately 80%
by its unchanged work estimate, with about ten points of uncertainty.

The fresh Linux release run passed 167 core tests, 57 additional controls and
five owned-process timeout controls. All 1,056 algorithm and 264 reference
outputs reconcile with retained deterministic evidence. Independent read
verification rechecks 683 algorithm and 172 reference certificates, the complete
benchmark, eight demo/replay steps, cleanup and all 68 candidate-bank records.

A clean isolated checkout restored 2,995 required members and ten archives,
verified all 3,468 frozen paper inputs and passed the unchanged 19-check V15
read audit. All accepted claims retain their source/evidence scope. The
optional native shopper V4 report also reproduced from that checkout: two
business attempts, zero business returns and zero receipts. Its failure stays
separate from scripted V2's two demo receipt cases and all earlier failures.

The full study, untouched holdout, human gold, route/model qualification and
final contribution/scientific review remain open. AI source and evidence reviews
do not replace human review. Shared lifting has no certified-coverage advantage
over goal-pruned direct in the finite development suite; adverse results and
unmeasured provider usage are explicitly retained. No publication readiness,
general superiority, real settlement or full-project completion is claimed.

Start with the [release entrypoint](v1-release-entrypoint-20261112.md),
[V15 manuscript](../../paper/working-draft-v15.md),
[current claim ledger](../../paper/claim-ledger-v15.json), and
[exact paper restoration guide](paper-v15-offline-restoration-guide-v2.md).
The [release JSON](v1-release-status-20261112.json) binds every accepted criterion
and its exact evidence. The original [project register](project-completion-status-v1.json)
is unchanged.
"""
    with NOTE.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(prose)
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--software-review", type=Path, required=True)
    args = parser.parse_args()
    value = finalize(args.software_review.resolve())
    print(json.dumps({"status": value["status"], "V1_percent": value["V1_progress_percent"],
                      "whole_project_percent": value["whole_project_work_estimate_percent"]}))
