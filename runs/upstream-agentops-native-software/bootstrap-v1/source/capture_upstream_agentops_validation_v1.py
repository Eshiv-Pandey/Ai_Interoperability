"""Capture frozen-copy stdlib validation without a native application launch.

Each allocation is exclusive. Selected tests run in isolated Python with only
captured src/scripts paths added explicitly. Permanent outputs are allocated
only by an explicit caller invocation; importing this driver starts nothing.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
APPLICATION = "runs/upstream-agentops-cases/v1/application/cases.json"
SUITES = {
    "client": (
        "src/interoperability/__init__.py", "src/interoperability/upstream_agentops_client_v1.py",
        "tests/test_upstream_agentops_client_v1.py", APPLICATION,
    ),
    "bootstrap": (
        "scripts/serve_upstream_agentops_cases_v1.py", "tests/test_serve_upstream_agentops_cases_v1.py",
    ),
    "owned-job": (
        "src/interoperability/__init__.py", "src/interoperability/windows_owned_job_v1.py", "tests/test_windows_owned_job_v1.py",
    ),
    "runner": (
        "src/interoperability/__init__.py", "src/interoperability/upstream_agentops_native_runner_v1.py",
        "scripts/run_upstream_agentops_cases_v1.py", "tests/test_upstream_agentops_native_runner_v1.py",
        "src/interoperability/upstream_agentops_client_v1.py", "src/interoperability/windows_owned_job_v1.py",
        "src/interoperability/windows_tcp_ownership_v1.py", "scripts/with_gemini_key.ps1",
        "scripts/serve_upstream_agentops_cases_v1.py", "scripts/agentops_asgi_capture_v1.py", "scripts/agentops_native_probe_v2.py",
        "src/interoperability/agentops_raw_events_v1.py", "src/interoperability/agentops_public_events_v1.py",
        "src/interoperability/agentops_event_binding_v1.py", APPLICATION,
    ),
}

# No site-packages or original project paths enter the test child's sys.path.
# runpy avoids discovery broadening beyond the explicitly captured test files.
TEST_PROGRAM = r'''
import json
from pathlib import Path
import runpy
import sys
import types
import unittest

root = Path(sys.argv[1]).resolve()
tests = json.loads(sys.argv[2])
execution_path = Path(sys.argv[3])
sys.path.insert(0, str(root / "scripts"))
sys.path.insert(0, str(root / "src"))
sys.argv = ["captured_upstream_agentops_validation"]
loader = unittest.TestLoader()
suite = unittest.TestSuite()
for index, relative in enumerate(tests):
    module_name = "captured_validation_test_" + str(index)
    values = runpy.run_path(str(root / relative), run_name=module_name)
    module = types.ModuleType(module_name)
    module.__dict__.update(values)
    sys.modules[module_name] = module
    suite.addTests(loader.loadTestsFromModule(module))
result = unittest.TextTestRunner(verbosity=2).run(suite)
record = {"tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
          "skips": len(result.skipped), "expected_failures": len(result.expectedFailures),
          "unexpected_successes": len(result.unexpectedSuccesses), "successful": result.wasSuccessful(),
          "isolated_python": sys.flags.isolated == 1, "site_disabled": sys.flags.no_site == 1,
          "bytecode_disabled": sys.dont_write_bytecode, "executed_test_files": tests}
with execution_path.open("x", encoding="utf-8") as stream:
    json.dump(record, stream, sort_keys=True, indent=2)
    stream.write("\n")
raise SystemExit(0 if result.wasSuccessful() else 1)
'''


def _need(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def regular(path, directory=False):
    path = Path(path).absolute()
    for part in (*reversed(path.parents), path):
        info = part.lstat()
        _need(not stat.S_ISLNK(info.st_mode)
              and not (getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)), "Links/reparse points are unsupported")
    _need(path.is_dir() if directory else path.is_file(), "Expected a regular path")
    return path


def write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    regular(path.parent, True)
    with path.open("xb") as stream:
        stream.write(raw)


def inventory(root):
    regular(root, True)
    files = {}
    for path in sorted(root.rglob("*")):
        regular(path, path.is_dir())
        if path.is_file() and "__pycache__" not in path.relative_to(root).parts:
            files[path.relative_to(root).as_posix()] = path.read_bytes()
    return files


def relative_path(value):
    _need(type(value) is str and value and ":" not in value and "\\" not in value
          and not PurePosixPath(value).is_absolute() and ".." not in PurePosixPath(value).parts
          and PurePosixPath(value).as_posix() == value and "__pycache__" not in PurePosixPath(value).parts,
          "Invalid selected relative source path")
    return value


def capture_validation(suite, output, *, timeout_seconds=120, runner_sources=None):
    """Execute selected frozen-copy tests into a new output and retain failures."""
    _need(suite in SUITES, "Unknown validation suite")
    _need(type(timeout_seconds) in (int, float) and 0 < timeout_seconds <= 120, "Timeout must be positive and at most 120 seconds")
    _need(runner_sources is None or suite == "runner", "Dependency overrides are only supported for the runner suite")
    selected = tuple(relative_path(value) for value in (runner_sources if runner_sources is not None else SUITES[suite]))
    _need(selected and len(set(selected)) == len(selected), "Empty or duplicate suite dependency membership")
    tests = [name for name in selected if name.startswith("tests/") and PurePosixPath(name).name.startswith("test_") and name.endswith(".py")]
    _need(tests, "Selected suite has no explicit test files")
    output = Path(output).absolute()
    _need(not output.exists() and not output.is_symlink(), "Refusing an existing validation allocation")
    _need(all(not (ROOT / name).absolute().resolve().is_relative_to(output.resolve()) for name in selected), "Output contains an original source input")
    output.mkdir(parents=True, exist_ok=False)
    regular(output, True)
    originals, copies, captures = {}, {}, {}
    driver_path = Path(__file__).absolute()
    driver_raw = regular(driver_path).read_bytes()
    workspace = output / "workspace"
    result = {"schema_version": "upstream-agentops-validation/1", "suite": suite, "status": "failed", "error": None,
              "application_processes_launched": 0, "direct_model_calls": 0, "sdk_imports_by_driver": 0,
              "original_archives_exported": 0, "graded_upstream_cases": 0, "native_qualification_established": False,
              "scope": "Focused captured software tests with temporary loopback/mocked/benign owned-process fixtures only"}
    stdout = stderr = b""
    execution = None
    started = time.perf_counter_ns()
    try:
        originals = {name: regular(ROOT / name).read_bytes() for name in selected}
        _need(sum(len(raw) for raw in originals.values()) <= 64 * 1024 * 1024, "Selected sources exceed capture limit")
        for name, raw in originals.items():
            target = workspace / name
            write(target, raw)
            copies[name] = raw
        captures["source/capture_upstream_agentops_validation_v1.py"] = driver_raw
        write(output / "source/capture_upstream_agentops_validation_v1.py", driver_raw)
        execution_path = output / "execution.json"
        command = [sys.executable, "-I", "-S", "-B", "-c", TEST_PROGRAM, str(workspace), json.dumps(tests), str(execution_path)]
        plan = {"schema_version": "upstream-agentops-validation-plan/1", "suite": suite,
                "started_at_utc": datetime.now(timezone.utc).isoformat(), "command": command, "cwd": str(workspace),
                "timeout_seconds": timeout_seconds, "source_files": {name: digest(raw) for name, raw in originals.items()},
                "driver_digest": digest(driver_raw), "test_files": tests, "source_membership": list(selected),
                "application_processes_launched": 0, "direct_model_calls": 0, "original_archives_exported": 0,
                "source_inputs_and_tests_are_software_evidence_only": True, "no_site_packages": True}
        captures["plan.json"] = encoded(plan)
        write(output / "plan.json", captures["plan.json"])
        try:
            process = subprocess.run(command, cwd=workspace, capture_output=True, timeout=timeout_seconds)
            stdout, stderr, exit_code = process.stdout, process.stderr, process.returncode
        except subprocess.TimeoutExpired as error:
            stdout, stderr, exit_code = error.stdout or b"", error.stderr or b"", None
            result["error"] = "Captured validation exceeded its declared timeout"
        result["exit_code"] = exit_code
        for name, raw in (("stdout.txt", stdout), ("stderr.txt", stderr)):
            captures[name] = raw
            write(output / name, raw)
        if execution_path.exists():
            captures["execution.json"] = regular(execution_path).read_bytes()
            execution = json.loads(captures["execution.json"])
        lines = stderr.decode("utf-8", errors="replace").splitlines()
        summary_counts = [int(match[1]) for line in lines if (match := re.fullmatch(r"Ran (\d+) tests? in .+", line))]
        summary_success = any(re.fullmatch(r"OK(?: \([^\r\n]*\))?", line) for line in lines)
        result.update(execution=execution, summary_test_counts=summary_counts, summary_success=summary_success,
                      stdout=digest(stdout), stderr=digest(stderr))
        if execution is not None:
            for key in ("tests_run", "failures", "errors", "skips", "expected_failures", "unexpected_successes"):
                _need(type(execution.get(key)) is int and execution[key] >= 0, "Invalid machine test count")
            _need(execution["executed_test_files"] == tests and execution["isolated_python"] is True
                  and execution["site_disabled"] is True and execution["bytecode_disabled"] is True, "Test isolation or membership differs from plan")
            result.update({key: execution[key] for key in ("tests_run", "failures", "errors", "skips", "expected_failures", "unexpected_successes")})
            result["status"] = ("passed" if exit_code == 0 and execution.get("successful") is True and execution["tests_run"] > 0
                                else "failed")
            if (summary_counts != [execution["tests_run"]] or not summary_success or execution["failures"]
                    or execution["errors"] or execution["skips"] or execution["expected_failures"] or execution["unexpected_successes"]):
                result["status"] = "failed"
        else:
            result["error"] = result["error"] or "Test process did not retain its machine result"
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as error:
        result.update(status="failed", error=f"{type(error).__name__}: {error}")
    finally:
        result["elapsed_ns"] = time.perf_counter_ns() - started
        try:
            result["original_sources_unchanged"] = bool(originals) and all(regular(ROOT / name).read_bytes() == raw for name, raw in originals.items())
            result["captured_sources_unchanged"] = bool(copies) and inventory(workspace) == copies
            result["driver_unchanged"] = regular(driver_path).read_bytes() == driver_raw
            result["captured_files_unchanged"] = inventory(output) == {**captures, **{"workspace/" + name: raw for name, raw in copies.items()}}
            _need(all(result[key] is True for key in ("original_sources_unchanged", "captured_sources_unchanged", "driver_unchanged", "captured_files_unchanged")),
                  "Original source, driver, captured bytes or allocation membership changed")
        except (OSError, ValueError, TypeError) as error:
            result.update(status="failed", preservation_error=f"{type(error).__name__}: {error}")
        result["source_files"] = {name: digest(raw) for name, raw in originals.items()}
        result["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        result["files"] = [{"path": name, **digest(raw)} for name, raw in sorted(inventory(output).items())]
        write(output / "result.json", encoded(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=tuple(SUITES), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=120)
    parser.add_argument("--runner-source", action="append", help="Explicit runner suite dependency; repeat for every selected file")
    args = parser.parse_args()
    result = capture_validation(args.suite, args.output, timeout_seconds=args.timeout_seconds, runner_sources=args.runner_source)
    print(json.dumps({"status": result["status"], "suite": args.suite, "tests_run": result.get("tests_run"),
                      "skips": result.get("skips"), "errors": result.get("errors"), "receipt": str(args.output.absolute() / "result.json")}, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
