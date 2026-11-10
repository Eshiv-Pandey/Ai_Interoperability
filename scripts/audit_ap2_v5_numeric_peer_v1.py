"""Independent stdlib-only numerical peer audit of retained AP2 V5 cells.

Reads original-source text and frozen JSON/raw ASGI observations. Never imports
the actor, original App, model router, admission evaluator, or first evaluator.
The output is new; captured evidence is opened read-only and never rewritten.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

OTP = "Initiate a payment. Include the challenge response."
RECEIPT = "ap2.PaymentReceipt"


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def identity(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def json_value(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result
    def invalid(value):
        raise ValueError("nonfinite_json:" + value)
    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)


def read(path):
    raw = path.read_bytes()
    require(len(raw) <= 64 * 1024 * 1024, "json_read_bound")
    return json_value(raw)


def untag(node, depth=0):
    require(type(node) is dict and depth <= 40, "tag_shape_or_depth")
    kind = node.get("type")
    if kind == "none":
        require(set(node) == {"type"}, "none_tag_shape")
        return None
    if kind == "bytes":
        require(set(node) == {"type", "value", "bytes", "sha256"}, "bytes_tag_shape")
        raw = base64.b64decode(node["value"], validate=True)
        require(identity(raw) == {"bytes": node["bytes"], "sha256": node["sha256"]}, "bytes_tag_digest")
        return raw
    if kind in ("str", "int", "float", "bool"):
        require(set(node) == {"type", "value"}, "scalar_tag_shape")
        value = node["value"]
        if kind == "bool":
            require(type(value) is bool, "bool_tag_type")
            return value
        require(type(value) is str and len(value) <= 2 * 1024 * 1024, "scalar_tag_bound")
        if kind == "str":
            return value
        if kind == "int":
            require(len(value) <= 1235, "integer_bound")
            decoded = int(value)
            require(str(decoded) == value, "integer_canonical")
            return decoded
        decoded = float.fromhex(value)
        require(math.isfinite(decoded) and decoded.hex() == value, "float_canonical")
        return decoded
    if kind in ("list", "tuple"):
        require(set(node) == {"type", "items"} and type(node["items"]) is list
                and len(node["items"]) <= 20000, "sequence_tag_shape")
        values = [untag(item, depth + 1) for item in node["items"]]
        return tuple(values) if kind == "tuple" else values
    require(kind == "dict" and set(node) == {"type", "entries"}, "dictionary_tag_shape")
    require(type(node["entries"]) is list and len(node["entries"]) <= 20000, "dictionary_tag_bound")
    result = {}
    for pair in node["entries"]:
        require(type(pair) is list and len(pair) == 2, "dictionary_tag_pair")
        key, value = (untag(item, depth + 1) for item in pair)
        require(key not in result, "dictionary_tag_duplicate_key")
        result[key] = value
    return result


def raw_exchanges(cell):
    raw = (cell / "observations/events.jsonl").read_bytes()
    terminal = read(cell / "observations/terminal.json")
    require(identity(raw) == terminal["journal"] and terminal["capture_complete_for_declared_intervals"]
            and terminal["missing_global_indices"] == [] and terminal["observation_errors"] == [], "journal_not_complete")
    events = [json_value(line) for line in raw.splitlines()]
    require(len(events) == terminal["attempted_events"] == terminal["durably_committed_events"], "journal_count_mismatch")
    sequences, exchanges = Counter(), {}
    for index, event in enumerate(events):
        stream = event["stream"]
        payload = untag(event["payload"])
        require(event["global_index"] == index, "journal_global_gap")
        require(event["source_index"] == payload["sequence"] == sequences[stream], "journal_source_gap")
        sequences[stream] += 1
        if stream.endswith("_public"):
            continue
        key = stream, payload["exchange"]
        exchange = exchanges.setdefault(key, {"stream": stream, "exchange": payload["exchange"],
                                             "request": bytearray(), "response": bytearray(), "first_index": index})
        boundary = payload["boundary"]
        if boundary == "scope":
            require("scope" not in exchange, "duplicate_scope")
            exchange["scope"] = payload["value"]
        if boundary == "receive_returned" and payload["value"].get("type") == "http.request":
            exchange["request"].extend(payload["value"].get("body", b""))
        if boundary == "send_completed" and payload["value"].get("type") == "http.response.body":
            exchange["response"].extend(payload["value"].get("body", b""))
        if boundary == "application_returned":
            require("last_index" not in exchange, "duplicate_exchange_close")
            exchange["last_index"] = index
    for stream, witness in terminal["streams"].items():
        require(witness["next_source_index"] == sequences[stream]
                and witness["final_witness"]["source_complete"]
                and witness["final_witness"]["active_operations"] == 0, "source_not_closed")
    rpc = []
    for exchange in exchanges.values():
        require("last_index" in exchange, "exchange_not_closed")
        if exchange["scope"]["method"] != "POST":
            continue
        request, response = (json_value(bytes(exchange[name])) for name in ("request", "response"))
        require(request.get("jsonrpc") == response.get("jsonrpc") == "2.0"
                and request["id"] == response["id"], "rpc_correlation")
        rpc.append({"stream": exchange["stream"], "exchange": exchange["exchange"],
                    "first_index": exchange["first_index"], "last_index": exchange["last_index"],
                    "request": request, "response": response})
    return rpc, len(events), identity(raw)


def texts(message):
    return [part["text"] for part in message.get("parts", []) if part.get("kind") == "text"]


def receipts(task):
    return [part["data"][RECEIPT] for artifact in task.get("artifacts") or []
            for part in artifact.get("parts", []) if RECEIPT in part.get("data", {})]


def task_wire_shape(task):
    """Omit only absent optional A2A envelope fields, never data payload fields."""
    def message_shape(message):
        result = dict(message)
        for key in ("metadata", "extensions", "referenceTaskIds", "taskId", "contextId"):
            if key in result and result[key] is None:
                del result[key]
        result["parts"] = [{key: value for key, value in part.items()
                            if not (key == "metadata" and value is None)} for part in result["parts"]]
        return result
    result = dict(task)
    for key in ("metadata", "artifacts", "history"):
        if key in result and result[key] is None:
            del result[key]
    if "history" in result:
        result["history"] = [message_shape(message) for message in result["history"]]
    result["status"] = dict(result["status"])
    if result["status"].get("message") is not None:
        result["status"]["message"] = message_shape(result["status"]["message"])
    return result


def task_responses(rpc, stream, task_id):
    return [exchange for exchange in rpc if exchange["stream"] == stream
            and exchange["response"].get("result", {}).get("id") == task_id]


def assess(cell, case, arm, execution):
    plan = read(cell / "plan.json")
    require(plan["case"] == case and plan["policy"] == arm, "plan_condition_changed")
    rpc, event_count, journal_identity = raw_exchanges(cell)
    starts = [row for row in rpc if row["stream"] == "merchant_raw"
              and row["request"].get("method") == "message/send"
              and texts(row["request"]["params"]["message"]) == ["Initiate a payment"]
              and not row["request"]["params"]["message"].get("taskId")]
    require(len(starts) == 1, "initial_payment_not_unique")
    pending = starts[0]["response"]["result"]
    require(pending["status"]["state"] == "input-required", "initial_payment_not_pending")
    require(task_wire_shape(read(cell / "payment-start-task.json")) == pending, "saved_pending_not_raw_task")
    canonical = read(cell / "canonical-input.json")
    require(canonical["initiate_payment_task_id"] == pending["id"]
            and canonical["shopping_context_id"] == pending["contextId"], "pending_canonical_binding")
    processor_id = pending["status"]["message"]["taskId"]
    merchant_rows = task_responses(rpc, "merchant_raw", pending["id"])
    processor_rows = task_responses(rpc, "processor_raw", processor_id)
    merchant = merchant_rows[-1]["response"]["result"]
    processor = processor_rows[-1]["response"]["result"] if processor_rows else {}
    mr, pr = receipts(merchant), receipts(processor)
    caller = read(cell / "caller-final-state.json")
    purchase = (merchant["status"]["state"] == "completed"
                and processor.get("status", {}).get("state") == "completed"
                and merchant["contextId"] == processor["contextId"] == pending["contextId"]
                and len(mr) == len(pr) == 1 and mr[0] == pr[0] == caller.get("payment_receipt"))
    delivery_count, receipt_digest = 0, None
    if purchase:
        leaf = canonical["payment_mandate_sdjwt"].rsplit("~~", 1)[-1].split("~", 1)[0]
        expected = base64.urlsafe_b64encode(hashlib.sha256(leaf.encode()).digest()).decode().rstrip("=")
        require(mr[0]["reference"] == expected and mr[0]["status"] == "Success", "receipt_reference_or_status")
        receipt_digest = hashlib.sha256(json.dumps(mr[0], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        deliveries = [row for row in rpc if row["stream"] == "credentials_raw"
                      and any(part.get("data", {}).get(RECEIPT) == mr[0]
                              for part in row["request"].get("params", {}).get("message", {}).get("parts", []))]
        delivery_count = len(deliveries)
        require(delivery_count == 1 and deliveries[0]["response"]["result"]["status"]["state"] == "completed",
                "receipt_not_delivered_once")
    outcome = read(cell / "application-outcome.json")
    invocations = read(cell / "source-tool-invocations.json")
    errors = [{key: row.get(key) for key in ("phase", "error_type", "reason")}
              for row in invocations if row.get("error_type") is not None]
    continuations = [row for row in rpc if row["stream"] == "merchant_raw"
                     and row["request"].get("method") == "message/send"
                     and texts(row["request"]["params"]["message"]) == [OTP]]
    rpc_errors = [{"stream": row["stream"], "exchange": row["exchange"], "error": row["response"]["error"]}
                  for row in rpc if "error" in row["response"]]
    worker = read(cell / "result.json")
    clean_purchase = (purchase and outcome["error_type"] is None and not errors and not rpc_errors
                      and execution["returncode"] == worker["returncode"] == 0)
    if case["human_response"] is None:
        require(not purchase and not continuations and outcome["supplied_otp_response"] is None, "absent_human_reply_not_preserved")
    if case["human_response"] == "000":
        require(not purchase and outcome["supplied_otp_response"] == "000", "wrong_human_reply_not_preserved")
    require(outcome["case_id"] == case["id"] and outcome["arm_id"] == arm["id"], "outcome_identity")
    return {"case_id": case["id"], "arm_id": arm["id"], "status": "numeric_raw_evidence_verified",
            "purchase_completed": purchase, "strict_error_free_owned_cell_purchase": clean_purchase,
            "merchant_task_state": merchant["status"]["state"], "processor_task_state": processor.get("status", {}).get("state"),
            "merchant_task_id": pending["id"], "processor_task_id": processor_id,
            "merchant_last_response_exchange": merchant_rows[-1]["exchange"],
            "processor_last_response_exchange": processor_rows[-1]["exchange"] if processor_rows else None,
            "merchant_receipt_count": len(mr), "processor_receipt_count": len(pr),
            "receipt_sha256": receipt_digest, "credential_receipt_deliveries": delivery_count,
            "raw_continuations": len(continuations), "actor_error_type": outcome["error_type"],
            "actor_error_reason": outcome["reason"], "source_errors": errors, "rpc_errors": rpc_errors,
            "worker_process_returncode": execution["returncode"], "durable_events": event_count,
            "raw_journal_identity": journal_identity,
            "full_original_ADK_task_success_established": False}


def compare(rows, cases, first, second, metric):
    lookup = {(row["case_id"], row["arm_id"]): row for row in rows}
    pairs = [{"case_id": case["id"], "first": int(lookup[case["id"], first][metric]),
              "second": int(lookup[case["id"], second][metric])} for case in cases]
    for pair in pairs:
        pair["difference"] = pair["first"] - pair["second"]
    delta = sum(pair["difference"] for pair in pairs)
    return {"first_arm": first, "second_arm": second, "metric": metric, "paired_cases": len(pairs),
            "sum_difference": delta, "mean_difference": delta / len(pairs),
            "first_only": sum(pair["difference"] == 1 for pair in pairs),
            "second_only": sum(pair["difference"] == -1 for pair in pairs),
            "equal": sum(pair["difference"] == 0 for pair in pairs), "pairs": pairs}


def audit(capture):
    matrix = capture / "matrix"
    public = read(matrix / "public-manifest.json")
    allocation = read(matrix / "allocation-manifest.json")
    execution = read(matrix / "execution-results.json")
    expected = [(case["id"], arm["id"]) for case in public["cases"] for arm in public["arms"]]
    require(len(set(expected)) == len(expected) == public["declared_cells"] == 65, "not_65_unique_cells")
    require(len(public["cases"]) == 13 and len(public["arms"]) == 5, "matrix_dimensions")
    require([(row["case_id"], row["arm_id"]) for row in allocation["cells"]] == expected
            == [(row["case_id"], row["arm_id"]) for row in execution["cells"]], "cartesian_allocation_execution_mismatch")
    require(identity((matrix / "public-manifest.json").read_bytes()) == allocation["public_manifest"], "manifest_allocation_identity")
    original = matrix / "cells" / (public["cases"][0]["id"] + "--" + public["arms"][0]["id"]) / "original-source"
    source_names = ["code/samples/python/src/roles/merchant_payment_processor_agent/tools.py",
                    "code/sdk/python/ap2/sdk/mandate.py",
                    "code/samples/python/src/roles/shopping_agent/tools.py"]
    sources = {name: (original / name).read_bytes() for name in source_names}
    require(b"return challenge_response == \"123\"" in sources[source_names[0]]
            and b"status='Success'" in sources[source_names[0]]
            and b"last_segment = presentation_token.rsplit('~~', 1)[-1]" in sources[source_names[1]]
            and b"return last_segment.split('~', 1)[0]" in sources[source_names[1]], "original_receipt_definition_not_reviewed_shape")
    cases = {case["id"]: case for case in public["cases"]}
    arms = {arm["id"]: arm for arm in public["arms"]}
    rows = []
    for process in execution["cells"]:
        case, arm = cases[process["case_id"]], arms[process["arm_id"]]
        cell = matrix / "cells" / (case["id"] + "--" + arm["id"])
        rows.append(assess(cell, case, arm, process))
    metrics = ["purchase_completed", "strict_error_free_owned_cell_purchase"]
    counts = {arm: {metric: sum(row[metric] for row in rows if row["arm_id"] == arm) for metric in metrics}
              for arm in arms}
    pairs = [compare(rows, public["cases"], first, second, metric)
             for first, second in (("shared", "recovery"), ("recovery_shared", "recovery"),
                                   ("shared", "conventional"), ("recovery_shared", "conventional"))
             for metric in metrics]
    summary = read(capture / "independent-evaluation/result.json")
    reported = {(row["case_id"], row["arm_id"]): row for row in summary["cells"]}
    disagreements = [{"case_id": row["case_id"], "arm_id": row["arm_id"],
                      "peer_purchase": row["purchase_completed"],
                      "first_evaluator_purchase": reported.get((row["case_id"], row["arm_id"]), {}).get("purchase_completed")}
                     for row in rows if reported.get((row["case_id"], row["arm_id"]), {}).get("purchase_completed") != row["purchase_completed"]]
    return {"schema_version": "ap2-v5-numeric-peer-review/1", "reviewed_utc": datetime.now(timezone.utc).isoformat(),
            "status": "independent_numeric_raw_evidence_verified" if not disagreements else "numeric_disagreement",
            "capture": str(capture), "audit_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "public_manifest_identity": identity((matrix / "public-manifest.json").read_bytes()),
            "reviewed_original_source": {name: identity(raw) for name, raw in sources.items()},
            "declared_cells": 65, "reviewed_cells": len(rows), "case_count": len(cases), "arm_count": len(arms),
            "arm_counts": counts, "total_verified_purchases": sum(row["purchase_completed"] for row in rows),
            "total_strict_error_free_owned_cell_purchases": sum(row["strict_error_free_owned_cell_purchase"] for row in rows),
            "purchases_with_retained_suffix_errors": [row for row in rows if row["purchase_completed"] and not row["strict_error_free_owned_cell_purchase"]],
            "paired_comparisons": pairs, "first_evaluator_purchase_disagreements": disagreements, "cells": rows,
            "limits": ["One deterministic exposed 13-case development matrix, not independent held-out human gold.",
                       "Offline tool choice, fixtures, original SDK task stores and owned in-process ASGI; provider quality and full ADK shopper tasks are not measured.",
                       "A completed purchase can precede a real suffix error. Error-free owned cell purchase is separate and does not establish unconditional full original task success.",
                       "Shared admission has adverse paired purchase utility versus public recovery in this declared matrix; do not omit the negative cases.",
                       "This peer audits numerical raw outcome evidence; source staging, gate, certificate and digest coherence are separately reviewed by the parent."]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    capture, output = args.capture.resolve(), args.output.resolve()
    require(output != capture and capture not in output.parents, "output_must_be_outside_capture")
    require(not output.exists(), "output_already_exists")
    result = audit(capture)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps({key: result[key] for key in ("status", "reviewed_cells", "arm_counts", "total_verified_purchases", "total_strict_error_free_owned_cell_purchases")}, sort_keys=True))
    return 0 if not result["first_evaluator_purchase_disagreements"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
