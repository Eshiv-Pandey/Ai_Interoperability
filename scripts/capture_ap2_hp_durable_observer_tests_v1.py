"""One isolated, source-pinned constructed durable-observer test capture.

This unconsumed driver must be reviewed before execution. No original AP2/SDK
source belongs to its test closure. Socket/process operations are denied in
the child; the parent may spawn only its exact isolated Python child once.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest


SOURCES = (
    "src/interoperability/ap2_hp_durable_observer_v1.py",
    "src/interoperability/ap2_hp_reference_execution_v1.py",
    "src/interoperability/ap2_hp_passive_capture_v1.py",
    "tests/test_ap2_hp_durable_observer_v1.py",
)
DRIVER = "scripts/capture_ap2_hp_durable_observer_tests_v1.py"
INPUTS = SOURCES + (DRIVER,)
FROZEN_SHA256 = {
    SOURCES[0]: "3ba610b079af528cca7301c8357de5cbd609dbf5cedd9460bdf843ce05e8f6bc",
    SOURCES[1]: "821b463c1e8d8500b32774b7c04ace2b865c7089c7a8e0ca1f5e7f20ab5df340",
    SOURCES[2]: "e3abb063246ee0688b098bba933a74c3c2e6c5789b7c9b39bc59cc12b135a5a8",
    SOURCES[3]: "411f9824dd51def860e027c5c285826dcbbf394396c0422a6e5c12f24a689941",
}
OUTPUT = "runs/ap2-hp-reference-software/durable-observer-v1"
RUN_NAME = "_constructed_ap2_durable_observer_tests"
EXPECTED_TEST_COUNT = 22
TIMEOUT_SECONDS = 120
DENIED_IMPORTS = {
    "common", "roles", "a2a", "ap2", "google", "httpx", "uvicorn",
    "starlette", "cryptography", "jwcrypto", "requests", "ctypes",
}


def now():
    return datetime.now(timezone.utc).isoformat()


def require(value, reason):
    if not value:
        raise ValueError(reason)


def regular(path, directory=False):
    path = Path(path)
    require(path.is_absolute(), "Absolute retained path required")
    for item in (path, *path.parents):
        info = item.lstat()
        require(not stat.S_ISLNK(info.st_mode)
                and not getattr(info, "st_file_attributes", 0) & 0x400,
                "Linked/reparse capture path refused")
    require(path.is_dir() if directory else path.is_file(), "Regular retained path required")
    return path.resolve()


def inside(path, root):
    return path == root or root in path.parents


def identity(path):
    path = regular(path)
    require(path.stat().st_size <= 2 * 1024 * 1024, "Bounded source/retained file required")
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def inventory(root):
    root = regular(root, True)
    result = {}
    for path in sorted(root.rglob("*")):
        regular(path, path.is_dir())
        if path.is_file():
            require(len(result) < 256, "Constructed capture file-count bound exceeded")
            result[path.relative_to(root).as_posix()] = identity(path)
    return result


def write(path, value):
    with path.open("xb") as stream:
        stream.write((json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())


def read_json(path):
    identity(path)
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate capture JSON key")
            result[key] = value
        return result
    def invalid(_):
        raise ValueError("Nonfinite capture JSON refused")
    return json.loads(path.read_bytes(), object_pairs_hook=pairs, parse_constant=invalid)


def verify_inputs(root, driver_sha256):
    require(len(driver_sha256) == 64 and all(item in "0123456789abcdef" for item in driver_sha256),
            "Reviewed external driver SHA256 required")
    root = regular(root, True)
    require(regular(Path(__file__)) == regular(root / DRIVER), "Driver and declared checkout differ")
    before = {name: identity(root / name) for name in INPUTS}
    require(all(before[name]["sha256"] == digest for name, digest in FROZEN_SHA256.items()),
            "Reviewed four-file constructed source closure differs")
    require(before[DRIVER]["sha256"] == driver_sha256, "Driver differs from external reviewed pin")
    tree = ast.parse((root / SOURCES[-1]).read_bytes())
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "DurableObserverChecks"]
    require(len(classes) == 1, "Exactly one declared constructed test class required")
    names = sorted(node.name for node in classes[0].body
                   if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"))
    require(len(names) == len(set(names)) == EXPECTED_TEST_COUNT, "Exactly 22 unique constructed methods required")
    require(not any(isinstance(node, ast.Import) and any(alias.name == "asyncio" for alias in node.names)
                    for node in ast.walk(tree)), "The reviewed suite must not create an asyncio event loop")
    return before, names


class AuditPolicy:
    """Bounded denial receipts without recording arguments or secret values."""
    def __init__(self, *, output=None, allowed_spawn=None):
        self.output = output
        self.standard_root = Path(sys.base_prefix).resolve()
        self.allowed_spawn = allowed_spawn
        self.spawn_used = False
        self.child_pid = None
        self.events_seen = 0
        self.denied = []
        self.denied_count = 0

    def refuse(self, event, reason):
        self.denied_count += 1
        if len(self.denied) < 64:
            self.denied.append({"event": event, "reason": reason})
        raise PermissionError("Constructed capture policy: " + reason)

    def __call__(self, event, args):
        self.events_seen += 1
        if event.startswith("socket.") or event.startswith("ctypes."):
            self.refuse(event, "socket/native foreign-call operations denied")
        if event == "import" and args[0].split(".", 1)[0] in DENIED_IMPORTS:
            self.refuse(event, "original/SDK/provider/foreign-call imports denied")
        if event == "subprocess.Popen":
            expected = self.allowed_spawn
            if expected is not None and not self.spawn_used and len(args) == 4:
                executable, command, cwd, environment = args
                expected_command = subprocess.list2cmdline(expected[0]) if os.name == "nt" else expected[0]
                if executable == expected[0][0] and command == expected_command and cwd == expected[1] and environment == expected[2]:
                    self.spawn_used = True
                    return
            self.refuse(event, "only the exact once-only isolated Python child is permitted")
        if event == "os.kill" and self.allowed_spawn is not None and type(args[0]) is int and args[0] == self.child_pid:
            return
        if event.startswith(("os.exec", "os.spawn", "os.fork", "os.posix_spawn", "os.startfile")) or event in (
            "os.system", "os.kill", "os.killpg", "pty.spawn", "_thread.start_new_thread",
        ):
            self.refuse(event, "unowned process/thread operations denied")
        if self.output is not None and event == "open" and not isinstance(args[0], int):
            path = Path(args[0]).absolute().resolve()
            flags = args[2]
            writing = type(flags) is int and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            if not inside(path, self.output) and not (inside(path, self.standard_root) and not writing):
                self.refuse(event, "file content outside captured artifacts and read-only standard library denied")

    def report(self):
        return {"events_seen": self.events_seen, "denied_count": self.denied_count,
                "denied_events": list(self.denied), "socket_operations_permitted": False,
                "original_sdk_provider_imports_permitted": False,
                "isolated_child_spawn_permitted": self.allowed_spawn is not None,
                "isolated_child_spawn_used": self.spawn_used,
                "receipt_limit": "Python audit denial receipts for reviewed constructed code; not runtime authentication"}


class RetainedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outcomes = []

    def record(self, test, status, error=None):
        row = {"id": test.id(), "status": status, "finished_at_utc": now()}
        if error is not None:
            row["error_type"] = error[0].__name__
        self.outcomes.append(row)

    def addSuccess(self, test):
        super().addSuccess(test)
        self.record(test, "passed")

    def addFailure(self, test, error):
        super().addFailure(test, error)
        self.record(test, "failed", error)

    def addError(self, test, error):
        super().addError(test, error)
        self.record(test, "error", error)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.record(test, "skipped")

    def addExpectedFailure(self, test, error):
        super().addExpectedFailure(test, error)
        self.record(test, "expected_failure", error)

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.record(test, "unexpected_success")


def run_tests(root, output, driver_sha256):
    root, output = regular(root, True), regular(output, True)
    require(root.name == "captured-checkout" and root.parent == output, "Bound captured child checkout required")
    before, names = verify_inputs(root, driver_sha256)
    plan = read_json(output / "capture-plan.json")
    require(plan["captured_inputs"] == before and plan["expected_test_count"] == EXPECTED_TEST_COUNT
            and plan["declared_test_names"] == names, "Child source and parent plan differ")
    require(not (output / "test-outcomes.json").exists(), "Consumed constructed outcomes refused")
    temporary_root = regular(output / "constructed-temporary", True)
    tempfile.tempdir = str(temporary_root)
    policy = AuditPolicy(output=output)
    sys.addaudithook(policy)
    namespace = runpy.run_path(str(root / SOURCES[-1]), run_name=RUN_NAME)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(namespace["DurableObserverChecks"])
    require(suite.countTestCases() == EXPECTED_TEST_COUNT, "Loaded test membership differs")
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=2, resultclass=RetainedResult).run(suite)
    write(output / "test-outcomes.json", {
        "tests_run": result.testsRun, "outcomes": result.outcomes, "successful": result.wasSuccessful(),
        "failure_count": len(result.failures), "error_count": len(result.errors), "skipped_count": len(result.skipped),
        "expected_failure_count": len(result.expectedFailures), "unexpected_success_count": len(result.unexpectedSuccesses),
        "policy": policy.report(), "event_loop_created_by_suite": False,
        "fixture_execution": "finite direct coroutine drives; explicit synthetic suspension/resumption; no event loop",
    })
    return 0 if result.wasSuccessful() else 1


def capture(root, output, driver_sha256):
    root = regular(root, True)
    require(output.is_absolute() and output == root / OUTPUT, "Only the dedicated durable-observer-v1 output is permitted")
    require(not output.exists(), "Consumed constructed output refused before allocation")
    regular(output.parent, True)
    before, names = verify_inputs(root, driver_sha256)
    require(sys.version_info[:3] == (3, 13, 1), "Reviewed Python 3.13.1 interpreter profile required")
    interpreter = {"path": str(regular(Path(sys.executable))), **identity(Path(sys.executable))}
    output.mkdir()
    checkout = output / "captured-checkout"
    checkout.mkdir()
    for name in INPUTS:
        destination = checkout / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, destination)
    copied = inventory(checkout)
    require(copied == before, "Copied five files differ from reviewed source/driver identities")
    temporary_root = output / "constructed-temporary"
    temporary_root.mkdir()
    command = [sys.executable, "-I", "-S", "-B", str(checkout / DRIVER), "--phase", "tests",
               "--root", str(checkout), "--output", str(output), "--expected-driver-sha256", driver_sha256]
    child_environment = {key: os.environ[key] for key in ("SystemRoot", "WINDIR") if key in os.environ}
    child_environment.update({"TEMP": str(temporary_root), "TMP": str(temporary_root)})
    write(output / "capture-plan.json", {
        "schema_version": "ap2-hp-durable-observer-software-plan/1", "created_at_utc": now(),
        "command": command, "inputs_before": before, "captured_inputs": copied,
        "source_closure_count": len(SOURCES), "driver_copy_count": 1, "copied_inputs_match": True,
        "declared_test_names": names, "expected_test_count": EXPECTED_TEST_COUNT,
        "expected_test_ids": [RUN_NAME + ".DurableObserverChecks." + name for name in names],
        "interpreter": interpreter, "external_reviewed_driver_sha256": driver_sha256,
        "timeout_seconds": TIMEOUT_SECONDS, "child_environment_keys": sorted(child_environment),
        "scope": "One constructed suite and exactly four authored module/test files plus its reviewed driver; no original/SDK source or prior suite",
        "event_loop_required": False, "socket_operations_permitted": False,
    })
    policy = AuditPolicy(allowed_spawn=(command, str(checkout), child_environment))
    sys.addaudithook(policy)
    started, returncode, timed_out, child_pid, cleanup_error, execution_error = now(), None, False, None, None, None
    with (output / "tests.stdout.bin").open("xb") as stdout, (output / "tests.stderr.bin").open("xb") as stderr:
        child = None
        try:
            child = subprocess.Popen(command, executable=sys.executable, cwd=str(checkout), env=child_environment,
                                     stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, shell=False)
            child_pid = policy.child_pid = child.pid
            try:
                returncode = child.wait(timeout=TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                timed_out = True
                child.kill()
                try:
                    returncode = child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    cleanup_error = "owned_child_did_not_settle_after_kill"
        except BaseException as error:
            execution_error = type(error).__name__
            if child is not None and child.poll() is None:
                try:
                    child.kill()
                    returncode = child.wait(timeout=10)
                except BaseException as cleanup:
                    cleanup_error = type(cleanup).__name__
        stdout.flush()
        stderr.flush()
        os.fsync(stdout.fileno())
        os.fsync(stderr.fileno())
    outcomes_path = output / "test-outcomes.json"
    outcomes = read_json(outcomes_path) if outcomes_path.is_file() else {}
    expected_ids = [RUN_NAME + ".DurableObserverChecks." + name for name in names]
    rows = outcomes.get("outcomes", [])
    matched = (outcomes.get("tests_run") == EXPECTED_TEST_COUNT and len(rows) == EXPECTED_TEST_COUNT
               and sorted(item["id"] for item in rows) == expected_ids
               and all(item["status"] == "passed" for item in rows)
               and all(outcomes.get(key) == 0 for key in ("failure_count", "error_count", "skipped_count",
                                                         "expected_failure_count", "unexpected_success_count")))
    after = {name: identity(root / name) for name in INPUTS}
    unchanged = before == after and copied == inventory(checkout)
    interpreter_unchanged = interpreter == {"path": str(regular(Path(sys.executable))), **identity(Path(sys.executable))}
    child_policy = outcomes.get("policy", {})
    policy_complete = (policy.spawn_used and policy.denied_count == 0 and child_policy.get("denied_count") == 0
                       and child_policy.get("socket_operations_permitted") is False
                       and child_policy.get("isolated_child_spawn_permitted") is False)
    passed = returncode == 0 and matched and unchanged and interpreter_unchanged and policy_complete and not timed_out and cleanup_error is None and execution_error is None
    result = {
        "schema_version": "ap2-hp-durable-observer-software-capture/1",
        "status": "passed_constructed_software_tests_only" if passed else "failed_or_incomplete_constructed_capture",
        "started_at_utc": started, "finished_at_utc": now(), "returncode": returncode,
        "timed_out": timed_out, "isolated_child_pid": child_pid, "cleanup_error": cleanup_error,
        "execution_error": execution_error,
        "tests_run": outcomes.get("tests_run"), "declared_test_membership_verified": matched,
        "source_and_driver_inputs_unchanged": unchanged, "inputs_after": after,
        "interpreter_unchanged": interpreter_unchanged, "source_closure_count": len(SOURCES),
        "captured_file_count": len(copied), "parent_policy": policy.report(), "child_policy": child_policy,
        "policy_complete": policy_complete, "retained_files_before_result": inventory(output),
        "original_source_imported": False, "native_application_executed": False,
        "credential_opened": False, "model_requests": 0, "native_qualification_established": False,
        "claim_limit": "Constructed durable-record/serialization/fail-open/terminal and denial-software checks only; no original SDK/runtime compatibility, transport ownership, provider entitlement or research gate credit",
    }
    write(output / "result.json", result)
    print(json.dumps({"status": result["status"], "tests_run": result["tests_run"], "inputs_unchanged": unchanged}))
    return 0 if passed else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("capture", "tests"), default="capture")
    parser.add_argument("--root", type=Path, default=Path(__file__).absolute().parents[1])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--expected-driver-sha256", required=True)
    args = parser.parse_args(argv)
    output = args.output if args.output is not None else args.root / OUTPUT
    if args.phase == "tests":
        return run_tests(args.root, output, args.expected_driver_sha256)
    return capture(args.root, output, args.expected_driver_sha256)


if __name__ == "__main__":
    raise SystemExit(main())
