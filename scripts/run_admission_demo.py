"""Run the admission implementation demonstration into a new evidence directory."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]


def write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def record(path: Path) -> dict:
    raw = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="New directory; never overwrite an attempt")
    parser.add_argument("--replay", action="store_true", help="Also execute the captured recipe benchmark again")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error(f"refusing to overwrite existing demonstration: {output}")

    suite_path = ROOT / "examples/benchmark-development/recipe-v1.json"
    suite = json.loads(suite_path.read_bytes())
    finite_path = ROOT / "examples/benchmark-development/suite.json"
    finite = json.loads(finite_path.read_bytes())
    inputs = {suite_path, finite_path, Path(__file__).resolve(),
              ROOT / "examples/refinement-development/manifest.json"}
    for path, specification in ((suite_path, suite), (finite_path, finite)):
        inputs.update((path.parent / case["path"]).resolve() for case in specification["cases"])
    inputs.update((ROOT / "src/interoperability").glob("*.py"))
    before = [record(path) for path in sorted(inputs)]
    prefix = [sys.executable, "-B", "-m", "interoperability"]
    profiles = ROOT / "examples/refinement-development"
    steps = []

    def add(name: str, arguments: list[str], requires: list[str] | None = None) -> None:
        steps.append({"name": name, "argv": prefix + arguments, "requires": requires or []})

    for name, filename, method in (
        ("supported", "04-correlated-prefix-refinement.json", "refinement"),
        ("direct", "04-correlated-prefix-refinement.json", "direct"),
        ("unsupported", "02-fixed-text-shape-obstruction.json", "refinement"),
        ("unknown", "03-missing-public-binding-partial-coverage.json", "refinement"),
    ):
        add(name, ["admit", "--input", str(profiles / filename), "--method", method,
                   "--now", "100", "--output", str(output / f"{name}.json")])
    add("benchmark", ["benchmark", "--suite", str(suite_path), "--algorithm",
        "candidate=interoperability.refinement:evaluate", "--work-budget", "100000",
        "--timeout-seconds", "30", "--output", str(output / "benchmark")])
    add("verify", ["benchmark", "--verify", str(output / "benchmark")], ["benchmark"])
    add("finite", ["benchmark", "--suite", str(finite_path), "--timeout-seconds", "30",
                   "--output", str(output / "finite")])
    add("verify-finite", ["benchmark", "--verify", str(output / "finite")], ["finite"])
    if args.replay:
        add("replay", ["benchmark", "--replay", str(output / "benchmark"),
                       "--output", str(output / "replay")], ["verify"])
        add("verify-replay", ["benchmark", "--verify", str(output / "replay")], ["replay"])

    output.mkdir(parents=True)
    plan = {"schema_version": "admission-demonstration-plan/1",
            "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
            "inputs": before, "recipe_suite": suite, "finite_suite": finite,
            "evaluation_clock": 100, "recipe_work_budget": 100000,
            "worker_timeout_seconds": 30, "steps": steps,
            "scope": "Authored development demonstration; no held-out or application execution",
            "success_criteria": ["All command receipts succeed", "Independent certificates accepted",
                "Benchmark case inventory and captured bundle verify", "Source and input bytes unchanged"],
            "threshold_claims": {"novelty": False, "speedup": False, "project_70_percent": False}}
    write(output / "plan.json", plan)
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), PYTHONDONTWRITEBYTECODE="1")
    completed = {}
    for step in steps:
        name = step["name"]
        if any(completed[item]["status"] != "passed" for item in step["requires"]):
            completed[name] = {"name": name, "status": "not_run_dependency_failed"}
            write(output / f"{name}-command.json", completed[name])
            continue
        print(f"Running {name}...", flush=True)
        tick = time.perf_counter_ns()
        started = datetime.now(timezone.utc).isoformat()
        with (output / f"{name}.stdout.txt").open("xb") as stdout, (output / f"{name}.stderr.txt").open("xb") as stderr:
            result = subprocess.run(step["argv"], cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                    stdout=stdout, stderr=stderr)
        completed[name] = {"name": name, "status": "passed" if result.returncode == 0 else "failed",
                           "argv": step["argv"], "returncode": result.returncode,
                           "started_at_utc": started, "wall_ns": time.perf_counter_ns() - tick}
        write(output / f"{name}-command.json", completed[name])
        print(f"  {completed[name]['status']}", flush=True)

    after = [record(path) for path in sorted(inputs)]
    source_unchanged = before == after
    passed = source_unchanged and all(item["status"] == "passed" for item in completed.values())
    receipt = {"schema_version": "admission-demonstration/1",
               "status": "passed" if passed else "failed", "inputs_unchanged": source_unchanged,
               "finished_at_utc": datetime.now(timezone.utc).isoformat(), "inputs_after": after,
               "steps": list(completed.values()), "application_requests": 0, "live_model_calls": 0,
               "claim_limit": plan["scope"]}
    write(output / "result.json", receipt)
    print(f"Demonstration {receipt['status']}: {output / 'result.json'}", flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
