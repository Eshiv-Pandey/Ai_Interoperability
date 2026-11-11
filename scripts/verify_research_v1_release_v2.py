"""Retain V1 release preflight failures before invoking its unchanged software checks.

The first hosted attempt failed on absent bank-source files before its allocation
was created. Its sources and failure remain preserved. This successor allocates
an outer receipt first and reuses the same tests, budgets and demo/replay.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_research_v1_release as original

core, owned = original.core, original.owned
BASE_INVENTORY = original.inventory


def inventory():
    rows = BASE_INVENTORY()
    extra = core.record(ROOT / ".github/workflows/research-v1-release-verification-v2.yml", ROOT)
    return sorted([*rows, extra], key=lambda row: row["path"])


def execute(output):
    output = output.resolve()
    core.require(output.is_relative_to(ROOT / "runs") and not output.exists(),
                 "Require a fresh outer release allocation under runs")
    output.mkdir(parents=True, exist_ok=False)
    before = [core.record(ROOT / name, ROOT) for name in (
        "scripts/verify_research_v1_release.py", "scripts/verify_research_v1_release_v2.py",
        ".github/workflows/research-v1-release-verification-v2.yml")]
    plan = {"schema_version": "research-v1-release-outer-plan/2", "started_at_utc": core.now(),
            "source": before, "historical_failed_run": 43076696650,
            "historical_failure_preserved": True, "software_output": "software",
            "scope": "Current bounded software qualification only; original full study remains open"}
    core.write(output / "plan.json", plan)
    result = {"schema_version": "research-v1-release-outer-result/2", "status": "failed",
              "application_calls": 0, "provider_calls": 0, "scientific_gate_credit": 0}
    original.inventory = inventory
    try:
        observed = original.execute(output / "software")
        core.require(observed["status"] == "passed", "Underlying software qualification failed")
        after = [core.record(ROOT / row["path"], ROOT) for row in before]
        core.require(after == before and not owned._OPEN_GROUPS, "Outer sources changed or a group remains open")
        result.update(status="passed", software_result=core.record(output / "software/result.json", output),
                      wrapper_source_unchanged=True, sources_after=after)
    except BaseException as error:
        result["error"] = type(error).__name__ + ": " + str(error)
        with (output / "failure.txt").open("x", encoding="utf-8") as stream:
            traceback.print_exc(file=stream)
    finally:
        original.inventory = BASE_INVENTORY
        result["finished_at_utc"] = core.now()
        result["outer_owned_groups_confirmed_closed"] = not owned._OPEN_GROUPS
        core.write(output / "result.json", result)
        if not owned._OPEN_GROUPS:
            owned.guarded_write(output / "retained-manifest.json", {
                "schema_version": "research-v1-release-outer-manifest/2", "status": result["status"],
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
        print(json.dumps({"status": value["status"], "application_calls": 0, "provider_calls": 0}))
        raise SystemExit(value["status"] != "passed")
