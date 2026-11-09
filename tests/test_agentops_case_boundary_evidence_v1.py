"""Synthetic retained ASGI/client/store fixtures, never an original runtime."""
from contextlib import closing
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import py_compile
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from interoperability import agentops_case_boundary_evidence_v1 as module
from interoperability import upstream_agentops_client_v1 as client
from interoperability.agentops_memory_evidence_v1 import snapshot_memory


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()


def identity(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="SYNTHETIC-boundaries-")
        self.addCleanup(temporary.cleanup)
        self.instance = Path(temporary.name) / "SYNTHETIC-instance"
        self.instance.mkdir()

    def write(self, relative, value):
        path = self.instance / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value if type(value) is bytes else encoded(value))

    def build(self, turns=1, terminal="completed", source_case=None):
        self.case = {"eval_set_id": "agentops_agent_core", "eval_id": "SYNTHETIC-boundary-case", "creation_timestamp": 0.0,
                     "session_input": {"app_name": "agentops_agent", "user_id": "eval", "state": {}},
                     "conversation": [{"invocation_id": f"SYNTHETIC-source-{index}", "creation_timestamp": 0.0,
                                       "user_content": {"role": "user", "parts": [{"text": f"SYNTHETIC request {index}"}]}}
                                      for index in range(1, turns + 1)]}
        if source_case is not None:
            self.case = deepcopy(source_case)
            turns = len(self.case["conversation"])
        context = "00000000-0000-4000-8000-000000000001"
        user = "A2A_USER_" + context
        policy = {"schema_version": client.SESSION_SCHEMA, "context_id": context, "source_session_input": self.case["session_input"],
                  "native_app_name_expected": "agentops-agent", "native_user_id_expected_from_source": user,
                  "native_session_id_expected_from_source": context, "mapping_basis": "SYNTHETIC source-mapping fixture"}
        retained = self.instance / "retained-state"
        retained.mkdir()
        with closing(sqlite3.connect(retained / "incidents.db")) as connection, connection:
            connection.execute("CREATE TABLE services(name TEXT PRIMARY KEY,description TEXT NOT NULL,status TEXT NOT NULL,owner TEXT NOT NULL)")
            connection.execute("CREATE TABLE incidents(id TEXT PRIMARY KEY,service TEXT NOT NULL,title TEXT NOT NULL,severity TEXT NOT NULL,status TEXT NOT NULL,runbook TEXT NOT NULL,opened_at TEXT NOT NULL,resolved_at TEXT,summary TEXT NOT NULL)")
            connection.execute("CREATE TABLE audit_log(id INTEGER PRIMARY KEY AUTOINCREMENT,schema_version INTEGER NOT NULL DEFAULT 1,ts TEXT NOT NULL,actor TEXT NOT NULL,approved_by TEXT NOT NULL,rationale TEXT NOT NULL,context_summary TEXT NOT NULL,session_id TEXT NOT NULL,invocation_id TEXT NOT NULL,action TEXT NOT NULL,target TEXT NOT NULL,detail TEXT NOT NULL)")
            connection.execute("INSERT INTO services VALUES('inventory','SYNTHETIC service','down','SYNTHETIC owner')")
        business, _ = module._closed_business(retained / "incidents.db", retained)
        business["path"], business["path_base"] = "state/incidents.db", "run"
        (self.instance / "service/state").mkdir(parents=True)
        memory = snapshot_memory(self.instance / "service/state/memory.db", observation_mode="live")
        self.records, turn_records = [], []
        self.add_server(1, "GET", "/healthz", b"", {"status": "ready"}, business, memory)
        self.add_exchange("GET", "/.well-known/agent-card.json", b"", {"SYNTHETIC_card": True}, business, memory)
        for index, source in enumerate(self.case["conversation"], 1):
            message_id, rpc_id, task_id = f"SYNTHETIC-message-{index}", f"SYNTHETIC-rpc-{index}", f"SYNTHETIC-task-{index}"
            request = {"jsonrpc": "2.0", "id": rpc_id, "method": "SendMessage", "params": {"message": {
                "messageId": message_id, "role": "ROLE_USER", "contextId": context,
                "parts": [{"text": part["text"]} for part in source["user_content"]["parts"]]}}}
            working = {"id": task_id, "contextId": context, "status": {"state": "working"}, "history": [], "artifacts": []}
            send = self.add_exchange("POST", "/", encoded(request), {"jsonrpc": "2.0", "id": rpc_id, "result": working}, business, memory)
            poll_rpc = f"SYNTHETIC-poll-{index}"
            request = {"jsonrpc": "2.0", "id": poll_rpc, "method": "GetTask", "params": {"id": task_id, "historyLength": 100}}
            final_state = terminal if index == turns else "completed"
            final = {**working, "status": {"state": final_state}}
            poll = self.add_exchange("POST", "/", encoded(request), {"jsonrpc": "2.0", "id": poll_rpc, "result": final}, business, memory)
            turn_records.append({"turn_index": index - 1, "source_invocation_id": source["invocation_id"],
                                 "source_user_content": source["user_content"], "send_capture_sequence": send,
                                 "message_id": message_id, "send_rpc_id": rpc_id, "task_id": task_id, "observed_context_id": context,
                                 "status": "recorded", "final_state": final_state,
                                 "observations": [client._observation(working, "direct_task", "working", send),
                                                  client._observation(final, "direct_task", final_state, poll)]})
        self.write("client/input-case.json", self.case)
        self.write("client/session-policy.json", policy)
        self.write("client/plan.json", {"schema_version": "upstream-agentops-case-client-plan/1", "endpoint": "http://127.0.0.1:8765/",
                                       "prospective_context_id": context, "case_digest": identity(encoded(self.case)),
                                       "session_policy_digest": identity(encoded(policy))})
        self.report = {"schema_version": "upstream-agentops-case-client/1", "status": "recorded", "prospective_context_id": context,
                       "turns": turn_records, "turns_completed": sum(row["final_state"] == "completed" for row in turn_records),
                       "exchanges": self.records, "input_objects_unchanged": True, "application_source_unchanged": True,
                       "implementation_unchanged": True, "captured_files_unchanged": True}
        self.refresh_client_manifest()
        family = {"agentops_agent_core": "core", "agentops_agent_structured_report": "report", "agentops_incident_workflow": "workflow"}[self.case["eval_set_id"]]
        binding = {"family": family, "host": "127.0.0.1", "port": 8765, "SYNTHETIC_binding": True}
        scheduled = {"case": self.case, "key": self.case["eval_set_id"] + "/" + self.case["eval_id"],
                     "sample": 1, "family": family, "context_id": context}
        self.write("plan.json", {"schema_version": "upstream-agentops-native-runner/2", "binding": binding,
                                 "source_case": scheduled, "session_policy": policy})
        self.write("service/bootstrap.created.json", {"schema_version": "upstream-agentops-bootstrap/2", "status": "constructed_not_ready", "binding": binding})
        self.write("service/bootstrap.exit.json", {"schema_version": "upstream-agentops-bootstrap/2", "status": "stopped", "binding": binding,
                                                   "owned_stop_accepted": True, "original_serve_returned": True})
        self.instance_report = {"status": "recorded_without_benchmark_grade", "client": self.report,
                                **{key: scheduled[key] for key in ("key", "sample", "family", "context_id")},
                                "cleanup": {"returncode": 0, "forced": False, "active_processes": 0, "main_handle_signaled": True,
                                            "handles_closed": True, "authority_retained": False, "job_empty_observed": True, "members": [], "errors": []},
                                "observed_runtime_identity": {"user_id": user, "session_id": context, "context_id": context, "app_name": "agentops-agent"},
                                "retention": {"source_and_copy_unchanged": True, "files": {"incidents.db": identity((retained / "incidents.db").read_bytes())}}}
        self.write("result.json", self.instance_report)

    def refresh_client_manifest(self):
        folder = self.instance / "client"
        self.report["files"] = [{"path": path.relative_to(folder).as_posix(), **identity(path.read_bytes())}
                                for path in sorted(folder.rglob("*")) if path.is_file() and path.name != "result.json"]
        self.write("client/result.json", self.report)

    def add_server(self, number, method, path, request, response, business, memory):
        body = encoded(response)
        prefix = f"service/wire/{number:06d}/"
        self.write(prefix + "request.body.bin", request)
        self.write(prefix + "response.body.bin", body)
        self.write(prefix + "exchange.json", {"schema_version": "agentops-asgi-exchange/1", "sequence": number,
                   "method": method, "path": path, "query_string": "", "response_status": 200,
                   "request_body_complete": True, "response_body_complete": True, "request_bytes": len(request), "response_bytes": len(body),
                   "response_chunks": [{"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "more_body": False}]})
        for boundary in ("before", "after"):
            self.write(prefix + boundary + ".snapshot.json", {"database": business, "observed_at_utc": "2026-10-30T00:00:00Z", "monotonic_ns": number})
            self.write(prefix + boundary + ".memory.snapshot.json", memory)

    def add_exchange(self, method, path, body, response, business, memory):
        sequence = len(self.records) + 1
        response_body = encoded(response)
        headers = [["Content-Type", "application/json"], ["Content-Length", str(len(response_body))], ["Connection", "close"]]
        raw_response = ("HTTP/1.1 200 OK\r\n" + "".join(f"{name}: {value}\r\n" for name, value in headers) + "\r\n").encode() + response_body
        request_headers, prepared = self.prepared_request(method, path, body)
        payload = json.loads(body) if body else {}
        row = {"schema_version": "upstream-agentops-client-exchange/1", "sequence": sequence, "method": method, "path": path,
               "rpc_method": payload.get("method"), "request_rpc_id": payload.get("id"), "request_send_attempted": True,
               "request_fully_sent": True, "response_eof": True, "http_body_complete": True, "status": "received", "http_status": 200,
               "request_headers": request_headers, "request_digest": identity(prepared), "received_http_digest": identity(raw_response), "response_headers": headers, "envelope": response}
        self.records.append(row)
        prefix = f"client/wire/{sequence:06d}/"
        for name, raw in (("request.http.bin", prepared), ("request.body.bin", body), ("response.http.bin", raw_response), ("response.body.bin", response_body), ("exchange.json", row)):
            self.write(prefix + name, raw)
        self.add_server(sequence + 1, method, path, body, response, business, memory)
        return sequence

    def prepared_request(self, method, path, body):
        headers = [["Host", "127.0.0.1:8765"], ["Connection", "close"], ["Accept-Encoding", "identity"],
                   ["Accept", "application/json"], ["A2A-Version", "1.0"], ["Content-Length", str(len(body))]]
        if body:
            headers.append(["Content-Type", "application/json"])
        return headers, (f"{method} {path} HTTP/1.1\r\n" + "".join(f"{key}: {value}\r\n" for key, value in headers) + "\r\n").encode() + body

    def test_distinct_readiness_baseline_and_all_poll_boundaries_are_bound(self):
        self.build()
        before = {path.relative_to(self.instance).as_posix(): path.read_bytes() for path in self.instance.rglob("*") if path.is_file()}
        value = module.collect_case_boundaries(self.instance, self.case)
        self.assertEqual(value["startup"]["wire_sequence"], 1)
        self.assertEqual([row["stage"] for row in value["turns"][0]["samples"]], ["before", "in_progress", "in_progress", "terminal"])
        self.assertEqual(value["retained_close"]["memory"]["status"], "absent")
        self.assertFalse(value["source_closed_proven"])
        self.assertEqual(before, {path.relative_to(self.instance).as_posix(): path.read_bytes() for path in self.instance.rglob("*") if path.is_file()})

    def test_two_turns_keep_native_context_and_separate_state_boundaries(self):
        self.build(turns=2)
        value = module.collect_case_boundaries(self.instance, self.case)
        self.assertEqual([row["turn_index"] for row in value["turns"]], [1, 2])
        self.assertEqual(value["turns"][0]["native_session_id"], value["turns"][1]["native_session_id"])
        self.assertEqual(len(value["client_server_entity_bindings"]), 5)

    def test_input_required_is_recorded_without_inventing_approval_execution(self):
        self.build(terminal="input_required")
        value = module.collect_case_boundaries(self.instance, self.case)
        self.assertEqual(value["turns"][0]["terminal_public_state"], "input_required")
        self.assertFalse(value["full_task_grade_assigned"])

    def test_no_successful_readiness_cannot_manufacture_task_baseline(self):
        self.build()
        path = "service/wire/000001/exchange.json"
        row = json.loads((self.instance / path).read_bytes()); row["path"] = "/livez"
        self.write(path, row)
        with self.assertRaisesRegex(ValueError, "readiness baseline is missing"):
            module.collect_case_boundaries(self.instance, self.case)

    def test_foreign_response_entity_is_rejected(self):
        self.build()
        body = encoded({"SYNTHETIC": "FOREIGN RESPONSE"})
        self.write("service/wire/000003/response.body.bin", body)
        path = "service/wire/000003/exchange.json"
        row = json.loads((self.instance / path).read_bytes()); row["response_bytes"] = len(body)
        row["response_chunks"] = [{"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "more_body": False}]
        self.write(path, row)
        with self.assertRaisesRegex(ValueError, "client/server response entity differs"):
            module.collect_case_boundaries(self.instance, self.case)

    def test_noncanonical_manifest_numeric_descriptor_is_rejected(self):
        self.build()
        self.report["files"][0]["bytes"] = float(self.report["files"][0]["bytes"])
        self.write("client/result.json", self.report)
        self.instance_report["client"] = self.report; self.write("result.json", self.instance_report)
        with self.assertRaises(ValueError): module.collect_case_boundaries(self.instance, self.case)

    def test_wal_header_is_rejected_before_business_reader_connects(self):
        self.build()
        path = self.instance / "retained-state/incidents.db"
        raw = bytearray(path.read_bytes()); raw[18] = raw[19] = 2; path.write_bytes(raw)
        self.instance_report["retention"]["files"]["incidents.db"] = identity(bytes(raw)); self.write("result.json", self.instance_report)
        with self.assertRaisesRegex(ValueError, "rollback-mode"):
            module.collect_case_boundaries(self.instance, self.case)
        self.assertFalse(Path(str(path) + "-shm").exists())

    def test_boundary_input_mutation_is_rejected(self):
        self.build()
        original = module._closed_business
        def observed(database, retained):
            result = original(database, retained)
            (self.instance / "client/unrecorded-empty").mkdir()
            return result
        with patch.object(module, "_closed_business", side_effect=observed):
            with self.assertRaisesRegex(ValueError, "changed during collection"):
                module.collect_case_boundaries(self.instance, self.case)

    def test_resealed_actual_user_body_cannot_match_copied_source_labels(self):
        self.build()
        body = json.loads((self.instance / "client/wire/000002/request.body.bin").read_bytes())
        body["params"]["message"]["parts"][0]["text"] = "SYNTHETIC foreign prompt"
        raw = encoded(body)
        headers, prepared = self.prepared_request("POST", "/", raw)
        self.records[1]["request_headers"] = headers
        self.records[1]["request_digest"] = identity(prepared)
        self.write("client/wire/000002/request.body.bin", raw)
        self.write("client/wire/000002/request.http.bin", prepared)
        self.write("client/wire/000002/exchange.json", self.records[1])
        self.write("service/wire/000003/request.body.bin", raw)
        path = "service/wire/000003/exchange.json"
        row = json.loads((self.instance / path).read_bytes()); row["request_bytes"] = len(raw); self.write(path, row)
        self.refresh_client_manifest(); self.instance_report["client"] = self.report; self.write("result.json", self.instance_report)
        with self.assertRaisesRegex(ValueError, "actual source SendMessage body differs"):
            module.collect_case_boundaries(self.instance, self.case)

    def test_ambiguous_duplicate_server_request_is_rejected(self):
        self.build()
        source = self.instance / "service/wire/000003"
        for path in source.iterdir(): self.write("service/wire/000005/" + path.name, path.read_bytes())
        path = "service/wire/000005/exchange.json"
        row = json.loads((self.instance / path).read_bytes()); row["sequence"] = 5; self.write(path, row)
        with self.assertRaisesRegex(ValueError, "absent/ambiguous/out of order"):
            module.collect_case_boundaries(self.instance, self.case)

    def test_collector_payload_integrates_with_stronger_effect_checker(self):
        from interoperability.agentops_source_case_effects_v1 import assess_source_case_effects
        application = json.loads((ROOT / "runs/upstream-agentops-cases/v1/application/cases.json").read_bytes())["cases"][0]
        obligation = json.loads((ROOT / "docs/research/upstream-agentops-grading-obligations-v1.json").read_bytes())["case_obligations"][0]
        self.build(source_case=application)
        boundaries = module.collect_case_boundaries(self.instance, self.case)
        turn = boundaries["turns"][0]
        result = assess_source_case_effects(obligation, boundaries, expected_native_user_id=turn["native_user_id"],
                                           expected_native_session_id=turn["native_session_id"])
        self.assertFalse(result["full_task_grade_assigned"])
        self.assertEqual(result["business"]["status"], "consistent")
        self.assertEqual(result["memory_structure"]["status"], "consistent")

    def test_hashed_reader_bytes_ignore_stale_timestamp_bytecode(self):
        self.build()
        scripts = self.instance / "SYNTHETIC-reader/scripts"
        scripts.mkdir(parents=True)
        source = scripts / "agentops_native_probe_v2.py"
        source.write_text("def database_snapshot(*args): return {'SYNTHETIC': 'cache'}\n")
        stamp = source.stat().st_mtime
        cache = Path(py_compile.compile(str(source), doraise=True))
        cached = cache.read_bytes()
        source.write_text("def database_snapshot(*args): return {'SYNTHETIC': 'bytes'}\n")
        os.utime(source, (stamp, stamp))
        raw = source.read_bytes()
        retained = self.instance / "retained-state"
        with patch.object(module, "ROOT", scripts.parent):
            value, descriptor = module._closed_business(retained / "incidents.db", retained)
        self.assertEqual(value, {"SYNTHETIC": "bytes"})
        self.assertEqual(descriptor, identity(raw))
        self.assertEqual(cache.read_bytes(), cached)

    def test_bootstrap_family_cannot_relabel_core_source_case(self):
        self.build()
        for name in ("service/bootstrap.created.json", "service/bootstrap.exit.json", "plan.json"):
            row = json.loads((self.instance / name).read_bytes())
            row["binding"]["family"] = "report"
            self.write(name, row)
        with self.assertRaisesRegex(ValueError, "family/endpoint/bootstrap"):
            module.collect_case_boundaries(self.instance, self.case)

    def test_client_plan_endpoint_cannot_disagree_with_bootstrap(self):
        self.build()
        name = "client/plan.json"
        row = json.loads((self.instance / name).read_bytes())
        row["endpoint"] = "http://127.0.0.1:8766/"
        self.write(name, row); self.refresh_client_manifest()
        self.instance_report["client"] = self.report; self.write("result.json", self.instance_report)
        with self.assertRaisesRegex(ValueError, "client endpoint/context"):
            module.collect_case_boundaries(self.instance, self.case)

    def replace_response(self, sequence, response):
        body = encoded(response)
        row = self.records[sequence - 1]
        headers = [["Content-Type", "application/json"], ["Content-Length", str(len(body))], ["Connection", "close"]]
        raw = ("HTTP/1.1 200 OK\r\n" + "".join(f"{key}: {value}\r\n" for key, value in headers) + "\r\n").encode() + body
        row.update(envelope=response, response_headers=headers, received_http_digest=identity(raw))
        prefix = f"client/wire/{sequence:06d}/"
        for name, value in (("response.body.bin", body), ("response.http.bin", raw), ("exchange.json", row)):
            self.write(prefix + name, value)
        prefix = f"service/wire/{sequence + 1:06d}/"
        observed = json.loads((self.instance / (prefix + "exchange.json")).read_bytes())
        observed.update(response_bytes=len(body), response_chunks=[{**identity(body), "more_body": False}])
        self.write(prefix + "response.body.bin", body); self.write(prefix + "exchange.json", observed)

    def test_confirmation_pause_cannot_be_polled_into_later_completion(self):
        self.build()
        response = deepcopy(self.records[1]["envelope"])
        response["result"]["status"]["state"] = "input_required"
        self.replace_response(2, response)
        self.report["turns"][0]["observations"][0] = client._observation(response["result"], "direct_task", "input_required", 2)
        self.refresh_client_manifest(); self.instance_report["client"] = self.report; self.write("result.json", self.instance_report)
        with self.assertRaisesRegex(ValueError, "cannot poll after"):
            module.collect_case_boundaries(self.instance, self.case)

    def test_resealed_null_poll_rpc_identity_is_rejected(self):
        self.build()
        row = self.records[2]
        payload = json.loads((self.instance / "client/wire/000003/request.body.bin").read_bytes())
        payload["id"] = None
        body = encoded(payload); headers, prepared = self.prepared_request("POST", "/", body)
        row.update(request_rpc_id=None, request_headers=headers, request_digest=identity(prepared))
        for name, value in (("request.body.bin", body), ("request.http.bin", prepared), ("exchange.json", row)):
            self.write("client/wire/000003/" + name, value)
        observed = json.loads((self.instance / "service/wire/000004/exchange.json").read_bytes())
        observed["request_bytes"] = len(body)
        self.write("service/wire/000004/request.body.bin", body); self.write("service/wire/000004/exchange.json", observed)
        response = deepcopy(row["envelope"]); response["id"] = None
        self.replace_response(3, response)
        self.refresh_client_manifest(); self.instance_report["client"] = self.report; self.write("result.json", self.instance_report)
        with self.assertRaisesRegex(ValueError, "poll RPC identity"):
            module.collect_case_boundaries(self.instance, self.case)


if __name__ == "__main__":
    unittest.main()
