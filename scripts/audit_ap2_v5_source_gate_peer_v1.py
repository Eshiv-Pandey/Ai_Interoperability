"""Read-only peer audit of AP2 v5 source, task and admission evidence.

The existing bounded durable-format decoder and the unchanged generic finite
certificate checker are reused explicitly. No actor, original application,
ADK/SDK module, provider or admission-profile module is imported or executed.
Business/source bindings, prefix integrity and relation predicates below are
independently reconstructed rather than calling the application evaluator.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SHA = "52138f417843e785d29344ae95e36c735ae8470a2ca6945c40c169bf2f3ac6d3"
STAGE_SHA = "78828cea09bdd387230a2fc0772b542beabfe07b72c3a2f24b24c02c1a2f4463"
PAYMENT = "ap2.mandates.PaymentMandateSdJwt"
CHECKOUT = "ap2.mandates.CheckoutMandateSdJwt"
OTP = "Initiate a payment. Include the challenge response."
MERCHANT = "http://localhost:8001/a2a/merchant_agent"


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def byte_identity(raw):
    return {"bytes": len(raw), "sha256": sha(raw)}


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode()


def non_null(value):
    if isinstance(value, dict):
        return {key: non_null(child) for key, child in value.items() if child is not None}
    if isinstance(value, list):
        return [non_null(child) for child in value]
    return value


def helper():
    path = ROOT / "scripts/evaluate_ap2_application_matrix_v5.py"
    spec = importlib.util.spec_from_file_location("_ap2_v5_peer_durable_decoder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, byte_identity(path.read_bytes())


def data_parts(message):
    return [part["data"] for part in message.get("parts", []) if part.get("kind") == "data"]


def mandate_hashes(canonical):
    """Follow disclosure digests from the signed root, never from an orphan."""
    def b64(value):
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    def encoded_hash(value):
        return base64.urlsafe_b64encode(hashlib.sha256(value.encode()).digest()).decode().rstrip("=")
    def anchors(value):
        result = set()
        if isinstance(value, dict):
            result.update(value.get("_sd", []))
            if "..." in value:
                result.add(value["..."])
            for child in value.values():
                result.update(anchors(child))
        elif isinstance(value, list):
            for child in value:
                result.update(anchors(child))
        return result
    delegates, rows = {}, []
    for field, vct in (("checkout_mandate_sdjwt", "mandate.checkout.1"),
                       ("payment_mandate_sdjwt", "mandate.payment.1")):
        token = canonical[field]
        parts = token.split("~")
        header, payload, signature = parts[0].split(".")
        require(json.loads(b64(header))["alg"] == "ES256" and len(b64(signature)) == 64,
                "buyer_root_signature_structure")
        root = json.loads(b64(payload))
        require(root.get("_sd_alg") == "sha-256", "unsupported_disclosure_hash")
        pending = {encoded_hash(part): json.loads(b64(part)) for part in parts[1:] if part}
        require(len(pending) == len([part for part in parts[1:] if part]), "duplicate_disclosure")
        allowed, decoded = anchors(root), []
        while pending:
            reached = [key for key in pending if key in allowed]
            require(reached, "disclosure_not_transitively_root_anchored")
            for key in reached:
                disclosure = pending.pop(key)
                require(isinstance(disclosure, list) and len(disclosure) in (2, 3), "disclosure_shape")
                decoded.append(disclosure)
                allowed.update(anchors(disclosure[1:]))
        delegate = [row[1] for row in decoded if len(row) == 2 and isinstance(row[1], dict)
                    and row[1].get("vct") == vct]
        require(len(delegate) == 1, "unique_mandate_delegate")
        delegates[field] = delegate[0]
        rows.append({"field": field, "token_sha256": sha(token.encode()),
                     "root_anchored_disclosures": len(decoded), "signature_reverified_here": False})
    require(delegates["checkout_mandate_sdjwt"]["checkout_hash"] == canonical["checkout_hash"]
            == delegates["payment_mandate_sdjwt"]["transaction_id"], "mandate_checkout_transaction_link")
    require(encoded_hash(canonical["checkout_data"]["checkout_jwt"]) == canonical["checkout_hash"],
            "merchant_checkout_hash_link")
    return rows


def expected_message(pending, canonical, message_id):
    return {"kind": "message", "role": "agent", "messageId": message_id,
            "taskId": pending["id"], "contextId": pending["contextId"],
            "parts": [{"kind": "text", "text": OTP}] +
            [{"kind": "data", "data": {key: value}} for key, value in
             ((PAYMENT, canonical["payment_mandate_sdjwt"]), ("shopping_agent_id", "trusted_shopping_agent"),
              ("challenge_response", "123"), ("risk_data", canonical["risk_data"]),
              (CHECKOUT, canonical["checkout_mandate_sdjwt"]))]}


def expression(value, bindings, emitted):
    """Independent evaluation of the limited retained relation expression."""
    require(isinstance(value, dict) and len(value) == 1, "relation_expression_shape")
    key, child = next(iter(value.items()))
    if key == "const":
        return child
    if key == "binding":
        return bindings[child]
    if key == "object":
        return {name: expression(item, bindings, emitted) for name, item in child.items()}
    if key == "array":
        return [expression(item, bindings, emitted) for item in child]
    require(key == "emit_path", "unmodeled_relation_operator")
    result = emitted
    for name in child:
        result = result[name]
    return result


def verify_prefix(h, raw, events, checkpoint):
    pieces = raw.splitlines(keepends=True)
    require(0 <= checkpoint["events"] <= len(pieces), "prefix_event_count")
    prefix = b"".join(pieces[:checkpoint["events"]])
    require(byte_identity(prefix) == {"bytes": checkpoint["bytes"], "sha256": checkpoint["sha256"]},
            "exact_durable_admission_prefix")
    sequences, opened = {}, set()
    for event in events[:checkpoint["events"]]:
        row = h.decode_tag(event["payload"])
        sequences[event["stream"]] = event["source_index"] + 1
        if not event["stream"].endswith("_raw"):
            continue
        identity = (event["stream"], row["exchange"])
        if row["boundary"] == "scope":
            require(identity not in opened, "raw_scope_reopened")
            opened.add(identity)
        elif row["boundary"] == "application_returned":
            require(identity in opened, "raw_close_without_scope")
            opened.remove(identity)
    require(sequences == checkpoint["next_source_indices"] and not opened,
            "admission_prefix_sequences_or_raw_quiescence")


def source_pins(h, cell, plan):
    stage_raw = (cell / "source-stage-manifest.json").read_bytes()
    require(sha(stage_raw) == STAGE_SHA == plan["source_manifest_sha256"], "original_manifest_pin")
    expected = {row["path"]: {"bytes": row["bytes"], "sha256": row["sha256"]}
                for row in h.read(cell / "source-stage-manifest.json")["files"] if row["project"] == "ap2"}
    actual = {path.relative_to(cell / "original-source").as_posix(): byte_identity(path.read_bytes())
              for path in (cell / "original-source").rglob("*") if path.is_file()}
    require(len(expected) == 136 and actual == expected, "all_original_file_pins")
    for name, identity in plan["owned_components"].items():
        require(byte_identity((cell / "owned-source" / name).read_bytes()) == identity,
                "owned_source_digest:" + name)
    require(byte_identity((cell / "source-runner.py").read_bytes()) ==
            plan["owned_components"]["scripts/ap2_reference_development_v5.py"], "owned_runner_digest")
    require(byte_identity((cell / "public-matrix-manifest.json").read_bytes()) == plan["public_matrix_manifest"]
            and plan["public_matrix_manifest"]["sha256"] == PUBLIC_SHA, "per_cell_public_manifest")
    checks = h.read(cell / "original-callable-code-checks.json")
    require(len(checks) == 64 and all(row["full_structural_code_equal"] is True
            and row["actual_fingerprint_sha256"] == row["expected_fingerprint_sha256"] for row in checks),
            "retained_callable_attestation_inconsistent")
    names = {(row["module"], row["qualified_name"]) for row in checks}
    require(all(("roles.shopping_agent.tools", name) in names for name in
                ("initiate_payment", "initiate_payment_with_otp")), "shopper_tool_attestation_missing")
    return {"original_files_rehashed": len(actual), "owned_files_rehashed": len(plan["owned_components"]),
            "retained_callable_attestations": len(checks), "callable_code_reexecuted_here": False}


def audit_gate(h, cell, case, arm, raw, events, public, rpc, start, canonical):
    pending = start["response"]["result"]
    rows = []
    for number, base in enumerate(sorted((cell / "admission").glob("attempt-*"))):
        attempt = h.read(base / "attempt.json")
        require(attempt["index"] == number and attempt["whole_route_non_support_inference_allowed"] is False,
                "admission_attempt_identity")
        sender = attempt["original_sender_message"]
        require(sum(row.get("public_value") == sender and row["boundary"] == "attempt"
                    and row["endpoint"] == MERCHANT for row in public) == 1, "sender_not_unique_public_attempt")
        row = {"attempt": base.name, "dispatched": False}
        if (base / "pending-input.json").exists():
            prepared, model, result, receipt = [h.read(base / name) for name in
                ("pending-input.json", "profile.json", "solver-result.json", "admission-before-send.json")]
            require(prepared["profile"] == model and receipt["solver_result"] == result
                    and sha(canonical_bytes(prepared)) == receipt["input_sha256"]
                    and sha(canonical_bytes(model)) == receipt["profile_sha256"], "gate_artifact_digest_binding")
            require(prepared["canonical_caller"] == canonical
                    and non_null(prepared["pending_task"]) == non_null(pending), "gate_full_pending_source_binding")
            require(model["coverage"]["complete"] is False and model["model"]["evidence"]["complete"] is False
                    and prepared["observed_task_completion"] is False
                    and receipt["actual_task_completion_established_by_certificate"] is False
                    and receipt["whole_route_non_support_inference_allowed"] is False, "finite_claim_limits")
            checkpoint = receipt["journal_checkpoint_before_admission"]
            verify_prefix(h, raw, events, checkpoint)
            require(receipt["pending_raw_binding"] == {
                "stream": start["stream"], "exchange": start["exchange"],
                "first_global_index": start["first_global_index"], "closed_at_global_index": start["closed_at_global_index"],
                "response_bytes_sha256": sha(start["response_bytes"]), "task_id": pending["id"],
                "context_id": pending["contextId"]}, "exact_pending_raw_binding")
            require(start["closed_at_global_index"] < checkpoint["events"], "pending_not_before_gate")
            received = prepared["original_request"]["message"]
            source_expected = expected_message(pending, canonical, received["messageId"])
            associated = any(x["stream"] == "credentials_raw"
                and h.texts(x["request"].get("params", {}).get("message", {})) == ["This is the signed payment mandate"]
                and x["request"]["params"]["message"].get("contextId") == pending["contextId"]
                and {PAYMENT: canonical["payment_mandate_sdjwt"]} in data_parts(x["request"]["params"]["message"])
                and x["response"].get("result", {}).get("status", {}).get("state") == "completed"
                and x["closed_at_global_index"] < checkpoint["events"] for x in rpc)
            bindings = {"merchant_task_id": pending["id"], "shopping_context_id": pending["contextId"],
                "original_message_id": received["messageId"], "payment_mandate_sdjwt": canonical["payment_mandate_sdjwt"],
                "checkout_mandate_sdjwt": canonical["checkout_mandate_sdjwt"], "risk_data": canonical["risk_data"],
                "public_demo_response": "123", "credential_association_completed": associated}
            require(model["initial_bindings"] == bindings and prepared["association_completed"] == associated,
                    "source_observation_bindings")
            relation = model["relations"]["actual_original_tool_received_otp_continuation"]
            emitted = expression(relation["emit"], bindings, None)
            require(emitted == prepared["original_request"], "relation_emit_not_received_request")
            guards = relation["guards"]
            require(len(guards) == 2 and all(guard["op"] == "eq" for guard in guards), "source_guard_shape")
            require(expression(guards[0]["right"], bindings, emitted) == source_expected
                    and expression(guards[0]["left"], bindings, emitted) == received
                    and expression(guards[1]["left"], bindings, emitted) is associated
                    and expression(guards[1]["right"], bindings, emitted) is True, "source_guard_semantics")
            guard_supported = associated and received == source_expected
            require(result["decision"] == ("supported" if guard_supported else "unknown"), "independent_guard_decision")
            evidence = model["model"]["evidence"]
            require(evidence["observed_at"] == receipt["evaluation_clock"]
                    and evidence["valid_until"] == receipt["valid_until"]
                    and evidence["valid_until"] - evidence["observed_at"] == case.get("certificate_valid_for_seconds", 15),
                    "declared_finite_freshness_interval")
            checker = h.generic_checker(cell)
            if guard_supported:
                require(checker.check_certificate(deepcopy(model), deepcopy(result), receipt["evaluation_clock"]),
                        "positive_certificate_recheck")
            else:
                require(result.get("certificate") is None and receipt["dispatch_permitted"] is False
                        and checker.evaluate(deepcopy(model), receipt["evaluation_clock"], budget=100000)["decision"] == "unknown",
                        "unknown_without_certificate_or_dispatch")
            row.update(decision=result["decision"], evaluation_clock=receipt["evaluation_clock"],
                       valid_until=receipt["valid_until"], relation_guards_independently_reconstructed=True)
            if case["id"] == "recipient_mandate_loss":
                require(PAYMENT in {k for part in data_parts(sender) for k in part}
                        and PAYMENT not in {k for part in data_parts(received) for k in part}, "recipient_fault_sender_receiver_split")
            else:
                require(non_null(sender) == non_null(received), "unexpected_sender_receiver_difference")
            if (base / "raw-dispatch.json").exists():
                dispatch = h.read(base / "raw-dispatch.json")
                candidates = [x for x in rpc if byte_identity(x["request_bytes"]) == dispatch["raw_request"]]
                require(len(candidates) == 1, "unique_digest_bound_dispatch")
                x = candidates[0]
                require(x["stream"] == "merchant_raw" and x["first_global_index"] >= checkpoint["events"]
                        and x["request"]["id"] == dispatch["actual_rpc_id"]
                        and non_null(x["request"]["params"]["message"]) == non_null(received), "raw_dispatch_rpc_and_message")
                require(dispatch["raw_request"] == attempt["raw_received_request"]
                        and dispatch["journal_checkpoint_before_dispatch"] == checkpoint
                        and dispatch["input_sha256"] == receipt["input_sha256"]
                        and dispatch["profile_sha256"] == receipt["profile_sha256"]
                        and dispatch["original_message_id"] == received["messageId"]
                        and dispatch["original_merchant_task_id"] == pending["id"]
                        and dispatch["original_context_id"] == pending["contextId"]
                        and dispatch["valid_until"] == receipt["valid_until"]
                        and dispatch["evaluation_clock"] == receipt["evaluation_clock"]
                        and dispatch["independent_checker_rechecked_at_dispatch"] is True
                        and dispatch["actual_task_completion_established_by_certificate"] is False, "complete_dispatch_receipt_binding")
                require(result["decision"] == "supported"
                        and checker.check_certificate(deepcopy(model), deepcopy(result), dispatch["checked_at"])
                        and result["certificate"]["steps"][0]["request"] == prepared["original_request"],
                        "fresh_certificate_actual_received_message")
                row.update(dispatched=True, dispatch_clock=dispatch["checked_at"], rpc_id=dispatch["actual_rpc_id"])
            if case["id"] == "stale_certificate":
                require(result["decision"] == "supported" and not row["dispatched"]
                        and (base / "refusal.json").exists()
                        and not checker.check_certificate(deepcopy(model), deepcopy(result), receipt["valid_until"] + 1),
                        "expired_supported_case_refused_before_handler")
                row["expired_supported_case_preserved"] = True
        else:
            require(case["id"] == "duplicate_continuation" and number == 1
                    and rows[0]["dispatched"] and (base / "refusal.json").exists(), "unmodeled_pre_solver_refusal")
        if (base / "refusal.json").exists():
            refusal = h.read(base / "refusal.json")
            require(refusal["original_raw_continuation_dispatched"] is False, "refusal_dispatched")
            row.update(refusal_type=refusal["error_type"], refusal_reason=refusal["reason"])
        rows.append(row)
    continuations = [x for x in rpc if x["stream"] == "merchant_raw"
                     and h.texts(x["request"].get("params", {}).get("message", {})) == [OTP]]
    require(not rows if not arm["shared_admission"] else len(continuations) == sum(x["dispatched"] for x in rows),
            "continuation_admission_denominator")
    return rows


def audit_cell(h, cell, case, arm):
    plan = h.read(cell / "plan.json")
    require(plan["case"] == case and plan["policy"] == arm and plan["provider_requests_allowed"] == 0,
            "declared_case_arm")
    sources = source_pins(h, cell, plan)
    raw, events, public, rpc = h.journal(cell)
    starts = [x for x in rpc if x["stream"] == "merchant_raw" and x["request"]["method"] == "message/send"
              and h.texts(x["request"]["params"]["message"]) == ["Initiate a payment"]
              and not x["request"]["params"]["message"].get("taskId")]
    require(len(starts) == 1, "unique_original_start")
    start, canonical = starts[0], h.read(cell / "canonical-input.json")
    pending = start["response"]["result"]
    require(pending["status"]["state"] == "input-required"
            and canonical["initiate_payment_task_id"] == pending["id"]
            and canonical["shopping_context_id"] == pending["contextId"], "canonical_start_task_authority")
    require(non_null(h.read(cell / "payment-start-task.json")) == non_null(pending), "retained_start_task_raw_equality")
    prefix = h.read(cell / "prefix-observations.json")["caller_state"]
    for field in ("payment_mandate_sdjwt", "checkout_mandate_sdjwt", "risk_data", "checkout_data", "checkout_hash"):
        require(prefix[field] == canonical[field], "canonical_original_prefix:" + field)
    processor_id = pending["status"]["message"]["taskId"]
    nested = [x for x in rpc if x["stream"] == "processor_raw"
              and x["response"].get("result", {}).get("id") == processor_id
              and not x["request"].get("params", {}).get("message", {}).get("taskId")]
    require(len(nested) == 1 and nested[0]["response"]["result"]["contextId"] == pending["contextId"]
            and nested[0]["response"]["result"]["status"]["state"] == "input-required", "unique_nested_processor_task")
    recovery = [x for x in rpc if x["request"]["method"] == "tasks/get"]
    require(len(recovery) == (1 if arm["recover"] else 0)
            and all(x["request"]["params"]["id"] == x["response"]["result"]["id"] == pending["id"] for x in recovery),
            "legal_recovery_original_task_read")
    admissions = audit_gate(h, cell, case, arm, raw, events, public, rpc, start, canonical)
    merchant = [x for x in rpc if x["stream"] == "merchant_raw" and x["response"].get("result", {}).get("id") == pending["id"]][-1]
    processor = [x for x in rpc if x["stream"] == "processor_raw" and x["response"].get("result", {}).get("id") == processor_id][-1]
    mt, pt = merchant["response"]["result"], processor["response"]["result"]
    mr, pr = h.receipts(mt), h.receipts(pt)
    purchase = mt["status"]["state"] == pt["status"]["state"] == "completed" and len(mr) == len(pr) == 1
    receipt_row = None
    if purchase:
        require(mt["contextId"] == pt["contextId"] == pending["contextId"]
                and mr[0] == pr[0] == h.read(cell / "caller-final-state.json").get("payment_receipt"), "same_task_receipt_link")
        closed_jwt = canonical["payment_mandate_sdjwt"].rsplit("~~", 1)[-1].split("~", 1)[0]
        receipt_reference = base64.urlsafe_b64encode(hashlib.sha256(closed_jwt.encode()).digest()).decode().rstrip("=")
        receipt = mr[0]
        require(receipt["reference"] == receipt_reference and receipt["status"] == "Success"
                and receipt["payment_id"] == receipt["psp_confirmation_id"] == receipt["network_confirmation_id"],
                "mandate_reference_and_confirmation_ids")
        delivery = [x for x in rpc if x["stream"] == "credentials_raw"
                    and {"ap2.PaymentReceipt": receipt} in data_parts(x["request"].get("params", {}).get("message", {}))]
        require(len(delivery) == 1 and delivery[0]["request"]["params"]["message"]["contextId"] == pending["contextId"]
                and delivery[0]["response"]["result"]["contextId"] == pending["contextId"]
                and delivery[0]["response"]["result"]["status"]["state"] == "completed", "same_context_credentials_receipt_delivery")
        receipt_row = {"reference": receipt_reference, "payment_id": receipt["payment_id"],
                       "credentials_task_id": delivery[0]["response"]["result"]["id"]}
    models = [json.loads(line) for line in (cell / "model-interventions.jsonl").read_bytes().splitlines()]
    transport = h.read(cell / "transport-interventions.json")
    require(all(row["provider_requests"] == 0 and row["kind"] in
                ("offline_catalog_fixture", "offline_tool_choice_fixture") for row in models)
            and all(row["provider_request"] is False and row["transport"] == "owned_httpx_ASGITransport"
                    and row["url"].startswith("http://localhost:800") for row in transport), "offline_provider_transport_scope")
    cleanup = h.read(cell / "cleanup.json")
    require(all(cleanup[key] is True for key in ("caller_aliases_restored", "clients_closed", "source_tree_unchanged", "runtime_tree_unchanged")),
            "retained_cleanup_attestation")
    outcome = h.read(cell / "application-outcome.json")
    source_errors = [{key: row[key] for key in ("phase", "error_type", "reason")}
                     for row in h.read(cell / "source-tool-invocations.json") if "error_type" in row]
    return {"id": cell.name, "verified": True, "source": sources, "durable_events": len(events), "rpc_requests": len(rpc),
            "merchant_task_id": pending["id"], "processor_task_id": processor_id, "context_id": pending["contextId"],
            "purchase_completed": purchase, "receipt": receipt_row, "admissions": admissions,
            "buyer_mandate_hash_checks": mandate_hashes(canonical), "offline_model_fixtures": len(models),
            "provider_requests": 0, "actor_error_type": outcome["error_type"], "actor_error_reason": outcome["reason"],
            "source_errors": source_errors, "strict_error_free_owned_cell_purchase": purchase and not outcome["error_type"] and not source_errors}


def run(capture):
    h, decoder_identity = helper()
    matrix = capture / "matrix"
    manifest_raw = (matrix / "public-manifest.json").read_bytes()
    require(sha(manifest_raw) == PUBLIC_SHA, "public_manifest_sha")
    manifest = h.read(matrix / "public-manifest.json")
    expected = [case["id"] + "--" + arm["id"] for case in manifest["cases"] for arm in manifest["arms"]]
    require(len(expected) == manifest["declared_cells"] == 65 and len(set(expected)) == 65,
            "65_cell_cartesian_denominator")
    require({path.name for path in (matrix / "cells").iterdir() if path.is_dir()} == set(expected), "actual_cell_set")
    execution = h.read(matrix / "execution-results.json")
    require([row["id"] for row in execution["cells"]] == expected, "execution_declared_order")
    rows = []
    for case in manifest["cases"]:
        for arm in manifest["arms"]:
            cell = matrix / "cells" / (case["id"] + "--" + arm["id"])
            try:
                row = audit_cell(h, cell, case, arm)
            except Exception as error:
                row = {"id": cell.name, "verified": False, "error_type": type(error).__name__, "reason": str(error)}
            rows.append(row)
    counts = {arm["id"]: sum(row.get("purchase_completed", False) for row in rows
                              if row["id"].endswith("--" + arm["id"])) for arm in manifest["arms"]}
    errors = [row for row in rows if not row["verified"]]
    duplicates = [row for row in rows if row["id"].startswith("duplicate_continuation--")]
    return {"schema_version": "ap2-v5-source-gate-peer-audit/1", "created_utc": datetime.now(timezone.utc).isoformat(),
        "capture": str(capture), "declared_cells": 65, "verified_cells": sum(row["verified"] for row in rows),
        "failed_cells": len(errors), "verification_passed": not errors, "purchase_counts": counts,
        "strict_error_free_owned_cell_purchase_counts": {arm["id"]: sum(row.get("strict_error_free_owned_cell_purchase", False)
            for row in rows if row["id"].endswith("--" + arm["id"])) for arm in manifest["arms"]},
        "duplicate_suffix_outcomes": [{key: row.get(key) for key in
            ("id", "purchase_completed", "actor_error_type", "actor_error_reason", "source_errors", "admissions")} for row in duplicates],
        "reused_read_only_decoder": decoder_identity,
        "reused_checker": "Captured hash-pinned unchanged refinement_oracle, finite semantics only",
        "signature_scope": "Root-anchored disclosure hashes and checkout/payment linkage reverified; buyer signatures are retained separate-evaluator attestations, not reverified here. Merchant signing key absent.",
        "claim_limits": ["Development matrix with owned prefix, offline fixtures and in-process ASGI, not full ADK shopper tasks or human gold.",
            "Source-reference uses canonical sender values; information and interventions differ across arms.",
            "Finite certificate projects one incomplete source relation and does not establish business completion or whole-route non-support.",
            "Completed payment plus duplicate suffix error is not unconditional whole-task success.",
            "No native transport, actual MCP bridge, legal issuer identity or full mandate-policy qualification is established."],
        "cells": rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "audit_output_must_be_fresh")
    result = run(args.capture.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("verified_cells", "failed_cells", "verification_passed", "purchase_counts")}))
    return 0 if result["verification_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
