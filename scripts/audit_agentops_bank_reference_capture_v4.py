"""Independent raw/state census; never imports actor, SDK, model or evaluator."""
import argparse
import base64
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_bytes())


def seal(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def need(value, message):
    if not value:
        raise ValueError(message)


def rows(path):
    return [json.loads(line) for line in path.read_bytes().splitlines() if line.strip()]


def state(path):
    tables = {}
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)) as con:
        con.row_factory = sqlite3.Row
        need(con.execute("PRAGMA quick_check").fetchone()[0] == "ok", "Closed SQLite corruption")
        for row in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            name = row[0]
            quoted = '"' + name.replace('"', '""') + '"'
            tables[name] = [{key: {"base64": base64.b64encode(value).decode()} if isinstance(value, bytes) else value
                             for key, value in dict(item).items()} for item in con.execute("SELECT * FROM " + quoted)]
    return tables


def events(path):
    fields, output = [], []
    for line in path.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n") + [""]:
        if not line and fields:
            output.append(json.loads("\n".join(fields)))
            fields = []
        elif line.startswith("data:"):
            fields.append(line[5:].removeprefix(" "))
    return output


def audit(base, output):
    need(not output.exists(), "Fresh output required")
    retention = read(base / "retention.json")
    capture = base / "extracted"
    need(seal(base / "artifact.zip") == {"bytes": retention["archive_bytes"], "sha256": retention["archive_sha256"]}
         and retention["digest_matches_api"], "Archive/API digest changed")
    inventory = read(base / "extracted-manifest.json")["files"]
    for row in inventory:
        need(seal(capture / row["path"]) == {"bytes": row["bytes"], "sha256": row["sha256"]}, "Archive member changed")
    for row in read(capture / "manifest.json")["files"]:
        need(seal(capture / row["path"]) == {"bytes": row["bytes"], "sha256": row["sha256"]}, "Driver manifest changed")
    ingestion = read(ROOT / "docs/research/source-evidence/agentops-local-archive-v1/ingestion.json")
    need(seal(capture / "original-agentops.zip")["sha256"] == ingestion["retained_archive"]["sha256"], "Original archive changed")
    source = [r for r in ingestion["records"] if r["kind"] == "regular_file"]
    need(len(source) == 421, "Source union changed")
    with zipfile.ZipFile(capture / "original-agentops.zip") as archive:
        for row in source:
            raw = archive.read(row["archive_member"])
            need(len(raw) == row["extracted"]["bytes"] and hashlib.sha256(raw).hexdigest() == row["extracted"]["sha256"], "Source member changed")
    public = {r["id"]: r for r in read(ROOT / "benchmark/tasks-v1/agentops/application.json")["records"]}
    grades = read(capture / "evaluation.json")
    need(len(grades["cases"]) == 34 and {r["case_id"] for r in grades["cases"]} == set(public), "Candidate denominator changed")
    census = []
    for grade in grades["cases"]:
        ident = grade["case_id"]
        case = capture / ident
        actor = read(case / "actor-receipt.json")
        need(read(case / "public-task.json") == public[ident], "Public recipe changed")
        need(actor["provider_calls"] == 0 and not actor["source_bodies_modified"] and not actor["governance_bodies_modified"], "Profile changed")
        if actor["status"] == "unsupported_public_recipe":
            need(actor["tasks"] == [] and actor["executed_public_turns"] == [] and grade["status"] == "unsupported_public_recipe", "Unsupported recipe claims execution")
            census.append({"case_id": ident, "retained_mechanical_status": grade["status"], "observed_SDK_tasks": 0})
            continue
        need(actor["original_lifespan_exited"] and actor["denied_capability_probes"] == [{"event": "private_evaluator_open"}], "Cleanup or private/socket denial mismatch")
        bootstrap = read(case / "socket-bootstrap.json")
        need(bootstrap["helper_code_unchanged"] and bootstrap["restored_socket_has_ipv6"] is bootstrap["original_socket_has_ipv6"]
             and not bootstrap["socket_operation_permission_added"] and not bootstrap["observed_network_attempts_during_bootstrap"], "Bootstrap profile changed")
        before, after = read(case / "state-before.json"), read(case / "state-after.json")
        need(after == {name: state(case / ("closed-" + name)) for name in after}, "Closed database/state mismatch")
        need(before["incidents.db"] == after["incidents.db"], "Unexpected domain action")
        tasks = []
        for turn in actor["tasks"]:
            td = case / f"turn-{turn['turn']}"
            request = read(td / "request.raw.json")
            expected = public[ident]["public"]["turns"][turn["turn"] - 1]["text"]
            need(request["params"]["message"]["parts"] == [{"kind": "text", "text": expected}], "Raw prompt mismatch")
            wire = events(td / "response.raw.sse")
            need(wire == read(td / "rpc-events.json") and wire and not any("error" in e for e in wire), "Raw SSE mismatch")
            remote, last = read(td / "task-get.response.raw.json")["result"], wire[-1]["result"]
            need(remote["id"] == last["taskId"] == turn["task_id"] and remote["contextId"] == last["contextId"] == turn["context_id"], "Task/context mismatch")
            need(remote["status"]["state"] == last["status"]["state"] == turn["last_state"], "Task status mismatch")
            tasks.append({"turn": turn["turn"], "task_id": remote["id"], "context_id": remote["contextId"], "state": turn["last_state"], "wire_events": len(wire)})
        runtime = after["runtime.db"]
        need(len(runtime["tasks"]) == len(tasks), "Durable SDK task denominator mismatch")
        tools, models = rows(case / "tool-contexts.jsonl"), rows(case / "model-journal.jsonl")
        owners = {(s["user_id"], s["id"]) for s in runtime["sessions"]}
        need(all((t["user_id"], t["session_id"]) in owners for t in tools), "Tool/session owner mismatch")
        notes = after.get("memory.db", {}).get("incident_notes", [])
        need(all(note["user_id"] in {u for u, _ in owners} for note in notes), "Stored note owner mismatch")
        census.append({"case_id": ident, "retained_mechanical_status": grade["status"],
            "preserved_failed_checks": [c["name"] for c in grade["checks"] if not c["passed"]],
            "complete_public_recipe": grade["complete_public_recipe"], "unsupported_turns": grade["unsupported_public_turns"],
            "tasks": tasks, "observed_SDK_tasks": len(tasks), "model_calls": len(models), "tool_calls": len(tools),
            "durable_ADK_events": len(runtime["events"]), "notes": len(notes), "business_state_unchanged": True})
    counts = dict(Counter(c["retained_mechanical_status"] for c in census))
    need(counts == {"observed_reference_recipe": 20, "observed_partial_reference_recipe": 10, "unsupported_public_recipe": 2, "checks_failed": 2}, "Mechanical census changed")
    value = {"schema_version": "agentops-v4-raw-source-state-census/1", "status": "passed_independent_raw_source_and_state_census",
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "run_id": retention["run_id"],
        "archive": seal(base / "artifact.zip"), "files_checked": len(inventory), "source_members_checked": len(source),
        "candidate_denominator": 34, "status_counts": counts, "cases": census, "source": seal(Path(__file__)),
        "new_application_model_or_evaluator_calls": 0, "human_review": False, "qualified_held_out_tasks": 0,
        "scope": "Reconstruct raw/source/state census and preserve first evaluator's mechanical classifications; not independent semantic gold or route qualification."}
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"status": value["status"], "counts": counts}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit(args.base, args.output)
