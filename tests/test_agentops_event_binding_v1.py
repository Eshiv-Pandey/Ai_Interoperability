"""Synthetic export-shape fixtures; no archive, SDK, application or model runs."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from interoperability import agentops_event_binding_v1 as binding
from interoperability import agentops_raw_events_v1 as raw_helper


def encoded(value):
    return json.dumps(value, sort_keys=True, allow_nan=False).encode("utf-8")


class EventBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.raw_root, self.public_root = self.base / "raw", self.base / "public"
        self.raw_root.mkdir(); self.public_root.mkdir()
        self.context, self.raw_context = "public-context", "public-context"
        # Explicit recorded metadata binds a differently named session and user.
        self.app, self.user, self.session = "recorded-app", "recorded-user", "recorded-session"
        self.task, self.invocation = "recorded-task", "invocation-one"
        self.metadata_user = self.user
        self.artifact_invocation = self.invocation
        action = {"id": "action-call", "name": "restart_service", "args": {"name": "inventory"}}
        confirmation = {"id": "confirmation-call", "name": "adk_request_confirmation", "args": {
            "originalFunctionCall": action, "toolConfirmation": {"confirmed": False, "hint": "fixture approval"}}}
        approval = {"id": "confirmation-call", "name": "adk_request_confirmation", "response": {
            "confirmed": True, "payload": {"rationale": "fixture-only rationale"}}}
        self.functions = [
            ("function_call", action, "agent"),
            ("function_response", {"id": "action-call", "name": "restart_service", "response": {"error": "confirmation required"}}, "agent"),
            ("function_call", confirmation, "agent"),
            ("function_response", approval, "user"),
            ("function_response", {"id": "action-call", "name": "restart_service", "response": {
                "result": "fixture response only", "audit": {"id": 1, "schema_version": 1, "target": "inventory"}}}, "agent"),
        ]
        self.extra_raw = []
        self.partial = False
        self.write_fixture()

    def write(self, root, name, content):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def seal(self, root, receipt):
        receipt = deepcopy(receipt)
        receipt["files"] = [{"path": p.relative_to(root).as_posix(), **binding._digest(p.read_bytes())}
                            for p in sorted(root.rglob("*")) if p.is_file() and p.name != "result.json"]
        self.write(root, "result.json", encoded(receipt))

    def reseal(self, root):
        self.seal(root, json.loads((root / "result.json").read_bytes()))

    def write_fixture(self):
        sources = b"Synthetic exporter-format source fixture, not original SDK code.\n"
        row_events = []
        for index, (kind, value, author) in enumerate(self.functions + self.extra_raw):
            event = {"id": f"event-{index}", "invocation_id": self.invocation, "timestamp": float(index + 1),
                     "author": author, "content": {"role": "model" if kind == "function_call" else "user", "parts": [{kind: deepcopy(value)}]}}
            row_events.append({"sqlite_rowid": index + 1, "id": event["id"], "app_name": self.app, "user_id": self.user,
                "session_id": self.session, "invocation_id": self.invocation, "timestamp": f"fixture-time-{index}", "event_data": event})
        metadata = {"adk_app_name": self.app, "adk_user_id": self.metadata_user, "adk_session_id": self.session}
        decoded = {
            "adk_internal_metadata": [{"sqlite_rowid": 1, "key": "fixture-version", "value": "fixture"}],
            "sessions": [{"sqlite_rowid": 1, "app_name": self.app, "user_id": self.user, "id": self.session,
                          "state": {}, "create_time": "fixture-create", "update_time": "fixture-update"}],
            "app_states": [{"sqlite_rowid": 1, "app_name": self.app, "state": {}, "update_time": "fixture-update"}],
            "user_states": [{"sqlite_rowid": 1, "app_name": self.app, "user_id": self.user, "state": {}, "update_time": "fixture-update"}],
            "events": row_events,
            "tasks": [{"sqlite_rowid": 1, "id": self.task, "context_id": self.raw_context, "kind": "task", "owner": "",
                       "last_updated": "fixture-update", "status": {"state": "completed"}, "artifacts": [], "history": [],
                       "protocol_version": "1.0", "metadata": metadata}],
        }
        tables = deepcopy(decoded)
        for table, fields in raw_helper.JSON_COLUMNS.items():
            for row in tables[table]:
                for field in fields:
                    if row[field] is not None:
                        row[field] = json.dumps(row[field], sort_keys=True)
        raw_observations = [observation for row in row_events for observation in raw_helper._project_event(row, row["event_data"])]
        database = b"SQLite format 3\x00Synthetic source-copy fixture; checker does not execute SQLite."
        raw_plan = {"schema_version": "agentops-raw-event-export-plan/1", "exporter_sha256": binding._digest(sources)["sha256"]}
        raw_files = {"plan.json": encoded(raw_plan), "exporter.py": sources, "input/runtime.db": database,
                     "raw-tables.json": encoded(tables), "decoded-tables.json": encoded(decoded),
                     "function-observations.json": encoded(raw_observations), "schema.json": encoded([]), "ordering.json": encoded({})}
        for name, content in raw_files.items():
            self.write(self.raw_root, name, content)
        raw_receipt = {"schema_version": "agentops-raw-event-export/1", "status": "passed", "source_unchanged": True,
            "captured_files_unchanged": True, "application_requests": 0, "model_calls": 0, "graded_task_outcomes": 0,
            "causal_order_proven": False, "complete_event_stream_proven": False, "database": binding._digest(database),
            "events": len(row_events), "table_rows": {key: len(rows) for key, rows in tables.items()},
            "function_calls": sum(row[0] == "function_call" for row in self.functions + self.extra_raw),
            "function_responses": sum(row[0] == "function_response" for row in self.functions + self.extra_raw)}
        self.seal(self.raw_root, raw_receipt)
        artifacts, messages, observations = [], [], []
        for index, (kind, value, author) in enumerate(self.functions):
            payload = deepcopy(value)
            if type(payload.get("response", {}).get("audit")) is dict:
                for field in ("id", "schema_version"):
                    payload["response"]["audit"][field] = float(payload["response"]["audit"][field])
            part = {"data": payload, "metadata": {"adk_type": kind}}
            is_artifact = index in {0, 1, 4}
            if is_artifact:
                container = {"artifactId": f"artifact-{index}", "metadata": {"adk_event_id": f"event-{index}",
                    "adk_invocation_id": self.artifact_invocation, "adk_author": author}, "parts": [part]}
                artifacts.append(container)
                identity, namespace, location = f"event-{index}", "artifact_event", "artifact"
            else:
                container = {"messageId": f"message-{index}", "role": "ROLE_USER" if author == "user" else "ROLE_AGENT", "parts": [part]}
                messages.append(container)
                identity, namespace, location = f"message-{index}", "message", "history"
            rep = {"capture_sequence": 1, "location": location, "part": part,
                   "container": {key: item for key, item in container.items() if key != "parts"}}
            reps = [rep]
            if index == 3:
                reps.append({**deepcopy(rep), "location": "request"})
            observations.append({"namespace": namespace, "identity": identity, "part_index": 0,
                "adk_event_id": identity if is_artifact else None, "adk_type": kind, "function_id": payload.get("id"),
                "function_identity_complete": type(payload.get("id")) is str and bool(payload["id"]),
                "part": part, "container": rep["container"], "representations": reps,
                "observed_in_sequences": [1] * len(reps), "first_capture_sequence": 1,
                "task_id": self.task, "context_id": self.context, "protocol_version_header": "1.0"})
        task = {"id": self.task, "contextId": self.context, "status": {"state": "completed"}, "artifacts": artifacts, "history": messages}
        request = {"jsonrpc": "2.0", "id": "rpc", "method": "SendMessage", "params": {"message": deepcopy(messages[1])}}
        response = {"jsonrpc": "2.0", "id": "rpc", "result": {"task": task}}
        exchange = {"schema_version": "agentops-asgi-exchange/1", "sequence": 1, "method": "POST", "path": "/",
            "request_headers": [["A2A-Version", "1.0"]], "response_status": 200,
            "request_body_complete": True, "response_body_complete": True,
            "request_bytes": len(encoded(request)), "response_bytes": len(encoded(response)),
            "started_at_utc": "2026-10-29T00:00:00+00:00", "finished_at_utc": "2026-10-29T00:00:01+00:00"}
        record = {"capture_sequence": 1, "outcome": "task", "task_shape": "wrapped_task", "state": "completed",
            "task": task, "task_id": self.task, "context_id": self.context, "request": request, "response": response,
            "rpc_method": "SendMessage", "method": "POST", "path": "/", "http_status": 200, "protocol_version_header": "1.0",
            "started_at_utc": exchange["started_at_utc"], "finished_at_utc": exchange["finished_at_utc"],
            "request_body": binding._digest(encoded(request)), "response_body": binding._digest(encoded(response))}
        view = {"schema_version": "agentops-public-observations/1", "normalization_complete": not self.partial,
            "unsupported_sequences": [1] if self.partial else [], "task_context_associations": {self.task: self.context},
            "observations": observations, "messages": messages, "records": [record]}
        public_files = {"plan.json": encoded({"schema_version": "agentops-public-event-export-plan/1",
            "exporter_sha256": binding._digest(b"synthetic public source")["sha256"], "helper_sha256": binding._digest(sources)["sha256"]}),
            "source/agentops_public_events_v1.py": b"synthetic public source", "source/agentops_raw_events_v1.py": sources,
            "observations.json": encoded(view), "wire/000001/request.body.bin": encoded(request),
            "wire/000001/response.body.bin": encoded(response), "wire/000001/exchange.json": encoded(exchange),
            "wire/000001/before.snapshot.json": encoded({}), "wire/000001/after.snapshot.json": encoded({})}
        for name, content in public_files.items():
            self.write(self.public_root, name, content)
        public_receipt = {"schema_version": "agentops-public-event-export/1", "status": "partial" if self.partial else "passed",
            "source_unchanged": True, "captured_files_unchanged": True, "application_requests": 0, "model_calls": 0,
            "graded_task_outcomes": 0, "causal_order_proven": False, "complete_event_stream_proven": False,
            "normalization_complete": not self.partial, "unsupported_sequences": [1] if self.partial else [],
            "capture_exchanges": 1, "unique_parts": len(observations), "function_calls": 2, "function_responses": 3}
        self.seal(self.public_root, public_receipt)

    def test_two_response_phases_and_metadata_gaps_are_preserved(self):
        result = binding.compare(self.raw_root, self.public_root)
        self.assertEqual((result["status"], result["verified_function_pairs"]), ("passed", 5))
        self.assertEqual((result["artifact_recorded_identity_pairs"], result["message_payload_only_pairs"]), (3, 2))
        responses = [pair for pair in result["pairs"] if pair["function_id"] == "action-call" and pair["kind"] == "function_response"]
        self.assertEqual({pair["matched_raw_event_id"] for pair in responses}, {"event-1", "event-4"})
        messages = [pair for pair in result["pairs"] if pair["public_namespace"] == "message"]
        self.assertTrue(all(pair["public_adk_event_id"] is None and pair["event_identity_proven"] is False for pair in messages))
        self.assertEqual(result["task_session_bindings"][self.task]["session_id"], self.session)
        self.assertEqual(result["task_session_bindings"][self.task]["user_id"], "recorded-user")
        for claim in ("causal_order_proven", "client_receipt_proven", "complete_event_stream_proven", "source_authenticity_proven"):
            self.assertIs(result[claim], False)

    def test_ambiguous_message_match_is_unresolved(self):
        self.extra_raw.append(deepcopy(self.functions[2])); self.write_fixture()
        result = binding.compare(self.raw_root, self.public_root)
        self.assertEqual(result["status"], "unresolved")
        self.assertTrue(any(item["reason"] == "ambiguous_raw_match" for item in result["unresolved"]))

    def test_missing_function_id_and_partial_export_are_unresolved(self):
        self.functions[2][1]["id"] = None; self.partial = True; self.write_fixture()
        result = binding.compare(self.raw_root, self.public_root)
        self.assertEqual(result["status"], "unresolved")
        reasons = {item["reason"] for item in result["unresolved"]}
        self.assertTrue({"partial_input_export", "missing_public_function_id"} <= reasons)

    def test_explicit_task_context_mismatch_is_rejected(self):
        self.raw_context = "different-context"; self.write_fixture()
        with self.assertRaisesRegex(ValueError, "task context"):
            binding.compare(self.raw_root, self.public_root)

    def test_missing_explicit_session_binding_is_unresolved_without_guessing(self):
        self.metadata_user = "A2A_USER_" + self.context; self.write_fixture()
        result = binding.compare(self.raw_root, self.public_root)
        self.assertEqual(result["status"], "unresolved")
        self.assertTrue(any(item["reason"] == "missing_recorded_session" for item in result["unresolved"]))

    def test_wrong_artifact_invocation_is_rejected(self):
        self.artifact_invocation = "different-invocation"; self.write_fixture()
        with self.assertRaisesRegex(ValueError, "Artifact recorded"):
            binding.compare(self.raw_root, self.public_root)

    def test_resealed_outcome_hiding_and_record_omission_are_rejected(self):
        path = self.public_root / "observations.json"
        view = json.loads(path.read_bytes())
        view["records"][0]["outcome"] = "jsonrpc_error"
        view["observations"] = []; view["task_context_associations"] = {}
        path.write_bytes(encoded(view))
        receipt = json.loads((self.public_root / "result.json").read_bytes())
        receipt.update(unique_parts=0, function_calls=0, function_responses=0)
        self.seal(self.public_root, receipt)
        with self.assertRaisesRegex(ValueError, "classification"):
            binding.compare(self.raw_root, self.public_root)
        self.write_fixture()
        view = json.loads(path.read_bytes()); view["records"] = []; view["observations"] = []; view["task_context_associations"] = {}
        path.write_bytes(encoded(view))
        receipt = json.loads((self.public_root / "result.json").read_bytes())
        receipt.update(capture_exchanges=0, unique_parts=0, function_calls=0, function_responses=0)
        self.seal(self.public_root, receipt)
        with self.assertRaisesRegex(ValueError, "omit copied wire"):
            binding.compare(self.raw_root, self.public_root)

    def test_fake_profile_and_duplicate_source_representation_are_rejected(self):
        path = self.public_root / "observations.json"
        view = json.loads(path.read_bytes())
        view["observations"][0]["protocol_version_header"] = "forged-profile"
        path.write_bytes(encoded(view)); self.reseal(self.public_root)
        with self.assertRaisesRegex(ValueError, "protocol profile"):
            binding.compare(self.raw_root, self.public_root)
        self.write_fixture()
        view = json.loads(path.read_bytes()); item = view["observations"][0]
        item["representations"].append(deepcopy(item["representations"][0])); item["observed_in_sequences"].append(1)
        path.write_bytes(encoded(view)); self.reseal(self.public_root)
        with self.assertRaisesRegex(ValueError, "source origin is reused"):
            binding.compare(self.raw_root, self.public_root)

    def test_optional_raw_scope_and_timestamp_contradictions_are_rejected(self):
        for field, value, pattern in (("session_id", "wrong-session", "optional scope"), ("timestamp", True, "timestamp")):
            self.write_fixture()
            raw_path, decoded_path = self.raw_root / "raw-tables.json", self.raw_root / "decoded-tables.json"
            raw, decoded = json.loads(raw_path.read_bytes()), json.loads(decoded_path.read_bytes())
            event = decoded["events"][0]["event_data"]; event[field] = value
            raw["events"][0]["event_data"] = json.dumps(event)
            raw_path.write_bytes(encoded(raw)); decoded_path.write_bytes(encoded(decoded)); self.reseal(self.raw_root)
            with self.assertRaisesRegex(ValueError, pattern):
                binding.compare(self.raw_root, self.public_root)

    def test_message_copied_metadata_cannot_be_hidden_by_payload_only_matching(self):
        path = self.public_root / "observations.json"
        view = json.loads(path.read_bytes()); record = view["records"][0]
        metadata = {"adk_event_id": "wrong-event", "adk_invocation_id": "wrong-invocation", "adk_author": "wrong-author"}
        record["response"]["result"]["task"]["history"][0]["metadata"] = metadata
        record["task"] = deepcopy(record["response"]["result"]["task"])
        item = view["observations"][2]
        item["container"]["metadata"] = metadata
        for rep in item["representations"]:
            rep["container"]["metadata"] = metadata
        body = encoded(record["response"])
        self.write(self.public_root, "wire/000001/response.body.bin", body)
        exchange = json.loads((self.public_root / "wire/000001/exchange.json").read_bytes())
        exchange["response_bytes"] = len(body)
        self.write(self.public_root, "wire/000001/exchange.json", encoded(exchange))
        record["response_body"] = binding._digest(body)
        path.write_bytes(encoded(view)); self.reseal(self.public_root)
        with self.assertRaisesRegex(ValueError, "Message explicitly declares"):
            binding.compare(self.raw_root, self.public_root)

    def test_manifest_tamper_and_extra_allocation_member_are_rejected(self):
        path = self.raw_root / "decoded-tables.json"
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "manifest byte/hash"):
            binding.compare(self.raw_root, self.public_root)
        self.reseal(self.raw_root)
        (self.raw_root / "extra.txt").write_text("not manifest-listed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "membership"):
            binding.compare(self.raw_root, self.public_root)

    def test_duplicate_json_and_forged_raw_projection_are_rejected(self):
        path = self.raw_root / "plan.json"
        path.write_bytes(b'{"schema_version":"x","schema_version":"agentops-raw-event-export-plan/1"}')
        self.reseal(self.raw_root)
        with self.assertRaisesRegex(ValueError, "Duplicate JSON"):
            binding.compare(self.raw_root, self.public_root)
        self.write_fixture()
        path = self.raw_root / "function-observations.json"
        value = json.loads(path.read_bytes()); value[0]["function"]["args"]["name"] = "wrong"
        path.write_bytes(encoded(value)); self.reseal(self.raw_root)
        with self.assertRaisesRegex(ValueError, "Raw function projection"):
            binding.compare(self.raw_root, self.public_root)

    def test_only_declared_audit_integer_fields_accept_integral_floats(self):
        original = {"id": "call", "name": "tool", "response": {"audit": {"id": 1, "schema_version": 1}, "other": 2}}
        public = deepcopy(original); public["response"]["audit"]["id"] = 1.0
        self.assertTrue(binding._function_same(original, public, "function_response"))
        for bad in (True, -1, 1.5, 2**53, float("inf")):
            public = deepcopy(original); public["response"]["audit"]["id"] = bad
            self.assertFalse(binding._function_same(original, public, "function_response"))
        public = deepcopy(original); public["response"]["other"] = 2.0
        self.assertFalse(binding._function_same(original, public, "function_response"))
        public = deepcopy(original); public["response"]["audit"]["id"] = True
        self.assertFalse(binding._function_same(original, public, "function_response"))

    def test_compare_detects_source_mutation(self):
        original = binding._compare_bytes
        def change(raw, public):
            result = original(raw, public)
            (self.raw_root / "plan.json").write_bytes(b"changed after comparison")
            return result
        with patch.object(binding, "_compare_bytes", change):
            with self.assertRaisesRegex(ValueError, "changed during comparison"):
                binding.compare(self.raw_root, self.public_root)

    def test_capture_copies_inputs_exclusively_and_retains_mutation_failure(self):
        output = self.base / "capture"
        result = binding.export_comparison(self.raw_root, self.public_root, output)
        self.assertEqual(result["status"], "passed")
        self.assertEqual((output / "inputs/raw/result.json").read_bytes(), (self.raw_root / "result.json").read_bytes())
        self.assertEqual((output / "inputs/public/observations.json").read_bytes(), (self.public_root / "observations.json").read_bytes())
        with self.assertRaisesRegex(ValueError, "existing output"):
            binding.export_comparison(self.raw_root, self.public_root, output)
        original = binding._compare_bytes
        def change(raw, public):
            report = original(raw, public)
            (self.public_root / "plan.json").write_bytes(b"changed after comparison")
            return report
        with patch.object(binding, "_compare_bytes", change):
            failed = binding.export_comparison(self.raw_root, self.public_root, self.base / "failed")
        self.assertEqual(failed["status"], "failed")
        self.assertIs(failed["inputs_unchanged"], False)
        self.assertTrue((self.base / "failed/result.json").exists())


if __name__ == "__main__":
    unittest.main()
