"""Prepare/capture one unchanged upstream offline AgentOps control.

Standard-library coordinator only. The explicit ``run`` command starts pytest;
``prepare`` reads source/seed and writes a prospective plan without app imports.
This is in-process eligibility, never a real HTTP or bridge result.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tomllib

WORKSPACE = Path(__file__).resolve().parents[1]
SOURCE = WORKSPACE / "external/agentops-c806b7f1"
PROJECT = SOURCE / "agents/python"
INGESTION = WORKSPACE / "docs/research/source-evidence/agentops-local-archive-v1/ingestion.json"
SPEC = WORKSPACE / "docs/research/source-evidence/agentops-native-probe-v2/protocol.md"
PLUGIN = WORKSPACE / "scripts/agentops_native_probe_v2_plugin.py"
CHECKER = WORKSPACE / "scripts/check_agentops_effect_v2.py"
TEST_NAME = "test_a2a_confirmation_response_resumes_the_guarded_action_with_audit_identity"
NODEID = f"tests/test_server.py::{TEST_NAME}"
TABLE_KEYS = {"services": "name", "incidents": "id", "audit_log": "id", "sqlite_sequence": "name"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def within(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()) or resolved == root.resolve():
        raise ValueError(f"Path is outside the required subtree: {path}")
    return resolved


def digest(path: Path) -> dict:
    raw = path.read_bytes()
    return {"path": path.relative_to(WORKSPACE).as_posix(), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def source_inventory() -> list[dict]:
    ingestion = load_json(INGESTION)
    expected = [row["extracted"] for row in ingestion["records"] if row["kind"] == "regular_file"]
    actual = []
    expected_paths = {(WORKSPACE / row["path"]).absolute() for row in expected}
    expected_directories = {parent for path in expected_paths for parent in path.parents
                            if parent.is_relative_to(SOURCE)}
    for candidate in SOURCE.rglob("*"):
        if candidate.is_symlink():
            raise ValueError(f"Unexpected source-tree symlink: {candidate}")
        if candidate.is_file() and candidate not in expected_paths:
            raise ValueError(f"Unexpected new file in preserved source tree: {candidate}")
        if candidate.is_dir() and candidate not in expected_directories:
            raise ValueError(f"Unexpected new directory in preserved source tree: {candidate}")
    for row in expected:
        path = within(WORKSPACE / row["path"], SOURCE)
        receipt = digest(path)
        if receipt != row:
            raise ValueError(f"Original archive source mismatch: {row['path']}")
        actual.append(receipt)
    if len(actual) != 421:
        raise ValueError("Expected the recorded 421 exact original regular files")
    return sorted(actual, key=lambda row: row["path"])


def database_snapshot(path: Path, base: Path, path_base: str) -> dict:
    """Read one consistent transaction; never prepare, copy or migrate state."""
    path = within(path, base)
    if not path.is_file():
        raise ValueError(f"Expected an existing database: {path}")
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        schema = [dict(row) for row in connection.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY type,name")]
        tables = sorted(row["name"] for row in schema if row["type"] == "table")
        if set(tables) != set(TABLE_KEYS):
            raise ValueError(f"Unexpected domain database tables: {tables}")
        result = {
            "path": path.relative_to(base.resolve()).as_posix(), "path_base": path_base,
            "user_tables": [name for name in tables if not name.startswith("sqlite_")],
            "schema": schema,
            "user_version": connection.execute("PRAGMA user_version").fetchone()[0],
            "tables": {}, "columns": {},
        }
        for table, key in TABLE_KEYS.items():
            # Both identifiers come only from the constant whitelist above.
            result["tables"][table] = [dict(row) for row in connection.execute(
                f'SELECT * FROM "{table}" ORDER BY "{key}"')]
            result["columns"][table] = [dict(row) for row in connection.execute(
                f'PRAGMA table_info("{table}")')]
        return result
    finally:
        connection.rollback()
        connection.close()


def harness_inventory() -> list[dict]:
    return [digest(Path(__file__).resolve()), digest(PLUGIN), digest(SPEC), digest(CHECKER)]


def prepare(output: Path) -> None:
    output = within(output, WORKSPACE / "runs/agentops-native-eligibility")
    if output.exists():
        raise FileExistsError("A preparation/attempt already exists; use a newly versioned path")
    sources = source_inventory()
    harness = harness_inventory()
    seed = database_snapshot(SOURCE / "agents/data/incidents.db", WORKSPACE, "workspace")
    lock = tomllib.loads((PROJECT / "uv.lock").read_text(encoding="utf-8"))
    critical = {"agentops-agent", "google-adk", "a2a-sdk", "pytest", "starlette", "httpx",
                "anyio", "pydantic", "pydantic-settings", "sqlalchemy", "aiosqlite"}
    locked = {row["name"]: row["version"] for row in lock["package"] if row["name"] in critical}
    if set(locked) != critical:
        raise ValueError("Critical package pin missing or renamed in the exact lock")
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "seed-before.json", seed)
    write_json(output / "plan.json", {
        "schema_version": "agentops-native-probe-plan/2", "prepared_at_utc": now(),
        "status": "prepared_not_executed", "scope": "Single unchanged upstream in-process offline test",
        "source_files": sources, "harness_files": harness, "source_ingestion": digest(INGESTION),
        "seed_snapshot": digest(output / "seed-before.json"), "nodeid": NODEID,
        "critical_locked_versions": locked,
        "expected_python": "3.13", "timeout_seconds": 300,
        "observations": ["approval-start:helper_call", "approval-start:helper_return",
                         "approval-resume:helper_call", "approval-resume:helper_return"],
        "observer_changes": "Passive main-thread profile; read-only SQLite snapshots; no function replacements",
        "source_changes": False, "live_model_calls": 0, "application_requests_performed": 0,
        "real_http_wire_covered": False, "bridge_eligibility_covered": False,
        "human_review_completed": False, "qualified_second_domain": False,
    })
    print(json.dumps({"prepared": str(output / "plan.json"), "source_files": len(sources),
                      "application_requests_performed": 0}))


def clean_environment(output: Path) -> dict[str, str]:
    removed_prefixes = ("AGENT_", "GOOGLE_", "MLFLOW_", "OPENAI_", "OTEL_", "PYTEST_", "PYTHON")
    environment = {name: value for name, value in os.environ.items()
                   if not name.upper().startswith(removed_prefixes)}
    environment.update({
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1", "PYTHONNOUSERSITE": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTHONPATH": str(WORKSPACE / "scripts"),
        "AGENTOPS_PROBE_OUTPUT": str(output),
        "OTEL_SDK_DISABLED": "true", "TEMP": str(output / "temp"),
        "TMP": str(output / "temp"), "TMPDIR": str(output / "temp"),
    })
    return environment


def capture(argv: list[str], *, output: Path, label: str, cwd: Path,
            environment: dict[str, str], timeout: int) -> dict:
    started = now()
    with (output / f"{label}.stdout.bin").open("xb") as stdout, (output / f"{label}.stderr.bin").open("xb") as stderr:
        process = subprocess.Popen(argv, cwd=cwd, env=environment, stdout=stdout, stderr=stderr,
                                   stdin=subprocess.DEVNULL, shell=False)
        timed_out = False
        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            returncode = process.wait(timeout=30)
    receipt = {"argv": argv, "cwd": str(cwd), "pid": process.pid,
               "started_at_utc": started, "finished_at_utc": now(), "returncode": returncode,
               "timed_out": timed_out, "stdout": digest(output / f"{label}.stdout.bin"),
               "stderr": digest(output / f"{label}.stderr.bin")}
    write_json(output / f"{label}.json", receipt)
    return receipt


def run(output: Path, runtime_python: Path, dependencies: Path) -> None:
    output = within(output, WORKSPACE / "runs/agentops-native-eligibility")
    plan = load_json(output / "plan.json")
    if plan["source_files"] != source_inventory() or plan["harness_files"] != harness_inventory():
        raise ValueError("Frozen source/harness differs; prepare a separately reviewed new version")
    if plan["seed_snapshot"] != digest(output / "seed-before.json"):
        raise ValueError("Prepared seed snapshot changed")
    # These prerequisites are evaluated before reserving a once-only attempt.
    runtime_python = within(runtime_python, WORKSPACE / "external/runtime-agentops-v2")
    if not runtime_python.is_file():
        raise FileNotFoundError("Pinned runtime interpreter is not installed")
    dependencies = within(dependencies, WORKSPACE / "runs/agentops-native-eligibility/dependencies-v2")
    setup = load_json(dependencies)
    if setup.get("status") != "dependencies_ready" or setup.get("source_lock_unchanged") is not True:
        raise ValueError("Successful unchanged-lock dependency receipt is required")
    if (output / "execution.json").exists():
        raise FileExistsError("This attempt already started; retain it and do not rerun")
    execution = {"schema_version": "agentops-native-probe-execution/2", "started_at_utc": now(),
                 "plan": digest(output / "plan.json"), "dependency_result": digest(dependencies),
                 "runtime_python": str(runtime_python), "source_unchanged_before": True}
    write_json(output / "execution.json", execution)
    (output / "temp").mkdir(exist_ok=False)
    environment = clean_environment(output)
    result = {"schema_version": "agentops-native-probe-result/2", "status": "failed",
              "application_test_started": False, "application_requests_performed": None,
              "live_model_calls": 0, "real_http_wire_covered": False,
              "qualified_second_domain": False, "independent_check": "required_separately"}
    try:
        code = ("import importlib.metadata as m,json,sys; "
                "print(json.dumps({'python':list(sys.version_info[:3]),"
                "'executable':sys.executable,'packages':sorted(["
                "{'name':d.metadata['Name'],'version':d.version,'location':str(d.locate_file(''))} "
                "for d in m.distributions()],key=lambda r:r['name'].lower())}))")
        metadata = capture([str(runtime_python), "-I", "-c", code], output=output, label="runtime-metadata",
                           cwd=output, environment=environment, timeout=30)
        if metadata["returncode"] != 0:
            raise RuntimeError("Runtime metadata command failed")
        inventory = json.loads((output / "runtime-metadata.stdout.bin").read_bytes())
        if inventory["python"][:2] != [3, 13]:
            raise ValueError("Installed runtime is not Python 3.13")
        versions = {}
        runtime_root = runtime_python.parents[1]
        for row in inventory["packages"]:
            name = row["name"].lower().replace("_", "-").replace(".", "-")
            if name in versions:
                raise ValueError(f"Duplicate installed distribution: {name}")
            versions[name] = row["version"]
            if not Path(row["location"]).resolve().is_relative_to(runtime_root):
                raise ValueError(f"Distribution resolves outside isolated runtime: {name}")
        for name, expected in plan["critical_locked_versions"].items():
            if versions.get(name) != expected:
                raise ValueError(f"Critical installed version does not match lock: {name}")
        lock = tomllib.loads((PROJECT / "uv.lock").read_text(encoding="utf-8"))
        allowed = {(row["name"], row["version"]) for row in lock["package"]}
        unexpected = sorted((name, version) for name, version in versions.items()
                            if (name, version) not in allowed)
        if unexpected:
            raise ValueError(f"Installed packages absent from exact source lock: {unexpected}")
        argv = [str(runtime_python), "-B", "-m", "pytest", "-c", str(PROJECT / "pyproject.toml"),
                "-p", "agentops_native_probe_v2_plugin", "--basetemp", str(output / "pytest-temp"),
                "-o", f"cache_dir={output / 'pytest-cache'}", "--junitxml", str(output / "junit.xml"),
                NODEID]
        result["application_test_started"] = True
        test = capture(argv, output=output, label="upstream-confirmation", cwd=PROJECT,
                       environment=environment, timeout=plan["timeout_seconds"])
        result["pytest_returncode"] = test["returncode"]
        if test["returncode"] != 0:
            raise RuntimeError("Unchanged upstream test did not pass; retain the original failure")
        observation = load_json(output / "passive-profile.json")
        reports = load_json(output / "pytest-reports.json")
        if observation["errors"] or observation["network_attempts"] or len(observation["observations"]) != 4:
            raise RuntimeError("Passive evidence is incomplete; independent checking cannot proceed")
        if reports["exitstatus"] != 0 or len(reports["reports"]) != 3 or any(
                row["outcome"] != "passed" for row in reports["reports"]):
            raise RuntimeError("Setup/call/teardown evidence does not show exactly one passing test")
        result["status"] = "upstream_test_passed_independent_check_pending"
        result["application_requests_performed"] = 2
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
    finally:
        try:
            result["source_unchanged_after"] = source_inventory() == plan["source_files"]
        except Exception as error:
            result["source_unchanged_after"] = False
            result["source_error"] = f"{type(error).__name__}: {error}"
        if not result["source_unchanged_after"]:
            result["status"] = "failed_source_integrity"
        result["finished_at_utc"] = now()
        result["files"] = [digest(path) for path in sorted(output.iterdir()) if path.is_file()]
        write_json(output / "result.json", result)
    print(json.dumps(result, indent=2))
    if result["status"] != "upstream_test_passed_independent_check_pending":
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    preparation = subparsers.add_parser("prepare", help="Source/seed reads only; no application imports")
    preparation.add_argument("--output", type=Path, required=True)
    execution = subparsers.add_parser("run", help="Run reviewed prepared control once after dependency setup")
    execution.add_argument("--output", type=Path, required=True)
    execution.add_argument("--runtime-python", type=Path,
                           default=WORKSPACE / "external/runtime-agentops-v2/venv/Scripts/python.exe")
    execution.add_argument("--dependency-result", type=Path,
                           default=WORKSPACE / "runs/agentops-native-eligibility/dependencies-v2/result.json")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.output)
    else:
        run(args.output, args.runtime_python, args.dependency_result)


if __name__ == "__main__":
    main()
