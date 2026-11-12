"""Independent owned oracle for a development read-only service-status fragment.

Executes pinned schema/seed SQL only in a private in-memory SQLite database,
then compares a separate Python projection with retained development evidence.
No application/SDK/provider is imported. No source or retained state is written.
Completeness is limited to the enumerated finite read fragment, never the task
oracle, full source-to-model semantics, human gold, or original-study eligibility.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import zipfile


class FragmentError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise FragmentError(message)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def binding(root, name):
    path = root / name
    return {"path": name, "bytes": path.stat().st_size, "sha256": sha(path)}


def seed_business_state(schema_sql, seed_sql):
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    try:
        connection.executescript(schema_sql)
        connection.executescript(seed_sql)
        return {name: [dict(row) for row in connection.execute(f"SELECT * FROM {name}")]
                for name in ("services", "incidents", "audit_log", "sqlite_sequence")}
    finally:
        connection.close()


def status_oracle(state, supplied_name):
    """Complete deterministic oracle on this finite read-only snapshot fragment."""
    require(type(supplied_name) is str, "non-string input outside declared fragment")
    require(set(state) == {"services", "incidents", "audit_log", "sqlite_sequence"}, "business-state closure missing")
    services = state["services"]
    require(len({s["name"] for s in services}) == len(services), "duplicate service identity")
    incidents = state["incidents"]
    require(len({i["id"] for i in incidents}) == len(incidents), "duplicate incident identity")
    require(all(i["status"] in {"open", "investigating", "resolved"} for i in incidents), "unmodelled incident status")
    name = supplied_name.strip().lower()
    if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) is None:
        return {"branch": "invalid_slug", "normalized_name": None}
    service = next((s for s in services if s["name"] == name), None)
    if service is None:
        return {"branch": "missing_service", "normalized_name": name}
    require(service["status"] in {"operational", "degraded", "down"}, "unmodelled service status")
    active = sorted((i for i in incidents if i["service"] == name and i["status"] != "resolved"),
                    key=lambda row: row["opened_at"], reverse=True)
    return {"branch": "observed_service", "normalized_name": name,
            "projection": {"service": {k: service[k] for k in ("name", "status", "owner")},
                           "open_incidents": [{k: i[k] for k in ("id", "severity", "status")} for i in active]}}


def response_projection(response):
    require(set(response) == {"service", "open_incidents"}, "tool terminal shape differs")
    return {"service": {k: response["service"][k] for k in ("name", "status", "owner")},
            "open_incidents": [{k: i[k] for k in ("id", "severity", "status")} for i in response["open_incidents"]]}


def check_observation(before, after, calls, journal, task, public_text):
    require(before["incidents.db"] == after["incidents.db"], "forbidden business-state effect")
    require(len(calls) == 1 and calls[0]["tool"] == "get_service_status" and
            calls[0]["args"] == {"name": " INVENTORY "}, "required grounded read missing or unexpected tool")
    require(len(journal) == 2, "declared two-model-step reference journal incomplete")
    require(all(j["observed_user_text"] == public_text for j in journal), "public task changed")
    first_parts = journal[0]["response"]["content"]["parts"]
    emitted = [p["function_call"] for p in first_parts if p.get("function_call")]
    require(len(emitted) == 1 and emitted[0]["name"] == "get_service_status" and
            emitted[0]["args"] == calls[0]["args"], "actual first emitted read differs")
    terminals = [(i, p["function_response"]) for i, c in enumerate(journal[1]["request"]["contents"])
                 for p in c.get("parts", []) if p.get("function_response")]
    require(len(terminals) == 1, "required observed tool terminal missing or ambiguous")
    _, terminal = terminals[0]
    require(terminal["id"] == emitted[0]["id"] and terminal["name"] == emitted[0]["name"],
            "terminal not bound to actual emitted read")
    expected = status_oracle(before["incidents.db"], calls[0]["args"]["name"])
    require(expected["branch"] == "observed_service" and response_projection(terminal["response"]) ==
            expected["projection"], "observed typed terminal disagrees with independent oracle")
    require(task["status"]["state"] == "completed", "origin task not completed")
    require(task["contextId"] == calls[0]["session_id"] and calls[0]["user_id"] == "A2A_USER_" + task["contextId"],
            "original public origin/context association differs")
    final_parts = journal[1]["response"]["content"]["parts"]
    require(any(p.get("text") for p in final_parts) and not any(p.get("function_call") for p in final_parts),
            "final answer boundary not observed after grounded read")
    return expected


def qualify(root):
    case_id = "agentops-d01-health-active"
    prefix = "runs/ci-agentops-governed-app-reference-v4/retained-42887519756-1/extracted/" + case_id
    source = "external/agentops-c806b7f1/agents/"
    names = ["benchmark/tasks-v1/agentops/application.json", "benchmark/tasks-v1/agentops/evaluator.json",
             source + "data/sql/schema.sql", source + "data/sql/seed.sql", source + "python/src/agent/models.py",
             source + "python/src/agent/tools.py", source + "python/src/agent/data.py"]
    names += [prefix + "/" + n for n in ("state-before.json", "state-after.json", "tool-contexts.jsonl",
              "model-journal.jsonl", "actor-receipt.json", "turn-1/task-get.response.raw.json")]
    checkpoint_name = "runs/study-readiness-audit/v2-20261112-1/inventory.json"
    checkpoint = read(root / checkpoint_name)
    frozen = {b["path"]: b for b in checkpoint["exact_input_bindings"]}
    for name in names[:7]:
        require(name in frozen and sha(root / name) == frozen[name]["sha256"], "frozen source/input changed")
    archive_name = "runs/ci-agentops-governed-app-reference-v4/retained-42887519756-1/artifact.zip"
    require(sha(root / archive_name) == frozen[archive_name]["sha256"], "captured reference archive changed")
    with zipfile.ZipFile(root / archive_name) as archive:
        for name in names[7:]:
            member = name.removeprefix(prefix + "/")
            member = case_id + "/" + member
            require(archive.namelist().count(member) == 1, "ambiguous/missing original raw archive member")
            require(archive.read(member) == (root / name).read_bytes(), "raw extracted evidence differs from retained archive")
    inputs = [binding(root, name) for name in names + [checkpoint_name, archive_name]]
    public = next(r for r in read(root / names[0])["records"] if r["id"] == case_id)
    require(public["split"] == "development", "never execute a held-out recipe after outcomes")
    evaluator = next(r for r in read(root / names[1])["records"] if r["id"] == case_id)
    for ref in evaluator["source_refs"].values():
        require(sha(root / ref["path"]) == ref["sha256"], "source pin drift")
    source_model = (root / (source + "python/src/agent/models.py")).read_text(encoding="utf-8")
    require('_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")' in source_model,
            "normalization source grammar changed")
    require('normalized = value.strip().lower()' in source_model, "normalization source changed")
    data_source = (root / (source + "python/src/agent/data.py")).read_text(encoding="utf-8")
    require('query += " ORDER BY opened_at DESC"' in data_source, "source incident order changed")
    tools_source = (root / (source + "python/src/agent/tools.py")).read_text(encoding="utf-8")
    require('if row.status is not IncidentStatus.RESOLVED' in tools_source, "source active predicate changed")
    before, after = [read(root / (prefix + f"/state-{n}.json")) for n in ("before", "after")]
    seeded = seed_business_state((root / (source + "data/sql/schema.sql")).read_text(encoding="utf-8"),
                                 (root / (source + "data/sql/seed.sql")).read_text(encoding="utf-8"))
    require(seeded == before["incidents.db"], "retained before-state differs from independently instantiated pinned seed")
    calls = [json.loads(l) for l in (root / (prefix + "/tool-contexts.jsonl")).read_text().splitlines()]
    journal = [json.loads(l) for l in (root / (prefix + "/model-journal.jsonl")).read_text().splitlines()]
    task = read(root / (prefix + "/turn-1/task-get.response.raw.json"))["result"]
    receipt = read(root / (prefix + "/actor-receipt.json"))
    require(receipt["provider_calls"] == 0 and receipt["original_lifespan_exited"] is True,
            "reference scope or lifecycle boundary differs")
    observed = check_observation(before, after, calls, journal, task, public["public"]["turns"][0]["text"])
    inputs_to_enumerate = [value for s in seeded["services"] for value in (s["name"], s["name"].upper(), " " + s["name"].upper() + " ")]
    inputs_to_enumerate += ["", "bad slug", "-inventory", "unknown-service"]
    worlds = [{"input": value, "oracle": status_oracle(seeded, value)} for value in inputs_to_enumerate]
    require(len(worlds) == 28 and sum(w["oracle"]["branch"] == "observed_service" for w in worlds) == 24,
            "finite fragment enumeration incomplete")
    return {"schema_version": "agentops-owned-read-fragment-qualification/1", "status": "passed_source_bound_development_fragment",
            "candidate_id": case_id, "original_split": "development", "exact_input_bindings": inputs,
            "observed_projection": observed, "finite_input_worlds": worlds, "finite_world_count": len(worlds),
            "fragment_oracle_complete_for_declared_28_inputs": True, "full_task_oracle_complete": False,
            "business_state_unchanged": True, "grounded_read_then_terminal_then_answer_observed": True,
            "semantic_gold_validated_by_humans": False, "qualified_confirmatory_tasks": 0,
            "new_application_runtime_calls": 0, "new_provider_calls": 0,
            "source_sql_executed_only_in_owned_memory": True,
            "limits": ["Complete only for the enumerated static read-state projection, not all arbitrary original application actions or opaque model continuations.",
                       "Free-text relevance, incidental note policy, allowed alternative trajectories and private gold still need human judgment.",
                       "A retained deterministic fixture is not a fresh original application trial, untouched holdout, runtime authentication, qualified bridge or study episode.",
                       "No gate receives private evaluator material and no admission/efficiency advantage is inferred."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "refusing existing qualification output")
    result = qualify(args.root)
    result["oracle_source_sha256"] = sha(Path(__file__))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "finite_worlds": result["finite_world_count"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
