"""Run the original offline control in a separately installed Linux runtime.

The failed Windows v3 attempt remains untouched. Linux platform and native fcntl
checks precede preparation or execution; upstream source and observer are unchanged.
"""
from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path
import sys

import agentops_native_probe_v2 as original


ROOT = original.WORKSPACE
RUNS = ROOT / "runs/agentops-native-eligibility"
RUNTIME = ROOT / "external/runtime-agentops-linux-v4/venv/bin/python"
INSPECTOR = ROOT / "scripts/inspect_agentops_runtime_v4.py"
PROTOCOL = ROOT / "docs/research/source-evidence/agentops-native-probe-v4/protocol.md"
LAUNCHER = ROOT / "scripts/run_agentops_linux_v4.py"


def harness() -> list[dict]:
    paths = [Path(__file__), Path(original.__file__), original.PLUGIN,
             original.CHECKER, original.SPEC, INSPECTOR, PROTOCOL, LAUNCHER]
    return [original.digest(path.resolve()) for path in paths]


def runtime_inspection(output: Path, label: str, environment: dict) -> dict:
    receipt = original.capture([str(RUNTIME), "-I", str(INSPECTOR)], output=output,
                               label=label, cwd=ROOT, environment=environment, timeout=60)
    if receipt["returncode"] != 0:
        raise ValueError(f"Installed runtime inspection failed; see {label} streams")
    return json.loads((output / f"{label}.stdout.bin").read_bytes())


def require_linux() -> None:
    if sys.platform != "linux" or platform.machine() != "x86_64":
        raise ValueError("This control requires Linux x86_64; Windows fcntl shims are not permitted")


def validate_setup() -> dict:
    directory = RUNS / "dependencies-linux-v4"
    result = original.load_json(directory / "result.json")
    if result.get("status") != "dependencies_ready" or result.get("source_unchanged_after") is not True:
        raise ValueError("Successful Linux dependency setup is required")
    if result["source_files"] != original.source_inventory():
        raise ValueError("Linux setup source differs from current original source")
    for row in result["files"]:
        path = original.within(ROOT / row["path"], directory)
        if original.digest(path) != row:
            raise ValueError("Retained Linux setup evidence changed")
    return original.digest(directory / "result.json")


def validate_pytest_reports(reports: dict) -> None:
    rows = reports["reports"]
    if (reports["exitstatus"] != 0 or len(rows) != 3
            or {row["when"] for row in rows} != {"setup", "call", "teardown"}
            or any(row["outcome"] != "passed" or row["nodeid"] != original.NODEID for row in rows)):
        raise ValueError("Exactly one passed setup/call/teardown is required")


def prepare(output: Path) -> None:
    require_linux()
    output = original.within(output, RUNS)
    if output.exists():
        raise FileExistsError("Preparation already exists; preserve it")
    setup = validate_setup()
    source = original.source_inventory()
    files = harness()
    output.mkdir(parents=True, exist_ok=False)
    (output / "temp").mkdir()
    environment = original.clean_environment(output)
    state = {"schema_version": "agentops-native-preparation/4", "status": "failed",
             "application_requests": 0, "model_calls": 0}
    try:
        inventory = runtime_inspection(output, "prepared-runtime", environment)
        seed = original.database_snapshot(original.SOURCE / "agents/data/incidents.db", ROOT, "workspace")
        original.write_json(output / "seed-before.json", seed)
        # Exercise the unchanged pytest directory mode without importing pytest
        # or collecting application tests. Retain failures and their directory.
        code = ("from pathlib import Path; import sys; "
                "p=Path(sys.argv[1]); p.mkdir(mode=0o700); "
                "(p/'probe.txt').write_text('directory capability probe',encoding='utf-8'); "
                "assert (p/'probe.txt').read_text(encoding='utf-8')=='directory capability probe'; "
                "print('mode0700 write/read passed')")
        permission = original.capture([str(RUNTIME), "-I", "-c", code,
                                       str(output / "mode0700-preparation")], output=output,
                                      label="directory-capability", cwd=output,
                                      environment=environment, timeout=30)
        plan = {
            "schema_version": "agentops-native-plan/4", "prepared_at_utc": original.now(),
            "nodeid": original.NODEID, "source_files": source, "harness_files": files,
            "runtime_python": str(RUNTIME),
            "runtime_inventory": original.digest(output / "prepared-runtime.stdout.bin"),
            "runtime_package_count": len(inventory["packages"]),
            "dependency_setup": setup,
            "seed_snapshot": original.digest(output / "seed-before.json"),
            "timeout_seconds": 300,
            "directory_capability_in_preparation": permission["returncode"] == 0,
            "installation_history": "Separate Linux v4 setup; inspect its retained dependency receipts",
            "scope": "One unchanged upstream in-process confirmation test with passive v2 observer",
            "real_http_wire_covered": False, "qualified_second_domain": False,
        }
        original.write_json(output / "plan.json", plan)
        state["status"] = "prepared"
        state["directory_capability_passed"] = permission["returncode"] == 0
        if permission["returncode"] != 0:
            raise ValueError("Linux directory capability failed; execution is not permitted")
        state["runtime_package_count"] = len(inventory["packages"])
    except Exception as error:
        state["status"] = "failed"
        state["error"] = f"{type(error).__name__}: {error}"
    state["finished_at_utc"] = original.now()
    original.write_json(output / "preparation-result.json", state)
    print(json.dumps(state, indent=2))
    if state["status"] != "prepared":
        raise SystemExit(1)


def run(output: Path) -> None:
    require_linux()
    output = original.within(output, RUNS)
    plan = original.load_json(output / "plan.json")
    if plan["dependency_setup"] != validate_setup():
        raise ValueError("Linux setup changed since preparation")
    if plan.get("directory_capability_in_preparation") is not True:
        raise ValueError("Linux directory capability did not pass")
    if original.load_json(output / "preparation-result.json").get("status") != "prepared":
        raise ValueError("Linux preparation did not finish successfully")
    if plan["source_files"] != original.source_inventory() or plan["harness_files"] != harness():
        raise ValueError("Prepared source/harness changed; do not execute this plan")
    for field in ("runtime_inventory", "seed_snapshot"):
        if original.digest(ROOT / plan[field]["path"]) != plan[field]:
            raise ValueError(f"Prepared {field} changed")
    if (output / "execution.json").exists():
        raise FileExistsError("Attempt already reserved; never rerun it")
    original.write_json(output / "execution.json", {
        "schema_version": "agentops-native-execution/4", "started_at_utc": original.now(),
        "plan": original.digest(output / "plan.json"), "runtime_python": str(RUNTIME),
    })
    result = {"schema_version": "agentops-native-result/4", "status": "failed",
              "pytest_started": False, "application_test_started": False, "application_requests_performed": None,
              "live_model_calls": 0, "real_http_wire_covered": False,
              "qualified_second_domain": False, "independent_check": "not_run"}
    try:
        environment = original.clean_environment(output)
        current = runtime_inspection(output, "execution-runtime", environment)
        prepared = json.loads((ROOT / plan["runtime_inventory"]["path"]).read_bytes())
        if current != prepared:
            raise ValueError("Installed runtime metadata/source changed since preparation")
        argv = [str(RUNTIME), "-B", "-m", "pytest", "-c", str(original.PROJECT / "pyproject.toml"),
                "-p", "agentops_native_probe_v2_plugin", "--basetemp", str(output / "pytest-temp"),
                "-o", f"cache_dir={output / 'pytest-cache'}", "--junitxml", str(output / "junit.xml"),
                original.NODEID]
        result["pytest_started"] = True
        receipt = original.capture(argv, output=output, label="upstream-confirmation",
                                   cwd=original.PROJECT, environment=environment,
                                   timeout=plan["timeout_seconds"])
        result["pytest_returncode"] = receipt["returncode"]
        reports = original.load_json(output / "pytest-reports.json")
        result["application_test_started"] = any(row["when"] == "call" for row in reports["reports"])
        if receipt["returncode"] != 0:
            raise ValueError("Original upstream test failed; retained without retry")
        validate_pytest_reports(reports)
        profile = original.load_json(output / "passive-profile.json")
        result["application_requests_performed"] = sum(
            row["event"] == "helper_call" for row in profile["observations"])
        isolated = original.load_json(output / "isolated-seed-before.json")
        seed = original.load_json(output / "seed-before.json")
        fields = {"user_tables", "schema", "user_version", "tables", "columns"}
        if {key: isolated[key] for key in fields} != {key: seed[key] for key in fields}:
            raise ValueError("Original fixture's isolated seed differs from immutable source seed")
        checked = original.capture([sys.executable, "-B", str(original.CHECKER),
            "--profile", str(output / "passive-profile.json"),
            "--seed-db", str(original.SOURCE / "agents/data/incidents.db"),
            "--output", str(output / "effect-check.json")], output=output,
            label="independent-effect-check", cwd=ROOT, environment=environment, timeout=30)
        result["independent_check"] = "passed" if checked["returncode"] == 0 else "failed"
        if checked["returncode"] != 0:
            raise ValueError("Independent effect checker rejected the retained record")
        result["status"] = "upstream_and_boundary_effect_check_passed"
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
    finally:
        try:
            result["source_unchanged_after"] = original.source_inventory() == plan["source_files"]
        except Exception as error:
            result["source_unchanged_after"] = False
            result["source_error"] = f"{type(error).__name__}: {error}"
        if not result["source_unchanged_after"]:
            result["status"] = "failed_source_integrity"
        result["finished_at_utc"] = original.now()
        result["files"] = [original.digest(path) for path in sorted(output.iterdir()) if path.is_file()]
        original.write_json(output / "result.json", result)
    print(json.dumps(result, indent=2))
    if result["status"] != "upstream_and_boundary_effect_check_passed":
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run"))
    parser.add_argument("--output", type=Path, default=RUNS / "native-probe-v4")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.output)
    else:
        run(args.output)
