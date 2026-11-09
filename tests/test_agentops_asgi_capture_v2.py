"""Synthetic ASGI/memory boundaries only; no original application import."""
import asyncio
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from agentops_asgi_capture_v2 import Capture
from interoperability.agentops_memory_evidence_v1 import TABLE_SQL, INDEX_SQL


class MemoryCaptureTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="agentops-memory-asgi-")
        self.addCleanup(temporary.cleanup)
        self.output = Path(temporary.name)
        (self.output / "state").mkdir()
        self.business = {"path": "state/incidents.db", "path_base": "run"}
        self.enterContext(patch("agentops_asgi_capture_v1.evidence.database_snapshot", return_value=self.business))
        self.scope = {"type": "http", "method": "POST", "path": "/", "http_version": "1.1",
                      "headers": [], "query_string": b""}
        self.request = {"type": "http.request", "body": b"input"}
        self.messages = [{"type": "http.response.start", "status": 200},
                         {"type": "http.response.body", "body": b"result"}]
        self.sent = []

    async def receive(self):
        return self.request

    async def send(self, message):
        self.sent.append(message)

    async def app(self, scope, receive, send):
        self.assertIs(scope, self.scope)
        self.assertIs(await receive(), self.request)
        for message in self.messages:
            await send(message)

    def read(self, name, sequence=1):
        return json.loads((self.output / f"wire/{sequence:06d}/{name}").read_bytes())

    def create_memory(self):
        with closing(sqlite3.connect(self.output / "state/memory.db")) as connection, connection:
            connection.execute(TABLE_SQL)
            connection.execute(INDEX_SQL)

    async def test_lazy_absence_is_recorded_without_creating_database(self):
        capture = Capture(self.app, self.output)
        await capture(self.scope, self.receive, self.send)
        self.assertEqual(self.read("before.memory.snapshot.json")["status"], "absent")
        self.assertEqual(self.read("after.memory.snapshot.json")["status"], "absent")
        self.assertFalse((self.output / "state/memory.db").exists())
        self.assertEqual(self.read("before.snapshot.json")["database"], self.business)
        self.assertEqual(self.sent, self.messages)
        for sent, original in zip(self.sent, self.messages):
            self.assertIs(sent, original)
        self.assertEqual(capture.memory_errors, [])

    async def test_original_memory_write_is_visible_between_boundaries(self):
        async def app(scope, receive, send):
            self.create_memory()
            with closing(sqlite3.connect(self.output / "state/memory.db")) as connection, connection:
                connection.execute("INSERT INTO incident_notes(ts,user_id,incident_id,note) VALUES(?,?,?,?)",
                                   ("synthetic-time", "user", "INC-1", "synthetic note"))
            await self.app(scope, receive, send)
        capture = Capture(app, self.output)
        await capture(self.scope, self.receive, self.send)
        self.assertEqual(self.read("before.memory.snapshot.json")["status"], "absent")
        after = self.read("after.memory.snapshot.json")
        self.assertEqual(after["status"], "recorded")
        self.assertEqual(after["notes"][0]["note"], "synthetic note")
        self.assertFalse(after["source_closed_proven"])
        self.assertFalse(after["cross_store_atomic_snapshot"])

    async def test_materialized_empty_store_is_distinct_and_bytes_unchanged(self):
        self.create_memory()
        database = self.output / "state/memory.db"
        original = database.read_bytes()
        capture = Capture(self.app, self.output)
        await capture(self.scope, self.receive, self.send)
        before = self.read("before.memory.snapshot.json")
        self.assertEqual(before["status"], "recorded")
        self.assertEqual(before["row_count"], 0)
        self.assertEqual(database.read_bytes(), original)
        self.assertEqual(sorted(path.name for path in database.parent.iterdir()), ["memory.db"])

    async def test_unsupported_schema_does_not_change_application_outcome(self):
        with closing(sqlite3.connect(self.output / "state/memory.db")) as connection, connection:
            connection.execute("CREATE TABLE unexpected(x)")
        capture = Capture(self.app, self.output)
        await capture(self.scope, self.receive, self.send)
        self.assertEqual(self.read("before.memory.snapshot.json")["status"], "unsupported")
        self.assertEqual(self.read("exchange.json")["response_status"], 200)
        self.assertEqual(self.sent, self.messages)
        self.assertEqual(capture.errors, [])
        self.assertEqual(len(capture.memory_errors), 2)

    async def test_observer_failure_preserves_application_exception(self):
        async def app(scope, receive, send):
            await self.app(scope, receive, send)
            raise RuntimeError("original synthetic failure")
        capture = Capture(app, self.output)
        with patch("agentops_asgi_capture_v2.snapshot_memory", side_effect=OSError("observer failure")):
            with self.assertRaisesRegex(RuntimeError, "original synthetic failure"):
                await capture(self.scope, self.receive, self.send)
        self.assertEqual(len(capture.memory_errors), 2)
        self.assertIn("original synthetic failure", self.read("exchange.json")["error"])
        self.assertFalse((self.output / "wire/000001/before.memory.snapshot.json").exists())

    async def test_memory_receipt_write_failure_is_separate(self):
        from agentops_asgi_capture_v2 import evidence
        original_write = evidence.write_json
        def write(path, value):
            if path.name.endswith(".memory.snapshot.json"):
                raise OSError("synthetic disk failure")
            return original_write(path, value)
        capture = Capture(self.app, self.output)
        with patch("agentops_asgi_capture_v2.evidence.write_json", side_effect=write):
            await capture(self.scope, self.receive, self.send)
        self.assertEqual(capture.errors, [])
        self.assertEqual([row["status"] for row in capture.memory_errors], ["capture_failed", "capture_failed"])
        self.assertEqual(self.read("exchange.json")["response_status"], 200)

    async def test_non_http_scope_is_identical_and_creates_no_boundaries(self):
        scope = {"type": "lifespan"}
        async def app(actual, receive, send):
            self.assertIs(actual, scope)
            self.assertEqual(receive, self.receive)
            self.assertEqual(send, self.send)
        capture = Capture(app, self.output)
        await capture(scope, self.receive, self.send)
        self.assertEqual(list((self.output / "wire").iterdir()), [])
        self.assertEqual(capture.sequence, 0)

    async def test_concurrent_requests_keep_separate_boundary_files(self):
        entered = asyncio.Event()
        release = asyncio.Event()
        count = 0
        async def app(scope, receive, send):
            nonlocal count
            count += 1
            if count == 2:
                entered.set()
            await release.wait()
            await self.app(scope, receive, send)
        capture = Capture(app, self.output)
        tasks = [asyncio.create_task(capture(self.scope, self.receive, self.send)) for _ in range(2)]
        await asyncio.wait_for(entered.wait(), 5)
        release.set()
        await asyncio.gather(*tasks)
        for sequence in (1, 2):
            for boundary in ("before", "after"):
                self.assertEqual(self.read(boundary + ".memory.snapshot.json", sequence)["status"], "absent")
        self.assertEqual(capture.sequence, 2)


if __name__ == "__main__":
    unittest.main()
