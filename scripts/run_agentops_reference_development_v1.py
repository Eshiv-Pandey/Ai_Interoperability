"""Retain one bounded original-component reference for each of six dev tasks."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from agentops_reference_evaluator_v1 import IDS, seed_gold, grade, adversarial_controls

ENV_REL = "runs/ap2-environment-preparation/installed-assessment-v1/environment-manifest.json"
ENV_SHA = "4d6efdd2e4003b82517f45aead140a7afd6f1e180b3ce518904d87c96e5adeb5"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def record(path, base):
    return {"path": Path(path).relative_to(base).as_posix(), "bytes": Path(path).stat().st_size, "sha256": digest(path)}


def child_environment(case_dir, recipe):
    names = {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "USERPROFILE", "LOCALAPPDATA", "APPDATA", "PROGRAMDATA", "COMSPEC"}
    result = {key: value for key, value in os.environ.items() if key.upper() in names}
    result.update({key: value for key, value in recipe["configuration"].items() if value is not None})
    result.update(AGENT_DATA_DIR=str(case_dir / "data"), AGENT_STATE_DIR=str(case_dir / "state"),
                  PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1", GOOGLE_GENAI_USE_VERTEXAI="false")
    return result


def execute(output, dependency_profile="agentops-windows", component_profile="minimal_reads", reuse_captures=None):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    application, evaluator = (ROOT / "benchmark/tasks-v1/agentops" / name for name in ("application.json", "evaluator.json"))
    bank = json.loads(application.read_bytes())
    private_bank = json.loads(evaluator.read_bytes())
    cases = [row for row in bank["records"] if row["split"] == "development"]
    if tuple(row["id"] for row in cases) != IDS:
        raise ValueError("six-existing-development-ID-set-changed")
    if not {row["id"] for row in cases}.issubset({row["id"] for row in private_bank["records"]}):
        raise ValueError("private-bank-join-missing")
    environment_path = ROOT / ENV_REL
    if digest(environment_path) != ENV_SHA:
        raise ValueError("frozen-dependency-manifest-changed")
    ap2_environment = json.loads(environment_path.read_bytes())
    base = ap2_environment["base_interpreter"]
    if digest(base["path"]) != base["sha256"]:
        raise ValueError("frozen-interpreter-changed")
    if dependency_profile == "agentops-windows":
        previous_manifest = ROOT / "runs/agentops-reference-development/v1-20261110-3/dependency-manifest.json"
        if previous_manifest.is_file():
            environment_path = previous_manifest
            environment = json.loads(environment_path.read_bytes())
        else:
            raise ValueError("existing-native-component-snapshot-required")
    elif dependency_profile == "freeze-agentops-windows":
        environment_root = ROOT / "external/runtime-agentops-v2-recovery-2/venv"
        site_packages = environment_root / "Lib/site-packages"
        packages = {}
        for metadata in sorted(site_packages.glob("*.dist-info/METADATA")):
            headers = BytesParser().parsebytes(metadata.read_bytes(), headersonly=True)
            packages[headers["Name"]] = {"version": headers["Version"], "metadata_sha256": digest(metadata)}
        environment = {"schema_version": "agentops-component-dependency-snapshot/1", "root": str(environment_root),
                       "site_packages": str(site_packages), "base_interpreter": base,
                       "packages": packages,
                       "files": {path.relative_to(environment_root).as_posix(): {"sha256": digest(path), "bytes": path.stat().st_size}
                                 for path in sorted(site_packages.rglob("*")) if path.is_file()},
                       "binding": "Fresh bytes of existing installed Windows runtime; no native/model application qualification"}
        environment_path = output / "dependency-manifest.json"
        write(environment_path, environment)
    else:
        environment = ap2_environment
    dependency_label = ("Fresh frozen existing AgentOps Windows dependency profile; component execution only"
                        if dependency_profile in {"agentops-windows", "freeze-agentops-windows"} else
                        "Frozen AP2 Windows dependency profile; differs from AgentOps native runtime")
    source_root = ROOT / bank["source_pin"]["source_root"]
    package_root = source_root / "agents/python/src"
    seed_dir = source_root / "agents/data"
    source_files = sorted(path for path in package_root.rglob("*") if path.is_file() and path.suffix == ".py")
    source_hashes = {path.relative_to(source_root).as_posix(): digest(path) for path in source_files}
    seed_inventory = [record(path, source_root) for path in sorted(seed_dir.rglob("*")) if path.is_file()]
    for row in bank["source_pin"]["data_files"]:
        if digest(ROOT / row["path"]) != row["sha256"]:
            raise ValueError("pinned-seed-data-changed")
    for row in private_bank["records"]:
        if row["id"] not in IDS:
            continue
        for source in row["source_refs"].values():
            if digest(ROOT / source["path"]) != source["sha256"]:
                raise ValueError("private-cited-source-changed")
    actor = ROOT / "scripts/agentops_reference_actor_v1.py"
    owned = [application, evaluator, actor, Path(__file__), ROOT / "scripts/agentops_reference_evaluator_v1.py", environment_path]
    plan = {"schema_version": "agentops-component-reference-plan/1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "case_ids": list(IDS), "maximum_recipe_processes": 6, "worker_timeout_seconds": 90,
            "provider_requests": 0, "owned_inputs": [record(path, ROOT) for path in owned],
            "source_pin": bank["source_pin"]["commit"], "source_files": source_hashes, "seed_files": seed_inventory,
            "dependency_manifest_sha256": digest(environment_path), "dependency_profile": dependency_label,
            "application_scope": "six original-component public development recipes; original App/model execution remains unknown"}
    if reuse_captures is not None:
        reuse_captures = Path(reuse_captures).resolve()
        plan["reused_capture_provenance"] = {"source": str(reuse_captures),
            "source_result_sha256": digest(reuse_captures / "result.json"),
            "classification": "Postcapture corrected evaluator analysis of prior actual reads; original failed result retained",
            "cases": {selected: digest(reuse_captures / selected / "actor-output.json") for selected in IDS
                      if (reuse_captures / selected / "actor-output.json").is_file()}}
    write(output / "plan.json", plan)
    gold = seed_gold(seed_dir)
    write(output / "private-seed-gold.json", gold)
    observations, scores, processes = {}, [], []
    result = {"schema_version": "agentops-component-reference-result/1", "status": "failed", "source_task_denominator": 6,
              "original_app_tasks_passed": 0, "original_app_tasks_unknown": 6,
              "provider_requests": 0, "human_gold_review": "not_reviewed", "independent_heldout_qualification": False}
    try:
        for case in cases:
            case_dir = output / case["id"]
            prior_case = reuse_captures / case["id"] if reuse_captures else None
            if prior_case and (prior_case / "actor-output.json").is_file():
                case_dir.mkdir(exist_ok=False)
                for filename in ("actor-output.json", "events.jsonl", "before-state.json", "after-state.json", "stdout.bin", "stderr.bin", "process.json"):
                    shutil.copyfile(prior_case / filename, case_dir / filename)
                observed = json.loads((case_dir / "actor-output.json").read_bytes())
                if digest(case_dir / "actor-output.json") != plan["reused_capture_provenance"]["cases"][case["id"]]:
                    raise ValueError("reused-capture-drift")
                observations[case["id"]] = observed
                scored = grade(observed, gold, component_profile)
                scored["capture_provenance"] = {"source": str(prior_case), "fresh_original_invocations": 0}
                write(case_dir / "evaluation.json", scored)
                scores.append(scored)
                if scored["checks_verified"] != scored["checks_total"]:
                    raise ValueError("postcapture-component-evaluation-failed:" + case["id"])
                continue
            case_dir.mkdir(exist_ok=False)
            shutil.copytree(seed_dir, case_dir / "data")
            (case_dir / "state").mkdir(exist_ok=False)
            public = {"schema_version": "agentops-component-reference-public-input/1", "root": str(ROOT), "case": case,
                      "source_root": str(source_root), "package_root": str(package_root), "source_hashes": source_hashes,
                      "site_packages": environment["site_packages"], "environment_root": environment["root"],
                      "environment_manifest": str(environment_path), "state_dir": str(case_dir / "state"),
                      "dependency_profile": dependency_label, "component_profile": component_profile}
            write(case_dir / "public-input.json", public)
            command = [base["path"], "-I", "-S", "-B", "-X", "utf8", str(actor),
                       "--input", str(case_dir / "public-input.json"), "--output", str(case_dir)]
            try:
                completed = subprocess.run(command, cwd=case_dir, env=child_environment(case_dir, case["public"]["fixture_recipe"]),
                                           capture_output=True, timeout=90, check=False)
                stdout, stderr, returncode, timed_out = completed.stdout, completed.stderr, completed.returncode, False
            except subprocess.TimeoutExpired as error:
                stdout, stderr, returncode, timed_out = error.stdout or b"", error.stderr or b"", None, True
            for name, raw in (("stdout.bin", stdout), ("stderr.bin", stderr)):
                with (case_dir / name).open("xb") as stream:
                    stream.write(raw)
            receipt = {"id": case["id"], "argv": command, "returncode": returncode, "timed_out": timed_out,
                       "cwd": str(case_dir), "state_retained": True, "provider_credentials_in_environment": False}
            write(case_dir / "process.json", receipt)
            processes.append(receipt)
            if returncode != 0:
                raise ValueError("original-component-actor-failed:" + case["id"])
            observed = json.loads((case_dir / "actor-output.json").read_bytes())
            observations[case["id"]] = observed
            scored = grade(observed, gold, component_profile)
            write(case_dir / "evaluation.json", scored)
            scores.append(scored)
            if scored["checks_verified"] != scored["checks_total"]:
                raise ValueError("private-component-evaluation-failed:" + case["id"])
        controls = adversarial_controls(observations, gold)
        if not controls["all_rejected"]:
            raise ValueError("forged-component-output-not-rejected")
        if any(record(ROOT / row["path"], ROOT) != row for row in plan["owned_inputs"]):
            raise ValueError("owned-input-drift")
        if source_hashes != {path.relative_to(source_root).as_posix(): digest(path) for path in source_files}:
            raise ValueError("original-source-drift")
        if seed_inventory != [record(path, source_root) for path in sorted(seed_dir.rglob("*")) if path.is_file()]:
            raise ValueError("original-seed-drift")
        result.update(status="six_development_reference_receipts_retained",
                      component_references_verified=sum(row["status"] == "component_reference_verified" for row in scores),
                      partial_component_references_verified=sum(row["status"] == "partial_component_reference_verified" for row in scores),
                      component_references_unexecuted=sum(row["status"] == "component_reference_unexecuted" for row in scores),
                      private_checks_verified=sum(row["checks_verified"] for row in scores),
                      private_checks_total=sum(row["checks_total"] for row in scores),
                      adversarial_controls=controls, original_source_and_seed_unchanged=True)
    except Exception as error:
        result.update(error_type=type(error).__name__, error=str(error), component_references_verified=sum(row["status"] == "component_reference_verified" for row in scores))
    result.update(case_evaluations=scores, processes=processes)
    write(output / "result.json", result)
    write(output / "manifest.json", {"files": [record(path, output) for path in sorted(output.rglob("*")) if path.is_file()]})
    print(json.dumps({key: result[key] for key in ("status", "component_references_verified", "original_app_tasks_passed", "original_app_tasks_unknown")}))
    return 0 if result["status"] == "six_development_reference_receipts_retained" else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dependency-profile", choices=("ap2", "agentops-windows", "freeze-agentops-windows"), default="agentops-windows")
    parser.add_argument("--component-profile", choices=("minimal_reads", "sdk_actions_memory"), default="minimal_reads")
    parser.add_argument("--reuse-captures", type=Path)
    options = parser.parse_args()
    raise SystemExit(execute(options.output, options.dependency_profile, options.component_profile, options.reuse_captures))
