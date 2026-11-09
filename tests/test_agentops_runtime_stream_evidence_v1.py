"""Closed journal and resealed structural mutations; synthetic fixtures only."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from agentops_runtime_stream_v1 import RunAsyncJournal
from interoperability.agentops_runtime_stream_evidence_v1 import read_closed_journal


def encoded(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False, indent=2) + "\n").encode()


def identity(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


class JournalEvidenceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="journal-reader-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name) / "journal"
        async def original(**kwargs):
            for index in (1, 2):
                yield {"id": f"event-{kwargs['session_id']}-{index}", "invocation_id": kwargs["session_id"],
                       "author": "synthetic-agent", "content": {"parts": [{"text": f"value-{index}"}]}}
        journal = RunAsyncJournal(original, self.directory, event_serializer=encoded,
                                  content_serializer=encoded, config_serializer=encoded)
        for session in ("session-1", "session-2"):
            async for _ in journal.run_async(user_id="user", session_id=session,
                                             new_message={"role": "user", "parts": [{"text": session}]},
                                             run_config=None, state_delta=None):
                pass
        journal.finish()

    def read(self, path="result.json"):
        return json.loads((self.directory / path).read_bytes())

    def write(self, path, value):
        (self.directory / path).write_bytes(encoded(value))

    def reseal(self, *paths):
        root = self.read()
        for path in paths:
            root["files"][path] = identity((self.directory / path).read_bytes())
        self.write("result.json", root)

    def change_call(self, change, index=1):
        path = f"invocations/{index:06d}/result.json"
        call = self.read(path)
        change(call)
        self.write(path, call)
        root = self.read()
        for key in root["invocations"][index - 1]:
            root["invocations"][index - 1][key] = call[key]
        self.write("result.json", root)
        self.reseal(path)

    def assertRejected(self):
        with self.assertRaises(ValueError):
            read_closed_journal(self.directory)

    def test_complete_journal_retains_input_events_and_explicit_sequence(self):
        before = {path.relative_to(self.directory).as_posix(): path.read_bytes()
                  for path in self.directory.rglob("*") if path.is_file()}
        result = read_closed_journal(self.directory,
                                     expected_receipt_identity=identity((self.directory / "result.json").read_bytes()),
                                     expected_observer_identity=identity((self.directory / "source/agentops_runtime_stream_v1.py").read_bytes()),
                                     expected_call_inputs=[{"user_id": "user", "session_id": session,
                                                            "new_message": {"role": "user", "parts": [{"text": session}]},
                                                            "run_config": None} for session in ("session-1", "session-2")])
        self.assertEqual(result["status"], "validated")
        self.assertEqual([row["global_yield_sequence"] for row in result["ordered_event_records"]], [1, 2, 3, 4])
        self.assertEqual([row["invocation_id"] for row in result["ordered_events"]], ["session-1"] * 2 + ["session-2"] * 2)
        self.assertFalse(result["source_closed_proven"])
        self.assertFalse(result["causal_tool_execution_order_proven"])
        self.assertEqual(before, {path.relative_to(self.directory).as_posix(): path.read_bytes()
                                  for path in self.directory.rglob("*") if path.is_file()})

    def test_external_root_receipt_binding_rejects_mismatch(self):
        with self.assertRaisesRegex(ValueError, "root receipt binding"):
            read_closed_journal(self.directory, expected_receipt_identity={"bytes": 0, "sha256": "0" * 64})

    def test_external_observer_binding_rejects_mismatch(self):
        with self.assertRaisesRegex(ValueError, "observer source binding"):
            read_closed_journal(self.directory, expected_observer_identity={"bytes": 0, "sha256": "0" * 64})

    def test_external_input_binding_rejects_other_context(self):
        with self.assertRaisesRegex(ValueError, "input/context binding"):
            read_closed_journal(self.directory, expected_call_inputs=[{"session_id": "other"}, {}])

    def test_missing_optional_input_cannot_match_supplied_null(self):
        with self.assertRaisesRegex(ValueError, "input/context binding"):
            read_closed_journal(self.directory, expected_call_inputs=[{"invocation_id": None}, {}])

    def test_changed_event_bytes_are_rejected_without_resealing(self):
        self.write("invocations/000001/events/000001.json", {"id": "different"})
        self.assertRejected()

    def test_extra_pending_receipt_is_rejected(self):
        (self.directory / "result.json.pending").write_bytes(b"{}"); self.assertRejected()

    def test_extra_empty_directory_is_rejected(self):
        (self.directory / "unrecorded").mkdir(); self.assertRejected()

    def test_partial_root_flags_cannot_qualify(self):
        root = self.read(); root["capture_complete"] = False
        self.write("result.json", root); self.assertRejected()

    def test_resealed_partial_call_cannot_qualify(self):
        self.change_call(lambda row: row.update(original_termination="consumer_aclose"))
        self.assertRejected()

    def test_resealed_missing_cleanup_cannot_qualify(self):
        self.change_call(lambda row: row.update(original_aclose_completed=False))
        self.assertRejected()

    def test_resealed_global_duplicate_is_rejected(self):
        self.change_call(lambda row: row["events"][0].update(global_yield_sequence=2), index=2)
        self.assertRejected()

    def test_resealed_per_call_event_reordering_is_rejected(self):
        self.change_call(lambda row: row["events"].reverse())
        self.assertRejected()

    def test_resealed_mismatched_actual_invocation_is_rejected(self):
        path = "invocations/000001/events/000001.json"
        event = self.read(path); event["invocation_id"] = "other"
        self.write(path, event)
        self.change_call(lambda row: row["events"][0].update(identity((self.directory / path).read_bytes())))
        self.reseal(path); self.assertRejected()

    def test_root_summary_must_match_call_receipt(self):
        root = self.read(); root["invocations"][0]["events_seen"] = 3
        self.write("result.json", root); self.assertRejected()

    def test_resealed_input_reference_must_match_own_invocation(self):
        path = "invocations/000001/input.json"
        inputs = self.read(path)
        inputs["new_message"]["path"] = "invocations/000002/input/new_message.json"
        self.write(path, inputs); self.reseal(path); self.assertRejected()

    def test_resealed_supplied_identity_must_match_actual_ids(self):
        path = "invocations/000001/input.json"
        inputs = self.read(path); inputs["invocation_id"] = "other"
        inputs["supplied_known_fields"] = sorted(inputs["supplied_known_fields"] + ["invocation_id"])
        inputs["omitted_known_fields"].remove("invocation_id")
        self.write(path, inputs); self.reseal(path)
        self.change_call(lambda row: row.update(supplied_invocation_id_present=True, supplied_invocation_id="other",
                                                supplied_invocation_id_matches_all_observed=True))
        self.assertRejected()

    def test_resealed_boolean_event_ordinal_is_rejected(self):
        self.change_call(lambda row: row["events"][0].update(event_ordinal=True))
        self.assertRejected()

    def test_duplicate_json_root_key_is_rejected(self):
        raw = (self.directory / "result.json").read_bytes()
        (self.directory / "result.json").write_bytes(b'{"status":"recorded",' + raw[1:])
        self.assertRejected()

    def test_resealed_boolean_call_sequence_cannot_match_numeric_summary(self):
        path = "invocations/000001/result.json"
        receipt = self.read(path); receipt["invocation_sequence"] = True
        self.write(path, receipt); self.reseal(path); self.assertRejected()

    def test_resealed_boolean_summary_count_cannot_match_numeric_receipt(self):
        root = self.read(); root["invocations"][0]["original_aclose_completed"] = 1
        self.write("result.json", root); self.assertRejected()

    def test_float_manifest_size_cannot_match_integer_file_size(self):
        root = self.read(); root["files"]["plan.json"]["bytes"] = float(root["files"]["plan.json"]["bytes"])
        self.write("result.json", root); self.assertRejected()

    def test_float_external_receipt_size_is_rejected(self):
        item = identity((self.directory / "result.json").read_bytes()); item["bytes"] = float(item["bytes"])
        with self.assertRaisesRegex(ValueError, "root receipt binding"):
            read_closed_journal(self.directory, expected_receipt_identity=item)

    def test_resealed_float_event_size_is_rejected(self):
        self.change_call(lambda row: row["events"][0].update(bytes=float(row["events"][0]["bytes"])))
        self.assertRejected()

    def test_resealed_float_input_reference_size_is_rejected(self):
        path = "invocations/000001/input.json"
        inputs = self.read(path); inputs["new_message"]["bytes"] = float(inputs["new_message"]["bytes"])
        self.write(path, inputs); self.reseal(path); self.assertRejected()

    def test_journal_change_during_validation_is_rejected(self):
        from unittest.mock import patch
        from interoperability import agentops_runtime_stream_evidence_v1 as module
        original = module._inventory
        calls = 0
        def observed(path):
            nonlocal calls
            calls += 1
            if calls == 2:
                (self.directory / "late").write_bytes(b"late change")
            return original(path)
        with patch.object(module, "_inventory", side_effect=observed):
            self.assertRejected()


if __name__ == "__main__":
    unittest.main()
