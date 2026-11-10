"""Prospectively allocate all 104 AP2 native/bridge development cells.

This orchestrator reads the public application manifest only. Business goals
and source-derived expectations are evaluated later in a separate process.
"""
from __future__ import annotations

import argparse
import ast
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
sys.path.insert(0, str(ROOT / 'scripts'))
PUBLIC = ROOT / "benchmark/ap2-native-bridge-development-v8/application.json"
RUNNER = ROOT / "scripts/ap2_reference_development_v8.py"


def digest(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write(path, value):
    with Path(path).open("xb") as handle:
        handle.write((json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode())
        handle.flush()
        os.fsync(handle.fileno())


def public_cells(manifest):
    if manifest.get("schema_version") != "ap2-native-bridge-development-matrix/8" or manifest.get("provider_requests_allowed") != 0:
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


def finalize_retained_cell(output, cell):
    """Reconstruct observed dispatch state without rewriting any existing receipt."""
    attempt = output / 'attempts' / cell['id']
    captured = output / 'cells' / cell['id']
    before, after, result = (attempt / 'before-dispatch.json', attempt / 'after-dispatch.json', captured / 'result.json')
    evidence = []
    parsed = {}
    for name, path in (('before', before), ('after', after), ('cell_result', result)):
        if not path.is_file():
            continue
        raw = path.read_bytes()
        evidence.append({'kind': name, 'path': path.relative_to(output).as_posix(), 'identity': digest(raw)})
        try:
            if len(raw) > 4 * 1024 * 1024:
                raise ValueError('dispatch_receipt_bound')
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError('dispatch_receipt_not_object')
            if name != 'cell_result' and any(value.get(key) != expected for key, expected in cell.items()):
                raise ValueError('dispatch_receipt_cell_identity_changed')
            parsed[name] = value
        except (ValueError, UnicodeError) as error:
            evidence[-1]['decode_error'] = type(error).__name__ + ': ' + str(error)[:500]
    if 'after' in parsed:
        row = dict(parsed['after'])
        row.update(reconstructed_from_retained_after_dispatch=True, finalization_evidence=evidence)
        return row
    cell_result = parsed.get('cell_result', {})
    returncode = cell_result.get('returncode')
    if type(returncode) is not int:
        returncode = None
    if 'cell_result' in parsed:
        status = 'cell_result_retained_without_matrix_after_receipt'
    elif before.exists():
        # The before receipt proves dispatch intent, not that Popen or any
        # application effect actually occurred. Keep the absent close unknown.
        status = 'dispatch_intent_recorded_without_closing_receipt'
    elif after.exists() or captured.exists():
        status = 'partial_cell_or_dispatch_evidence_retained_without_closing_receipt'
    else:
        status = 'not_executed_before_workflow_finalization'
    return dict(cell, allocation_status=status, returncode=returncode,
                matrix_after_dispatch_receipt_present=False, finalization_evidence=evidence,
                captured_cell_output_present=captured.exists(), business_goal_decided_by_actor=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--site-packages", type=Path, required=True)
    parser.add_argument("--bridge-runtime", type=Path, required=True)
    parser.add_argument("--node", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare-only", action="store_true")
    mode.add_argument("--resume-prepared", action="store_true")
    mode.add_argument("--finalize-unexecuted", action="store_true")
    args = parser.parse_args(argv)
    raw = PUBLIC.read_bytes()
    manifest = json.loads(raw)
    cells = public_cells(manifest)
    output = args.output.absolute()
    if args.resume_prepared or args.finalize_unexecuted:
        if not output.is_dir() or (output / 'execution-results.json').exists():
            raise ValueError('only_unexecuted_prospective_allocation_may_resume_or_finalize')
        if (output / 'public-manifest.json').read_bytes() != raw:
            raise ValueError('prepared_public_manifest_changed')
    else:
        output.mkdir(parents=True, exist_ok=False)
        (output / "public-manifest.json").write_bytes(raw)
        (output / "source-orchestrator.py").write_bytes(Path(__file__).read_bytes())
    components = ast.literal_eval(next(node.value for node in ast.parse(RUNNER.read_text()).body
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'OWNED_COMPONENTS' for target in node.targets)))
    prospective = {"schema_version": "ap2-native-bridge-allocation/8", "created_utc": datetime.now(timezone.utc).isoformat(),
        "public_manifest": digest(raw), "runner": digest(RUNNER.read_bytes()), "declared_cells": len(cells),
        "cells": cells, "cell_timeout_seconds": manifest["worker_timeout_seconds"],
        "matrix_timeout_seconds": manifest["matrix_timeout_seconds"], "provider_requests_allowed": 0,
        "source_bank_candidates_unchanged": 34, "source_bank_task_qualification_established": False,
        "native_qualification_established": False, "whole_route_non_support_inference_allowed": False,
        "actor_does_not_read_private_evaluator": True,
        "source_reference_arm_has_canonical_sender_state": True,
        "fresh_private_signing_state_per_cell": True,
        "all_missing_or_failed_cells_remain_in_denominator": True}
    prospective.update(owned_components={name: digest((ROOT / name).read_bytes()) for name in components},
                       bridge_runtime=str(args.bridge_runtime.resolve()), node=str(args.node.resolve()),
                       bridge_graph_sha256=manifest['bridge_graph_sha256'], bridge_archive_sha256=manifest['bridge_archive_sha256'],
                       native_cells=65, bridge_initiation_cells=39, inverse_mapping_invented=False,
                       original_cards_rewritten=False)
    if args.resume_prepared or args.finalize_unexecuted:
        old = json.loads((output / 'allocation-manifest.json').read_bytes())
        if any(old[key] != value for key, value in prospective.items() if key != 'created_utc'):
            raise ValueError('prospective_allocation_or_actor_changed')
        prospective = old
        if args.resume_prepared and (output / 'attempts').exists():
            raise ValueError('retained_dispatch_attempts_must_be_finalized_not_replayed')
    else:
        write(output / "allocation-manifest.json", prospective)
    if args.prepare_only:
        print(json.dumps({'status': 'prospective_104_cell_allocation_prepared_before_smoke', 'output': str(output)}))
        return 0
    environment = {key: os.environ[key] for key in ("SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "LANG") if key in os.environ}
    environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1")
    outcomes = []
    started = time.monotonic()
    exhausted = False
    for cell in cells:
        if args.finalize_unexecuted:
            outcomes.append(finalize_retained_cell(output, cell))
            continue
        remaining = manifest["matrix_timeout_seconds"] - (time.monotonic() - started)
        if exhausted or remaining < manifest["worker_timeout_seconds"] + 15:
            exhausted = True
            outcomes.append(dict(cell, allocation_status="not_executed_matrix_budget_exhausted", returncode=None))
            continue
        if PUBLIC.read_bytes() != raw or digest(RUNNER.read_bytes()) != prospective["runner"]:
            outcomes.append(dict(cell, allocation_status="not_executed_prospective_actor_changed", returncode=None))
            exhausted = True
            continue
        if any(digest((ROOT / name).read_bytes()) != expected for name, expected in prospective['owned_components'].items()):
            outcomes.append(dict(cell, allocation_status='not_executed_prospective_helper_changed', returncode=None))
            exhausted = True
            continue
        command = [sys.executable, "-I", "-S", "-B", str(RUNNER), "execute", "--output", str(output / "cells" / cell["id"]),
                   "--site-packages", str(args.site_packages.resolve()), "--case", cell["case_id"], "--arm", cell["arm_id"],
                   "--bridge-runtime", str(args.bridge_runtime.resolve()), "--node", str(args.node.resolve())]
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
    write(output / "execution-results.json", {"schema_version": "ap2-native-bridge-execution/8", "declared_cells": len(cells),
        "cells": outcomes, "elapsed_seconds": time.monotonic() - started, "budget_exhausted": exhausted,
        'finalized_from_retained_dispatch_history': args.finalize_unexecuted,
        "provider_requests_allowed": 0, "actor_purchase_success_count": None,
        "source_bank_candidates_unchanged": 34, "source_bank_task_qualification_established": False,
        "native_qualification_established": False, "whole_route_non_support_inference_allowed": False})
    print(json.dumps({"status": "retained_application_matrix_allocation", "declared_cells": len(cells),
                      "executed_actor_processes": sum(row["returncode"] is not None for row in outcomes), "output": str(output)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
