"""Temporary SQLite fixtures; no application, SDK or model execution."""
from copy import deepcopy
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from interoperability import agentops_raw_events_v1 as exporter


def event(identity, timestamp, part, author="agent"):
    return {"id": identity, "invocation_id": "invocation", "timestamp": timestamp,
            "author": author, "content": {"role": "model" if author != "user" else "user", "parts": [part]},
            "actions": {"state_delta": {}}, "custom_metadata": {"retained": "original"}}


class RawEventExporterTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.database = self.root / "input" / "runtime.db"
        self.database.parent.mkdir()
        self.output = self.root / "export"
        self.events = [
            event("z-call", 10, {"function_call": {"id": "original-call", "name": "restart_service", "args": {"name": "inventory"}}}),
            event("y-pending", 11, {"function_response": {"id": "original-call", "name": "restart_service", "response": {"error": "confirmation required"}}}),
            event("x-confirm", 12, {"function_call": {"id": "confirmation", "name": "adk_request_confirmation", "args": {"originalFunctionCall": {"id": "original-call"}}}}),
            event("w-answer", 13, {"function_response": {"id": "confirmation", "name": "adk_request_confirmation", "response": {"confirmed": True}}}, author="user"),
            event("v-executed", 14, {"function_response": {"id": "original-call", "name": "restart_service", "response": {"result": "executed", "audit": {"id": 1}}}}),
        ]
        with closing(sqlite3.connect(self.database)) as connection, connection:
            for table, columns in exporter.TABLES.items():
                fields = ",".join(chr(34)+column+chr(34)+" TEXT" for column in columns)
                primary = ",".join(chr(34)+column+chr(34) for column in exporter.PRIMARY_KEYS[table])
                connection.execute(f'CREATE TABLE "{table}" ({fields},PRIMARY KEY ({primary}))')
            for name, (table, columns) in exporter.INDEXES.items():
                fields = ",".join(chr(34)+name+chr(34)+( " DESC" if descending else "") for name, descending in columns)
                connection.execute(f'CREATE INDEX "{name}" ON "{table}" ({fields})')
            connection.execute("INSERT INTO sessions VALUES (?,?,?,?,?,?)", ("app", "user", "session", '{"retained":true}', "2026-01-01", "2026-01-01"))
            connection.execute("INSERT INTO adk_internal_metadata VALUES (?,?)", ("schema_version", "1"))
        self.replace_events(self.events)

    def replace_events(self, events):
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute("DELETE FROM events")
            for item in events:
                connection.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?)", (item["id"], "app", "user", "session", "invocation", "2026-01-01", json.dumps(item)))

    def export(self):
        return exporter.export_database(self.database, self.output)

    def test_raw_bytes_json_and_repeated_confirmation_phase_responses_preserved(self):
        before = self.database.read_bytes()
        result = self.export()
        self.assertEqual(result["status"], "passed")
        self.assertEqual((result["events"], result["function_calls"], result["function_responses"]), (5, 2, 3))
        self.assertTrue(result["source_unchanged"])
        self.assertTrue(result["captured_files_unchanged"])
        self.assertEqual(self.database.read_bytes(), before)
        self.assertEqual((self.output / "input/runtime.db").read_bytes(), before)
        decoded = json.loads((self.output / "decoded-tables.json").read_bytes())
        raw = json.loads((self.output / "raw-tables.json").read_bytes())
        self.assertEqual([row["event_data"] for row in decoded["events"]], self.events)
        self.assertEqual([json.loads(row["event_data"]) for row in raw["events"]], self.events)
        observations = json.loads((self.output / "function-observations.json").read_bytes())
        phase_responses = [row for row in observations if row["kind"] == "function_response" and row["function_id"] == "original-call"]
        self.assertEqual([row["event_id"] for row in phase_responses], ["y-pending", "v-executed"])
        self.assertFalse(result["causal_order_proven"])
        self.assertFalse(result["complete_event_stream_proven"])
        self.assertEqual(result["graded_task_outcomes"], 0)

    def test_physical_order_ties_reversals_and_same_event_batches_are_retained(self):
        events = deepcopy(self.events)
        events[1]["timestamp"] = 9
        events[2]["timestamp"] = 9
        events[0]["content"]["parts"].append({"function_call": {"id": "parallel", "name": "get_incident", "args": {"incident_id": "INC-002"}}})
        self.replace_events(events)
        self.assertEqual(self.export()["status"], "passed")
        ordering = json.loads((self.output / "ordering.json").read_bytes())
        decoded = json.loads((self.output / "decoded-tables.json").read_bytes())
        self.assertEqual([row["id"] for row in decoded["events"]], [item["id"] for item in events])
        self.assertEqual(ordering["timestamp_reversals_in_physical_order"], [1])
        self.assertEqual(ordering["equal_timestamp_groups"], [["y-pending", "x-confirm"]])
        self.assertEqual(ordering["same_event_multiple_call_batches"], ["z-call"])

    def test_duplicate_json_key_is_rejected_and_failure_plan_retained(self):
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute("UPDATE events SET event_data=? WHERE id=?", ('{"id":"wrong","id":"z-call"}', "z-call"))
        result = self.export()
        self.assertEqual(result["status"], "failed")
        self.assertIn("Duplicate JSON key", result["error"])
        self.assertTrue((self.output / "plan.json").is_file())
        self.assertTrue((self.output / "result.json").is_file())

    def test_event_row_identity_mismatch_is_rejected(self):
        events = deepcopy(self.events)
        events[0]["invocation_id"] = "unrelated"
        self.replace_events(events)
        self.assertEqual(self.export()["status"], "failed")

    def test_absent_session_is_rejected(self):
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute("DELETE FROM sessions")
        self.assertEqual(self.export()["status"], "failed")

    def test_missing_schema_and_extra_columns_are_rejected(self):
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute("ALTER TABLE events ADD COLUMN undocumented TEXT")
        self.assertEqual(self.export()["status"], "failed")

    def test_missing_function_id_is_retained_as_incomplete_identity(self):
        events = deepcopy(self.events)
        del events[0]["content"]["parts"][0]["function_call"]["id"]
        self.replace_events(events)
        self.assertEqual(self.export()["status"], "passed")
        observations = json.loads((self.output / "function-observations.json").read_bytes())
        self.assertFalse(observations[0]["function_identity_complete"])
        self.assertIsNone(observations[0]["function_id"])

    def test_camelcase_function_parts_are_not_silently_omitted(self):
        events = deepcopy(self.events)
        part = events[0]["content"]["parts"][0]
        part["functionCall"] = part.pop("function_call")
        self.replace_events(events)
        result = self.export()
        self.assertEqual(result["status"], "failed")
        self.assertIn("camelCase", result["error"])

    def test_nonfinite_timestamp_and_json_constants_are_rejected(self):
        events = deepcopy(self.events)
        events[0]["timestamp"] = float("inf")
        self.replace_events(events)
        self.assertEqual(self.export()["status"], "failed")

    def test_existing_output_is_refused_without_mutation(self):
        self.assertEqual(self.export()["status"], "passed")
        hashes = {path.relative_to(self.output): hashlib.sha256(path.read_bytes()).hexdigest() for path in self.output.rglob("*") if path.is_file()}
        with self.assertRaises(ValueError):
            self.export()
        self.assertEqual(hashes, {path.relative_to(self.output): hashlib.sha256(path.read_bytes()).hexdigest() for path in self.output.rglob("*") if path.is_file()})

    def test_existing_wal_is_refused_before_database_read(self):
        Path(str(self.database) + "-wal").write_bytes(b"pending WAL")
        result = self.export()
        self.assertEqual(result["status"], "failed")
        self.assertIn("sidecars", result["error"])
        self.assertTrue((self.output / "plan.json").is_file())
        self.assertFalse((self.output / "input/runtime.db").exists())

    def test_source_mutation_during_export_invalidates_receipt(self):
        original = exporter._tables
        def mutate(path):
            result = original(path)
            with closing(sqlite3.connect(self.database)) as connection, connection:
                connection.execute("UPDATE sessions SET state=?", ('{"changed":true}',))
            return result
        with patch.object(exporter, "_tables", mutate):
            result = self.export()
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["source_unchanged"])

    def test_sidecar_created_during_export_invalidates_receipt(self):
        original = exporter._tables
        def mutate(path):
            result = original(path)
            Path(str(self.database) + "-wal").write_bytes(b"new WAL")
            return result
        with patch.object(exporter, "_tables", mutate):
            result = self.export()
        self.assertEqual(result["status"], "failed")
        self.assertIn("sidecars", result["preservation_error"])


if __name__ == "__main__":
    unittest.main()
