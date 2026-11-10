"""Prospectively allocate every AP2 v5 development comparison, retaining failures.

This orchestrator reads the public application manifest only. Business goals
and source-derived expectations are evaluated later in a separate process.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "benchmark/ap2-application-development-v5/application.json"
RUNNER = ROOT / "scripts/ap2_reference_development_v5.py"


def digest(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write(path, value):
    with Path(path).open("xb") as handle:
        handle.write((json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode())
        handle.flush()
        os.fsync(handle.fileno())


def public_cells(manifest):
    if manifest.get("schema_version") != "ap2-application-development-matrix/5" or manifest.get("provider_requests_allowed") != 0:
        raise ValueError("public_zero_provider_matrix_required")
    cases, arms = manifest["cases"], manifest["arms"]
    if len({row["id"] for row in cases}) != len(cases) or len({row["id"] for row in arms}) != len(arms):
        raise ValueError("duplicate_public_case_or_arm")
    cells = [{"index": i, "id": case["id"] + "--" + arm["id"], "case_id": case["id"], "arm_id": arm["id"]}
             for i, (case, arm) in enumerate((case, arm) for case in cases for arm in arms)]
    if len(cells) != manifest["declared_cells"]:
        raise ValueError("declared_denominator_differs_from_cartesian_product")
    if any(any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for ch in row["id"]) for row in cells):
        raise ValueError("unsafe_public_cell_identifier")
    return cells


def owned_run(command, environment, timeout):
    options = {"env": environment, "stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        options["start_new_session"] = True
    process = subprocess.Popen(command, **options)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        return process.returncode, stdout, stderr, False
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        else:
            os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
        return 124, stdout, stderr, True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--site-packages", type=Path, required=True)
    args = parser.parse_args(argv)
    raw = PUBLIC.read_bytes()
    manifest = json.loads(raw)
    cells = public_cells(manifest)
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    (output / "public-manifest.json").write_bytes(raw)
    (output / "source-orchestrator.py").write_bytes(Path(__file__).read_bytes())
    prospective = {"schema_version": "ap2-application-allocation/5", "created_utc": datetime.now(timezone.utc).isoformat(),
        "public_manifest": digest(raw), "runner": digest(RUNNER.read_bytes()), "declared_cells": len(cells),
        "cells": cells, "cell_timeout_seconds": manifest["worker_timeout_seconds"],
        "matrix_timeout_seconds": manifest["matrix_timeout_seconds"], "provider_requests_allowed": 0,
        "source_bank_candidates_unchanged": 34, "source_bank_task_qualification_established": False,
        "native_qualification_established": False, "whole_route_non_support_inference_allowed": False,
        "actor_does_not_read_private_evaluator": True,
        "source_reference_arm_has_canonical_sender_state": True,
        "fresh_private_signing_state_per_cell": True,
        "all_missing_or_failed_cells_remain_in_denominator": True}
    write(output / "allocation-manifest.json", prospective)
    environment = {key: os.environ[key] for key in ("SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "LANG") if key in os.environ}
    environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1")
    outcomes = []
    started = time.monotonic()
    exhausted = False
    for cell in cells:
        remaining = manifest["matrix_timeout_seconds"] - (time.monotonic() - started)
        if exhausted or remaining < manifest["worker_timeout_seconds"] + 15:
            exhausted = True
            outcomes.append(dict(cell, allocation_status="not_executed_matrix_budget_exhausted", returncode=None))
            continue
        if PUBLIC.read_bytes() != raw or digest(RUNNER.read_bytes()) != prospective["runner"]:
            outcomes.append(dict(cell, allocation_status="not_executed_prospective_actor_changed", returncode=None))
            exhausted = True
            continue
        command = [sys.executable, "-I", "-S", "-B", str(RUNNER), "execute", "--output", str(output / "cells" / cell["id"]),
                   "--site-packages", str(args.site_packages.resolve()), "--case", cell["case_id"], "--arm", cell["arm_id"]]
        before = time.monotonic()
        attempt_path = output / "attempts" / cell["id"]
        attempt_path.mkdir(parents=True, exist_ok=False)
        write(attempt_path / "before-dispatch.json", dict(cell, command=command,
            started_utc=datetime.now(timezone.utc).isoformat(), remaining_matrix_seconds=remaining))
        code, stdout, stderr, timed_out = owned_run(command, environment, manifest["worker_timeout_seconds"] + 10)
        (attempt_path / "stdout.txt").write_bytes(stdout[:2 * 1024 * 1024])
        (attempt_path / "stderr.txt").write_bytes(stderr[:2 * 1024 * 1024])
        row = dict(cell, allocation_status="actor_process_finished" if not timed_out else "actor_process_timed_out",
                   returncode=code, elapsed_seconds=time.monotonic() - before,
                   ended_utc=datetime.now(timezone.utc).isoformat(), business_goal_decided_by_actor=False)
        write(attempt_path / "after-dispatch.json", row)
        outcomes.append(row)
        print(json.dumps({"cell": cell["id"], "index": cell["index"], "returncode": code,
                          "elapsed_seconds": round(row["elapsed_seconds"], 3)}), flush=True)
    write(output / "execution-results.json", {"schema_version": "ap2-application-execution/5", "declared_cells": len(cells),
        "cells": outcomes, "elapsed_seconds": time.monotonic() - started, "budget_exhausted": exhausted,
        "provider_requests_allowed": 0, "actor_purchase_success_count": None,
        "source_bank_candidates_unchanged": 34, "source_bank_task_qualification_established": False,
        "native_qualification_established": False, "whole_route_non_support_inference_allowed": False})
    print(json.dumps({"status": "retained_application_matrix_allocation", "declared_cells": len(cells),
                      "executed_actor_processes": sum(row["returncode"] is not None for row in outcomes), "output": str(output)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
