"""Temporary A2A wire-format fixtures; no native applications or models."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from interoperability import agentops_public_events_v1 as normalizer


def encoded(value):
    return json.dumps(value).encode("utf-8")


def data_part(kind, value):
    return {"data": value, "metadata": {"adk_type": kind}}


def artifact(identity, part):
    return {"artifactId": "artifact-" + identity,
            "metadata": {"adk_event_id": identity, "adk_invocation_id": "invocation", "adk_author": "agent"},
            "parts": [part]}


class PublicEventNormalizerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.wire = self.root / "wire"
        self.output = self.root / "export"
        self.user = {"messageId": "user-message", "role": "ROLE_USER", "parts": [{"text": "Original fixture prompt.", "mediaType": "text/plain"}]}
        history_user = {"messageId": "user-message", "role": "ROLE_USER", "taskId": "task", "contextId": "context",
                        "parts": [{"text": "Original fixture prompt."}]}
        self.empty = {"messageId": "working-message", "role": "ROLE_AGENT", "metadata": {"adk_event_id": "working-event"}}
        action = {"id": "action-call", "name": "restart_service", "args": {"name": "inventory"}}
        self.confirm = {"messageId": "confirmation-message", "role": "ROLE_AGENT", "parts": [data_part("function_call", {
            "id": "confirmation-call", "name": "adk_request_confirmation", "args": {"originalFunctionCall": action, "toolConfirmation": {"confirmed": False}}})]}
        self.answer = {"messageId": "answer-message", "role": "ROLE_USER", "taskId": "task", "contextId": "context",
                       "parts": [data_part("function_response", {"id": "confirmation-call", "name": "adk_request_confirmation", "response": {"confirmed": True}})]}
        self.artifacts = [artifact("call-event", data_part("function_call", action)),
            artifact("pending-event", data_part("function_response", {"id": "action-call", "name": "restart_service", "response": {"error": "confirmation required"}})),
            artifact("executed-event", data_part("function_response", {"id": "action-call", "name": "restart_service", "response": {"result": "executed", "audit": {"id": 1.0}}})),
            artifact("text-event", {"text": "Fixture completed."})]
        submitted = self.task("TASK_STATE_SUBMITTED", history=[history_user])
        working = self.task("TASK_STATE_WORKING", message=self.empty, history=[history_user])
        pending = self.task("TASK_STATE_INPUT_REQUIRED", message=self.confirm, artifacts=self.artifacts[:2], history=[history_user, self.empty, self.confirm])
        completed = self.task("TASK_STATE_COMPLETED", artifacts=self.artifacts, history=[history_user, self.empty, self.confirm, self.answer])
        self.payloads = [
            ({}, {"name": "Fixture card"}, "GET", "/.well-known/agent-card.json"),
            (self.rpc("SendMessage", {"message": self.user}, 1), self.reply({"task": submitted}, 1), "POST", "/"),
            (self.rpc("GetTask", {"id": "task"}, 2), self.reply(working, 2), "POST", "/"),
            (self.rpc("GetTask", {"id": "task"}, 3), self.reply(pending, 3), "POST", "/"),
            (self.rpc("SendMessage", {"message": self.answer}, 4), self.reply({"task": completed}, 4), "POST", "/"),
            (self.rpc("GetTask", {"id": "task"}, 5), self.reply(completed, 5), "POST", "/"),
        ]
        self.rebuild()

    def task(self, state, *, message=None, artifacts=None, history=None):
        value = {"id": "task", "contextId": "context", "status": {"state": state}}
        if message is not None:
            value["status"]["message"] = deepcopy(message)
        if artifacts is not None:
            value["artifacts"] = deepcopy(artifacts)
        if history is not None:
            value["history"] = deepcopy(history)
        return value

    def rpc(self, method, params, identity):
        return {"jsonrpc": "2.0", "method": method, "params": deepcopy(params), "id": identity}

    def reply(self, result, identity):
        return {"jsonrpc": "2.0", "result": deepcopy(result), "id": identity}

    def rebuild(self):
        for sequence, (request, response, method, path) in enumerate(self.payloads, 1):
            directory = self.wire / f"{sequence:06d}"
            directory.mkdir(parents=True, exist_ok=True)
            request_raw = b"" if method == "GET" else encoded(request)
            response_raw = encoded(response)
            metadata = {"schema_version": "agentops-asgi-exchange/1", "sequence": sequence,
                "method": method, "path": path, "response_status": 200,
                "request_body_complete": True, "response_body_complete": True,
                "request_bytes": len(request_raw), "response_bytes": len(response_raw),
                "request_headers": [["a2a-version", "1.0"]],
                "started_at_utc": "2026-01-01T00:00:00+00:00", "finished_at_utc": "2026-01-01T00:00:01+00:00"}
            for name, raw in {"exchange.json": encoded(metadata), "request.body.bin": request_raw,
                              "response.body.bin": response_raw, "before.snapshot.json": b"{}", "after.snapshot.json": b"{}"}.items():
                (directory / name).write_bytes(raw)

    def raw(self):
        return normalizer._inventory(self.wire)

    def normalized(self):
        return normalizer.normalize(self.raw())

    def change_exchange(self, sequence, change):
        path = self.wire / f"{sequence:06d}" / "exchange.json"
        value = json.loads(path.read_bytes())
        change(value)
        path.write_bytes(encoded(value))

    def test_a2a_one_wrapped_direct_tasks_history_empty_messages_and_phase_replies(self):
        result = self.normalized()
        self.assertTrue(result["normalization_complete"])
        self.assertEqual(len(result["records"]), 6)
        self.assertEqual(sum(row["outcome"] == "task" for row in result["records"]), 5)
        self.assertEqual(len(result["messages"]), 4)
        self.assertEqual(len(result["observations"]), 7)
        calls = [row for row in result["observations"] if row["adk_type"] == "function_call"]
        responses = [row for row in result["observations"] if row["adk_type"] == "function_response"]
        self.assertEqual((len(calls), len(responses)), (2, 3))
        action_replies = [row for row in responses if row["function_id"] == "action-call"]
        self.assertEqual([row["adk_event_id"] for row in action_replies], ["pending-event", "executed-event"])
        self.assertFalse(result["client_receipt_proven"])
        self.assertFalse(result["causal_order_proven"])
        self.assertFalse(result["complete_event_stream_proven"])
        self.assertEqual(result["graded_task_outcomes"], 0)

    def test_request_history_enrichment_and_raw_representations_are_retained(self):
        result = self.normalized()
        message = next(row for row in result["messages"] if row["message_id"] == "user-message")
        request = next(row["message"] for row in message["representations"] if row["location"] == "request")
        history = next(row["message"] for row in message["representations"] if row["location"] == "history")
        self.assertNotIn("taskId", request)
        self.assertEqual(history["taskId"], "task")
        self.assertIn("mediaType", request["parts"][0])
        self.assertNotIn("mediaType", history["parts"][0])
        empty = next(row for row in result["messages"] if row["message_id"] == "working-message")
        self.assertNotIn("parts", empty["representations"][0]["message"])

    def test_cumulative_artifacts_deduplicate_without_dropping_action_phases(self):
        result = self.normalized()
        self.assertGreater(result["identical_repeated_parts"], 0)
        self.assertEqual(sum(row["namespace"] == "artifact_event" for row in result["observations"]), 4)

    def test_conflicting_repeated_artifact_part_is_rejected(self):
        self.payloads[-1][1]["result"]["artifacts"][2]["parts"][0]["data"]["response"]["result"] = "different"
        self.rebuild()
        with self.assertRaisesRegex(ValueError, "Conflicting repeated"):
            self.normalized()

    def test_changed_message_part_count_is_rejected(self):
        self.payloads[-1][1]["result"]["history"][0]["parts"] = []
        self.rebuild()
        with self.assertRaisesRegex(ValueError, "Conflicting repeated message"):
            self.normalized()

    def test_changed_existing_empty_message_adk_identity_is_rejected(self):
        self.payloads[-1][1]["result"]["history"][1]["metadata"]["adk_event_id"] = "different"
        self.rebuild()
        with self.assertRaisesRegex(ValueError, "Conflicting repeated message"):
            self.normalized()

    def test_history_message_role_or_association_mismatch_is_rejected(self):
        self.payloads[-1][1]["result"]["history"][0]["taskId"] = "unrelated"
        self.rebuild()
        with self.assertRaisesRegex(ValueError, "association mismatch"):
            self.normalized()

    def test_gettask_and_sendmessage_cannot_substitute_returned_task(self):
        self.payloads[-1][1]["result"]["id"] = "unrelated"
        self.rebuild()
        with self.assertRaisesRegex(ValueError, "unrelated task"):
            self.normalized()

    def test_rpc_response_id_mismatch_is_rejected(self):
        self.payloads[-1][1]["id"] = "other"
        self.rebuild()
        with self.assertRaisesRegex(ValueError, "ID mismatch"):
            self.normalized()

    def test_duplicate_json_key_is_rejected_and_failure_evidence_retained(self):
        path = self.wire / "000006" / "response.body.bin"
        raw = path.read_bytes().replace(b'"jsonrpc": "2.0"', b'"jsonrpc": "2.0", "jsonrpc": "2.0"')
        path.write_bytes(raw)
        self.change_exchange(6, lambda value: value.update(response_bytes=len(raw)))
        result = normalizer.export_wire(self.wire, self.output)
        self.assertEqual(result["status"], "failed")
        self.assertIn("Duplicate JSON key", result["error"])
        self.assertTrue((self.output / "plan.json").exists())
        self.assertEqual((self.output / "wire/000006/response.body.bin").read_bytes(), raw)

    def test_incomplete_exchange_and_message_only_results_remain_partial(self):
        self.change_exchange(6, lambda value: value.update(response_body_complete=False))
        result = self.normalized()
        self.assertFalse(result["normalization_complete"])
        self.assertEqual(result["unsupported_sequences"], [6])
        self.rebuild()
        self.payloads[-1][1]["result"] = {"message": {"messageId": "bare", "role": "ROLE_AGENT", "parts": [{"text": "A legal message."}]}}
        self.rebuild()
        self.assertFalse(self.normalized()["normalization_complete"])

    def test_jsonrpc_error_is_retained_without_task_success_inference(self):
        self.payloads[-1] = (self.rpc("GetTask", {"id": "task"}, 5), {"jsonrpc": "2.0", "id": 5, "error": {"code": -32001, "message": "missing task"}}, "POST", "/")
        self.rebuild()
        result = self.normalized()
        self.assertEqual(result["records"][-1]["outcome"], "jsonrpc_error")
        self.assertEqual(result["graded_task_outcomes"], 0)

    def test_falsey_invalid_metadata_and_artifacts_are_rejected(self):
        self.payloads[-1][1]["result"]["artifacts"] = False
        self.rebuild()
        with self.assertRaisesRegex(ValueError, "artifacts must"):
            self.normalized()

    def test_unbound_task_is_explicitly_unsupported(self):
        self.payloads[-1][1]["result"].pop("contextId")
        self.rebuild()
        result = self.normalized()
        self.assertFalse(result["normalization_complete"])
        self.assertEqual(result["records"][-1]["outcome"], "unbound_task_result")

    def test_body_counter_mismatch_is_rejected(self):
        self.change_exchange(6, lambda value: value.update(response_bytes=value["response_bytes"] + 1))
        with self.assertRaisesRegex(ValueError, "byte-count mismatch"):
            self.normalized()

    def test_export_is_readonly_and_existing_output_is_refused(self):
        before = self.raw()
        result = normalizer.export_wire(self.wire, self.output)
        self.assertEqual(result["status"], "passed")
        self.assertTrue(result["source_unchanged"])
        self.assertTrue(result["captured_files_unchanged"])
        self.assertEqual(self.raw(), before)
        hashes = {p.relative_to(self.output): hashlib.sha256(p.read_bytes()).hexdigest() for p in self.output.rglob("*") if p.is_file()}
        with self.assertRaises(ValueError):
            normalizer.export_wire(self.wire, self.output)
        self.assertEqual(hashes, {p.relative_to(self.output): hashlib.sha256(p.read_bytes()).hexdigest() for p in self.output.rglob("*") if p.is_file()})

    def test_source_mutation_during_export_invalidates_receipt(self):
        original = normalizer.normalize
        def mutate(raw):
            result = original(raw)
            path = self.wire / "000006" / "response.body.bin"
            path.write_bytes(path.read_bytes() + b" ")
            return result
        with patch.object(normalizer, "normalize", mutate):
            result = normalizer.export_wire(self.wire, self.output)
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["source_unchanged"])


if __name__ == "__main__":
    unittest.main()
