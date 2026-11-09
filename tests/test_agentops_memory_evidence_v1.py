"""Temporary source-schema fixtures; no original DB, application or SDK run."""
import ast
from copy import deepcopy
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from interoperability import agentops_memory_evidence_v1 as memory


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "external/agentops-c806b7f1/agents/python/src/agent/longterm.py"


def original_schema():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    assignments = [node for node in tree.body if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == "_SCHEMA" for target in node.targets)]
    if len(assignments) != 1:
        raise AssertionError("original memory schema literal not unique")
    return ast.literal_eval(assignments[0].value)


class MemoryEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.state = self.root / "state"
        self.state.mkdir()
        self.path = self.state / "memory.db"

    def prepare(self, notes=()):
        connection = sqlite3.connect(self.path)
        try:
            connection.executescript(original_schema())
            for row in notes:
                connection.execute("INSERT INTO incident_notes(ts,user_id,incident_id,note) VALUES (?,?,?,?)", row)
            connection.commit()
        finally:
            connection.close()

    def row(self, text="I raised the api-gateway memory limit to 2Gi as a stopgap.", user="A2A_USER_context"):
        return ("2026-10-29T17:00:00Z", user, "INC-010", text)

    def test_absent_lazy_store_observation_does_not_create_database(self):
        before = list(self.state.iterdir())
        result = memory.snapshot_memory(self.path, observation_mode="live")
        self.assertEqual(result["status"], "absent")
        self.assertEqual(result["notes"], [])
        self.assertFalse(result["source_closed_proven"])
        self.assertFalse(result["continuous_mutation_absence_proven"])
        self.assertEqual(list(self.state.iterdir()), before)

    def test_exact_inert_original_schema_and_rows_are_recorded_read_only(self):
        self.prepare([self.row(), self.row("second", "other-user")])
        before = self.path.read_bytes()
        result = memory.snapshot_memory(self.path)
        self.assertEqual(result["status"], "recorded")
        self.assertEqual(result["row_count"], 2)
        self.assertEqual(result["notes"][0], {"id": 1, "ts": self.row()[0], "user_id": self.row()[1], "incident_id": "INC-010", "note": self.row()[3]})
        self.assertEqual(result["sqlite_sequence"], [{"name": "incident_notes", "seq": 2}])
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.state.iterdir()), [self.path])

    def test_empty_materialized_store_is_distinct_from_absence(self):
        self.prepare()
        result = memory.snapshot_memory(self.path)
        self.assertEqual(result["status"], "recorded")
        self.assertTrue(result["exists_observed"])
        self.assertEqual(result["notes"], [])
        self.assertEqual(result["sqlite_sequence"], [])

    def test_duplicate_and_other_user_rows_are_preserved_for_grader(self):
        self.prepare([self.row(), self.row(), self.row("unrelated", "other")])
        result = memory.snapshot_memory(self.path)
        self.assertEqual(result["row_count"], 3)
        self.assertEqual([row["id"] for row in result["notes"]], [1, 2, 3])
        self.assertEqual(result["notes"][2]["user_id"], "other")

    def test_sequence_keeps_deleted_note_evidence(self):
        self.prepare([self.row()])
        connection = sqlite3.connect(self.path)
        connection.execute("DELETE FROM incident_notes")
        connection.commit()
        connection.close()
        result = memory.snapshot_memory(self.path)
        self.assertEqual(result["status"], "recorded")
        self.assertEqual(result["notes"], [])
        self.assertEqual(result["sqlite_sequence"], [{"name": "incident_notes", "seq": 1}])

    def test_unknown_schema_objects_are_not_silently_omitted(self):
        for sql in ("CREATE TABLE extra(x)", "CREATE VIEW extra AS SELECT note FROM incident_notes", "CREATE TRIGGER extra AFTER INSERT ON incident_notes BEGIN SELECT 1; END"):
            with self.subTest(sql=sql):
                if self.path.exists():
                    self.path.unlink()
                self.prepare()
                connection = sqlite3.connect(self.path)
                connection.execute(sql)
                connection.commit()
                connection.close()
                before = self.path.read_bytes()
                result = memory.snapshot_memory(self.path)
                self.assertEqual(result["status"], "unsupported")
                self.assertEqual(self.path.read_bytes(), before)

    def test_missing_original_index_is_unsupported(self):
        self.prepare()
        connection = sqlite3.connect(self.path)
        connection.execute("DROP INDEX idx_notes_user_incident")
        connection.commit()
        connection.close()
        self.assertEqual(memory.snapshot_memory(self.path)["status"], "unsupported")

    def test_nonoriginal_column_constraint_is_unsupported(self):
        connection = sqlite3.connect(self.path)
        connection.executescript(memory.TABLE_SQL.replace("note TEXT NOT NULL", "note TEXT") + ";" + memory.INDEX_SQL)
        connection.close()
        self.assertEqual(memory.snapshot_memory(self.path)["status"], "unsupported")

    def test_journal_sidecars_are_conservatively_refused_without_removal(self):
        self.prepare()
        for suffix in ("-wal", "-shm", "-journal"):
            sidecar = Path(str(self.path) + suffix)
            sidecar.write_bytes(b"retained sidecar")
            result = memory.snapshot_memory(self.path, observation_mode="live")
            self.assertEqual(result["status"], "unsupported")
            self.assertEqual(sidecar.read_bytes(), b"retained sidecar")
            sidecar.unlink()

    def test_invalid_header_and_unknown_user_version_are_unsupported(self):
        self.path.write_bytes(b"not SQLite")
        self.assertEqual(memory.snapshot_memory(self.path)["status"], "unsupported")
        self.path.unlink()
        self.prepare()
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA user_version=2")
        connection.close()
        self.assertEqual(memory.snapshot_memory(self.path)["status"], "unsupported")

    def test_behind_sequence_is_rejected(self):
        self.prepare([self.row()])
        connection = sqlite3.connect(self.path)
        connection.execute("UPDATE sqlite_sequence SET seq=0")
        connection.commit()
        connection.close()
        self.assertEqual(memory.snapshot_memory(self.path)["status"], "unsupported")

    def test_live_physical_change_is_recorded_without_claiming_reader_mutation(self):
        self.prepare()
        actual = memory._read
        def read_and_external_write(path):
            result = actual(path)
            connection = sqlite3.connect(path)
            connection.execute("INSERT INTO incident_notes(ts,user_id,incident_id,note) VALUES (?,?,?,?)", self.row())
            connection.commit()
            connection.close()
            return result
        with patch.object(memory, "_read", side_effect=read_and_external_write):
            result = memory.snapshot_memory(self.path, observation_mode="live")
        self.assertEqual(result["status"], "recorded")
        self.assertFalse(result["physical_file_unchanged_during_observation"])
        self.assertEqual(result["notes"], [])
        self.assertFalse(result["source_closed_proven"])

    def test_archived_physical_change_is_not_accepted(self):
        self.prepare()
        actual = memory._read
        def read_and_external_write(path):
            result = actual(path)
            connection = sqlite3.connect(path)
            connection.execute("INSERT INTO incident_notes(ts,user_id,incident_id,note) VALUES (?,?,?,?)", self.row())
            connection.commit()
            connection.close()
            return result
        with patch.object(memory, "_read", side_effect=read_and_external_write):
            result = memory.snapshot_memory(self.path)
        self.assertEqual(result["status"], "unsupported")

    def test_export_preserves_raw_and_logical_closed_fixture(self):
        self.prepare([self.row(), self.row("other", "someone")])
        before = self.path.read_bytes()
        result = memory.export_memory(self.path, self.root / "export")
        self.assertEqual(result["status"], "recorded")
        self.assertTrue(result["captured_files_unchanged"])
        self.assertEqual((self.root / "export/input/memory.db").read_bytes(), before)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertFalse(result["source_closed_proven"])
        self.assertEqual(result["graded_source_cases"], 0)

    def test_export_absence_preserves_point_in_time_observation(self):
        result = memory.export_memory(self.path, self.root / "export")
        self.assertEqual(result["status"], "recorded")
        self.assertEqual(result["snapshot"]["status"], "absent")
        self.assertFalse(self.path.exists())
        self.assertFalse((self.root / "export/input").exists())

    def test_existing_and_overlapping_export_allocations_refused(self):
        output = self.root / "existing"
        output.mkdir()
        for target in (output, self.state / "export"):
            with self.assertRaises(ValueError):
                memory.export_memory(self.path, target)

    def test_bound_limits_fail_without_database_modification(self):
        self.prepare([self.row(), self.row("second")])
        before = self.path.read_bytes()
        with patch.object(memory, "MAX_BYTES", 1):
            self.assertEqual(memory.snapshot_memory(self.path)["status"], "unsupported")
        with patch.object(memory, "MAX_ROWS", 1):
            self.assertEqual(memory.snapshot_memory(self.path)["status"], "unsupported")
        self.assertEqual(self.path.read_bytes(), before)

    def test_unsupported_copy_cannot_pass_by_matching_notes_only(self):
        self.prepare([self.row()])
        actual = memory.snapshot_memory
        def rejected_copy(path, **kwargs):
            result = actual(path, **kwargs)
            if "input" in Path(path).parts:
                result["status"] = "unsupported"
            return result
        with patch.object(memory, "snapshot_memory", side_effect=rejected_copy):
            result = memory.export_memory(self.path, self.root / "export")
        self.assertEqual(result["status"], "failed")

    def test_clean_wal_header_is_refused_before_any_sqlite_read(self):
        self.prepare([self.row()])
        connection = sqlite3.connect(self.path)
        self.assertEqual(connection.execute("PRAGMA journal_mode=WAL").fetchone(), ("wal",))
        connection.close()
        before = self.path.read_bytes()
        self.assertEqual(before[18:20], b"\x02\x02")
        self.assertEqual(list(self.state.iterdir()), [self.path])
        with patch.object(memory.sqlite3, "connect", side_effect=AssertionError("must not open WAL source")):
            result = memory.snapshot_memory(self.path, observation_mode="live")
        self.assertEqual(result["status"], "unsupported")
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.state.iterdir()), [self.path])

    def test_orphan_sidecar_is_not_silent_lazy_absence(self):
        for suffix in ("-wal", "-shm", "-journal"):
            sidecar = Path(str(self.path) + suffix)
            sidecar.write_bytes(b"orphan memory evidence")
            with patch.object(memory.sqlite3, "connect", side_effect=AssertionError("must not open absent main")):
                result = memory.snapshot_memory(self.path)
            self.assertEqual(result["status"], "unsupported")
            self.assertFalse(self.path.exists())
            self.assertEqual(sidecar.read_bytes(), b"orphan memory evidence")
            sidecar.unlink()


if __name__ == "__main__":
    unittest.main()
