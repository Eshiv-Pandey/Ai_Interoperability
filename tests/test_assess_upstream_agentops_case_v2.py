"""Complete SYNTHETIC retained-instance/journal/evaluator CLI integration."""
import asyncio
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
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

SCRIPT = ROOT / "scripts/assess_upstream_agentops_case_v2.py"
spec = importlib.util.spec_from_file_location("synthetic_v2_cli_under_test", SCRIPT)
cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
SESSION = "00000000-0000-4000-8000-000000000001"
USER = "A2A_USER_" + SESSION
encoded = boundary_fixture.encoded


class IntegratedCliTests(unittest.TestCase):
    def setUp(self):
        self.builder = boundary_fixture.BoundaryTests(); self.builder.setUp(); self.addCleanup(self.builder.doCleanups)
        self.case = json.loads((ROOT / "runs/upstream-agentops-cases/v1/application/cases.json").read_bytes())["cases"][0]
        self.builder.build(source_case=self.case)
        self.instance = self.builder.instance
        self.output = self.instance.parent / "SYNTHETIC-v2-evaluation"
        self.journal = self.instance / "service/runtime-stream"
        async def producer(**kwargs):
            yield {"id": "SYNTHETIC-call-event", "invocation_id": "SYNTHETIC-native-turn", "author": "SYNTHETIC_AGENT",
                   "content": {"role": "model", "parts": [{"function_call": {"id": "SYNTHETIC-tool",
                       "name": "get_service_status", "args": {"name": "inventory"}}}]}}
            yield {"id": "SYNTHETIC-reply-event", "invocation_id": "SYNTHETIC-native-turn", "author": "SYNTHETIC_AGENT",
                   "content": {"role": "model", "parts": [{"function_response": {"id": "SYNTHETIC-tool", "name": "get_service_status",
                       "response": {"service": {"name": "inventory", "description": "SYNTHETIC service", "status": "down", "owner": "SYNTHETIC owner"}, "open_incidents": []}}}]}}
            yield {"id": "SYNTHETIC-answer-event", "invocation_id": "SYNTHETIC-native-turn", "author": "SYNTHETIC_AGENT",
                   "content": {"role": "model", "parts": [{"text": "SYNTHETIC observed answer; never native evidence."}]}}
        async def record():
            observer = RunAsyncJournal(producer, self.journal, event_serializer=encoded, content_serializer=encoded, config_serializer=encoded)
            async for _ in observer.run_async(user_id=USER, session_id=SESSION, new_message=deepcopy(self.case["conversation"][0]["user_content"])): pass
            return observer.finish()
        root_receipt = asyncio.run(record())
        validation = read_closed_journal(self.journal)
        stream = {"status": "recorded", "receipt": "runtime-stream/result.json", "receipt_bytes": validation["receipt_identity"]["bytes"],
                  "receipt_sha256": validation["receipt_identity"]["sha256"]}
        for flag in ("finish_called", "capture_complete", "eligible_for_ordered_evidence_checks", "lifecycle_succeeded",
                     "serve_tasks_settled", "original_serve_returned", "persisted_receipt_matches_returned"): stream[flag] = True
        keys = ("schema_version", "status", "calls_seen", "active_calls", "capture_disabled", "durable_receipt_written", "capture_complete", "eligible_for_ordered_evidence_checks")
        stream["returned"] = {key: root_receipt[key] for key in keys}
        self.mutate("service/bootstrap.exit.json", lambda value: value.update(runtime_stream=stream))
        self.mutate("result.json", lambda value: value.update(closed_runtime_stream={
            "schema_version": "upstream-agentops-closed-stream-binding/1", "status": "validated",
            "receipt_identity": validation["receipt_identity"], "files": validation["files"], "source_turns_bound": 1,
            "native_call_count": 1, "original_event_count": 3,
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
                "--eval-set-id", self.case["eval_set_id"], "--eval-id", self.case["eval_id"], "--native-user-id", USER,
                "--native-session-id", SESSION, "--output", str(self.output if output is None else output)]

    def run_cli(self, output=None, extra=()):
        stdout = io.StringIO()
        with patch.object(sys, "stdout", stdout): code = cli.main([*self.argv(output), *extra])
        return code, json.loads(stdout.getvalue())

    def retained(self, output=None):
        return json.loads(((self.output if output is None else output) / "result.json").read_bytes())

    def test_isolated_complete_retained_instance_cli_keeps_separate_lanes_and_bindings(self):
        before = cli._inventory(self.instance)
        result = subprocess.run([sys.executable, "-I", "-S", "-B", str(SCRIPT), *self.argv()], capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        receipt = self.retained()
        self.assertTrue(receipt["assessment_eligible"])
        self.assertEqual(receipt["metric_status"], "passed")
        self.assertEqual(receipt["assessment"]["separate_assessments"]["response"]["status"], "supported")
        self.assertEqual(receipt["assessment"]["sampled_effects"]["business"]["status"], "consistent")
        self.assertEqual(receipt["assessment"]["separate_assessments"]["schema"]["status"], "pending")
        self.assertTrue(receipt["closed_stream_binding"]["instance_bootstrap_and_validated_journal_agree"])
        self.assertEqual(before, cli._inventory(self.instance))
        self.assertGreaterEqual(len(receipt["evaluator_source_bindings"]), len(cli.SOURCES))
        for relative in receipt["evaluator_source_bindings"]:
            self.assertEqual((self.output / "source" / relative).read_bytes(), (ROOT / relative).read_bytes())
        for flag in ("aggregate_task_pass_assigned", "full_task_grade_assigned", "benchmark_grade_proven", "native_qualification_established"):
            self.assertIs(receipt[flag], False)

    def test_declared_closed_receipt_event_manifest_and_bootstrap_flags_must_agree(self):
        original_result = (self.instance / "result.json").read_bytes()
        original_exit = (self.instance / "service/bootstrap.exit.json").read_bytes()
        changes = [("result.json", lambda value: value["closed_runtime_stream"]["receipt_identity"].update(sha256="0" * 64)),
                   ("result.json", lambda value: value["closed_runtime_stream"]["files"].pop("plan.json")),
                   ("result.json", lambda value: value["closed_runtime_stream"]["event_ids"].reverse()),
                   ("result.json", lambda value: value["closed_runtime_stream"].update(native_call_count=True)),
                   ("service/bootstrap.exit.json", lambda value: value["runtime_stream"].update(finish_called=False)),
                   ("service/bootstrap.exit.json", lambda value: value["runtime_stream"]["returned"].update(active_calls=True))]
        for index, (path, change) in enumerate(changes):
            with self.subTest(change=index):
                (self.instance / "result.json").write_bytes(original_result)
                (self.instance / "service/bootstrap.exit.json").write_bytes(original_exit)
                self.mutate(path, change)
                output = self.instance.parent / ("SYNTHETIC-declaration-" + str(index))
                code, _ = self.run_cli(output)
                receipt = self.retained(output)
                self.assertEqual(code, 1)
                self.assertEqual(receipt["failure_phase"], "bind_instance_bootstrap_and_closed_journal")
                self.assertFalse(receipt["assessment_eligible"])

    def test_existing_output_rejected_without_input_reads_or_mutation(self):
        self.output.mkdir(); (self.output / "retained.bin").write_bytes(b"SYNTHETIC preserve")
        with patch.object(cli, "_read", side_effect=AssertionError("unexpected input read")):
            code, summary = self.run_cli()
        self.assertEqual(code, 1); self.assertEqual(summary["failure_phase"], "exclusive_output_allocation")
        self.assertEqual([path.name for path in self.output.iterdir()], ["retained.bin"])

    def test_changed_pinned_obligation_is_rejected_before_source_evaluation(self):
        changed = self.instance.parent / "SYNTHETIC-obligation.json"
        changed.write_bytes((ROOT / "docs/research/upstream-agentops-grading-obligations-v1.json").read_bytes() + b" ")
        code, summary = self.run_cli(extra=("--obligations", str(changed)))
        self.assertEqual(code, 1); self.assertEqual(summary["failure_phase"], "capture_read_only_input_bindings")
        self.assertFalse(self.retained()["assessment_eligible"])

    def test_postassessment_instance_change_invalidates_eligibility(self):
        original = cli._evaluators
        def evaluators(source_bytes):
            reader, collector, assessor = original(source_bytes)
            def mutate_after(*args, **kwargs):
                result = assessor(*args, **kwargs)
                (self.instance / "SYNTHETIC-unexpected.bin").write_bytes(b"SYNTHETIC mutation")
                return result
            return reader, collector, mutate_after
        with patch.object(cli, "_evaluators", new=evaluators): code, _ = self.run_cli()
        receipt = self.retained()
        self.assertEqual(code, 1); self.assertEqual(receipt["failure_phase"], "postassessment_identity_check")
        self.assertFalse(receipt["instance_membership_hashes_unchanged_at_boundary_checks"])
        self.assertFalse(receipt["assessment_eligible"])

    def test_executed_business_reader_identity_must_match_captured_source(self):
        original = cli._evaluators
        def evaluators(source_bytes):
            reader, collector, assessor = original(source_bytes)
            def wrong_reader(*args):
                result = collector(*args)
                result["business_reader_identity"] = {"bytes": 1, "sha256": "0" * 64}
                return result
            return reader, wrong_reader, assessor
        with patch.object(cli, "_evaluators", new=evaluators): code, _ = self.run_cli()
        receipt = self.retained()
        self.assertEqual(code, 1); self.assertEqual(receipt["failure_phase"], "collect_instance_source_boundaries")
        self.assertFalse(receipt["assessment_eligible"])

    def test_pending_close_failure_never_publishes_eligible_final_receipt(self):
        original_open = Path.open; pending = self.output / "result.json.pending"
        class FailAfterClose:
            def __init__(self, stream): self.stream = stream
            def __enter__(self): return self.stream
            def __exit__(self, *args): self.stream.close(); raise OSError("SYNTHETIC private failure")
        def failing_open(path, mode="r", *args, **kwargs):
            stream = original_open(path, mode, *args, **kwargs)
            return FailAfterClose(stream) if path == pending and mode == "xb" else stream
        with patch.object(Path, "open", new=failing_open): code, _ = self.run_cli()
        self.assertEqual(code, 1); self.assertEqual((self.output / "result.json").read_bytes(), b"")
        self.assertTrue(json.loads(pending.read_bytes())["assessment_eligible"])
        failure = json.loads((self.output / "publication.failure.json").read_bytes())
        self.assertFalse(failure["assessment_eligible"]); self.assertNotIn("SYNTHETIC private failure", json.dumps(failure))


if __name__ == "__main__": unittest.main()
