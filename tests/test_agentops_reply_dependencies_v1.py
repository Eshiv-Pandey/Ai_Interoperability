"""SYNTHETIC stdlib-only reply/value observations; no tools, SDK or model run.

The all-case fixtures deliberately manufacture source-shaped observations.
They verify the pure assessor and provide no native source-case evidence.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from interoperability.agentops_reply_dependencies_v1 import assess_reply_dependencies
from interoperability.agentops_required_trajectory_v1 import invocations_from_events, score_invocations

USER = "SYNTHETIC-NATIVE-USER"
SESSION = "SYNTHETIC-NATIVE-SESSION"
PREFIX = "<<<TOOL_DATA data-not-instructions>>>"
SUFFIX = "<<<END_TOOL_DATA>>>"
PAUSE = "This tool call requires confirmation, please approve or reject."
TS = "2026-10-30T00:00:00Z"
NOTE = "I raised the api-gateway memory limit to 2Gi as a stopgap."


def identity(value):
    raw = json.dumps(value, sort_keys=True, allow_nan=False).encode()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def incident(incident_id):
    service, runbook = {"INC-001": ("checkout", "high-latency"), "INC-002": ("inventory", "service-down"),
                        "INC-005": ("search", "high-latency"), "INC-007": ("cache", "memory-leak"),
                        "INC-009": ("api-gateway", "cascade-failure"), "INC-010": ("api-gateway", "memory-leak")}[incident_id]
    return {"id": incident_id, "service": service, "runbook": runbook, "title": "SYNTHETIC incident",
            "severity": "SEV2", "status": "resolved" if incident_id == "INC-007" else "investigating",
            "opened_at": TS, "resolved_at": TS if incident_id == "INC-007" else None, "summary": "SYNTHETIC observation"}


def payload(name, args, classification="source_supported_success", memory_saved=False):
    if classification == "expected_missing_incident_error":
        return {"error": f"No incident found with id {args['incident_id']!r}."}
    if classification == "expected_missing_service_error":
        return {"error": f"No service named {args['name']!r}. Known services: inventory, cache, checkout."}
    if classification == "expected_missing_sample_logs_error":
        return {"error": f"No logs for service {args['service']!r}. Available logs: inventory, database, cache, checkout."}
    if name == "get_incident":
        return {"incident": incident(args["incident_id"])}
    if name == "get_service_status":
        return {"service": {"name": args["name"], "description": "SYNTHETIC service", "status": "degraded", "owner": "SYNTHETIC team"}, "open_incidents": []}
    if name == "search_service_logs":
        return {"service": args["service"], "count": 1, "lines": ["SYNTHETIC sample log"]}
    if name == "get_runbook":
        return {"slug": args["slug"], "content": "# SYNTHETIC full instruction body\nRead the observed evidence."}
    if name == "search_runbooks":
        return {"count": 1, "retrieval": "keyword", "runbooks": [{"slug": "memory-leak", "content": "SYNTHETIC ranked runbook"}]}
    if name == "list_skills":
        return {"result": "<available_skills>\n<skill>\n<name>\nremediation\n</name>\n<description>\nSYNTHETIC discovery summary\n</description>\n</skill>\n</available_skills>"}
    if name == "load_skill":
        return {"skill_name": args["skill_name"], "instructions": "# SYNTHETIC full instructions\nRequire evidence and approval.",
                "frontmatter": {"name": args["skill_name"], "description": "SYNTHETIC discovery summary", "metadata": {}}}
    if name == "save_incident_note":
        return {"saved": {"incident_id": args["incident_id"], "ts": TS, "note": args["note"]}}
    if name == "recall_incident_context":
        notes = [{"incident_id": "INC-010", "ts": TS, "note": NOTE}] if memory_saved else []
        return {"count": len(notes), "notes": notes}
    if name in {"restart_service", "resolve_incident"}:
        return {"error": PAUSE}
    raise AssertionError(name)


def function(name, args, identifier):
    return {"id": identifier, "name": name, "args": deepcopy(args)}


def event(parts, *, branch=None, partial=False, author="SYNTHETIC_AGENT", long_running=None):
    result = {"author": author, "branch": branch, "partial": partial, "content": {"role": "model", "parts": deepcopy(parts)}}
    if long_running is not None:
        result["long_running_tool_ids"] = long_running
    return result


def call_event(name, args, identifier, **kwargs):
    return event([{"function_call": function(name, args, identifier)}], **kwargs)


def reply_event(name, response, identifier, **kwargs):
    return event([{"function_response": {"id": identifier, "name": name, "response": deepcopy(response)}}], **kwargs)


def confirmation_event(name, args, identifier):
    request_id = "SYNTHETIC-CONFIRMATION-" + identifier
    return call_event("adk_request_confirmation", {"originalFunctionCall": function(name, args, identifier),
                      "toolConfirmation": {"confirmed": False, "hint": f"Please approve or reject the tool call {name}() by responding with a FunctionResponse with an expected ToolConfirmation payload."}},
                      request_id, long_running=[request_id])


def rebuild(report):
    """Rebind fabricated in-memory reports; never modifies retained evidence."""
    ordered, global_yield = [], 0
    for turn, call in enumerate(report["calls"], 1):
        records = []
        actual_id = f"SYNTHETIC-NATIVE-INVOCATION-{turn}"
        for ordinal, observed in enumerate(call["events"], 1):
            global_yield += 1
            observed.setdefault("id", f"SYNTHETIC-EVENT-{turn}-{ordinal}")
            observed.setdefault("invocation_id", actual_id)
            record = {"event_ordinal": ordinal, "batch_ordinal": ordinal, "global_yield_sequence": global_yield,
                      "actual_event_id": observed["id"], "actual_invocation_id": observed["invocation_id"],
                      "captured_before_downstream_yield": True, "part_count_in_original_yield": len(observed["content"]["parts"]),
                      "path": f"invocations/{turn:06d}/events/{ordinal:06d}.json", **identity(observed)}
            records.append(record)
            ordered.append({**record, "invocation_sequence": turn, "event": observed})
        receipt = {"schema_version": "agentops-runtime-stream/1", "status": "recorded", "invocation_sequence": turn,
                   "capture_disabled": False, "capture_errors": [], "original_termination": "normal_exhaustion",
                   "original_error_type": None, "cleanup_error_type": None, "original_call_attempts": 1,
                   "events": records, "observed_invocation_ids": list(dict.fromkeys(item["invocation_id"] for item in call["events"]))}
        for key in ("capture_complete", "durable_receipt_written", "inputs_complete", "directory_created_exclusively",
                    "original_aclose_attempted", "original_aclose_completed", "event_identity_fields_complete"):
            receipt[key] = True
        for key in ("events_seen", "events_recorded", "downstream_yields_entered"):
            receipt[key] = len(records)
        call.update(event_records=records, receipt=receipt, receipt_identity=identity(receipt))
    report["ordered_event_records"] = ordered
    report["ordered_events"] = [row["event"] for row in ordered]
    return report


def synthetic_journal(obligation):
    calls = []
    for turn in obligation["turns"]:
        events = []
        for required in turn["original_metric"]["required_trajectory"]:
            name, args = required["name"], required["required_args"]
            identifier = f"SYNTHETIC-CALL-{turn['turn_index']}-{required['sequence']}"
            classification = required["reply_extra_assessment"]["classification"]
            events.append(call_event(name, args, identifier))
            events.append(reply_event(name, payload(name, args, classification, obligation["eval_id"] == "memory-note-recall" and turn["turn_index"] == 2), identifier))
            if classification == "confirmation_pause_not_execution":
                events.append(confirmation_event(name, args, identifier))
        calls.append({"invocation_sequence": turn["turn_index"], "inputs": {"user_id": USER, "session_id": SESSION, "invocation_id": None}, "events": events})
    return rebuild({"schema_version": "agentops-runtime-stream-evidence/1", "status": "validated", "calls": calls,
                    "recorded_publication_order_validated": True, "receipt_identity": identity("SYNTHETIC ROOT RECEIPT"),
                    "observer_identity": identity("SYNTHETIC OBSERVER"), "SYNTHETIC_TEST_OBSERVATIONS_ONLY": True})


class ReplyDependencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = json.loads((ROOT / "docs/research/upstream-agentops-grading-obligations-v1.json").read_bytes())
        cls.obligations = manifest["case_obligations"]
        cls.by_name = {item["eval_id"]: item for item in cls.obligations}

    def setUp(self):
        self.obligation = deepcopy(self.by_name["recommend-fix"])
        self.report = synthetic_journal(self.obligation)

    def assess(self, report=None, obligation=None, **kwargs):
        return assess_reply_dependencies(self.report if report is None else report, self.obligation if obligation is None else obligation,
                                         expected_native_user_id=kwargs.get("user", USER), expected_native_session_id=kwargs.get("session", SESSION))

    def choose(self, name):
        self.obligation = deepcopy(self.by_name[name])
        self.report = synthetic_journal(self.obligation)

    def rebuild(self):
        rebuild(self.report)

    def test_all_21_cases_22_turns_have_separate_synthetic_expected_reply_classes(self):
        self.assertEqual(len(self.obligations), 21)
        self.assertEqual(sum(item["turn_count"] for item in self.obligations), 22)
        for obligation in self.obligations:
            with self.subTest(case=obligation["eval_id"]):
                result = self.assess(synthetic_journal(obligation), obligation)
                self.assertEqual(result["status"], "observed_reply_and_value_consistency")
                self.assertEqual(result["reply_consistency_status"], "supported")
                self.assertEqual(result["dependency_consistency_status"], "unknown" if obligation["eval_id"] == "memory-note-recall" else
                                 "supported" if any(turn["source_dependencies_extra_assessment"] for turn in obligation["turns"]) else "not_applicable")
                for field in ("benchmark_grade_proven", "actual_tool_dataflow_proven", "awaited_tool_execution_proven", "original_configured_metric_modified",
                              "source_authentication_proven", "state_effects_proven", "full_task_grade_assigned", "native_source_case_qualification"):
                    self.assertIs(result[field], False)

    def test_calls_without_replies_are_unknown_even_when_original_metric_passes(self):
        self.report["calls"][0]["events"] = [item for item in self.report["calls"][0]["events"] if "function_call" in item["content"]["parts"][0]]
        self.rebuild()
        result = self.assess()
        self.assertEqual(result["reply_consistency_status"], "unknown")
        expected = [{"intermediate_data": {"tool_uses": self.obligation["turns"][0]["original_metric"]["expected_calls"]}}]
        metric = score_invocations(invocations_from_events(self.report["ordered_events"]), expected)
        self.assertEqual(metric["overall_score"], 1.0)
        self.assertIs(metric["awaited_dependencies_proven"], False)

    def test_same_batch_reply_before_consumer_is_not_dependency_support(self):
        for reversed_parts in (False, True):
            with self.subTest(reversed_parts=reversed_parts):
                report = synthetic_journal(self.obligation)
                events = report["calls"][0]["events"]
                parts = events[1]["content"]["parts"] + events[2]["content"]["parts"]
                events[1]["content"]["parts"] = list(reversed(parts)) if reversed_parts else parts
                del events[2]
                rebuild(report)
                result = self.assess(report)
                self.assertEqual(result["turns"][0]["dependency_assessments"][0]["status"], "unknown")
                self.assertIs(result["same_yield_array_order_used_as_dependency_support"], False)

    def test_same_batch_call_and_reply_cannot_attribute_by_part_array_order(self):
        events = self.report["calls"][0]["events"]
        events[0]["content"]["parts"].extend(events[1]["content"]["parts"])
        del events[1]
        self.rebuild()
        self.assertEqual(self.assess()["turns"][0]["required_reply_assessments"][0]["status"], "unknown")

    def test_returned_value_must_equal_consumer_verbatim(self):
        self.report["calls"][0]["events"][1]["content"]["parts"][0]["function_response"]["response"]["incident"]["service"] = "checkout"
        self.rebuild()
        row = self.assess()["turns"][0]["dependency_assessments"][0]
        self.assertEqual(row["status"], "inconsistent")
        self.assertEqual(row["producer_observed_value"], "checkout")
        self.assertEqual(row["consumer_observed_value"], "inventory")

    def test_multiple_partial_call_observations_are_retained_and_ambiguous(self):
        events = self.report["calls"][0]["events"]
        duplicate = deepcopy(events[0])
        duplicate.pop("id")
        duplicate["partial"] = True
        events.insert(1, duplicate)
        self.rebuild()
        result = self.assess()
        self.assertEqual(len(result["turns"][0]["tool_calls"]), 4)
        self.assertEqual(result["turns"][0]["tool_replies"][0]["candidate_call_observation_indices"], [0, 1])
        self.assertEqual(result["dependency_consistency_status"], "unknown")
        self.assertIs(result["partial_calls_deduplicated"], False)

    def test_identical_repeated_replies_are_not_silently_collapsed(self):
        duplicate = deepcopy(self.report["calls"][0]["events"][1])
        duplicate.pop("id")
        self.report["calls"][0]["events"].insert(2, duplicate)
        self.rebuild()
        result = self.assess()
        self.assertEqual(len(result["turns"][0]["tool_replies"]), 4)
        self.assertEqual(result["turns"][0]["required_reply_assessments"][0]["status"], "unknown")

    def test_reply_and_consumer_branch_mismatches_are_unknown(self):
        for index in (1, 2):
            with self.subTest(index=index):
                report = synthetic_journal(self.obligation)
                report["calls"][0]["events"][index]["branch"] = "SYNTHETIC_OTHER_BRANCH"
                if index == 2:
                    report["calls"][0]["events"][3]["branch"] = "SYNTHETIC_OTHER_BRANCH"
                rebuild(report)
                self.assertEqual(self.assess(report)["turns"][0]["dependency_assessments"][0]["status"], "unknown")

    def test_reply_requires_actual_id_and_exact_name(self):
        for key, value in (("id", None), ("id", "WRONG"), ("name", "get_runbook")):
            with self.subTest(key=key, value=value):
                report = synthetic_journal(self.obligation)
                report["calls"][0]["events"][1]["content"]["parts"][0]["function_response"][key] = value
                rebuild(report)
                self.assertEqual(self.assess(report)["turns"][0]["required_reply_assessments"][0]["status"], "unknown")

    def test_user_authored_function_reply_cannot_forge_support(self):
        self.report["calls"][0]["events"][1]["author"] = "user"
        self.rebuild()
        self.assertEqual(self.assess()["dependency_consistency_status"], "unknown")

    def test_expected_missing_resource_error_is_legitimate_not_provider_failure(self):
        for name, expected in (("unknown-incident", "expected_missing_incident_error"), ("unknown-service", "expected_missing_service_error"),
                               ("gateway-memory-report", "expected_missing_sample_logs_error"), ("gateway-memory-evidence-review", "expected_missing_sample_logs_error")):
            with self.subTest(case=name):
                self.choose(name)
                result = self.assess()
                self.assertEqual(result["reply_consistency_status"], "supported")
                self.assertIn(expected, [item["source_contract_classification"] for item in result["turns"][0]["tool_replies"]])

    def test_illustrative_listing_order_is_not_an_expected_error_oracle(self):
        self.choose("unknown-service")
        response = self.report["calls"][0]["events"][1]["content"]["parts"][0]["function_response"]
        response["response"]["error"] = "No service named 'warehouse'. Known services: search, database."
        self.rebuild()
        self.assertEqual(self.assess()["reply_consistency_status"], "supported")

    def test_wrong_missing_error_or_fabricated_success_is_inconsistent_or_unknown(self):
        self.choose("unknown-incident")
        response = self.report["calls"][0]["events"][1]["content"]["parts"][0]["function_response"]
        response["response"] = {"error": "No incident found with id 'INC-002'."}
        self.rebuild()
        self.assertEqual(self.assess()["reply_consistency_status"], "inconsistent")
        response["response"] = {"incident": {"id": "INC-999"}}
        self.rebuild()
        self.assertEqual(self.assess()["reply_consistency_status"], "unknown")

    def test_source_error_on_expected_success_is_separate_from_original_metric(self):
        self.report["calls"][0]["events"][1]["content"]["parts"][0]["function_response"]["response"] = {"error": "Tool 'get_incident' failed safely; inspect the service logs for the root cause."}
        self.rebuild()
        self.assertEqual(self.assess()["reply_consistency_status"], "inconsistent")

    def test_approval_request_is_supported_observation_without_execution_claim(self):
        self.choose("restart-needs-approval")
        result = self.assess()
        self.assertEqual(result["reply_consistency_status"], "supported")
        self.assertIs(result["tool_body_execution_proven"], False)
        self.assertEqual(result["turns"][0]["tool_replies"][-1]["source_contract_classification"], "approval_not_executed_reply")

    def test_multiple_same_id_action_response_phases_remain_visible(self):
        self.choose("restart-needs-approval")
        events = self.report["calls"][0]["events"]
        action = events[-3]["content"]["parts"][0]["function_call"]
        audit = {"id": 1, "schema_version": 1, "ts": TS, "actor": "agentops-agent", "approved_by": USER,
                 "rationale": "SYNTHETIC approval", "context_summary": "SYNTHETIC context", "session_id": SESSION,
                 "invocation_id": "SYNTHETIC-NATIVE-INVOCATION-1", "action": "restart_service", "target": "inventory",
                 "detail": "service restarted and marked operational (mock)"}
        events.append(reply_event("restart_service", {"result": "Service 'inventory' restarted and marked operational.", "audit": audit}, action["id"]))
        self.rebuild()
        result = self.assess()
        self.assertEqual(result["turns"][0]["required_reply_assessments"][-1]["observed_attributed_source_classifications"],
                         ["approval_not_executed_reply", "success_reply"])
        self.assertEqual(result["reply_consistency_status"], "inconsistent")
        self.assertIs(result["state_effects_proven"], False)

    def test_missing_or_mutated_confirmation_request_stays_unknown(self):
        for mutation in ("missing", "target", "confirmed", "user", "long_running", "partial_metadata", "partial_event"):
            with self.subTest(mutation=mutation):
                self.choose("resolve-needs-approval")
                events = self.report["calls"][0]["events"]
                request = events[-1]["content"]["parts"][0]["function_call"]
                if mutation == "missing":
                    events.pop()
                elif mutation == "target":
                    request["args"]["originalFunctionCall"]["args"]["incident_id"] = "INC-002"
                elif mutation == "confirmed":
                    request["args"]["toolConfirmation"]["confirmed"] = 1
                elif mutation == "user":
                    events[-1]["author"] = "user"
                elif mutation == "partial_metadata":
                    request["partial_args"] = [{"json_path": "$.invented", "string_value": "unsupported"}]
                elif mutation == "partial_event":
                    events[-1]["partial"] = True
                else:
                    events[-1].pop("long_running_tool_ids")
                self.rebuild()
                self.assertEqual(self.assess()["turns"][0]["required_reply_assessments"][-1]["status"], "unknown")

    def test_guarded_action_requires_all_read_replies_in_earlier_yields(self):
        self.choose("restart-needs-approval")
        events = self.report["calls"][0]["events"]
        events[-4]["content"]["parts"].extend(events[-3]["content"]["parts"])
        del events[-3]
        self.rebuild()
        barrier = self.assess()["turns"][0]["dependency_assessments"][-1]
        self.assertEqual(barrier["status"], "unknown")

    def test_empty_recall_is_successful_data_before_incident_read(self):
        self.choose("investigation-recalls-context")
        result = self.assess()
        self.assertEqual(result["reply_consistency_status"], "supported")
        self.assertEqual(result["dependency_consistency_status"], "supported")
        self.assertEqual(result["turns"][0]["tool_replies"][0]["payload"], {"count": 0, "notes": []})

    def test_skill_discovery_xml_and_instruction_reply_are_separate(self):
        self.choose("remediation-loads-skill")
        self.assertEqual(self.assess()["dependency_consistency_status"], "supported")
        load = self.report["calls"][0]["events"][3]["content"]["parts"][0]["function_response"]["response"]
        load["content"] = load.pop("instructions")
        self.rebuild()
        result = self.assess()
        self.assertEqual(result["reply_consistency_status"], "unknown")
        self.assertEqual(result["dependency_consistency_status"], "unknown")

    def test_skill_discovery_must_include_requested_name(self):
        self.choose("remediation-loads-skill")
        response = self.report["calls"][0]["events"][1]["content"]["parts"][0]["function_response"]["response"]
        response["result"] = response["result"].replace("remediation", "different-skill")
        self.rebuild()
        self.assertEqual(self.assess()["dependency_consistency_status"], "inconsistent")

    def test_xml_entities_and_invented_discovery_dicts_are_unsupported(self):
        self.choose("remediation-loads-skill")
        for value in ({"skills": ["remediation"]}, {"result": "<!DOCTYPE a [<!ENTITY x 'unsafe'>]><available_skills/>"}, {"result": "<available_skills extra='yes'/>"}):
            with self.subTest(value=value):
                report = synthetic_journal(self.obligation)
                report["calls"][0]["events"][1]["content"]["parts"][0]["function_response"]["response"] = value
                rebuild(report)
                self.assertEqual(self.assess(report)["reply_consistency_status"], "unknown")

    def test_spotlight_log_fences_do_not_change_original_count(self):
        response = self.report["calls"][0]["events"][3]["content"]["parts"][0]["function_response"]["response"]
        response["lines"] = [PREFIX, *response["lines"], SUFFIX]
        self.rebuild()
        result = self.assess()
        self.assertEqual(result["reply_consistency_status"], "supported")
        self.assertEqual(result["turns"][0]["tool_replies"][1]["payload"]["count"], 1)
        self.assertIs(result["tool_output_transformation_proven"], False)

    def test_bad_reply_types_and_unsupported_fields_stay_unknown(self):
        for mutation in ("count_bool", "lines", "service", "extra"):
            with self.subTest(mutation=mutation):
                report = synthetic_journal(self.obligation)
                response = report["calls"][0]["events"][3]["content"]["parts"][0]["function_response"]["response"]
                if mutation == "count_bool":
                    response["count"] = True
                elif mutation == "lines":
                    response["lines"] = []
                elif mutation == "service":
                    response["service"] = None
                else:
                    response["invented_success"] = True
                rebuild(report)
                self.assertEqual(self.assess(report)["reply_consistency_status"], "unknown")

    def test_malformed_enum_and_error_code_do_not_crash_classifier(self):
        for value in ([], {}, True):
            with self.subTest(value=value):
                report = synthetic_journal(self.obligation)
                report["calls"][0]["events"][1]["content"]["parts"][0]["function_response"]["response"]["incident"]["severity"] = value
                rebuild(report)
                self.assertEqual(self.assess(report)["reply_consistency_status"], "unknown")

    def test_first_diagnostic_filter_is_not_permitted_by_stronger_argument_check(self):
        self.report["calls"][0]["events"][2]["content"]["parts"][0]["function_call"]["args"]["query"] = "panic"
        self.rebuild()
        result = self.assess()
        self.assertEqual(result["argument_consistency_status"], "inconsistent")
        self.assertEqual(result["reply_consistency_status"], "supported")

    def test_later_filter_needs_distinct_earlier_unfiltered_reply(self):
        for in_same_yield in (False, True):
            with self.subTest(in_same_yield=in_same_yield):
                report = synthetic_journal(self.obligation)
                events = report["calls"][0]["events"]
                extra = call_event("search_service_logs", {"service": "inventory", "query": "panic"}, "SYNTHETIC-EXTRA-FILTER")
                if in_same_yield:
                    events[3]["content"]["parts"].extend(extra["content"]["parts"])
                else:
                    events.insert(4, extra)
                rebuild(report)
                self.assertEqual(self.assess(report)["argument_consistency_status"], "unknown" if in_same_yield else "supported")

    def test_extra_filtered_read_before_required_sample_is_retained_and_inconsistent(self):
        self.report["calls"][0]["events"].insert(2, call_event("search_service_logs", {"service": "inventory", "query": "panic"}, "SYNTHETIC-EARLY-FILTER"))
        self.rebuild()
        result = self.assess()
        self.assertEqual(result["argument_consistency_status"], "inconsistent")
        self.assertEqual(len(result["turns"][0]["tool_calls"]), 4)

    def test_displayed_save_recall_consistency_never_proves_committed_rows(self):
        self.choose("memory-note-recall")
        result = self.assess()
        self.assertEqual(result["cross_turn_displayed_note_consistency"]["status"], "supported")
        self.assertEqual(result["turns"][1]["dependency_assessments"][0]["status"], "unavailable")
        self.assertIs(result["committed_memory_persistence_proven"], False)

    def test_duplicate_recalled_note_rows_are_not_deduplicated(self):
        self.choose("memory-note-recall")
        response = self.report["calls"][1]["events"][1]["content"]["parts"][0]["function_response"]["response"]
        response["notes"].append(deepcopy(response["notes"][0]))
        response["count"] = 2
        self.rebuild()
        result = self.assess()
        self.assertEqual(result["cross_turn_displayed_note_consistency"]["status"], "unknown")
        self.assertEqual(result["cross_turn_displayed_note_consistency"]["exact_matching_note_indices"], [0, 1])

    def test_differently_transformed_note_text_is_preserved_and_unresolved(self):
        self.choose("memory-note-recall")
        self.report["calls"][1]["events"][1]["content"]["parts"][0]["function_response"]["response"]["notes"][0]["note"] = PREFIX + "\n" + NOTE + "\n" + SUFFIX
        self.rebuild()
        self.assertEqual(self.assess()["cross_turn_displayed_note_consistency"]["status"], "unknown")

    def test_extra_unknown_tool_and_response_remain_explicit(self):
        events = self.report["calls"][0]["events"]
        events.extend([call_event("invented_tool", {}, "SYNTHETIC-UNKNOWN"), reply_event("invented_tool", {"result": "SYNTHETIC"}, "SYNTHETIC-UNKNOWN")])
        self.rebuild()
        result = self.assess()
        self.assertIs(result["turns"][0]["tool_calls"][-1]["known_source_tool_contract"], False)
        self.assertEqual(result["turns"][0]["tool_calls"][-1]["declared_source_scope"], "outside_supplied_case_tool_scope")
        self.assertEqual(result["turns"][0]["tool_replies"][-1]["source_contract_classification"], "unknown")

    def test_nonstandard_partial_call_metadata_cannot_supply_stronger_attribution(self):
        self.report["calls"][0]["events"][0]["content"]["parts"][0]["function_call"]["will_continue"] = True
        self.rebuild()
        result = self.assess()
        self.assertEqual(result["reply_consistency_status"], "unknown")
        self.assertIs(result["turns"][0]["tool_calls"][0]["ordinary_source_call_shape_supported"], False)

    def test_invalid_timestamp_and_frontmatter_metadata_are_unknown(self):
        self.choose("memory-note-recall")
        self.report["calls"][0]["events"][1]["content"]["parts"][0]["function_response"]["response"]["saved"]["ts"] = "2026-99-99T00:00:00Z"
        self.rebuild()
        self.assertEqual(self.assess()["reply_consistency_status"], "unknown")
        self.choose("remediation-loads-skill")
        self.report["calls"][0]["events"][3]["content"]["parts"][0]["function_response"]["response"]["frontmatter"]["metadata"] = []
        self.rebuild()
        self.assertEqual(self.assess()["reply_consistency_status"], "unknown")

    def test_existing_recall_rows_keep_source_text_timestamps_without_writer_oracle(self):
        self.choose("investigation-recalls-context")
        response = self.report["calls"][0]["events"][1]["content"]["parts"][0]["function_response"]["response"]
        response.update(count=1, notes=[{"ts": "SYNTHETIC older stored TEXT", "incident_id": "INC-002", "note": "SYNTHETIC old note"}])
        self.rebuild()
        result = self.assess()
        self.assertEqual(result["reply_consistency_status"], "supported")
        self.assertEqual(result["dependency_consistency_status"], "supported")
        self.assertEqual(result["turns"][0]["tool_replies"][0]["payload"]["notes"][0]["ts"], "SYNTHETIC older stored TEXT")

    def test_unrelated_save_and_recall_cannot_support_required_memory_case(self):
        self.choose("memory-note-recall")
        for turn in self.report["calls"]:
            for observed in turn["events"]:
                part = observed["content"]["parts"][0]
                if "function_call" in part:
                    part["function_call"]["args"]["incident_id"] = "INC-002"
                elif "saved" in part["function_response"]["response"]:
                    part["function_response"]["response"]["saved"]["incident_id"] = "INC-002"
                else:
                    part["function_response"]["response"]["notes"][0]["incident_id"] = "INC-002"
        self.rebuild()
        self.assertEqual(self.assess()["cross_turn_displayed_note_consistency"]["status"], "unknown")

    def test_assessment_does_not_mutate_input_or_share_output_payloads(self):
        before = deepcopy(self.report)
        result = self.assess()
        self.assertEqual(self.report, before)
        result["turns"][0]["tool_replies"][0]["payload"]["incident"]["summary"] = "MUTATED OUTPUT"
        self.assertEqual(self.report, before)

    def test_invalid_native_context_invocation_and_receipt_bindings_raise(self):
        for mutation in ("user", "session", "mixed_id", "reused_id", "receipt", "count", "flag", "event_id", "global", "per_call_order"):
            with self.subTest(mutation=mutation):
                self.choose("memory-note-recall")
                call = self.report["calls"][0]
                if mutation in {"user", "session"}:
                    call["inputs"]["user_id" if mutation == "user" else "session_id"] = "WRONG"
                elif mutation == "mixed_id":
                    call["events"][0]["invocation_id"] = "OTHER"
                    self.rebuild()
                elif mutation == "reused_id":
                    for observed in self.report["calls"][1]["events"]:
                        observed["invocation_id"] = "SYNTHETIC-NATIVE-INVOCATION-1"
                    self.rebuild()
                elif mutation == "receipt":
                    call["receipt"]["events"] = []
                elif mutation == "count":
                    call["receipt"]["events_seen"] = True
                elif mutation == "flag":
                    call["receipt"]["capture_complete"] = 1
                elif mutation == "event_id":
                    call["event_records"][0]["actual_event_id"] = "WRONG"
                elif mutation == "global":
                    call["event_records"][0]["global_yield_sequence"] = 2
                else:
                    call["event_records"][0]["global_yield_sequence"], call["event_records"][1]["global_yield_sequence"] = 2, 1
                with self.assertRaises(ValueError):
                    self.assess()

    def test_malformed_or_unknown_dependency_contracts_raise(self):
        for mutation in ("kind", "field", "bounds", "bool", "turn"):
            with self.subTest(mutation=mutation):
                obligation = deepcopy(self.by_name["recommend-fix"])
                dependency = obligation["turns"][0]["source_dependencies_extra_assessment"][0]
                if mutation == "kind":
                    dependency["kind"] = {}
                elif mutation == "field":
                    dependency["producer_reply_field"] = "invented.field"
                elif mutation == "bounds":
                    dependency["consumer_required_sequence"] = 99
                elif mutation == "bool":
                    dependency["producer_required_sequence"] = True
                else:
                    obligation["turns"][0]["turn_index"] = True
                with self.assertRaises(ValueError):
                    self.assess(obligation=obligation)

    def test_cross_turn_sequence_bool_substitutions_raise(self):
        self.choose("memory-note-recall")
        for key, value in (("producer_turn", True), ("producer_turn", 1.0), ("consumer_turn", 2.0)):
            with self.subTest(key=key, value=value):
                obligation = deepcopy(self.obligation)
                obligation["turns"][1]["source_dependencies_extra_assessment"][0][key] = value
                with self.assertRaises(ValueError):
                    self.assess(obligation=obligation)

    def test_nonfinite_and_foreign_function_part_forms_raise(self):
        for value in (float("nan"), float("inf"), object()):
            with self.subTest(value=type(value)):
                report = synthetic_journal(self.obligation)
                report["unsupported"] = value
                with self.assertRaises(ValueError):
                    self.assess(report)
        self.report["calls"][0]["events"][0]["content"]["parts"][0]["functionCall"] = {"name": "foreign"}
        self.rebuild()
        with self.assertRaises(ValueError):
            self.assess()


if __name__ == "__main__":
    unittest.main()
