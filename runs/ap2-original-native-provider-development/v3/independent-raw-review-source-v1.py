"""Read-only review of actual V3 singleton. No original imports or executions."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[3]
RETAINED = ROOT / "runs/ap2-original-native-provider-development/v3/retained-43014447502-1"
CAPTURE = RETAINED / "extracted"
OUT = ROOT / "runs/ap2-original-native-provider-development/v3/independent-raw-review-v1.json"
ARCHIVE_SHA = "b8f988d85bb47cb98ea8c2171125e6441323a338223b634aed4ab2bfc3af3f49"
RUN = 43014447502
HEAD = "b65a6767e21191314c27cdf50d3f5ff810d5a2ce"
CASE = "ap2-native-provider-v3-repeat-completed"
MODEL_PATH = "/v1beta/models/gemini-3.1-flash-lite-preview:generateContent"


def digest(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def read(path):
    return json.loads(path.read_bytes())


def rows(path):
    return [json.loads(line) for line in path.read_bytes().splitlines()] if path.is_file() else []


def main():
    if OUT.exists():
        raise ValueError("fresh_review_output_required")
    issues, evidence = [], {}
    def need(condition, reason):
        if not condition:
            issues.append(reason)
    def bound(path, expected):
        actual = digest(path.read_bytes())
        evidence[str(path)] = actual
        need(actual == {key: expected.get(key) for key in ("bytes", "sha256")}, "binding_mismatch:" + str(path))

    archive = RETAINED / "artifact.zip"
    need(digest(archive.read_bytes()) == {"bytes": 1282507, "sha256": ARCHIVE_SHA}, "archive_binding")
    members = {}
    with zipfile.ZipFile(archive) as zipped:
        for member in zipped.infolist():
            if member.is_dir():
                continue
            need(member.filename not in members, "duplicate_zip_member")
            members[member.filename] = digest(zipped.read(member))
            bound(CAPTURE / member.filename, members[member.filename])
    need(len(members) == 34, "archive_member_count")
    manifest = {row["path"]: {key: row[key] for key in ("bytes", "sha256")} for row in read(RETAINED / "extracted-manifest.json")["files"]}
    need(members == manifest, "extracted_manifest")
    retention = read(RETAINED / "retention.json")
    run = read(RETAINED / "github-run.json")
    api = read(RETAINED / "github-artifacts.json")["artifacts"]
    need(retention.get("run_id") == RUN and retention.get("head_sha") == HEAD and retention.get("archive_sha256") == ARCHIVE_SHA, "retention_identity")
    need(run.get("id") == RUN and run.get("head_sha") == HEAD, "hosted_identity")
    need(len(api) == 1 and api[0].get("digest") == "sha256:" + ARCHIVE_SHA and api[0].get("size_in_bytes") == 1282507, "API_archive_digest")
    plan_path = CAPTURE / "plan/plan.json"
    plan, opening, closing = read(plan_path), read(CAPTURE / "execution/opening.json"), read(CAPTURE / "execution/result.json")
    bound(plan_path, opening["plan"])
    expected_facts = {"case_id": CASE, "catalog_search": "unbranded walking shoes", "user_email": "bugsbunny@gmail.com", "cart_index": 0, "payment_method_index": 0, "wallet_consent": True, "confirm_cart": True, "otp_response": "123", "fault": "none", "repeat_after_completed": True}
    need(plan.get("facts") == [expected_facts], "singleton_facts")
    need(plan.get("schema_version") == "ap2-original-native-provider-screen/3" and plan.get("adaptive_development_followup") is True and plan.get("held_out_study") is False, "adaptive_schema")
    need(plan.get("preserved_source_run") == 42995902326 and plan.get("preserved_source_archive_sha256") == "5aa54a06193b25416e6d952fdee9be2af1760fd60fed596107906c5864bb2bf3", "V2_preservation_metadata")
    need(len(plan.get("owned_sources", {})) == 5 and len(plan.get("sources", {})) == 136 and len(plan.get("x402_sources", {})) == 24 and len(plan.get("versions", {})) == 182, "frozen_source_census")
    for name, expected in plan["owned_sources"].items():
        bound(ROOT / name, expected)
    source_root = ROOT / "runs/ap2-environment-preparation/source-stage-v1"
    for name, expected in plan["sources"].items():
        bound(source_root / "ap2" / name, expected)
    for name, expected in plan["x402_sources"].items():
        bound(source_root / "a2a-x402" / name, expected)
    need(closing.get("allocated_task_count") == 1 and closing.get("unexecuted_count") == 0 and len(closing.get("cases", [])) == 1, "singleton_closing_census")
    parent = closing["cases"][0]
    need(parent.get("case_id") == CASE and parent.get("status") == "executed_returned" and parent.get("caller_returncode") == 0, "parent_attempt_disposition")
    ledger = rows(CAPTURE / "execution/provider/ledger.jsonl")
    need([row.get("allocation") for row in ledger] == [0, 0, 1, 1, 2, 2] and [row.get("phase") for row in ledger] == ["started", "finished"] * 3, "upstream_allocation_census")
    response_rows, known_usage, request_bytes, failed_missing_usage = [], 0, 0, 0
    for index in range(3):
        started, finished = ledger[index * 2:index * 2 + 2]
        request_path = CAPTURE / f"execution/provider/{index:03d}.request.json"
        response_path = CAPTURE / f"execution/provider/{index:03d}.response.json"
        bound(request_path, started["request"])
        bound(response_path, finished["response"])
        request, response = read(request_path), read(response_path)
        need(started.get("path") == MODEL_PATH and started.get("provider_mode") == "live" and started.get("retry") is False, "upstream_path_mode_retry")
        need(finished.get("transport_error_type") is None and finished.get("upstream_call_consumed") is True, "upstream_received_body_disposition")
        status = finished["http_status"]
        need(status == (503 if index == 2 else 200), "raw_HTTP_status")
        total = response.get("usageMetadata", {}).get("totalTokenCount")
        if total is not None:
            need(type(total) is int and total > 0, "positive_reported_usage")
            known_usage += total
        elif status != 200:
            failed_missing_usage += 1
        request_bytes += request_path.stat().st_size
        need(finished.get("observed_cumulative_usage_tokens") == known_usage, "known_usage_running_sum")
        declarations = [function.get("name") for tool in request.get("tools", []) for function in tool.get("functionDeclarations", [])]
        response_rows.append({"allocation": index, "HTTP_status": status, "request_bytes": request_path.stat().st_size, "response_bytes": response_path.stat().st_size,
                              "raw_totalTokenCount": total, "raw_usage_metadata": response.get("usageMetadata"), "returned_modelVersion": response.get("modelVersion"),
                              "tool_declaration_names": declarations, "raw_error": response.get("error"),
                              "phase": "parent_access_smoke" if index == 0 else ("original_native_function_resolution" if declarations else "original_native_catalog_generation")})
    need(known_usage == 839 and request_bytes == 6327 and failed_missing_usage == 1, "known_usage_and_byte_totals")
    need(response_rows[2]["raw_error"].get("code") == 503 and response_rows[2]["raw_error"].get("status") == "UNAVAILABLE" and "high demand" in response_rows[2]["raw_error"].get("message", ""), "actual_upstream_503_body")
    provider = closing["provider"]
    need(provider.get("upstream_allocations") == 3 and provider.get("successful_provider_responses") == 2 and provider.get("observed_usage_tokens") == known_usage and provider.get("cumulative_request_bytes") == request_bytes and provider.get("failed") is True and provider.get("stopped") is True, "provider_closing_census")
    local = rows(CAPTURE / "execution/provider/local-refusals.jsonl")
    case_root = CAPTURE / "execution/cases" / CASE
    actor = read(case_root / "caller/result.json")
    events = rows(case_root / "caller/actor-public-events.jsonl")
    calls = actor.get("original_business_calls", [])
    need(actor.get("status") == "actual_failed_or_partial_attempt_retained" and len(calls) == 1 and calls[0].get("phase") == "catalog" and "error_type" in calls[0] and "public_return" not in calls[0], "failed_catalog_only")
    terminals = [{key: value for key, value in row.items() if key != "kind"} for row in events if row.get("kind") in {"original-call-return", "original-call-error"}]
    need(terminals == calls, "actor_vs_raw_catalog_terminal")
    need(actor.get("public_task_reads") == [] and actor.get("public_pending_task") is None and actor.get("public_final_task") is None, "no_payment_Task_reads")
    need(not any(row.get("kind") == "public-repeat-observation" or row.get("phase") == "repeat-original-otp" for row in events), "no_repeat_attempt")
    need(actor.get("grade") is None and actor.get("evaluator_or_private_journal_inputs") == [], "no_gold_or_private_inputs")
    need("503 UNAVAILABLE" in actor.get("error", {}).get("message", ""), "503_propagated_to_actor")
    cleanup = parent.get("process_cleanup", [])
    need(len(cleanup) == 4 and all(row.get("reaped") is True and row.get("cleanup_error_type") is None for row in cleanup), "four_child_reaps")
    report = {"schema_version": "ap2-original-native-repeat-independent-raw-review/3", "completed_at": datetime.now(timezone.utc).isoformat(),
              "status": "retained_V3_external_failure_evidence_consistent" if not issues else "raw_consistency_questions_retained", "issues": issues,
              "run_id": RUN, "head_sha": HEAD, "archive": {"sha256": ARCHIVE_SHA, "bytes": 1282507, "members": 34},
              "source": digest(Path(__file__).read_bytes()), "adaptive_development_followup": True, "source_V2_preserved": True,
              "parent_case_count": 1, "actor_result_count": 1, "original_call_terminal_count": 1, "original_call_return_count": 0,
              "public_payment_Task_reads": 0, "receipt_count": 0, "completed_prefix_count": 0, "repeat_attempt_count": 0,
              "upstream_allocations": 3, "successful_HTTP200_responses": 2, "received_HTTP503_responses": 1, "forwarded_request_bytes": request_bytes,
              "known_reported_usage_tokens": known_usage, "failed_responses_without_usage_metadata": failed_missing_usage,
              "failed_response_token_usage": "unknown; no zero-token claim", "overall_token_total_fully_measured": False,
              "successful_response_unknown_usage_counter": provider.get("responses_with_unknown_usage"),
              "provider_responses": response_rows, "local_refusal_count": len(local), "caller_status": actor.get("status"), "caller_error": actor.get("error"), "process_cleanup": cleanup,
              "hard_limits": plan["limits"], "evidence_bindings": evidence,
              "interpretation": ["The third request was consumed upstream and returned a retained HTTP503 UNAVAILABLE high-demand body; it is an external service response, unlike V2's locally generated byte-budget refusal.",
                                 "The 839 observed tokens come from two successful responses only. Missing HTTP503 usage is unknown, not zero, and the complete token/cost total is not measured.",
                                 "No added public payment Task read or receipt occurred. The failed catalog Task/message is embedded in the original tool error; the business prefix and repeat remain unrealized.",
                                 "All request/call hard allocation bounds remained unexhausted; the observed usage threshold remains post-response stopping, not a hard token/cost ceiling.",
                                 "This fresh adaptive singleton preserves V2's five-case partial/denominator and supplies no held-out, human-gold, idempotency, full-study or scientific gate credit."],
              "reviewer_original_app_API_SDK_model_actor_evaluator_solver_checker_imports_or_executions": 0, "reviewer_provider_requests": 0}
    with OUT.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "issues": issues, "known_reported_tokens": known_usage, "failed_usage_unknown": True, "output": str(OUT), "sha256": digest(OUT.read_bytes())["sha256"]}))


if __name__ == "__main__":
    main()
