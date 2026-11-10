"""Independently correlate a retained completed AP2 offline application capture."""
import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_ap2_v4_capture_base import audit


def untag(value, depth=0):
    assert type(value) is dict and depth <= 80
    kind = value["type"]
    if kind == "none":
        assert set(value) == {"type"}
        return None
    if kind in {"str", "bool", "int", "float"}:
        assert set(value) == {"type", "value"}
        if kind == "str":
            assert type(value["value"]) is str
            return value["value"]
        if kind == "bool":
            assert type(value["value"]) is bool
            return value["value"]
        if kind == "int":
            number = int(value["value"])
            assert str(number) == value["value"]
            return number
        number = float.fromhex(value["value"])
        assert math.isfinite(number) and number.hex() == value["value"]
        return number
    if kind == "bytes":
        assert set(value) == {"type", "value", "bytes", "sha256"}
        raw = base64.b64decode(value["value"], validate=True)
        assert len(raw) == value["bytes"] and hashlib.sha256(raw).hexdigest() == value["sha256"]
        return raw
    if kind in {"tuple", "list"}:
        assert set(value) == {"type", "items"}
        result = [untag(child, depth + 1) for child in value["items"]]
        return tuple(result) if kind == "tuple" else result
    assert kind == "dict" and set(value) == {"type", "entries"}
    result = {}
    for key, child in value["entries"]:
        key = untag(key, depth + 1)
        assert key not in result
        result[key] = untag(child, depth + 1)
    return result


def complete(capture):
    capture = Path(capture).resolve()
    value = audit(capture, expected_returncode=0)
    app = capture / "application"
    load = lambda name: json.loads((app / name).read_bytes())
    reference, state = load("reference-result.json"), load("caller-final-state.json")
    assert reference["status"] == "public_sequence_observed" and reference["phase"] == "finished"
    phases = [row["phase"] for row in reference["planning_report"]["observations"]]
    assert phases == ["catalog", "cart_selection", "shipping", "payment_methods", "payment_selection", "credential_token",
                      "checkout", "approval", "checkout_mandate", "payment_mandate", "cp_association", "payment_start", "otp_response", "payment_resume"]
    receipt = state["payment_receipt"]
    assert receipt["status"] == "Success" and receipt["error"] is None
    assert receipt["payment_id"] == receipt["psp_confirmation_id"] == receipt["network_confirmation_id"]
    token = state["payment_mandate_sdjwt"]
    assert "~~" not in token, "This audit only implements the observed single-root SD-JWT reference"
    reference_hash = base64.urlsafe_b64encode(hashlib.sha256(token.split("~", 1)[0].encode("ascii")).digest()).decode("ascii").rstrip("=")
    assert receipt["reference"] == reference_hash
    events = [json.loads(line) for line in (app / "observations/events.jsonl").read_bytes().splitlines()]
    decoded = [(row["stream"], row["source_index"], untag(row["payload"])) for row in events]
    public = [payload for stream, _, payload in decoded if stream.endswith("_public")]
    records = reference["public_records"]
    assert [{key: child for key, child in row.items() if key != "global_sequence"} for row in records] == public
    assert [row["global_sequence"] for row in records] == list(range(len(records)))
    for stream in {stream for stream, _, _ in decoded}:
        subset = [(index, payload) for name, index, payload in decoded if name == stream]
        assert [index for index, _ in subset] == list(range(len(subset)))
    merchant_records = [row for row in records if row["endpoint"] == "http://localhost:8001/a2a/merchant_agent"]
    start = next(row["public_value"] for row in merchant_records if row["call"] == 2 and row["boundary"] == "returned")
    resume_request = next(row["public_value"] for row in merchant_records if row["call"] == 3 and row["boundary"] == "attempt")
    resumed = next(row["public_value"] for row in merchant_records if row["call"] == 3 and row["boundary"] == "returned")
    assert start["status"]["state"] == "input-required" and resumed["status"]["state"] == "completed"
    assert start["id"] == resume_request["taskId"] == resumed["id"] == state["initiate_payment_task_id"]
    assert start["contextId"] == resume_request["contextId"] == resumed["contextId"] == state["shopping_context_id"]

    def all_receipts(obj):
        found = []
        if isinstance(obj, dict):
            if obj.get("status") == "Success" and "reference" in obj and "payment_id" in obj:
                found.append(obj)
            for child in obj.values():
                found.extend(all_receipts(child))
        elif isinstance(obj, list):
            for child in obj:
                found.extend(all_receipts(child))
        return found

    assert receipt in all_receipts(resumed.get("artifacts"))
    exchanges = {}
    for stream, _, row in decoded:
        if not stream.endswith("_raw"):
            continue
        exchange = exchanges.setdefault((stream, row["exchange"]), {"request": [], "response": []})
        if row["boundary"] == "scope":
            exchange["scope"] = row["value"]
        if row["boundary"] == "receive_returned" and row["value"].get("type") == "http.request":
            exchange["request"].append(row["value"].get("body", b""))
        if row["boundary"] == "send_completed" and row["value"].get("type") == "http.response.body":
            exchange["response"].append(row["value"].get("body", b""))
    wire = []
    for (stream, index), exchange in exchanges.items():
        request_raw, response_raw = b"".join(exchange["request"]), b"".join(exchange["response"])
        wire.append({"stream": stream, "exchange": index, "method": exchange["scope"]["method"],
                     "request": json.loads(request_raw) if request_raw else None,
                     "response": json.loads(response_raw) if response_raw else None})
    processor = [row for row in wire if row["stream"] == "processor_raw" and row["method"] == "POST"]
    assert len(processor) == 2
    first_task, last_task = processor[0]["response"]["result"], processor[1]["response"]["result"]
    resumed_message = processor[1]["request"]["params"]["message"]
    assert first_task["status"]["state"] == "input-required" and last_task["status"]["state"] == "completed"
    assert first_task["id"] == resumed_message["taskId"] == last_task["id"]
    assert first_task["contextId"] == resumed_message["contextId"] == last_task["contextId"] == state["shopping_context_id"]
    assert receipt in all_receipts(last_task.get("artifacts"))
    wire_receipts = [row for row in wire if receipt in all_receipts(row["request"]) or receipt in all_receipts(row["response"])]
    assert {row["stream"] for row in wire_receipts} == {"merchant_raw", "processor_raw", "credentials_raw"}
    cleanup = load("cleanup.json")
    value.update(schema_version="ap2-v4-completed-offline-capture-independent-audit/1",
                 status="completed_offline_original_app_sequence_independently_verified",
                 actual_original_application_returncode=0, original_reference_phases_verified=14,
                 fresh_buyer_root_signature_and_disclosure_checks=True,
                 public_caller_records_exactly_match_durable_journal=True,
                 merchant_original_task_resumed_to_completed=True, processor_original_task_resumed_to_completed=True,
                 task_context_correlation={"merchant_task_id": start["id"], "processor_task_id": first_task["id"],
                                           "context_id": state["shopping_context_id"]},
                 actual_receipt_exact_in_final_caller_merchant_processor_and_credentials_bytes=True,
                 receipt_reference_freshly_recomputed_from_closed_mandate_JWT=True,
                 payment_receipt_sha256=hashlib.sha256(json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                 closed_clients=cleanup["client_count"], payment_receipt_observed=True,
                 full_application_task_pass=False,
                 scope="One actual original-app/SDK/caller offline reference sequence with fixture/ASGI/controller interventions; original ADK shopper/native provider/independent held-out task qualification not established")
    return value


def admitted(capture, value):
    """Independent arithmetic/byte correlation; does not import the gate adapter."""
    from copy import deepcopy
    capture = Path(capture).resolve()
    app = capture / "application"
    gate = app / "admission"
    load = lambda name: json.loads((gate / name).read_bytes())
    prepared, profile = load("pending-input.json"), load("profile.json")
    receipt, result, dispatch = load("admission-before-send.json"), load("solver-result.json"), load("raw-dispatch.json")
    observed, boundary = load("observed-continuation.json"), load("boundary-result.json")
    encoded = lambda item: json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    digest = lambda item: hashlib.sha256(encoded(item)).hexdigest()
    assert prepared["profile"] == profile and receipt["solver_result"] == result
    assert receipt["status"] == "positive_finite_model_admission_checked" and receipt["decision"] == result["decision"] == "supported"
    assert receipt["certificate_valid"] is True and receipt["dispatch_permitted"] is True
    assert receipt["work_budget"] == 100000 and result["stats"]["work_units"] <= 100000
    assert profile["model"]["horizon"] == 1 and profile["model"]["evidence"]["complete"] is False and profile["coverage"]["complete"] is False
    assert receipt["profile_sha256"] == dispatch["profile_sha256"] == digest(profile)
    assert receipt["input_sha256"] == dispatch["input_sha256"] == digest(prepared)
    assert receipt["original_request_sha256"] == dispatch["original_request_sha256"] == digest(prepared["original_request"])
    assert receipt["evaluation_clock"] == dispatch["certificate_checked_at"] == profile["model"]["evidence"]["observed_at"]
    assert receipt["evaluation_clock"] <= dispatch["checked_at"] <= receipt["valid_until"] == profile["model"]["evidence"]["valid_until"]
    assert result["certificate"]["kind"] == "recipe-path" and len(result["certificate"]["steps"]) == 1
    step = result["certificate"]["steps"][0]
    assert step["request"] == prepared["original_request"]
    sys.path.insert(0, str(ROOT / "src"))
    from interoperability import refinement_oracle
    assert refinement_oracle.check_certificate(deepcopy(profile), deepcopy(result), receipt["evaluation_clock"]) is True
    assert refinement_oracle.check_certificate(deepcopy(profile), deepcopy(result), dispatch["checked_at"]) is True
    altered = deepcopy(result)
    altered["certificate"]["steps"][0]["request"]["message"]["taskId"] = "unrelated-certificate-task"
    assert refinement_oracle.check_certificate(deepcopy(profile), altered, receipt["evaluation_clock"]) is False
    assert refinement_oracle.check_certificate(deepcopy(profile), deepcopy(result), receipt["valid_until"] + 1) is False
    for name, expected in dispatch["admission_artifacts"].items():
        raw = (gate / name).read_bytes()
        assert expected == {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    journal_raw = (app / "observations/events.jsonl").read_bytes()
    events = [json.loads(line) for line in journal_raw.splitlines()]
    for checkpoint in (receipt["journal_checkpoint_before_admission"], dispatch["journal_checkpoint_before_dispatch"]):
        prefix = journal_raw[:checkpoint["bytes"]]
        assert hashlib.sha256(prefix).hexdigest() == checkpoint["sha256"] and prefix.endswith(b"\n")
        prefix_events = [json.loads(line) for line in prefix.splitlines()]
        assert len(prefix_events) == checkpoint["events"] and prefix_events == events[:checkpoint["events"]]
    before = receipt["journal_checkpoint_before_admission"]
    predispatch = dispatch["journal_checkpoint_before_dispatch"]
    assert before["events"] <= predispatch["events"] < len(events)
    exchanges = {}
    for event in events:
        if not event["stream"].endswith("_raw"):
            continue
        row = untag(event["payload"])
        exchange = exchanges.setdefault((event["stream"], row["exchange"]), {"request": b"", "response": b"", "first": event["global_index"]})
        if row["boundary"] == "scope":
            exchange["scope"] = row["value"]
        elif row["boundary"] == "receive_returned" and row["value"].get("type") == "http.request":
            exchange["request"] += row["value"].get("body", b"")
            exchange["request_index"] = event["global_index"]
        elif row["boundary"] == "send_completed" and row["value"].get("type") == "http.response.body":
            exchange["response"] += row["value"].get("body", b"")
        elif row["boundary"] == "application_returned":
            exchange["closed"] = event["global_index"]
    bound = receipt["pending_raw_binding"]
    pending = exchanges[bound["stream"], bound["exchange"]]
    pending_result = json.loads(pending["response"])["result"]
    assert pending["closed"] == bound["closed_at_global_index"] < before["events"]
    assert pending["first"] == bound["first_global_index"]
    assert hashlib.sha256(pending["request"]).hexdigest() == bound["request_bytes_sha256"]
    assert hashlib.sha256(pending["response"]).hexdigest() == bound["response_bytes_sha256"]
    task = prepared["pending_task"]
    assert pending_result["id"] == task["id"] == bound["original_merchant_task_id"]
    assert pending_result["contextId"] == task["contextId"] == bound["original_context_id"]
    assert pending_result["status"]["state"] == task["status"]["state"] == "input-required"
    assert digest(task) == bound["public_pending_task_sha256"]
    def omit_optional_nulls(message):
        message = deepcopy(message)
        for field in ("metadata", "extensions", "referenceTaskIds", "taskId", "contextId"):
            if message.get(field, False) is None:
                del message[field]
        for part in message["parts"]:
            if part.get("metadata", False) is None:
                del part["metadata"]
        return message
    assert omit_optional_nulls(pending_result["status"]["message"]) == omit_optional_nulls(task["status"]["message"])
    matches = []
    for key, exchange in exchanges.items():
        if key[0] != "merchant_raw" or exchange.get("scope", {}).get("method") != "POST":
            continue
        request = json.loads(exchange["request"])
        if request.get("params", {}).get("message", {}).get("taskId") == task["id"]:
            matches.append((key, exchange, request, json.loads(exchange["response"])))
    assert len(matches) == 1
    key, actual, request, response = matches[0]
    assert actual["request_index"] >= predispatch["events"]
    assert dispatch["raw_request"] == {"bytes": len(actual["request"]), "sha256": hashlib.sha256(actual["request"]).hexdigest()}
    assert request["jsonrpc"] == response["jsonrpc"] == "2.0" and request["id"] == response["id"] == dispatch["actual_rpc_id"]
    assert request["method"] == dispatch["actual_rpc_method"] == "message/send"
    assert omit_optional_nulls(request["params"]["message"]) == omit_optional_nulls(step["request"]["message"])
    assert request["params"]["message"]["taskId"] == dispatch["original_merchant_task_id"] == task["id"]
    assert request["params"]["message"]["contextId"] == dispatch["original_context_id"] == task["contextId"]
    assert response["result"]["id"] == task["id"] and response["result"]["status"]["state"] == "completed"
    assert boundary["admission_attempted"] and boundary["original_continuation_dispatched"] and boundary["checked_witness_bound_to_observed_original_completion"]
    assert observed["actual_original_task_completed"] is True
    assert boundary["aggregate_task_grade"] is None and boundary["native_qualification_established"] is False
    assert receipt["actual_task_completion_established_by_certificate"] is False
    value.update(status="completed_offline_original_app_admitted_sequence_independently_verified",
                 fresh_positive_certificate_checks_at_admission_and_dispatch=True,
                 certificate_tamper_and_expired_clock_controls_rejected=True,
                 actual_pending_raw_reply_precedes_bound_admission_journal_prefix=True,
                 immutable_admission_artifacts_match_pre_send_receipt=True,
                 actual_single_original_resume_raw_bytes_match_certified_builder=True,
                 exact_bound_original_merchant_task_observed_completed=True,
                 admission_evaluation_clock=receipt["evaluation_clock"], admission_dispatch_clock=dispatch["checked_at"],
                 admission_work_units=result["stats"]["work_units"], positive_certificate_bytes=len(encoded(result["certificate"])),
                 actual_resume_raw_request_sha256=dispatch["raw_request"]["sha256"],
                 admission_scope="Conditional one-step finite public demo continuation; incomplete coverage; actual outcome checked separately; no whole-interface closure, native provider or independent gold qualification")
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    value = complete(options.capture)
    value = admitted(options.capture, value)
    with options.output.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
    print(json.dumps({key: value[key] for key in ("status", "run_id", "original_reference_phases_verified", "durable_events_checked", "closed_clients")}, indent=2))
