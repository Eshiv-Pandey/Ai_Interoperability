"""Runnable CLI over synthetic stdlib journal observations; no original runtime."""
import asyncio
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/assess_upstream_agentops_case_v1.py"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from agentops_runtime_stream_v1 import RunAsyncJournal

SPEC = importlib.util.spec_from_file_location("synthetic_evaluator_cli_under_test", SCRIPT)
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)

USER = "SYNTHETIC_CLI_USER"
SESSION = "SYNTHETIC_CLI_SESSION"


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


class EvaluatorCliTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="SYNTHETIC-evaluator-cli-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.journal = self.root / "SYNTHETIC-journal"
        self.application = self.root / "SYNTHETIC-application.json"
        self.expectations = self.root / "SYNTHETIC-expectations.json"
        self.output = self.root / "SYNTHETIC-evaluation"
        identity = {"eval_set_id": "agentops_agent_core", "eval_id": "SYNTHETIC_CLI_CASE", "creation_timestamp": 0.0}
        self.prompt = {"role": "user", "parts": [{"text": "SYNTHETIC: inspect the isolated fixture only."}]}
        self.case = {**identity, "session_input": {"app_name": "agentops_agent", "user_id": "eval", "state": {}},
                     "conversation": [{"invocation_id": "SYNTHETIC_SOURCE_LABEL", "creation_timestamp": 0.0, "user_content": self.prompt}]}
        self.expected = {**identity, "conversation": [{"invocation_id": "SYNTHETIC_SOURCE_LABEL", "creation_timestamp": 0.0,
                         "final_response": {"role": "model", "parts": [{"text": "SYNTHETIC reference; never a passing oracle."}]},
                         "intermediate_data": {"tool_uses": [{"name": "SYNTHETIC_fixture_status", "args": {"fixture": "isolated"}}],
                                               "intermediate_responses": []}}]}
        self.app_doc = {"schema_version": "upstream-agentops-application-cases/1", "provenance": {"SYNTHETIC_ONLY": True}, "cases": [self.case]}
        self.expected_doc = {"schema_version": "upstream-agentops-evaluator-expectations/1", "provenance": {"SYNTHETIC_ONLY": True}, "cases": [self.expected]}
        self.application.write_bytes(encoded(self.app_doc))
        self.expectations.write_bytes(encoded(self.expected_doc))

        async def synthetic_producer(**kwargs):
            yield {"id": "SYNTHETIC_EVENT_1", "invocation_id": "SYNTHETIC_NATIVE_GENERATED_ID", "author": "SYNTHETIC_AGENT",
                   "content": {"role": "model", "parts": [{"function_call": {"name": "SYNTHETIC_fixture_status", "args": {"fixture": "isolated"}}}]}}
            yield {"id": "SYNTHETIC_EVENT_2", "invocation_id": "SYNTHETIC_NATIVE_GENERATED_ID", "author": "SYNTHETIC_AGENT",
                   "content": {"role": "model", "parts": [{"text": "SYNTHETIC non-reference response."}]}}
        async def capture():
            observer = RunAsyncJournal(synthetic_producer, self.journal, event_serializer=encoded, content_serializer=encoded, config_serializer=encoded)
            async for _ in observer.run_async(user_id=USER, session_id=SESSION, new_message=deepcopy(self.prompt)):
                pass
            observer.finish()
        asyncio.run(capture())

    def argv(self, user=USER, session=SESSION, output=None):
        return ["--journal", str(self.journal), "--application", str(self.application), "--expectations", str(self.expectations),
                "--eval-set-id", "agentops_agent_core", "--eval-id", "SYNTHETIC_CLI_CASE", "--native-user-id", user,
                "--native-session-id", session, "--output", str(self.output if output is None else output)]

    def run_cli(self, **kwargs):
        stdout = io.StringIO()
        with patch.object(sys, "stdout", stdout):
            code = cli.main(self.argv(**kwargs))
        return code, json.loads(stdout.getvalue())

    def retained(self):
        return json.loads((self.output / "result.json").read_bytes())

    def input_inventory(self):
        return {str(path): path.read_bytes() for path in (self.application, self.expectations, *self.journal.rglob("*")) if path.is_file()}

    def test_isolated_runnable_recorder_reader_assessor_cli_success_retains_bindings(self):
        before = self.input_inventory()
        outcome = subprocess.run([sys.executable, "-I", "-S", "-B", str(SCRIPT), *self.argv()], capture_output=True, check=False)
        self.assertEqual(outcome.returncode, 0, outcome.stderr.decode("utf-8"))
        summary = json.loads(outcome.stdout)
        result = self.retained()
        self.assertEqual(summary["status"], "assessed_configured_metric_only")
        self.assertEqual(result["metric_status"], "passed")
        self.assertEqual(result["assessment"]["configured_metric"]["overall_score"], 1.0)
        self.assertTrue(result["assessment_eligible"])
        self.assertEqual(result["input_bindings"]["application"], {"path": str(self.application), **cli._digest(self.application.read_bytes())})
        self.assertEqual(result["validated_journal_receipt_identity"], cli._digest((self.journal / "result.json").read_bytes()))
        self.assertTrue(result["input_bytes_unchanged_at_boundary_checks"])
        self.assertTrue(result["evaluator_source_bytes_unchanged_at_boundary_checks"])
        self.assertTrue(result["journal_membership_hashes_unchanged_at_boundary_checks"])
        self.assertEqual(before, self.input_inventory())
        for relative in cli.SOURCES:
            self.assertEqual((self.output / "source" / relative).read_bytes(), (ROOT / relative).read_bytes())
        self.assertTrue((self.output / "plan.json").exists())
        self.assertTrue((self.output / "bindings.before.json").exists())
        self.assertEqual(result["assessment"]["separate_assessments"]["state"]["status"], "unavailable")
        for key in ("source_authentication_proven", "native_authentication_proven", "native_qualification_established",
                    "native_source_case_qualification", "process_exit_proven", "public_raw_binding_checked", "state_effects_proven",
                    "benchmark_grade_proven", "full_task_grade_assigned", "caller_native_ids_are_authenticated", "continuous_input_immutability_proven"):
            self.assertIs(result[key], False)

    def test_wrong_native_context_retains_failure_and_leaves_inputs_unchanged(self):
        before = self.input_inventory()
        code, summary = self.run_cli(user="SYNTHETIC_WRONG_USER")
        result = self.retained()
        self.assertEqual(code, 1)
        self.assertEqual(summary["status"], "failed")
        self.assertEqual(result["failure_phase"], "assess_configured_source_metric")
        self.assertIsNone(result["assessment"])
        self.assertFalse(result["assessment_eligible"])
        self.assertEqual(before, self.input_inventory())
        self.assertTrue(result["journal_membership_hashes_unchanged_at_boundary_checks"])

    def test_incomplete_journal_retains_failed_validation_without_repair(self):
        path = self.journal / "result.json"
        value = json.loads(path.read_bytes()); value["capture_complete"] = False
        path.write_bytes(encoded(value))
        before = self.input_inventory()
        code, summary = self.run_cli()
        result = self.retained()
        self.assertEqual(code, 1)
        self.assertEqual(result["failure_phase"], "validate_closed_journal")
        self.assertIsNone(result["metric_status"])
        self.assertEqual(before, self.input_inventory())

    def test_existing_output_is_preserved_byte_for_byte_without_input_reads(self):
        self.output.mkdir()
        retained = self.output / "retained.bin"
        retained.write_bytes(b"SYNTHETIC existing allocation must remain untouched")
        with patch.object(cli, "_read", side_effect=AssertionError("input read before rejecting allocation")):
            code, summary = self.run_cli()
        self.assertEqual(code, 1)
        self.assertEqual(summary["failure_phase"], "exclusive_output_allocation")
        self.assertEqual(retained.read_bytes(), b"SYNTHETIC existing allocation must remain untouched")
        self.assertEqual([path.name for path in self.output.iterdir()], ["retained.bin"])

    def test_duplicate_or_missing_exact_projection_case_is_rejected(self):
        for condition in ("duplicate", "missing"):
            with self.subTest(condition=condition):
                document = deepcopy(self.expected_doc)
                document["cases"] = [self.expected, deepcopy(self.expected)] if condition == "duplicate" else []
                self.expectations.write_bytes(encoded(document))
                output = self.root / ("SYNTHETIC-" + condition)
                code, summary = self.run_cli(output=output)
                self.assertEqual(code, 1)
                result = json.loads((output / "result.json").read_bytes())
                self.assertEqual(result["failure_phase"], "select_source_case")
                self.assertIsNone(result["assessment"])

    def test_postscore_input_change_invalidates_metric_eligibility(self):
        reader, assessor = cli._evaluators()
        def mutate_after_scoring(*args, **kwargs):
            result = assessor(*args, **kwargs)
            self.application.write_bytes(self.application.read_bytes() + b" ")
            return result
        with patch.object(cli, "_evaluators", return_value=(reader, mutate_after_scoring)):
            code, summary = self.run_cli()
        result = self.retained()
        self.assertEqual(code, 1)
        self.assertEqual(result["failure_phase"], "postassessment_identity_check")
        self.assertFalse(result["input_bytes_unchanged_at_boundary_checks"])
        self.assertFalse(result["assessment_eligible"])
        self.assertIsNone(result["metric_status"])

    def test_postscore_journal_change_retains_failure_without_silent_repair(self):
        reader, assessor = cli._evaluators()
        def mutate_after_scoring(*args, **kwargs):
            result = assessor(*args, **kwargs)
            (self.journal / "SYNTHETIC_UNEXPECTED_MEMBER.bin").write_bytes(b"SYNTHETIC changed journal")
            return result
        with patch.object(cli, "_evaluators", return_value=(reader, mutate_after_scoring)):
            code, summary = self.run_cli()
        result = self.retained()
        self.assertEqual(code, 1)
        self.assertFalse(result["journal_membership_hashes_unchanged_at_boundary_checks"])
        self.assertFalse(result["assessment_eligible"])
        self.assertTrue((self.journal / "SYNTHETIC_UNEXPECTED_MEMBER.bin").exists())

    def test_complete_pending_close_failure_never_exposes_eligible_final_receipt(self):
        original_open = Path.open
        pending = self.output / "result.json.pending"
        class FailAfterClose:
            def __init__(self, stream):
                self.stream = stream
            def __enter__(self):
                return self.stream
            def __exit__(self, *args):
                self.stream.close()
                raise OSError("SYNTHETIC private close failure detail")
        def failing_open(path, mode="r", *args, **kwargs):
            stream = original_open(path, mode, *args, **kwargs)
            return FailAfterClose(stream) if path == pending and mode == "xb" else stream
        with patch.object(Path, "open", new=failing_open):
            code, summary = self.run_cli()
        self.assertEqual(code, 1)
        self.assertEqual(summary["status"], "failed")
        self.assertEqual((self.output / "result.json").read_bytes(), b"")
        self.assertTrue(json.loads(pending.read_bytes())["assessment_eligible"])  # pending is deliberately unusable
        failure = json.loads((self.output / "publication.failure.json").read_bytes())
        self.assertEqual(failure["status"], "failed")
        self.assertFalse(failure["assessment_eligible"])
        self.assertNotIn("SYNTHETIC private close failure detail", json.dumps(failure) + json.dumps(summary))


if __name__ == "__main__":
    unittest.main()
