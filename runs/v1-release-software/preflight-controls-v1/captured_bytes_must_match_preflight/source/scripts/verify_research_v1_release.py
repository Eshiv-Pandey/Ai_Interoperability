"""Fresh Linux V1 software qualification using existing bounded coordinators.

This executes development software, not original applications or providers.
Every allocation is exclusive; failed commands and unknown decisions are kept.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import ci_research_core_v2 as owned
import run_shared_admission_demo_v1 as demo
import validate_task_banks_v1 as bank

core = owned.core
EXTRA_TESTS = (
    "test_pending_admission", "test_task_bank_validation_v1",
    "test_ap2_original_native_provider_semantics_v2",
    "test_analyze_ap2_native_shopper_provider_v3",
    "test_ap2_native_shopper_provider_v4",
)


def inventory():
    preflight = owned.check_inputs()
    _, demonstration = demo.inventory()
    paths = {ROOT / item["path"] for item in preflight["original_inventory"] + demonstration}
    for folder in ("scripts", "tests"):
        paths.update((ROOT / folder).glob("*.py"))
    paths.update(path for path in (ROOT / "tests/fixtures").rglob("*") if path.is_file())
    paths.update(path for path in (ROOT / "runs/ap2-native-shopper-provider-development/v3/preparation-1").rglob("*")
                 if path.is_file())
    paths.update((ROOT / "examples/refinement-development").glob("*.json"))
    for domain in ("agentops", "ap2"):
        inputs = [ROOT / f"benchmark/tasks-v1/{domain}/{projection}.json"
                  for projection in ("application", "evaluator")]
        paths.update(inputs)
        report = bank.validate_pair(*(core.read(path) for path in inputs),
                                    lambda name: bank.read_regular(ROOT, name))
        core.require(report["allocation_complete"], "Candidate allocation is incomplete")
        paths.update(ROOT / name for name in report["source_files"])
    paths.add(ROOT / ".github/workflows/research-v1-release-verification.yml")
    return [core.record(path, ROOT) for path in sorted(paths)]


def execute(output):
    owned.require_linux()
    core.require(sys.version_info[:3] == (3, 13, 1), "Release comparison uses Python 3.13.1")
    output = output.resolve()
    core.require(output.is_relative_to(ROOT / "runs") and not output.exists(),
                 "Require a fresh release allocation under workspace runs")
    before = inventory()
    output.mkdir(parents=True, exist_ok=False)
    # The coordinator's outer commands use an empty working directory. Each
    # existing driver resolves its code from its absolute, recorded script path.
    (output / "checkout").mkdir()
    captured = []
    for row in before:
        target = output / "source" / row["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = core.regular_bytes(ROOT / row["path"])
        core.require(core.record(ROOT / row["path"], ROOT) == row, "Source changed before capture")
        with target.open("xb") as stream:
            stream.write(raw)
        captured.append(core.record(target, output / "source"))
    core.require(captured == before, "Frozen release copy differs from preflight bytes")
    plan = {"schema_version": "research-v1-release-software-plan/1",
            "prepared_at_utc": core.now(), "source": before, "captured_source_matches_preflight": True,
            "github": {key: os.environ.get(key) for key in (
                "GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "RUNNER_OS", "RUNNER_ARCH")},
            "python": sys.version, "extra_test_modules": list(EXTRA_TESTS),
            "scope": "Fresh development software qualification; no application, provider, human-gold or full-study qualification",
            "failure_policy": "Stop dependent commands on failure; retain consumed allocation and all streams"}
    core.write(output / "plan.json", plan)
    commands = [
        ("owned-timeout-controls", [sys.executable, "-I", "-S", "-B",
            str(ROOT / "scripts/ci_research_core_v2.py"), "--test-timeouts", "--output", str(output / "timeouts")], 90,
            output / "timeouts/result.json"),
        ("complete-core-reproduction", [sys.executable, "-I", "-S", "-B",
            str(ROOT / "scripts/ci_research_core_v2.py"), "--execute", "--output", str(output / "core")], 1200,
            output / "core/result.json"),
        ("admission-demo-and-replay", [sys.executable, "-I", "-S", "-B",
            str(ROOT / "scripts/run_shared_admission_demo_v1.py"), "--output", str(output / "demo"), "--replay"], 180,
            output / "demo/result.json"),
        ("current-extra-controls", [sys.executable, "-I", "-S", "-B", "-c", core.TEST_BOOT,
            str(ROOT), *EXTRA_TESTS], 180, None),
        ("complete-bank-validation", [sys.executable, "-I", "-S", "-B",
            str(ROOT / "scripts/validate_task_banks_v1.py"), "--require-complete",
            "--output", str(output / "bank-validation.json")], 60, None),
    ]
    result = {"schema_version": "research-v1-release-software-result/1", "status": "failed",
              "started_at_utc": core.now(), "commands": [], "scheduled_commands": len(commands),
              "application_calls": 0, "provider_calls": 0, "human_review": False,
              "whole_original_research_project_complete": False, "claim_limit": plan["scope"]}
    try:
        for name, argv, timeout, outcome in commands:
            print("Running " + name, flush=True)
            receipt = owned.invoke(output, name, argv, timeout)
            result["commands"].append(receipt)
            core.require(receipt["returncode"] == 0 and not receipt["timed_out"], "Command failed: " + name)
            if outcome is not None:
                observed = core.read(outcome)
                core.require(observed["status"] == "passed", "Recorded outcome failed: " + name)
                receipt["validated_outcome"] = core.record(outcome, output)
            if name == "current-extra-controls":
                observed = core.read(output / "commands" / name / "stdout.bin")
                core.require(observed["successful"] and observed["tests_run"] > 0
                             and observed["skipped"] == observed["failures"] == observed["errors"] == 0,
                             "Current controls did not all execute successfully")
                result["extra_controls"] = observed
            if name == "complete-bank-validation":
                observed = core.read(output / "bank-validation.json")
                core.require(observed["status"] == "structurally_valid"
                             and observed["allocation_complete"] and observed["total_templates"] == 68
                             and observed["semantic_or_runtime_qualification_claimed"] is False,
                             "Bank structure or its explicit qualification boundary differs")
                result["bank_structure"] = {"templates": 68, "semantic_or_runtime_qualification": False}
        after = inventory()
        captured_after = [core.record(output / "source" / row["path"], output / "source") for row in before]
        result.update(source_after=after, sources_unchanged=before == after,
                      captured_source_matches_preflight=captured == before,
                      captured_sources_unchanged=captured == captured_after)
        core.require(before == after == captured == captured_after, "Release source bytes changed")
        result["status"] = "passed"
    except BaseException as error:
        result["error"] = type(error).__name__ + ": " + str(error)
        with (output / "failure.txt").open("x", encoding="utf-8") as stream:
            traceback.print_exc(file=stream)
    finally:
        result["finished_at_utc"] = core.now()
        result["outer_owned_groups_confirmed_closed"] = not owned._OPEN_GROUPS
        core.write(output / "result.json", result)
        if not owned._OPEN_GROUPS:
            owned.guarded_write(output / "retained-manifest.json", {
                "schema_version": "research-v1-release-software-manifest/1", "status": result["status"],
                "files": [core.record(path, output) for path in sorted(output.rglob("*")) if path.is_file()]})
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-inputs", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.check_inputs:
        rows = inventory()
        print(json.dumps({"status": "passed", "input_files": len(rows), "application_calls": 0, "provider_calls": 0}))
    else:
        if args.output is None:
            parser.error("--execute requires --output")
        value = execute(args.output)
        print(json.dumps({"status": value["status"], "commands_completed": len(value["commands"]),
                          "output": str(args.output), "application_calls": 0, "provider_calls": 0}))
        raise SystemExit(0 if value["status"] == "passed" else 1)
constructed altered capture