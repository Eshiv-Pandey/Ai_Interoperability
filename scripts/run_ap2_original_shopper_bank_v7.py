"""Bounded original ADK feasibility allocation preserving all 34 AP2 candidates."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "benchmark/ap2-shopper-development-v7/application.json"
RUNNER = ROOT / "scripts/ap2_reference_development_v7.py"


def digest(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write(path, value):
    with Path(path).open("xb") as handle:
        handle.write((json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode())
        handle.flush()
        os.fsync(handle.fileno())


def manifest_cells(manifest):
    def need(value, reason):
        if not value:
            raise ValueError(reason)
    need(manifest["candidate_denominator"] == len(manifest["records"]) == 34, "unchanged_candidate_denominator_required")
    rows = manifest["records"]
    need(len({row["id"] for row in rows}) == 34, "unique_source_bank_candidates_required")
    need({split: sum(row["split"] == split for row in rows) for split in ("development", "calibration", "held_out")}
         == {"development": 6, "calibration": 4, "held_out": 24}, "source_bank_split_weights_changed")
    cells = []
    for index, row in enumerate(rows):
        need(all(char in "abcdefghijklmnopqrstuvwxyz0123456789-_" for char in row["id"]), "unsafe_public_candidate_identifier")
        repeats = row["original_processes_per_candidate"] if row["execution_mode"] == "original_adk_conversation" else 0
        need(repeats in (0, 1, 2), "bounded_original_workflow_repetitions_required")
        cells.append({"index": index, "candidate_id": row["id"], "execution_mode": row["execution_mode"],
                      "original_processes": [{"id": row["id"] + f"--original-{ordinal + 1}", "ordinal": ordinal}
                                             for ordinal in range(repeats)]})
    return cells


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--site-packages", type=Path, required=True)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args(argv)
    raw = PUBLIC.read_bytes()
    manifest = json.loads(raw)
    cells = manifest_cells(manifest)
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    (output / "public-manifest.json").write_bytes(raw)
    (output / "source-orchestrator.py").write_bytes(Path(__file__).read_bytes())
    spec = importlib.util.spec_from_file_location("_ap2_v7_owned_process_helper", ROOT / "scripts/run_ap2_application_matrix_v5.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    prior_raw = (ROOT / manifest["source_boundary_capture"]).read_bytes()
    if hashlib.sha256(prior_raw).hexdigest() != manifest["source_boundary_capture_sha256"]:
        raise ValueError("retained_prior_original_source_boundary_capture_changed")
    (output / "prior-source-boundary-actor-output.json").write_bytes(prior_raw)
    plan = {"schema_version": "ap2-original-adk-allocation/7", "created_utc": datetime.now(timezone.utc).isoformat(),
            "public_manifest": digest(raw), "runner": digest(RUNNER.read_bytes()), "candidate_denominator": 34,
            "cells": cells, "new_original_adk_process_denominator": sum(len(row["original_processes"]) for row in cells),
            "prior_mixed_scope_boundary_candidate_denominator": 6,
            "provider_requests_allowed": 0, "worker_timeout_seconds": manifest["worker_timeout_seconds"],
            "allocation_timeout_seconds": manifest["allocation_timeout_seconds"],
            "human_gold_validated": False, "native_qualification_established": False,
            "all_adverse_missing_and_unrealized_branches_remain_in_denominator": True}
    write(output / "allocation-manifest.json", plan)
    if args.prepare_only:
        rows = [dict(cell, allocation_status="prospective_allocation_only",
            process_attempts=[dict(process, returncode=None, allocation_status="not_executed_preparation_only")
                              for process in cell["original_processes"]]) for cell in cells]
        write(output / "execution-results.json", {"schema_version": "ap2-original-adk-execution/7", "candidate_denominator": 34,
            "cells": rows, "provider_requests_allowed": 0, "human_gold_validated": False, "native_qualification_established": False,
            "source_candidate_branch_qualification_decided_by_actor": False, "preparation_only": True})
        print(json.dumps({"status": "prospective_original_adk_bank_denominator_retained", "candidate_denominator": 34,
                          "new_original_adk_process_denominator": plan["new_original_adk_process_denominator"], "output": str(output)}))
        return 0
    environment = {key: os.environ[key] for key in ("SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "LANG") if key in os.environ}
    environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1")
    started, exhausted = time.monotonic(), False
    results = []
    for cell in cells:
        row = dict(cell, process_attempts=[])
        if cell["execution_mode"] == "prior_source_boundary_capture":
            row["allocation_status"] = "prior_original_source_boundary_capture_linked_not_rerun_or_full_shopper"
            results.append(row)
            continue
        for process in cell["original_processes"]:
            remaining = manifest["allocation_timeout_seconds"] - (time.monotonic() - started)
            if exhausted or remaining < manifest["worker_timeout_seconds"] + 15:
                exhausted = True
                row["process_attempts"].append(dict(process, allocation_status="not_executed_allocation_budget_exhausted", returncode=None))
                continue
            if PUBLIC.read_bytes() != raw or digest(RUNNER.read_bytes()) != plan["runner"]:
                exhausted = True
                row["process_attempts"].append(dict(process, allocation_status="not_executed_prospective_actor_changed", returncode=None))
                continue
            command = [sys.executable, "-I", "-S", "-B", str(RUNNER), "execute", "--output", str(output / "cells" / process["id"]),
                       "--case", cell["candidate_id"], "--site-packages", str(args.site_packages.resolve())]
            attempt = output / "attempts" / process["id"]
            attempt.mkdir(parents=True, exist_ok=False)
            write(attempt / "before-dispatch.json", dict(process, candidate_id=cell["candidate_id"], command=command,
                started_utc=datetime.now(timezone.utc).isoformat(), remaining_allocation_seconds=remaining))
            before = time.monotonic()
            code, stdout, stderr, timed_out = helper.owned_run(command, environment, manifest["worker_timeout_seconds"] + 10)
            (attempt / "stdout.txt").write_bytes(stdout[:2 * 1024 * 1024])
            (attempt / "stderr.txt").write_bytes(stderr[:2 * 1024 * 1024])
            outcome = dict(process, allocation_status="actor_process_timed_out" if timed_out else "actor_process_finished",
                           returncode=code, elapsed_seconds=time.monotonic() - before,
                           candidate_branch_qualification_decided_by_actor=False)
            write(attempt / "after-dispatch.json", outcome)
            row["process_attempts"].append(outcome)
            print(json.dumps({"candidate": cell["candidate_id"], "process": process["id"], "returncode": code,
                              "elapsed_seconds": round(outcome["elapsed_seconds"], 3)}), flush=True)
        row["allocation_status"] = "all_original_process_outcomes_retained"
        results.append(row)
    write(output / "execution-results.json", {"schema_version": "ap2-original-adk-execution/7", "candidate_denominator": 34,
        "cells": results, "elapsed_seconds": time.monotonic() - started, "budget_exhausted": exhausted,
        "provider_requests_allowed": 0, "human_gold_validated": False, "native_qualification_established": False,
        "source_candidate_branch_qualification_decided_by_actor": False})
    print(json.dumps({"status": "retained_original_adk_source_bank_feasibility_allocation", "candidate_denominator": 34,
                      "new_original_adk_process_denominator": plan["new_original_adk_process_denominator"], "output": str(output)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
