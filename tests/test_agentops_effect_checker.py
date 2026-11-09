"""Authored evidence tests, never an AgentOps run or observed successful task."""

import copy
import json
import subprocess
import sys
import unittest
import uuid
from pathlib import Path

from scripts.check_agentops_effect_v2 import NODEID, RATIONALE, check_record, seed_snapshot


ROOT = Path(__file__).resolve().parents[1]


def authored_profile(seed):
    start = {"jsonrpc": "2.0", "id": "approval-start", "method": "message/stream", "params": {
        "message": {"kind": "message", "messageId": "approval-message", "role": "user",
                    "parts": [{"kind": "text", "text": "Restart inventory."}]}}}
    confirmation = {"id": "authored-confirmation", "name": "adk_request_confirmation", "args": {
        "originalFunctionCall": {"id": "restart-inventory-call", "args": {"name": "inventory"}, "name": "restart_service"}}}
    resume = {"jsonrpc": "2.0", "id": "approval-resume", "method": "message/stream", "params": {"message": {
        "kind": "message", "messageId": "approval-response", "role": "user", "contextId": "authored-context",
        "taskId": "authored-task", "parts": [{"kind": "data", "data": {"id": confirmation["id"],
            "name": confirmation["name"], "response": {"confirmed": True, "payload": {"rationale": RATIONALE}}},
            "metadata": {"adk_type": "function_response"}}]}}}
    kinds = ["task", "status-update", "artifact-update", "status-update", "artifact-update", "status-update"]
    initial_results = [{"kind": kind, "taskId": "authored-task", "contextId": "authored-context"} for kind in kinds]
    initial_results[0].update(id="authored-task", status={"state": "submitted"})
    initial_results[1]["status"] = {"state": "working"}
    initial_results[-1].update(final=False, status={"state": "input-required", "message": {"parts": [
        {"kind": "data", "metadata": {"adk_type": "function_call"}, "data": confirmation}]}})
    completed = [{"kind": kind, "taskId": "authored-task", "contextId": "authored-context"}
                 for kind in ["status-update", "artifact-update", "artifact-update", "status-update"]]
    completed[-1].update(final=True, status={"state": "completed"})
    record = {"schema_version": "agentops-passive-upstream-observation/2", "nodeid": NODEID, "errors": [],
              "network_attempts": [], "function_replacements": 0,
              "observations": [], "final_test_locals": {"task_id": "authored-task", "context_id": "authored-context",
                "rationale": RATIONALE, "model_calls": 2, "confirmation_call": confirmation,
                "seen_contexts": [["A2A_USER_authored-context", "authored-context", "authored-invocation", flag]
                                  for flag in (False, True)]}}
    for i, event in enumerate(("helper_call", "helper_return", "helper_call", "helper_return")):
        database = copy.deepcopy(seed)
        database["path"] = "pytest-temp/authored/state/incidents.db"
        database["path_base"] = "run"
        obs = {"sequence": i, "event": event, "rpc_id": "approval-start" if i < 2 else "approval-resume",
               "monotonic_ns": i + 1, "observed_at_utc": f"2026-10-25T01:00:0{i}+00:00",
               "payload": copy.deepcopy(start if i < 2 else resume), "database": database}
        if i in (1, 3):
            obs["results"] = copy.deepcopy(initial_results if i == 1 else completed)
        record["observations"].append(obs)
    final_db = record["observations"][3]["database"]
    next(row for row in final_db["tables"]["services"] if row["name"] == "inventory")["status"] = "operational"
    final_db["tables"]["audit_log"] = [{"id": 1, "schema_version": 1, "ts": "2026-10-25T01:00:02Z",
        "actor": "agentops-agent", "approved_by": "A2A_USER_authored-context", "rationale": RATIONALE,
        "context_summary": "service inventory was down; open incidents: INC-002", "session_id": "authored-context",
        "invocation_id": "authored-invocation", "action": "restart_service", "target": "inventory",
        "detail": "service restarted and marked operational (mock)"}]
    final_db["tables"]["sqlite_sequence"] = [{"name": "audit_log", "seq": 1}]
    return record


class AgentOpsEffectCheckerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed = seed_snapshot(ROOT / "external/agentops-c806b7f1/agents/data/incidents.db")

    def test_authored_boundary_evidence_passes(self):
        result = check_record(authored_profile(self.seed), self.seed)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["new_audit_rows"], 1)

    def test_materially_invalid_evidence_is_rejected(self):
        mutations = {
            "missing boundary": lambda p: p["observations"].pop(1),
            "reversed time": lambda p: p["observations"][3].update(monotonic_ns=1),
            "capture error": lambda p: p["errors"].append({"error": "missing database"}),
            "malformed timestamp": lambda p: p["observations"][3].update(observed_at_utc=123),
            "network attempt": lambda p: p["network_attempts"].append({"event": "socket.connect"}),
            "function replacement": lambda p: p.update(function_replacements=1),
            "wrong task": lambda p: p["observations"][3]["results"][-1].update(taskId="other"),
            "intermediate wrong context": lambda p: p["observations"][3]["results"][1].update(contextId="other"),
            "terminal waiting": lambda p: p["observations"][1]["results"][-1].update(final=True),
            "false completed": lambda p: p["observations"][3]["results"][-1]["status"].update(state="input-required"),
            "integer completion boolean": lambda p: p["observations"][3]["results"][-1].update(final=1),
            "preapproval effect": lambda p: p["observations"][1]["database"]["tables"]["services"][0].update(status="operational"),
            "no target effect": lambda p: next(r for r in p["observations"][3]["database"]["tables"]["services"] if r["name"] == "inventory").update(status="down"),
            "unrelated service effect": lambda p: p["observations"][3]["database"]["tables"]["services"][0].update(status="operational"),
            "unrelated incident effect": lambda p: p["observations"][3]["database"]["tables"]["incidents"][0].update(status="resolved"),
            "missing audit": lambda p: p["observations"][3]["database"]["tables"]["audit_log"].clear(),
            "extra audit": lambda p: p["observations"][3]["database"]["tables"]["audit_log"].append(dict(p["observations"][3]["database"]["tables"]["audit_log"][0], id=2)),
            "wrong audit principal": lambda p: p["observations"][3]["database"]["tables"]["audit_log"][0].update(approved_by="other"),
            "wrong audit invocation": lambda p: p["observations"][3]["database"]["tables"]["audit_log"][0].update(invocation_id="other"),
            "audit before approval": lambda p: p["observations"][3]["database"]["tables"]["audit_log"][0].update(ts="2026-10-24T01:00:00Z"),
            "audit boolean id": lambda p: p["observations"][3]["database"]["tables"]["audit_log"][0].update(id=True),
            "sequence missing": lambda p: p["observations"][3]["database"]["tables"]["sqlite_sequence"].clear(),
            "schema changed": lambda p: p["observations"][3]["database"]["schema"].pop(),
            "dropped column": lambda p: p["observations"][3]["database"]["tables"]["services"][0].pop("owner"),
            "duplicate row": lambda p: p["observations"][3]["database"]["tables"]["services"].append(copy.deepcopy(p["observations"][3]["database"]["tables"]["services"][0])),
            "hidden table": lambda p: p["observations"][3]["database"]["tables"].update(hidden=[]),
            "database switched": lambda p: p["observations"][3]["database"].update(path="other.db"),
            "model calls not two": lambda p: p["final_test_locals"].update(model_calls=3),
            "context approval missing": lambda p: p["final_test_locals"]["seen_contexts"].pop(),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                record = authored_profile(self.seed)
                mutate(record)
                with self.assertRaises((ValueError, KeyError, TypeError, IndexError)):
                    check_record(record, self.seed)

    def test_cli_retains_bad_input_failures(self):
        # Never exercise application code: the subprocess only validates saved JSON.
        base = ROOT / "tmp" / ("agentops-checker-cli-" + uuid.uuid4().hex)
        base.mkdir()
        # Retain these diagnostic inputs/results. TemporaryDirectory's restricted
        # Windows ACL is unusable under this sandbox's separate process identity.
        inputs = {"malformed": b"{", "duplicate-key": b'{"x":1,"x":2}', "wrong-shape": b"[]"}
        for name, raw in inputs.items():
            (base / (name + ".json")).write_bytes(raw)
        malformed = authored_profile(self.seed)
        malformed["observations"][1]["results"][-1]["status"]["message"]["parts"] = [9]
        (base / "wrong-part.json").write_text(json.dumps(malformed), encoding="utf-8")
        for name in [*inputs, "wrong-part", "missing"]:
            output = base / (name + "-check.json")
            run = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/check_agentops_effect_v2.py"),
                "--profile", str(base / (name + ".json")), "--seed-db",
                str(ROOT / "external/agentops-c806b7f1/agents/data/incidents.db"), "--output", str(output)],
                capture_output=True, check=False, timeout=20)
            with self.subTest(name=name):
                self.assertEqual(run.returncode, 1, run.stderr)
                self.assertEqual(json.loads(output.read_text())["status"], "failed")


if __name__ == "__main__":
    unittest.main()
