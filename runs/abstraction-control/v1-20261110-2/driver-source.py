"""Separate inner-graph control; never a same-semantics recipe comparator.

Reuses the retained high-budget recipe inputs, strips only the declared recipe
wrapper, and runs the original finite baseline and independent finite oracle.
The four-arm study is read, verified and preserved, never rerun or extended.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from interoperability import benchmark, benchmark_resources_v1 as resources
from interoperability import shared_lifting_comparison_v3 as comparison

ARM = benchmark.AlgorithmSpec("abstraction_only", "interoperability.baseline")
SCHEMA = "abstraction-only-control/1"
LIMIT = ("Related authored development inputs. Inner-graph support is not "
         "recipe feasibility or application success. This arm answers a weaker "
         "question and is excluded from same-input four-method accuracy/work ranks.")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return benchmark._json(Path(path))


def write(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        handle.write("\n")


def record(path, base):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), "Require a regular evidence file")
    raw = path.read_bytes()
    return {"path": path.relative_to(base).as_posix(), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def rows(path):
    return [json.loads(line) for line in Path(path).read_bytes().splitlines()]


@contextmanager
def resource_workers():
    previous = benchmark._WORKER_BOOT
    benchmark._WORKER_BOOT = resources.WORKER_BOOT
    try:
        yield
    finally:
        benchmark._WORKER_BOOT = previous


def derive(control, refined):
    require(len(control) == len(refined), "Unequal planned case counts")
    pairs, families, checks, workers = Counter(), {}, 0, 0
    for inner, recipe in zip(control, refined):
        # Wrapper and inner graph have deliberately different IDs. Exact
        # ordered graph/profile digests are checked in verify(), not renamed.
        require(inner["family"] == recipe["family"], "Case family changed")
        arm = inner["algorithms"][ARM.name]
        direct = recipe["algorithms"]["direct_pruned"]
        require(inner["reference_valid"] and arm["valid_result"] and arm["decision_agreement"] is True,
                "Abstract baseline/oracle is not a valid agreeing observation")
        require(direct["valid_result"], "Retained direct result is invalid")
        a, b = arm["execution"]["result"]["decision"], direct["execution"]["result"]["decision"]
        if a != "unknown":
            require(arm["certificate_valid"] is True, "Abstract certificate not accepted")
            checks += 1
        if b != "unknown":
            require(direct["certificate_valid"] is True, "Retained recipe certificate not accepted")
        key = a + "/" + b
        pairs[key] += 1
        families.setdefault(inner["family"], Counter())[key] += 1
        invocations = [inner["reference"], arm["execution"]]
        if "certificate_check" in arm:
            invocations.append(arm["certificate_check"])
        for item in invocations:
            require(item["process"]["returncode"] == 0 and not item["process"]["timed_out"],
                    "Failed/partial abstract worker")
            require(item["input_unchanged"] is True, "Worker input changed")
        workers += len(invocations)
    return {"cases": len(control), "pairs_abstract_over_recipe": dict(sorted(pairs.items())),
            "families": {name: dict(sorted(value.items())) for name, value in sorted(families.items())},
            "new_worker_jobs": workers, "accepted_abstract_certificates": checks,
            "resources": resources.summarize([item for row in control for item in
                [row["reference"], row["algorithms"][ARM.name]["execution"]] +
                ([row["algorithms"][ARM.name]["certificate_check"]]
                 if "certificate_check" in row["algorithms"][ARM.name] else [])])}


def verify(output):
    output = Path(output).resolve()
    manifest = read(output / "manifest.json")
    actual = [record(p, output) for p in sorted(output.rglob("*"))
              if p.is_file() and p != output / "manifest.json"]
    require(actual == manifest["files"], "Control file bytes or membership changed")
    plan, result = read(output / "plan.json"), read(output / "result.json")
    require(plan["schema_version"] == SCHEMA and plan["algorithm"] == asdict(ARM), "Wrong control plan")
    benchmark.verify_bundle(output / "control")
    execution = read(output / "control/execution.json")
    require(execution["algorithms"] == [asdict(ARM)] and execution["input_schema"] == "finite-continuation/1",
            "Control used a different algorithm/schema")
    require(execution["schema_adapter"] == benchmark.ADAPTERS["finite-continuation/1"],
            "Control did not use the independent finite oracle/checker")
    control, refined = rows(output / "control/results.jsonl"), rows(output / "retained-recipe-results.jsonl")
    require(len(plan["cases"]) == len(control), "Plan case membership differs")
    for index, (case, inner, recipe) in enumerate(zip(plan["cases"], control, refined)):
        profile = read(output / case["recipe_snapshot"])
        abstract = read(output / "control" / inner["input_snapshot"])
        require(case["id"] == recipe["case_id"] == profile["id"]
                and case["graph_id"] == inner["case_id"] == abstract["id"], "Case identity changed")
        require(benchmark.digest(profile) == recipe["model_sha256"] == case["recipe_digest"],
                "Recipe snapshot differs from retained comparison")
        require(benchmark.digest(profile["model"]) == benchmark.digest(abstract) == inner["model_sha256"],
                "Inner graph differs from recipe model")
        for label, module in (("reference", "interoperability.oracle"), (ARM.name, ARM.module)):
            job = read(output / f"control/jobs/case-{index:04d}-{label}/input.json")
            require(job["module"] == module and job["entrypoint"] == "evaluate"
                    and job["now"] == plan["clock"] and job["runtime_manifest"] == abstract,
                    "Abstract evaluation dispatch changed")
        arm = inner["algorithms"][ARM.name]
        if "certificate_check" in arm:
            job = read(output / f"control/jobs/case-{index:04d}-{ARM.name}-certificate/input.json")
            require(job["module"] == "interoperability.oracle" and job["entrypoint"] == "check_certificate"
                    and job["result"] == arm["execution"]["result"] and job["runtime_manifest"] == abstract,
                    "Abstract certificate dispatch changed")
    require(result["analysis"] == derive(control, refined), "Derived comparison changed")
    return {"status": "passed", "manifest_files": len(actual), "cases": len(control),
            "claim_limit": LIMIT, "source_authentication": False}


def run(source_bundle, output):
    source_bundle, output = Path(source_bundle).resolve(), Path(output).resolve()
    require(not output.exists() and output.parent.is_dir(), "Require new output beneath an existing parent")
    original_check = comparison.verify(source_bundle)
    execution = read(source_bundle / "execution.json")
    require(execution["work_budget"] == 100000, "This control binds the original high-budget study")
    originals = rows(source_bundle / "results.jsonl")
    output.mkdir()
    try:
        for name in ("prepared", "prepared/graphs", "recipe-snapshots"):
            (output / name).mkdir()
        shutil.copyfile(__file__, output / "driver-source.py")
        shutil.copyfile(source_bundle / "results.jsonl", output / "retained-recipe-results.jsonl")
        cases, suite_cases = [], []
        for index, row in enumerate(originals):
            profile = read(source_bundle / row["input_snapshot"])
            require(profile["id"] == row["case_id"], "Ambiguous recipe identity")
            recipe_name = f"recipe-snapshots/case-{index:04d}.json"
            graph_name = f"graphs/case-{index:04d}.json"
            write(output / recipe_name, profile)
            write(output / "prepared" / graph_name, profile["model"])
            suite_cases.append({"path": graph_name, "family": row["family"]})
            cases.append({"id": row["case_id"], "graph_id": profile["model"]["id"], "recipe_snapshot": recipe_name,
                          "recipe_digest": benchmark.digest(profile), "family": row["family"]})
        suite = {"schema_version": "admission-benchmark-suite/1", "id": "inner-graph-control-v1",
                 "split": "development", "evaluation_clock": execution["evaluation_clock"], "cases": suite_cases}
        write(output / "prepared/suite.json", suite)
        write(output / "plan.json", {"schema_version": SCHEMA, "created_at": datetime.now(timezone.utc).isoformat(),
              "algorithm": asdict(ARM), "clock": execution["evaluation_clock"], "cases": cases,
              "timeout_seconds": 10, "source_bundle": str(source_bundle),
              "source_bundle_verification": original_check,
              "source_results": record(source_bundle / "results.jsonl", source_bundle),
              "source_manifest": record(source_bundle / "manifest.json", source_bundle),
              "runtime": {"python": sys.version, "executable": sys.executable, "platform": platform.platform()},
              "claim_limit": LIMIT, "predeclared_analysis": "Full ordered cross-tab versus retained high-budget goal-pruned direct; all cases remain in denominator."})
        with resource_workers():
            summary = benchmark.run_benchmark(output / "prepared/suite.json", output / "control", [ARM], timeout_seconds=10)
        checked = benchmark.verify_bundle(output / "control")
        analysis = derive(rows(output / "control/results.jsonl"), originals)
        require(summary["status"] == "passed", "Abstract control failed")
        comparison.verify(source_bundle)
        require(record(source_bundle / "results.jsonl", source_bundle) == read(output / "plan.json")["source_results"],
                "Original recipe results changed")
        write(output / "result.json", {"schema_version": SCHEMA, "status": "passed", "analysis": analysis,
              "control_verification": checked, "claim_limit": LIMIT, "new_recipe_solver_jobs": 0,
              "new_application_requests": 0, "new_live_model_requests": 0})
        inventory = [record(p, output) for p in sorted(output.rglob("*")) if p.is_file()]
        write(output / "manifest.json", {"schema_version": SCHEMA, "files": inventory})
        return verify(output)
    except Exception as error:
        write(output / "runner-failure.json", {"status": "failed", "error_type": type(error).__name__, "error": str(error)})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("run", "verify"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-bundle", type=Path)
    args = parser.parse_args()
    result = (run(args.source_bundle, args.output) if args.mode == "run" and args.source_bundle
              else verify(args.output) if args.mode == "verify" else parser.error("run requires --source-bundle"))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
