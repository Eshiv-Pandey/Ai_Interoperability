"""No-application constructed audit of V8 partial-allocation finalization."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import types

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("fresh_peer_control_output_required")
    source = ROOT / "scripts/run_ap2_native_bridge_matrix_v8.py"
    raw = source.read_bytes()
    module = types.ModuleType("_ap2_v8_constructed_finalization_peer")
    module.__file__ = str(source)
    exec(compile(raw, str(source), "exec"), module.__dict__)
    public = json.loads(module.PUBLIC.read_bytes())
    expected = module.public_cells(public)
    if len(expected) != 104:
        raise ValueError("prospective_104_denominator_changed")
    with tempfile.TemporaryDirectory(prefix="ap2-v8-finalization-peer-") as temporary:
        base = Path(temporary)
        output = base / "allocation"
        argv = ["--output", str(output), "--site-packages", str(base / "nonexecuted-packages"),
                "--bridge-runtime", str(base / "nonexecuted-runtime"), "--node", sys.executable]
        module.main(argv + ["--prepare-only"])
        closed, started = expected[:2]
        for row in (closed, started):
            attempt = output / "attempts" / row["id"]
            attempt.mkdir(parents=True)
            module.write(attempt / "before-dispatch.json", dict(row, command=["synthetic-no-process-executed"],
                         started_utc="2026-11-11T00:00:00+00:00", remaining_matrix_seconds=2000))
        closed_receipt = dict(closed, allocation_status="actor_process_finished", returncode=0,
                              elapsed_seconds=1.0, ended_utc="2026-11-11T00:00:01+00:00",
                              business_goal_decided_by_actor=False)
        module.write(output / "attempts" / closed["id"] / "after-dispatch.json", closed_receipt)
        before_bytes = (output / "attempts" / closed["id"] / "after-dispatch.json").read_bytes()
        module.main(argv + ["--finalize-unexecuted"])
        result = json.loads((output / "execution-results.json").read_bytes())
        first, second, untouched = result["cells"][:3]
        controls = {
            "all_104_cells_retained": len(result["cells"]) == 104,
            "closed_dispatch_keeps_actual_returncode": first["returncode"] == 0,
            "closed_dispatch_keeps_actual_finished_status": first["allocation_status"] == "actor_process_finished",
            "started_only_not_labelled_unexecuted": "not_executed" not in second["allocation_status"],
            "truly_untouched_stays_unexecuted": untouched["returncode"] is None and "not_executed" in untouched["allocation_status"],
            "prior_closed_receipt_not_rewritten": before_bytes == (output / "attempts" / closed["id"] / "after-dispatch.json").read_bytes(),
        }
        report = {"schema_version": "ap2-v8-partial-finalization-peer-control/1",
                  "reviewed_utc": datetime.now(timezone.utc).isoformat(), "orchestrator_sha256": hashlib.sha256(raw).hexdigest(),
                  "constructed_fixture_only": True, "actual_application_or_provider_calls": 0,
                  "actual_actor_processes_executed": 0, "controls": controls,
                  "passed": all(controls.values()), "closed_cell": first, "started_only_cell": second,
                  "untouched_cell": untouched, "synthetic_closed_receipt": closed_receipt,
                  "failure_meaning": "Existing completed and started allocations must not be relabelled as untouched when finalizing an interrupted matrix."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "failed_controls": [key for key, value in controls.items() if not value]}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
