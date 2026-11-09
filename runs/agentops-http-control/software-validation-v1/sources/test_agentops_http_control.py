"""Authored wire evidence and malformed-input tests; no AgentOps execution."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch
import uuid

from scripts.agentops_http_bytes_v1 import decode_response, rpc_results
from scripts.check_agentops_effect_v2 import seed_snapshot
from scripts.check_agentops_http_v1 import BOUNDARIES, LABELS, check

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("authored_agentops_profile", ROOT / "tests/test_agentops_effect_checker.py")
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)


def encoded(value):
    return json.dumps(value, separators=(",", ":"), allow_nan=False).encode()


def response(body, content_type="application/json", chunked=False):
    prefix = f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nConnection: close\r\n".encode()
    if chunked:
        middle = len(body) // 2
        chunks = [body[:middle], body[middle:]]
        return prefix + b"Transfer-Encoding: chunked\r\n\r\n" + b"".join(
            f"{len(chunk):x}\r\n".encode() + chunk + b"\r\n" for chunk in chunks) + b"0\r\n\r\n"
    return prefix + f"Content-Length: {len(body)}\r\n\r\n".encode() + body


def authored_files(seed):
    profile = fixtures.authored_profile(seed)
    port = 18761
    initial = profile["observations"][1]["results"]
    completed = profile["observations"][3]["results"]
    card = {"version": "0.11.0", "capabilities": {"streaming": True},
            "supportedInterfaces": [{"url": f"http://127.0.0.1:{port}/", "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}],
            "skills": [{"id": value} for value in ("incident-triage", "remediation")],
            "defaultInputModes": ["text/plain"], "defaultOutputModes": ["text/plain"]}
    payloads = {"card": None, "start": profile["observations"][0]["payload"],
                "resume": profile["observations"][2]["payload"]}
    replies = {"card": card}
    for label, state in (("get-pending", "input-required"), ("get-completed", "completed")):
        payloads[label] = {"jsonrpc": "2.0", "id": label, "method": "tasks/get", "params": {"id": "authored-task"}}
        replies[label] = {"jsonrpc": "2.0", "id": label, "result": {"kind": "task", "id": "authored-task",
                              "contextId": "authored-context", "status": {"state": state}}}
    files = {"plan.json": encoded({"schema_version": "agentops-http-plan/1", "sequence": list(LABELS), "port": port})}
    for index, label in enumerate(LABELS):
        method, target = ("GET", "/.well-known/agent-card.json") if label == "card" else ("POST", "/")
        body = b"" if label == "card" else encoded(payloads[label])
        headers = [f"{method} {target} HTTP/1.1", f"Host: 127.0.0.1:{port}", "Connection: close",
                   "Accept-Encoding: identity", "Accept: application/json, text/event-stream", f"Content-Length: {len(body)}"]
        if label != "card":
            headers.append("Content-Type: application/json")
        files[label + ".request.bin"] = ("\r\n".join(headers) + "\r\n\r\n").encode() + body
        if label in {"start", "resume"}:
            events = initial if label == "start" else completed
            body = b"".join(b"data: " + encoded({"jsonrpc": "2.0", "id": "approval-" + label, "result": row})
                            + b"\r\n\r\n" for row in events)
            files[label + ".response.bin"] = response(body, "text/event-stream; charset=utf-8", chunked=True)
        else:
            files[label + ".response.bin"] = response(encoded(replies[label]))
        files[label + ".exchange.json"] = encoded({"label": label, "method": method, "path": target, "port": port,
            "request_fully_sent": True, "response_eof": True, "status": "captured",
            "started_at_utc": f"2026-10-26T00:00:{index * 3 + 1:02d}+00:00",
            "finished_at_utc": f"2026-10-26T00:00:{index * 3 + 2:02d}+00:00"})
    rows = []
    for index, label in enumerate(BOUNDARIES):
        db = copy.deepcopy(profile["observations"][0 if index < 4 else 3]["database"])
        db["path"] = "state/incidents.db"
        if index >= 4:
            db["tables"]["audit_log"][0]["ts"] = "2026-10-26T00:00:10Z"
        row = {"label": label, "database": db, "monotonic_ns": index + 1,
               "observed_at_utc": f"2026-10-26T00:00:{index * 3:02d}+00:00"}
        rows.append(row)
        files[label + ".snapshot.json"] = encoded(row)
    files["boundaries.json"] = encoded(rows)
    files["service-result.json"] = encoded({"schema_version": "agentops-http-service/1", "status": "stopped",
        "network_errors": [], "model_double_calls": 2, "seen_contexts": profile["final_test_locals"]["seen_contexts"]})
    return files


class WireBytesTests(unittest.TestCase):
    def test_chunked_and_content_length_roundtrip(self):
        for chunked in (True, False):
            self.assertEqual(decode_response(response(b'{"actual":"bytes"}', chunked=chunked))[2], b'{"actual":"bytes"}')

    def test_bad_transport_is_rejected(self):
        valid = response(b"data", chunked=True)
        cases = [valid[:-1], valid + b"extra", valid.replace(b"4\r\n", b"z\r\n"),
                 response(b"data")[:-1], response(b"data") + b"extra",
                 valid.replace(b"Transfer-Encoding: chunked", b"Transfer-Encoding: chunked\r\nContent-Length: 4"),
                 response(b"data").replace(b"Content-Length: 4", b"Content-Length: 4\r\nContent-Length: 4")]
        # Split chunks are size 2, not 4.
        cases[2] = valid.replace(b"2\r\n", b"z\r\n", 1)
        for raw in cases:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                decode_response(raw)

    def test_sse_envelopes_and_incomplete_events(self):
        raw = b': heartbeat\r\ndata: {"jsonrpc":"2.0",\r\ndata: "id":"x","result":{"ok":true}}\r\n\r\n'
        self.assertEqual(rpc_results(raw, "x"), [{"ok": True}])
        cases = [raw[:-2], raw.replace(b'"id":"x"', b'"id":"y"'),
                 raw.replace(b'"ok":true', b'"ok":true,"ok":false'),
                 raw.replace(b'"ok":true', b'"ok":NaN'),
                 raw.replace(b'"result":', b'"error":')]
        for value in cases:
            with self.subTest(raw=value), self.assertRaises(ValueError):
                rpc_results(value, "x")


class WireSemanticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed = seed_snapshot(ROOT / "external/agentops-c806b7f1/agents/data/incidents.db")
        cls.base = ROOT / "tmp" / ("authored-agentops-http-" + uuid.uuid4().hex)
        cls.base.mkdir(parents=True)
        (cls.base / "AUTHORED-TEST-DATA.txt").write_text("Constructed checker fixtures. No AgentOps execution.\n")

    def materialize(self, files):
        target = self.base / uuid.uuid4().hex
        target.mkdir()
        for name, raw in files.items():
            (target / name).write_bytes(raw)
        return target

    def test_authored_profile_passes(self):
        report = check(self.materialize(authored_files(self.seed)), self.seed)
        self.assertEqual(report["status"], "passed")
        self.assertFalse(report["bridge_qualification"])
        self.assertIsNone(report["request_version_header"])

    def test_adverse_wire_and_effect_evidence_is_rejected(self):
        good = authored_files(self.seed)
        cases = []
        for name, raw in (("resume.response.bin", good["resume.response.bin"][:-5]),
                          ("get-completed.response.bin", response(encoded({"jsonrpc": "2.0", "id": "get-completed", "error": {"code": -1}}))),
                          ("start.request.bin", good["start.request.bin"].replace(b"Connection: close", b"A2A-Version: 1.0\r\nConnection: close"))):
            files = dict(good)
            files[name] = raw
            cases.append((name, files))
        for key, value in (("model_double_calls", 3), ("network_errors", [{"event": "socket.connect"}]), ("status", "failed")):
            files = dict(good)
            service = json.loads(files["service-result.json"])
            service[key] = value
            files["service-result.json"] = encoded(service)
            cases.append((key, files))
        for kind in ("unrelated effect", "extra audit", "query mutation", "wrong task", "false completion", "pending query"):
            files = dict(good)
            if kind in {"wrong task", "false completion", "pending query"}:
                label = "get-pending" if kind == "pending query" else "get-completed"
                body = json.loads(decode_response(files[label + ".response.bin"])[2])
                if kind == "wrong task":
                    body["result"]["id"] = "different-task"
                else:
                    body["result"]["status"]["state"] = "completed" if kind == "pending query" else "input-required"
                files[label + ".response.bin"] = response(encoded(body))
            else:
                rows = json.loads(files["boundaries.json"])
                for index in ([5] if kind == "query mutation" else [4, 5]):
                    db = rows[index]["database"]
                    if kind == "extra audit":
                        db["tables"]["audit_log"].append(dict(db["tables"]["audit_log"][0], id=2))
                    else:
                        db["tables"]["incidents"][0]["status"] = "unexpected"
                    files[rows[index]["label"] + ".snapshot.json"] = encoded(rows[index])
                files["boundaries.json"] = encoded(rows)
            cases.append((kind, files))
        for name, files in cases:
            with self.subTest(case=name), self.assertRaises((ValueError, KeyError, TypeError)):
                check(self.materialize(files), self.seed)

    def test_missing_native_gate_never_reserves_execution(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import agentops_http_control_v1 as control
            target = self.materialize({"plan.json": encoded({"source_files": [], "harness_files": [],
                                                            "runtime_inventory": {"path": "missing"}})})
            with patch.object(control.evidence, "source_inventory", return_value=[]), \
                    patch.object(control, "harness", return_value=[]), \
                    patch.object(control.evidence, "digest", return_value={"path": "missing"}), \
                    patch.object(control, "PREREQUISITE", self.base / "missing-native"), \
                    patch.object(control.subprocess, "Popen") as spawn:
                with self.assertRaises(FileNotFoundError):
                    control.run(target)
                spawn.assert_not_called()
                self.assertFalse((target / "execution.json").exists())
        finally:
            sys.path.pop(0)


if __name__ == "__main__":
    unittest.main()
