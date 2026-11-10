"""Read-only retained Linux comparison audit and fresh exhaustive checking."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
import run_guard_pruned_comparison_v3 as study
import run_abstraction_control_v1 as files
from interoperability import benchmark, direct_goal_pruned_v2 as checker


def audit(capture, archive, output):
    capture, archive, output = map(lambda p: Path(p).resolve(), (capture, archive, output))
    files.require(not output.exists(), "Audit output must be unused")
    manifest = files.read(capture / "manifest.json")
    actual = [files.record(p, capture) for p in sorted(capture.rglob("*")) if p.is_file() and p != capture / "manifest.json"]
    files.require(actual == manifest["files"], "Capture file bytes or membership changed")
    raw_digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    files.require(raw_digest == "ae24d4ed85f23100f6e994d26386322d7d7ac781d22d180200c687d611c666fc", "GitHub raw archive digest differs")
    with zipfile.ZipFile(archive) as zipped:
        inventory = {p.relative_to(capture).as_posix(): p for p in capture.rglob("*") if p.is_file()}
        infos = zipped.infolist()
        files.require(len(infos) == len(inventory) and {i.filename for i in infos} == set(inventory), "Raw ZIP membership differs")
        for item in infos:
            files.require(zipped.read(item) == inventory[item.filename].read_bytes(), "ZIP/extraction bytes differ")
    plan, result = files.read(capture / "plan.json"), files.read(capture / "result.json")
    files.require(plan["budgets"] == list(study.BUDGETS) and plan["case_count"] == 66 and plan["clock"] == 100,
                  "Study settings changed")
    files.require(plan["worker_timeout_seconds"] == 30 and result["status"] == "passed", "Wrong successor execution")
    checked, workers, source_files, reports = 0, 0, 0, {}
    for budget in study.BUDGETS:
        folder = capture / f"budget-{budget}"
        benchmark.verify_bundle(folder)
        execution = files.read(folder / "execution.json")
        files.require(execution["runtime"]["platform"].startswith("Linux"), "Not retained Linux reproduction")
        files.require(execution["schema_adapter"]["checker"] == study.adapter.CHECKER
                      and execution["algorithms"] == [study.asdict(a) for a in study.ALGORITHMS], "Wrong algorithms/checker")
        for name in ("oracle.py", "refinement_oracle.py", "direct_goal_pruned_v2.py", "direct_guard_pruned_v3.py", "manifest.py"):
            path = folder / "source/interoperability" / name
            files.require(path.read_bytes() == (ROOT / "src/interoperability" / name).read_bytes(), "Changed current checker/solver source")
            source_files += 1
        rows = files.rows(folder / "results.jsonl")
        originals = files.rows(ROOT / "runs/shared-lifting-scaling/v3-20261110-1" / f"budget-{budget}/results.jsonl")
        reports[str(budget)] = study.analyze(rows, originals)
        files.require(reports[str(budget)] == result["reports"][str(budget)], "Derived report differs")
        for index, row in enumerate(rows):
            profile = files.read(folder / row["input_snapshot"])
            for label, module in (("reference", study.adapter.LEGACY),) + tuple((a.name, a.module) for a in study.ALGORITHMS):
                item = (row["reference"] if label == "reference" else row["algorithms"][label]["execution"])
                job = files.read(folder / f"jobs/case-{index:04d}-{label}/input.json")
                files.require(job["module"] == module and job["entrypoint"] == "evaluate"
                              and job["now"] == 100 and job["keyword_arguments"] == {"budget": budget}
                              and job["runtime_manifest"] == profile, "Wrong evaluation dispatch")
                files.require(item["status"] == "returned" and item["input_unchanged"] is True
                              and item["process"]["returncode"] == 0 and not item["process"]["timed_out"], "Incomplete worker")
                workers += 1
            for spec in study.ALGORITHMS:
                arm = row["algorithms"][spec.name]
                if arm["execution"]["result"]["decision"] == "unknown":
                    files.require("certificate_check" not in arm and arm["execution"]["result"]["certificate"] is None,
                                  "Unknown has an unexpected proof/check")
                    continue
                job = files.read(folder / f"jobs/case-{index:04d}-{spec.name}-certificate/input.json")
                observation = arm["certificate_check"]
                files.require(job["module"] == study.adapter.CHECKER and job["entrypoint"] == "check_certificate"
                              and job["runtime_manifest"] == profile and job["result"] == arm["execution"]["result"]
                              and job["now"] == 100, "Wrong certificate dispatch")
                files.require(arm["certificate_valid"] is True and observation["result"] is True
                              and observation["status"] == "returned" and not observation["process"]["timed_out"]
                              and observation["process"]["returncode"] == 0, "Recorded certificate failed")
                files.require(checker.check_certificate(profile, arm["execution"]["result"], 100) is True,
                              "Fresh exhaustive checker rejected retained proof")
                checked += 1
                workers += 1
    receipt = {"schema_version": "guard-pruned-independent-capture-audit/3", "status": "passed",
               "capture": str(capture), "raw_archive_sha256": raw_digest, "manifest_files_verified": len(actual),
               "zip_files_verified": len(inventory), "source_bindings_verified": source_files,
               "worker_jobs_bound": workers, "fresh_exhaustive_certificate_checks": checked,
               "reports": reports, "github_run_id": 42836579527,
               "executed_commit": "d341909ff1ccb1ce641e4eab63699bd4ff2cc671",
               "new_solver_jobs": 0, "new_application_or_model_requests": 0,
               "human_review": False, "claim_limit": study.LIMIT}
    files.write(output, receipt)
    return {k: receipt[k] for k in ("status", "manifest_files_verified", "zip_files_verified", "worker_jobs_bound", "fresh_exhaustive_certificate_checks")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.capture, args.archive, args.output)))
