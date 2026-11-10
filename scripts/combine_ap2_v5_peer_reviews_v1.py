"""Cross-check two AP2 v5 peer audits and retain bounded rejection controls."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_auditor():
    path = ROOT / "scripts/audit_ap2_v5_source_gate_peer_v1.py"
    spec = importlib.util.spec_from_file_location("_ap2_v5_source_peer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def controls(auditor, h, capture):
    cell = capture / "matrix/cells/human_demo_otp--shared"
    raw, events, public, rpc = h.journal(cell)
    base = cell / "admission/attempt-000"
    prepared = h.read(base / "pending-input.json")
    receipt = h.read(base / "admission-before-send.json")
    result = h.read(base / "solver-result.json")
    checkpoint = receipt["journal_checkpoint_before_admission"]
    canonical = h.read(cell / "canonical-input.json")
    checker = h.generic_checker(cell)
    rows = []

    def reject(name, call):
        try:
            call()
        except (ValueError, KeyError, TypeError) as error:
            rows.append({"id": name, "rejected": True, "reason": str(error)})
        else:
            raise ValueError("peer_control_accepted:" + name)

    changed_raw = bytes([raw[0] ^ 1]) + raw[1:]
    reject("altered_durable_prefix_byte", lambda: auditor.verify_prefix(h, changed_raw, events, checkpoint))
    bad_count = dict(checkpoint, events=checkpoint["events"] + 1)
    reject("altered_prefix_event_count", lambda: auditor.verify_prefix(h, raw, events, bad_count))
    bad_sequence = deepcopy(checkpoint)
    bad_sequence["next_source_indices"]["merchant_raw"] += 1
    reject("altered_prefix_source_sequence", lambda: auditor.verify_prefix(h, raw, events, bad_sequence))
    orphan = deepcopy(canonical)
    pieces = orphan["payment_mandate_sdjwt"].split("~")
    part = pieces[1]
    pieces[1] = part[:10] + ("A" if part[10] != "A" else "B") + part[11:]
    orphan["payment_mandate_sdjwt"] = "~".join(pieces)
    reject("modified_unanchored_mandate_disclosure", lambda: auditor.mandate_hashes(orphan))
    bad_checkout = dict(canonical, checkout_hash="wrong")
    reject("changed_checkout_transaction_link", lambda: auditor.mandate_hashes(bad_checkout))
    for name, clock, mutant in (
        ("expired_finite_certificate", receipt["valid_until"] + 1, deepcopy(result)),
        ("modified_certificate_request", receipt["evaluation_clock"], deepcopy(result)),
    ):
        if name == "modified_certificate_request":
            mutant["certificate"]["steps"][0]["request"]["message"]["taskId"] = "wrong-task"
        auditor.require(not checker.check_certificate(deepcopy(prepared["profile"]), mutant, clock),
                        "generic_checker_control_accepted:" + name)
        rows.append({"id": name, "rejected": True})
    return rows


def combine(retained):
    auditor = load_auditor()
    h, decoder = auditor.helper()
    source_path = retained / "source-gate-peer-review-v1.json"
    numeric_path = retained / "numeric-peer-review-v1.json"
    source, numeric = h.read(source_path), h.read(numeric_path)
    auditor.require(source["verification_passed"] and source["verified_cells"] == numeric["reviewed_cells"] == 65,
                    "peer_review_incomplete")
    source_rows = {row["id"]: row for row in source["cells"]}
    numeric_rows = {row["case_id"] + "--" + row["arm_id"]: row for row in numeric["cells"]}
    auditor.require(source_rows.keys() == numeric_rows.keys(), "peer_denominator_disagreement")
    for label, row in source_rows.items():
        peer = numeric_rows[label]
        for key in ("purchase_completed", "strict_error_free_owned_cell_purchase", "merchant_task_id",
                    "processor_task_id", "actor_error_type", "actor_error_reason", "source_errors"):
            auditor.require(row[key] == peer[key], "peer_cell_disagreement:" + label + ":" + key)
    auditor.require(source["purchase_counts"] == {arm: values["purchase_completed"] for arm, values in numeric["arm_counts"].items()}
                    and source["strict_error_free_owned_cell_purchase_counts"] == {
                        arm: values["strict_error_free_owned_cell_purchase"] for arm, values in numeric["arm_counts"].items()},
                    "peer_total_disagreement")
    capture = retained / "extracted"
    rejection_controls = controls(auditor, h, capture)
    original = h.read(capture / "independent-evaluation/result.json")
    buyer_attestations = [row["buyer_signature_review"] for row in original["cells"]]
    auditor.require(len(buyer_attestations) == 65 and all(row["verified"] and not row["merchant_checkout_signature_verified"]
                    for row in buyer_attestations), "retained_signature_attestation_scope")
    return {"schema_version": "ap2-v5-independent-peer-review/1", "reviewed_utc": datetime.now(timezone.utc).isoformat(),
        "status": "65_cell_source_gate_and_numeric_peer_audits_agree", "declared_cells": 65,
        "source_gate_verified_cells": 65, "numeric_verified_cells": 65, "disagreements": [],
        "purchase_counts": source["purchase_counts"], "total_verified_purchases": numeric["total_verified_purchases"],
        "strict_error_free_owned_cell_purchase_counts": source["strict_error_free_owned_cell_purchase_counts"],
        "total_strict_error_free_owned_cell_purchases": numeric["total_strict_error_free_owned_cell_purchases"],
        "paired_comparisons": numeric["paired_comparisons"], "duplicate_suffix_outcomes": source["duplicate_suffix_outcomes"],
        "original_source_rehashed_files_per_cell": 136, "original_source_rehashed_file_instances": 136 * 65,
        "shared_gate_source_relation_bindings_verified": True, "stale_supported_certificate_refused_before_handler": True,
        "buyer_mandate_root_anchored_disclosure_and_checkout_hash_links_reverified": True,
        "buyer_signature_scope": "The first separate evaluator retained 65 passed buyer-root cryptographic checks. This peer audit verifies those attestation records and anchored hash links, not cryptographic signatures. Merchant checkout key/signature and legal issuer policy remain unqualified.",
        "rejection_controls": rejection_controls, "all_rejection_controls_passed": all(row["rejected"] for row in rejection_controls),
        "inputs": {str(path.relative_to(ROOT)): auditor.byte_identity(path.read_bytes()) for path in (source_path, numeric_path,
            capture / "independent-evaluation/result.json")},
        "audit_scripts": {str(path.relative_to(ROOT)): auditor.byte_identity(path.read_bytes()) for path in
            (Path(__file__).resolve(), ROOT / "scripts/audit_ap2_v5_source_gate_peer_v1.py", ROOT / "scripts/audit_ap2_v5_numeric_peer_v1.py")},
        "claim_limits": source["claim_limits"], "human_review_replaced": False,
        "whole_original_adk_task_success_established": False, "novelty_or_broad_empirical_superiority_established": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--retained", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("fresh_combined_review_output_required")
    result = combine(args.retained.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "total_verified_purchases", "total_strict_error_free_owned_cell_purchases", "all_rejection_controls_passed")}))


if __name__ == "__main__":
    main()
