"""Independently audit the V15 release paper and current claim ledger; stdlib only.

No builder, application, SDK, provider, solver, evaluator or certificate checker
is imported or executed. Earlier numerical checks are inherited from the exact
saved V14 audit and byte-identical technical/results text, not reexecuted.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from urllib.parse import unquote, urlparse
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NATIVE = "paper/original-native-provider-v2-appendix.provenance.json"
AUTONOMOUS = "paper/original-autonomous-workflow-shopper-appendix-v1.provenance.json"
WORKFLOW_BASE = "runs/agentops-workflow-reference-development/v2/retained-43055395848-1"
WORKFLOW_REVIEW = "runs/agentops-workflow-reference-development/v2/root-raw-review-1/review.json"
SHOPPER = "runs/ap2-native-shopper-provider-development/v3/offline-analysis-43055390208-1/source-diagnosis.json"
EXPECTED_NATIVE = [
    ("v1", 42982595287, 5, "0b73d252058fe6d967a54e4cbe1646e1f08b0ac0d3711d82791b90dd445e6d0a"),
    ("v2", 42995902326, 5, "5aa54a06193b25416e6d952fdee9be2af1760fd60fed596107906c5864bb2bf3"),
    ("v3", 43014447502, 1, "b8f988d85bb47cb98ea8c2171125e6441323a338223b634aed4ab2bfc3af3f49"),
]


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def strict(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            need(key not in value, "duplicate_JSON_key")
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite_JSON")))


def read(path):
    return strict((ROOT / path).read_bytes())


def digest(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def record(path):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    need(not path.is_symlink(), "symbolic_input_refused")
    path = path.resolve()
    need(path.is_relative_to(ROOT) and path.is_file(), "regular_workspace_input_required")
    h, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
            size += len(block)
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": size, "sha256": h.hexdigest()}


def byte_identity(row):
    return {key: row[key] for key in ("bytes", "sha256")}


def raw_jsonl(raw):
    return [strict(line) for line in raw.splitlines()]


def verify_archive(base, archive_sha):
    run, retention = read(base + "/github-run.json"), read(base + "/retention.json")
    actual = record(base + "/artifact.zip")
    need(actual["sha256"] == retention["archive_sha256"] == archive_sha
         and actual["bytes"] == retention["archive_bytes"]
         and retention["api_digest"] == "sha256:" + archive_sha
         and run["id"] == retention["run_id"] and run["head_sha"] == retention["head_sha"]
         and run["status"] == "completed", "retained_API_archive_identity_changed")
    artifacts = [row for row in read(base + "/github-artifacts.json")["artifacts"]
                 if row["id"] == retention["artifact_id"]]
    need(len(artifacts) == 1 and artifacts[0]["digest"] == retention["api_digest"]
         and artifacts[0]["size_in_bytes"] == actual["bytes"], "API_archive_digest_changed")
    inventory = read(base + "/extracted-manifest.json")["files"]
    members = {row["path"]: byte_identity(row) for row in inventory}
    need(len(members) == len(inventory), "duplicate_manifest_member")
    zipped = zipfile.ZipFile(ROOT / base / "artifact.zip")
    files = [info for info in zipped.infolist() if not info.is_dir()]
    need(len(files) == len(members) == retention["extracted_files"]
         and len({info.filename for info in files}) == len(files), "archive_member_census_changed")
    for info in files:
        path = PurePosixPath(info.filename)
        need(not path.is_absolute() and ".." not in path.parts and "\\" not in info.filename
             and info.filename in members, "unsafe_or_unlisted_archive_member")
        need(digest(zipped.read(info)) == members[info.filename], "archive_member_bytes_changed")
    return zipped, run, actual, len(files)


def native_summary(version, run_id, cases, archive_sha):
    base = f"runs/ap2-original-native-provider-development/{version}/retained-{run_id}-1"
    archive, run, archive_identity, member_count = verify_archive(base, archive_sha)
    with archive:
        closing = strict(archive.read("execution/result.json"))
        need(closing["allocated_task_count"] == cases and len(closing["cases"]) == cases,
             "scripted_native_case_denominator_changed")
        rows = raw_jsonl(archive.read("execution/provider/ledger.jsonl"))
        opened = {row["allocation"]: row for row in rows if row["phase"] == "started"}
        closed = {row["allocation"]: row for row in rows if row["phase"] == "finished"}
        need(len(opened) == len([row for row in rows if row["phase"] == "started"])
             and len(closed) == len([row for row in rows if row["phase"] == "finished"])
             and set(opened) == set(closed) == set(range(len(opened))), "provider_allocation_join_changed")
        statuses, tokens, unknown, request_bytes = Counter(), 0, 0, 0
        for index in sorted(opened):
            request = archive.read(f"execution/provider/{index:03d}.request.json")
            response = archive.read(f"execution/provider/{index:03d}.response.json")
            need(digest(request) == opened[index]["request"]
                 and digest(response) == closed[index]["response"], "provider_payload_binding_changed")
            request_bytes += len(request)
            statuses[str(closed[index]["http_status"])] += 1
            usage = strict(response).get("usageMetadata", {}).get("totalTokenCount")
            if type(usage) is int and usage >= 0:
                tokens += usage
            else:
                unknown += 1
        local = "execution/provider/local-refusals.jsonl"
        refusals = len(archive.read(local).splitlines()) if local in archive.namelist() else 0
    return {"version": version, "run_id": run_id, "head_sha": run["head_sha"],
            "parent_attempts": cases, "archive": byte_identity(archive_identity),
            "archive_members": member_count, "upstream_allocations": len(opened),
            "HTTP_status_counts": dict(statuses), "known_reported_tokens": tokens,
            "responses_without_usage": unknown, "all_response_token_total_measured": unknown == 0,
            "request_bytes": request_bytes, "owned_local_refusals": refusals}


def workflow_summary():
    review = read(WORKFLOW_REVIEW)
    archive, _, _, members = verify_archive(WORKFLOW_BASE, review["archive_identity"]["sha256"])
    frozen_raw = archive.read("analysis.json")
    frozen = strict(frozen_raw)
    need(digest(frozen_raw) == review["analysis_identity"]
         and (ROOT / WORKFLOW_BASE / "extracted/analysis.json").read_bytes() == frozen_raw,
         "frozen_workflow_analysis_not_actual_archive_bytes")
    summaries = []
    with archive:
        for expected, recorded in zip(frozen["cases"], review["cases"], strict=True):
            case = expected["case_id"]
            journal = raw_jsonl(archive.read(case + "/model-journal.jsonl"))
            events = raw_jsonl(archive.read(case + "/adk-events.jsonl"))
            stages = raw_jsonl(archive.read(case + "/stage-observations.jsonl"))
            tool_context = raw_jsonl(archive.read(case + "/tool-contexts.jsonl"))
            calls, responses = {}, {}
            for sequence, row in enumerate(events):
                for part in row.get("event", {}).get("content", {}).get("parts", []):
                    for field, table in (("function_call", calls), ("function_response", responses)):
                        item = part.get(field)
                        if item:
                            key = (row["event"]["author"], item["name"], item["id"])
                            need(key not in table, "duplicate_workflow_call_or_terminal")
                            table[key] = sequence
            need(calls.keys() == responses.keys() and all(calls[key] < responses[key] for key in calls),
                 "raw_original_tool_terminal_delivery_changed")
            expected_stages = ["plan", "investigate", "evidence_review", "recommend"]
            need([row["stage"] for row in stages if row["kind"] == "stage_entry"] == expected_stages
                 and [row["stage"] for row in stages if row["kind"] == "stage_exit"] == expected_stages,
                 "all_four_original_stages_not_retained")
            review_inputs = [row["observed_input"] for row in journal if row["stage"] == "evidence_review"]
            need(len(review_inputs) == 1, "one_governed_evidence_review_input_required")
            try:
                strict(review_inputs[0])
            except json.JSONDecodeError as error:
                need(error.msg == recorded["malformed_governed_review_input"]["message"]
                     and error.pos == recorded["malformed_governed_review_input"]["position"]
                     and "\\<US_DRIVER_LICENSE>" in review_inputs[0], "actual_PII_invalid_escape_changed")
                error_offset = error.pos
            else:
                raise ValueError("frozen_governed_input_no_longer_malformed")
            final_journal = [row for row in journal if row["stage"] == "recommend"][-1]
            texts = [part["text"] for part in final_journal["response"]["content"]["parts"] if "text" in part]
            need(len(texts) == 1, "one_final_fixture_recommendation_required")
            final = strict(texts[0])
            need(final == expected["reported_final_output"] == recorded["final_output"]
                 and final["target"] is None and final["verdict"] == "insufficient",
                 "insufficient_null_target_result_changed")
            observed = {"case_id": case, "fixture_callbacks": len(journal), "raw_events": len(events),
                        "tool_terminals": len(responses), "optional_after_tool_observers":
                        sum(row["kind"] == "tool_after" for row in tool_context),
                        "json_error_offset": error_offset, "frozen_questions": len(expected["questions"]),
                        "final_target": None, "final_verdict": final["verdict"]}
            need(observed["fixture_callbacks"] == expected["model_calls"] == recorded["fixture_callbacks"]
                 and observed["raw_events"] == expected["raw_official_events"] == recorded["raw_events"]
                 and observed["tool_terminals"] == expected["raw_official_tool_terminal_count"] == recorded["raw_read_tool_terminal_pairs"]
                 and observed["optional_after_tool_observers"] == 0, "workflow_raw_counts_not_analysis_or_review")
            summaries.append(observed)
    need(frozen["case_denominator"] == 2 and len(summaries) == 2
         and sum(row["frozen_questions"] for row in summaries) == 6,
         "workflow_denominator_or_frozen_questions_changed")
    return summaries, members


def audit(draft_path, provenance_path, ledger_path):
    text = draft_path.read_text(encoding="utf-8")
    provenance, ledger = strict(provenance_path.read_bytes()), strict(ledger_path.read_bytes())
    checks = []

    def checked(condition, name, evidence):
        need(condition, name)
        checks.append({"id": name, "passed": True, "evidence": evidence})

    draft_identity = record(draft_path)
    checked(provenance["paper_identity"] == ledger["draft"] == draft_identity
            and provenance["claim_ledger_identity"] == record(ledger_path),
            "current_V15_draft_provenance_ledger_bound", draft_identity)
    inputs = provenance["inputs"]
    checked(len({row["path"] for row in inputs}) == len(inputs)
            and all(record(row["path"]) == row for row in inputs),
            "all_3468_current_and_inherited_build_inputs_unchanged", len(inputs))
    input_map = {row["path"]: row for row in inputs}
    checked(all(record(row["path"]) == row and input_map.get(row["path"]) == row for row in ledger["evidence"])
            and record(ledger["builder"]["path"]) == ledger["builder"]
            and record(ledger["artifact_guide"]["path"]) == ledger["artifact_guide"],
            "claim_source_artifact_and_builder_identities_bound", len(ledger["evidence"]))
    prior = read("paper/working-draft-v14.audit.json")
    checked(prior["checks_passed"] == 20 and all(row["passed"] for row in prior["checks"])
            and prior["draft_identity"] == record("paper/working-draft-v14.md")
            and prior["provenance_identity"] == record("paper/working-draft-v14.provenance.json")
            and record("paper/working-draft-v14.md")["sha256"] == "32d1064887e0b464ee73739430a0e5cb88fb7c4f0105ceb7b77f0e1bed38bc63",
            "exact_saved_20_check_V14_numerical_audit_inherited", record("paper/working-draft-v14.audit.json"))
    v14 = (ROOT / "paper/working-draft-v14.md").read_text(encoding="utf-8")
    anchor = "## 2. Related work and comparator requirements"
    checked(text[text.index(anchor):text.index("### 8.13.")] == v14[v14.index(anchor):v14.index("## 9. Discussion")]
            and text.splitlines()[0] == v14.splitlines()[0],
            "V14_technical_methods_all_tables_and_result_sections_identical", "Sections 2 through 8.12 preserved")
    native = [native_summary(*spec) for spec in EXPECTED_NATIVE]
    checked(native == read(NATIVE)["runs"] == provenance["native_scripted_profiles"],
            "three_native_run_ledgers_reconstructed_from_raw_archives", native)
    for row in native:
        statuses = row["HTTP_status_counts"]
        line = f"| {row['version'].upper()} / {row['run_id']} | {row['parent_attempts']} | {row['upstream_allocations']} | {statuses.get('200', 0)} / {statuses.get('503', 0)} | {row['request_bytes']:,} | {row['known_reported_tokens']:,} | {row['responses_without_usage']} | {row['owned_local_refusals']} |"
        checked(text.count(line) == 1, "V15N_" + row["version"] + "_all_counts_and_usage_statuses", line)
    semantic = read("runs/ap2-original-native-provider-development/v2/independent-semantic-analysis-v1/analysis.json")
    receipts = [row for row in semantic["cases"] if row["disposition"] == "completed_public_receipt_observed"]
    checked(len(semantic["cases"]) == 5 and len(receipts) == semantic["public_receipt_case_count"] == 2
            and all(row["final_task"]["state"] == "completed" and len(row["final_task"]["receipts"]) == 1
                    and row["final_task"]["receipts"][0]["status"] == "Success" for row in receipts)
            and not semantic["integrity_questions"],
            "V2_two_completed_Task_receipt_cases_kept_at_separate_denominator", 5)
    raw3 = read("runs/ap2-original-native-provider-development/v3/independent-raw-review-v1.json")
    checked(raw3["receipt_count"] == raw3["repeat_attempt_count"] == 0
            and raw3["received_HTTP503_responses"] == 1 and not raw3["issues"]
            and native[-1]["known_reported_tokens"] == 839 and native[-1]["responses_without_usage"] == 1,
            "V3_unreached_repeat_and_failed_response_usage_remain_unknown", "839 known tokens; one unknown response")
    workflow, members = workflow_summary()
    checked([(row["fixture_callbacks"], row["raw_events"], row["tool_terminals"], row["json_error_offset"])
             for row in workflow] == [(9, 14, 5, 2140), (8, 12, 4, 2737)],
            "Workflow_actual_raw_delivery_and_malformed_handoffs_reconstructed", {"cases": workflow, "archive_members": members})
    checked(all(value in text for value in ("| Fixture callbacks | 9 / 8 |", "| Raw official events | 14 / 12 |",
                                          "| Delivered raw tool terminals | 5 / 4 |", "| Frozen analysis questions | 3 / 3 |",
                                          "2140 and 2737", "both final recommendations")),
            "V15W_counts_null_targets_and_frozen_questions_preserved", 2)
    shopper = read(SHOPPER)
    checked(shopper["case_denominator"] == 1 and shopper["provider_allocations"] == 1
            and shopper["known_reported_tokens"] == 45 and shopper["allocations_with_unmeasured_usage"] == 0
            and shopper["original_shopper_SDK_or_ADK_execution_reached"] is False
            and shopper["all_non_case_public_facts_match"] is True
            and set(shopper["public_fact_differences"]) == {"case_id"}
            and shopper["shopper_returncode"] == 1,
            "V3_shopper_startup_failure_not_live_business_execution", shopper["public_fact_differences"])
    expected_shop = ["| V1 / 43038234376 | 2 | 45 | 1 |", "| V2 / 43045731741 | 0 | 0 | 0 |",
                     "| V3 / 43055390208 | 1 | 45 | 0 |"]
    checked(all(text.count(prefix) == 1 for prefix in expected_shop)
            and "zero shopper model requests" in text
            and "Its shopper generation times out" in text and "has unknown usage" in text,
            "V15S_separate_one_case_failures_and_usage_table", expected_shop)
    claim_ids, evidence_paths = set(), {row["path"] for row in ledger["evidence"]}
    for claim in ledger["claims"]:
        need(claim["id"] not in claim_ids, "duplicate_claim_id")
        claim_ids.add(claim["id"])
        location = claim["manuscript_location"]
        lines = text.splitlines()
        need(lines[location["line_start"] - 1] == location["heading"]
             and location["line_start"] <= location["line_end"] <= len(lines)
             and all(path in evidence_paths for path in claim["source_artifact_paths"])
             and claim["statement"] and claim["scope_and_limitations"] and claim["source_artifact_paths"]
             and claim["validation"]["independent_human_scientific_review"] is False,
             "current_claim_location_scope_or_source_unbound:" + claim["id"])
    required_ids = {"COVERAGE", "STRESS", "CACHE_ABLATION", "PROOF_CODEC", "OWNED_TCP", "NATIVE_FAILURE_HISTORY",
                    "NATIVE_V13", "COMMON_COST", "NATIVE_PROVIDER", "WORKFLOW_V2", "SHOPPER_V3", "LIMITATIONS"}
    checked(required_ids.issubset(claim_ids) and len(claim_ids) == 29,
            "29_current_substantive_claims_map_inherited_and_new_results", sorted(claim_ids))
    opens = {row["id"]: row for row in ledger["open_claims"]}
    checked(set(opens) == {"NOVELTY", "HUMAN_GOLD", "HOLDOUT", "FULL_REGISTERED_STUDY", "LIVE_TASK_UTILITY", "PUBLICATION_READY"}
            and opens["FULL_REGISTERED_STUDY"]["tasks"] == 96
            and opens["FULL_REGISTERED_STUDY"]["path_cells"] == 288
            and opens["FULL_REGISTERED_STUDY"]["additional_crossings"] == 96
            and provenance["full_original_study_complete"] is False
            and ledger["full_original_study_complete"] is False
            and provenance["publication_ready"] is ledger["publication_ready"] is False
            and ledger["human_scientific_review_claimed"] is False,
            "original_scope_and_six_open_scientific_claims_preserved", opens)
    prose = " ".join(text.split())
    checked("genuine provider execution" not in prose
            and "AgentOps and AP2 development integrations made no live model calls" not in prose
            and "held-out live-model utility remain" in prose
            and "higher observed full-process" in prose
            and "These adverse" in prose and "not a hard" in prose,
            "stale_blanket_claims_corrected_and_adverse_limits_explicit", "Bounded provider observations; original scientific scope open")
    missing = []
    for file in (draft_path, ROOT / ledger["artifact_guide"]["path"]):
        for target in re.findall(r"\]\(([^)]+)\)", file.read_text(encoding="utf-8")):
            target = target.strip("<>")
            parsed = urlparse(target)
            if parsed.scheme or target.startswith("#"):
                continue
            path = (file.parent / unquote(parsed.path)).resolve()
            if not path.is_relative_to(ROOT) or not path.exists():
                # The canonical saved audit is produced after this check.
                if path != ROOT / "paper/working-draft-v15.audit.json":
                    missing.append({"file": file.relative_to(ROOT).as_posix(), "target": target})
    checked(not missing, "current_manuscript_and_guide_local_links_resolve", missing)
    return {"schema_version": "paper-v15-independent-read-audit/1",
            "created_utc": datetime.now(timezone.utc).isoformat(), "status": "passed_current_claim_and_raw_profile_read_audit",
            "passed": True, "checks_passed": len(checks), "checks": checks,
            "draft_identity": draft_identity, "provenance_identity": record(provenance_path),
            "ledger_identity": record(ledger_path), "auditor_source_identity": record(__file__),
            "inherited_V14_saved_numerical_checks": 20, "inherited_numerical_runtime_reexecuted": False,
            "native_profiles_raw_reconstructed": native, "workflow_raw_reconstructed": workflow,
            "new_application_sdk_provider_solver_checker_or_evaluator_executions": 0,
            "human_scientific_review": False, "full_original_study_complete": False, "publication_ready": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("draft", "provenance", "ledger", "output"):
        parser.add_argument("--" + flag, type=Path, required=True)
    args = parser.parse_args()
    draft, provenance, ledger, output = [path.resolve() for path in (args.draft, args.provenance, args.ledger, args.output)]
    need(output.is_relative_to(ROOT / "paper") and not output.exists(), "fresh_paper_audit_output_required")
    value = audit(draft, provenance, ledger)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": value["status"], "checks_passed": value["checks_passed"],
                      "audit": record(output), "new_runtime_or_provider_calls": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
