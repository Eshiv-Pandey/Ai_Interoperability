"""Fresh allocation and gating tests. No service, bridge or model is launched."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import agentops_admission_live_plan_v2 as design
import agentops_admission_control_v2 as control


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
