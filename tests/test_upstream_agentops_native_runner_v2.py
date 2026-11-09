"""Meaningful scheduler/resource/ownership failure checks with no native launch."""
from datetime import datetime, timedelta, timezone
import asyncio
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import socket
import struct
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from interoperability import upstream_agentops_native_runner_v2 as runner
from interoperability import windows_tcp_ownership_v1 as tcp


APPLICATION = ROOT / "runs/upstream-agentops-cases/v1/application/cases.json"
spec = importlib.util.spec_from_file_location("test_runner_runtime_stream", ROOT / "scripts/agentops_runtime_stream_v1.py")
stream_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stream_module)


def mock_closed_stream(service, item):
    async def original(**kwargs):
        yield {"id": "event-" + kwargs["session_id"], "invocation_id": "native-invocation-1",
               "content": {"role": "model", "parts": [{"text": "mock original output"}]}}
    serialize = lambda value: runner.client._encoded(value)
    recorder = stream_module.RunAsyncJournal(original, service / "runtime-stream", event_serializer=serialize,
                                             content_serializer=serialize, config_serializer=serialize)
    policy = runner.session_policy(item)
    async def consume():
        for turn in item["case"]["conversation"]:
            async for _ in recorder.run_async(user_id=policy["native_user_id_expected_from_source"], session_id=item["context_id"],
                                              new_message=turn["user_content"]):
                pass
    asyncio.run(consume())
    returned = recorder.finish()
    keys = ("schema_version", "status", "calls_seen", "active_calls", "capture_disabled", "durable_receipt_written",
            "capture_complete", "eligible_for_ordered_evidence_checks")
    return {"status": "recorded", "finish_called": True, "capture_complete": True, "eligible_for_ordered_evidence_checks": True,
            "lifecycle_succeeded": True, "serve_tasks_settled": True, "original_serve_returned": True,
            "persisted_receipt_matches_returned": True, "returned": {key: returned[key] for key in keys},
            "receipt": "runtime-stream/result.json", "receipt_bytes": runner.digest(service / "runtime-stream/result.json")["bytes"],
            "receipt_sha256": runner.digest(service / "runtime-stream/result.json")["sha256"]}


class Job:
    def __init__(self, owner):
        self.owner = owner
        self.pid = 17

    def launch(self, argv, cwd, stdout, stderr):
        self.owner.launched += 1
        if self.owner.launch_failure:
            raise OSError("mock launch failure")
        return self.pid

    def poll(self):
        return None

    def finish(self, **kwargs):
        self.owner.finished += 1
        self.owner.write_exit()
        return {"schema_version": "windows-owned-job-cleanup/1", "pid": self.pid, "forced": self.owner.forced,
                "returncode": 0, "members": [], "active_processes": 0,
                "job_empty_observed": True, "main_handle_signaled": True, "handles_closed": True,
                "authority_retained": False, "errors": []}


class MockRuntime(runner.Runtime):
    def __init__(self, eligible=True):
        self.eligible = eligible
        self.launched = self.finished = self.retained = self.clients = self.exports = 0
        self.tick = 0
        self.sleep_calls = []
        self.forced = self.launch_failure = self.readiness_failure = self.client_failure = False
        self.bad_binding = False
        self.service = None
        self.stream_summary = None

    def memory_sample(self):
        # Two synthetic observations finish at current wall-clock time. No wait,
        # real GlobalMemoryStatusEx or SDK/model/native process is invoked.
        end = datetime.now(timezone.utc)
        first = self.tick % 2 == 0
        self.tick += 1
        return {"observed_at_utc": (end - timedelta(seconds=10.1 if first else 0)).isoformat(),
                "monotonic_ns": self.tick // 2 * 30_000_000_000 + (0 if first else 10_100_000_000) if not first else (self.tick // 2 + 1) * 30_000_000_000,
                "physical_available_bytes": 2 * 1024**3 if self.eligible else 100,
                "commit_available_bytes": 3 * 1024**3}

    def sleep(self, seconds):
        self.sleep_calls.append(seconds)

    def dependencies(self, config):
        return {"locked_version_differences": {}, "files": {}}

    def job(self):
        return Job(self)

    def free_port(self):
        return 19101

    def launch_argv(self, config, project, args, destination):
        self.service = destination.parent / "service"
        runner.write_json(destination, {"mocked_nonexecuted_arguments": args})
        return [str(config.interpreter)]

    def ready(self, service, endpoint, job):
        if self.readiness_failure:
            raise ValueError("mock readiness failure")
        binding = runner.read_json(service.parent / "plan.json")["binding"]
        runner.write_json(service / "bootstrap.created.json", {"schema_version": "upstream-agentops-bootstrap/2",
                          "status": "constructed_not_ready", "binding": {} if self.bad_binding else binding})

    def write_exit(self):
        if self.service is None or (self.service / "bootstrap.exit.json").exists():
            return
        binding = runner.read_json(self.service.parent / "plan.json")["binding"]
        runner.write_json(self.service / "bootstrap.exit.json", {"schema_version": "upstream-agentops-bootstrap/2",
                          "status": "stopped", "owned_stop_accepted": True, "original_serve_returned": True,
                          "binding": binding, "runtime_stream": self.stream_summary,
                          "memory_observation": {"capture_installed": True, "memory_errors": [], "memory_error_count": 0,
                                                 "snapshot_path": "state/memory.db"}})

    def client(self, item, endpoint, output, application, *, job):
        self.clients += 1
        self.item = item
        self.stream_summary = mock_closed_stream(self.service, item)
        return {"status": "partial" if self.client_failure else "recorded", "turns": [{"task_id": "task-1"}],
                "turns_attempted": len(item["case"]["conversation"])}

    def retain(self, service, destination):
        self.retained += 1
        destination.mkdir(exist_ok=False)
        runner.write_json(destination / "mock-closed-state.json", {"scope": "mock only"})
        return {"stores": {"incidents.db": True, "runtime.db": True, "memory.db": False}}

    def export(self, service, retained, output):
        self.exports += 1
        policy = runner.session_policy(self.item)
        context = self.item["context_id"]
        row = {"app_name": policy["native_app_name_expected"], "user_id": policy["native_user_id_expected_from_source"], "id": context}
        runner.write_json(output / "raw/decoded-tables.json", {"sessions": [row], "tasks": [{"id": "task-1", "context_id": context}],
                          "events": [{**row, "id": "event-1", "session_id": context, "invocation_id": "native-invocation-1"}]})
        return {"all_pipeline_steps_passed": True, "benchmark_grade_proven": False}


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.source = self.root / "external/source"
        self.source.mkdir(parents=True)
        self.application = self.root / "application/cases.json"
        self.application.parent.mkdir()
        self.application.write_bytes(APPLICATION.read_bytes())
        self.cases = runner.read_json(self.application)["cases"]
        self.receipt = self.root / "application/result.json"
        runner.write_json(self.receipt, {"schema_version": "upstream-agentops-export/1", "status": "passed", "case_count": 21,
                          "application_inputs": "cases.json", "files": [{"path": "cases.json", **runner.digest(self.application)}]})
        self.ingestion = self.root / "ingestion.json"
        runner.write_json(self.ingestion, {})
        self.interpreter = self.root / "runtime/Scripts/python.exe"
        self.interpreter.parent.mkdir(parents=True)
        self.interpreter.write_bytes(b"mock inert interpreter identity")
        self.config = runner.Config(self.root, self.root / "runs/upstream-agentops-native/test-1", self.source,
                                    self.ingestion, self.application, self.receipt, self.interpreter, "gemini-3.1-flash-lite-preview")

    def one(self, runtime, label=""):
        project, staged = self.root / ("project" + label), self.root / ("staged" + label)
        staged.mkdir()
        path = "scripts/serve_upstream_agentops_cases_v2.py"
        runner.copy_checked(ROOT / path, project / path, runner.digest(ROOT / path))
        path = "scripts/agentops_runtime_stream_v1.py"
        runner.copy_checked(ROOT / path, project / path, runner.digest(ROOT / path))
        item = runner.schedule(self.cases, {"core": 1, "report": 3, "workflow": 3},
                               ("agentops_agent_core/inventory-status",), 1)[0]
        return runner.run_one(self.config, runtime, item, project, staged, self.root / ("one" + label))

    def wire(self, label=""):
        from interoperability.agentops_memory_evidence_v1 import snapshot_memory
        source = self.root / ("wire" + label)
        exchange = source / "000001"
        exchange.mkdir(parents=True)
        for name in runner.PUBLIC_V1_FILES:
            (exchange / name).write_bytes(runner.client._encoded({"original_file": name}))
        value = snapshot_memory(self.root / "absent-memory.db", observation_mode="live")
        for name in runner.MEMORY_BOUNDARY_FILES:
            runner.write_json(exchange / name, value)
        return source

    def mutate_exit(self, runtime, change):
        original = runtime.write_exit
        def modified():
            original()
            path = runtime.service / "bootstrap.exit.json"
            value = runner.read_json(path)
            change(value)
            path.write_bytes(runner.client._encoded(value))
        runtime.write_exit = modified

    def test_all_21_original_cases_schedule_33_instances_and_34_turns(self):
        planned = runner.schedule(self.cases, {"core": 1, "report": 3, "workflow": 3})
        self.assertEqual(len(planned), 33)
        self.assertEqual(len({item["key"] for item in planned}), 21)
        self.assertEqual(sum(len(item["case"]["conversation"]) for item in planned), 34)
        self.assertEqual(len({item["context_id"] for item in planned}), 33)
        self.assertEqual([item["family"] for item in planned].count("core"), 15)

    def test_selected_diagnostic_keeps_exact_original_text(self):
        item = runner.schedule(self.cases, {"core": 1, "report": 3, "workflow": 3}, ("agentops_agent_core/inventory-status",), 1)[0]
        self.assertEqual(item["case"]["conversation"][0]["user_content"]["parts"], [{"text": "What is the status of the inventory service?"}])
        self.assertEqual(runner.client._session(runner.session_policy(item), item["case"]), item["context_id"])

    def test_duplicate_or_unknown_selector_rejected(self):
        for selectors in (("missing/case",), ("agentops_agent_core/inventory-status",) * 2):
            with self.assertRaises(ValueError):
                runner.schedule(self.cases, {"core": 1, "report": 3, "workflow": 3}, selectors)

    def test_sample_override_covers_all_cases(self):
        planned = runner.schedule(self.cases, {"core": 1, "report": 3, "workflow": 3}, samples=2)
        self.assertEqual(len(planned), 42)
        self.assertEqual(len({item["context_id"] for item in planned}), 42)

    def test_export_scope_and_hash_checked(self):
        cases, provenance = runner.load_application(self.config)
        self.assertEqual(len(cases), 21)
        self.assertFalse(provenance["evaluator_reference_texts_parsed_or_given_to_model"])
        self.application.write_bytes(self.application.read_bytes() + b" ")
        with self.assertRaises(ValueError):
            runner.load_application(self.config)

    def test_nonempty_source_state_rejected(self):
        document = runner.read_json(self.application)
        document["cases"][0]["session_input"]["state"] = {"x": "y"}
        self.application.write_bytes(runner.client._encoded(document))
        receipt = runner.read_json(self.receipt)
        receipt["files"][0].update(runner.digest(self.application))
        self.receipt.write_bytes(runner.client._encoded(receipt))
        with self.assertRaises(ValueError):
            runner.load_application(self.config)

    def test_existing_or_escaped_allocation_rejected(self):
        self.config.output.mkdir(parents=True)
        with self.assertRaises(ValueError):
            runner.validate_config(self.config)
        escaped = runner.Config(**{**vars(self.config), "output": self.root / "runs/upstream-agentops-native/../escaped"})
        with self.assertRaises(ValueError):
            runner.validate_config(escaped)

    def test_gate_requires_two_passing_timed_typed_observations(self):
        runtime = MockRuntime()
        gate = runner.collect_gate(runtime, "prelaunch", {})
        self.assertTrue(gate["eligible"])
        self.assertEqual(runtime.sleep_calls, [10.1])
        self.assertFalse(runner.collect_gate(MockRuntime(False), "prestage", {})["eligible"])
        bad = MockRuntime()
        actual = bad.memory_sample
        bad.memory_sample = lambda: {**actual(), "physical_available_bytes": True}
        self.assertFalse(runner.collect_gate(bad, "prelaunch", {})["eligible"])

    def test_gate_rejects_inconsistent_time(self):
        runtime = MockRuntime()
        actual = runtime.memory_sample
        runtime.memory_sample = lambda: {**actual(), "monotonic_ns": 3}
        self.assertFalse(runner.collect_gate(runtime, "prelaunch", {})["eligible"])

    def test_closed_stream_is_checked_after_cleanup_before_retention_and_exports(self):
        runtime = MockRuntime()
        original = runtime.closed_journal
        observed = []
        def checked(*args):
            observed.append((runtime.finished, runtime.retained, runtime.exports))
            return original(*args)
        runtime.closed_journal = checked
        result = self.one(runtime)
        self.assertEqual(result["status"], "recorded_without_benchmark_grade")
        self.assertEqual(observed, [(1, 0, 0)])
        self.assertEqual(result["closed_runtime_stream"]["source_turns_bound"], 1)
        self.assertFalse(result["closed_runtime_stream"]["benchmark_grade_proven"])

    def test_v1_bootstrap_exit_cannot_qualify_v2_runner(self):
        runtime = MockRuntime()
        self.mutate_exit(runtime, lambda value: value.update(schema_version="upstream-agentops-bootstrap/1"))
        result = self.one(runtime)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(runtime.exports, 0)
        self.assertNotIn("closed_runtime_stream", result)

    def test_incomplete_bootstrap_stream_stops_pipeline_with_closed_partial_state_retained(self):
        runtime = MockRuntime()
        self.mutate_exit(runtime, lambda value: value["runtime_stream"].update(capture_complete=False))
        result = self.one(runtime)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(runtime.exports, 0)
        self.assertEqual(runtime.retained, 1)

    def test_bootstrap_stream_returned_bool_or_float_substitution_is_rejected(self):
        for index, substituted in enumerate((True, 1.0)):
            with self.subTest(substituted=substituted):
                runtime = MockRuntime()
                self.mutate_exit(runtime, lambda value, substituted=substituted: value["runtime_stream"]["returned"].update(calls_seen=substituted))
                result = self.one(runtime, str(index))
                self.assertEqual(result["status"], "partial")
                self.assertEqual(runtime.exports, 0)

    def test_bootstrap_stream_receipt_hash_disagreement_stops_pipeline(self):
        runtime = MockRuntime()
        self.mutate_exit(runtime, lambda value: value["runtime_stream"].update(receipt_sha256="0" * 64))
        result = self.one(runtime)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(runtime.exports, 0)

    def test_tampered_original_yield_file_stops_pipeline_without_replaying_original_call(self):
        runtime = MockRuntime()
        original = runtime.client
        def mutated_client(*args, **kwargs):
            result = original(*args, **kwargs)
            path = runtime.service / "runtime-stream/invocations/000001/events/000001.json"
            path.write_bytes(path.read_bytes() + b"\n")
            return result
        runtime.client = mutated_client
        result = self.one(runtime)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(runtime.clients, 1)
        self.assertEqual(runtime.exports, 0)

    def test_memory_observer_errors_cannot_qualify_source_case_evidence(self):
        runtime = MockRuntime()
        self.mutate_exit(runtime, lambda value: value["memory_observation"].update(memory_errors=[{"status": "unsupported"}], memory_error_count=1))
        result = self.one(runtime)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(runtime.exports, 0)

    def test_public_projection_preserves_all_original_seven_files_and_exact_five_file_profile(self):
        source = self.wire()
        before = runner.inventory(source)
        destination = self.root / "projection"
        report = runner.project_public_wire(source, destination)
        self.assertEqual(runner.inventory(source), before)
        self.assertEqual(len(report["full_wire_files"]), 7)
        self.assertEqual(len(report["projection_files"]), 5)
        self.assertEqual(len(report["memory_boundary_files_retained_in_original"]), 2)
        for name in report["projection_files"]:
            self.assertEqual((source / name).read_bytes(), (destination / name).read_bytes())
        self.assertFalse(report["memory_boundaries_included_in_v1_public_export"])
        self.assertFalse(report["benchmark_grade_proven"])

    def test_public_projection_rejects_missing_extra_or_unsupported_memory_files(self):
        for index, change in enumerate(("missing", "extra", "unsupported")):
            with self.subTest(change=change):
                source = self.wire(str(index))
                directory = source / "000001"
                if change == "missing":
                    (directory / "before.memory.snapshot.json").unlink()
                elif change == "extra":
                    (directory / "unexpected.json").write_bytes(b"{}")
                else:
                    value = runner.read_json(directory / "before.memory.snapshot.json")
                    value["status"] = "unsupported"
                    (directory / "before.memory.snapshot.json").write_bytes(runner.client._encoded(value))
                destination = self.root / ("projection" + str(index))
                with self.assertRaises(ValueError):
                    runner.project_public_wire(source, destination)
                self.assertFalse(destination.exists())

    def test_public_projection_detects_original_or_copy_mutation_during_copy(self):
        for index, change_original in enumerate((True, False)):
            with self.subTest(change_original=change_original):
                source = self.wire(str(index))
                destination = self.root / ("projection" + str(index))
                original = runner.copy_checked
                changed = []
                def mutate_after_copy(incoming, outgoing, identity):
                    original(incoming, outgoing, identity)
                    if not changed:
                        target = source / "000001/before.memory.snapshot.json" if change_original else outgoing
                        target.write_bytes(target.read_bytes() + b"\n")
                        changed.append(True)
                with patch.object(runner, "copy_checked", side_effect=mutate_after_copy):
                    with self.assertRaises(ValueError):
                        runner.project_public_wire(source, destination)
                self.assertTrue(changed)

    def test_public_projection_rejects_late_empty_directory_in_original_or_projection(self):
        for index, change_original in enumerate((True, False)):
            with self.subTest(change_original=change_original):
                source = self.wire(str(index))
                destination = self.root / ("projection" + str(index))
                original = runner.copy_checked
                changed = []
                def add_empty_directory(incoming, outgoing, identity):
                    original(incoming, outgoing, identity)
                    if not changed:
                        parent = source / "000001" if change_original else outgoing.parent
                        (parent / "unexpected-empty").mkdir()
                        changed.append(True)
                with patch.object(runner, "copy_checked", side_effect=add_empty_directory):
                    with self.assertRaises(ValueError):
                        runner.project_public_wire(source, destination)
                self.assertTrue(changed)

    def test_pipeline_exports_archived_absent_memory_and_bound_public_projection(self):
        from interoperability import agentops_raw_events_v1 as raw
        from interoperability import agentops_public_events_v1 as public
        from interoperability import agentops_event_binding_v1 as binding
        service = self.root / "service"
        service.mkdir()
        source = self.wire()
        source.rename(service / "wire")
        retained = self.root / "retained"
        retained.mkdir()
        (retained / "runtime.db").write_bytes(b"inert raw exporter fixture")
        seen = []
        def export_raw(database, output):
            seen.append("raw")
            runner.write_json(output / "mock.json", {"scope": "mock"})
            return {"status": "passed"}
        def export_public(directory, output):
            seen.append("public")
            self.assertEqual({path.name for path in (directory / "000001").iterdir()}, runner.PUBLIC_V1_FILES)
            self.assertNotEqual(directory, service / "wire")
            runner.write_json(output / "mock.json", {"scope": "mock"})
            return {"status": "passed"}
        def export_binding(raw_path, public_path, output):
            seen.append("binding")
            runner.write_json(output / "mock.json", {"scope": "mock"})
            return {"status": "passed"}
        with patch.object(raw, "export_database", side_effect=export_raw), patch.object(public, "export_wire", side_effect=export_public), \
             patch.object(binding, "export_comparison", side_effect=export_binding):
            report = runner.Runtime().export(service, retained, self.root / "evidence")
        self.assertEqual(seen, ["raw", "public", "binding"])
        self.assertTrue(report["all_pipeline_steps_passed"])
        self.assertEqual(report["exports"]["memory"]["status"], "recorded")
        self.assertEqual(report["exports"]["memory"]["snapshot"]["status"], "absent")
        self.assertFalse(report["public_v1_projection_binding"]["memory_boundaries_included_in_v1_public_export"])
        self.assertEqual(len(runner.inventory(service / "wire")), 7)

    def test_prestage_failure_performs_no_staging_dependencies_or_launches(self):
        runtime = MockRuntime(False)
        with patch.object(runtime, "dependencies", side_effect=AssertionError("must not inspect dependencies")):
            result = runner.run(self.config, runtime)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["native_launch_attempts"], 0)
        self.assertFalse((self.config.output / "stage").exists())
        self.assertFalse(runner.read_json(self.config.output / "prestage-gate.json")["eligible"])

    def test_prelaunch_failure_never_constructs_job_or_client(self):
        runtime = MockRuntime(False)
        with patch.object(runtime, "job", side_effect=AssertionError("job forbidden")):
            result = self.one(runtime)
        self.assertFalse(result["launch_attempted"])
        self.assertEqual(runtime.clients, 0)

    def test_clean_mocked_instance_binds_actual_ids_but_never_grades(self):
        runtime = MockRuntime()
        result = self.one(runtime)
        self.assertEqual(result["status"], "recorded_without_benchmark_grade")
        self.assertEqual((runtime.launched, runtime.finished, runtime.clients, runtime.retained, runtime.exports), (1, 1, 1, 1, 1))
        self.assertIsNone(result["native_case_grade"])
        self.assertFalse(result["qualification_established"])
        self.assertTrue(result["observed_runtime_identity"]["runtime_identity_observed"])
        self.assertFalse(result["observed_runtime_identity"]["runtime_identity_authenticated"])
        self.assertTrue((self.root / "one/service/stop.request.json").is_file())

    def test_forced_cleanup_preserves_partial_state_but_cannot_qualify(self):
        runtime = MockRuntime()
        runtime.forced = True
        result = self.one(runtime)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(runtime.exports, 0)
        self.assertEqual(runtime.retained, 1)

    def test_launch_failure_still_finishes_owned_job(self):
        runtime = MockRuntime()
        runtime.launch_failure = True
        result = self.one(runtime)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(runtime.finished, 1)
        self.assertFalse(result["client_attempted"])

    def test_readiness_failure_stops_owned_job_without_client(self):
        runtime = MockRuntime()
        runtime.readiness_failure = True
        result = self.one(runtime)
        self.assertEqual(runtime.finished, 1)
        self.assertFalse(result["client_attempted"])
        self.assertEqual(runtime.retained, 1)

    def test_constructed_binding_mismatch_stops_before_client(self):
        runtime = MockRuntime()
        runtime.bad_binding = True
        result = self.one(runtime)
        self.assertFalse(result["client_attempted"])
        self.assertEqual(runtime.finished, 1)

    def test_partial_client_cannot_become_recorded(self):
        runtime = MockRuntime()
        runtime.client_failure = True
        result = self.one(runtime)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(runtime.finished, 1)

    def test_empty_pid_list_alone_cannot_qualify(self):
        receipt = {"forced": False, "returncode": 0, "members": [], "active_processes": 0, "job_empty_observed": True,
                   "main_handle_signaled": True, "handles_closed": True, "authority_retained": False, "errors": []}
        self.assertTrue(runner.clean_cleanup(receipt))
        for changed in ({"active_processes": 1}, {"active_processes": False}, {"returncode": None}, {"forced": True}, {"errors": ["query"]}):
            self.assertFalse(runner.clean_cleanup({**receipt, **changed}))

    def test_original_repetition_is_read_without_evaluator_import(self):
        base = self.source / "agents/python"
        (base / "evals").mkdir(parents=True)
        (base / "mise.toml").write_text('[tasks.eval]\nrun = "python eval"\n[tasks."eval:workflow"]\nrun = "python eval --repeat 3 --detailed"\n')
        (base / "evals/run_adk_eval.py").write_text('parser.add_argument("--repeat", default=1)\n')
        (base / "evals/report_eval.py").write_text('evaluate(num_runs=3)\n')
        repeats, basis = runner.original_repeats(self.source)
        self.assertEqual(repeats, {"core": 1, "report": 3, "workflow": 3})
        self.assertEqual(len(basis["source_files"]), 3)
        (base / "evals/report_eval.py").write_text('evaluate(num_runs=2)\n')
        with self.assertRaises(ValueError):
            runner.original_repeats(self.source)

    def test_runtime_identity_rejects_wrong_context_and_extra_tasks(self):
        item = runner.schedule(self.cases, {"core": 1, "report": 3, "workflow": 3})[0]
        policy = runner.session_policy(item)
        tables = {"sessions": [{"app_name": "agentops-agent", "user_id": policy["native_user_id_expected_from_source"], "id": item["context_id"]}],
                  "tasks": [{"id": "task-1", "context_id": item["context_id"]}],
                  "events": [{"app_name": "agentops-agent", "user_id": policy["native_user_id_expected_from_source"], "session_id": item["context_id"], "id": "event-1", "invocation_id": "inv-1"}]}
        public = {"turns": [{"task_id": "task-1"}]}
        self.assertTrue(runner.runtime_identity(item, public, tables)["runtime_identity_observed"])
        tables["tasks"].append({"id": "extra", "context_id": item["context_id"]})
        with self.assertRaises(ValueError):
            runner.runtime_identity(item, public, tables)

    def test_ingestion_hashes_membership_and_reference_isolation(self):
        records = []
        names = ["agents/python/src/agent/core.py", "agents/data/incidents.db", "agents/python/evals/private-reference.json"]
        names += [f"other/file-{index:04d}.txt" for index in range(418)]
        for name in names:
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"inert ingestion fixture")
            records.append({"source_relative_path": name, "kind": "regular_file", "extracted": {
                "path": "external/source/" + name, **runner.digest(path)}})
        self.ingestion.write_bytes(runner.client._encoded({"schema_version": "user-source-archive-ingestion/1", "status": "passed",
                                    "source_tree": "external/source", "regular_files": 421, "records": records}))
        identities, staged, _ = runner.verify_sources(self.config)
        self.assertEqual(len(identities), 421)
        self.assertIn(names[0], staged)
        self.assertIn(names[1], staged)
        self.assertNotIn(names[2], staged)
        (self.source / names[0]).write_bytes(b"altered source")
        with self.assertRaises(ValueError):
            runner.verify_sources(self.config)
        (self.source / names[0]).write_bytes(b"inert ingestion fixture")
        (self.source / "extra.txt").write_bytes(b"undeclared membership")
        with self.assertRaises(ValueError):
            runner.verify_sources(self.config)

    def test_full_scheduler_stops_after_first_unqualified_instance(self):
        # Real source application inputs; inert temporary runtime/source fixture.
        name = "agents/python/src/agent/example.py"
        path = self.source / name
        path.parent.mkdir(parents=True)
        path.write_bytes(b"inert source")
        helper = self.root / "scripts/helper.py"
        helper.parent.mkdir()
        helper.write_bytes(b"inert helper")
        calls = []
        def mock_one(config, runtime, item, project, staged, allocation):
            calls.append(item)
            return {"status": "partial", "launch_attempted": False, "client_attempted": False}
        with patch.object(runner, "verify_sources", return_value=({name: runner.digest(path)}, [name], {"archive_root_and_comment_commit": "mock-label"})), \
             patch.object(runner, "original_repeats", return_value=({"core": 1, "report": 3, "workflow": 3}, {})), \
             patch.object(runner, "IMPLEMENTATION", ("scripts/helper.py",)), patch.object(runner, "run_one", side_effect=mock_one):
            result = runner.run(self.config, MockRuntime())
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["planned_instances"], 33)
        self.assertEqual(result["unattempted_instances"], 32)
        self.assertEqual(result["native_upstream_case_grades"], 0)
        self.assertEqual(result["status"], "partial")
        self.assertTrue(result["original_inputs_unchanged"])

    def test_tcp_table_byte_order_and_truncation(self):
        address = struct.unpack("<I", socket.inet_aton("127.0.0.1"))[0]
        raw = struct.pack("<7I", 1, 5, address, socket.htons(19101), address, socket.htons(50001), 17)
        self.assertEqual(tcp.decode_table(raw), [{"state": 5, "local_address": "127.0.0.1", "local_port": 19101,
                                               "remote_address": "127.0.0.1", "remote_port": 50001, "owner_pid": 17}])
        with self.assertRaises(ValueError):
            tcp.decode_table(raw[:-1])
        with self.assertRaises(ValueError):
            tcp.decode_table(struct.pack("<I", 4097))

    def test_tcp_guard_requires_unique_server_side_owner_in_job(self):
        class Socket:
            def getsockname(self):
                return ("127.0.0.1", 50001)
            def getpeername(self):
                return ("127.0.0.1", 19101)
        class Owned:
            def poll(self):
                return None
            def members(self):
                return [11, 17]
        row = {"state": 5, "local_address": "127.0.0.1", "local_port": 19101,
               "remote_address": "127.0.0.1", "remote_port": 50001, "owner_pid": 17}
        result = tcp.verify_connection(Socket(), 17, Owned(), table_reader=lambda: [row])
        self.assertTrue(result["checked_before_request_bytes"])
        for rows in ([{**row, "owner_pid": 99}], [row, row], [{**row, "local_port": 50001, "remote_port": 19101}], []):
            with self.assertRaises(ValueError):
                tcp.verify_connection(Socket(), 17, Owned(), table_reader=lambda: rows)

    def test_tcp_guard_rejects_native_pid_absent_from_owned_members(self):
        class Socket:
            def getsockname(self):
                return ("127.0.0.1", 50001)
            def getpeername(self):
                return ("127.0.0.1", 19101)
        class Foreign:
            def poll(self):
                return None
            def members(self):
                return [11, 99]
        with self.assertRaises(ValueError):
            tcp.verify_connection(Socket(), 17, Foreign(), table_reader=lambda: [])

    def test_retained_cleanup_authority_is_not_discarded_and_retry_stays_partial(self):
        runtime = MockRuntime()
        class RetryingJob(Job):
            def finish(self, **kwargs):
                self.owner.finished += 1
                if self.owner.finished == 1:
                    return {"forced": True, "handles_closed": False, "authority_retained": True,
                            "job_empty_observed": False, "returncode": None, "members": [17], "active_processes": 1, "errors": []}
                # A forced cleanup remains a failed clean qualification on retry.
                return {"forced": True, "handles_closed": True, "authority_retained": False,
                        "main_handle_signaled": True, "job_empty_observed": True, "returncode": 1,
                        "members": [], "active_processes": 0, "errors": []}
        runtime.job = lambda: RetryingJob(runtime)
        result = self.one(runtime)
        self.assertEqual(runtime.finished, 2)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(runtime.held_jobs, [])
        # The live object survived the failed first finish and was retried.
        runtime.settle_owned_jobs()
        self.assertEqual(runtime.held_jobs, [])

    def test_partial_retention_rejects_uncorroborated_empty_flag(self):
        runtime = MockRuntime()
        class UnknownJob(Job):
            def finish(self, **kwargs):
                self.owner.finished += 1
                return {"forced": True, "handles_closed": True, "authority_retained": False,
                        "main_handle_signaled": False, "job_empty_observed": True,
                        "returncode": 1, "members": [], "active_processes": 1, "errors": []}
        runtime.job = lambda: UnknownJob(runtime)
        result = self.one(runtime)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(runtime.retained, 0)

    def test_real_readiness_logic_rejects_owner_before_any_http_request(self):
        service = self.root / "ready/service"
        service.mkdir(parents=True)
        runner.write_json(service / "bootstrap.created.json", {"status": "constructed_not_ready"})
        runtime = MockRuntime()
        def rejected(sock):
            raise ValueError("mock foreign accepted owner")
        runtime.connection_guard = lambda service, job: rejected
        requests = []
        connection = SimpleNamespace(sock=object(), connect=lambda: None, request=lambda *a, **k: requests.append(a), close=lambda: None)
        with patch.object(runner.http.client, "HTTPConnection", return_value=connection):
            with self.assertRaises(runner.ConnectionOwnershipError):
                runner.Runtime.ready(runtime, service, "http://127.0.0.1:19101/", Job(runtime))
        self.assertEqual(requests, [])
        self.assertEqual(runner.read_json(service / "readiness.json")["status"], "ownership_rejected")
        self.assertEqual(runtime.sleep_calls, [])

    def test_real_readiness_logic_requires_exact_original_ready_body(self):
        service = self.root / "ready/service"
        service.mkdir(parents=True)
        runner.write_json(service / "bootstrap.created.json", {"status": "constructed_not_ready"})
        runtime = MockRuntime()
        runtime.connection_guard = lambda service, job: lambda sock: None
        response = SimpleNamespace(status=200, getheaders=lambda: [], read=lambda count: b'{"status":"other"}')
        connection = SimpleNamespace(sock=object(), connect=lambda: None, request=lambda *a, **k: None,
                                     getresponse=lambda: response, close=lambda: None)
        with patch.object(runner.http.client, "HTTPConnection", return_value=connection), \
             patch.object(runner.time, "monotonic", side_effect=[0, 1, 121]):
            with self.assertRaises(ValueError):
                runner.Runtime.ready(runtime, service, "http://127.0.0.1:19101/", Job(runtime))
        self.assertEqual(runner.read_json(service / "readiness.json")["status"], "timeout")

    def test_constructor_exception_attached_job_keeps_cleanup_authority(self):
        runtime = MockRuntime()
        owned = Job(runtime)
        def fail_constructor():
            error = OSError("mock failed construction with retained Job handle")
            error.owned_job = owned
            raise error
        runtime.job = fail_constructor
        result = self.one(runtime)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(runtime.finished, 1)
        self.assertFalse(result["launch_attempted"])

    def test_quarantine_keeps_authority_through_broken_pipe_and_sleep_interrupt(self):
        runtime = MockRuntime()
        class Held:
            def __init__(self):
                self.calls = 0
            def finish(self, **kwargs):
                self.calls += 1
                return {"handles_closed": self.calls > 1, "authority_retained": self.calls <= 1}
        held = Held()
        runtime.held_jobs = [held]
        runtime.sleep = lambda seconds: (_ for _ in ()).throw(KeyboardInterrupt())
        with patch("builtins.print", side_effect=BrokenPipeError()):
            runtime.settle_owned_jobs()
        self.assertEqual(held.calls, 2)
        self.assertEqual(runtime.held_jobs, [])

    def test_quarantine_keeps_authority_through_finish_interrupt(self):
        runtime = MockRuntime()
        class Held:
            def __init__(self):
                self.calls = 0
            def finish(self, **kwargs):
                self.calls += 1
                if self.calls == 1:
                    raise KeyboardInterrupt()
                return {"handles_closed": True, "authority_retained": False}
        held = Held()
        runtime.held_jobs = [held]
        with patch("builtins.print"):
            runtime.settle_owned_jobs()
        self.assertEqual(held.calls, 2)
        self.assertEqual(runtime.held_jobs, [])

    def test_quarantine_keeps_authority_through_snapshot_interrupt(self):
        runtime = MockRuntime()
        class Held:
            def finish(self, **kwargs):
                return {"handles_closed": True, "authority_retained": False}
        held = Held()
        runtime.held_jobs = [held]
        calls = []
        def snapshot(values):
            calls.append(1)
            if len(calls) == 1:
                raise KeyboardInterrupt()
            return list(values)
        with patch("builtins.print"), patch.object(runner, "list", side_effect=snapshot, create=True):
            runtime.settle_owned_jobs()
        self.assertEqual(len(calls), 2)
        self.assertEqual(runtime.held_jobs, [])


if __name__ == "__main__":
    unittest.main()
