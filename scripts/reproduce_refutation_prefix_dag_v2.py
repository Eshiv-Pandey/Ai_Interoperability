"""Recompute all retained V2 proof sizes without admission or checker execution."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from interoperability import refutation_prefix_dag_v2 as codec

RECEIPT = ROOT / "docs/research/refutation-prefix-dag-comparison-v2.json"


def need(condition, label):
    if not condition:
        raise ValueError(label)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def record(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw), "sha256": sha(raw)}


def reproduce():
    receipt = json.loads(RECEIPT.read_bytes())
    source = ROOT / receipt["input"]["path"]
    need(source.resolve().is_relative_to(ROOT), "workspace_input_required")
    need(record(source) == receipt["input"], "retained_input_changed")
    need(record(ROOT / receipt["implementation"]["path"]) == receipt["implementation"],
         "codec_source_changed")
    raw_lines = source.read_bytes().splitlines(keepends=True)
    parsed = [(raw, json.loads(raw)) for raw in raw_lines if raw.strip()]
    selected = [(raw, row) for raw, row in parsed
                if row["algorithms"]["shared_lift"]["execution"]["result"]["decision"] == "unsupported"]
    need(len(parsed) == receipt["retained_case_count"] == 66
         and len(selected) == receipt["selected_unsupported_certificate_count"] == 26,
         "complete_retained_subset_required")
    rows = []
    for raw, row in selected:
        shared = row["algorithms"]["shared_lift"]
        old = shared["execution"]["result"]["certificate"]
        direct = row["algorithms"]["direct_pruned"]["execution"]["result"]["certificate"]
        encoded = codec.encode_certificate(old)
        restored = codec.decode_certificate(encoded)
        old_raw, encoded_raw, restored_raw, direct_raw = map(canonical, (old, encoded, restored, direct))
        need(restored == old and restored_raw == old_raw, "ordered_certificate_round_trip_changed")
        rows.append({"case_id": row["case_id"], "dag_arcs": sum(len(n["arcs"]) for n in encoded["dag"]["nodes"]),
            "dag_bytes": len(encoded_raw), "dag_certificate_sha256": sha(encoded_raw),
            "dag_nodes": len(encoded["dag"]["nodes"]), "direct_bytes": len(direct_raw),
            "direct_certificate_sha256": sha(direct_raw), "evaluation_clock": row["evaluation_clock"],
            "exact_ordered_object_and_canonical_byte_round_trip": True,
            "inherited_shared_certificate_valid": shared["certificate_valid"], "new_semantic_checker_call": False,
            "old_bytes": len(old_raw), "old_certificate_sha256": sha(old_raw),
            "prefix_count": len(old["refuted_prefixes"]),
            "prefix_edge_count": sum(len(p) for p in old["refuted_prefixes"]),
            "restored_certificate_sha256": sha(restored_raw), "retained_row_sha256": sha(raw)})
    need(rows == receipt["rows"], "retained_comparison_row_changed")
    aggregate = {"dag_bytes": sum(r["dag_bytes"] for r in rows),
        "direct_bytes": sum(r["direct_bytes"] for r in rows),
        "equal": sum(r["dag_bytes"] == r["old_bytes"] for r in rows),
        "larger": sum(r["dag_bytes"] > r["old_bytes"] for r in rows),
        "old_bytes": sum(r["old_bytes"] for r in rows),
        "smaller": sum(r["dag_bytes"] < r["old_bytes"] for r in rows)}
    need(aggregate == receipt["aggregate"], "aggregate_changed")
    need([r["case_id"] for r in rows if r["dag_bytes"] > r["old_bytes"]] == receipt["larger_case_ids"]
         and [r["case_id"] for r in rows if r["dag_bytes"] < r["old_bytes"]] == receipt["smaller_case_ids"],
         "adverse_or_favorable_case_membership_changed")
    return {"schema_version": "refutation-prefix-dag-v2-retained-reproduction/1", "passed": True,
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "cases": len(rows), "aggregate": aggregate,
        "rows": rows, "inputs": [record(RECEIPT), record(source), record(Path(codec.__file__)), record(Path(__file__))],
        "new_admission_solver_calls": 0, "new_semantic_checker_calls": 0,
        "constructed_tests_run_in_this_command": 0, "human_scientific_review": False,
        "scope": "Exact retained proof representation and bytes; original semantic acceptance is inherited evidence."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    need(output.is_relative_to(ROOT / "runs") and not output.exists(), "fresh_workspace_run_output_required")
    result = reproduce()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"passed": result["passed"], "cases": result["cases"], "aggregate": result["aggregate"]}))


if __name__ == "__main__":
    main()
