"""New CLI regressions over retained SYNTHETIC instances; no native runtime.

The frozen boundary fixture contributes builders only; its tests are not run.
New journals are captured before use, with partial flags set at production.
"""
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
import test_agentops_case_boundary_evidence_v1 as boundary_fixture
from agentops_runtime_stream_v1 import RunAsyncJournal
from interoperability.agentops_runtime_stream_evidence_v1 import read_closed_journal
from interoperability.agentops_answer_schema_v1 import SOURCE_BINDINGS

SCRIPT = ROOT / "scripts/assess_upstream_agentops_case_v3.py"
spec = importlib.util.spec_from_file_location("synthetic_v3_cli_under_test", SCRIPT)
cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
SESSION = "00000000-0000-4000-8000-000000000001"
USER = "A2A_USER_" + SESSION
encoded = boundary_fixture.encoded
V2_SOURCE_SHA256 = "b52a711a7d222e6e554804353b29ba45f938ba7bf20d639065b6b9653aec39ce"


class CorrectedCliTests(unittest.TestCase):
    def setUp(self):
        self.before_v2 = (ROOT / "scripts/assess_upstream_agentops_case_v2.py").read_bytes()
        self.assertEqual(hashlib.sha256(self.before_v2).hexdigest(), V2_SOURCE_SHA256)
        self.builder = boundary_fixture.BoundaryTests()
        self.builder.setUp(); self.addCleanup(self.builder.doCleanups)
        self.case = next(item for item in json.loads((ROOT / "runs/upstream-agentops-cases/v1/application/cases.json").read_bytes())["cases"]
                         if item["eval_set_id"] == "agentops_agent_core" and item["eval_id"] == "inventory-status")
        self.builder.build(source_case=self.case)
        self.instance = self.builder.instance
        self.output = self.instance.parent / "SYNTHETIC-v3-evaluation"
        self.addCleanup(self.retain_artifacts)

    def tearDown(self):
        self.assertEqual((ROOT / "scripts/assess_upstream_agentops_case_v2.py").read_bytes(), self.before_v2)

    def retain_artifacts(self):
        target = os.environ.get("ASSESS_CLI_V3_ARTIFACTS")
        if target:
            destination = Path(target) / self._testMethodName
            if destination.resolve().is_relative_to(self.instance.parent.resolve()):
                raise ValueError("Constructed artifact copy would overlap its source")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(self.instance.parent, destination)

    def make_journal(self, partial=None):
        events = [
            {"id": "SYNTHETIC-call-event", "invocation_id": "SYNTHETIC-native-turn", "author": "agentops_agent", "node_info": {"path": ""},
             "content": {"role": "model", "parts": [{"function_call": {"id": "SYNTHETIC-tool", "name": "get_service_status", "args": {"name": "inventory"}}}]}},
            {"id": "SYNTHETIC-reply-event", "invocation_id": "SYNTHETIC-native-turn", "author": "agentops_agent", "node_info": {"path": ""},
             "content": {"role": "model", "parts": [{"function_response": {"id": "SYNTHETIC-tool", "name": "get_service_status",
                 "response": {"service": {"name": "inventory", "description": "SYNTHETIC service", "status": "down", "owner": "SYNTHETIC owner"}, "open_incidents": []}}}]}},
            {"id": "SYNTHETIC-answer-event", "invocation_id": "SYNTHETIC-native-turn", "author": "agentops_agent", "node_info": {"path": ""},
             "content": {"role": "model", "parts": [{"text": "SYNTHETIC observed answer; never native evidence."}]}},
        ]
        if partial is not None:
            events[partial]["partial"] = True
        journal = self.instance / "service/runtime-stream"
        async def producer(**kwargs):
            for event in events:
                yield event
        async def record():
            observer = RunAsyncJournal(producer, journal, event_serializer=encoded,
                                       content_serializer=encoded, config_serializer=encoded)
            async for _ in observer.run_async(user_id=USER, session_id=SESSION,
                                              new_message=deepcopy(self.case["conversation"][0]["user_content"])):
                pass
            return observer.finish()
        # This finite constructed producer performs no scheduling or I/O awaits.
        # Drive it once without creating Windows asyncio's socket self-pipe;
        # every socket operation remains denied by the capture audit hook.
        coroutine = record()
        try:
            try:
                coroutine.send(None)
            except StopIteration as completed:
                root_receipt = completed.value
            else:
                self.fail("Constructed journal producer unexpectedly suspended")
        finally:
            coroutine.close()
        validation = read_closed_journal(journal)
        stream = {"status": "recorded", "receipt": "runtime-stream/result.json",
                  "receipt_bytes": validation["receipt_identity"]["bytes"], "receipt_sha256": validation["receipt_identity"]["sha256"]}
        for flag in ("finish_called", "capture_complete", "eligible_for_ordered_evidence_checks", "lifecycle_succeeded",
                     "serve_tasks_settled", "original_serve_returned", "persisted_receipt_matches_returned"):
            stream[flag] = True
        keys = ("schema_version", "status", "calls_seen", "active_calls", "capture_disabled", "durable_receipt_written",
                "capture_complete", "eligible_for_ordered_evidence_checks")
        stream["returned"] = {key: root_receipt[key] for key in keys}
        self.mutate("service/bootstrap.exit.json", lambda value: value.update(runtime_stream=stream))
        self.mutate("result.json", lambda value: value.update(closed_runtime_stream={
            "schema_version": "upstream-agentops-closed-stream-binding/1", "status": "validated", "receipt_identity": validation["receipt_identity"],
            "files": validation["files"], "source_turns_bound": 1, "native_call_count": 1, "original_event_count": 3,
            "event_ids": [row["id"] for row in validation["ordered_events"]],
            "invocation_ids_in_event_order": [row["invocation_id"] for row in validation["ordered_events"]],
            "closed_owned_process_gate_checked_by_caller": True, "source_authentication_proven": False,
            "causal_tool_execution_order_proven": False, "benchmark_grade_proven": False}))

    def mutate(self, relative, change):
        path = self.instance / relative
        value = json.loads(path.read_bytes()); change(value); path.write_bytes(encoded(value))

    def argv(self, output=None):
        return ["--instance", str(self.instance), "--application", str(ROOT / "runs/upstream-agentops-cases/v1/application/cases.json"),
                "--expectations", str(ROOT / "runs/upstream-agentops-cases/v1/evaluator/expectations.json"),
                "--eval-set-id", self.case["eval_set_id"], "--eval-id", self.case["eval_id"],
                "--native-user-id", USER, "--native-session-id", SESSION, "--output", str(output or self.output)]

    def isolated_cli(self, *, script=SCRIPT, output=None, extra=()):
        result = subprocess.run([sys.executable, "-I", "-S", "-B", str(script), *self.argv(output), *extra],
                                capture_output=True, timeout=60, check=False)
        prefix = (output or self.output).name
        (self.instance.parent / (prefix + ".stdout.bin")).write_bytes(result.stdout)
        (self.instance.parent / (prefix + ".stderr.bin")).write_bytes(result.stderr)
        return result

    def in_process_cli(self, *, extra=()):
        stdout = io.StringIO()
        with patch.object(sys, "stdout", stdout):
            code = cli.main([*self.argv(), *extra])
        (self.instance.parent / "SYNTHETIC-in-process.stdout.bin").write_bytes(stdout.getvalue().encode())
        return code

    def receipt(self):
        return json.loads((self.output / "result.json").read_bytes())

    def assert_no_native_grade(self, receipt):
        for flag in ("aggregate_task_pass_assigned", "full_task_grade_assigned", "benchmark_grade_proven",
                     "native_qualification_established", "native_source_case_qualification", "source_authentication_proven"):
            self.assertIs(receipt[flag], False)

    def extraction(self):
        path = self.instance.parent / "SYNTHETIC-answer-extraction.json"
        path.write_bytes(encoded({"schema_version": "agentops-answer-extraction-bindings/1", "family": "core",
            "selection_profile": "complete_model_text_after_node_tools_v1", "source_bindings": deepcopy(SOURCE_BINDINGS),
            "turns": [{"turn_index": 1, "native_invocation_id": "SYNTHETIC-native-turn",
                       "source_invocation_label": self.case["conversation"][0]["invocation_id"],
                       "nodes": {"answer": {"author": "agentops_agent", "node_path": "", "branch": None}}}]}))
        return ("--answer-extraction-bindings", str(path))

    def test_complete_isolated_cli_keeps_metric_state_and_uses_pinned_corrected_helpers(self):
        self.make_journal()
        before = cli._inventory(self.instance)
        completed = self.isolated_cli()
        self.assertEqual(completed.returncode, 0, completed.stderr.decode())
        receipt = self.receipt(); assessment = receipt["assessment"]
        self.assertEqual(receipt["schema_version"], "upstream-agentops-case-evaluator/3")
        self.assertTrue(receipt["corrected_complete_observation_API_used"])
        self.assertEqual(assessment["schema_version"], "agentops-source-case-assessment/3")
        self.assertEqual(receipt["metric_status"], "passed")
        self.assertEqual(assessment["reply_dependencies"]["schema_version"], "agentops-reply-dependencies/2")
        self.assertEqual(assessment["separate_assessments"]["response"]["status"], "supported")
        self.assertEqual(assessment["sampled_effects"]["business"]["status"], "consistent")
        self.assertEqual(before, cli._inventory(self.instance))
        for source in ("src/interoperability/agentops_reply_dependencies_v2.py", "src/interoperability/agentops_source_case_assessment_v3.py"):
            self.assertEqual(receipt["evaluator_source_bindings"][source]["sha256"], cli.FROZEN_SOURCE_SHA256[source])
            self.assertEqual((self.output / "source" / source).read_bytes(), (ROOT / source).read_bytes())
        self.assert_no_native_grade(receipt)

    def test_partial_call_is_unknown_in_actual_cli_while_original_metric_passes(self):
        self.make_journal(partial=0)
        self.assertEqual(self.isolated_cli().returncode, 0)
        receipt = self.receipt()
        self.assertEqual(receipt["metric_status"], "passed")
        self.assertEqual(receipt["assessment"]["separate_assessments"]["response"]["status"], "unknown")
        self.assertEqual(receipt["assessment"]["partial_tool_observation_refs"][0]["kind"], "call")
        self.assert_no_native_grade(receipt)

    def test_partial_reply_is_unknown_in_actual_cli_while_original_metric_passes(self):
        self.make_journal(partial=1)
        self.assertEqual(self.isolated_cli().returncode, 0)
        receipt = self.receipt()
        self.assertEqual(receipt["metric_status"], "passed")
        self.assertEqual(receipt["assessment"]["separate_assessments"]["response"]["status"], "unknown")
        self.assertEqual(receipt["assessment"]["partial_tool_observation_refs"][0]["kind"], "reply")
        self.assert_no_native_grade(receipt)

    def test_optional_answer_extraction_is_withheld_for_retained_partial_reply(self):
        self.make_journal(partial=1)
        self.assertEqual(self.isolated_cli(extra=self.extraction()).returncode, 0)
        assessment = self.receipt()["assessment"]
        self.assertTrue(assessment["supplied_bindings_withheld_due_to_partial"])
        self.assertEqual(assessment["separate_assessments"]["answer"]["status"], "pending")
        self.assertEqual(assessment["separate_assessments"]["schema"]["status"], "pending")
        self.assertIsNone(assessment["answer_schema"])
        self.assertIn("answer_extraction_bindings", self.receipt()["input_bindings"])

    def test_optional_answer_extraction_stays_observed_on_complete_retained_reply(self):
        self.make_journal()
        self.assertEqual(self.isolated_cli(extra=self.extraction()).returncode, 0)
        assessment = self.receipt()["assessment"]
        self.assertFalse(assessment["supplied_bindings_withheld_due_to_partial"])
        self.assertEqual(assessment["answer_schema"]["turns"][0]["answer_extraction"]["answer"]["status"], "observed")
        self.assertEqual(assessment["answer_schema"]["turns"][0]["semantic_manual_assessment"]["status"], "pending")

    def test_changed_corrected_helper_is_refused_before_helper_execution(self):
        self.make_journal()
        clone = self.instance.parent / "SYNTHETIC-tampered-checkout"
        design = json.loads((ROOT / "docs/research/agentops-answer-schema-assessment-design-v1.json").read_bytes())
        paths = set(cli.SOURCES) | {row["path"] for row in design["source_artifacts"]} | {
            "docs/research/agentops-answer-schema-assessment-design-v1.json", "docs/research/upstream-agentops-grading-obligations-v1.json"}
        for relative in paths:
            destination = clone / relative; destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as out: out.write((ROOT / relative).read_bytes())
        helper = clone / "src/interoperability/agentops_reply_dependencies_v2.py"
        helper.write_bytes(helper.read_bytes() + b"\n# SYNTHETIC tampered helper\n")
        completed = self.isolated_cli(script=clone / "scripts/assess_upstream_agentops_case_v3.py")
        self.assertEqual(completed.returncode, 1)
        receipt = self.receipt()
        self.assertEqual(receipt["failure_phase"], "capture_read_only_input_bindings")
        self.assertFalse(receipt["assessment_eligible"])
        self.assertFalse(receipt["corrected_complete_observation_API_used"])

    def test_bootstrap_type_mismatch_is_still_rejected_before_grading(self):
        self.make_journal()
        self.mutate("result.json", lambda value: value["closed_runtime_stream"].update(native_call_count=True))
        self.assertEqual(self.isolated_cli().returncode, 1)
        receipt = self.receipt()
        self.assertEqual(receipt["failure_phase"], "bind_instance_bootstrap_and_closed_journal")
        self.assertFalse(receipt["assessment_eligible"])

    def test_postassessment_instance_mutation_still_invalidates_eligibility(self):
        self.make_journal()
        original = cli._evaluators
        def evaluators(source_bytes):
            reader, collector, assessor = original(source_bytes)
            def mutate_after(*args, **kwargs):
                result = assessor(*args, **kwargs)
                (self.instance / "SYNTHETIC-unexpected.bin").write_bytes(b"SYNTHETIC mutation")
                return result
            return reader, collector, mutate_after
        with patch.object(cli, "_evaluators", new=evaluators):
            self.assertEqual(self.in_process_cli(), 1)
        receipt = self.receipt()
        self.assertEqual(receipt["failure_phase"], "postassessment_identity_check")
        self.assertFalse(receipt["assessment_eligible"])
        self.assertFalse(receipt["instance_membership_hashes_unchanged_at_boundary_checks"])

    def test_pending_close_failure_keeps_final_receipt_noneligible(self):
        self.make_journal()
        original_open = Path.open; pending = self.output / "result.json.pending"
        class FailAfterClose:
            def __init__(self, stream): self.stream = stream
            def __enter__(self): return self.stream
            def __exit__(self, *args): self.stream.close(); raise OSError("SYNTHETIC close failure")
        def failing_open(path, mode="r", *args, **kwargs):
            stream = original_open(path, mode, *args, **kwargs)
            return FailAfterClose(stream) if path == pending and mode == "xb" else stream
        with patch.object(Path, "open", new=failing_open):
            self.assertEqual(self.in_process_cli(), 1)
        self.assertEqual((self.output / "result.json").read_bytes(), b"")
        self.assertTrue(json.loads(pending.read_bytes())["assessment_eligible"])
        failure = json.loads((self.output / "publication.failure.json").read_bytes())
        self.assertFalse(failure["assessment_eligible"])

    def test_explicit_parent_creation_is_restricted_to_one_named_checkout_directory(self):
        clone = self.instance.parent / "SYNTHETIC-parent-checkout"
        (clone / "runs").mkdir(parents=True)
        permitted = clone / "runs/upstream-agentops-grades"
        with patch.object(cli, "ROOT", clone):
            with self.assertRaises(ValueError):
                cli._prepare_output_parent(clone / "runs/other-grade-parent/result", True)
            self.assertFalse(permitted.exists())
            self.assertTrue(cli._prepare_output_parent(permitted / "SYNTHETIC-grade", True))
            marker = permitted / "SYNTHETIC-preserve.bin"; marker.write_bytes(b"SYNTHETIC preserve")
            self.assertFalse(cli._prepare_output_parent(permitted / "SYNTHETIC-other", True))
            self.assertEqual(marker.read_bytes(), b"SYNTHETIC preserve")
            self.assertFalse((clone / "runs/other-grade-parent").exists())


if __name__ == "__main__":
    unittest.main()
