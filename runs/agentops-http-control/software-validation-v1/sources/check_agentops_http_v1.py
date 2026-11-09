"""Check retained HTTP bytes and domain effects without importing the runner/app.

Transport decoding is shared; semantic checks are separate from the driver.
This is not independently authored scientific review or capture authentication.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

try:
    from .agentops_http_bytes_v1 import decode_response, rpc_results, strict_json
    from .check_agentops_effect_v2 import at_utc, db_value, require, same, seed_snapshot
except ImportError:
    from agentops_http_bytes_v1 import decode_response, rpc_results, strict_json
    from check_agentops_effect_v2 import at_utc, db_value, require, same, seed_snapshot


ROOT = Path(__file__).resolve().parents[1]
RATIONALE = "Inventory is down and INC-002 matches the service-down runbook."
LABELS = ("card", "start", "get-pending", "resume", "get-completed")
BOUNDARIES = ("before-card", "before-start", "after-start", "before-resume",
              "after-resume", "after-get-completed")


def request_json(raw, method, target, port):
    head, separator, body = raw.partition(b"\r\n\r\n")
    require(bool(separator), "complete HTTP request")
    lines = head.decode("ascii").split("\r\n")
    require(lines[0] == f"{method} {target} HTTP/1.1", "request method/target")
    headers = {}
    for line in lines[1:]:
        key, separator, value = line.partition(":")
        key = key.lower()
        require(bool(separator) and key not in headers, "unique HTTP request headers")
        headers[key] = value.strip()
    required = {"host": f"127.0.0.1:{port}", "connection": "close", "accept-encoding": "identity",
                "accept": "application/json, text/event-stream", "content-length": str(len(body))}
    if method == "POST":
        required["content-type"] = "application/json"
    require(headers == required, "exact default-version, credential-free request headers")
    if method == "GET":
        require(body == b"", "bodyless discovery")
        return None
    return strict_json(body)


def check(run: Path, seed):
    plan = strict_json((run / "plan.json").read_bytes())
    require(plan["schema_version"] == "agentops-http-plan/1", "plan schema")
    require(plan["sequence"] == list(LABELS), "frozen request sequence")
    port = plan["port"]
    require(type(port) is int and 1024 <= port <= 65535, "local port")
    requests, responses, receipts = {}, {}, []
    for label in LABELS:
        method, target = ("GET", "/.well-known/agent-card.json") if label == "card" else ("POST", "/")
        receipt = strict_json((run / f"{label}.exchange.json").read_bytes())
        require(receipt["label"] == label and receipt["method"] == method and receipt["path"] == target
                and receipt["port"] == port and receipt["status"] == "captured"
                and receipt["request_fully_sent"] is True and receipt["response_eof"] is True,
                "complete matching exchange receipt")
        require(at_utc(receipt["started_at_utc"]) <= at_utc(receipt["finished_at_utc"]), "exchange time order")
        receipts.append(receipt)
        requests[label] = request_json((run / f"{label}.request.bin").read_bytes(), method, target, port)
        status, headers, body = decode_response((run / f"{label}.response.bin").read_bytes())
        require(status == 200, "HTTP success: " + label)
        if label in {"start", "resume"}:
            require(headers.get("content-type", "").split(";", 1)[0] == "text/event-stream", "SSE content type")
            responses[label] = rpc_results(body, "approval-" + label)
        else:
            require(headers.get("content-type", "").split(";", 1)[0] == "application/json", "JSON content type")
            responses[label] = strict_json(body)
    card = responses["card"]
    require(card["version"] == "0.11.0" and card["capabilities"]["streaming"] is True, "original application card")
    interfaces = card["supportedInterfaces"]
    require(any(row.get("url") == f"http://127.0.0.1:{port}/" and row.get("protocolBinding") == "JSONRPC"
                for row in interfaces), "advertised original JSONRPC route")
    require({row["id"] for row in card["skills"]} == {"incident-triage", "remediation"}, "original skills")
    require(card["defaultInputModes"] == ["text/plain"] and card["defaultOutputModes"] == ["text/plain"],
            "original text mode declarations")
    start = requests["start"]
    require(same(start, {"jsonrpc": "2.0", "id": "approval-start", "method": "message/stream", "params": {
        "message": {"kind": "message", "messageId": "approval-message", "role": "user",
                    "parts": [{"kind": "text", "text": "Restart inventory."}]}}}), "original start input")
    initial = responses["start"]
    require([row["kind"] for row in initial] == ["task", "status-update", "artifact-update",
            "status-update", "artifact-update", "status-update"], "initial event sequence")
    require(initial[0]["status"]["state"] == "submitted" and initial[1]["status"]["state"] == "working",
            "submitted then working")
    pending = initial[-1]
    require(pending["status"]["state"] == "input-required" and pending["final"] is False, "nonterminal pause")
    task_id, context_id = pending["taskId"], pending["contextId"]
    require(all(type(value) is str and value for value in (task_id, context_id)), "task/context strings")
    require(initial[0]["id"] == task_id and initial[0]["contextId"] == context_id, "initial task binding")
    for row in initial[1:] + responses["resume"]:
        require(row["taskId"] == task_id and row["contextId"] == context_id, "all events bound to original task")
    calls = [part["data"] for part in pending["status"]["message"]["parts"]
             if part.get("kind") == "data" and part.get("metadata", {}).get("adk_type") == "function_call"
             and part.get("data", {}).get("name") == "adk_request_confirmation"]
    require(len(calls) == 1, "single confirmation request")
    call = calls[0]
    require(type(call["id"]) is str and bool(call["id"]), "confirmation identity")
    require(same(call["args"]["originalFunctionCall"], {"id": "restart-inventory-call", "name": "restart_service",
                                                       "args": {"name": "inventory"}}), "original guarded action")
    require(same(requests["resume"], {"jsonrpc": "2.0", "id": "approval-resume", "method": "message/stream",
        "params": {"message": {"kind": "message", "messageId": "approval-response", "role": "user",
        "taskId": task_id, "contextId": context_id, "parts": [{"kind": "data", "data": {
            "id": call["id"], "name": call["name"], "response": {"confirmed": True, "payload": {"rationale": RATIONALE}}},
            "metadata": {"adk_type": "function_response"}}]}}}), "bound original DataPart confirmation")
    completed = responses["resume"]
    require([row["kind"] for row in completed] == ["status-update", "artifact-update", "artifact-update", "status-update"],
            "completion event sequence")
    require(completed[-1]["status"]["state"] == "completed" and completed[-1]["final"] is True, "same-task completion")
    for label, state in (("get-pending", "input-required"), ("get-completed", "completed")):
        require(same(requests[label], {"jsonrpc": "2.0", "id": label, "method": "tasks/get", "params": {"id": task_id}}),
                "original task queried")
        reply = responses[label]
        require(reply.get("jsonrpc") == "2.0" and reply.get("id") == label and "error" not in reply, "query RPC success")
        task = reply["result"]
        require(task["kind"] == "task" and task["id"] == task_id and task["contextId"] == context_id
                and task["status"]["state"] == state, "native persisted task state")
    rows = strict_json((run / "boundaries.json").read_bytes())
    require([row["label"] for row in rows] == list(BOUNDARIES), "all six database boundaries")
    stamps = [at_utc(row["observed_at_utc"]) for row in rows]
    require(stamps == sorted(stamps), "UTC snapshot order")
    for index, receipt in enumerate(receipts):
        require(stamps[index] <= at_utc(receipt["started_at_utc"])
                <= at_utc(receipt["finished_at_utc"]) <= stamps[index + 1], "exchange bounded by its database snapshots")
    ticks = [row["monotonic_ns"] for row in rows]
    require(all(type(tick) is int for tick in ticks) and all(a < b for a, b in zip(ticks, ticks[1:])),
            "monotonic snapshot order")
    databases = [db_value(row["database"]) for row in rows]
    for row in rows:
        require(row["database"]["path"] == "state/incidents.db" and row["database"]["path_base"] == "run",
                "isolated source-owned runtime database")
        require(same(row, strict_json((run / f'{row["label"]}.snapshot.json').read_bytes())), "snapshot record consistency")
    require(all(same(value, db_value(seed)) for value in databases[:4]), "no startup, discovery, pause or query domain writes")
    final = databases[4]
    require(same(final, databases[5]), "final query does not mutate domain")
    audit_rows = final["tables"]["audit_log"]
    require(len(audit_rows) == 1, "exactly one attributed audit row")
    audit = audit_rows[0]
    require(type(audit["id"]) is int and audit["id"] == 1 and type(audit["schema_version"]) is int
            and audit["schema_version"] == 1, "original audit identity/schema")
    require(type(audit["invocation_id"]) is str and bool(audit["invocation_id"]), "invocation identity")
    require(stamps[3].replace(microsecond=0) <= at_utc(audit["ts"]) <= stamps[4], "effect during confirmation interval")
    expected_fields = {"actor": "agentops-agent", "approved_by": "A2A_USER_" + context_id,
        "rationale": RATIONALE, "context_summary": "service inventory was down; open incidents: INC-002",
        "session_id": context_id, "action": "restart_service", "target": "inventory",
        "detail": "service restarted and marked operational (mock)"}
    require(all(same(audit[key], value) for key, value in expected_fields.items()), "complete synthetic-caller audit")
    expected = copy.deepcopy(db_value(seed))
    inventory = [row for row in expected["tables"]["services"] if row["name"] == "inventory"]
    require(len(inventory) == 1 and inventory[0]["status"] == "down", "original seed target")
    inventory[0]["status"] = "operational"
    expected["tables"]["audit_log"] = [audit]
    expected["tables"]["sqlite_sequence"] = [{"name": "audit_log", "seq": 1}]
    require(same(final, expected), "only one target status and audit/sequence change")
    service = strict_json((run / "service-result.json").read_bytes())
    require(service["schema_version"] == "agentops-http-service/1" and service["status"] == "stopped"
            and service["network_errors"] == [] and not service.get("watchdog_expired"), "clean offline service termination")
    require(type(service["model_double_calls"]) is int and service["model_double_calls"] == 2, "two offline double calls")
    require(same(service["seen_contexts"], [["A2A_USER_" + context_id, context_id, audit["invocation_id"], flag]
                                          for flag in (False, True)]), "same guarded invocation on both callbacks")
    return {"status": "passed", "task_id": task_id, "context_id": context_id, "new_audit_rows": 1,
            "advertised_interfaces": interfaces, "request_version_header": None,
            "scope": "One captured no-version-header HTTP continuation using the original factory and offline fixture",
            "bridge_qualification": False, "independent_scientific_review": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Refusing to overwrite a prior check")
    report = {"schema_version": "agentops-http-check/1"}
    try:
        report.update(check(args.run, seed_snapshot(ROOT / "external/agentops-c806b7f1/agents/data/incidents.db")))
        report["inputs"] = [{"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                            for path in sorted(args.run.iterdir()) if path.is_file()]
    except Exception as error:
        report.update(status="failed", error=f"{type(error).__name__}: {error}")
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps({key: value for key, value in report.items() if key != "inputs"}))
    raise SystemExit(0 if report["status"] == "passed" else 1)
