"""Software controls from archived public traces; no new bridge observations.

Mutated data stay in memory. Raw-operation wrappers are explicitly constructed
controls, not a claim that the four-variant prospective probe already ran.
"""

import base64
import copy
import hashlib
import json
from pathlib import Path
import unittest

from interoperability import baseline, oracle
from interoperability.status_projection import project_status_trace
from interoperability.wire_projection import ProjectionError


ROOT = Path(__file__).resolve().parents[1]
CAPTURES = (
    "runs/wire-observation/amirk_a2a_to_mcp-2026-10-23T20-02-10-750Z-3828/runtime.json",
    "runs/wire-observation/mgcrea_mcp_a2a-2026-10-23T20-06-37-342Z-9536/runtime.json",
)


def captured(index):
    return json.loads((ROOT / CAPTURES[index]).read_text(encoding="utf-8"))


def rewrite(record, value):
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n"
    data = raw.encode("utf-8")
    record.update(raw=raw, json=value, sha256=hashlib.sha256(data).hexdigest())
    if "bytes" in record:
        record["bytes"] = len(data)
    if "base64" in record:
        record["base64"] = base64.b64encode(data).decode("ascii")


def edit_payload(exchange, mutator):
    response = copy.deepcopy(exchange["response"]["json"])
    result = response["result"]
    if "structuredContent" in result:
        mutator(result["structuredContent"])
    else:
        payload = json.loads(result["content"][0]["text"])
        mutator(payload)
        result["content"][0]["text"] = json.dumps(payload, ensure_ascii=False)
    rewrite(exchange["response"], response)


def raw_control():
    """Convert final old typed sends/reads into labelled raw software controls."""
    source = captured(1)
    source["provenance"]["controlled_derivative"] = "Constructed raw SendMessage/GetTask wrappers"
    first = json.loads(source["exchanges"][3]["response"]["json"]["result"]["content"][0]["text"])
    task, context = first["task"]["id"], first["task"]["context_id"]
    for exchange in source["exchanges"]:
        if exchange["exchange_id"] not in ("mcp-6", "mcp-8", "mcp-9"):
            continue
        request = copy.deepcopy(exchange["request"]["json"])
        send = exchange["exchange_id"] == "mcp-6"
        native_method = "SendMessage" if send else "GetTask"
        native_params = {"message": {"taskId": task, "contextId": context, "referenceTaskIds": [task]}} if send else {"id": task}
        request["params"] = {"name": "a2a_request", "arguments": {"method": native_method, "params": native_params}}
        rewrite(exchange["request"], request)
        native_task = {"id": task, "contextId": context, "status": {"state": "TASK_STATE_INPUT_REQUIRED" if send else "TASK_STATE_COMPLETED"}}
        native = {"jsonrpc": "2.0", "id": "control-native-" + exchange["exchange_id"], "result": {"task": native_task} if send else native_task}
        response = copy.deepcopy(exchange["response"]["json"])
        response["result"] = {"content": [{"type": "text", "text": json.dumps(native)}]}
        rewrite(exchange["response"], response)
    return source


class StatusProjection(unittest.TestCase):
    def test_actual_old_public_traces_support_only_historical_status_goal(self):
        for index in (0, 1):
            projection = project_status_trace(captured(index))
            model, clock = projection["manifest"], projection["analysis_clock"]
            self.assertEqual(len(model["runtime_contract"]["goal"]), 3)
            self.assertFalse(model["evidence"]["complete"])
            self.assertEqual(model["evidence"]["observed_at"], model["evidence"]["valid_until"])
            self.assertEqual(baseline.evaluate(model, clock)["decision"], "supported")
            result = oracle.evaluate(model, clock)
            self.assertTrue(oracle.check_certificate(model, result, clock))
            self.assertEqual(baseline.evaluate(model, clock + 1)["decision"], "unknown")
            self.assertTrue(all("artifact_contains_expected" not in event["observable_fields"] for event in projection["events"]))

    def test_actual_profiles_use_distinct_discovery_and_initialization(self):
        for index in (0, 1):
            source = captured(index)
            self.assertEqual(source["exchanges"][0]["request"]["json"]["method"], "server/discover" if index == 0 else "initialize")
            project_status_trace(source)

    def test_missing_setup_is_rejected(self):
        for index in (0, 1):
            source = captured(index)
            source["exchanges"] = source["exchanges"][1:]
            with self.assertRaisesRegex(ProjectionError, "profile|setup"):
                project_status_trace(source)

    def test_changed_discovered_version_is_rejected(self):
        source = captured(0)
        response = copy.deepcopy(source["exchanges"][0]["response"]["json"])
        response["result"]["supportedVersions"] = ["2025-11-25"]
        rewrite(source["exchanges"][0]["response"], response)
        with self.assertRaisesRegex(ProjectionError, "discovery"):
            project_status_trace(source)

    def test_missing_modern_envelope_is_rejected(self):
        source = captured(0)
        request = copy.deepcopy(source["exchanges"][2]["request"]["json"])
        del request["params"]["_meta"]
        rewrite(source["exchanges"][2]["request"], request)
        with self.assertRaisesRegex(ProjectionError, "per-request"):
            project_status_trace(source)

    def test_header_disagrees_is_rejected(self):
        source = captured(0)
        source["exchanges"][2]["request"]["headers"]["Mcp-Name"] = "wrong-tool"
        with self.assertRaisesRegex(ProjectionError, "header"):
            project_status_trace(source)

    def test_modern_tasks_requires_actual_declaration(self):
        source = captured(0)
        request = copy.deepcopy(source["exchanges"][3]["request"]["json"])
        request["params"]["_meta"]["io.modelcontextprotocol/clientCapabilities"] = {}
        rewrite(source["exchanges"][3]["request"], request)
        with self.assertRaisesRegex(ProjectionError, "Tasks declaration"):
            project_status_trace(source)

    def test_r1_cannot_silently_declare_tasks(self):
        source = captured(0)
        source["variant_id"] = "R1"
        with self.assertRaisesRegex(ProjectionError, "Tasks declaration"):
            project_status_trace(source)

    def test_declined_task_update_requires_separate_model(self):
        source = captured(0)
        exchange = next(e for e in source["exchanges"] if e["request"]["json"]["method"] == "tasks/update")
        request = copy.deepcopy(exchange["request"]["json"])
        for response in request["params"]["inputResponses"].values():
            response["action"] = "decline"
        rewrite(exchange["request"], request)
        with self.assertRaisesRegex(ProjectionError, "decline"):
            project_status_trace(source)

    def test_monotonic_corruption_rejected_despite_valid_utc(self):
        source = captured(1)
        source["exchanges"][-1]["request"]["monotonic_ns"] = "0"
        with self.assertRaisesRegex(ProjectionError, "monotonic"):
            project_status_trace(source)

    def test_changed_initialize_request_or_reply_is_rejected(self):
        for side in ("request", "response"):
            source = captured(1)
            value = copy.deepcopy(source["exchanges"][0][side]["json"])
            value["params" if side == "request" else "result"]["protocolVersion"] = "2026-07-28"
            rewrite(source["exchanges"][0][side], value)
            with self.assertRaisesRegex(ProjectionError, "negotiated"):
                project_status_trace(source)

    def test_missing_initialized_notification_is_rejected(self):
        source = captured(1)
        del source["exchanges"][1]
        with self.assertRaisesRegex(ProjectionError, "setup"):
            project_status_trace(source)

    def test_complete_trace_corruption_rejected_in_read_only_setup(self):
        source = captured(1)
        source["exchanges"][2]["response"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ProjectionError, "SHA-256"):
            project_status_trace(source)

    def test_wrong_decoding_of_unicode_is_rejected_without_altering_archive(self):
        source = json.loads((ROOT / CAPTURES[1]).read_bytes().decode("cp1252"))
        with self.assertRaisesRegex(ProjectionError, "SHA-256"):
            project_status_trace(source)
        project_status_trace(captured(1))

    def test_waiting_only_is_unknown(self):
        source = captured(1)
        source["exchanges"] = [e for e in source["exchanges"] if e["exchange_id"] not in ("mcp-8", "mcp-9")]
        projection = project_status_trace(source)
        self.assertEqual(oracle.evaluate(projection["manifest"], projection["analysis_clock"])["decision"], "unknown")

    def test_outer_delivery_completed_does_not_invent_logical_completion(self):
        source = captured(0)
        source["exchanges"] = source["exchanges"][:-1]
        response = copy.deepcopy(source["exchanges"][-1]["response"]["json"])
        del response["result"]["result"]
        rewrite(source["exchanges"][-1]["response"], response)
        projection = project_status_trace(source)
        self.assertNotIn("status", projection["events"][-1]["observable_fields"])
        self.assertEqual(oracle.evaluate(projection["manifest"], projection["analysis_clock"])["decision"], "unknown")

    def test_early_task_switch_cannot_redefine_original_task(self):
        source = captured(0)
        response = copy.deepcopy(source["exchanges"][2]["response"]["json"])
        response["result"]["taskId"] = "foreign-early-task"
        rewrite(source["exchanges"][2]["response"], response)
        with self.assertRaisesRegex(ProjectionError, "Early public"):
            project_status_trace(source)

    def test_missing_returned_context_remains_unknown(self):
        source = captured(1)
        for exchange in source["exchanges"]:
            if exchange["exchange_id"] in ("mcp-8", "mcp-9"):
                edit_payload(exchange, lambda payload: payload.pop("context_id"))
        projection = project_status_trace(source)
        self.assertNotIn("returned_context_reference", projection["events"][-1]["observable_fields"])
        self.assertEqual(oracle.evaluate(projection["manifest"], projection["analysis_clock"])["decision"], "unknown")

    def test_wrong_task_target_is_explicit_invariant_failure(self):
        source = captured(1)
        request = copy.deepcopy(source["exchanges"][-1]["request"]["json"])
        request["params"]["arguments"]["task_id"] = "foreign-target"
        rewrite(source["exchanges"][-1]["request"], request)
        projection = project_status_trace(source)
        self.assertFalse(projection["events"][-1]["observable_fields"]["request_target_valid"])

    def test_raw_software_control_has_native_states_and_action_edges(self):
        projection = project_status_trace(raw_control())
        raw_events = [e for e in projection["events"] if e["operation"].startswith("a2a_request/")]
        self.assertEqual([e["operation"] for e in raw_events], ["a2a_request/SendMessage", "a2a_request/GetTask", "a2a_request/GetTask"])
        self.assertEqual(raw_events[-1]["evidence_source"], "peer-refreshed")
        self.assertEqual(raw_events[-1]["observable_fields"]["status"], "completed")

    def test_raw_inner_error_rejected_when_outer_tool_not_error(self):
        source = raw_control()
        response = copy.deepcopy(source["exchanges"][-1]["response"]["json"])
        native = json.loads(response["result"]["content"][0]["text"])
        native["error"] = {"code": -32000, "message": "Authored control"}
        response["result"]["content"][0]["text"] = json.dumps(native)
        rewrite(source["exchanges"][-1]["response"], response)
        with self.assertRaisesRegex(ProjectionError, "Native raw error"):
            project_status_trace(source)

    def test_unmapped_raw_state_rejected(self):
        source = raw_control()
        def change(payload):
            payload["result"]["status"]["state"] = "NEW_NATIVE_STATE"
        edit_payload(source["exchanges"][-1], change)
        with self.assertRaisesRegex(ProjectionError, "Unmapped"):
            project_status_trace(source)

    def test_cancel_or_unmodelled_mutation_cannot_be_removed(self):
        for name in ("a2a_cancel_task", "a2a_respond_to_task"):
            source = captured(1)
            request = copy.deepcopy(source["exchanges"][3]["request"]["json"])
            request["params"]["name"] = name
            rewrite(source["exchanges"][3]["request"], request)
            with self.assertRaisesRegex(ProjectionError, "Cancellation|Unmodelled"):
                project_status_trace(source)

    def test_raw_parsed_hash_id_or_clock_corruption_rejected(self):
        for corrupt in ("parsed", "hash", "id", "clock", "duplicate"):
            source = captured(1)
            exchange = source["exchanges"][-1]
            if corrupt == "parsed":
                exchange["response"]["json"]["id"] = 999
            elif corrupt == "hash":
                exchange["request"]["sha256"] = "0" * 64
            elif corrupt == "id":
                value = copy.deepcopy(exchange["response"]["json"])
                value["id"] = 999
                rewrite(exchange["response"], value)
            elif corrupt == "clock":
                exchange["request"]["started_at_utc"] = source["exchanges"][0]["request"]["started_at_utc"]
            else:
                exchange["exchange_id"] = source["exchanges"][0]["exchange_id"]
            with self.assertRaises(ProjectionError):
                project_status_trace(source)


if __name__ == "__main__":
    unittest.main()
