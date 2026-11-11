"""Reconstruct the retained adaptive V3 public caller observations offline.

The unchanged V2 public semantic helpers read JSON only. No original app, SDK,
actor, model, solver or evaluator is imported or executed. Native provenance
and full provider accounting remain the separate raw review's responsibility.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import analyze_ap2_original_native_provider_v2 as public


EXPECTED_RUN = 43014447502
EXPECTED_HEAD = "b65a6767e21191314c27cdf50d3f5ff810d5a2ce"
EXPECTED_ARCHIVE = "b8f988d85bb47cb98ea8c2171125e6441323a338223b634aed4ab2bfc3af3f49"
CASE_ID = "ap2-native-provider-v3-repeat-completed"


def facts():
    return {"case_id": CASE_ID, "catalog_search": "unbranded walking shoes",
            "user_email": "bugsbunny@gmail.com", "cart_index": 0,
            "payment_method_index": 0, "wallet_consent": True,
            "confirm_cart": True, "otp_response": "123", "fault": "none",
            "repeat_after_completed": True}


def file_digest(path):
    h, count = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while block := stream.read(262144):
            count += len(block)
            h.update(block)
    return {"bytes": count, "sha256": h.hexdigest()}


def failure_observation(case, provider_rows):
    """Keep a propagated provider error separate from a public Task read."""
    error_text = (case.get("caller_error") or {}).get("message", "")
    matched = []
    for row in provider_rows:
        error = row.get("error")
        if (type(error) is dict and type(error.get("message")) is str
                and error["message"] and error["message"] in error_text
                and str(error.get("code")) in error_text
                and str(error.get("status")) in error_text):
            matched.append(row)
    no_payment = (case.get("actor_result_present") is True
                  and case.get("original_call_started_count") == case.get("original_call_terminal_count")
                  and case.get("original_call_phases") == ["catalog"]
                  and case.get("original_call_return_count") == 0
                  and case.get("original_call_errors")
                  and case.get("initial_task") is None and case.get("final_task") is None
                  and case.get("repeat_task") is None and case.get("repeat_event") is None
                  and case.get("otp_request") is None and case.get("explicit_human_reply") is None
                  and not case.get("public_tasks"))
    return {"original_catalog_terminal_error_observed": bool(no_payment),
            "provider_error_embedded_in_original_tool_error": bool(matched),
            "matched_provider_errors": matched,
            "original_failed_task_repr_embedded_in_error": bool(
                "state=<TaskState.failed: 'failed'>" in error_text),
            "no_payment_prerequisite_or_repeat_observed": bool(no_payment),
            "failure_disposition": (
                "received_provider_error_propagated_before_payment_prerequisite" if no_payment and matched
                else "original_catalog_error_before_payment_prerequisite" if no_payment else None),
            "public_error_text_is_not_a_tasks_get_observation": True}


def analyze(retained):
    analysis = public.Analysis(retained.resolve(strict=True))
    retention = analysis.read_json(analysis.retained / "retention.json", required=True)
    analysis.need(retention.get("run_id") == EXPECTED_RUN
                  and retention.get("head_sha") == EXPECTED_HEAD
                  and retention.get("archive_sha256") == EXPECTED_ARCHIVE
                  and retention.get("api_digest") == "sha256:" + EXPECTED_ARCHIVE
                  and retention.get("digest_matches_api") is True,
                  "root_retention_run_head_archive_binding_mismatch")
    archive = file_digest(analysis.retained / "artifact.zip")
    analysis.need(archive == {"bytes": retention.get("archive_bytes"), "sha256": EXPECTED_ARCHIVE},
                  "retained_archive_bytes_or_digest_mismatch")
    manifest = analysis.read_json(analysis.retained / "extracted-manifest.json", required=True)
    analysis.members = {row["path"]: {key: row[key] for key in ("bytes", "sha256")}
                        for row in manifest.get("files", [])}
    analysis.need(len(analysis.members) == len(manifest.get("files", [])) == retention.get("extracted_files"),
                  "manifest_member_census_mismatch")
    for relative in analysis.members:
        path = (analysis.capture / relative).resolve()
        analysis.need(path.is_relative_to(analysis.capture.resolve()), "manifest_member_escaped_capture")
        if path.is_relative_to(analysis.capture.resolve()):
            analysis.raw(path, required=True)
    plan = analysis.read_json(analysis.capture / "plan/plan.json", required=True)
    result = analysis.read_json(analysis.capture / "execution/result.json", required=True)
    analysis.need(plan.get("schema_version") == "ap2-original-native-provider-screen/3"
                  and public.equal(plan.get("facts"), [facts()])
                  and plan.get("adaptive_development_followup") is True
                  and plan.get("held_out_study") is False, "plan_not_fixed_adaptive_v3_singleton")
    analysis.need(plan.get("preserved_source_run") == public.EXPECTED_RUN
                  and plan.get("preserved_source_archive_sha256") == "5aa54a06193b25416e6d952fdee9be2af1760fd60fed596107906c5864bb2bf3",
                  "v2_preservation_metadata_changed")
    rows = result.get("cases", [])
    analysis.need(result.get("schema_version") == "ap2-original-native-provider-screen-result/3"
                  and result.get("allocated_task_count") == 1
                  and [row.get("case_id") for row in rows] == [CASE_ID], "closing_singleton_census_mismatch")
    folder = analysis.capture / "execution/cases" / CASE_ID
    for relative in ("caller/result.json", "caller/actor-public-events.jsonl", CASE_ID + ".public-human-facts.json"):
        analysis.need((folder / relative).is_file(), "required_case_capture_missing:" + relative)
    case = analysis.case(facts(), rows[0] if len(rows) == 1 else {})
    analysis.need(case["actor_result_present"], "actor_result_missing_no_absence_inference")
    analysis.need(case["original_call_started_count"] == case["original_call_terminal_count"],
                  "unterminated_original_calls_no_complete_absence_inference")
    ledger = analysis.lines(analysis.capture / "execution/provider/ledger.jsonl")
    starts = [row for row in ledger if row.get("phase") == "started"]
    finishes = [row for row in ledger if row.get("phase") == "finished"]
    analysis.need([row.get("allocation") for row in starts] == list(range(len(starts)))
                  and [row.get("allocation") for row in finishes] == list(range(len(starts))),
                  "provider_start_finish_census_mismatch")
    provider_rows = []
    for start, finish in zip(starts, finishes):
        number = start["allocation"]
        response_path = analysis.capture / f"execution/provider/{number:03d}.response.json"
        response_raw = analysis.raw(response_path, required=True)
        if response_raw is None:
            continue
        analysis.need(public.digest(response_raw) == finish.get("response"), "provider_response_ledger_digest_mismatch")
        response = public.strict(response_raw)
        provider_rows.append({"allocation": number, "http_status": finish.get("http_status"),
                              "error": response.get("error"), "reported_total_tokens": (response.get("usageMetadata") or {}).get("totalTokenCount"),
                              "within_case_window": bool(rows and rows[0].get("started_at") <= start.get("time", "")
                                                         <= finish.get("time", "") <= rows[0].get("finished_at"))})
    observation = failure_observation(case, provider_rows)
    if observation["matched_provider_errors"]:
        analysis.need(all(row["within_case_window"] for row in observation["matched_provider_errors"]),
                      "matched_provider_error_outside_case_window")
    if observation["failure_disposition"]:
        case["disposition"] = observation["failure_disposition"]
    known_usage = sum(row["reported_total_tokens"] for row in provider_rows if type(row["reported_total_tokens"]) is int)
    unknown_usage = sum(row["reported_total_tokens"] is None for row in provider_rows)
    local_refusals = analysis.lines(analysis.capture / "execution/provider/local-refusals.jsonl")
    return {"schema_version": "ap2-original-native-repeat-public-semantic-observations/3",
            "completed_at": datetime.now(timezone.utc).isoformat(), "expected_run_id": EXPECTED_RUN,
            "expected_head_sha": EXPECTED_HEAD, "root_retention": retention, "archive_verified": archive,
            "status": "retained_public_observations_consistent" if not analysis.issues else "public_capture_consistency_questions_retained",
            "integrity_questions": analysis.issues, "cases": [case], "allocated_task_count": 1,
            "adaptive_development_followup": True, "held_out_study": False,
            "public_receipt_case_count": int(case["prior_completed_receipt_observed"]),
            "repeat_original_call_count": case["original_call_phases"].count("repeat-original-otp"),
            "public_repeat_observation_count": int(case["repeat_event"] is not None),
            "failure_observation": observation, "provider_response_observations": provider_rows,
            "known_reported_usage_tokens": known_usage, "responses_without_usage_metadata": unknown_usage,
            "whole_token_total_measured": unknown_usage == 0, "unknown_usage_is_never_assigned_zero": True,
            "local_refusal_count": len(local_refusals), "closing_provider_summary": result.get("provider"),
            "analyzer_source": {"path": str(Path(__file__).resolve()), **file_digest(Path(__file__))},
            "unchanged_public_helper_source": {"path": str(Path(public.__file__).resolve()), **file_digest(Path(public.__file__))},
            "evidence_bindings": analysis.evidence,
            "original_app_sdk_model_actor_solver_evaluator_checker_imports_or_executions": 0,
            "provider_requests_by_analyzer": 0, "human_gold_qualified": False, "whole_task_grade": None,
            "limitations": ["Root's separate raw review owns original native/runtime/provider provenance and full accounting.",
                            "A failed Task representation in an original tool exception is retained public error text, not a new tasks/get observation.",
                            "No receipt or repeated public response cannot establish idempotency, hidden-effect uniqueness or durability.",
                            "The adaptive singleton never replaces V2's fifth partial outcome or its five-case denominator.",
                            "No unchanged ADK shopper, independent bridge, human gold, held-out, full-study or scientific checkpoint qualification is granted."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retained-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = analyze(args.retained_root)
    args.output.mkdir(parents=True, exist_ok=False)
    with (args.output / "analysis.json").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"status": report["status"], "questions": len(report["integrity_questions"]),
                      "receipt_cases": report["public_receipt_case_count"],
                      "repeat_calls": report["repeat_original_call_count"],
                      "failure_disposition": report["cases"][0]["disposition"]}))


if __name__ == "__main__":
    main()
