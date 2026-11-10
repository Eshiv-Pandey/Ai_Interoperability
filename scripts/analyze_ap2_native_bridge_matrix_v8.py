"""Analyze retained native/bridge outcomes without importing an actor or evaluator.

The 39 bridge cells are initiation observations of repeated prefixes, not
executed fault continuations. No missing cell leaves its allocated denominator.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS = ROOT / "runs/ap2-reference-development/v5/retained-42881390576-2/extracted/independent-evaluation/result.json"
PUBLIC = ROOT / "benchmark/ap2-native-bridge-development-v8/application.json"
NATIVE = ("reference", "conventional", "recovery", "shared", "recovery_shared")
BRIDGES = ("amir_typed", "mg_typed", "mg_raw")


def read(path):
    return json.loads(path.read_bytes())


def record(path):
    raw = path.read_bytes()
    return {"path": path.resolve().relative_to(ROOT).as_posix(), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def analyze(evaluation, output):
    if output.exists():
        raise ValueError("Fresh analysis path required")
    current, previous, manifest = read(evaluation), read(PREVIOUS), read(PUBLIC)
    cells = current["cells"]
    if current["declared_cells"] != 104 or len(cells) != 104:
        raise ValueError("Preserved 104-cell denominator differs")
    expected = {(case["id"], arm["id"]) for case in manifest["cases"] for arm in manifest["arms"]}
    indexed = {(cell["case_id"], cell["arm_id"]): cell for cell in cells}
    if len(indexed) != 104 or set(indexed) != expected:
        raise ValueError("Missing or duplicated allocated cell identities")
    older = {(cell["case_id"], cell["arm_id"]): cell for cell in previous["cells"]}
    summaries, comparisons = {}, []
    for arm in NATIVE + BRIDGES:
        group = [cell for cell in cells if cell["arm_id"] == arm]
        observed = sum(cell.get("purchase_completed") is True for cell in group)
        error_free = sum(cell.get("purchase_completed") is True and not cell.get("source_errors")
                         and cell.get("actor_error_type") is None for cell in group)
        summaries[arm] = {"allocated_cells": len(group), "purchase_observations": observed,
            "error_free_owned_cell_purchase_observations": error_free,
            "evaluation_statuses": dict(Counter(cell["evaluation_status"] for cell in group)),
            "interpretation": "Repeated original bridge initiation prefixes; fault continuations unrealized" if arm in BRIDGES else "Owned TCP/Uvicorn original payment-tool development cells"}
    for (case, arm), cell in indexed.items():
        if arm in NATIVE:
            prior = older[case, arm]
            evaluable = (cell["evaluation_status"] == "original_application_capture_verified"
                         and prior["evaluation_status"] == "original_application_capture_verified")
            comparisons.append({"case_id": case, "arm_id": arm,
                "ASGI_purchase_observed": prior["purchase_completed"],
                "TCP_purchase_observed": cell.get("purchase_completed"),
                "comparison_evaluable": evaluable,
                "same_purchase_indicator": cell.get("purchase_completed") == prior["purchase_completed"] if evaluable else None,
                "TCP_evaluation_status": cell["evaluation_status"],
                "TCP_source_errors": cell.get("source_errors", []),
                "whole_original_task_success_inferred": False})
    value = {"schema_version": "ap2-v8-native-bridge-development-analysis/1", "status": "analyzed_all_allocated_cells",
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "evidence": [record(evaluation), record(PREVIOUS), record(PUBLIC), record(Path(__file__))],
        "declared_cells": 104, "native_payment_tool_cells": 65, "bridge_initiation_cells": 39,
        "distinct_authored_public_cases": 13, "independent_task_count_is_not_cell_count": True,
        "arm_summaries": summaries, "paired_ASGI_TCP_purchase_indicators": comparisons,
        "ASGI_TCP_purchase_indicator_changes": sum(row["comparison_evaluable"] and not row["same_purchase_indicator"] for row in comparisons),
        "unresolved_ASGI_TCP_pairs": sum(not row["comparison_evaluable"] for row in comparisons),
        "new_actor_evaluator_solver_checker_or_provider_calls": 0, "human_gold_validated": False,
        "original_server_launch_qualification_claimed": False, "bridge_continuation_success_inferred": False,
        "limits": ["All unexecuted/refused/errored cells retain allocated denominators.",
                   "Transport comparison uses separate source-bound development allocations, not independent held-out tasks.",
                   "Bridge initiation prefix attempts do not exercise the later case-specific receiver or OTP faults.",
                   "Purchase observations may precede a duplicate suffix failure; report both outcome counts.",
                   "No provider, whole-route non-support, financial settlement, native-launch or human-gold qualification is inferred."]}
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"status": value["status"], "arms": summaries,
                      "ASGI_TCP_purchase_indicator_changes": value["ASGI_TCP_purchase_indicator_changes"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.evaluation, args.output)
