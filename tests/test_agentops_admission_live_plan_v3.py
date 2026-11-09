"""Fresh allocation and gating tests. No service, bridge or model is launched."""
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import agentops_admission_live_plan_v3 as design
import agentops_admission_control_v3 as control
import agentops_admission_live_plan_v2 as previous_design
import execute_agentops_admission_phase_v3 as phase_driver
from check_agentops_startup_v1 import diagnostic_launch


class AdmissionLivePlanTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="agentops-fresh-plan-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def write(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_versioned_launch_and_client_semantics_preserve_the_previous_gate(self):
        plan = {"runtime_python": "/sealed/python", "bridge_runtime": "/sealed/bridges", "node": {"path": "/usr/bin/node"}}
        for case in ("N11", "B7"):
            self.assertEqual(design.client_config(case, self.root / case, plan, self.root),
                             previous_design.client_config(case, self.root / case, plan, self.root))
        self.assertEqual(design.READINESS_TIMEOUT_SECONDS, 65)
        with patch.object(control, "ROOT", Path('/sealed')):
            argv = control.service_argv(plan, Path('/sealed/runs/agentops-http-control/N11/service'))
        parsed = diagnostic_launch(Path('N11'), {'pid': 123, 'argv': argv})
        self.assertEqual((parsed['exit_seconds'], parsed['startup_seconds']), (5.0, 5.0))
        self.assertIn('serve_agentops_bridge_diagnostic_v4.py', argv[2])
        commands = phase_driver.phase_commands('software', self.root, self.root / 'reuse', '/python', self.root / 'plan.json')
        names = {name for name, _, _ in commands}
        self.assertTrue({'test_agentops_admission_live_plan_v3', 'test_check_agentops_interpreter_exit_v2',
                         'test_check_agentops_startup_v1', 'test_agentops_startup_diagnostics_v1',
                         'test_agentops_admission_chain_v3',
                         'test_export_agentops_admission_v3'}.issubset(names))
        for phase, script in (('prepare', 'agentops_admission_live_plan_v3.py'),
                              ('launch', 'agentops_admission_control_v3.py')):
            command = phase_driver.phase_commands(phase, self.root, self.root / 'reuse', '/python', self.root / 'plan.json')[0][1]
            self.assertIn('scripts/' + script, command)

    def test_missing_startup_or_existing_acceptance_evidence_cannot_qualify_native(self):
        checked, result = {'strict_success': True}, {'status': 'recorded'}
        diagnostic = {'valid': True, 'complete': True, 'classification': 'asyncio_run_returned'}
        exit_check = startup = {'valid': True, 'complete': True}
        self.assertTrue(control.strict_case_acceptance(checked, result, diagnostic, exit_check, startup))
        for partial in ({}, {'valid': True, 'complete': False}, {'valid': False, 'complete': True}):
            self.assertFalse(control.strict_case_acceptance(checked, result, diagnostic, exit_check, partial))
        self.assertFalse(control.strict_case_acceptance({'strict_success': False}, result, diagnostic, exit_check, startup))
        self.assertFalse(control.strict_case_acceptance(checked, {'status': 'failed'}, diagnostic, exit_check, startup))
        self.assertFalse(control.strict_case_acceptance(checked, result, dict(diagnostic, classification='partial'), exit_check, startup))
        self.assertFalse(control.strict_case_acceptance(checked, result, diagnostic, {'valid': True, 'complete': False}, startup))

    def test_after_inspection_runtime_mismatch_cannot_be_reported_as_passed(self):
        report = {'phase': 'after', 'commands': [{'returncode': 0}, {'returncode': 0}],
                  'staged_sources_unchanged': True}
        self.assertEqual(phase_driver.phase_status(report, 2), 'failed')
        report['python_runtime_equal'] = False
        self.assertEqual(phase_driver.phase_status(report, 2), 'failed')
        report['python_runtime_equal'] = True
        self.assertEqual(phase_driver.phase_status(report, 2), 'passed')
        report['staged_sources_unchanged'] = False
        self.assertEqual(phase_driver.phase_status(report, 2), 'failed')

    def test_readiness_timeout_withholds_client_and_retains_new_partial_diagnostics(self):
        for name in (design.SERVICE_ENTRYPOINT, 'scripts/agentops_startup_diagnostics_v1.py', 'scripts/check_agentops_startup_v1.py'):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('# inert captured helper', encoding='utf-8')
        plan_path = self.write('prepared.json', {})
        plan = {'runtime_python': '/sealed/python', 'bridge_runtime': '/sealed/bridges', 'node': {'path': '/usr/bin/node'}}

        def inert_popen(argv, **_):
            output = Path(argv[4]) / 'startup-diagnostics'
            output.mkdir()
            events = []
            for i, phase in enumerate(('startup_observer_armed', 'startup_monitor_started'), 1):
                event = {'schema_version': 'agentops-startup-event/1', 'sequence': i, 'pid': 123,
                         'phase': phase, 'monotonic_ns': time.monotonic_ns(), 'at_epoch_ns': time.time_ns(), 'diagnostic_errors': []}
                if i == 1:
                    event.update(interval_seconds=5.0, poll_seconds=.05, capture_backend='daemon_dump_traceback')
                events.append(event)
            (output / 'lifecycle.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in events), encoding='utf-8')
            (output / 'startup-stacks.txt').write_bytes(b'')
            return SimpleNamespace(pid=123, poll=lambda: None)

        def stopped(_process, _argv, _service, result):
            result.update(service_returncode=-15, forced_service_stop=True,
                          service_group_cleanup={'initially_empty': True, 'final_empty': True, 'forced_cleanup': False, 'errors': []})

        with ExitStack() as stack:
            for target, name, value in ((control, 'ROOT', self.root), (design, 'verify', lambda *_a, **_k: {'status': 'verified'}),
                                        (design, 'probe_port', lambda: {}), (control.evidence, 'source_inventory', lambda: []),
                                        (control.evidence, 'clean_environment', lambda _: {}), (control.evidence, 'PROJECT', self.root / 'project'),
                                        (control.evidence, 'SOURCE', self.root / 'source'), (control, 'seed_snapshot', lambda _: {}),
                                        (control, 'check_service', lambda *_: {'strict_success': False}),
                                        (control, 'check_case', lambda *_: {'strict_success': False}),
                                        (control, 'validate_diagnostics', lambda *_: {'valid': True, 'complete': False}),
                                        (control, 'stop_service', stopped)):
                stack.enter_context(patch.object(target, name, value))
            spawn = stack.enter_context(patch.object(control.subprocess, 'Popen', side_effect=inert_popen))
            client = stack.enter_context(patch.object(control, 'capture_client'))
            stack.enter_context(patch.object(control.time, 'monotonic', side_effect=[0, 65]))
            receipt = control.run_case('N11', plan, plan_path)
        spawn.assert_called_once()
        client.assert_not_called()
        self.assertFalse(receipt['strict_success'])
        case = self.root / (design.CASE_PREFIX + 'N11')
        result = json.loads((case / 'result.json').read_bytes())
        self.assertEqual(result['error'], 'TimeoutError: Fixture readiness deadline')
        startup = json.loads((case / 'startup-check.json').read_bytes())
        self.assertTrue(startup['valid'], startup)
        self.assertFalse(startup['complete'])
        self.assertEqual(startup['captures_started'], 0)
        self.assertFalse((case / 'client').exists())

    def test_two_fixed_cases_have_one_matched_control_then_explicit_admission(self):
        self.assertEqual(list(design.CASES), ["N11", "B7"])
        plan = {"runtime_python": "/reused/python", "bridge_runtime": "/reused/bridges", "node": {"path": "/usr/bin/node"}}
        native = design.client_config("N11", self.root / "native", plan, self.root)
        admitted = design.client_config("B7", self.root / "admitted", plan, self.root)
        self.assertEqual((native["profile"], native["representation"]), ("mg-raw-header", "data"))
        self.assertEqual(admitted["schema_version"], "agentops-admitted-client-config/1")
        self.assertEqual(admitted["admission"]["budget"], 100000)
        self.assertEqual(admitted["admission"]["timeout_ms"], 30000)
        self.assertEqual(admitted["admission"]["deployment"]["header_mode"], "version-header")
        self.assertNotIn("output_dir", admitted["admission"])
        self.assertEqual(admitted["bridge"]["env"]["A2A_MAX_RETRIES"], "0")

    def test_zero_code_after_forced_service_stop_is_not_clean_acceptance(self):
        service = self.root / "service"; service.mkdir()
        process = SimpleNamespace(pid=123)
        receipt = {"returncode": 0, "graceful_timeout": True, "signal_requests": [{"signal": "SIGTERM"}],
            "reaped_before_group_check": True, "errors": [],
            "owned_group": {"initially_empty": True, "final_empty": True, "forced_cleanup": False, "errors": []}}
        result = {"cleanup_errors": []}
        with patch.object(control, "finish_owned_child", return_value=receipt):
            control.stop_service(process, ["inert-command"], service, result)
        self.assertEqual(result["service_returncode"], 0)
        self.assertTrue(result["forced_service_stop"])
        self.assertEqual(result["service_child_cleanup"], receipt)

    def test_all_staged_helpers_are_pinned_and_changed_source_is_rejected(self):
        rows = []
        for index in range(421):
            path = self.root / f"external/agentops-c806b7f1/file-{index}.txt"
            path.parent.mkdir(parents=True, exist_ok=True); path.write_text(str(index), encoding="utf-8")
            rows.append({"kind": "regular_file", "extracted": design.record(path, self.root)})
        for name in design.PINNED_DOCS:
            self.write(name, {})
        self.write(design.PINNED_DOCS[0], {"records": rows})
        for name in design.REQUIRED_SCRIPTS:
            path = self.root / "scripts" / name; path.parent.mkdir(exist_ok=True)
            path.write_text("# fixture", encoding="utf-8")
        helper = self.root / "scripts/additional_imported_helper.py"; helper.write_text("# original", encoding="utf-8")
        self.write("src/interoperability/pending_admission.py", {})
        reproduction_paths = ["tests/test_fixture.py", "tests/test_fixture.mjs",
            "examples/refinement-development/manifest.json", "examples/refinement-development/profile.json",
            "examples/benchmark-development/recipe-v1.json", "examples/benchmark-development/suite.json"]
        for name in reproduction_paths:
            self.write(name, {})
        inputs = design.staged_inventory(self.root)
        recorded = {row["path"] for row in inputs}
        self.assertIn("scripts/additional_imported_helper.py", recorded)
        self.assertTrue(set(reproduction_paths).issubset(recorded))
        plan = {"schema_version": design.SCHEMA, "workspace": str(self.root.resolve()),
                "cases": list(design.CASES.values()), "inputs": inputs}
        helper.write_text("# changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "source/code inputs changed"), patch.object(control.subprocess, "Popen") as spawn:
            design.verify(plan, self.root)
        spawn.assert_not_called()
        helper.write_text("# original", encoding="utf-8")
        self.write("examples/refinement-development/profile.json", {"changed": True})
        with self.assertRaisesRegex(ValueError, "source/code inputs changed"):
            design.verify(plan, self.root)
        manifest = self.root / "examples/refinement-development/manifest.json"
        self.assertTrue(manifest.resolve().is_relative_to(self.root.resolve()))
        manifest.unlink()
        with self.assertRaisesRegex(ValueError, "Required reproduction fixture missing"):
            design.staged_inventory(self.root)

    def test_existing_case_is_refused_before_port_probe_or_process_creation(self):
        (self.root / (design.CASE_PREFIX + "N11")).mkdir(parents=True)
        with patch.object(control, "ROOT", self.root), patch.object(design, "verify"), \
                patch.object(design, "probe_port") as probe, patch.object(control.subprocess, "Popen") as spawn:
            with self.assertRaisesRegex(FileExistsError, "no rerun"):
                control.run_case("N11", {}, self.root / "plan.json")
        probe.assert_not_called(); spawn.assert_not_called()

    def test_failed_native_control_blocks_b7_and_group_output_cannot_be_reused(self):
        plan = self.write("plan.json", {})
        with patch.object(control, "ROOT", self.root), patch.object(control.sys, "platform", "linux"), \
                patch.object(design, "verify", return_value={"status": "verified"}), \
                patch.object(control, "run_case", return_value={"status": "recorded", "strict_success": False}) as run_case, \
                patch.object(control.subprocess, "Popen") as spawn, redirect_stdout(io.StringIO()):
            result = control.run_group(plan)
            self.assertEqual(run_case.call_count, 1)
            self.assertEqual(run_case.call_args.args[0], "N11")
            self.assertEqual(result["cases"]["B7"]["status"], "skipped")
            with self.assertRaises(FileExistsError):
                control.run_group(plan)
            spawn.assert_not_called()

    def test_exception_after_allocation_retains_partial_case_and_withholds_b7(self):
        plan = self.write("plan.json", {})
        def partial(case_id, *_):
            self.write(design.CASE_PREFIX + case_id + "/service-process.json", {"pid": 123})
            raise OSError("simulated final receipt write failure")
        with patch.object(control, "ROOT", self.root), patch.object(control.sys, "platform", "linux"), \
                patch.object(design, "verify", return_value={"status": "verified"}), \
                patch.object(control, "run_case", side_effect=partial) as run_case, \
                patch.object(control.subprocess, "Popen") as spawn, redirect_stdout(io.StringIO()):
            result = control.run_group(plan)
        self.assertEqual(run_case.call_count, 1); spawn.assert_not_called()
        native = result["cases"]["N11"]
        self.assertEqual(native["status"], "failed_partial")
        self.assertTrue(native["allocated"]); self.assertTrue(native["service_process_receipt_present"])
        self.assertEqual(result["cases"]["B7"]["status"], "unexecuted")
        self.assertTrue((self.root / design.GROUP / "attempt/N11.partial.json").is_file())

    def test_admission_subprocess_cleanup_accepts_only_exact_canonical_command(self):
        case = self.root / "case"
        config = {"bridge": {"command": "/usr/bin/node", "args": ["/bridge.mjs"]},
                  "admission": {"python": "/runtime/python"}}
        argv = ["/usr/bin/node", "/client.mjs"]
        args = ["-B", "-m", "interoperability.pending_admission", "--input", str(case / "client/admission/snapshot.json"),
                "--output", str(case / "client/admission/result.json"), "--now", "100", "--budget", "100000"]
        def put(values):
            self.write("case/client/admission/execution.json", {"schema_version": "agentops-admission-subprocess/1",
                "executable": "/runtime/python", "args": values, "cwd": str(self.root)})
        with patch.object(control, "ROOT", self.root):
            put(args)
            self.assertEqual(control.allowed_client_commands(argv, case, config)[-1], ["/runtime/python", *args])
            invalid = [args[:-1], args + ["extra"]]
            for clock in ("+100", "0100", "-1", "١٠٠", 100):
                changed = list(args); changed[8] = clock; invalid.append(changed)
            changed = list(args); changed[2] = "unpermitted.module"; invalid.append(changed)
            for values in invalid:
                with self.subTest(args=values):
                    put(values)
                    with self.assertRaises(ValueError):
                        control.allowed_client_commands(argv, case, config)

    def test_actual_origin_params_must_exactly_match_certified_continuation(self):
        case = self.root / "case"
        params = {"message": {"taskId": "task", "contextId": "context", "parts": [{"data": {"confirmed": True}}]}}
        receipt = {"request": {"method": "tools/call", "params": {"name": "a2a_request", "arguments": {
            "url": "http://127.0.0.1:18764/", "method": "SendMessage", "params": params}}}}
        self.write("case/client/admission/result.json", receipt)
        (case / "service/wire/000001").mkdir(parents=True)
        actual = {"request": {"jsonrpc": "2.0", "id": "bridge-generated", "method": "SendMessage", "params": deepcopy(params)},
                  "record": {"sequence": 1}}
        with patch.object(control, "ROOT", self.root), patch.object(control, "parse_asgi_exchange", return_value=actual):
            self.assertTrue(control.check_certified_origin_request(case, {"task_id": "task"})["valid"])
            actual["request"]["params"]["message"]["parts"][0]["data"]["confirmed"] = 1
            mismatch = control.check_certified_origin_request(case, {"task_id": "task"})
            self.assertFalse(mismatch["valid"])
            self.assertIn("differ", mismatch["errors"][0])

    def test_admitted_check_binds_process_receipt_and_evaluator_chronology(self):
        case = self.root / "case"
        config_path = self.write("case/client-config.json", {"schema_version": "fixture"})
        self.write("case/client/config.json", {"schema_version": "fixture"})
        self.write("case/plan.json", {"client_config": design.record(config_path, self.root)})
        process = {"pid": 123, "returncode": 0, "timed_out": False, "forced_kill": False,
            "cleanup_errors": [], "owned_group": {"fixture": True},
            "started_at_utc": "2026-10-29T00:00:00+00:00", "finished_at_utc": "2026-10-29T00:00:01+00:00"}
        self.write("case/client-process.json", process); self.write("case/service-process.json", {"pid": 456})
        result = {"status": "recorded", "client_returncode": 0, "client_timed_out": False, "client_forced_kill": False,
            "client_group_cleanup": {"fixture": True}, "service_group_cleanup": {"fixture": True}, "cleanup_errors": [],
            "service_returncode": 0, "forced_service_stop": False, "bridge_clean_exit": True,
            "bridge_forced_kill": False, "source_unchanged_after": True,
            "evaluator_query": {"executed": True, "grader_only": True, "available_to_client": False,
                                "task_id": "task", "context_id": "context"}}
        service = {"strict_success": True, "original": {"task_id": "task", "context_id": "context"},
            "evaluator_final_started_at_utc": "2026-10-29T00:00:02+00:00"}
        checker = SimpleNamespace(check_client=lambda *_args, **_kwargs: {"client_scope_verified": True,
            "public_bindings": {"task_id": "task", "context_id": "context"}})
        with patch.object(control, "ROOT", self.root), patch.dict(sys.modules, {"check_agentops_admitted_client_v1": checker}), \
                patch.object(control, "check_owned_group", return_value=True), \
                patch.object(control, "check_certified_origin_request", return_value={"valid": True}):
            self.assertTrue(control.admitted_case_check(case, {"inputs": []}, result, service)["strict_success"])
            service["evaluator_final_started_at_utc"] = "2026-10-29T00:00:00+00:00"
            self.assertFalse(control.admitted_case_check(case, {"inputs": []}, result, service)["strict_success"])
            service["evaluator_final_started_at_utc"] = "2026-10-29T00:00:02+00:00"
            process["returncode"] = 1; self.write("case/client-process.json", process)
            self.assertFalse(control.admitted_case_check(case, {"inputs": []}, result, service)["strict_success"])
            process["returncode"] = 0; self.write("case/client-process.json", process)
            result["evaluator_query"]["available_to_client"] = True
            self.assertFalse(control.admitted_case_check(case, {"inputs": []}, result, service)["strict_success"])


if __name__ == "__main__":
    unittest.main()
