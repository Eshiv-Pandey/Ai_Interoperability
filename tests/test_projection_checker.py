"""Separately authored wire-checker fixtures, never observed bridge runs.

Expected projections below are stated directly by the test author. These tests
do not import the projector or use its extraction or transition construction.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import unittest

from interoperability.oracle import evaluate
from interoperability.projection_checker import check_native_sidecar, check_projection


AMIRK = "amirk_a2a_to_mcp"
MGCREA = "mgcrea_mcp_a2a"
PIN = {AMIRK: "58eff9da469bccdc432bf164662727947de646b4",
       MGCREA: "c4d9d3c57c1746abbf9f6aadd3a9912d464eb1f5"}
EXPECTED = "destination = Paris"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def stamp(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat().replace("+00:00", "Z")


def body(message, seconds, *, response=False):
    raw = json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n"
    return {"raw": raw, "json": message,
            "sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            "observed_at_utc" if response else "started_at_utc": stamp(seconds)}


def tool_payload(payload):
    return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}]}


def exchange(index, operation, arguments, result):
    method = operation if operation.startswith("tasks/") else "tools/call"
    params = arguments if method.startswith("tasks/") else {"name": operation, "arguments": arguments}
    request = {"jsonrpc": "2.0", "id": index, "method": method, "params": params}
    response = {"jsonrpc": "2.0", "id": index, "result": result}
    return {"exchange_id": "mcp-" + str(index), "phase": "synthetic-development",
            "request": body(request, 100 + index), "response": body(response, 100.5 + index, response=True),
            "elapsed_ms": 500}


def authored_trace(route, exchanges):
    return {"schema_version": "runtime-wire-observation/1", "run_id": "synthetic-" + route,
            "route_id": route, "source_commit": PIN[route],
            "protocol": {"mcp": "2026-07-28" if route == AMIRK else "2025-11-25"},
            "provenance": {"kind": "authored-test", "label": "synthetic checker fixture; no bridge execution"},
            "outcome": "synthetic", "exchanges": exchanges}


def view(route, **fields):
    values = {"task_namespace": "bridge-handle" if route == AMIRK else "public-native-a2a-id",
              "request_target_valid": True, "required_task_reference": "task-A",
              "required_context_reference": "context-A"}
    values.update(fields)
    return values


def claimed(trace, observations, sources):
    """Manually specified public shape; reads no returned payload field paths."""
    clock = 101 + len(trace["exchanges"])
    run = trace["run_id"]
    route = trace["route_id"]
    ids = [run + "::" + e["exchange_id"] for e in trace["exchanges"]]
    operations = [e["request"]["json"]["params"].get("name", e["request"]["json"]["method"])
                  for e in trace["exchanges"]]
    source_digest = digest(trace)
    events = [{"state_id": ids[index], "exchange_id": e["exchange_id"],
               "request_method": e["request"]["json"]["method"], "operation": operations[index],
               "response_sha256": e["response"]["sha256"], "evidence_source": sources[index],
               "observable_fields": observations[index]}
              for index, e in enumerate(trace["exchanges"])]
    namespace = observations[0]["task_namespace"]
    return {"schema_version": "observed-trace-projection/0", "source_trace_sha256": source_digest,
            "config": {"expected_artifact_text": EXPECTED}, "analysis_clock": clock,
            "initial_exchange_id": trace["exchanges"][0]["exchange_id"], "events": events,
            "manifest": {
                "schema_version": "finite-continuation/1", "id": run + ":historical",
                "route": route + " historical observation",
                "provenance": {"kind": "wire-derived", "source": "runtime-wire-observation/1:" + source_digest,
                               "review_status": "AI-authored projection; human review pending"},
                "horizon": len(ids) - 1,
                "evidence": {"complete": False, "observed_at": clock, "valid_until": clock},
                "initial": ids[0], "states": dict(zip(ids, observations)),
                "transitions": [{"id": "edge:" + trace["exchanges"][i]["exchange_id"],
                                 "source": ids[i - 1], "target": ids[i], "operation": operations[i]}
                                for i in range(1, len(ids))],
                "runtime_contract": {
                    "goal": [{"field": "status", "op": "eq", "value": "completed"},
                             {"field": "returned_task_reference", "op": "eq_field", "other_field": "required_task_reference"},
                             {"field": "returned_context_reference", "op": "eq_field", "other_field": "required_context_reference"},
                             {"field": "artifact_contains_expected", "op": "eq", "value": True}],
                    "invariants": [{"field": "request_target_valid", "op": "eq", "value": True},
                                   {"field": "task_namespace", "op": "eq", "value": namespace}],
                },
            }}


def mgcrea_fixture(*, continuation=False):
    first = {"id": "task-A", "context_id": "context-A", "state": "submitted", "artifact_count": 0}
    final = {"id": "task-A", "context_id": "context-A", "state": "completed",
             "history": [{"role": "user", "text": "Paris"}],
             "artifacts": [{"artifact_id": "artifact-A", "name": "result", "text": EXPECTED}]}
    exchanges = [exchange(1, "a2a_send_message", {"text": "task: reverse"}, tool_payload({"task": first}))]
    observations = [view(MGCREA, returned_task_reference="task-A", returned_context_reference="context-A", status="submitted")]
    sources = ["send-acknowledgement"]
    if continuation:
        pending = {"id": "task-A", "context_id": "context-A", "state": "input_required", "artifacts": []}
        exchanges.extend([
            exchange(2, "a2a_get_task", {"task_id": "task-A", "refresh": False}, tool_payload(pending)),
            exchange(3, "a2a_send_message", {"task_id": "task-A", "context_id": "context-A", "text": "Paris"}, tool_payload({"task": {k: v for k, v in pending.items() if k != "artifacts"}})),
            exchange(4, "a2a_get_task", {"task_id": "task-A", "refresh": False}, tool_payload(pending)),
        ])
        observations.extend([
            view(MGCREA, returned_task_reference="task-A", returned_context_reference="context-A", status="input_required", artifact_contains_expected=False),
            view(MGCREA, returned_task_reference="task-A", returned_context_reference="context-A", status="input_required"),
            view(MGCREA, returned_task_reference="task-A", returned_context_reference="context-A", status="input_required", artifact_contains_expected=False),
        ])
        sources.extend(["local-mirror", "send-acknowledgement", "local-mirror"])
    exchanges.append(exchange(len(exchanges) + 1, "a2a_get_task", {"task_id": "task-A", "refresh": True}, tool_payload(final)))
    observations.append(view(MGCREA, returned_task_reference="task-A", returned_context_reference="context-A", status="completed", artifact_contains_expected=True))
    sources.append("peer-refreshed")
    trace = authored_trace(MGCREA, exchanges)
    return trace, claimed(trace, observations, sources)


def amirk_fixture():
    pending = {"kind": "task", "taskHandle": "task-A", "contextHandle": "context-A", "status": "input_required"}
    final = {"kind": "task", "taskHandle": "task-A", "contextHandle": "context-A", "status": "completed",
             "artifacts": [{"artifactId": "artifact-A", "name": "result"}]}
    artifact_block = {"type": "text", "text": EXPECTED,
                      "_meta": {"io.github.amirk-s/a2a": {"artifactId": "artifact-A", "partKind": "text"}}}
    exchanges = [
        exchange(1, "a2a_send_message", {"text": "ask: destination"}, {"structuredContent": pending, "content": []}),
        exchange(2, "tasks/get", {"taskId": "task-A"}, {"taskId": "task-A", "status": "input_required", "inputRequests": {"answer": {}}}),
        exchange(3, "tasks/update", {"taskId": "task-A", "inputResponses": {"answer": {"action": "accept", "content": {"answer": "Paris"}}}}, {"resultType": "complete"}),
        exchange(4, "tasks/get", {"taskId": "task-A"}, {"taskId": "task-A", "status": "completed", "result": {"structuredContent": final, "content": [artifact_block]}}),
    ]
    observations = [view(AMIRK, returned_task_reference="task-A", returned_context_reference="context-A", status="input_required"),
                    view(AMIRK, returned_task_reference="task-A", status="input_required"),
                    view(AMIRK),
                    view(AMIRK, returned_task_reference="task-A", returned_context_reference="context-A", status="completed", artifact_contains_expected=True)]
    trace = authored_trace(AMIRK, exchanges)
    return trace, claimed(trace, observations, ["send-acknowledgement", "extension-observation", "extension-observation", "extension-observation"])


def replace_response(trace, index, result):
    message = {"jsonrpc": "2.0", "id": trace["exchanges"][index]["request"]["json"]["id"], "result": result}
    trace["exchanges"][index]["response"] = body(message, 101.5 + index, response=True)


def rebind(trace, projection):
    """Update only source/event hashes after a labelled synthetic mutation."""
    projection["source_trace_sha256"] = digest(trace)
    projection["manifest"]["provenance"]["source"] = "runtime-wire-observation/1:" + digest(trace)
    for event, exchange_record in zip(projection["events"], trace["exchanges"]):
        event["response_sha256"] = exchange_record["response"]["sha256"]


class ProjectionCheckerTests(unittest.TestCase):
    def test_normal_task_send_get(self):
        trace, projection = mgcrea_fixture()
        self.assertTrue(check_projection(trace, projection))
        self.assertEqual(evaluate(projection["manifest"], projection["analysis_clock"])["decision"], "supported")

    def test_pending_ack_local_stale_final_artifact(self):
        trace, projection = mgcrea_fixture(continuation=True)
        self.assertTrue(check_projection(trace, projection))
        self.assertEqual(projection["events"][3]["evidence_source"], "local-mirror")
        self.assertEqual(evaluate(projection["manifest"], projection["analysis_clock"])["decision"], "supported")

    def test_modern_ack_and_nested_completion_are_distinct(self):
        trace, projection = amirk_fixture()
        self.assertTrue(check_projection(trace, projection))
        self.assertNotIn("status", projection["events"][2]["observable_fields"])
        self.assertNotIn("returned_context_reference", projection["events"][1]["observable_fields"])

    def test_ack_cannot_be_projected_as_completion(self):
        trace, projection = amirk_fixture()
        projection["events"][2]["observable_fields"]["status"] = "completed"
        self.assertFalse(check_projection(trace, projection))

    def test_wrong_response_id(self):
        trace, projection = mgcrea_fixture()
        response = trace["exchanges"][-1]["response"]
        response["json"]["id"] = 999
        trace["exchanges"][-1]["response"] = body(response["json"], 102.5, response=True)
        rebind(trace, projection)
        self.assertFalse(check_projection(trace, projection))

    def test_hash_and_parsed_mismatches(self):
        for field in ("sha256", "json"):
            with self.subTest(field=field):
                trace, projection = mgcrea_fixture()
                response = trace["exchanges"][-1]["response"]
                response[field] = "0" * 64 if field == "sha256" else {"jsonrpc": "2.0", "id": 2, "result": {}}
                rebind(trace, projection)
                self.assertFalse(check_projection(trace, projection))

    def test_duplicate_json_keys(self):
        trace, projection = mgcrea_fixture()
        response = trace["exchanges"][-1]["response"]
        response["raw"] = '{"jsonrpc":"2.0","id":2,"id":2,"result":{}}'
        response["json"] = {"jsonrpc": "2.0", "id": 2, "result": {}}
        response["sha256"] = hashlib.sha256(response["raw"].encode()).hexdigest()
        rebind(trace, projection)
        self.assertFalse(check_projection(trace, projection))

    def test_duplicate_request_exchange_ids_and_overlap(self):
        for mutation in ("exchange", "request", "overlap"):
            with self.subTest(mutation=mutation):
                trace, projection = mgcrea_fixture()
                e = trace["exchanges"][-1]
                if mutation == "exchange":
                    e["exchange_id"] = trace["exchanges"][0]["exchange_id"]
                elif mutation == "request":
                    e["request"]["json"]["id"] = 1
                    e["request"] = body(e["request"]["json"], 102)
                    e["response"]["json"]["id"] = 1
                    e["response"] = body(e["response"]["json"], 102.5, response=True)
                else:
                    e["request"]["started_at_utc"] = stamp(101.2)
                rebind(trace, projection)
                self.assertFalse(check_projection(trace, projection))

    def test_returned_reference_mutations_remain_literal(self):
        for field, observable in (("id", "returned_task_reference"), ("context_id", "returned_context_reference")):
            with self.subTest(field=field):
                trace, projection = mgcrea_fixture()
                data = {"id": "task-A", "context_id": "context-A", "state": "completed", "artifacts": [{"artifact_id": "artifact-A", "text": EXPECTED}]}
                data[field] = "other-execution-reference"
                replace_response(trace, 1, tool_payload(data))
                projection["events"][1]["observable_fields"][observable] = data[field]
                rebind(trace, projection)
                self.assertTrue(check_projection(trace, projection))
                self.assertEqual(evaluate(projection["manifest"], projection["analysis_clock"])["decision"], "unknown")

    def test_history_is_never_artifact_delivery(self):
        trace, projection = mgcrea_fixture()
        replace_response(trace, 1, tool_payload({"id": "task-A", "context_id": "context-A", "state": "completed", "history": [{"text": EXPECTED}], "artifacts": []}))
        projection["events"][1]["observable_fields"]["artifact_contains_expected"] = False
        rebind(trace, projection)
        self.assertTrue(check_projection(trace, projection))
        self.assertEqual(evaluate(projection["manifest"], projection["analysis_clock"])["decision"], "unknown")
        projection["events"][1]["observable_fields"]["artifact_contains_expected"] = True
        self.assertFalse(check_projection(trace, projection))

    def test_missing_observable_is_unknown(self):
        trace, projection = mgcrea_fixture()
        replace_response(trace, 1, tool_payload({"id": "task-A", "state": "completed"}))
        fields = projection["events"][1]["observable_fields"]
        del fields["returned_context_reference"]
        del fields["artifact_contains_expected"]
        rebind(trace, projection)
        self.assertTrue(check_projection(trace, projection))
        self.assertEqual(evaluate(projection["manifest"], projection["analysis_clock"])["decision"], "unknown")

    def test_wrong_or_missing_request_target_is_false(self):
        for params in ({"refresh": True}, {"task_id": "different-task", "refresh": True}):
            trace, projection = mgcrea_fixture()
            request = trace["exchanges"][1]["request"]["json"]
            request["params"]["arguments"] = params
            trace["exchanges"][1]["request"] = body(request, 102)
            projection["events"][1]["observable_fields"]["request_target_valid"] = False
            rebind(trace, projection)
            self.assertTrue(check_projection(trace, projection))
            self.assertEqual(evaluate(projection["manifest"], projection["analysis_clock"])["decision"], "unknown")

    def test_malformed_tool_arguments_return_false(self):
        for arguments in (None, [], 7, "task-A"):
            with self.subTest(arguments=arguments):
                trace, projection = mgcrea_fixture()
                request = trace["exchanges"][1]["request"]["json"]
                request["params"]["arguments"] = arguments
                trace["exchanges"][1]["request"] = body(request, 102)
                rebind(trace, projection)
                self.assertFalse(check_projection(trace, projection))

    def test_namespace_and_provenance_cannot_be_rewritten(self):
        trace, projection = mgcrea_fixture()
        for mutation in ("namespace", "run", "source", "pin", "digest"):
            with self.subTest(mutation=mutation):
                t, p = copy.deepcopy(trace), copy.deepcopy(projection)
                if mutation == "namespace":
                    p["events"][1]["observable_fields"]["task_namespace"] = "bridge-handle"
                elif mutation == "run":
                    t["exchanges"][1]["run_id"] = "other-run"
                    rebind(t, p)
                elif mutation == "source":
                    p["manifest"]["provenance"]["review_status"] = "human approved"
                elif mutation == "pin":
                    t["source_commit"] = "0" * 40
                    rebind(t, p)
                else:
                    p["source_trace_sha256"] = "0" * 64
                self.assertFalse(check_projection(t, p))

    def test_model_cannot_gain_branch_complete_evidence_or_ttl(self):
        for mutation in ("edge", "complete", "ttl", "clock", "horizon", "goal"):
            with self.subTest(mutation=mutation):
                trace, projection = mgcrea_fixture()
                model = projection["manifest"]
                if mutation == "edge":
                    model["transitions"].append({"id": "invented", "source": model["initial"], "target": model["initial"], "operation": "future-call"})
                elif mutation == "complete":
                    model["evidence"]["complete"] = True
                elif mutation == "ttl":
                    model["evidence"]["valid_until"] += 900
                elif mutation == "clock":
                    projection["analysis_clock"] += 1
                elif mutation == "horizon":
                    model["horizon"] += 1
                else:
                    model["runtime_contract"]["goal"] = []
                self.assertFalse(check_projection(trace, projection))

    def test_historical_evidence_expires_immediately(self):
        trace, projection = mgcrea_fixture()
        self.assertTrue(check_projection(trace, projection))
        self.assertEqual(evaluate(projection["manifest"], projection["analysis_clock"] + 1)["decision"], "unknown")

    def test_archival_clock_includes_non_task_error_response(self):
        trace, projection = mgcrea_fixture()
        request = {"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}}
        response = {"jsonrpc": "2.0", "id": 3, "error": {"code": -32601, "message": "synthetic setup error"}}
        trace["exchanges"].append({"exchange_id": "setup-3", "phase": "synthetic-setup",
                                   "request": body(request, 103), "response": body(response, 103.5, response=True),
                                   "elapsed_ms": 500})
        projection["analysis_clock"] = 104
        projection["manifest"]["evidence"] = {"complete": False, "observed_at": 104, "valid_until": 104}
        rebind(trace, projection)
        self.assertTrue(check_projection(trace, projection))

    def test_missing_artifact_body_is_not_false_or_true(self):
        trace, projection = amirk_fixture()
        record = trace["exchanges"][-1]["response"]["json"]["result"]
        record["result"]["content"] = []
        replace_response(trace, 3, record)
        del projection["events"][-1]["observable_fields"]["artifact_contains_expected"]
        rebind(trace, projection)
        self.assertTrue(check_projection(trace, projection))
        self.assertEqual(evaluate(projection["manifest"], projection["analysis_clock"])["decision"], "unknown")

    def test_unlabelled_expected_text_cannot_satisfy_artifact_ref(self):
        trace, projection = amirk_fixture()
        record = trace["exchanges"][-1]["response"]["json"]["result"]
        record["result"]["content"][0]["_meta"] = {"io.github.amirk-s/a2a": {"messageId": "history-message"}}
        replace_response(trace, 3, record)
        del projection["events"][-1]["observable_fields"]["artifact_contains_expected"]
        rebind(trace, projection)
        self.assertTrue(check_projection(trace, projection))

    def test_nested_task_record_contradiction_is_rejected(self):
        trace, projection = amirk_fixture()
        record = trace["exchanges"][-1]["response"]["json"]["result"]
        record["taskId"] = "another-task"
        replace_response(trace, 3, record)
        rebind(trace, projection)
        self.assertFalse(check_projection(trace, projection))

    def test_ordinary_status_cannot_contradict_disclosed_a2a_state(self):
        trace, projection = amirk_fixture()
        record = trace["exchanges"][-1]["response"]["json"]["result"]
        record["result"]["structuredContent"]["a2aState"] = "TASK_STATE_FAILED"
        replace_response(trace, 3, record)
        rebind(trace, projection)
        self.assertFalse(check_projection(trace, projection))

    def test_modern_completed_without_result_is_unknown(self):
        trace, projection = amirk_fixture()
        replace_response(trace, 3, {"taskId": "task-A", "status": "completed"})
        projection["events"][-1]["observable_fields"] = view(AMIRK, returned_task_reference="task-A")
        projection["manifest"]["states"][projection["events"][-1]["state_id"]] = projection["events"][-1]["observable_fields"]
        rebind(trace, projection)
        self.assertTrue(check_projection(trace, projection))
        self.assertEqual(evaluate(projection["manifest"], projection["analysis_clock"])["decision"], "unknown")

    def test_modern_delivery_completed_does_not_override_logical_failure(self):
        trace, projection = amirk_fixture()
        record = trace["exchanges"][-1]["response"]["json"]["result"]
        record["result"]["structuredContent"]["status"] = "failed"
        replace_response(trace, 3, record)
        projection["events"][-1]["observable_fields"]["status"] = "failed"
        rebind(trace, projection)
        self.assertTrue(check_projection(trace, projection))
        self.assertEqual(evaluate(projection["manifest"], projection["analysis_clock"])["decision"], "unknown")

    def test_nested_tool_error_requires_separate_recovery_model(self):
        trace, projection = amirk_fixture()
        record = trace["exchanges"][-1]["response"]["json"]["result"]
        record["result"]["structuredContent"]["status"] = "failed"
        record["result"]["isError"] = True
        replace_response(trace, 3, record)
        rebind(trace, projection)
        self.assertFalse(check_projection(trace, projection))

    def test_removed_completion_is_partial_unknown(self):
        trace, projection = amirk_fixture()
        trace["exchanges"] = trace["exchanges"][:3]
        observations = [e["observable_fields"] for e in projection["events"][:3]]
        projection = claimed(trace, observations, ["send-acknowledgement", "extension-observation", "extension-observation"])
        self.assertTrue(check_projection(trace, projection))
        self.assertEqual(evaluate(projection["manifest"], projection["analysis_clock"])["decision"], "unknown")

    def test_task_error_cannot_disappear_between_states(self):
        trace, projection = mgcrea_fixture()
        trace["exchanges"][-1]["response"] = body({"jsonrpc": "2.0", "id": 2, "error": {"code": -32000, "message": "fixture error"}}, 102.5, response=True)
        rebind(trace, projection)
        self.assertFalse(check_projection(trace, projection))

    def test_cancellation_after_selected_prefix_cannot_be_skipped(self):
        for operation, arguments in (("tasks/cancel", {"taskId": "task-A"}),
                                     ("a2a_cancel_task", {"task_id": "task-A"})):
            with self.subTest(operation=operation):
                trace, projection = mgcrea_fixture()
                cancel = exchange(3, operation, arguments, {"resultType": "complete"})
                trace["exchanges"].append(cancel)
                projection["analysis_clock"] = 104
                projection["manifest"]["evidence"] = {"complete": False, "observed_at": 104, "valid_until": 104}
                rebind(trace, projection)
                self.assertFalse(check_projection(trace, projection))

    def test_no_projector_import_or_shared_extraction(self):
        source = (Path(__file__).parents[1] / "src/interoperability/projection_checker.py").read_text(encoding="utf-8")
        self.assertNotIn("from interoperability.wire_projection", source)
        self.assertNotIn("from .wire_projection", source)
        self.assertNotIn("from .baseline", source)


class PrivateSidecarTests(unittest.TestCase):
    def fixture(self, *, streaming=False):
        trace, projection = mgcrea_fixture()
        native_task = {"id": "task-A", "contextId": "context-A", "status": {"state": "TASK_STATE_SUBMITTED"}}
        final_task = {"id": "task-A", "contextId": "context-A", "status": {"state": "TASK_STATE_COMPLETED"},
                      "artifacts": [{"artifactId": "artifact-A", "parts": [{"text": EXPECTED}]}]}
        records = [{"schema_version": "private-native-http/1", "run_id": trace["run_id"], "route_id": trace["route_id"]}]
        for index, (method, params, task) in enumerate([
            ("SendStreamingMessage" if streaming else "SendMessage", {"message": {"parts": [{"text": "task: reverse"}]}}, native_task),
            ("GetTask", {"id": "task-A"}, final_task),
        ], 1):
            request = {"jsonrpc": "2.0", "id": index, "method": method, "params": params}
            response = {"jsonrpc": "2.0", "id": index, "result": {"task": task}}
            q, r = body(request, 100.1 + index), body(response, 100.3 + index, response=True)
            q["method"] = "POST"
            r.update(status=200, headers={"content-type": "application/json"}, headers_observed_at_utc=stamp(100.2 + index))
            if streaming and index == 1:
                r["raw"] = "data: " + json.dumps(response) + "\n\n"
                r["json"] = None
                r["sha256"] = hashlib.sha256(r["raw"].encode()).hexdigest()
                r["headers"] = {"content-type": "text/event-stream"}
                # Explicit async reply: headers occur after send's MCP ack.
                r["headers_observed_at_utc"] = stamp(102.1)
                r["observed_at_utc"] = stamp(102.2)
            records.append({"exchange_id": "native-" + str(index), "role": "native_peer_response", "request": q, "response": r, "elapsed_ms": 200})
        return trace, records

    def test_exact_native_correlation(self):
        trace, records = self.fixture()
        self.assertTrue(check_native_sidecar(trace, records))

    def test_stream_headers_after_ack_remain_tied_to_dispatch(self):
        trace, records = self.fixture(streaming=True)
        self.assertTrue(check_native_sidecar(trace, records))

    def test_native_empty_artifacts_errors_states_and_snapshots_cannot_back_success(self):
        for mutation in ("empty-artifacts", "omitted-artifacts", "error", "failed-state", "empty-result"):
            with self.subTest(mutation=mutation):
                trace, records = self.fixture()
                response = records[2]["response"]["json"]
                if mutation == "empty-artifacts":
                    response["result"]["task"]["artifacts"] = []
                elif mutation == "omitted-artifacts":
                    del response["result"]["task"]["artifacts"]
                elif mutation == "error":
                    del response["result"]
                    response["error"] = {"code": -32001, "message": "Task not found"}
                elif mutation == "failed-state":
                    response["result"]["task"]["status"]["state"] = "TASK_STATE_FAILED"
                else:
                    response["result"] = {}
                records[2]["response"] = body(response, 102.3, response=True)
                records[2]["response"].update(status=200, headers={"content-type": "application/json"}, headers_observed_at_utc=stamp(102.2))
                self.assertFalse(check_native_sidecar(trace, records))

    def test_native_error_can_be_disclosed_as_modern_failed_record(self):
        pending = {"kind": "task", "taskHandle": "task-A", "contextHandle": "context-A", "status": "input_required"}
        trace = authored_trace(AMIRK, [
            exchange(1, "a2a_send_message", {"text": "task: reverse"}, {"structuredContent": pending, "content": []}),
            exchange(2, "tasks/get", {"taskId": "task-A"}, {"taskId": "task-A", "status": "failed", "error": {"code": -32001, "message": "Task not found"}}),
        ])
        _, records = self.fixture()
        records[0].update(run_id=trace["run_id"], route_id=AMIRK)
        native_response = {"jsonrpc": "2.0", "id": 2, "error": {"code": -32001, "message": "Task not found"}}
        records[2]["response"] = body(native_response, 102.3, response=True)
        records[2]["response"].update(status=200, headers={"content-type": "application/json"}, headers_observed_at_utc=stamp(102.2))
        self.assertTrue(check_native_sidecar(trace, records))

    def test_native_cross_run_hash_id_or_context_mutations(self):
        for mutation in ("run", "hash", "id", "context", "text", "initiation"):
            with self.subTest(mutation=mutation):
                trace, records = self.fixture()
                r = records[2]["response"]
                if mutation == "run":
                    records[0]["run_id"] = "other-run"
                elif mutation == "hash":
                    r["sha256"] = "0" * 64
                elif mutation == "id":
                    r["json"]["id"] = 99
                    records[2]["response"] = body(r["json"], 102.3, response=True)
                    records[2]["response"].update(status=200, headers={"content-type": "application/json"}, headers_observed_at_utc=stamp(102.2))
                elif mutation == "context":
                    r["json"]["result"]["task"]["contextId"] = "another-context"
                    records[2]["response"] = body(r["json"], 102.3, response=True)
                    records[2]["response"].update(status=200, headers={"content-type": "application/json"}, headers_observed_at_utc=stamp(102.2))
                elif mutation == "text":
                    q = records[1]["request"]["json"]
                    q["params"]["message"]["parts"][0]["text"] = "unrelated send"
                    records[1]["request"] = body(q, 101.1)
                else:
                    records[2]["request"]["started_at_utc"] = stamp(109)
                    records[2]["response"]["headers_observed_at_utc"] = stamp(109.1)
                    records[2]["response"]["observed_at_utc"] = stamp(109.2)
                self.assertFalse(check_native_sidecar(trace, records))


if __name__ == "__main__":
    unittest.main()
