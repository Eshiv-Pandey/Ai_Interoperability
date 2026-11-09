"""Constructed export tests. No Linux, application, server or model is executed."""
import ast
from contextlib import contextmanager
import copy
import json
from pathlib import Path
import sys
import tomllib
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_agentops_socket_resume_v8 as checker
from export_agentops_workspace_v7 import export_evidence
from run_agentops_linux_workspace_v5 import copy_exact, record
from test_agentops_http_control import authored_files, fixtures
from test_agentops_socket_policy_v1 import policy_fixture
from check_agentops_effect_v3 import check_record


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if isinstance(value, bytes) else json.dumps(value, indent=2).encode())


def capture(root, folder, label, argv, stdout=b"authored capture; not executed\n", cwd=None):
    directory = root / folder
    write(directory / f"{label}.stdout.bin", stdout)
    write(directory / f"{label}.stderr.bin", b"")
    times = {
        (checker.NATIVE, 'prepared-runtime'): ('00:59:01','00:59:02'),
        (checker.NATIVE, 'execution-runtime'): ('00:59:21','00:59:22'),
        (checker.NATIVE, 'upstream-confirmation'): ('01:00:00','01:00:04'),
        (checker.NATIVE, 'independent-effect-check'): ('01:00:05','01:00:06'),
        (checker.HTTP, 'prepared-runtime'): ('01:00:21','01:00:22'),
        (checker.HTTP, 'execution-runtime'): ('01:00:31','01:00:32'),
        (checker.HTTP, 'wire-check'): ('01:01:30','01:01:31'),
    }
    start, end = ['2026-10-27T'+value+'+00:00' for value in times[(folder, label)]]
    receipt = {"argv": argv, "cwd": cwd or checker.load(checker.PRIOR / "result.json")["linux_workspace"],
               "returncode": 0, "timed_out": False,
               "started_at_utc": start, "finished_at_utc": end,
               "stdout": record(directory / f"{label}.stdout.bin", root),
               "stderr": record(directory / f"{label}.stderr.bin", root)}
    write(directory / (label + ".json"), receipt)


def seal(root, folder, value):
    value = copy.deepcopy(value)
    value["files"] = [record(path, root) for path in sorted((root / folder).iterdir())
                      if path.is_file() and path.name != "result.json"]
    write(root / folder / "result.json", value)


def fixture(base):
    """Real unchanged input bytes plus wholly authored runtime/outcome evidence."""
    base.mkdir()
    write(base / "AUTHORED-TEST-DATA.txt", b"All new runtime and success evidence here is constructed. No application execution.\n")
    replica, run = base / "authored-source", base / "authored-export"
    replica.mkdir()
    run.mkdir()
    old = checker.load(checker.PRIOR / "export-manifest.json")
    copy_exact(checker.PRIOR / "workspace", replica, old["files"])
    expected = checker.load(checker.SEAL)["replica_inputs"]
    old_names = {row["path"] for row in old["files"]}
    copy_exact(ROOT, replica, [row for row in expected if row["path"] not in old_names])
    linux = old["original_linux_root"]
    absolute = lambda name: checker.linux_path(linux, name)
    site = 'external/runtime-agentops-linux-v7/venv/lib/python3.13/site-packages'
    source = replica / 'external/agentops-c806b7f1'
    runtime = checker.load(replica / checker.SETUP / 'installed-runtime.stdout.bin')
    write(replica / site / 'urllib3/util/connection.py',
          (ROOT / 'docs/research/source-evidence/agentops-socket-policy-v1/source/urllib3-util-connection.py').read_bytes())
    # The old run stopped before HTTP preparation, so these future harness
    # sources were not exported. Supply explicit, never-executed test bytes.
    for name in ('a2a/server/routes/jsonrpc_dispatcher.py', 'a2a/server/routes/agent_card_routes.py',
                 'a2a/server/request_handlers/response_helpers.py', 'a2a/utils/constants.py',
                 'google/adk/a2a/utils/agent_to_a2a.py', 'uvicorn/server.py'):
        if not (replica / site / name).exists():
            write(replica / site / name, b"raise AssertionError('Authored placeholder; must never execute')\n")
    http, sources = checker.validators_for(replica, expected, linux)
    native, wire = checker.NATIVE, checker.HTTP
    inspection = [absolute(checker.RUNTIME), '-I', absolute(checker.INSPECTOR)]
    verifier_seal = base / 'authored-verifier-seal.json'
    write(verifier_seal, {'files': [record(ROOT / 'scripts/check_agentops_socket_resume_v8.py', ROOT)]})
    checker.VERIFIER_SEAL = verifier_seal
    seed_path = source / "agents/data/incidents.db"
    seed = checker.seed_snapshot(seed_path)
    profile = json.loads(json.dumps(fixtures.authored_profile(seed)).replace('2026-10-25T01:00:', '2026-10-27T01:00:'))
    policy = policy_fixture()
    policy['capability_source']['installed_path'] = absolute(site + '/urllib3/util/connection.py')
    profile.update(schema_version='agentops-passive-upstream-observation/3', socket_policy=policy)
    for label in ("prepared-runtime", "execution-runtime"):
        capture(replica, native, label, inspection, runtime)
    for name, value in (("seed-before.json", seed), ("isolated-seed-before.json", seed),
                        ("preparation-result.json", {"status": "prepared"}), ("passive-profile.json", profile)):
        write(replica / native / name, value)
    effect = check_record(profile, seed)
    effect.update(schema_version="agentops-independent-effect-check/3",
        profile_sha256=record(replica / native / "passive-profile.json", replica)["sha256"],
        seed_sha256=record(seed_path, replica)["sha256"])
    write(replica / native / "effect-check.json", effect)
    write(replica / native / "plan.json", {"schema_version": "agentops-native-plan/7", "source_files": sources,
        "harness_files": http.native.harness(), "runtime_setup": record(replica / checker.SETUP / "result.json", replica),
        "directory_capability_in_preparation": True,
        "runtime_inventory": record(replica / native / "prepared-runtime.stdout.bin", replica),
        "seed_snapshot": record(replica / native / "seed-before.json", replica)})
    write(replica / native / "execution.json", {"schema_version": "agentops-native-execution/7", "runtime_python": absolute(checker.RUNTIME), "plan": record(replica / native / "plan.json", replica)})
    write(replica / native / "pytest-reports.json", {"exitstatus": 0, "reports": [
        {"nodeid": checker.native.original.NODEID, "when": when, "outcome": "passed"}
        for when in ("setup", "call", "teardown")]})
    project, ndir = absolute("external/agentops-c806b7f1/agents/python"), absolute(native)
    capture(replica, native, "upstream-confirmation", [absolute(checker.RUNTIME), "-B", "-m", "pytest",
        "-c", project + "/pyproject.toml", "-p", "agentops_native_probe_v3_plugin", "--basetemp", ndir + "/pytest-temp",
        "-o", "cache_dir=" + ndir + "/pytest-cache", "--junitxml", ndir + "/junit.xml", checker.native.original.NODEID], cwd=project)
    capture(replica, native, "independent-effect-check", ["/usr/bin/python3", "-B", absolute("scripts/check_agentops_effect_v3.py"),
        "--profile", ndir + "/passive-profile.json", "--seed-db", absolute("external/agentops-c806b7f1/agents/data/incidents.db"),
        "--output", ndir + "/effect-check.json"])
    seal(replica, native, {"schema_version": "agentops-native-result/7", "status": "upstream_and_boundary_effect_check_passed",
        "source_unchanged_after": True, "pytest_returncode": 0, "independent_check": "passed",
        "application_test_started": True, "live_model_calls": 0})
    for name, raw in authored_files(seed).items():
        if name.endswith('.json'):
            raw = raw.replace(b'2026-10-26T00:00:', b'2026-10-27T01:01:')
        write(replica / wire / name, raw)
    for label in ("prepared-runtime", "execution-runtime"):
        capture(replica, wire, label, inspection, runtime)
    plan = checker.load(replica / wire / "plan.json")
    plan.update(controller_version="agentops-http-control/5", source_files=sources, harness_files=http.harness(runtime),
                native_prerequisite=record(replica / native / "result.json", replica),
                runtime_inventory=record(replica / wire / "prepared-runtime.stdout.bin", replica))
    write(replica / wire / "plan.json", plan)
    write(replica / wire / "preparation-result.json", {"status": "prepared_not_executed"})
    write(replica / wire / "execution.json", {"schema_version": "agentops-http-execution/5",
        "plan": record(replica / wire / "plan.json", replica), "native_prerequisite": plan["native_prerequisite"]})
    capture(replica, wire, "wire-check", ["/usr/bin/python3", "-B", absolute("scripts/check_agentops_http_v2.py"),
        "--run", absolute(wire), "--output", absolute(wire + "/check.json")])
    service = checker.load(replica / wire / 'service-result.json')
    service_policy = policy_fixture(port=18761)
    service_policy['capability_source']['installed_path'] = absolute(site + '/urllib3/util/connection.py')
    service.update(observer_version=2, socket_policy=service_policy, finished_at_utc='2026-10-27T01:01:21+00:00')
    write(replica / wire / 'service-result.json', service)
    write(replica / wire / 'service-process.json', {'pid': 1001, 'argv': [absolute(checker.RUNTIME), '-B',
        absolute('scripts/serve_agentops_http_v2.py'), '--output', absolute(wire), '--port', '18761'],
        'started_at_utc': '2026-10-27T01:00:35+00:00'})
    write(replica / wire / 'service-ready.json', {'port':18761, 'state_dir':absolute(wire+'/state'),
        'source_factory':absolute('external/agentops-c806b7f1/agents/python/src/agent/server.py'),
        'started_at_utc':'2026-10-27T01:00:36+00:00'})
    write(replica / wire / 'stop-requested.json', {'requested_at_utc':'2026-10-27T01:01:20+00:00'})
    write(replica / wire / 'service.stdout.bin', b'Authored service output, no process ran')
    write(replica / wire / 'service.stderr.bin', b'')
    checked = checker.check_wire(replica / wire, seed)
    checked.update(schema_version="agentops-http-check/2", inputs=[{"path": p.name, "sha256": record(p, replica)["sha256"]}
                   for p in sorted((replica / wire).iterdir()) if p.is_file()])
    write(replica / wire / "check.json", checked)
    seal(replica, wire, {"schema_version": "agentops-http-result/5", "status": "wire_and_effect_check_passed",
        "source_unchanged_after": True, "live_model_calls": 0, "forced_service_stop": False, "service_returncode": 0})
    exported = export_evidence(replica, run / "workspace", expected)
    assert exported["reference_failures"] == [], exported["reference_failures"]
    # The entire new capture is authored; model its declared original Linux
    # namespace explicitly while keeping every file record relative and exact.
    exported["original_linux_root"] = linux
    write(run / "export-manifest.json", exported)
    state = {"schema_version": "agentops-linux-socket-resume/8", "status": "native_and_http_controls_passed",
        "linux_workspace": linux, "parent_inputs_unchanged": True, "export_reference_failures": [],
        "installations": 0, "live_model_calls": 0, "research_gate_credit_added": 0, "qualified_second_domain": False,
        "native_result": "upstream_and_boundary_effect_check_passed", "http_result": "wire_and_effect_check_passed",
        "exported_files": len(exported["files"]), "prior_attempt": record(checker.PRIOR / "result.json", ROOT),
        "started_at_utc": "2026-10-27T00:59:00+00:00", "finished_at_utc": "2026-10-27T01:01:50+00:00"}
    write(run / "result.json", state)
    write(run / "execution.json", dict(state, inputs=expected,
          prior_export=record(checker.PRIOR / "export-manifest.json", ROOT), launch_seal=record(checker.SEAL, ROOT)))
    write(run / "linux-workspace.json", {"path": linux})
    stage_times = {
        'native-prepare': ('2026-10-27T00:59:00+00:00','2026-10-27T00:59:10+00:00'),
        'native-control': ('2026-10-27T00:59:20+00:00','2026-10-27T01:00:15+00:00'),
        'http-prepare': ('2026-10-27T01:00:20+00:00','2026-10-27T01:00:25+00:00'),
        'http-control': ('2026-10-27T01:00:30+00:00','2026-10-27T01:01:40+00:00')}
    for i, (label, arguments) in enumerate([
        ("native-prepare", ["scripts/agentops_native_probe_v7.py", "prepare"]),
        ("native-control", ["scripts/agentops_native_probe_v7.py", "run"]),
        ("http-prepare", ["scripts/agentops_http_control_v5.py", "prepare"]),
        ("http-control", ["scripts/agentops_http_control_v5.py", "run"]) ]):
        stage = {"argv": ["/usr/bin/python3", "-B", "-X", "utf8", *arguments], "cwd": linux, "linux_pid": 123+i,
                 "started_at_utc": stage_times[label][0], "timed_out": False}
        write(run / (label + ".started.json"), stage)
        for suffix in ("stdout", "stderr"):
            write(run / f"{label}.{suffix}.bin", b"authored, not executed\n")
        stage.update(returncode=0, finished_at_utc=stage_times[label][1],
                     streams=[record(run / f"{label}.{suffix}.bin", run) for suffix in ("stdout", "stderr")])
        write(run / (label + ".json"), stage)
    return run, expected, linux


class ResumeExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.run_dir, cls.expected, cls.linux = fixture(ROOT / "tmp" / ("authored-resume-export-" + uuid.uuid4().hex))
        cls.export = cls.run_dir / "workspace"

    @contextmanager
    def edits(self):
        saved = {}
        def edit(path, transform):
            saved.setdefault(path, path.read_bytes())
            value = checker.load(path)
            transform(value)
            write(path, value)
        try:
            yield edit
        finally:
            for path, raw in saved.items():
                write(path, raw)

    def reseal_export(self, edit):
        def update(value):
            value["files"] = [record(self.export / row["path"], self.export) for row in value["files"]]
            value["bytes"] = sum(row["bytes"] for row in value["files"])
        edit(self.run_dir / "export-manifest.json", update)

    def reseal_result(self, folder, edit):
        edit(self.export / folder / "result.json", lambda value: value.update(files=[
            record(self.export / row["path"], self.export) for row in value["files"]]))

    def test_complete_constructed_export_passes_without_executing_archive(self):
        result = checker.check(self.run_dir)
        self.assertEqual(result["status"], "artifact_integrity_and_semantics_verified")
        self.assertEqual(result["http_semantics"]["new_audit_rows"], 1)
        self.assertFalse(result["fresh_experiment"])

    def test_receipt_rebasing_preserves_original_bytes_and_digest(self):
        http, _ = checker.validators_for(self.export, self.expected, self.linux)
        path = self.export / checker.SETUP / "installed-runtime.json"
        before = path.read_bytes()
        actual = http.evidence.load_json(path)
        self.assertEqual(actual["argv"][0], str(self.export / checker.RUNTIME))
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(http.evidence.digest(path), record(path, self.export))
        self.assertTrue(Path(http.__file__).resolve().is_relative_to(ROOT / "scripts"))

    def test_forged_original_command_cannot_be_hidden_by_rebasing(self):
        with self.edits() as edit:
            path = self.export / checker.SETUP / "installed-runtime.json"
            edit(path, lambda value: value["argv"].__setitem__(0, "/different/python"))
            http, _ = checker.validators_for(self.export, self.expected, self.linux)
            with self.assertRaisesRegex(ValueError, "original setup command"):
                http.evidence.load_json(path)

    def test_wrong_resume_schema_and_prior_binding_are_rejected(self):
        for changes in ({"schema_version": "agentops-linux-filesystem-attempt/5"}, {"prior_attempt": {}}):
            with self.edits() as edit:
                edit(self.run_dir / "result.json", lambda value: value.update(changes))
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    checker.package_integrity(self.run_dir, self.expected)

    def test_outer_outcome_cannot_hide_successful_inner_attempt(self):
        with self.edits() as edit:
            edit(self.run_dir / "result.json", lambda value: value.update(native_result="not_run"))
            with self.assertRaisesRegex(ValueError, "Outer outcome"):
                checker.check(self.run_dir)

    def test_resealed_capability_command_still_requires_original_probe(self):
        with self.edits() as edit:
            edit(self.export / checker.SETUP / "managed-capability.json",
                 lambda value: value["argv"].__setitem__(3, "print('fake successful control')"))
            self.reseal_result(checker.SETUP, edit)
            self.reseal_export(edit)
            http, _ = checker.validators_for(self.export, self.expected, self.linux)
            with self.assertRaisesRegex(ValueError, "original setup command"):
                checker.verify_setup(self.export, self.linux, http)

    def test_runtime_native_provider_cannot_be_relabelled_as_shim(self):
        with self.edits() as edit:
            edit(self.export / checker.SETUP / "installed-runtime.stdout.bin",
                 lambda value: value["fcntl_native"].update(kind="python"))
            with self.assertRaisesRegex(ValueError, "extension binding"):
                checker.verify_runtime(self.export, self.linux)

    def test_missing_boundary_source_inventory_is_rejected(self):
        with self.edits() as edit:
            edit(self.export / checker.SETUP / "installed-runtime.stdout.bin",
                 lambda value: value.update(selected_sources=[]))
            with self.assertRaisesRegex(ValueError, "boundary source"):
                checker.verify_runtime(self.export, self.linux)

    def test_resealed_native_network_attempt_fails_effect_semantics(self):
        with self.edits() as edit:
            profile = self.export / checker.NATIVE / "passive-profile.json"
            edit(profile, lambda value: value.update(network_attempts=[{"event": "socket.connect"}]))
            edit(self.export / checker.NATIVE / "effect-check.json",
                 lambda value: value.update(profile_sha256=record(profile, self.export)["sha256"]))
            self.reseal_result(checker.NATIVE, edit)
            self.reseal_export(edit)
            with self.assertRaisesRegex(ValueError, "network record binding"):
                checker.check(self.run_dir)

    def test_nonzero_native_capture_rejected_after_resealing(self):
        with self.edits() as edit:
            edit(self.export / checker.NATIVE / "upstream-confirmation.json", lambda value: value.update(returncode=1))
            self.reseal_result(checker.NATIVE, edit)
            self.reseal_export(edit)
            with self.assertRaisesRegex(ValueError, "Capture did not"):
                checker.check(self.run_dir)

    def test_missing_capture_workspace_rejected_after_resealing(self):
        with self.edits() as edit:
            edit(self.export / checker.NATIVE / "upstream-confirmation.json", lambda value: value.pop("cwd"))
            self.reseal_result(checker.NATIVE, edit)
            self.reseal_export(edit)
            with self.assertRaisesRegex(ValueError, "captured command/workspace"):
                checker.check(self.run_dir)

    def test_overlapping_outer_stages_rejected(self):
        with self.edits() as edit:
            for suffix in (".json", ".started.json"):
                edit(self.run_dir / ("http-prepare" + suffix), lambda value: value.update(started_at_utc="2026-10-27T01:00:01+00:00"))
            with self.assertRaisesRegex(ValueError, "overlap"):
                checker.check(self.run_dir)

    def test_resealed_http_unrelated_effect_rejected(self):
        with self.edits() as edit:
            # Reseal both representations of the final database boundary.
            def corrupt(database):
                database["tables"]["services"][0]["status"] = "unauthorized-test-change"
            for name in ("after-resume", "after-get-completed"):
                edit(self.export / checker.HTTP / (name + ".snapshot.json"), lambda value: corrupt(value["database"]))
            def boundaries(value):
                for row in value[4:]:
                    corrupt(row["database"])
            edit(self.export / checker.HTTP / "boundaries.json", boundaries)
            self.reseal_result(checker.HTTP, edit)
            self.reseal_export(edit)
            with self.assertRaisesRegex(ValueError, "only one target"):
                checker.check(self.run_dir)


if __name__ == "__main__":
    unittest.main()
