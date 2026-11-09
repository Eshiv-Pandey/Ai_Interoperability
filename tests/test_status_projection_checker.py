"""Authored checker controls, including explicitly labelled wire derivatives.

These tests do not import the status projector or its extraction/graph logic.
Their claims are stated independently. Raw MCP envelopes here are constructed
controls, never assertions that a new R4 bridge capture has already occurred.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import unittest

from interoperability.oracle import evaluate
from interoperability.status_projection_checker import check_status_native_sidecar, check_status_projection


AMIR, MG = "amirk_a2a_to_mcp", "mgcrea_mcp_a2a"
PINS = {AMIR: "58eff9da469bccdc432bf164662727947de646b4", MG: "c4d9d3c57c1746abbf9f6aadd3a9912d464eb1f5"}
NAMESPACE = {AMIR: "bridge-handle", MG: "public-native-a2a-id"}
GOAL = [{"field": "status", "op": "eq", "value": "completed"},
        {"field": "returned_task_reference", "op": "eq_field", "other_field": "required_task_reference"},
        {"field": "returned_context_reference", "op": "eq_field", "other_field": "required_context_reference"}]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def stamp(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat().replace("+00:00", "Z")


def body(value, seconds, reply=False):
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n"
    return {"raw": raw, "json": value, "sha256": hashlib.sha256(raw.encode()).hexdigest(),
            "observed_at_utc" if reply else "started_at_utc": stamp(seconds)}


def exchange(index, operation, arguments, result):
    method = operation if operation.startswith("tasks/") else "tools/call"
    params = arguments if method.startswith("tasks/") else {"name": operation, "arguments": arguments}
    return {"exchange_id": "mcp-" + str(index), "phase": "authored-status-checker-control",
            "request": body({"jsonrpc": "2.0", "id": index, "method": method, "params": params}, 100 + index),
            "response": body({"jsonrpc": "2.0", "id": index, "result": result}, 100.5 + index, True), "elapsed_ms": 500}


def tool(payload):
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


def trace(route, exchanges):
    version = "2026-07-28" if route == AMIR else "2025-11-25"
    method = "server/discover" if route == AMIR else "initialize"
    request = {"jsonrpc": "2.0", "id": "profile", "method": method,
               "params": {} if route == AMIR else {"protocolVersion": version, "capabilities": {}}}
    response = {"jsonrpc": "2.0", "id": "profile", "result": {"supportedVersions": [version]} if route == AMIR else {"protocolVersion": version}}
    setup = [{"exchange_id": "profile", "request": body(request, 99), "response": body(response, 99.5, True), "elapsed_ms": 500}]
    if route == MG:
        setup.append({"exchange_id": "initialized", "request": body({"jsonrpc": "2.0", "method": "notifications/initialized"}, 100), "response": None})
    else:
        capabilities = {"extensions": {"io.modelcontextprotocol/tasks": {}}} if any(e["request"]["json"]["method"].startswith("tasks/") for e in exchanges) else {}
        for entry in setup + exchanges:
            message = entry["request"]["json"]
            message.setdefault("params", {})["_meta"] = {"io.modelcontextprotocol/protocolVersion": version, "io.modelcontextprotocol/clientCapabilities": capabilities}
            seconds = datetime.fromisoformat(entry["request"]["started_at_utc"].replace("Z", "+00:00")).timestamp()
            entry["request"] = body(message, seconds)
            entry["request"]["headers"] = {"MCP-Protocol-Version": version, "Mcp-Method": message["method"]}
            if message["method"] == "tools/call":
                entry["request"]["headers"]["Mcp-Name"] = message["params"]["name"]
            elif message["method"].startswith("tasks/"):
                entry["request"]["headers"]["Mcp-Name"] = message["params"]["taskId"]
    return {"schema_version": "runtime-wire-observation/1", "run_id": "authored-status-" + route,
            "route_id": route, "source_commit": PINS[route], "outcome": "recorded", "exit_code": 0,
            "protocol": {"mcp": "2026-07-28" if route == AMIR else "2025-11-25"},
            "provenance": {"kind": "authored-unit-control", "label": "Constructed status checker fixture; no new bridge capture"},
            "exchanges": setup + exchanges}


def fields(route, *, task="task-A", context="context-A", **literal):
    result = {"task_namespace": NAMESPACE[route], "required_task_reference": task,
              "required_context_reference": context, "request_target_valid": True}
    result.update(literal)
    return result


def claim(source, values, operations, evidence_sources, indices=None):
    """Bind independently stated claims; never extracts response field paths."""
    if indices is None:
        indices = [i for i, e in enumerate(source["exchanges"]) if e["request"]["json"]["method"].startswith("tasks/") or e["request"]["json"].get("params", {}).get("name") in {"a2a_send_message", "a2a_get_task", "a2a_request"}]
    elif source["provenance"].get("kind") == "authored-unit-control":
        indices = [i + (1 if source["route_id"] == AMIR else 2) for i in indices]
    exchanges = [source["exchanges"][i] for i in indices]
    run, route = source["run_id"], source["route_id"]
    source_hash = digest(source)
    clock = math.ceil(max(datetime.fromisoformat(e["response"]["observed_at_utc"].replace("Z", "+00:00")).timestamp()
                          for e in source["exchanges"] if e["response"] is not None))
    ids = [run + "::" + e["exchange_id"] for e in exchanges]
    events = [{"state_id": ids[i], "exchange_id": e["exchange_id"], "request_method": e["request"]["json"]["method"],
               "operation": operations[i], "response_sha256": e["response"]["sha256"],
               "evidence_source": evidence_sources[i], "observable_fields": values[i]} for i, e in enumerate(exchanges)]
    return {"schema_version": "observed-status-trace-projection/1", "source_trace_sha256": source_hash,
            "config": {"goal": "logical-completion-and-original-association"}, "analysis_clock": clock,
            "initial_exchange_id": exchanges[0]["exchange_id"], "events": events,
            "manifest": {"schema_version": "finite-continuation/1", "id": run + ":historical-status",
                         "route": route + " historical status observation",
                         "provenance": {"kind": "wire-derived", "source": "runtime-wire-observation/1:" + source_hash,
                                        "review_status": "AI-authored status projection; human review pending"},
                         "horizon": len(ids) - 1, "evidence": {"complete": False, "observed_at": clock, "valid_until": clock},
                         "initial": ids[0], "states": dict(zip(ids, values)),
                         "transitions": [{"id": "edge:" + exchanges[i]["exchange_id"], "source": ids[i - 1], "target": ids[i], "operation": operations[i]} for i in range(1, len(ids))],
                         "runtime_contract": {"goal": copy.deepcopy(GOAL), "invariants": [{"field": "request_target_valid", "op": "eq", "value": True},
                             {"field": "task_namespace", "op": "eq", "value": NAMESPACE[route]}]}}}


def refresh(source, projection):
    projection["source_trace_sha256"] = digest(source)
    projection["manifest"]["provenance"]["source"] = "runtime-wire-observation/1:" + digest(source)
    by_id = {e["exchange_id"]: e for e in source["exchanges"]}
    for event in projection["events"]:
        event["response_sha256"] = by_id[event["exchange_id"]]["response"]["sha256"]


def replace_result(source, index, result):
    item = next(e for e in source["exchanges"] if e["exchange_id"] == "mcp-" + str(index + 1))
    item["response"] = body({"jsonrpc": "2.0", "id": index + 1, "result": result}, 101.5 + index, True)


def mg_control(final="completed", raw=False):
    pending = {"id": "task-A", "context_id": "context-A", "state": "input_required"}
    exchanges = [exchange(1, "a2a_send_message", {"text": "shuffle"}, tool({"task": pending})),
                 exchange(2, "a2a_get_task", {"task_id": "task-A", "refresh": True}, tool(pending))]
    values = [fields(MG, returned_task_reference="task-A", returned_context_reference="context-A", status="input_required") for _ in range(2)]
    operations, sources = ["a2a_send_message", "a2a_get_task"], ["send-acknowledgement", "peer-refreshed"]
    if raw:
        native = {"id": "task-A", "contextId": "context-A", "status": {"state": "TASK_STATE_" + final.upper()}}
        exchanges.extend([exchange(3, "a2a_request", {"method": "SendMessage", "params": {"message": {"taskId": "task-A", "contextId": "context-A", "referenceTaskIds": ["task-A"], "parts": [{"text": "Well done!"}]}}}, tool({"jsonrpc": "2.0", "id": "native-3", "result": {"task": native}})),
                          exchange(4, "a2a_request", {"method": "GetTask", "params": {"id": "task-A", "historyLength": 10}}, tool({"jsonrpc": "2.0", "id": "native-4", "result": native}))])
        operations.extend(["a2a_request/SendMessage", "a2a_request/GetTask"])
    else:
        exchanges.extend([exchange(3, "a2a_send_message", {"task_id": "task-A", "context_id": "context-A", "text": "Well done!"}, tool({"task": pending})),
                          exchange(4, "a2a_get_task", {"task_id": "task-A", "refresh": True}, tool({"id": "task-A", "context_id": "context-A", "state": final}))])
        operations.extend(["a2a_send_message", "a2a_get_task"])
    values.extend([fields(MG, returned_task_reference="task-A", returned_context_reference="context-A", status=final if raw else "input_required"),
                   fields(MG, returned_task_reference="task-A", returned_context_reference="context-A", status=final)])
    sources.extend(["send-acknowledgement", "peer-refreshed"])
    source = trace(MG, exchanges)
    return source, claim(source, values, operations, sources)


def amir_control():
    pending = {"kind": "task", "taskHandle": "task-A", "contextHandle": "context-A", "status": "input_required", "a2aState": "TASK_STATE_INPUT_REQUIRED"}
    final = {"kind": "task", "taskHandle": "task-A", "contextHandle": "context-A", "status": "completed", "a2aState": "TASK_STATE_COMPLETED"}
    exchanges = [exchange(1, "a2a_send_message", {"text": "shuffle"}, {"taskId": "task-A", "status": "input_required"}),
                 exchange(2, "a2a_get_task", {"taskHandle": "task-A"}, {"structuredContent": pending, "content": []}),
                 exchange(3, "tasks/get", {"taskId": "task-A"}, {"taskId": "task-A", "status": "input_required", "inputRequests": {"answer": {}}}),
                 exchange(4, "tasks/update", {"taskId": "task-A", "inputResponses": {"answer": {"action": "accept", "content": {"answer": "Well done!"}}}}, {"resultType": "complete"}),
                 exchange(5, "tasks/get", {"taskId": "task-A"}, {"taskId": "task-A", "status": "completed", "result": {"structuredContent": final, "content": []}})]
    values = [fields(AMIR, returned_task_reference="task-A", returned_context_reference="context-A", status="input_required"),
              fields(AMIR, returned_task_reference="task-A", status="input_required"), fields(AMIR),
              fields(AMIR, returned_task_reference="task-A", returned_context_reference="context-A", status="completed")]
    source = trace(AMIR, exchanges)
    return source, claim(source, values, ["a2a_get_task", "tasks/get", "tasks/update", "tasks/get"], ["peer-refreshed", "extension-observation", "extension-observation", "extension-observation"], [1, 2, 3, 4])


class StatusProjectionCheckerTests(unittest.TestCase):
    def test_variant_route_consistency_and_each_request_tasks_declaration(self):
        source, projection = amir_control()
        source["variant_id"] = "R2"
        refresh(source, projection)
        self.assertTrue(check_status_projection(source, projection))
        for index in (0, 1, len(source["exchanges"]) - 1):
            changed = copy.deepcopy(source)
            entry = changed["exchanges"][index]
            request = entry["request"]["json"]
            request["params"]["_meta"]["io.modelcontextprotocol/clientCapabilities"] = {}
            seconds = datetime.fromisoformat(entry["request"]["started_at_utc"].replace("Z", "+00:00")).timestamp()
            old_headers = entry["request"]["headers"]
            entry["request"] = body(request, seconds)
            entry["request"]["headers"] = old_headers
            refresh(changed, projection)
            self.assertFalse(check_status_projection(changed, projection))
        pending = {"kind": "task", "taskHandle": "task-A", "contextHandle": "context-A", "status": "completed"}
        source = trace(AMIR, [exchange(1, "a2a_send_message", {"text": "R1 ordinary"}, {"structuredContent": pending})])
        source["variant_id"] = "R1"
        projection = claim(source, [fields(AMIR, returned_task_reference="task-A", returned_context_reference="context-A", status="completed")], ["a2a_send_message"], ["send-acknowledgement"])
        self.assertTrue(check_status_projection(source, projection))
        entry = source["exchanges"][0]
        request = entry["request"]["json"]
        request["params"]["_meta"]["io.modelcontextprotocol/clientCapabilities"] = {"extensions": {"io.modelcontextprotocol/tasks": {}}}
        headers = entry["request"]["headers"]
        entry["request"] = body(request, 99)
        entry["request"]["headers"] = headers
        refresh(source, projection)
        self.assertFalse(check_status_projection(source, projection))
        for variant in ("R1", "R2", "unknown", None):
            source, projection = mg_control()
            source["variant_id"] = variant
            refresh(source, projection)
            self.assertFalse(check_status_projection(source, projection), variant)

    def test_http_names_case_insensitivity_and_duplicate_header_rejection(self):
        source, projection = amir_control()
        for entry in source["exchanges"]:
            entry["request"]["headers"] = {key.swapcase(): value for key, value in entry["request"]["headers"].items()}
        refresh(source, projection)
        self.assertTrue(check_status_projection(source, projection))
        for index in (1, len(source["exchanges"]) - 1):
            changed = copy.deepcopy(source)
            headers = changed["exchanges"][index]["request"]["headers"]
            headers["mCP-nAME"] = "wrong-body-operation-or-target"
            refresh(changed, projection)
            self.assertFalse(check_status_projection(changed, projection))
        source, projection = amir_control()
        source["exchanges"][0]["request"]["headers"]["mcp-protocol-version"] = "2026-07-28"
        refresh(source, projection)
        self.assertFalse(check_status_projection(source, projection))

    def test_setup_rpc_errors_missing_result_and_tool_errors_rejected(self):
        for mutation in ("rpc-error", "missing", "null", "tool-error", "http-error"):
            source, projection = mg_control()
            entry = {"exchange_id": "tools-list", "request": body({"jsonrpc": "2.0", "id": "tools-list", "method": "tools/list", "params": {}}, 100.1),
                     "response": body({"jsonrpc": "2.0", "id": "tools-list", "result": {"tools": []}}, 100.2, True)}
            source["exchanges"].insert(2, entry)
            refresh(source, projection)
            self.assertTrue(check_status_projection(source, projection))
            response = entry["response"]["json"]
            if mutation == "rpc-error":
                del response["result"]
                response["error"] = {"code": -32601, "message": "missing setup operation"}
            elif mutation == "missing":
                del response["result"]
            elif mutation == "null":
                response["result"] = None
            elif mutation == "tool-error":
                response["result"]["isError"] = True
            entry["response"] = body(response, 100.2, True)
            if mutation == "http-error":
                entry["response"]["status"] = 500
            refresh(source, projection)
            self.assertFalse(check_status_projection(source, projection), mutation)

    def test_unknown_setup_operations_cannot_disappear_before_prefix(self):
        for method, params in (("arbitrary/setup", {}), ("tools/call", {"name": "unknown_tool", "arguments": {}}),
                               ("tools/call", {"name": "a2a_list_tasks", "arguments": {}})):
            source, projection = mg_control()
            entry = {"exchange_id": "unmodelled-setup", "request": body({"jsonrpc": "2.0", "id": "unmodelled", "method": method, "params": params}, 98),
                     "response": body({"jsonrpc": "2.0", "id": "unmodelled", "result": {}}, 98.5, True)}
            source["exchanges"].insert(0, entry)
            refresh(source, projection)
            self.assertFalse(check_status_projection(source, projection), method)

    def test_route_specific_setup_is_actual_wire_evidence(self):
        for route, mutation in ((MG, "initialize"), (MG, "notification"), (MG, "version"),
                                (AMIR, "discovery"), (AMIR, "version"), (AMIR, "header"), (AMIR, "capabilities")):
            source, projection = amir_control() if route == AMIR else mg_control()
            if mutation in {"initialize", "discovery"}:
                source["exchanges"].pop(0)
            elif mutation == "notification":
                source["exchanges"].pop(1)
            elif mutation == "version":
                first = source["exchanges"][0]
                result = first["response"]["json"]
                if route == MG:
                    result["result"]["protocolVersion"] = "2026-07-28"
                else:
                    result["result"]["supportedVersions"] = ["2025-11-25"]
                first["response"] = body(result, 99.5, True)
            elif mutation == "header":
                source["exchanges"][-1]["request"]["headers"]["MCP-Protocol-Version"] = "2025-11-25"
            else:
                last = source["exchanges"][-1]
                request = last["request"]["json"]
                request["params"]["_meta"]["io.modelcontextprotocol/clientCapabilities"] = {}
                last["request"] = body(request, 105)
                last["request"]["headers"] = {"MCP-Protocol-Version": "2026-07-28", "Mcp-Method": "tasks/get", "Mcp-Name": "task-A"}
            refresh(source, projection)
            self.assertFalse(check_status_projection(source, projection), (route, mutation))

    def test_conflicting_earlier_creation_handle_rejects_multi_task_prefix(self):
        source, projection = amir_control()
        replace_result(source, 0, {"taskId": "different-task", "status": "input_required"})
        refresh(source, projection)
        self.assertFalse(check_status_projection(source, projection))

    def test_protocol_version_and_unmodelled_later_read_rejected(self):
        source, projection = mg_control()
        source["protocol"]["mcp"] = "2026-07-28"
        refresh(source, projection)
        self.assertFalse(check_status_projection(source, projection))
        source, projection = mg_control()
        source["exchanges"].append(exchange(5, "a2a_list_tasks", {}, {}))
        refresh(source, projection)
        self.assertFalse(check_status_projection(source, projection))

    def test_zero_transition_completion_and_input_immutability(self):
        pending = {"id": "task-A", "context_id": "context-A", "state": "completed"}
        source = trace(MG, [exchange(1, "a2a_send_message", {"text": "already complete"}, tool({"task": pending}))])
        projection = claim(source, [fields(MG, returned_task_reference="task-A", returned_context_reference="context-A", status="completed")], ["a2a_send_message"], ["send-acknowledgement"])
        before = copy.deepcopy((source, projection))
        self.assertTrue(check_status_projection(source, projection))
        self.assertEqual((source, projection), before)
        result = evaluate(projection["manifest"], projection["analysis_clock"])
        self.assertEqual(result["decision"], "supported")
        self.assertEqual(result["certificate"]["transition_ids"], [])

    def test_nested_task_binding_and_ordinary_status_contradiction_rejected(self):
        source, projection = amir_control()
        payload = source["exchanges"][-1]["response"]["json"]["result"]
        payload["result"]["structuredContent"]["taskHandle"] = "other-task"
        replace_result(source, 4, payload)
        refresh(source, projection)
        self.assertFalse(check_status_projection(source, projection))
        source, projection = amir_control()
        payload = source["exchanges"][-1]["response"]["json"]["result"]
        payload["result"]["structuredContent"]["status"] = "input_required"
        replace_result(source, 4, payload)
        refresh(source, projection)
        self.assertFalse(check_status_projection(source, projection))

    def test_typed_completion_has_exactly_three_predicates_and_no_artifact(self):
        source, projection = mg_control()
        self.assertTrue(check_status_projection(source, projection))
        self.assertEqual(projection["manifest"]["runtime_contract"]["goal"], GOAL)
        self.assertEqual(evaluate(projection["manifest"], projection["analysis_clock"])["decision"], "supported")
        self.assertNotIn("artifact", json.dumps(projection))

    def test_waiting_is_unknown_and_later_clock_abstains(self):
        source, projection = mg_control("input_required")
        self.assertTrue(check_status_projection(source, projection))
        for clock in (projection["analysis_clock"], projection["analysis_clock"] + 1):
            result = evaluate(projection["manifest"], clock)
            self.assertEqual(result["decision"], "unknown")
            self.assertIsNone(result["certificate"])

    def test_raw_send_and_get_have_different_native_result_paths(self):
        source, projection = mg_control(raw=True)
        self.assertTrue(check_status_projection(source, projection))
        self.assertEqual(evaluate(projection["manifest"], projection["analysis_clock"])["decision"], "supported")

    def test_tasks_delivery_and_ack_are_not_logical_completion(self):
        source, projection = amir_control()
        self.assertTrue(check_status_projection(source, projection))
        self.assertEqual(projection["initial_exchange_id"], "mcp-2")
        self.assertNotIn("status", projection["events"][2]["observable_fields"])
        replace_result(source, 4, {"taskId": "task-A", "status": "completed"})
        final = projection["events"][-1]["observable_fields"]
        del final["status"]
        del final["returned_context_reference"]
        refresh(source, projection)
        self.assertTrue(check_status_projection(source, projection))
        self.assertEqual(evaluate(projection["manifest"], projection["analysis_clock"])["decision"], "unknown")

    def test_sole_a2a_state_does_not_invent_missing_status(self):
        source, projection = amir_control()
        last = {"kind": "task", "taskHandle": "task-A", "contextHandle": "context-A", "a2aState": "TASK_STATE_COMPLETED"}
        replace_result(source, 4, {"taskId": "task-A", "status": "completed", "result": {"structuredContent": last}})
        del projection["events"][-1]["observable_fields"]["status"]
        refresh(source, projection)
        self.assertTrue(check_status_projection(source, projection))

    def test_missing_context_is_unknown_not_request_filled(self):
        source, projection = mg_control()
        replace_result(source, 3, tool({"id": "task-A", "state": "completed"}))
        del projection["events"][-1]["observable_fields"]["returned_context_reference"]
        refresh(source, projection)
        self.assertTrue(check_status_projection(source, projection))
        self.assertEqual(evaluate(projection["manifest"], projection["analysis_clock"])["decision"], "unknown")
        projection["events"][-1]["observable_fields"]["returned_context_reference"] = "context-A"
        self.assertFalse(check_status_projection(source, projection))

    def test_known_scalars_are_retained(self):
        for value in (None, "", False, 0):
            source, projection = mg_control()
            replace_result(source, 3, tool({"id": "task-A", "context_id": value, "state": "completed"}))
            projection["events"][-1]["observable_fields"]["returned_context_reference"] = value
            refresh(source, projection)
            self.assertTrue(check_status_projection(source, projection))

    def test_raw_null_and_missing_state_are_known_and_unknown(self):
        for state in (None, "absent"):
            source, projection = mg_control(raw=True)
            task = {"id": "task-A", "contextId": "context-A", "status": {} if state == "absent" else {"state": state}}
            replace_result(source, 3, tool({"jsonrpc": "2.0", "id": "native-4", "result": task}))
            final = projection["events"][-1]["observable_fields"]
            if state == "absent":
                del final["status"]
            else:
                final["status"] = None
            refresh(source, projection)
            self.assertTrue(check_status_projection(source, projection))

    def test_raw_inner_error_is_rejected_even_outer_ok(self):
        source, projection = mg_control(raw=True)
        replace_result(source, 2, tool({"jsonrpc": "2.0", "id": "native-3", "error": {"code": -32001, "message": "gone"}}))
        refresh(source, projection)
        self.assertFalse(check_status_projection(source, projection))

    def test_raw_inner_id_reuse_rejected(self):
        source, projection = mg_control(raw=True)
        payload = json.loads(source["exchanges"][-1]["response"]["json"]["result"]["content"][0]["text"])
        payload["id"] = "native-3"
        replace_result(source, 3, tool(payload))
        refresh(source, projection)
        self.assertFalse(check_status_projection(source, projection))

    def test_unmodelled_mutation_cancel_and_decline_rejected(self):
        for operation, arguments in [("a2a_cancel_task", {"task_id": "task-A"}), ("a2a_respond_to_task", {}),
                                     ("a2a_request", {"method": "CancelTask", "params": {"id": "task-A"}}),
                                     ("tasks/cancel", {"taskId": "task-A"})]:
            source, projection = mg_control()
            source["exchanges"].append(exchange(5, operation, arguments, {}))
            refresh(source, projection)
            self.assertFalse(check_status_projection(source, projection), operation)
        source, projection = amir_control()
        request = source["exchanges"][4]["request"]["json"]
        request["params"]["inputResponses"]["answer"]["action"] = "decline"
        source["exchanges"][4]["request"] = body(request, 104)
        source["exchanges"][4]["request"]["headers"] = {"MCP-Protocol-Version": "2026-07-28", "Mcp-Method": "tasks/update", "Mcp-Name": "task-A"}
        refresh(source, projection)
        self.assertFalse(check_status_projection(source, projection))

    def test_unknown_and_numeric_native_states_rejected(self):
        for state in ("TASK_STATE_MAGIC", 4, False, {"state": "completed"}):
            source, projection = mg_control(raw=True)
            replace_result(source, 3, tool({"jsonrpc": "2.0", "id": "native-4", "result": {"id": "task-A", "contextId": "context-A", "status": {"state": state}}}))
            refresh(source, projection)
            self.assertFalse(check_status_projection(source, projection))

    def test_public_reference_and_target_mutation_remain_literal(self):
        source, projection = mg_control()
        replace_result(source, 3, tool({"id": "other-task", "context_id": "context-A", "state": "completed"}))
        projection["events"][-1]["observable_fields"]["returned_task_reference"] = "other-task"
        refresh(source, projection)
        self.assertTrue(check_status_projection(source, projection))
        self.assertEqual(evaluate(projection["manifest"], projection["analysis_clock"])["decision"], "unknown")
        request = source["exchanges"][-1]["request"]["json"]
        request["params"]["arguments"]["task_id"] = "other-task"
        source["exchanges"][-1]["request"] = body(request, 104)
        projection["events"][-1]["observable_fields"]["request_target_valid"] = False
        refresh(source, projection)
        self.assertTrue(check_status_projection(source, projection))

    def test_graph_contract_clock_and_namespace_tampering_rejected(self):
        mutations = [lambda p: p["manifest"]["evidence"].update(complete=True), lambda p: p["manifest"]["evidence"].update(valid_until=999),
                     lambda p: p["manifest"]["runtime_contract"]["goal"].append({"field": "artifact", "op": "eq", "value": True}),
                     lambda p: p["manifest"]["transitions"].pop(), lambda p: p["events"].pop(1),
                     lambda p: p["events"][-1]["observable_fields"].update(task_namespace="bridge-handle"),
                     lambda p: p.update(analysis_clock=True), lambda p: p["config"].update(extra=True),
                     lambda p: p["events"][-1].update(private_native_id="secret"), lambda p: p["manifest"].update(extra=True)]
        for mutate in mutations:
            source, projection = mg_control()
            mutate(projection)
            self.assertFalse(check_status_projection(source, projection))

    def test_whole_wire_raw_hash_duplicate_ids_and_overlap(self):
        for mutation in ("raw", "parsed", "hash", "duplicate-key", "request-id", "exchange-id", "overlap", "utf8", "nonfinite", "non-scalar"):
            source, projection = mg_control()
            last = source["exchanges"][-1]
            if mutation == "raw":
                last["response"]["raw"] += " "
            elif mutation == "parsed":
                last["response"]["json"]["id"] = 99
            elif mutation == "hash":
                last["response"]["sha256"] = "0" * 64
            elif mutation in ("duplicate-key", "nonfinite", "utf8"):
                raw = '{"jsonrpc":"2.0","id":4,"id":4,"result":{}}' if mutation == "duplicate-key" else ('{"x":NaN}' if mutation == "nonfinite" else '\ud800')
                last["response"]["raw"] = raw
                last["response"]["sha256"] = hashlib.sha256(raw.encode(errors="surrogatepass")).hexdigest()
            elif mutation == "request-id":
                request = last["request"]["json"]
                request["id"] = 1
                last["request"] = body(request, 104)
            elif mutation == "exchange-id":
                last["exchange_id"] = "mcp-1"
            elif mutation == "overlap":
                last["request"]["started_at_utc"] = stamp(103.2)
            elif mutation == "non-scalar":
                replace_result(source, 3, tool({"id": "task-A", "context_id": [], "state": "completed"}))
            self.assertFalse(check_status_projection(source, projection), mutation)

    def test_missing_reply_and_nested_error_rejected(self):
        source, projection = mg_control()
        source["exchanges"][-1]["response"] = None
        self.assertFalse(check_status_projection(source, projection))
        source, projection = amir_control()
        replace_result(source, 4, {"taskId": "task-A", "status": "completed", "result": {"isError": True}})
        refresh(source, projection)
        self.assertFalse(check_status_projection(source, projection))

    def test_setup_corruption_and_declared_sse_body(self):
        source, projection = mg_control()
        setup = exchange(5, "ping", {}, {})
        setup["request"] = body({"jsonrpc": "2.0", "id": 5, "method": "ping", "params": {}}, 105)
        source["exchanges"].append(setup)
        # Setup must also be included in the archival clock and trace hash.
        projection["analysis_clock"] = 106
        projection["manifest"]["evidence"].update(observed_at=106, valid_until=106)
        refresh(source, projection)
        self.assertTrue(check_status_projection(source, projection))
        setup["response"]["sha256"] = "0" * 64
        refresh(source, projection)
        self.assertFalse(check_status_projection(source, projection))
        source, projection = amir_control()
        response = source["exchanges"][-1]["response"]
        response["raw"] = "event: message\ndata: " + json.dumps(response["json"]) + "\n\n"
        response["headers"] = {"content-type": "text/event-stream"}
        response["sha256"] = hashlib.sha256(response["raw"].encode()).hexdigest()
        refresh(source, projection)
        self.assertTrue(check_status_projection(source, projection))


def native_records(source, raw=False, amir=False, modern=True):
    route = source["route_id"]
    records = [{"schema_version": "private-native-http/1", "run_id": source["run_id"], "route_id": route, "pid": 42}]
    for i, exchange_record in enumerate(source["exchanges"]):
        request = exchange_record["request"]["json"]
        if request["method"] in {"initialize", "server/discover", "notifications/initialized"}:
            continue
        operation = request["params"].get("name", request["method"])
        args = request["params"].get("arguments", {})
        method = "GetTask" if operation == "a2a_get_task" else "SendMessage"
        if operation == "a2a_request":
            method, params = args["method"], args["params"]
            result = json.loads(exchange_record["response"]["json"]["result"]["content"][0]["text"])
            native_id = result["id"]
        else:
            native_id = "native-" + str(request["id"])
            params = {"id": "native-task" if amir else "task-A"} if method == "GetTask" else {"message": {"parts": [{"text": args["text"]}]}}
            if request["id"] != 1 and method == "SendMessage":
                params["message"].update(taskId="native-task" if amir else "task-A", contextId="native-context" if amir else "context-A")
            final = i == len(source["exchanges"]) - 1
            task = {"id": "native-task" if amir else "task-A", "contextId": "native-context" if amir else "context-A", "status": {"state": "TASK_STATE_COMPLETED" if final else "TASK_STATE_INPUT_REQUIRED"}}
            result = {"jsonrpc": "2.0", "id": native_id, "result": task if method == "GetTask" else {"task": task}}
        seconds = datetime.fromisoformat(exchange_record["request"]["started_at_utc"].replace("Z", "+00:00")).timestamp()
        first = body({"jsonrpc": "2.0", "id": native_id, "method": method, "params": params}, seconds + .1)
        first.update(url="http://localhost/a2a", method="POST", headers={"a2a-version": "1.0"})
        last = body(result, seconds + .2, True)
        last.update(status=200, headers={"content-type": "application/json"})
        record = {"exchange_id": "http-" + str(request["id"]), "role": "native_peer_response", "request": first, "response": last}
        if modern:
            records.append({"type": "request-started", **record, "response": None})
            records.append({"type": "exchange-completed", **record})
        else:
            records.append(record)
    return records


class NativeStatusCheckerTests(unittest.TestCase):
    def test_amir_opaque_handles_are_distinct_from_private_native_ids(self):
        pending = {"kind": "task", "taskHandle": "task-A", "contextHandle": "context-A", "status": "input_required"}
        final = {"kind": "task", "taskHandle": "task-A", "contextHandle": "context-A", "status": "completed"}
        source = trace(AMIR, [exchange(1, "a2a_send_message", {"text": "shuffle"}, {"structuredContent": pending}),
                              exchange(2, "a2a_get_task", {"taskHandle": "task-A"}, {"structuredContent": pending}),
                              exchange(3, "a2a_send_message", {"text": "Well done!", "taskHandle": "task-A", "contextHandle": "context-A"}, {"structuredContent": pending}),
                              exchange(4, "a2a_get_task", {"taskHandle": "task-A"}, {"structuredContent": final})])
        records = native_records(source, amir=True)
        self.assertTrue(check_status_native_sidecar(source, records))
        self.assertNotIn("native-task", json.dumps(source))
        last = records[-1]
        result = last["response"]["json"]
        result["result"]["id"] = "different-private-task"
        last["response"] = body(result, 104.2, True)
        last["response"].update(status=200)
        self.assertFalse(check_status_native_sidecar(source, records))

    def test_private_native_typed_ids_and_status(self):
        source, _ = mg_control()
        records = native_records(source)
        self.assertTrue(check_status_native_sidecar(source, records))
        self.assertTrue(check_status_native_sidecar(source, native_records(source, modern=False)))

    def test_raw_native_inner_correlations_and_actual_target(self):
        source, _ = mg_control(raw=True)
        records = native_records(source, raw=True)
        self.assertTrue(check_status_native_sidecar(source, records))
        records[-1]["request"]["json"]["params"]["id"] = "private-only-other-task"
        self.assertFalse(check_status_native_sidecar(source, records))

    def test_missing_native_get_status_mismatch_and_hash_fail(self):
        for mutation in ("missing", "state", "hash", "id", "time", "unpaired"):
            source, _ = mg_control()
            records = native_records(source)
            last = records[-1]
            if mutation == "missing":
                records = records[:-2]
            elif mutation == "state":
                result = last["response"]["json"]
                result["result"]["status"]["state"] = "TASK_STATE_INPUT_REQUIRED"
                last["response"] = body(result, 104.2, True)
                last["response"].update(status=200)
            elif mutation == "hash":
                last["response"]["sha256"] = "0" * 64
            elif mutation == "id":
                result = last["response"]["json"]
                result["id"] = "other-native-id"
                last["response"] = body(result, 104.2, True)
                last["response"].update(status=200)
            elif mutation == "time":
                last["request"]["started_at_utc"] = stamp(999)
            else:
                records.pop()
            self.assertFalse(check_status_native_sidecar(source, records), mutation)

    def test_raw_absent_header_uses_captured_card_version(self):
        source, _ = mg_control(raw=True)
        records = native_records(source)
        card = {"supportedInterfaces": [{"url": "http://localhost/a2a", "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}]}
        first = {"raw": "", "json": None, "sha256": hashlib.sha256(b"").hexdigest(), "started_at_utc": stamp(101.01), "url": "http://localhost/card", "method": "GET", "headers": {}}
        last = body(card, 101.02, True)
        last.update(status=200)
        entry = {"exchange_id": "card-1", "role": "native_peer_response", "request": first, "response": last}
        records[1:1] = [{"type": "request-started", **entry, "response": None}, {"type": "exchange-completed", **entry}]
        for record in records:
            if (record.get("request", {}).get("json") or {}).get("method") in {"SendMessage", "GetTask"} and record.get("exchange_id") in {"http-3", "http-4"}:
                record["request"]["headers"] = {}
        self.assertTrue(check_status_native_sidecar(source, records))
        records = [r for r in records if r.get("exchange_id") != "card-1"]
        self.assertFalse(check_status_native_sidecar(source, records))


class ArchivedControlledDerivativeTests(unittest.TestCase):
    def test_wrong_capture_text_decoding_rejected_without_rebasing_hashes(self):
        root = Path(__file__).resolve().parents[1]
        path = root / "runs/wire-observation/mgcrea_mcp_a2a-2026-10-23T20-06-37-342Z-9536"
        source = json.loads((path / "runtime.json").read_text(encoding="cp1252"))
        records = [json.loads(line) for line in (path / "private-native-http.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertFalse(check_status_native_sidecar(source, records))

    def test_archived_sidecars_are_explicit_private_input_controls(self):
        root = Path(__file__).resolve().parents[1]
        for name in ("mgcrea_mcp_a2a-2026-10-23T20-06-37-342Z-9536", "amirk_a2a_to_mcp-2026-10-23T20-02-10-750Z-3828"):
            with self.subTest(route=name):
                path = root / "runs/wire-observation" / name
                source = json.loads((path / "runtime.json").read_text(encoding="utf-8"))
                source["provenance"]["status_checker_control"] = "Earlier artifact-goal capture used only as a native-correlation unit control"
                records = [json.loads(line) for line in (path / "private-native-http.jsonl").read_text(encoding="utf-8").splitlines()]
                self.assertTrue(check_status_native_sidecar(source, records))

    def test_old_real_capture_status_derivative_remains_labelled(self):
        root = Path(__file__).resolve().parents[1]
        filename = root / "runs/wire-observation/mgcrea_mcp_a2a-2026-10-23T20-06-37-342Z-9536/runtime.json"
        source = json.loads(filename.read_text(encoding="utf-8"))
        source["provenance"]["status_checker_control"] = "Status-only unit derivative of older artifact-goal observation; not new Carol capture"
        values = []
        operations, sources, indices = [], [], []
        # Explicit expected sequence is fixed independently from the old capture.
        expected = [("submitted", "send-acknowledgement"), ("submitted", "local-mirror"),
                    ("input_required", "peer-refreshed"), ("input_required", "send-acknowledgement"),
                    ("input_required", "local-mirror"), ("completed", "peer-refreshed"), ("completed", "local-mirror")]
        selected = [i for i, e in enumerate(source["exchanges"]) if e["request"]["json"].get("params", {}).get("name") in {"a2a_send_message", "a2a_get_task"}]
        first_payload = json.loads(source["exchanges"][selected[0]]["response"]["json"]["result"]["content"][0]["text"])
        task = first_payload["task"]["id"]
        context = first_payload["task"]["context_id"]
        for offset, index in enumerate(selected):
            values.append(fields(MG, task=task, context=context, returned_task_reference=task, returned_context_reference=context, status=expected[offset][0]))
            operations.append("a2a_send_message" if offset in (0, 3) else "a2a_get_task")
            sources.append(expected[offset][1])
            indices.append(index)
        projection = claim(source, values, operations, sources, indices)
        self.assertTrue(check_status_projection(source, projection))

    def test_native_port_positive_raw_wrappers_are_constructed_controls(self):
        root = Path(__file__).resolve().parents[1]
        path = root / "runs/reference-port-native/carol-port-native-v1-2026-10-23T21-10-38-290Z-14572/native-http.jsonl"
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        completed = {record["exchange_id"]: record for record in records if record.get("type") == "exchange-completed"}
        pending = completed["http-3"]["response"]["json"]["result"]
        task, context = pending["id"], pending["contextId"]
        exchanges = [exchange(1, "a2a_send_message", {"text": "controlled initial prefix"}, tool({"task": {"id": task, "context_id": context, "state": "input_required"}}))]
        for index, key in enumerate(("http-4", "http-5"), 2):
            native = completed[key]
            request, response = native["request"]["json"], native["response"]["json"]
            exchanges.append(exchange(index, "a2a_request", {"method": request["method"], "params": request["params"]}, tool(response)))
        source = trace(MG, exchanges)
        source["provenance"]["label"] = "Constructed MCP raw wrappers around actual Carol-native1.0 control bodies; not observed R4"
        source["provenance"]["native_control_source"] = str(path.relative_to(root)).replace("\\", "/")
        values = [fields(MG, task=task, context=context, returned_task_reference=task, returned_context_reference=context, status=state)
                  for state in ("input_required", "completed", "completed")]
        projection = claim(source, values, ["a2a_send_message", "a2a_request/SendMessage", "a2a_request/GetTask"], ["send-acknowledgement", "send-acknowledgement", "peer-refreshed"])
        self.assertTrue(check_status_projection(source, projection))
        self.assertEqual(evaluate(projection["manifest"], projection["analysis_clock"])["decision"], "supported")


if __name__ == "__main__":
    unittest.main()
