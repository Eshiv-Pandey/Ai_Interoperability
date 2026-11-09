"""Independent check of the fixed upstream AgentOps confirmation observation.

Reads the saved passive profile and the pinned seed, without importing the
observer, pytest, SDK, application or its predicates. Acceptance establishes
consistency of the captured four boundaries only. It does not authenticate the
capture, rule out transient changes between boundaries, establish live HTTP
behavior, or supply human task validity. Execution/provenance are separate checks.
"""

import argparse
import copy
import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath


SEED_SHA256 = "957ae8da4e1d174b9ff349acfca7ce4c204020a572fbeb7245783285d49d455b"
NODEID = "tests/test_server.py::test_a2a_confirmation_response_resumes_the_guarded_action_with_audit_identity"
RATIONALE = "Inventory is down and INC-002 matches the service-down runbook."
DB_FIELDS = ("user_tables", "schema", "columns", "user_version", "tables")
ORDER = {"services": "name", "incidents": "id", "audit_log": "id", "sqlite_sequence": "name"}


def require(condition, message):
    if condition is not True:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def same(left, right):
    return canonical(left) == canonical(right)


def unique_pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def decode_json(raw):
    def invalid(value):
        raise ValueError("nonfinite JSON value: " + value)
    return json.loads(raw, object_pairs_hook=unique_pairs, parse_constant=invalid)


def load_json(path):
    return decode_json(path.read_bytes())


def seed_snapshot(path):
    """Read an independently pinned, immutable input through SQLite read-only mode."""
    require(hashlib.sha256(path.read_bytes()).hexdigest() == SEED_SHA256, "pinned seed hash")
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        schema = [dict(row) for row in connection.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY type,name")]
        user_tables = [row[0] for row in connection.execute(
            "SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        tables, columns = {}, {}
        for table, key in ORDER.items():
            tables[table] = [dict(row) for row in connection.execute(f'SELECT * FROM "{table}" ORDER BY "{key}"')]
            columns[table] = [dict(row) for row in connection.execute(f'PRAGMA table_info("{table}")')]
        result = {"schema": schema, "user_tables": user_tables, "columns": columns,
                  "user_version": connection.execute("PRAGMA user_version").fetchone()[0], "tables": tables}
        connection.rollback()
    require(hashlib.sha256(path.read_bytes()).hexdigest() == SEED_SHA256, "seed unchanged after read")
    return result


def db_value(database):
    result = {field: database[field] for field in DB_FIELDS}
    require(result["user_tables"] == ["audit_log", "incidents", "services"], "complete domain table inventory")
    require(set(result["tables"]) == set(ORDER), "all domain and sequence tables captured")
    require(set(result["columns"]) == set(ORDER), "all table columns captured")
    for table, key in ORDER.items():
        rows = result["tables"][table]
        fields = [column["name"] for column in result["columns"][table]]
        require(type(rows) is list and len(fields) == len(set(fields)), "row/column shape")
        ids = []
        for row in rows:
            require(type(row) is dict and set(row) == set(fields), "full row columns: " + table)
            ids.append(canonical(row[key]))
        require(len(ids) == len(set(ids)), "duplicate row identity: " + table)
    return result


def at_utc(value):
    require(type(value) is str and bool(value), "timestamp is a nonempty string")
    instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(instant.tzinfo is not None and instant.utcoffset().total_seconds() == 0, "UTC timestamp")
    return instant


def check_record(profile, seed):
    require(profile["schema_version"] == "agentops-passive-upstream-observation/2", "profile version")
    require(profile["nodeid"] == NODEID and profile["errors"] == [], "selected test and capture errors")
    require(profile["network_attempts"] == [] and type(profile["function_replacements"]) is int
            and profile["function_replacements"] == 0, "offline observer boundaries")
    observations = profile["observations"]
    require(len(observations) == 4, "exactly four request boundaries")
    expected = [("helper_call", "approval-start"), ("helper_return", "approval-start"),
                ("helper_call", "approval-resume"), ("helper_return", "approval-resume")]
    previous_ns = -1
    stamps = []
    for index, (observation, (event, rpc_id)) in enumerate(zip(observations, expected)):
        require(type(observation["sequence"]) is int and observation["sequence"] == index, "capture sequence")
        require((observation["event"], observation["rpc_id"]) == (event, rpc_id), "request boundary order")
        require(type(observation["monotonic_ns"]) is int and observation["monotonic_ns"] > previous_ns,
                "monotonic boundary order")
        previous_ns = observation["monotonic_ns"]
        stamps.append(at_utc(observation["observed_at_utc"]))
        require(observation["payload"]["id"] == rpc_id, "captured request identity")
    require(stamps == sorted(stamps), "UTC boundary order")
    require(same(observations[0]["payload"], observations[1]["payload"]), "initial request unmodified")
    require(same(observations[2]["payload"], observations[3]["payload"]), "approval request unmodified")
    start = observations[0]["payload"]
    require(same(start, {"jsonrpc": "2.0", "id": "approval-start", "method": "message/stream", "params": {
        "message": {"kind": "message", "messageId": "approval-message", "role": "user",
                    "parts": [{"kind": "text", "text": "Restart inventory."}]}}}), "original start payload")
    start_results = observations[1]["results"]
    require([row["kind"] for row in start_results] == ["task", "status-update", "artifact-update",
            "status-update", "artifact-update", "status-update"], "original start event kinds")
    require(start_results[0]["status"]["state"] == "submitted" and
            start_results[1]["status"]["state"] == "working", "submitted then working")
    pending = start_results[-1]
    require(pending["status"]["state"] == "input-required" and pending["final"] is False, "nonterminal approval pause")
    task_id, context_id = pending["taskId"], pending["contextId"]
    require(all(type(value) is str and value for value in (task_id, context_id)), "original task/context identity")
    require(start_results[0]["id"] == task_id and start_results[0]["contextId"] == context_id,
            "initial task association")
    for row in start_results[1:]:
        require(row["taskId"] == task_id and row["contextId"] == context_id, "start event association")
    calls = [part["data"] for part in pending["status"]["message"]["parts"]
             if part.get("kind") == "data" and part.get("metadata", {}).get("adk_type") == "function_call"
             and part.get("data", {}).get("name") == "adk_request_confirmation"]
    require(len(calls) == 1, "one confirmation request")
    confirmation = calls[0]
    require(type(confirmation["id"]) is str and bool(confirmation["id"]), "confirmation identity")
    require(same(confirmation["args"]["originalFunctionCall"], {"id": "restart-inventory-call",
            "args": {"name": "inventory"}, "name": "restart_service"}), "requested guarded action")
    require(same(observations[2]["payload"], {"jsonrpc": "2.0", "id": "approval-resume",
        "method": "message/stream", "params": {"message": {"kind": "message", "messageId": "approval-response",
            "role": "user", "contextId": context_id, "taskId": task_id, "parts": [{"kind": "data", "data": {
                "id": confirmation["id"], "name": confirmation["name"],
                "response": {"confirmed": True, "payload": {"rationale": RATIONALE}}},
                "metadata": {"adk_type": "function_response"}}]}}}), "exact bound DataPart approval")
    completed_results = observations[3]["results"]
    require([row["kind"] for row in completed_results] == ["status-update", "artifact-update", "artifact-update",
            "status-update"], "original completion event kinds")
    for row in completed_results:
        require(row["taskId"] == task_id and row["contextId"] == context_id, "completion event association")
    require(completed_results[-1]["status"]["state"] == "completed" and completed_results[-1]["final"] is True,
            "original task completed")
    databases = [db_value(row["database"]) for row in observations]
    require(same(databases[0], db_value(seed)), "initial runtime database equals pinned seed")
    require(same(databases[0], databases[1]) and same(databases[1], databases[2]), "no preapproval domain effect")
    paths = [row["database"]["path"] for row in observations]
    require(all(type(path) is str and path for path in paths) and len(set(paths)) == 1, "same observed runtime database")
    path = PurePosixPath(paths[0])
    require(not path.is_absolute() and not PureWindowsPath(paths[0]).drive and ".." not in path.parts
            and path.parts[0] == "pytest-temp" and all(row["database"]["path_base"] == "run" for row in observations),
            "database declared inside isolated run")
    expected_db = copy.deepcopy(databases[0])
    services = expected_db["tables"]["services"]
    target = [service for service in services if service["name"] == "inventory"]
    require(len(target) == 1 and target[0]["status"] == "down", "seeded target is down")
    target[0]["status"] = "operational"
    require(expected_db["tables"]["audit_log"] == [] and expected_db["tables"]["sqlite_sequence"] == [], "fresh audit seed")
    audit_rows = databases[3]["tables"]["audit_log"]
    require(len(audit_rows) == 1, "exactly one new audit row")
    audit = audit_rows[0]
    require(type(audit["id"]) is int and audit["id"] == 1, "first audit row identity")
    require(type(audit["schema_version"]) is int and audit["schema_version"] == 1, "audit schema version")
    require(type(audit["invocation_id"]) is str and bool(audit["invocation_id"]), "audit invocation identity")
    audit_time = at_utc(audit["ts"])
    require(stamps[2].replace(microsecond=0) <= audit_time <= stamps[3], "audit timestamp within approval interval")
    expected_fields = {"actor": "agentops-agent", "approved_by": "A2A_USER_" + context_id,
        "rationale": RATIONALE, "context_summary": "service inventory was down; open incidents: INC-002",
        "session_id": context_id, "action": "restart_service", "target": "inventory",
        "detail": "service restarted and marked operational (mock)"}
    require(all(same(audit[key], value) for key, value in expected_fields.items()), "complete audit attribution and effect")
    expected_db["tables"]["audit_log"] = [audit]
    expected_db["tables"]["sqlite_sequence"] = [{"name": "audit_log", "seq": 1}]
    require(same(databases[3], expected_db), "only target status, one audit and audit sequence changed")
    local = profile["final_test_locals"]
    require(local["task_id"] == task_id and local["context_id"] == context_id and local["rationale"] == RATIONALE,
            "test locals agree with public identity")
    require(type(local["model_calls"]) is int and local["model_calls"] == 2, "two deterministic model-double calls")
    require(same(local["confirmation_call"], confirmation), "same captured confirmation")
    expected_contexts = [["A2A_USER_" + context_id, context_id, audit["invocation_id"], flag] for flag in (False, True)]
    require(same(local["seen_contexts"], expected_contexts), "same invocation observed before and after confirmation")
    return {"status": "passed", "task_id": task_id, "context_id": context_id,
            "changed_service": "inventory", "new_audit_rows": 1, "other_domain_rows_unchanged": True,
            "scope": "Saved in-process boundary consistency; execution provenance and real HTTP qualification separate"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--seed-db", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Refusing to overwrite prior check")
    report = {"schema_version": "agentops-independent-effect-check/2", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "profile_sha256": None, "seed_sha256": SEED_SHA256}
    try:
        raw = args.profile.read_bytes()
        report["profile_sha256"] = hashlib.sha256(raw).hexdigest()
        report.update(check_record(decode_json(raw), seed_snapshot(args.seed_db)))
    except Exception as error:
        # Retain parse/read/shape failures as failures too, never missing evidence
        # or a passing result. Output creation errors remain visible to the caller.
        report.update(status="failed", error=f"{type(error).__name__}: {error}")
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps(report))
    raise SystemExit(0 if report["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
