"""Fresh stdlib core comparison with retained Windows deterministic reconciliation.

--check-inputs is read-only. --execute consumes a new output allocation exactly
once. It captures the current checkout, runs existing adversarial tests, executes
all four budgets in fresh workers, and verifies every completed bundle.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "runs/refinement-scaling/v2/inputs"
REFERENCE = ROOT / "runs/shared-lifting-scaling/v3-20261110-1"
BUDGETS = (32, 256, 4096, 100000)
ARMS = ("baseline", "direct_pruned", "candidate", "shared_lift")
TESTS = (
    "test_refinement", "test_refinement_shared_lift_v2",
    "test_direct_goal_pruned_v2", "test_oracle", "test_direct_comparison_v2",
    "test_shared_lifting_comparison_v3", "test_benchmark_resources_v1",
    "test_benchmark", "test_refinement_scaling_generator_v1", "test_shared_admission_v1",
)
INPUT_PINS = {
    "suite.json": "5ed596bcaf8e4868f1159db9773f1d3cb80b5334fd2b65fe4e4abbfb9fb93738",
    "manifest.json": "73dca6c030e709da2707969c15f5f590eec7b1c35fe0bcb3ef5829fa5a87933e",
}
RESULT_PINS = {
    32: "b33c6491e0b175e76fff8ae8826ddd039e8d545b0ed28c9d5bc19c6ff2cbedcf",
    256: "b8465e02cf8bdaf0e9dd6a67bdc982130b7c64d462de69e2cd5fbbc49a6c8399",
    4096: "de30ac1a2cbc1523a15b2f44a0ca619a2683ce06f572eac3870f1f446b8efcb0",
    100000: "92137f9cc15feac73fb51b9777cd961be307c6161bf6ad5c797ef3464ff1817c",
}
CLI_BOOT = (
    "import sys; sys.path.insert(0,sys.argv[1]); "
    "from interoperability.shared_lifting_comparison_v3 import main; "
    "raise SystemExit(main(sys.argv[2:]))"
)
TEST_BOOT = (
    "import json,sys,unittest; from pathlib import Path; "
    "r=Path(sys.argv[1]); sys.path[:0]=[str(r/'src'),str(r/'tests'),str(r/'scripts')]; "
    "s=unittest.defaultTestLoader.loadTestsFromNames(sys.argv[2:]); "
    "v=unittest.TextTestRunner(verbosity=2).run(s); "
    "print(json.dumps({'tests_run':v.testsRun,'errors':len(v.errors),"
    "'failures':len(v.failures),'skipped':len(v.skipped),'successful':v.wasSuccessful()})); "
    "raise SystemExit(0 if v.wasSuccessful() and not v.skipped else 1)"
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def regular_bytes(path):
    require(path.is_file() and not path.is_symlink(), "Expected regular input: " + str(path))
    return path.read_bytes()


def record(path, relative_to):
    raw = regular_bytes(path)
    return {"path": path.relative_to(relative_to).as_posix(), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def read(path):
    return json.loads(regular_bytes(path))


def write(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def rows(path):
    values = {}
    for line in regular_bytes(path).splitlines():
        row = json.loads(line)
        require(row["case_id"] not in values, "Duplicate retained case ID")
        values[row["case_id"]] = row
    return values


def check_inputs():
    for name, expected in INPUT_PINS.items():
        require(record(INPUT / name, ROOT)["sha256"] == expected, "Frozen input pin differs: " + name)
    suite, manifest = read(INPUT / "suite.json"), read(INPUT / "manifest.json")
    require(suite["split"] == "development" and suite["evaluation_clock"] == 100
            and len(suite["cases"]) == len(manifest["cases"]) == 66,
            "Expected the complete 66-profile development suite at clock 100")
    cases, inventory = [], [record(INPUT / name, ROOT) for name in INPUT_PINS]
    for entry, metadata in zip(suite["cases"], manifest["cases"]):
        item = metadata["input"]
        name = PurePosixPath(item["path"])
        require(not name.is_absolute() and ".." not in name.parts and str(name) == item["path"]
                and "\\" not in item["path"], "Unsafe profile path")
        actual = record(INPUT / str(name), INPUT)
        require(actual == item and entry["path"] == item["path"]
                and entry["family"] == metadata["family"], "Profile manifest binding differs")
        profile = read(INPUT / str(name))
        require(profile["id"] == metadata["profile_id"], "Profile ID differs from manifest")
        cases.append({"id": profile["id"], "family": entry["family"], "path": entry["path"],
                      "sha256": actual["sha256"]})
        inventory.append(record(INPUT / str(name), ROOT))
    require(len({case["id"] for case in cases}) == 66, "Profile IDs must be unique")
    for budget in BUDGETS:
        path = REFERENCE / f"budget-{budget}/results.jsonl"
        require(record(path, ROOT)["sha256"] == RESULT_PINS[budget],
                "Frozen Windows result pin differs: " + str(budget))
        old = rows(path)
        require(set(old) == {case["id"] for case in cases}, "Reference case membership differs")
        for case in cases:
            row = old[case["id"]]
            require(row["family"] == case["family"] and row["evaluation_clock"] == 100
                    and set(row["algorithms"]) == set(ARMS), "Reference design differs")
        inventory.append(record(path, ROOT))
    paths = list((ROOT / "src/interoperability").rglob("*.py"))
    paths += list((ROOT / "tests").glob("*.py"))
    paths += list((ROOT / "examples/refinement-development").rglob("*.json"))
    paths += list((ROOT / "examples/benchmark-development").rglob("*.json"))
    paths += [ROOT / "scripts/generate_refinement_scaling_v1.py",
              ROOT / "scripts/ci_research_core_v1.py",
              ROOT / "docs/research/ci-research-core-plan-v1.md",
              ROOT / ".github/workflows/research-core-reproduction.yml"]
    require(all((ROOT / "tests" / (name + ".py")).is_file() for name in TESTS), "Required test is absent")
    inventory += [record(path, ROOT) for path in sorted(paths)]
    require(len({item["path"] for item in inventory}) == len(inventory), "Duplicate original input")
    return {"schema_version": "ci-research-core-preflight/1", "status": "passed", "cases": cases,
            "budgets": list(BUDGETS), "algorithms": list(ARMS), "test_modules": list(TESTS),
            "original_inventory": inventory, "live_model_calls": 0, "live_application_runs": 0}


def capture(output, preflight):
    copied = []
    for item in preflight["original_inventory"]:
        source = ROOT / item["path"]
        if source.is_relative_to(INPUT):
            target = output / "inputs" / source.relative_to(INPUT)
        elif source.is_relative_to(REFERENCE):
            target = output / "reference" / source.relative_to(REFERENCE)
        else:
            target = output / "checkout" / source.relative_to(ROOT)
        require(record(source, ROOT) == item, "Input changed before capture: " + item["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(regular_bytes(source))
        copied.append(record(target, output))
    return copied


def unchanged(output, plan):
    changes = []
    for base, items in ((ROOT, plan["original_inventory"]), (output, plan["captured_inventory"])):
        for item in items:
            try:
                actual = record(base / item["path"], base)
            except (OSError, ValueError) as error:
                actual = {"error": str(error)}
            if actual != item:
                changes.append({"base": str(base), "path": item["path"], "actual": actual})
    actual_names = {path.relative_to(output).as_posix() for name in ("checkout", "inputs", "reference")
                    for path in (output / name).rglob("*") if path.is_file()}
    expected_names = {item["path"] for item in plan["captured_inventory"]}
    if actual_names != expected_names:
        changes.append({"category": "captured_inventory", "added": sorted(actual_names - expected_names),
                        "missing": sorted(expected_names - actual_names)})
    return {"unchanged": not changes, "changes": changes}


def invoke(output, label, argv, timeout):
    folder = output / "commands" / label
    folder.mkdir(parents=True, exist_ok=False)
    environment = {key: os.environ[key] for key in (
        "PATH", "SystemRoot", "WINDIR", "TEMP", "TMP", "TMPDIR", "COMSPEC", "PATHEXT") if key in os.environ}
    environment.update(PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1")
    receipt = {"label": label, "argv": argv, "cwd": str(output / "checkout"),
               "started_at": now(), "timeout_seconds": timeout, "returncode": None, "timed_out": False,
               "environment_keys": sorted(environment)}
    tick = time.perf_counter_ns()
    with (folder / "stdout.bin").open("xb") as stdout, (folder / "stderr.bin").open("xb") as stderr:
        try:
            process = subprocess.run(argv, cwd=output / "checkout", env=environment,
                stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, timeout=timeout, check=False)
            receipt["returncode"] = process.returncode
        except subprocess.TimeoutExpired:
            receipt["timed_out"] = True
        except OSError as error:
            receipt["error"] = type(error).__name__ + ": " + str(error)
    receipt.update(finished_at=now(), coordinator_wall_ns=time.perf_counter_ns() - tick,
                   stdout=record(folder / "stdout.bin", output), stderr=record(folder / "stderr.bin", output))
    write(folder / "process.json", receipt)
    return receipt


def deterministic(execution):
    result = execution.get("result")
    if not isinstance(result, dict):
        projection = {"status": execution.get("status"), "result": result}
    else:
        projection = {"status": execution.get("status"), "result": {
            key: value for key, value in result.items() if key != "stats"}}
        projection["result"]["stats"] = {
            key: value for key, value in result.get("stats", {}).items() if key != "elapsed_ns"}
    # Keep input integrity in the comparison; omit only machine/runtime observations.
    projection.update({key: execution.get(key) for key in (
        "input_sha256_before", "input_sha256_after", "input_unchanged")})
    return projection


def reconcile(output, plan, budget):
    actual = rows(output / f"budget-{budget}/results.jsonl")
    previous = rows(output / f"reference/budget-{budget}/results.jsonl")
    require(set(actual) == set(previous) == {case["id"] for case in plan["cases"]},
            "Fresh or retained result membership differs")
    differences, coverage, comparisons = [], {arm: Counter() for arm in ARMS}, 0
    for case in plan["cases"]:
        row, old = actual[case["id"]], previous[case["id"]]
        for key in ("family", "evaluation_clock", "model_sha256", "input_schema", "reference_valid"):
            if row.get(key) != old.get(key):
                differences.append({"case": case["id"], "kind": key})
        require(set(row["algorithms"]) == set(ARMS), "Fresh arm membership differs")
        if deterministic(row["reference"]) != deterministic(old["reference"]):
            differences.append({"case": case["id"], "kind": "reference_execution"})
        for arm in ARMS:
            value, retained = row["algorithms"][arm], old["algorithms"][arm]
            comparisons += 1
            decision = value["execution"].get("result", {}).get("decision", value["execution"]["status"])
            coverage[arm][decision] += 1
            coverage[arm]["certified"] += int(value["valid_result"] is True and value["certificate_valid"] is True)
            if deterministic(value["execution"]) != deterministic(retained["execution"]):
                differences.append({"case": case["id"], "arm": arm, "kind": "deterministic_execution"})
            for key in ("status", "valid_result", "certificate_valid", "decision_agreement"):
                if value.get(key) != retained.get(key):
                    differences.append({"case": case["id"], "arm": arm, "kind": key})
            if ("certificate_check" in value) != ("certificate_check" in retained):
                differences.append({"case": case["id"], "arm": arm, "kind": "checker_membership"})
            elif "certificate_check" in value and deterministic(value["certificate_check"]) != deterministic(retained["certificate_check"]):
                differences.append({"case": case["id"], "arm": arm, "kind": "checker_execution"})
    verification = read(output / f"commands/budget-{budget}-verify/stdout.bin")
    summary = read(output / f"budget-{budget}/summary.json")
    return {"budget": budget, "cases": len(actual), "algorithm_comparisons": comparisons,
            "deterministic_unchanged": not differences, "differences": differences,
            "coverage": {arm: dict(counts) for arm, counts in coverage.items()},
            "verification": verification, "benchmark_status": summary["status"],
            "all_cases_remain_in_denominator": True}


def execute(output):
    output = output.resolve()
    require(not output.exists(), "Output allocation already exists; choose a fresh run/attempt path")
    output.mkdir(parents=True, exist_ok=False)
    result = {"schema_version": "ci-research-core-result/1", "status": "failed", "started_at": now(),
              "budgets": [], "commands": [], "live_model_calls": 0, "live_application_runs": 0}
    plan = None
    try:
        require(sys.version_info[:2] == (3, 13), "Use Python 3.13 for the retained-version comparison")
        preflight = check_inputs()
        plan = {**preflight, "schema_version": "ci-research-core-plan/1", "prepared_at": now(),
                "captured_inventory": capture(output, preflight),
                "runtime": {"python": sys.version, "platform": platform.platform(), "executable": sys.executable},
                "github": {key: os.environ.get(key) for key in (
                    "GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "RUNNER_OS", "RUNNER_ARCH")},
                "work_budget_unit": "each algorithm's declared deterministic work units",
                "worker_timeout_seconds": 30, "checker_work_budget": 2000000,
                "comparison_exclusions": ["stats.elapsed_ns", "evaluation_ns", "worker_body_ns",
                    "process", "resources"],
                "resource_limit": "Linux ru_maxrss and Windows PeakWorkingSetSize are distinct observations; no cross-OS performance equality claim"}
        write(output / "plan.json", plan)
        write(output / "plan-seal.json", {"plan": record(output / "plan.json", output)})
        tests = invoke(output, "existing-core-tests", [sys.executable, "-I", "-S", "-B", "-c", TEST_BOOT,
                       str(output / "checkout"), *TESTS], 300)
        result["commands"].append(tests)
        result["tests"] = read(output / "commands/existing-core-tests/stdout.bin") if tests["returncode"] == 0 else None
        result["post_test_integrity"] = unchanged(output, plan)
        require(result["post_test_integrity"]["unchanged"], "Tests changed captured or original research inputs")
        require(tests["returncode"] == 0, "Existing core tests failed; raw test output retained")
        boot = [sys.executable, "-I", "-S", "-B", "-c", CLI_BOOT, str(output / "checkout/src")]
        for budget in BUDGETS:
            bundle = output / f"budget-{budget}"
            run = invoke(output, f"budget-{budget}-run", [*boot, "run", "--suite", str(output / "inputs/suite.json"),
                "--output", str(bundle), "--work-budget", str(budget), "--timeout-seconds", "30"], 420)
            result["commands"].append(run)
            # Verification is attempted even when the command failed or produced a partial allocation.
            verify = invoke(output, f"budget-{budget}-verify", [*boot, "verify", str(bundle)], 120)
            result["commands"].append(verify)
            if run["returncode"] == verify["returncode"] == 0:
                result["budgets"].append(reconcile(output, plan, budget))
            else:
                result["budgets"].append({"budget": budget, "status": "failed", "run_returncode": run["returncode"],
                                          "verify_returncode": verify["returncode"]})
        result["final_integrity"] = unchanged(output, plan)
        require(result["final_integrity"]["unchanged"], "Captured or original inputs changed during reproduction")
        require(record(output / "plan.json", output) == read(output / "plan-seal.json")["plan"], "Plan seal differs")
        require(all(item.get("deterministic_unchanged") is True and item["verification"]["status"] == "passed"
                    and item["benchmark_status"] == "passed" for item in result["budgets"]),
                "A budget failed verification or deterministic Windows reconciliation")
        result.update(status="passed", algorithm_comparisons=sum(item["algorithm_comparisons"] for item in result["budgets"]),
                      worker_jobs_bound=sum(item["verification"]["worker_jobs_bound"] for item in result["budgets"]),
                      certificate_jobs_bound=sum(item["verification"]["certificate_jobs_bound"] for item in result["budgets"]))
    except Exception as error:
        result["error"] = type(error).__name__ + ": " + str(error)
        with (output / "failure.txt").open("x", encoding="utf-8") as stream:
            traceback.print_exc(file=stream)
    finally:
        result["finished_at"] = now()
        write(output / "result.json", result)
        files = [record(path, output) for path in sorted(output.rglob("*")) if path.is_file()]
        write(output / "retained-manifest.json", {"schema_version": "ci-research-core-retained-manifest/1",
            "status": result["status"], "files": files,
            "scope": "Every retained regular file except this manifest; includes failures and raw command streams"})
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-inputs", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.check_inputs:
        result = check_inputs()
        print(json.dumps({key: value for key, value in result.items() if key != "original_inventory"}, indent=2))
    else:
        parser.error("--execute requires --output") if args.output is None else None
        result = execute(args.output)
        print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
