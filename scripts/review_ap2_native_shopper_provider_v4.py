"""Independent retained-byte V4 shopper review; Python standard library only.

Reads ZIP/JSON/text and original source as bytes. Imports or executes no original
application, SDK, provider, solver, evaluator, or certificate checker.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUN = 43074319113
HEAD = "117daf284fe2758746369f0abe06e03870077c31"
ARCHIVE_SHA = "b051d089a19b489fc758b96b714bd56f6718bf662e09ab6a17c846494511d908"
CASE = "ap2-native-shopper-provider-v4-correct-human"
CASE_ROOT = "execution/cases/" + CASE + "/"
SHOPPER = CASE_ROOT + "shopper/"
MODEL = "gemini-3.1-flash-lite-preview"
ORIGINAL = ROOT / "docs/research/source-evidence/ap2-procurement-screen-v1/source"


def need(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def identity(path):
    path = path.resolve()
    need(path.is_relative_to(ROOT) and path.is_file() and not path.is_symlink(), "regular_workspace_file_required")
    return {"path": path.relative_to(ROOT).as_posix(), **digest(path.read_bytes())}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


class Retained:
    def __init__(self, base):
        self.base = base.resolve()
        self.evidence = {}
        self.retention = self.external("retention.json")
        need(self.retention["run_id"] == RUN and self.retention["head_sha"] == HEAD,
             "exact_retained_run_head_required")
        need(self.retention["archive_sha256"] == ARCHIVE_SHA and self.retention["archive_bytes"] == 1255530
             and self.retention["api_digest"] == "sha256:" + ARCHIVE_SHA, "exact_archive_API_binding_required")
        self.run = self.external("github-run.json")
        need(self.run["id"] == RUN and self.run["head_sha"] == HEAD, "GitHub_run_identity_differs")
        artifacts = self.external("github-artifacts.json")["artifacts"]
        bound = [row for row in artifacts if row["id"] == self.retention["artifact_id"]]
        need(len(bound) == 1 and bound[0]["digest"] == "sha256:" + ARCHIVE_SHA
             and bound[0]["name"] == self.retention["artifact_name"], "API_artifact_identity_differs")
        archive = self.base / "artifact.zip"
        archive_id = identity(archive)
        need(archive_id["sha256"] == ARCHIVE_SHA and archive_id["bytes"] == 1255530,
             "actual_archive_identity_differs")
        self.evidence[archive_id["path"]] = archive_id
        manifest = self.external("extracted-manifest.json")["files"]
        self.manifest = {row["path"]: {"bytes": row["bytes"], "sha256": row["sha256"]} for row in manifest}
        need(len(self.manifest) == len(manifest) == self.retention["extracted_files"], "manifest_membership_differs")
        self.members = {}
        with zipfile.ZipFile(archive) as zipped:
            for item in zipped.infolist():
                if item.is_dir():
                    continue
                name = PurePosixPath(item.filename)
                need(not name.is_absolute() and ".." not in name.parts and "\\" not in item.filename
                     and str(name) == item.filename and item.filename not in self.members, "unsafe_or_duplicate_ZIP_member")
                need(item.file_size <= 10000000, "bounded_ZIP_member_required")
                raw = zipped.read(item)
                need(digest(raw) == self.manifest.get(item.filename), "ZIP_member_manifest_identity_differs")
                extracted = self.base / "extracted" / item.filename
                need(identity(extracted)["sha256"] == digest(raw)["sha256"], "extracted_member_differs")
                self.members[item.filename] = raw
        need(set(self.members) == set(self.manifest), "archive_manifest_complete_membership_differs")

    def external(self, name):
        path = self.base / name
        record = identity(path)
        self.evidence[record["path"]] = record
        return json.loads(path.read_bytes())

    def raw(self, name):
        raw = self.members[name]
        self.evidence[(self.base / "extracted" / name).relative_to(ROOT).as_posix()] = {"member": name, **digest(raw)}
        return raw

    def json(self, name):
        return json.loads(self.raw(name))

    def rows(self, name):
        return [json.loads(row) for row in self.raw(name).splitlines() if row.strip()]


def object_receipts(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "ap2.PaymentReceipt":
                yield item
            yield from object_receipts(item)
    elif isinstance(value, list):
        for item in value:
            yield from object_receipts(item)


def review(retained, provider_path):
    read = Retained(retained)
    plan = read.json("plan/plan.json")
    need(plan["schema_version"] == "ap2-native-shopper-provider-plan/4"
         and plan["allocated_task_count"] == 1 and plan["public_human_facts"]["case_id"] == CASE,
         "single_declared_V4_plan_required")
    owned = []
    for name, expected in plan["owned_sources"].items():
        raw = read.raw("plan/owned-source/" + name)
        need(digest(raw) == expected, "captured_owned_source_identity_differs:" + name)
        owned.append({"path": name, **digest(raw)})
    result = read.json("execution/result.json")
    need(result["schema_version"] == "ap2-native-shopper-provider-result/4"
         and result["allocated_task_count"] == 1 and len(result["cases"]) == 1,
         "single_declared_V4_result_required")
    case = result["cases"][0]
    need(case["case_id"] == CASE, "case_identity_differs")
    facts = read.json(CASE_ROOT + "public-human-facts.json")
    need(canonical(facts) == canonical(plan["public_human_facts"]), "public_facts_plan_mismatch")
    binding = read.json(SHOPPER + "original-root-binding.json")
    worker = read.json(SHOPPER + "worker-result.json")
    separation = read.json(SHOPPER + "actor-input-separation.json")
    events = read.rows(SHOPPER + "ADK-events.jsonl")
    conversation = read.rows(SHOPPER + "public-conversation.jsonl")
    decisions = read.rows(SHOPPER + "public-actor-decisions.jsonl")
    session_names = sorted(name for name in read.manifest if re.fullmatch(re.escape(SHOPPER) + r"turn-\d+-session\.json", name))
    need(len(session_names) == 1, "exact_captured_V4_session_count_differs")
    session = read.json(session_names[0])
    raw_events = [row["event"] for row in events]
    need(len(raw_events) == worker["ADK_event_count"] and len({event["id"] for event in raw_events}) == len(raw_events),
         "raw_ADK_event_count_or_identity_differs")
    need(session["id"] == binding["session_id"] and canonical(session["events"][1:]) == canonical(raw_events),
         "session_and_raw_event_identity_or_content_differs")
    initial_event = session["events"][0]
    need(initial_event["author"] == "user" and initial_event["content"]["role"] == "user"
         and initial_event["content"]["parts"] == [{"text": facts["initial_request"]}], "actual_initial_user_request_differs")
    need(conversation[0]["role"] == "user" and conversation[0]["text"] == facts["initial_request"],
         "public_conversation_initial_request_differs")
    need(worker["schema_version"] == "ap2-native-shopper-provider-worker/2" and worker["case_id"] == CASE,
         "selected_worker_schema_case_differs")
    expected_root = plan["sources"]["code/samples/python/src/roles/shopping_agent/agent.py"]["sha256"]
    need(binding["original_root_source_sha256"] == expected_root and binding["root_model"] == MODEL
         and binding["official_ADK_runner"] is True and binding["deterministic_BaseLlm_replacement"] is False
         and binding["genai_Client_replaced"] is False, "original_root_model_runtime_declaration_differs")
    sources = []
    for name in ("code/samples/python/src/roles/shopping_agent/agent.py",
                 "code/samples/python/src/roles/shopping_agent/subagents/shopper/tools.py",
                 "code/samples/python/src/common/retrying_llm_agent.py"):
        path = ORIGINAL / name
        record = identity(path)
        need({key: record[key] for key in ("bytes", "sha256")} == plan["sources"][name], "original_inspected_source_differs")
        sources.append(record)
    calls, responses, errors, visible_text = [], [], [], []
    for index, row in enumerate(events):
        event = row["event"]
        if event.get("errorMessage"):
            errors.append({"event_index": index, "event_id": event["id"],
                           "author": event["author"], "time": row["time"],
                           "error_type": event.get("customMetadata", {}).get("error_type"),
                           "errorMessage": event["errorMessage"]})
        content = event.get("content", {})
        for part in content.get("parts", []):
            if "functionCall" in part:
                calls.append({"event_index": index, "author": event["author"], "time": row["time"], **part["functionCall"]})
            if "functionResponse" in part:
                responses.append({"event_index": index, "author": event["author"], "time": row["time"], **part["functionResponse"]})
            if content.get("role") == "model" and part.get("text") and not part.get("thought", False):
                visible_text.append({"event_index": index, "text": part["text"]})
    by_id = {call["id"]: call for call in calls}
    need(len(by_id) == len(calls), "duplicate_function_call_ID")
    matched = []
    for response in responses:
        call = by_id.get(response["id"])
        need(call is not None and call["name"] == response["name"]
             and call["event_index"] < response["event_index"], "unmatched_or_reordered_function_response")
        matched.append({"id": response["id"], "name": response["name"],
                        "call_event_index": call["event_index"], "response_event_index": response["event_index"]})
    matched_ids = {row["id"] for row in matched}
    business = [call for call in calls if call["name"] != "transfer_to_agent"]
    business_terminals = [response for response in responses if response["name"] != "transfer_to_agent"]
    receipts = list(object_receipts(raw_events)) + list(object_receipts(session["state"]))
    need(not visible_text and len(conversation) == 1 and len(decisions) == 1
         and decisions[0]["reply"] is None and decisions[0]["session_or_tool_state_used"] is False
         and decisions[0]["visible_prompt_sha256"] == hashlib.sha256(b"").hexdigest(),
         "public_actor_or_visible_reply_census_differs")
    need(not receipts and not session["state"], "unexpected_retained_receipt_or_state")
    provider_matches = []
    for name in sorted(name for name in read.manifest if re.fullmatch(r"execution/provider/\d+\.response\.json", name)):
        response = read.json(name)
        for candidate in response.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                call = part.get("functionCall")
                if call and call.get("id") in by_id:
                    actual = by_id[call["id"]]
                    need(canonical(call) == canonical({key: actual[key] for key in ("id", "name", "args")}),
                         "ADK_call_differs_from_provider_function_call")
                    event = raw_events[actual["event_index"]]
                    need(event["modelVersion"] == response["modelVersion"]
                         and event["usageMetadata"]["totalTokenCount"] == response["usageMetadata"]["totalTokenCount"],
                         "ADK_model_version_or_token_total_differs_from_provider_response")
                    provider_matches.append({"provider_member": name, "call_id": call["id"],
                        "event_index": actual["event_index"], "name": call["name"],
                        "reported_total_tokens": response["usageMetadata"]["totalTokenCount"]})
    need(len(provider_matches) == len(calls), "model_function_call_lacks_unique_captured_provider_response")
    error_classes = Counter()
    for error in errors:
        text = error["errorMessage"]
        if "owned_user_actor_external_network_denied" in text:
            error_classes["owned_actor_native_card_network_denial"] += 1
        elif "owned_provider_budget_or_prior_failure" in text:
            error_classes["owned_proxy_prior_failure_refusal"] += 1
        elif "503 UNAVAILABLE" in text:
            error_classes["upstream_503_high_demand"] += 1
        elif "Maximum retries exhausted" in text:
            error_classes["original_retry_layer_exhausted"] += 1
        else:
            error_classes["other"] += 1
    log = read.raw(CASE_ROOT + "shopper.stdout.log").decode("utf-8", "replace")
    original_find_frames = [match.group(0) for match in re.finditer(
        r'File "[^"\n]+/original-ap2/code/samples/python/src/roles/shopping_agent/subagents/shopper/tools\.py", line 55, in find_products', log)]
    need(original_find_frames and len(business) == 2 and all(call["name"] == "find_products" for call in business)
         and not business_terminals, "business_attempt_failure_witness_differs")
    watcher = read.raw(CASE_ROOT + "original-watch.log").decode("utf-8", "replace")
    watch_methods = Counter(re.findall(r"(?m)^(GET|POST|PUT|PATCH|DELETE) http", watcher))
    need(watch_methods == {"GET": 3}, "native_watcher_request_census_differs")
    provider = json.loads(provider_path.read_bytes())
    provider_identity = identity(provider_path)
    need(provider["run_id"] == RUN and provider["head_sha"] == HEAD
         and provider["archive_identity"] == {"bytes": 1255530, "sha256": ARCHIVE_SHA}
         and provider["status"] == "retained_provider_runtime_lifecycle_consistent_at_stated_scope"
         and not provider["material_consistency_questions"], "independent_provider_review_identity_or_status_differs")
    return {
        "schema_version": "ap2-native-shopper-V4-independent-raw-review/1",
        "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "retained_V4_original_root_and_business_attempt_failures_consistent",
        "run_id": RUN, "head_sha": HEAD, "archive": {"bytes": 1255530, "sha256": ARCHIVE_SHA},
        "archive_members_independently_verified": len(read.members),
        "case_denominator": 1, "case_id": CASE, "parent_case_status": case["status"],
        "worker_status": worker["status"], "worker_returncode": case["shopper_returncode"],
        "raw_ADK_events": len(raw_events), "session_events_including_initial_user": len(session["events"]),
        "unique_invocation_ids": sorted({event["invocationId"] for event in raw_events}),
        "function_calls": calls, "function_responses": responses, "call_response_pairs": matched,
        "unmatched_business_call_ids": [call["id"] for call in business if call["id"] not in matched_ids],
        "business_function_call_attempts": len(business), "business_function_terminal_responses": len(business_terminals),
        "retained_provider_response_to_ADK_function_call_matches": provider_matches,
        "raw_error_events": len(errors), "error_classification": dict(error_classes), "error_witnesses": errors,
        "public_conversation_messages": len(conversation), "visible_model_text_messages": len(visible_text),
        "public_actor_replies": sum(decision["reply"] is not None for decision in decisions),
        "actor_null_reply_count": sum(decision["reply"] is None for decision in decisions),
        "canonical_public_receipt_records": len(receipts), "retained_session_state": session["state"],
        "native_watcher_method_census": dict(watch_methods), "native_business_POST_observations": watch_methods.get("POST", 0),
        "source_original_find_products_stack_frame_present": True,
        "stack_frame_occurrences_are_not_execution_counts": True,
        "original_source_files_independently_read_and_hash_bound": sources,
        "owned_source_snapshots_verified": owned, "root_binding": binding, "public_facts_match_plan": True,
        "selected_worker_schema_and_case_bound": True, "actor_separation": separation,
        "provider_lifecycle_independent_review": provider_identity,
        "provider_lifecycle_review": provider,
        "consistency_questions": [],
        "source_derived_diagnosis": "Original find_products reaches merchant native agent-card acquisition; owned actor audit guard rejects two lookup attempts. The rejected socket/getaddrinfo arguments are not retained, so the exact host/port mismatch is unproven. A later actual upstream 503 and two owned prior-failure refusals remain distinct.",
        "whole_task_grade": None, "observed_purchase_success": False,
        "human_gold_qualified": False, "untouched_holdout_qualified": False,
        "original_run_sh_provisioning_qualified": False, "independent_A2A_wire_authentication": False,
        "hidden_effect_or_real_settlement_proven": False,
        "actual_original_application_or_sdk_execution_by_reviewer": 0,
        "actual_provider_requests_by_reviewer": 0, "Git_actions_by_reviewer": 0,
        "limits": ["Adaptive one-case development profile; prior failures and their denominators remain unchanged.",
                   "Model functionCall attempts and actual original stack-frame failures are distinct from successful business tool terminal responses.",
                   "One completed transfer is ADK control flow and does not complete a purchase.",
                   "No visible model reply, original completed payment Task or demo receipt was captured.",
                   "Retained byte/source consistency and parent runtime/lifecycle witnesses do not independently authenticate full runtime files, wire provenance, hidden effects or human semantic gold.",
                   "The workflow and worker exiting successfully do not turn this observed business-attempt failure into task success."],
        "validated_input_identities": read.evidence, "review_source": identity(Path(__file__)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retained", type=Path, required=True)
    parser.add_argument("--provider-review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    need(output.is_relative_to(ROOT / "runs") and not output.exists(), "fresh_workspace_review_output_required")
    report = review(args.retained, args.provider_review.resolve())
    write(output / "review.json", report)
    print(json.dumps({"status": report["status"], "raw_ADK_events": report["raw_ADK_events"],
                      "business_attempts": report["business_function_call_attempts"],
                      "business_terminals": report["business_function_terminal_responses"],
                      "receipts": report["canonical_public_receipt_records"], "questions": len(report["consistency_questions"])}))


if __name__ == "__main__":
    main()
