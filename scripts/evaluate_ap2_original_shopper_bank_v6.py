"""Independent read-only assessment of actual original ADK shopper captures.

This process may read authored evaluator expectations. It imports the frozen
v5 read-only raw decoder, never an actor, coordinator, AP2 app or model fixture.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "benchmark/ap2-shopper-development-v6/application.json"
PRIVATE = ROOT / "benchmark/ap2-shopper-development-v6/evaluator.json"
spec = importlib.util.spec_from_file_location("_ap2_v6_frozen_read_only_raw_decoder", ROOT / "scripts/evaluate_ap2_application_matrix_v5.py")
raw_reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(raw_reader)
read, digest, need = raw_reader.read, raw_reader.digest, raw_reader.need


def lines(path):
    raw = Path(path).read_bytes()
    need(len(raw) <= 128 * 1024 * 1024, "original_adk_capture_read_bound")
    return [json.loads(value) for value in raw.splitlines()]


def attr(value, snake, camel):
    return value.get(snake, value.get(camel))


def identity(application, case):
    plan = read(application / "plan.json")
    need(plan["case"] == case and plan["provider_requests_allowed"] == 0, "not_prospective_public_adk_case")
    need(digest((application / "source-runner.py").read_bytes()) == plan["owned_components"]["scripts/ap2_reference_development_v6.py"],
         "original_adk_runner_snapshot_mismatch")
    for name, expected in plan["owned_components"].items():
        need(digest((application / "owned-source" / name).read_bytes()) == expected, "owned_adk_component_snapshot_mismatch")
    stage_raw = (application / "source-stage-manifest.json").read_bytes()
    need(hashlib.sha256(stage_raw).hexdigest() == raw_reader.STAGE_SHA, "original_adk_stage_pin_mismatch")
    stage = json.loads(stage_raw)
    expected = {row["path"]: {"bytes": row["bytes"], "sha256": row["sha256"]} for row in stage["files"] if row["project"] == "ap2"}
    actual = {path.relative_to(application / "original-source").as_posix(): digest(path.read_bytes())
              for path in (application / "original-source").rglob("*") if path.is_file()}
    need(len(expected) == 136 and actual == expected, "original_adk_source_union_mismatch")
    checks = read(application / "original-callable-code-checks.json")
    need(checks and all(row["full_structural_code_equal"] for row in checks), "original_tool_structural_source_check_failed")
    adk_checks = read(application / "original-adk-source-checks.json")
    need(sum(row.get("full_structural_code_equal") is True for row in adk_checks) == 3, "original_retrying_adk_methods_not_authenticated")
    configs = read(application / "original-adk-agent-configs.json")
    need([row["name"] for row in configs] == ["root_agent", "shopper", "shipping_address_collector", "payment_method_collector"],
         "original_adk_agent_membership_mismatch")
    need(all(row["model"] == "gemini-3.1-flash-lite-preview"
             and hashlib.sha256(row["instruction"].encode()).hexdigest() == row["instruction_sha256"] for row in configs),
         "original_adk_agent_instruction_or_model_mismatch")
    return configs


def assess(application, case, manifest, crypto):
    configs = identity(application, case)
    raw, durable_events, public, rpc = raw_reader.journal(application)
    reference = read(application / "reference-result.json")
    need([{key: value for key, value in row.items() if key != "global_sequence"} for row in reference["public_records"]] == public,
         "original_adk_public_calls_not_durable_observations")
    outcome = read(application / "shopper-outcome.json")
    need(outcome["candidate_id"] == case["id"] and outcome["provider_requests"] == 0, "original_adk_outcome_identity_mismatch")
    events = lines(application / "original-adk-events.jsonl")
    tools = lines(application / "adk-tool-capture.jsonl")
    models = lines(application / "adk-model-interventions.jsonl")
    humans = lines(application / "human-conversation.jsonl")
    need([row["owned_capture_index"] for row in events] == list(range(len(events)))
         and [row["index"] for row in tools] == list(range(len(tools)))
         and [row["index"] for row in humans] == list(range(len(humans))), "original_adk_capture_sequence_gap")
    need(len(events) == outcome["original_adk_events"] and len(tools) == outcome["original_adk_tool_records"]
         and len(models) == outcome["model_fixture_calls"] and len(humans) == outcome["human_turns"], "original_adk_denominator_mismatch")
    need(all(row["provider_requests"] == 0 for row in models)
         and len(models) <= manifest["actor_model_call_bound"] and len(humans) <= manifest["human_turn_bound"],
         "original_adk_model_or_human_bound_changed")
    need(all(row["response"]["kind"] != "call" or row["response"]["name"] in row["offered_original_adk_tools"] for row in models),
         "original_adk_fixture_called_unoffered_tool")
    separation = read(application / "actor-input-separation.json")
    need(separation["private_evaluator_read_probe_blocked"] is True
         and separation["denials"]["private_reads_blocked"] >= 1
         and separation["provider_credentials_present"] is False, "original_adk_actor_private_input_separation_failed")
    before, after = read(application / "original-state-before.json"), read(application / "original-state-after.json")
    session_before, session_after = read(application / "original-adk-session-before.json"), read(application / "original-adk-session-after.json")
    need(before["merchant_store"] == before["credential_tokens"] == {} and before["private_signing_key_files"] == 0
         and all(value["task_ids"] == [] for value in before["task_stores"].values())
         and session_before["state"] == {} and session_before["event_count"] == 0, "actual_original_adk_reset_not_fresh")
    need(session_before["session_id"] == session_after["session_id"]
         and session_after["state"] == read(application / "caller-final-state.json"), "original_adk_session_state_not_actual_caller")
    before_calls = [row for row in tools if row["boundary"] == "before"]
    calls = [row for row in before_calls if row["function"] and row["function"].startswith("roles.shopping_agent.")]
    need(all(row["actual_context_class"] == "google.adk.agents.context.Context" for row in tools),
         "original_adk_calls_not_actual_tool_contexts")
    expected_names = ["find_products", "select_cart"] + (["get_shipping_address"] if case["shipping_mode"] == "wallet" else [])
    expected_names += ["get_payment_methods", "get_payment_credential_token", "create_checkout"]
    if case["confirm_cart"]:
        expected_names += ["create_checkout_mandate", "create_payment_mandate", "send_signed_mandates_to_credentials_provider", "initiate_payment"]
    called_names = [row["name"] for row in calls]
    # A source/model failure stays a partial original trace, never a pass.
    complete_prefix = called_names[:len(expected_names)] == expected_names and outcome["error_type"] is None
    event_calls = {}
    assistant_by_turn = {}
    for event in events:
        turn = event["owned_human_turn_index"]
        for part in (event.get("content") or {}).get("parts") or []:
            if part.get("text") and not part.get("thought"):
                assistant_by_turn.setdefault(turn, []).append(part["text"])
            call = attr(part, "function_call", "functionCall")
            if call:
                need(call.get("id") and call["id"] not in event_calls, "actual_adk_function_call_identity_missing_or_reused")
                event_calls[call["id"]] = {"name": call["name"], "args": call.get("args") or {}, "turn": turn}
    for row in before_calls:
        actual = event_calls.get(row["function_call_id"])
        need(actual and actual["name"] == row["name"] and actual["args"] == row["args"], "adk_callback_not_actual_original_function_call")
    # Every human choice follows a question actually emitted in the prior turn.
    need(humans and humans[0]["text"] == case["public"]["prompt"], "original_public_task_prompt_not_used")
    for human in humans[1:]:
        previous = "\n".join(assistant_by_turn.get(human["index"] - 1, []))
        need(previous, "human_choice_without_actual_original_adk_prompt")
        if human["text"].startswith("I choose the displayed cart "):
            need(human["text"][len("I choose the displayed cart "):-1] in previous, "human_selected_cart_not_displayed")
        if human["text"].startswith("I choose the displayed payment method "):
            need(human["text"][len("I choose the displayed payment method "):-1] in previous, "human_selected_alias_not_displayed")
        if human["text"] in ("123", "000"):
            need("Verification required:" in previous, "human_otp_supplied_without_actual_request")
    sign_calls = [row for row in calls if row["name"] in ("create_checkout_mandate", "create_payment_mandate")]
    for row in sign_calls:
        turn = event_calls[row["function_call_id"]]["turn"]
        need(any(human["text"] == "Yes, I confirm this displayed cart." and human["index"] <= turn for human in humans),
             "original_signing_preceded_human_cart_confirmation")
    payment_start = [row for row in rpc if row["stream"] == "merchant_raw" and row["request"].get("method") == "message/send"
                     and raw_reader.texts(row["request"]["params"]["message"]) == ["Initiate a payment"]]
    continuations = [row for row in rpc if row["stream"] == "merchant_raw" and row["request"].get("method") == "message/send"
                     and raw_reader.texts(row["request"]["params"]["message"]) == [raw_reader.OTP_TEXT]]
    pending = payment_start[0]["response"].get("result") if len(payment_start) == 1 else None
    backend_pending = pending is not None and pending.get("status", {}).get("state") == "input-required"
    generic_adverse = (backend_pending and outcome["terminal_reason"] == "original_generic_payment_status_has_no_otp_request"
                       and not continuations and outcome["supplied_human_otp_replies"] == 0)
    actual_returns = [row["result"] for row in tools if row["boundary"] == "after" and row["name"] == "initiate_payment"]
    if backend_pending:
        need(actual_returns == [outcome["original_payment_tool_return"]], "generic_adk_status_not_actual_original_tool_return")
        processor_id = pending["status"]["message"]["taskId"]
        child = [row["response"].get("result", {}) for row in rpc if row["stream"] == "processor_raw"
                 and row["response"].get("result", {}).get("id") == processor_id]
        need(child and child[0]["status"]["state"] == "input-required" and child[0]["contextId"] == pending["contextId"],
             "original_adk_parent_child_pending_tasks_mismatch")
    else:
        processor_id = None
    if not case["confirm_cart"]:
        need(not sign_calls and not payment_start and not continuations, "withheld_confirmation_did_not_stop_original_signing_payment")
    caller = session_after["state"]
    association = bool(caller.get("payment_credential_token") and any(
        value.get("payment_mandate_id") == caller.get("checkout_hash")
        and value.get("email_address") == "bugsbunny@gmail.com"
        for value in after["credential_tokens"].values()))
    crypto_review = raw_reader.verify_signatures(application, caller, crypto) if caller.get("payment_mandate_sdjwt") else {"verified": False, "status": "signing_not_reached"}
    receipt_tasks = [row["response"].get("result", {}) for row in rpc if row["stream"] == "merchant_raw"
                     and pending is not None and row["response"].get("result", {}).get("id") == pending["id"]]
    final_task = receipt_tasks[-1] if receipt_tasks else {}
    observed_purchase = bool(final_task.get("status", {}).get("state") == "completed"
                             and raw_reader.receipts(final_task) and caller.get("payment_receipt"))
    cleanup = read(application / "cleanup.json")
    need(cleanup["clients_closed"] and cleanup["caller_aliases_restored"] and cleanup["source_tree_unchanged"]
         and cleanup["runtime_tree_unchanged"] and outcome["original_model_registry_restored"], "original_adk_cleanup_or_fidelity_failed")
    return {"evaluation_status": "actual_original_adk_prefix_verified" if complete_prefix else "actual_partial_original_adk_trace_retained",
        "complete_original_adk_prefix_observed": complete_prefix, "original_adk_tool_order": called_names,
        "original_adk_events": len(events), "human_turns": len(humans), "model_fixture_calls": len(models),
        "durable_events": len(durable_events), "rpc_requests": len(rpc), "backend_parent_child_payment_pending": backend_pending,
        "original_generic_status_adverse_boundary_observed": generic_adverse, "otp_continuations": len(continuations),
        "selected_credential_transaction_association_observed": association, "buyer_signature_review": crypto_review,
        "actual_original_purchase_observed": observed_purchase, "original_merchant_task_id": pending["id"] if pending else None,
        "original_processor_task_id": processor_id, "original_context_id": pending["contextId"] if pending else None,
        "original_session_id": session_before["session_id"], "actual_fresh_stores_and_session_observed": True,
        "terminal_reason": outcome["terminal_reason"], "actor_error_type": outcome["error_type"], "actor_error_reason": outcome["reason"],
        "provider_requests": 0, "human_gold_validated": False, "native_qualification_established": False}


def disposition(candidate, processes):
    verified = processes and all(row.get("complete_original_adk_prefix_observed") for row in processes)
    specific = candidate["id"] in {"ap2-cal-002", "ap2-cal-003", "ap2-ho-001", "ap2-ho-002", "ap2-ho-003", "ap2-ho-004", "ap2-ho-005", "ap2-ho-006"}
    if candidate["id"] == "ap2-cal-004" and verified and len(processes) == 2:
        keys = ["original_session_id", "original_merchant_task_id", "original_context_id"]
        reset = all(processes[0].get(key) and processes[1].get(key) and processes[0][key] != processes[1][key] for key in keys)
        public_keys = [row.get("buyer_signature_review", {}).get("buyer_public_key", {}).get("sha256") for row in processes]
        reset = reset and all(public_keys) and public_keys[0] != public_keys[1]
        return "candidate_original_reset_pair_obligation_observed" if reset else "candidate_reset_pair_not_independently_established"
    if specific and verified:
        return "candidate_source_obligation_observed_pending_human_gold"
    if verified and any(row.get("original_generic_status_adverse_boundary_observed") for row in processes):
        return "candidate_required_otp_receipt_or_fault_branch_unrealized_after_original_generic_status"
    return "candidate_partial_missing_or_failed_attempt_retained"


def evaluate_allocation(allocation, manifest, crypto):
    plan, execution = read(allocation / "allocation-manifest.json"), read(allocation / "execution-results.json")
    need(plan["candidate_denominator"] == execution["candidate_denominator"] == 34
         and digest((allocation / "public-manifest.json").read_bytes()) == plan["public_manifest"], "original_bank_denominator_or_allocation_changed")
    records = {row["id"]: row for row in manifest["records"]}
    need([row["candidate_id"] for row in execution["cells"]] == [row["id"] for row in manifest["records"]], "original_bank_candidate_order_changed")
    prior_raw = (allocation / "prior-source-boundary-actor-output.json").read_bytes()
    need(hashlib.sha256(prior_raw).hexdigest() == manifest["source_boundary_capture_sha256"], "prior_source_boundary_capture_link_changed")
    prior = json.loads(prior_raw)
    prior_cases = {row["id"]: row for row in prior["cases"]}
    results = []
    for cell in execution["cells"]:
        candidate = records[cell["candidate_id"]]
        row = {"candidate_id": candidate["id"], "execution_class": candidate["execution_class"], "processes": []}
        if candidate["execution_mode"] == "prior_source_boundary_capture":
            need(candidate["id"] in prior_cases and prior["provider_requests"] == 0 and prior["full_shopper_workflow_completed"] is False,
                 "prior_source_boundary_case_missing_or_mislabeled")
            row.update(disposition="prior_original_sdk_source_boundary_observed_not_new_full_shopper", prior_case=prior_cases[candidate["id"]])
        else:
            for process in cell["process_attempts"]:
                result = {"id": process["id"], "returncode": process["returncode"], "allocation_status": process["allocation_status"]}
                base = allocation / "cells" / process["id"]
                if (base / "shopper-outcome.json").exists():
                    try:
                        result.update(assess(base, candidate, manifest, crypto))
                    except Exception as error:
                        result.update(evaluation_status="independent_original_adk_evaluation_refused", evaluation_error_type=type(error).__name__,
                                      evaluation_reason=str(error)[:1000])
                else:
                    result["evaluation_status"] = "missing_or_pre_execution_failure_retained"
                row["processes"].append(result)
            row["disposition"] = disposition(candidate, row["processes"])
        results.append(row)
    all_processes = [process for row in results for process in row["processes"]]
    return {"schema_version": "ap2-independent-original-adk-bank-feasibility/6", "evaluated_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_denominator": 34, "new_original_adk_process_denominator": 29, "prior_source_boundary_candidate_denominator": 6,
        "candidates": results, "totals": {
            "verified_original_adk_prefix_processes": sum(row.get("complete_original_adk_prefix_observed", False) for row in all_processes),
            "generic_status_adverse_processes": sum(row.get("original_generic_status_adverse_boundary_observed", False) for row in all_processes),
            "independent_evaluation_refusals": sum(row["evaluation_status"] == "independent_original_adk_evaluation_refused" for row in all_processes),
            "missing_processes": sum(row["evaluation_status"] == "missing_or_pre_execution_failure_retained" for row in all_processes),
            "actual_purchase_processes": sum(row.get("actual_original_purchase_observed", False) for row in all_processes)},
        "human_gold_validated": False, "independent_heldout_qualification": False, "native_qualification_established": False,
        "scope": "Feasibility and actual original ADK prefix/adverse observations; candidate-specific unrealized branches remain in denominator"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allocation", type=Path)
    parser.add_argument("--cell", type=Path)
    parser.add_argument("--candidate")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--site-packages", type=Path)
    args = parser.parse_args(argv)
    if args.site_packages:
        sys.path.insert(0, str(args.site_packages.resolve()))
    manifest, expectations = read(PUBLIC), read(PRIVATE)
    need(expectations["actor_must_not_read_this_file"] is True, "original_adk_private_evaluator_contract_changed")
    if args.cell:
        candidate = next(row for row in manifest["records"] if row["id"] == args.candidate)
        result = assess(args.cell.absolute(), candidate, manifest, args.site_packages is not None)
    else:
        need(args.allocation is not None, "allocation_or_cell_required")
        result = evaluate_allocation(args.allocation.absolute(), manifest, args.site_packages is not None)
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    result["independent_evaluator_sha256"] = digest(Path(__file__).read_bytes())["sha256"]
    result["private_expectations_sha256"] = digest(PRIVATE.read_bytes())["sha256"]
    (output / "result.json").write_bytes((json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n").encode())
    print(json.dumps({"status": result.get("evaluation_status", "original_source_bank_feasibility_evaluated"),
                      "totals": result.get("totals"), "output": str(output)}))
    if args.cell:
        return 0 if result["complete_original_adk_prefix_observed"] else 2
    return 0 if result["totals"]["independent_evaluation_refusals"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
