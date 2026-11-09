"""Loader-format fixtures only; no model, AgentOps import or final real export."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from interoperability import upstream_agentops_cases_v1 as loader


def encoded(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")


def turn(name, prompt):
    return {"invocation_id": name, "creation_timestamp": 0.0,
            "user_content": {"role": "user", "parts": [{"text": prompt}]},
            "final_response": {"role": "model", "parts": [{"text": "PRIVATE_EXPECTATION_SENTINEL"}]},
            "intermediate_data": {"tool_uses": [{"name": "lookup", "args": {"key": "EXPECTED_TOOL_SENTINEL", "flag": True}}],
                                  "intermediate_responses": []}}


class UpstreamCaseLoaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source, self.capture, self.output = (self.base / name for name in ("source", "capture", "export"))
        self.capture.mkdir()
        self.documents = {}
        for index, (filename, set_id) in enumerate(loader.SETS.items()):
            turns = [turn(f"invocation-{index}-0", f"Original user request {index}")]
            if index == 0:
                turns.append(turn("invocation-0-1", "Original follow-up with unicode: café"))
            self.documents[filename] = {"eval_set_id": set_id, "name": f"Fixture set {index}",
                "description": "Authored loader-format fixture, not upstream evidence", "eval_cases": [
                    {"eval_id": f"case-{index}", "conversation": turns, "creation_timestamp": 0.0,
                     "session_input": {"app_name": "fixture", "user_id": "fixture-user", "state": {"public": "session input"}}}]}
        for relative in loader.FILES:
            target = self.source / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.name in self.documents:
                target.write_bytes(encoded(self.documents[target.name]))
            else:
                target.write_bytes(b"Synthetic selected-file payload; this test does not execute it.\n")
        self.reseal()

    def reseal(self):
        records = []
        for relative in loader.FILES:
            raw = (self.source / relative).read_bytes()
            records.append({"source_relative_path": relative, "kind": "regular_file", "extracted": {
                "path": f"{loader.SOURCE_TREE}/{relative}", "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}})
        self.ingestion = {"schema_version": "user-source-archive-ingestion/1", "status": "passed",
            "source_tree": loader.SOURCE_TREE, "archive_root_and_comment_commit": loader.COMMIT,
            "all_regular_payload_bytes_match_archive": True, "all_archive_file_entries_accounted_for": True,
            "archive_changed": False, "records": records}
        (self.capture / "ingestion.json").write_bytes(encoded(self.ingestion))

    def change_document(self, filename, change):
        path = self.source / loader.EVAL_DIRECTORY / filename
        document = json.loads(path.read_bytes())
        change(document)
        path.write_bytes(encoded(document))
        self.reseal()

    def run_export(self, name=None):
        return loader.export_cases(self.source, self.capture, self.base / name if name else self.output)

    def test_separation_preserves_all_original_user_turns_and_evaluator_fields(self):
        result = self.run_export()
        self.assertEqual(result["status"], "passed")
        self.assertEqual((result["case_count"], result["turn_count"]), (3, 4))
        self.assertIs(result["source_inputs_unchanged"], True)
        self.assertIs(result["captured_outputs_unchanged"], True)
        self.assertEqual(len(result["source_checks"]), 7)
        application_raw = (self.output / "application/cases.json").read_bytes()
        application = json.loads(application_raw)
        expected = json.loads((self.output / "evaluator/expectations.json").read_bytes())
        self.assertNotIn(b"PRIVATE_EXPECTATION_SENTINEL", application_raw)
        self.assertNotIn(b"EXPECTED_TOOL_SENTINEL", application_raw)
        self.assertNotIn(b'"final_response"', application_raw)
        self.assertNotIn(b'"intermediate_data"', application_raw)
        self.assertEqual(application["provenance"]["kind"], "public-source-derived-development")
        self.assertIs(application["provenance"]["held_out"], False)
        self.assertIs(application["provenance"]["independent_human_review"], False)
        for index, document in enumerate(self.documents.values()):
            original = document["eval_cases"][0]
            public, private = application["cases"][index], expected["cases"][index]
            self.assertEqual(public["eval_id"], original["eval_id"])
            self.assertEqual(public["session_input"], original["session_input"])
            self.assertEqual(len(public["conversation"]), len(original["conversation"]))
            for a, b, c in zip(original["conversation"], public["conversation"], private["conversation"]):
                self.assertEqual(b["user_content"], a["user_content"])
                self.assertEqual(b["invocation_id"], a["invocation_id"])
                self.assertEqual(c["final_response"], a["final_response"])
                self.assertEqual(c["intermediate_data"], a["intermediate_data"])
                self.assertIs(c["intermediate_data"]["tool_uses"][0]["args"]["flag"], True)
        for relative in loader.FILES:
            self.assertEqual((self.source / relative).read_bytes(), (self.output / "source" / relative).read_bytes())

    def test_source_hash_drift_retains_failure_without_exporting_application_inputs(self):
        path = self.source / loader.FILES[0]
        path.write_bytes(path.read_bytes() + b" ")
        result = self.run_export()
        self.assertEqual(result["status"], "failed")
        self.assertIn("Source hash or size drift", result["error"])
        self.assertFalse((self.output / "application/cases.json").exists())
        self.assertTrue((self.output / "plan.json").is_file())
        self.assertEqual(json.loads((self.output / "result.json").read_bytes())["status"], "failed")
        original = (self.output / "result.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "overwrite"):
            self.run_export()
        self.assertEqual((self.output / "result.json").read_bytes(), original)

    def test_duplicate_case_ids_within_and_across_sets_are_rejected(self):
        self.change_document("ops.evalset.json", lambda d: d["eval_cases"].append(deepcopy(d["eval_cases"][0])))
        self.assertIn("Duplicate case id", self.run_export("duplicate-within")["error"])
        path = self.source / loader.FILES[0]
        path.write_bytes(encoded(self.documents["ops.evalset.json"]))
        self.change_document("workflow.evalset.json", lambda d: d["eval_cases"][0].update(eval_id="case-0"))
        self.assertIn("Duplicate case id", self.run_export("duplicate-across")["error"])

    def test_duplicate_turn_identity_is_rejected(self):
        self.change_document("ops.evalset.json", lambda d: d["eval_cases"][0]["conversation"][1].update(invocation_id="invocation-0-0"))
        self.assertIn("Duplicate invocation", self.run_export()["error"])

    def test_malformed_and_extra_fields_are_not_silently_dropped(self):
        changes = (
            lambda d: d.update(unrecognized_source_field="value"),
            lambda d: d["eval_cases"][0]["conversation"][0]["user_content"].update(final_response="leak"),
            lambda d: d["eval_cases"][0]["conversation"][0].update(creation_timestamp=True),
            lambda d: d["eval_cases"][0]["conversation"][0]["intermediate_data"].update(tool_uses="not a list"),
            lambda d: d["eval_cases"][0]["conversation"][0]["intermediate_data"]["tool_uses"][0].update(args=[]),
            lambda d: d["eval_cases"][0]["conversation"][0]["final_response"].update(parts=[]),
        )
        for index, change in enumerate(changes):
            with self.subTest(index=index):
                path = self.source / loader.FILES[0]
                path.write_bytes(encoded(self.documents["ops.evalset.json"]))
                self.change_document("ops.evalset.json", change)
                result = self.run_export(f"malformed-{index}")
                self.assertEqual(result["status"], "failed")
                self.assertFalse((self.base / f"malformed-{index}/application/cases.json").exists())

    def test_duplicate_json_keys_and_nonfinite_numbers_are_rejected_after_rehash(self):
        original = encoded(self.documents["ops.evalset.json"])
        alterations = (b'{"eval_set_id":"duplicate",' + original[1:],
                       original.replace(b'"creation_timestamp": 0.0', b'"creation_timestamp": NaN', 1),
                       original.replace(b'"creation_timestamp": 0.0', b'"creation_timestamp": 1e999', 1))
        for index, raw in enumerate(alterations):
            with self.subTest(index=index):
                (self.source / loader.FILES[0]).write_bytes(raw)
                self.reseal()
                self.assertEqual(self.run_export(f"invalid-json-{index}")["status"], "failed")

    def test_extra_evalset_and_missing_selected_file_fail_but_unselected_docs_are_ignored(self):
        extra = self.source / loader.EVAL_DIRECTORY / "extra.evalset.json"
        extra.write_bytes(b"{}")
        self.assertIn("extra eval-set", self.run_export("extra")["error"])
        extra.unlink()
        (extra.parent / "README.md").write_text("An upstream directory contains other nonselected sources.", encoding="utf-8")
        self.assertEqual(self.run_export("unselected-document")["status"], "passed")
        (self.source / "agents/data/incidents.db").unlink()
        self.assertEqual(self.run_export("missing-seed")["status"], "failed")

    def test_ingestion_identity_missing_selected_and_duplicate_digest_records_fail(self):
        changes = (
            lambda d: d.update(archive_root_and_comment_commit="0" * 40),
            lambda d: d["records"].pop(),
            lambda d: d["records"].append(deepcopy(d["records"][0])),
            lambda d: d["records"][0]["extracted"].update(bytes=True),
        )
        for index, change in enumerate(changes):
            with self.subTest(index=index):
                self.reseal()
                change(self.ingestion)
                (self.capture / "ingestion.json").write_bytes(encoded(self.ingestion))
                self.assertEqual(self.run_export(f"bad-capture-{index}")["status"], "failed")

    def test_existing_outputs_and_outputs_inside_inputs_are_refused_without_modification(self):
        self.output.mkdir()
        marker = self.output / "keep.txt"
        marker.write_bytes(b"keep")
        with self.assertRaisesRegex(ValueError, "overwrite"):
            self.run_export()
        self.assertEqual(marker.read_bytes(), b"keep")
        for root in (self.source, self.capture):
            with self.assertRaisesRegex(ValueError, "outside"):
                loader.export_cases(self.source, self.capture, root / "new-export")
            self.assertFalse((root / "new-export").exists())

    def test_source_mutation_after_projection_invalidates_the_export(self):
        original_write = loader._write
        def alter_source_after_projection(path, raw):
            original_write(path, raw)
            if path.name == "cases.json":
                target = self.source / "agents/data/sql/seed.sql"
                target.write_bytes(target.read_bytes() + b"changed during export")
        with patch.object(loader, "_write", side_effect=alter_source_after_projection):
            result = self.run_export()
        self.assertEqual(result["status"], "failed")
        self.assertIs(result["source_inputs_unchanged"], False)
        self.assertIn("Source changed during export", result["error"])

    def test_captured_or_projected_output_mutation_is_rejected(self):
        original_write = loader._write
        for index, target_relative in enumerate((f"source/{loader.FILES[0]}", "evaluator/expectations.json")):
            output = self.base / f"mutated-export-{index}"
            def alter_output_after_projection(path, raw):
                original_write(path, raw)
                if path.name == "source-sets.json":
                    target = output / target_relative
                    target.write_bytes(target.read_bytes() + b" ")
            with self.subTest(target=target_relative), patch.object(loader, "_write", side_effect=alter_output_after_projection):
                result = loader.export_cases(self.source, self.capture, output)
            self.assertEqual(result["status"], "failed")
            self.assertIn("changed during export", result["error"])
            self.assertIs(result["source_inputs_unchanged"], True)
            self.assertIs(result["captured_outputs_unchanged"], False)


if __name__ == "__main__":
    unittest.main()
