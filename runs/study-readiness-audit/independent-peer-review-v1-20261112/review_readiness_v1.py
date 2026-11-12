"""Independent retained-source readiness/fragment review; no original execution."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent / "review.json"
BINDINGS = {}


def need(value, reason):
    if not value:
        raise ValueError(reason)


def identity(name):
    path = (ROOT / name).resolve()
    need(path.is_relative_to(ROOT) and path.is_file(), "regular_workspace_evidence_required")
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while raw := stream.read(262144):
            digest.update(raw)
            size += len(raw)
    row = {"path": name, "bytes": size, "sha256": digest.hexdigest()}
    BINDINGS[name] = row
    return row


def load(name):
    identity(name)
    return json.loads((ROOT / name).read_bytes())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def main():
    need(not OUTPUT.exists(), "exclusive_peer_review_output_required")
    checkpoint_name = "runs/study-readiness-audit/v2-20261112-1/inventory.json"
    base = "runs/study-readiness-audit/v2-20261112-2/"
    checkpoint, validation, tests, fragment = [load(name) for name in (
        checkpoint_name, base + "validation-v2.json", base + "tests-40.json", base + "agentops-d01-read-fragment-v3.json")]
    need(checkpoint["status"] == "incomplete_post_V1_readiness_checkpoint" and len(checkpoint["records"]) == 68,
         "retained_incomplete_checkpoint_changed")
    for row in checkpoint["exact_input_bindings"]:
        need(identity(row["path"]) == row, "checkpoint_input_identity_differs")
    need(len(checkpoint["exact_input_bindings"]) == 103, "complete_input_inventory_required")
    need(validation["status"] == "passed_snapshot_binding_and_fail_closed_checks"
         and validation["checks_passed"] == 6 and validation["bound_files"] == 103
         and validation["cited_source_files"] == 51
         and validation["inventory_sha256"] == identity(checkpoint_name)["sha256"],
         "actual_validation_receipt_or_checkpoint_binding_differs")
    need(validation["qualified_confirmatory_tasks"] == validation["qualified_crossing_cells"] == 0
         and validation["human_review"] is False and validation["semantic_gold_validated"] is False
         and validation["full_task_oracle_complete"] is False, "structural_validation_promoted_to_scientific_qualification")
    need(tests["status"] == "passed" and tests["tests_run"] == 40
         and tests["source_hashes_before"] == tests["source_hashes_after"]
         and [row["tests_run"] for row in tests["executions"]] == [28, 12]
         and all(row["exit_code"] == 0 and f"Ran {row['tests_run']} tests" in row["stderr"]
            and "\nOK\n" in row["stderr"] for row in tests["executions"]), "actual_40_control_receipt_differs")
    for name, sha in tests["source_hashes_after"].items():
        need(identity(name)["sha256"] == sha, "tested_current_source_identity_changed")
    for row in checkpoint["records"]:
        need(row["human_review"] == "not_reviewed" and row["gold_status"] == "proposed_not_validated"
             and row["holdout_independence"] == "exposed_authoring_and_development_evidence_not_independent_holdout"
             and all(row[key] is False for key in ("qualified_candidate", "confirmatory_execution_eligible", "source_to_model_qualified")),
             "candidate_human_holdout_or_source_model_promotion")
    need(all(value == 0 and type(value) is int for value in checkpoint["eligible_confirmatory_counts"].values()),
         "original_study_eligibility_promoted")
    for row in fragment["exact_input_bindings"]:
        need(identity(row["path"]) == row, "fragment_input_identity_changed")
    need(fragment["status"] == "passed_source_bound_development_fragment"
         and fragment["original_split"] == "development" and fragment["finite_world_count"] == 28
         and fragment["fragment_oracle_complete_for_declared_28_inputs"] is True
         and fragment["full_task_oracle_complete"] is False and fragment["semantic_gold_validated_by_humans"] is False
         and fragment["qualified_confirmatory_tasks"] == 0,
         "finite_development_fragment_scope_promoted")
    need(fragment["oracle_source_sha256"] == identity("scripts/qualify_agentops_read_fragment_v1.py")["sha256"],
         "fragment_oracle_source_changed")
    case = "agentops-d01-health-active"
    archive_name = "runs/ci-agentops-governed-app-reference-v4/retained-42887519756-1/artifact.zip"
    prefix = "runs/ci-agentops-governed-app-reference-v4/retained-42887519756-1/extracted/" + case + "/"
    members = ("state-before.json", "state-after.json", "tool-contexts.jsonl", "model-journal.jsonl", "actor-receipt.json", "turn-1/task-get.response.raw.json")
    with zipfile.ZipFile(ROOT / archive_name) as zipped:
        names = zipped.namelist()
        for member in members:
            name = case + "/" + member
            need(names.count(name) == 1 and zipped.read(name) == (ROOT / (prefix + member)).read_bytes(),
                 "consumed_fragment_member_not_exact_digest_bound_archive_bytes")
    before, after, task, receipt = [load(prefix + name) for name in ("state-before.json", "state-after.json", "turn-1/task-get.response.raw.json", "actor-receipt.json")]
    task = task["result"]
    calls = [json.loads(line) for line in (ROOT / (prefix + "tool-contexts.jsonl")).read_bytes().splitlines()]
    journal = [json.loads(line) for line in (ROOT / (prefix + "model-journal.jsonl")).read_bytes().splitlines()]
    need(canonical(before["incidents.db"]) == canonical(after["incidents.db"]), "business_state_changed")
    state = before["incidents.db"]
    service = next(row for row in state["services"] if row["name"] == "inventory")
    active = sorted((row for row in state["incidents"] if row["service"] == "inventory" and row["status"] in {"open", "investigating"}),
                    key=lambda row: row["opened_at"], reverse=True)
    projection = {"service": {key: service[key] for key in ("name", "status", "owner")},
        "open_incidents": [{key: row[key] for key in ("id", "severity", "status")} for row in active]}
    need(projection == fragment["observed_projection"]["projection"], "independently_selected_d01_projection_differs")
    need(len(calls) == 1 and calls[0]["tool"] == "get_service_status" and calls[0]["args"] == {"name": " INVENTORY "},
         "grounded_actual_read_differs")
    need(len(journal) == 2, "exact_two_step_journal_required")
    call = next(part["function_call"] for part in journal[0]["response"]["content"]["parts"] if part.get("function_call"))
    terminals = [part["function_response"] for content in journal[1]["request"]["contents"] for part in content.get("parts", []) if part.get("function_response")]
    need(len(terminals) == 1 and terminals[0]["id"] == call["id"] and terminals[0]["name"] == call["name"],
         "terminal_not_bound_to_emitted_call")
    terminal = terminals[0]["response"]
    terminal_projection = {"service": {key: terminal["service"][key] for key in ("name", "status", "owner")},
        "open_incidents": [{key: row[key] for key in ("id", "severity", "status")} for row in terminal["open_incidents"]]}
    need(canonical(terminal_projection) == canonical(projection), "typed_terminal_projection_differs")
    final_parts = journal[1]["response"]["content"]["parts"]
    need(any(part.get("text") for part in final_parts) and not any(part.get("function_call") for part in final_parts)
         and task["status"]["state"] == "completed" and receipt["tasks"][0]["task_id"] == task["id"]
         and receipt["tasks"][0]["context_id"] == task["contextId"] == calls[0]["session_id"],
         "terminal_before_final_answer_or_original_task_context_join_differs")
    branches = Counter(row["oracle"]["branch"] for row in fragment["finite_input_worlds"])
    need(branches == {"observed_service": 24, "invalid_slug": 3, "missing_service": 1}, "finite_28_input_branch_census_differs")
    identity("docs/research/study-readiness-audit-v2.md")
    identity(Path(__file__).relative_to(ROOT).as_posix())
    result = {"schema_version": "study-readiness-V2-independent-source-and-evidence-review/1",
        "status": "accepted_with_unqualified_original_study_and_finite_fragment_limits",
        "reviewed_at_utc": datetime.now(timezone.utc).isoformat(), "material_consistency_questions": [],
        "bound_checkpoint_inputs_verified": 103, "retained_constructed_controls_verified": 40,
        "candidate_human_holdout_source_model_promotion_rejected": True,
        "fragment_original_split": "development", "finite_fragment_input_census": dict(branches),
        "independent_d01_retained_state_projection": projection,
        "exact_archive_members_consumed": len(members), "grounded_read_terminal_final_answer_task_context_binding_verified": True,
        "original_study_qualified_confirmatory_tasks": 0, "original_study_qualified_crossing_cells": 0,
        "full_task_oracle_complete": False, "human_semantic_gold": False, "percentage_credit_claimed": False,
        "new_original_application_SDK_provider_solver_checker_or_SQL_executions_by_reviewer": 0,
        "source_read_findings": ["Validator imports only stdlib and hashes/joins the specifically unqualified snapshot; it never enables original routes or study execution.",
            "All68 candidate human/holdout/source-model limits remain explicit. Prospective four-stage grammars are structural controls with execution and original surface qualification disabled.",
            "The separately authored fragment executes the inspected pinned schema/seed SQL only in an owned in-memory database; no SDK or application module is imported.",
            "Full-business-state closure and finite static read projection are useful bounded development checks, not complete task semantics, free-text relevance or allowed-trajectory qualification.",
            "Archive/source hashes establish retained byte consistency; capture authenticity, native-launcher fidelity, task gold, holdout and human scientific review remain outside this acceptance."],
        "evidence_identities": list(BINDINGS.values())}
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "bound_inputs": 103, "constructed_controls": 40, "finite_inputs": 28,
        "new_original_or_provider_calls": 0}))


if __name__ == "__main__":
    main()
