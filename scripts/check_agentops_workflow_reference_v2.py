"""Constructed V2 binding/short-circuit controls; no App/SDK/provider execution."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

from agentops_workflow_fixture_v2 import PublicWorkflowFixture, compiled_node_map
from agentops_workflow_public_v1 import IDS, STAGES, TOOLS
from agentops_workflow_reference_v1 import INSTRUCTION_SHA256
from analyze_agentops_workflow_reference_v2 import BOUNDARY, analyze
from check_agentops_workflow_reference_v1 import constructed_case, jsonl, write, main as check_v1


def context(stage):
    return SimpleNamespace(agent_name=stage, invocation_id="constructed-invocation",
                           user_id="constructed-user", session=SimpleNamespace(id="constructed-session"))


def request(prompt, stage, responses=None, tools=None):
    contents = [SimpleNamespace(role="user", parts=[SimpleNamespace(text=prompt, function_response=None)])]
    for name, value in (responses or {}).items():
        part = SimpleNamespace(text=None, function_response=SimpleNamespace(name=name, response=value))
        contents.append(SimpleNamespace(role="user", parts=[part]))
    surface = dict.fromkeys(TOOLS[stage]) if tools is None else tools
    return SimpleNamespace(contents=contents, tools_dict=surface, model="preserved-original-backend",
                           model_dump=lambda **kwargs: {"model": "preserved-original-backend", "constructed": True})


def response(item, call_id):
    part = {"function_call": {"id": call_id, "name": item["name"], "args": item["args"]}} if "name" in item else {"text": item["text"]}
    value = {"content": {"role": "model", "parts": [part]}}
    return SimpleNamespace(model_dump=lambda **kwargs: value)


def bind_constructed_case(base, case_id):
    captured = constructed_case(base, case_id, resolved=case_id == IDS[1])
    case = base / case_id
    receipt = json.loads((case / "actor-receipt.json").read_bytes())
    receipt.update(schema_version="agentops-original-workflow-reference/2", fixture_boundary=BOUNDARY,
                   status="official_original_workflow_observed", constructed_evidence_only=True,
                   copied_data_unchanged_during_task=True, model_calls=len(captured["models"]),
                   raw_official_events=len(captured["events"]), tool_observations=len(captured["contexts"]),
                   private_evaluator_probe_denied=True, denied_capability_probes=[{"event": "private_evaluator_open"}],
                   socket_bootstrap={"status": "source_bound_cold_import_without_probe_socket",
                                     "observed_network_attempts_during_bootstrap": [], "socket_operation_permission_added": False,
                                     "helper_code_unchanged": True, "cold_import_before_App": True,
                                     "restored_socket_has_ipv6": True, "original_socket_has_ipv6": True},
                   original_app_identity={"compiled_graph_container": "list", "compiled_graph_node_names": ["__START__", *STAGES]},
                   fixture_callback_counts={stage: sum(row["stage"] == stage for row in captured["models"]) for stage in STAGES},
                   runtime_plugins=["original.AgentOpsPolicyPlugin", "owned.PublicWorkflowFixturePlugin", "owned.ObservationalPlugin"],
                   nodes=[{"name": stage, "compiled_node_is_distinct_exported_clone": True,
                           "compiled_model_matches_exported_original_model": True, "original_node_callbacks_unchanged": True,
                           "compiled_node_callbacks_unchanged": True, "compiled_instruction_sha256": digest,
                           "compiled_tools": list(TOOLS[stage]), "compiled_original_model_type": "constructed.OriginalModel",
                           "original_model_type": "constructed.OriginalModel", "original_model_identifier": "constructed-original-model",
                           "compiled_original_model_identifier": "constructed-original-model"} for stage, digest in zip(STAGES, INSTRUCTION_SHA256)])
    receipt["actual_identity"]["actual_sdk_invocation_id"] = "constructed-invocation"
    for row in captured["models"]:
        row.update(fixture_boundary=BOUNDARY, actual_callback_agent_name=row["stage"],
                   actual_callback_invocation_id="constructed-invocation", actual_callback_user_id="constructed-user",
                   actual_callback_session_id="constructed-session", actual_governed_request_model="constructed-original-model",
                   request={"model": "constructed-original-model"})
    for row in captured["events"]:
        row["event"]["invocation_id"] = "constructed-invocation"
    for row in captured["stages"]:
        if row["kind"] == "stage_entry":
            row.update(actual_agent_is_compiled_node=True, actual_agent_is_exported_node=False,
                       actual_original_model_type="constructed.OriginalModel", actual_original_model_identifier="constructed-original-model")
    write(case / "actor-receipt.json", receipt)
    jsonl(case / "model-journal.jsonl", captured["models"])
    jsonl(case / "stage-observations.jsonl", captured["stages"])
    jsonl(case / "adk-events.jsonl", captured["events"])
    jsonl(case / "audit-denials.jsonl", receipt["denied_capability_probes"])
    captured["receipt"] = receipt
    return captured


def main():
    check_v1()
    checks = []
    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)
    def rejects(call):
        try:
            call()
        except ValueError:
            return True
        return False
    list_nodes = [SimpleNamespace(name=name) for name in ("__START__", *STAGES)]
    mapped = compiled_node_map(list_nodes)
    check("actual_list_graph_resolves_each_compiled_stage_without_string_indexing", all(mapped[stage] is list_nodes[index + 1] for index, stage in enumerate(STAGES)))
    check("compiled_list_graph_must_retain_original_start_sentinel", rejects(lambda: compiled_node_map(list_nodes[1:])))
    check("duplicate_compiled_stage_names_are_rejected", rejects(lambda: compiled_node_map([*list_nodes, SimpleNamespace(name="plan")])))
    check("missing_compiled_stage_is_rejected", rejects(lambda: compiled_node_map(list_nodes[:-1])))
    check("unknown_compiled_graph_node_is_rejected", rejects(lambda: compiled_node_map([*list_nodes, SimpleNamespace(name="unreviewed-node")])))
    check("a_dictionary_cannot_replace_the_pinned_list_graph", rejects(lambda: compiled_node_map(mapped)))
    journal, recorded = [], []
    fixture = PublicWorkflowFixture(journal, recorded.append, lambda: "constructed-time")
    backend_calls = []
    def dispatch(policy_result, stage, req):
        # Constructed SDK first-non-None dispatch model, not execution of SDK.
        for callback in (lambda: policy_result, lambda: fixture.respond(context(stage), req, response)):
            value = callback()
            if value is not None:
                return value
        backend_calls.append("original-copied-backend")
        return None
    original_policy_response = object()
    check("original_policy_short_circuit_prevents_fixture_and_backend", dispatch(original_policy_response, "plan", request("Select most urgent unresolved.", "plan")) is original_policy_response and not journal and not backend_calls)
    first = dispatch(None, "plan", request("Select most urgent unresolved.", "plan"))
    check("actual_app_fixture_short_circuit_bypasses_unchanged_copied_backend", first is not None and len(journal) == 1 and not backend_calls and journal[0]["actual_governed_request_model"] == "preserved-original-backend")
    plan = first.model_dump()["content"]["parts"][0]["text"]
    second = fixture.respond(context("investigate"), request(plan, "investigate"), response)
    check("actual_callback_stage_and_actual_predecessor_select_tool", second.model_dump()["content"]["parts"][0]["function_call"]["name"] == "list_incidents" and journal[-1]["actual_callback_agent_name"] == "investigate")
    check("fixture_records_actual_governed_callback_identity", journal == recorded and journal[-1]["actual_callback_user_id"] == "constructed-user" and journal[-1]["actual_callback_session_id"] == "constructed-session" and journal[-1]["actual_callback_invocation_id"] == "constructed-invocation")
    unknown = SimpleNamespace(agent_name="forged-stage")
    check("unknown_actual_agent_cannot_be_replaced_by_exported_stage_hint", rejects(lambda: fixture.respond(unknown, request(plan, "investigate"), response)))
    limited = PublicWorkflowFixture([], lambda row: None, lambda: "constructed-time")
    check("actual_governed_tool_surface_must_contain_requested_tool", rejects(lambda: limited.respond(context("investigate"), request(plan, "investigate", tools={}), response)))
    for index in range(8):
        limited.respond(context("investigate"), request("malformed predecessor", "investigate"), response)
    check("ninth_actual_stage_callback_is_rejected", rejects(lambda: limited.respond(context("investigate"), request("malformed", "investigate"), response)))
    global_journal = []
    global_fixture = PublicWorkflowFixture(global_journal, lambda row: None, lambda: "constructed-time")
    for stage in STAGES[1:]:
        for index in range(8):
            global_fixture.respond(context(stage), request("malformed predecessor", stage), response)
    check("twenty_fifth_actual_callback_is_rejected_globally", len(global_journal) == 24 and rejects(lambda: global_fixture.respond(context("plan"), request("Select.", "plan"), response)))
    with tempfile.TemporaryDirectory(prefix="constructed-agentops-workflow-v2-") as allocated:
        base = Path(allocated)
        captures = {iid: bind_constructed_case(base, iid) for iid in IDS}
        check("constructed_v2_two_case_binding_and_raw_correspondence", analyze(base)["questions"] == 0)
        case, captured = base / IDS[0], captures[IDS[0]]
        changed = copy.deepcopy(captured["receipt"])
        changed["runtime_plugins"][0], changed["runtime_plugins"][1] = changed["runtime_plugins"][1], changed["runtime_plugins"][0]
        write(case / "actor-receipt.json", changed)
        check("fixture_before_original_policy_is_not_validated", analyze(base)["questions"] > 0)
        changed = copy.deepcopy(captured["receipt"])
        changed["nodes"][0]["compiled_model_is_exported_original_model"] = False
        write(case / "actor-receipt.json", changed)
        check("equal_compiled_model_values_do_not_require_same_object_identity", analyze(base)["questions"] == 0)
        changed["nodes"][1]["compiled_tools"] = ["restart_service"]
        write(case / "actor-receipt.json", changed)
        check("compiled_tool_surface_is_checked_against_frozen_original_names", analyze(base)["questions"] > 0)
        changed = copy.deepcopy(captured["receipt"])
        changed["nodes"][1]["compiled_instruction_sha256"] = "changed-instruction"
        write(case / "actor-receipt.json", changed)
        check("compiled_instruction_is_checked_against_frozen_source_hash", analyze(base)["questions"] > 0)
        changed = copy.deepcopy(captured["receipt"])
        changed["nodes"][1]["compiled_node_callbacks_unchanged"] = False
        write(case / "actor-receipt.json", changed)
        check("compiled_node_policy_callback_insertion_is_rejected", analyze(base)["questions"] > 0)
        changed = copy.deepcopy(captured["receipt"])
        changed["denied_capability_probes"] = [{"event": "socket.connect", "address": ["127.0.0.1", 11434]}]
        write(case / "actor-receipt.json", changed)
        check("denied_backend_connect_preserves_failed_binding", analyze(base)["questions"] > 0)
        write(case / "actor-receipt.json", captured["receipt"])
        changed = copy.deepcopy(captured["events"])
        changed[0]["event"]["error_code"] = "MODEL_UNAVAILABLE"
        jsonl(case / "adk-events.jsonl", changed)
        check("raw_model_error_cannot_pass_on_stage_presence", analyze(base)["questions"] > 0)
        jsonl(case / "adk-events.jsonl", captured["events"])
        changed = copy.deepcopy(captured["models"])
        changed[0]["actual_callback_agent_name"] = "investigate"
        jsonl(case / "model-journal.jsonl", changed)
        check("wrong_actual_stage_identity_is_not_validated", analyze(base)["questions"] > 0)
        jsonl(case / "model-journal.jsonl", captured["models"])
        changed = copy.deepcopy(captured["stages"])
        changed[0]["actual_agent_is_compiled_node"] = False
        jsonl(case / "stage-observations.jsonl", changed)
        check("exported_stage_observation_does_not_prove_compiled_runtime_binding", analyze(base)["questions"] > 0)
        changed = copy.deepcopy(captured["stages"])
        changed[0]["actual_original_model_identifier"] = "replaced-model"
        jsonl(case / "stage-observations.jsonl", changed)
        check("actual_executing_model_identifier_must_match_preserved_compiled_node", analyze(base)["questions"] > 0)
        jsonl(case / "stage-observations.jsonl", captured["stages"])
        changed = copy.deepcopy(captured["events"])
        changed = [row for row in changed if not any("function_response" in part for part in row["event"].get("content", {}).get("parts", []))]
        jsonl(case / "adk-events.jsonl", changed)
        check("fixture_output_and_stage_presence_do_not_replace_raw_tool_terminals", analyze(base)["questions"] > 0)
    check("controls_import_no_original_application_or_official_SDK", not any(name == "agent" or name.startswith(("agent.", "google.adk")) for name in sys.modules))
    print(json.dumps({"status": "constructed_v2_binding_controls_passed", "v2_checks": len(checks), "v1_checks_also_run": 18,
                      "total_constructed_checks": len(checks) + 18, "checks": checks, "SDK_or_application_imported": False, "provider_calls": 0}))


if __name__ == "__main__":
    main()
