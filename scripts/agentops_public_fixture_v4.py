"""Explicit public copied-data fixtures and observed-user partial note staging."""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_new(path, value):
    with path.open("x", encoding="utf-8") as target:
        json.dump(value, target, indent=2, allow_nan=False)
        target.write("\n")


def apply_data(case, data, public):
    recipe = public["public"]["fixture_recipe"]
    before = {p.relative_to(data).as_posix(): sha(p.read_bytes()) for p in data.rglob("*") if p.is_file()}
    applied = []
    for change in recipe["before_start_changes"]:
        if change["kind"] == "sqlite_row_update":
            table = change["table"]
            allowed = {"incidents": {"id", "severity", "opened_at", "status"}, "services": {"name", "status"}}
            if table not in allowed or not set(change["where"]) <= allowed[table] or not set(change["set"]) <= allowed[table]:
                raise ValueError("Unsupported declared fixture table/columns")
            if not change["where"] or not change["set"]:
                raise ValueError("Bounded declared row fixture required")
            with closing(sqlite3.connect(data / "incidents.db")) as connection, connection:
                assignment = ", ".join('"' + key + '"=?' for key in change["set"])
                predicate = " AND ".join('"' + key + '"=?' for key in change["where"])
                cursor = connection.execute('UPDATE "' + table + '" SET ' + assignment + " WHERE " + predicate,
                    (*change["set"].values(), *change["where"].values()))
                if cursor.rowcount != 1:
                    raise ValueError("Declared fixture did not change exactly one row")
        elif change["kind"] == "append_utf8_line":
            path = data / change["path"]
            if not path.resolve().is_relative_to((data / "logs").resolve()) or not path.is_file() or path.is_symlink():
                raise ValueError("Declared fixture must append to an existing copied log")
            with path.open("a", encoding="utf-8", newline="\n") as target:
                target.write(change["text"] + "\n")
        else:
            raise ValueError("Unsupported public fixture operation")
        applied.append(change)
    after = {p.relative_to(data).as_posix(): sha(p.read_bytes()) for p in data.rglob("*") if p.is_file()}
    result = {"schema_version": "agentops-public-data-fixture/4", "configuration": recipe["configuration"],
        "declared_changes": recipe["before_start_changes"], "applied_changes": applied,
        "data_before_sha256": before, "data_after_sha256": after, "original_sources_modified": False}
    write_new(case / "data-fixture-receipt.json", result)
    return result


def stage_notes(case, original, public, callback_context, state):
    recipe = public["public"]["fixture_recipe"]["memory_initialization"]
    if recipe["kind"] != "declared_note_rows" or (case / "fixture-receipt.json").exists():
        return None
    source = recipe["schema_source"]
    relative = Path(source["path"]).relative_to("external/agentops-c806b7f1")
    if sha((original / relative).read_bytes()) != source["sha256"]:
        raise ValueError("Declared memory schema source differs")
    from agent import longterm
    if (state / "memory.db").exists():
        raise ValueError("Note fixture requires an initially absent memory store")
    actual_user, actual_session = callback_context.user_id, callback_context.session.id
    if not actual_user or not actual_session:
        raise ValueError("Actual callback identity missing")
    applied, skipped = [], []
    with closing(sqlite3.connect(state / "memory.db")) as connection, connection:
        connection.executescript(longterm._SCHEMA)
        for row in recipe["rows"]:
            if row["user_id_label"] != "bank-user-a":
                skipped.append({"row": row, "reason": "No second actual runtime user was observed; do not invent its identity."})
                continue
            observed = {key: value for key, value in row.items() if key != "user_id_label"}
            observed["user_id"] = actual_user
            connection.execute("INSERT INTO incident_notes(id,ts,user_id,incident_id,note) VALUES (?,?,?,?,?)",
                (row["id"], row["ts"], actual_user, row["incident_id"], row["note"]))
            applied.append(observed)
    pending = ["Declared before-first-public-user-turn preload timing was not realized; fixture staged after actual user ingestion, before first model call."]
    if skipped:
        pending.append("Declared second-user fixture rows were not staged without an actual runtime identity binding.")
    result = {"schema_version": "agentops-observed-user-partial-note-fixture/4", "kind": "declared_note_rows",
        "schema_source": source, "actual_user_id": actual_user, "actual_session_id": actual_session,
        "initialized_before_first_model_call": True, "initialized_before_first_public_user_turn": False,
        "user_id_mapping": {"bank-user-a": actual_user, "bank-user-b": None},
        "declared_rows": recipe["rows"], "applied_rows": applied, "skipped_rows": skipped, "obligations_pending": pending}
    write_new(case / "fixture-receipt.json", result)
    return result
