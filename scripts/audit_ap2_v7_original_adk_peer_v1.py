"""Independent raw AP2 V7 peer audit; stdlib, no captured-code execution.

The standalone raw byte decoder below is copied from this peer's V5 numerical
audit, independently of the original actor and first evaluator.
"""
from __future__ import annotations

import argparse
import ast
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


def json_lines(path):
    raw = path.read_bytes()
    require(len(raw) <= 128 * 1024 * 1024, "jsonl_bound")
    return [json_value(line) for line in raw.splitlines()]


def original_configs(cell, plan):
    for name, expected in plan["owned_components"].items():
        require(identity((cell / "owned-source" / name).read_bytes()) == expected, "owned_source_binding")
    require(identity((cell / "source-runner.py").read_bytes()) == plan["owned_components"]["scripts/ap2_reference_development_v7.py"], "runner_binding")
    stage_raw = (cell / "source-stage-manifest.json").read_bytes()
    require(hashlib.sha256(stage_raw).hexdigest() == "78828cea09bdd387230a2fc0772b542beabfe07b72c3a2f24b24c02c1a2f4463", "stage_pin")
    expected = {row["path"]: {"bytes": row["bytes"], "sha256": row["sha256"]}
                for row in json_value(stage_raw)["files"] if row["project"] == "ap2"}
    root = cell / "original-source"
    actual = {path.relative_to(root).as_posix(): identity(path.read_bytes()) for path in root.rglob("*") if path.is_file()}
    require(len(actual) == 136 and actual == expected, "original_source_136_file_pin")
    common = ast.parse((root / "code/samples/python/src/common/system_utils.py").read_text(encoding="utf-8"))
    debug = next(ast.literal_eval(node.value) for node in common.body if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == "DEBUG_MODE_INSTRUCTIONS" for target in node.targets))
    configs = read(cell / "original-adk-agent-configs.json")
    names = ["root_agent", "shopper", "shipping_address_collector", "payment_method_collector"]
    require([row["name"] for row in configs] == names, "original_agent_membership")
    paths = ["roles/shopping_agent/agent.py"] + ["roles/shopping_agent/subagents/" + name + "/agent.py" for name in names[1:]]
    for cfg, path in zip(configs, paths):
        tree = ast.parse((root / "code/samples/python/src" / path).read_text(encoding="utf-8"))
        invocation = next(node.value for node in tree.body if isinstance(node, ast.Assign)
                          and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
                          and node.value.func.id == "RetryingLlmAgent")
        kwargs = {keyword.arg: keyword.value for keyword in invocation.keywords}
        require(ast.literal_eval(kwargs["name"]) == cfg["name"] and ast.literal_eval(kwargs["model"]) == cfg["model"], "agent_name_model_not_source")
        instruction = kwargs["instruction"]
        if isinstance(instruction, ast.BinOp) and isinstance(instruction.op, ast.Mod):
            require(isinstance(instruction.right, ast.Name) and instruction.right.id == "DEBUG_MODE_INSTRUCTIONS", "instruction_interpolation")
            text = ast.literal_eval(instruction.left) % debug
        else:
            text = ast.literal_eval(instruction)
        require(text == cfg["instruction"] and hashlib.sha256(text.encode()).hexdigest() == cfg["instruction_sha256"], "instruction_not_source")
        tool_names = [node.attr for node in kwargs["tools"].elts]
        require(tool_names == [value.rsplit(".", 1)[-1] for value in cfg["tools"]], "tool_list_not_source")
        require(cfg["class"] == "common.retrying_llm_agent.RetryingLlmAgent", "agent_class_changed")
    return configs


def assess(cell, candidate, manifest, process):
    plan = read(cell / "plan.json")
    require(plan["case"] == candidate and plan["provider_requests_allowed"] == 0, "prospective_case_binding")
    configs = original_configs(cell, plan)
    rpc, durable_count, journal_hash = raw_exchanges(cell)
    events = json_lines(cell / "original-adk-events.jsonl")
    tools = json_lines(cell / "adk-tool-capture.jsonl")
    models = json_lines(cell / "adk-model-interventions.jsonl")
    humans = json_lines(cell / "human-conversation.jsonl")
    outcome = read(cell / "shopper-outcome.json")
    require(outcome["candidate_id"] == candidate["id"] and outcome["error_type"] is None, "outcome_error_or_identity")
    require([row["owned_capture_index"] for row in events] == list(range(len(events)))
            and [row["index"] for row in tools] == list(range(len(tools)))
            and [row["index"] for row in humans] == list(range(len(humans))), "adk_capture_gap")
    require(len(events) == outcome["original_adk_events"] and len(tools) == outcome["original_adk_tool_records"]
            and len(models) == outcome["model_fixture_calls"] and len(humans) == outcome["human_turns"], "adk_count_binding")
    require(all(row["provider_requests"] == 0 for row in models) and outcome["provider_requests"] == 0
            and len(models) <= manifest["actor_model_call_bound"] and len(humans) <= manifest["human_turn_bound"], "offline_bounded_model_scope")
    before, after = read(cell / "original-state-before.json"), read(cell / "original-state-after.json")
    sb, sa = read(cell / "original-adk-session-before.json"), read(cell / "original-adk-session-after.json")
    require(before["merchant_store"] == before["credential_tokens"] == sb["state"] == {}
            and before["private_signing_key_files"] == sb["event_count"] == 0
            and all(row["task_ids"] == [] for row in before["task_stores"].values()), "fresh_stores_session")
    require(sb["session_id"] == sa["session_id"] and sa["state"] == read(cell / "caller-final-state.json"), "actual_session_state")
    call_events, response_events, assistant_by_turn = {}, {}, {}
    for event in events:
        turn = event["owned_human_turn_index"]
        for part in (event.get("content") or {}).get("parts") or []:
            if part.get("text") and not part.get("thought"):
                assistant_by_turn.setdefault(turn, []).append(part["text"])
            call = part.get("functionCall") or part.get("function_call")
            response = part.get("functionResponse") or part.get("function_response")
            if call:
                require(call["id"] not in call_events, "duplicate_adk_call")
                call_events[call["id"]] = dict(call, turn=turn)
            if response:
                require(response["id"] not in response_events, "duplicate_adk_response")
                response_events[response["id"]] = response
    callbacks, after_callbacks = [], {}
    for row in tools:
        require(row["actual_context_class"] == "google.adk.agents.context.Context", "not_actual_adk_tool_context")
        observed = call_events[row["function_call_id"]]
        require(row["name"] == observed["name"] and row["args"] == observed.get("args", {}), "callback_not_event_call")
        if row["boundary"] == "before":
            callbacks.append(row)
        else:
            require(row["boundary"] == "after", "unknown_callback_boundary")
            result = response_events[row["function_call_id"]]
            # ADK returns native dictionaries directly. The original wallet
            # tool returns a ContactAddress model, which ADK wraps like other
            # non-dictionary results before our JSON callback serialization.
            native_dict = type(row["result"]) is dict and row["name"] != "get_shipping_address"
            native_response = row["result"] if native_dict else {"result": row["result"]}
            require(result["name"] == row["name"] and result["response"] == native_response, "callback_not_event_response")
            require(row["function_call_id"] not in after_callbacks, "duplicate_after_callback")
            after_callbacks[row["function_call_id"]] = row
    require(len(callbacks) == len(after_callbacks), "callback_not_paired")
    original_calls = [row for row in callbacks if row["function"].startswith("roles.shopping_agent.")]
    expected_tools = ["find_products", "select_cart"] + (["get_shipping_address"] if candidate["shipping_mode"] == "wallet" else [])
    expected_tools += ["get_payment_methods", "get_payment_credential_token", "create_checkout"]
    if candidate["confirm_cart"]:
        expected_tools += ["create_checkout_mandate", "create_payment_mandate", "send_signed_mandates_to_credentials_provider", "initiate_payment"]
    require([row["name"] for row in original_calls] == expected_tools, "original_tool_order_not_expected_prefix")
    require(humans and humans[0]["text"] == candidate["public"]["prompt"], "public_prompt_not_observed")
    for human in humans[1:]:
        previous = "\n".join(assistant_by_turn.get(human["index"] - 1, []))
        require(previous, "human_without_assistant_question")
        for prefix in ("I choose the displayed cart ", "I choose the displayed payment method "):
            if human["text"].startswith(prefix):
                require(human["text"][len(prefix):-1] in previous, "human_choice_not_displayed")
        if human["text"] in ("123", "000"):
            require("Verification required:" in previous, "human_otp_without_request")
    for row in original_calls:
        if row["name"] in ("create_checkout_mandate", "create_payment_mandate"):
            turn = call_events[row["function_call_id"]]["turn"]
            require(any(h["text"] == "Yes, I confirm this displayed cart." and h["index"] <= turn for h in humans), "sign_before_confirmation")
    wallet = None
    if candidate["shipping_mode"] == "wallet":
        address_rows = [row for row in original_calls if row["name"] == "get_shipping_address"]
        require(len(address_rows) == 1, "wallet_call_count")
        address_tool = after_callbacks[address_rows[0]["function_call_id"]]["result"]
        wire_addresses = [part["data"]["contact_picker.ContactAddress"] for row in rpc if row["stream"] == "credentials_raw"
                          and texts(row["request"].get("params", {}).get("message", {})) == ["Get the user's shipping address."]
                          for artifact in row["response"].get("result", {}).get("artifacts") or []
                          for part in artifact["parts"] if "contact_picker.ContactAddress" in part.get("data", {})]
        require(len(wire_addresses) == 1 and all(address_tool.get(k) == v for k, v in wire_addresses[0].items()), "wallet_tool_not_datapart")
        components = []
        for value in wire_addresses[0].values():
            if type(value) is list:
                components.extend(str(v) for v in value if type(v) in (str, int) and str(v))
            elif type(value) in (str, int) and str(value):
                components.append(str(value))
        all_display = "\n".join(text for pieces in assistant_by_turn.values() for text in pieces)
        require(components and all(component in all_display for component in components), "wallet_full_address_not_displayed")
        wallet = {"actual_datapart": wire_addresses[0], "actual_tool_return": address_tool,
                  "all_original_components_displayed": True, "original_address_line": wire_addresses[0].get("address_line"),
                  "display_fragments": [text for pieces in assistant_by_turn.values() for text in pieces if "shipping address is" in text or "Shipping:" in text]}
    starts = [row for row in rpc if row["stream"] == "merchant_raw" and row["request"].get("method") == "message/send"
              and texts(row["request"]["params"]["message"]) == ["Initiate a payment"]]
    continuations = [row for row in rpc if row["stream"] == "merchant_raw" and row["request"].get("method") == "message/send"
                     and texts(row["request"]["params"]["message"]) == [OTP]]
    pending = starts[0]["response"]["result"] if len(starts) == 1 else None
    adverse, processor_id = False, None
    if candidate["confirm_cart"]:
        require(pending and pending["status"]["state"] == "input-required", "merchant_not_pending")
        processor_id = pending["status"]["message"]["taskId"]
        child = [row["response"]["result"] for row in rpc if row["stream"] == "processor_raw"
                 and row["response"].get("result", {}).get("id") == processor_id]
        require(child and child[-1]["status"]["state"] == "input-required" and child[-1]["contextId"] == pending["contextId"], "processor_not_pending")
        actual_return = [after_callbacks[row["function_call_id"]]["result"] for row in original_calls if row["name"] == "initiate_payment"]
        require(actual_return == ["Status: TaskState.input_required"] == [outcome["original_payment_tool_return"]], "generic_return_not_actual_tool")
        require(outcome["terminal_reason"] == "original_generic_payment_status_has_no_otp_request" and not continuations
                and outcome["supplied_human_otp_replies"] == 0, "generic_adverse_not_retained")
        adverse = True
    else:
        require(not starts and not continuations and outcome["terminal_reason"] == "human_cart_confirmation_withheld", "withheld_did_not_stop")
    purchase = bool(sa["state"].get("payment_receipt") or any(receipts(row["response"].get("result", {})) for row in rpc))
    require(not purchase, "unexpected_raw_purchase_evidence")
    cleanup = read(cell / "cleanup.json")
    require(all(cleanup[k] for k in ("clients_closed", "caller_aliases_restored", "source_tree_unchanged", "runtime_tree_unchanged"))
            and outcome["original_model_registry_restored"], "cleanup_failure")
    key = cell / "public-verification/agent_provider_signing_key.pub"
    return {"process_id": process["id"], "candidate_id": candidate["id"], "complete_original_adk_prefix_observed": True,
            "original_generic_status_adverse_boundary_observed": adverse, "actual_original_purchase_observed": purchase,
            "original_tool_order": expected_tools, "actual_tool_callbacks_bound_to_adk_events": True,
            "wallet_review": wallet, "original_session_id": sb["session_id"], "fresh_session_stores_observed": True,
            "original_merchant_task_id": pending["id"] if pending else None, "original_processor_task_id": processor_id,
            "original_context_id": pending["contextId"] if pending else None,
            "buyer_public_key_sha256": identity(key.read_bytes())["sha256"] if key.exists() else None,
            "durable_events": durable_count, "journal_identity": journal_hash, "model_fixture_calls": len(models),
            "human_turns": len(humans), "otp_continuations": len(continuations), "terminal_reason": outcome["terminal_reason"],
            "source_files_pinned": 136, "original_agent_configurations_compared_to_source_ast": len(configs),
            "provider_requests": 0, "full_original_task_success_established": False}


def audit(capture):
    bank = capture / "bank"
    manifest = read(bank / "public-manifest.json")
    allocation, execution = read(bank / "allocation-manifest.json"), read(bank / "execution-results.json")
    records = manifest["records"]
    require(len(records) == len({row["id"] for row in records}) == manifest["candidate_denominator"] == 34, "34_unique_candidates")
    require([row["id"] for row in records] == [row["candidate_id"] for row in allocation["cells"]]
            == [row["candidate_id"] for row in execution["cells"]], "candidate_order_denominator")
    require(identity((bank / "public-manifest.json").read_bytes()) == allocation["public_manifest"], "allocation_manifest_identity")
    prior_raw = (bank / "prior-source-boundary-actor-output.json").read_bytes()
    require(hashlib.sha256(prior_raw).hexdigest() == manifest["source_boundary_capture_sha256"], "prior_source_binding")
    prior = json_value(prior_raw)
    prior_cases = {row["id"]: row for row in prior["cases"]}
    processes, candidates = [], []
    for candidate, cell in zip(records, execution["cells"]):
        if candidate["execution_mode"] == "prior_source_boundary_capture":
            require(candidate["id"] in prior_cases and not prior["full_shopper_workflow_completed"]
                    and prior["provider_requests"] == 0, "prior_not_full_workflow")
            candidates.append({"candidate_id": candidate["id"], "new_original_processes": 0,
                               "disposition": "retained_prior_source_boundary_only"})
            continue
        require(len(cell["process_attempts"]) == candidate["original_processes_per_candidate"], "process_denominator")
        for process in cell["process_attempts"]:
            require(process["returncode"] == 0, "process_failure_retained")
            processes.append(assess(bank / "cells" / process["id"], candidate, manifest, process))
        candidates.append({"candidate_id": candidate["id"], "new_original_processes": len(cell["process_attempts"]),
                           "disposition": "original_prefix_observed_specific_required_branch_not_qualified"})
    require(len(processes) == 29 and sum(row["new_original_processes"] == 0 for row in candidates) == 6, "29_new_6_prior_denominators")
    reset = [row for row in processes if row["candidate_id"] == "ap2-cal-004"]
    require(len(reset) == 2, "reset_pair_missing")
    reset_fields = ["original_session_id", "original_merchant_task_id", "original_processor_task_id", "original_context_id", "buyer_public_key_sha256"]
    require(all(reset[0][key] and reset[1][key] and reset[0][key] != reset[1][key] for key in reset_fields), "reset_pair_identity_not_fresh")
    first = read(capture / "independent-bank-evaluation/result.json")
    reported = {row["id"]: row for candidate in first["candidates"] for row in candidate["processes"]}
    disagreements = [{"process_id": row["process_id"], "field": key} for row in processes
                     for key in ("complete_original_adk_prefix_observed", "original_generic_status_adverse_boundary_observed", "actual_original_purchase_observed")
                     if reported.get(row["process_id"], {}).get(key) != row[key]]
    return {"schema_version": "ap2-v7-original-adk-raw-peer-review/1", "reviewed_utc": datetime.now(timezone.utc).isoformat(),
            "status": "independent_original_adk_raw_evidence_verified" if not disagreements else "first_evaluator_disagreement",
            "audit_source_sha256": identity(Path(__file__).read_bytes())["sha256"], "capture": str(capture),
            "candidate_denominator": 34, "new_original_processes": 29, "new_workflow_candidates": 28,
            "prior_source_boundary_candidates": 6, "split_counts": dict(Counter(row["split"] for row in records)),
            "complete_original_adk_prefixes": sum(row["complete_original_adk_prefix_observed"] for row in processes),
            "generic_status_adverse_boundaries": sum(row["original_generic_status_adverse_boundary_observed"] for row in processes),
            "actual_original_purchases": sum(row["actual_original_purchase_observed"] for row in processes),
            "wallet_processes": [row for row in processes if row["wallet_review"] is not None],
            "reset_pair": {"candidate_id": "ap2-cal-004", "identity_fields_independently_different": reset_fields, "processes": reset},
            "first_evaluator_disagreements": disagreements, "candidates": candidates, "processes": processes,
            "limits": ["All34 exposed candidates stay in denominator. Complete prefix is not a completed candidate-specific OTP, receipt or injected-fault obligation.",
                       "29 new original ADK processes comprise28 candidates plus one reset repetition; six candidates link only prior source-boundary captures.",
                       "Deterministic registered model and human fixtures, original local SDK stores and owned ASGI; provider quality, native deployment and independent held-out human gold remain unestablished.",
                       "Buyer key hashes establish distinct reset identities here; cryptographic token signature review is outside this raw peer audit."]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    capture, output = args.capture.resolve(), args.output.resolve()
    require(capture not in output.parents and not output.exists(), "fresh_output_outside_capture_required")
    result = audit(capture)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps({key: result[key] for key in ("status", "candidate_denominator", "new_original_processes", "complete_original_adk_prefixes", "generic_status_adverse_boundaries", "actual_original_purchases")}, sort_keys=True))
    return 0 if not result["first_evaluator_disagreements"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
