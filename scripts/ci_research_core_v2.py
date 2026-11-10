"""Linux-owned timeout cleanup for the preserved core CI coordinator.

Version 1 remains unchanged. Normal benchmark/test/reconciliation methods are
reused; each command now owns a new POSIX session/group and its orphaned children
are adopted and reaped before verification or a retained manifest can be sealed.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager, redirect_stdout
import ctypes
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import unittest

# Isolated Python omits the script directory; resolve only this known source
# directory, and keep the CLI and test import bound to one ownership registry.
sys.path.insert(0, str(Path(__file__).resolve().parent))
if __name__ == "__main__":
    sys.modules["ci_research_core_v2"] = sys.modules[__name__]
import ci_research_core_v1 as core

_V1_CHECK = core.check_inputs
_V1_WRITE = core.write
_OPEN_GROUPS = set()
_TERM_SECONDS = 0.5
_KILL_SECONDS = 3.0
_POLL_SECONDS = 0.02
PR_SET_CHILD_SUBREAPER = 36
PR_GET_CHILD_SUBREAPER = 37


def require_linux():
    core.require(sys.platform == "linux", "Version 2 execution requires Linux owned-process-group support")


def _prctl(operation, value):
    require_linux()
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.restype = ctypes.c_int
    libc.prctl.argtypes = [ctypes.c_int, ctypes.c_void_p,
                          ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
    argument = ctypes.c_void_p(value) if isinstance(value, int) else ctypes.cast(value, ctypes.c_void_p)
    if libc.prctl(operation, argument, 0, 0, 0) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def subreaper_state():
    value = ctypes.c_int()
    _prctl(PR_GET_CHILD_SUBREAPER, ctypes.byref(value))
    return value.value


@contextmanager
def _adopt_orphans():
    previous = subreaper_state()
    _prctl(PR_SET_CHILD_SUBREAPER, 1)
    try:
        yield previous
    finally:
        # An unconfirmed group must prevent further work/sealing. Retain the
        # adoption capability until this invocation process exits in that case.
        if not _OPEN_GROUPS:
            _prctl(PR_SET_CHILD_SUBREAPER, previous)


def group_members(pgid):
    """Read stat identities only for the newly allocated owned process group."""
    members = []
    for folder in Path("/proc").iterdir():
        if not folder.name.isdecimal():
            continue
        try:
            raw = (folder / "stat").read_text()
        except (FileNotFoundError, ProcessLookupError):
            continue
        fields = raw[raw.rfind(")") + 1:].split()
        if len(fields) < 20:
            raise ValueError("Truncated Linux process stat")
        if int(fields[2]) == pgid:
            core.require(int(fields[3]) == pgid, "Group member is outside the owned session")
            members.append({"pid": int(folder.name), "state": fields[0],
                            "ppid": int(fields[1]), "pgid": int(fields[2]),
                            "session": int(fields[3]), "starttick": int(fields[19])})
    return sorted(members, key=lambda item: item["pid"])


def finish_group(process, *, timed_out):
    pgid = process.pid
    core.require(pgid > 1 and pgid != os.getpgrp(), "Require the actual distinct Popen-owned group")
    report = {"schema_version": "ci-research-core-owned-group/2", "pgid": pgid,
              "timed_out": timed_out, "snapshots": [], "signals": [],
              "adopted_children_reaped": [], "parent_reaped": False, "final_empty": False}

    def observe(phase):
        process.poll()  # Popen retains ownership of the direct child's status.
        before = group_members(pgid)
        for member in before:
            if member["pid"] == process.pid:
                continue
            try:
                child, status = os.waitpid(member["pid"], os.WNOHANG)
            except ChildProcessError:
                continue  # Still owned by its living coordinator, not adopted yet.
            if child:
                report["adopted_children_reaped"].append({"pid": child, "wait_status": status})
        after = group_members(pgid)
        report["snapshots"].append({"phase": phase, "monotonic_ns": time.monotonic_ns(), "members": after})
        report["parent_reaped"] = process.returncode is not None
        report["final_empty"] = not after and report["parent_reaped"]
        return after

    initial = observe("initial")
    report["initial_members"] = initial
    report["unexpected_members_after_normal_exit"] = bool(initial) and not timed_out

    def await_empty(seconds, phase):
        deadline = time.monotonic() + seconds
        while True:
            if not observe(phase):
                return
            left = deadline - time.monotonic()
            if left <= 0:
                return
            time.sleep(min(_POLL_SECONDS, left))

    for signum, seconds in ((signal.SIGTERM, _TERM_SECONDS), (signal.SIGKILL, _KILL_SECONDS)):
        if report["final_empty"]:
            break
        if not observe("before_" + signal.Signals(signum).name):
            break
        try:
            os.killpg(pgid, signum)
            report["signals"].append(signal.Signals(signum).name)
        except ProcessLookupError:
            pass
        await_empty(seconds, "after_" + signal.Signals(signum).name)
    observe("final")
    if report["final_empty"]:
        _OPEN_GROUPS.discard(pgid)
    return report


def invoke(output, label, argv, timeout):
    require_linux()
    core.require(not _OPEN_GROUPS, "An earlier owned group is unconfirmed; further commands are blocked")
    core.require(type(timeout) in (int, float) and math.isfinite(timeout) and timeout > 0,
                 "Timeout must be finite and positive")
    folder = output / "commands" / label
    folder.mkdir(parents=True, exist_ok=False)
    environment = {key: os.environ[key] for key in (
        "PATH", "SystemRoot", "WINDIR", "TEMP", "TMP", "TMPDIR", "COMSPEC", "PATHEXT") if key in os.environ}
    environment.update(PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1")
    receipt = {"label": label, "argv": argv, "cwd": str(output / "checkout"),
               "started_at": core.now(), "timeout_seconds": timeout, "returncode": None,
               "timed_out": False, "environment_keys": sorted(environment),
               "new_owned_session": True, "owned_group": None}
    source_paths = (Path(core.__file__).resolve(), Path(__file__).resolve())
    receipt["coordinator_source_before"] = [core.record(path, core.ROOT) for path in source_paths]
    started = time.perf_counter_ns()
    failure = None
    try:
        with (folder / "stdout.bin").open("xb") as stdout, (folder / "stderr.bin").open("xb") as stderr:
            with _adopt_orphans() as prior:
                receipt["previous_subreaper_state"] = prior
                process = None
                try:
                    process = subprocess.Popen(argv, cwd=output / "checkout", env=environment,
                        stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, start_new_session=True)
                    receipt["pid"] = process.pid
                    _OPEN_GROUPS.add(process.pid)
                    try:
                        process.wait(timeout=timeout)
                    except subprocess.TimeoutExpired:
                        receipt["timed_out"] = True
                except BaseException as error:
                    failure = error
                    receipt["error"] = type(error).__name__ + ": " + str(error)
                finally:
                    if process is not None:
                        try:
                            receipt["owned_group"] = finish_group(process, timed_out=receipt["timed_out"])
                        except BaseException as error:
                            receipt["cleanup_error"] = type(error).__name__ + ": " + str(error)
                            failure = error
                        receipt["returncode"] = process.returncode
                        if receipt["owned_group"] is not None:
                            if not receipt["owned_group"]["final_empty"]:
                                failure = RuntimeError("Owned group was not fully terminated/reaped; verification and sealing blocked")
                            elif receipt["owned_group"]["unexpected_members_after_normal_exit"]:
                                failure = RuntimeError("Coordinator exited with unexpected surviving group members")
    except BaseException as error:
        failure = error
        receipt["context_error"] = type(error).__name__ + ": " + str(error)
    try:
        receipt["coordinator_source_after"] = [core.record(path, core.ROOT) for path in source_paths]
        receipt["coordinator_source_unchanged"] = receipt["coordinator_source_before"] == receipt["coordinator_source_after"]
        if not receipt["coordinator_source_unchanged"]:
            failure = RuntimeError("Coordinator v1/v2 source changed during invocation")
    except (OSError, ValueError) as error:
        failure = error
        receipt["source_integrity_error"] = type(error).__name__ + ": " + str(error)
    receipt.update(finished_at=core.now(), coordinator_wall_ns=time.perf_counter_ns() - started,
                   stdout=core.record(folder / "stdout.bin", output), stderr=core.record(folder / "stderr.bin", output))
    _V1_WRITE(folder / "process.json", receipt)
    if failure is not None:
        raise failure
    return receipt


def check_inputs():
    result = _V1_CHECK()
    extra = ("scripts/ci_research_core_v2.py", "tests/test_ci_research_core_timeout_v2.py",
             "docs/research/ci-research-core-timeout-v2.md", ".github/workflows/research-core-timeout-check.yml")
    known = {item["path"] for item in result["original_inventory"]}
    result["original_inventory"] += [core.record(core.ROOT / name, core.ROOT) for name in extra if name not in known]
    result["timeout_ownership"] = "Linux new session/group; subreaper adoption and whole-group termination/reaping"
    return result


def guarded_write(path, value):
    if path.name == "retained-manifest.json":
        core.require(not _OPEN_GROUPS, "Cannot seal evidence while an owned process group is unconfirmed")
    return _V1_WRITE(path, value)


def execute(output):
    require_linux()  # Refuse Windows before allocating or launching anything.
    original = core.invoke, core.check_inputs, core.write
    core.invoke, core.check_inputs, core.write = invoke, check_inputs, guarded_write
    try:
        return core.execute(output)
    finally:
        core.invoke, core.check_inputs, core.write = original


def test_timeouts(output):
    require_linux()
    output = output.resolve()
    core.require(not output.exists(), "Timeout-test evidence allocation already exists")
    output.mkdir(parents=True)
    source_paths = (core.ROOT / "scripts/ci_research_core_v1.py", Path(__file__).resolve(),
                    core.ROOT / "tests/test_ci_research_core_timeout_v2.py",
                    core.ROOT / ".github/workflows/research-core-timeout-check.yml",
                    core.ROOT / "docs/research/ci-research-core-timeout-v2.md")
    before = [core.record(path, core.ROOT) for path in source_paths]
    captured = []
    for source, binding in zip(source_paths, before):
        target = output / "source" / binding["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        core.require(core.record(source, core.ROOT) == binding, "Timeout source changed before capture")
        with target.open("xb") as stream:
            stream.write(core.regular_bytes(source))
        captured.append(core.record(target, output))
    prior = os.environ.get("CI_TIMEOUT_TEST_OUTPUT")
    os.environ["CI_TIMEOUT_TEST_OUTPUT"] = str(output)
    sys.path.insert(0, str(core.ROOT / "tests"))
    try:
        suite = unittest.defaultTestLoader.loadTestsFromName("test_ci_research_core_timeout_v2")
        with (output / "tests.stdout.bin").open("x", encoding="utf-8") as stdout, (output / "tests.stderr.bin").open("x", encoding="utf-8") as stderr:
            with redirect_stdout(stdout):
                result = unittest.TextTestRunner(stream=stderr, verbosity=2).run(suite)
        after = [core.record(path, core.ROOT) for path in source_paths]
        captured_after = [core.record(output / item["path"], output) for item in captured]
        passed = (result.wasSuccessful() and result.testsRun >= 5 and not result.skipped
                  and before == after and captured == captured_after and not _OPEN_GROUPS)
        report = {"schema_version": "ci-research-core-timeout-tests/2", "status": "passed" if passed else "failed",
                  "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
                  "skips": len(result.skipped), "source_before": before, "source_after": after,
                  "source_unchanged": before == after, "python": list(sys.version_info[:3]),
                  "captured_source_before": captured, "captured_source_after": captured_after,
                  "captured_source_unchanged": captured == captured_after,
                  "github": {key: os.environ.get(key) for key in (
                      "GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "RUNNER_OS", "RUNNER_ARCH")},
                  "platform": sys.platform, "application_runs": 0, "model_calls": 0, "finished_at": core.now()}
        _V1_WRITE(output / "result.json", report)
        records = [core.record(path, output) for path in sorted(output.rglob("*")) if path.is_file()]
        guarded_write(output / "retained-manifest.json", {"files": records, "status": report["status"]})
        return report
    finally:
        if prior is None:
            os.environ.pop("CI_TIMEOUT_TEST_OUTPUT", None)
        else:
            os.environ["CI_TIMEOUT_TEST_OUTPUT"] = prior


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-inputs", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--test-timeouts", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.check_inputs:
        result = check_inputs()
        print(json.dumps({key: value for key, value in result.items() if key != "original_inventory"}, indent=2))
    else:
        if args.output is None:
            parser.error("Execution/test mode requires --output")
        result = test_timeouts(args.output) if args.test_timeouts else execute(args.output)
        print(json.dumps(result, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
