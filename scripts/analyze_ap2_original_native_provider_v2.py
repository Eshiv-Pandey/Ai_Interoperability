"""Read retained V2 public actor/Task captures without importing applications.

This analyzer reports observed public behavior and consistency questions. It
does not run an actor, SDK, model, evaluator or checker, and assigns no gold or
whole-task grade. Root's separate raw review owns native/provider reconciliation.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


EXPECTED_RUN = 42995902326
EXPECTED_HEAD = "5f8ef7c8948c0a4a89b665810968cc4d5a734cda"
CASE_VARIATIONS = (
    ("correct-reply", {}),
    ("wrong-reply", {"otp_response": "wrong-human-reply"}),
    ("no-reply", {"otp_response": None}),
    ("foreign-context-recovery", {"fault": "other_original_context"}),
    ("repeat-completed", {"repeat_after_completed": True}),
)
ACTOR_KINDS = {
    "human-cart-selection", "human-wallet-consent", "public-shipping-display",
    "human-payment-selection", "human-cart-confirmation", "public-otp-request",
    "explicit-human-otp", "received-public-authority-fault",
    "adverse-original-rpc-error", "unexpected-adverse-read-error",
    "adverse-read-disposition", "recover-from-prior-public-task",
    "public-payment-observation", "public-repeat-observation", "actor-error",
}


def strict(raw):
    """Copied narrow JSON parsing recipe from the preserved V1 raw utility."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate_json_key:" + key)
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError("nonfinite_json:" + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)


def digest(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def equal(left, right):
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def facts():
    base = dict(catalog_search="unbranded walking shoes", user_email="bugsbunny@gmail.com",
                cart_index=0, payment_method_index=0, wallet_consent=True,
                confirm_cart=True, otp_response="123", fault="none", repeat_after_completed=False)
    return [dict(base, case_id="ap2-native-provider-v2-" + name, **change)
            for name, change in CASE_VARIATIONS]


def parts(task):
    if type(task) is not dict:
        return []
    status_message = task.get("status", {}).get("message") or {}
    return status_message.get("parts") or []


def receipts(task):
    if type(task) is not dict:
        return []
    return [part["data"]["ap2.PaymentReceipt"]
            for artifact in task.get("artifacts") or [] for part in artifact.get("parts") or []
            if type(part.get("data")) is dict and "ap2.PaymentReceipt" in part["data"]]


def challenge(task):
    values = [part["data"]["challenge"] for part in parts(task)
              if type(part.get("data")) is dict and "challenge" in part["data"]]
    if (type(task) is dict and task.get("status", {}).get("state") == "input-required"
            and len(values) == 1 and type(values[0]) is dict
            and values[0].get("type") == "otp" and type(values[0].get("display_text")) is str):
        return values[0]
    return None


def task_summary(task):
    if type(task) is not dict:
        return None
    messages = list(task.get("history") or [])
    message = task.get("status", {}).get("message")
    if type(message) is dict:
        messages.append(message)
    responses = [part["data"]["challenge_response"] for message in messages
                 for part in message.get("parts") or []
                 if type(part.get("data")) is dict and "challenge_response" in part["data"]]
    return {"id": task.get("id"), "context_id": task.get("contextId"),
            "state": task.get("status", {}).get("state"),
            "status_text": [part["text"] for part in parts(task) if "text" in part],
            "status_message_task_id": (task.get("status", {}).get("message") or {}).get("taskId"),
            "status_message_context_id": (task.get("status", {}).get("message") or {}).get("contextId"),
            "otp_challenge": challenge(task), "receipts": receipts(task),
            "retained_task_message_challenge_responses": responses,
            "raw_task_digest": digest(json.dumps(task, sort_keys=True, allow_nan=False).encode())}


class Analysis:
    def __init__(self, retained):
        self.retained = retained
        self.capture = retained / "extracted"
        self.issues, self.evidence, self.members = [], {}, {}
        self.local_refusals, self.byte_boundary_by_exclusion = [], False

    def need(self, condition, reason):
        if not condition:
            self.issues.append(reason)
        return bool(condition)

    def raw(self, path, required=False):
        if not path.is_file():
            if required:
                self.issues.append("missing_file:" + str(path))
            return None
        raw = path.read_bytes()
        self.evidence[str(path)] = digest(raw)
        if path.is_relative_to(self.capture):
            relative = path.relative_to(self.capture).as_posix()
            self.need(self.members.get(relative) == digest(raw), "root_manifest_member_binding_mismatch:" + relative)
        return raw

    def read_json(self, path, required=False):
        raw = self.raw(path, required)
        return strict(raw) if raw is not None else None

    def lines(self, path):
        raw = self.raw(path)
        return [strict(line) for line in raw.splitlines()] if raw is not None else []

    def case(self, declared, parent):
        case_id = declared["case_id"]
        prefix = case_id + ":"
        folder = self.capture / "execution/cases" / case_id
        question_start = len(self.issues)
        actor = self.read_json(folder / "caller/result.json")
        raw_events = self.lines(folder / "caller/actor-public-events.jsonl")
        public_facts = self.read_json(folder / (case_id + ".public-human-facts.json"))
        if public_facts is not None:
            self.need(equal(public_facts, declared), prefix + "retained_facts_differ_from_five_fixed_cases")
        terminal_calls = [{key: value for key, value in event.items() if key != "kind"}
                          for event in raw_events if event.get("kind") in {"original-call-return", "original-call-error"}]
        calls = actor.get("original_business_calls", []) if actor else terminal_calls
        events = actor.get("actor_public_events", []) if actor else [row for row in raw_events if row.get("kind") in ACTOR_KINDS]
        raw_reads = [{key: value for key, value in event.items() if key != "kind"}
                     for event in raw_events if event.get("kind") in {"public-task-read-return", "public-task-read-error"}]
        reads = actor.get("public_task_reads", []) if actor else raw_reads
        if actor:
            self.need(actor.get("schema_version") == "ap2-owned-public-scripted-continuation/2", prefix + "actor_schema_mismatch")
            self.need(actor.get("case_id") == case_id and equal(actor.get("public_human_facts"), declared), prefix + "actor_facts_mismatch")
            self.need(actor.get("grade") is None and actor.get("evaluator_or_private_journal_inputs") == [], prefix + "unexpected_grade_or_private_inputs")
            self.need(equal(calls, terminal_calls), prefix + "actor_calls_differ_from_raw_terminal_calls")
            self.need(equal(reads, raw_reads), prefix + "actor_reads_differ_from_raw_read_terminals")
            self.need(equal(events, [row for row in raw_events if row.get("kind") in ACTOR_KINDS]), prefix + "actor_events_differ_from_raw_event_census")
            self.need([row.get("index") for row in calls] == list(range(len(calls))), prefix + "original_call_index_sequence_mismatch")
            self.need([row.get("index") for row in events] == list(range(len(events))), prefix + "actor_event_index_sequence_mismatch")

        def one(rows, key, value):
            selected = [row for row in rows if row.get(key) == value]
            self.need(len(selected) <= 1, prefix + "duplicate_" + str(value))
            return selected[0] if len(selected) == 1 else None

        def event(kind):
            return one(events, "kind", kind)

        def call(phase):
            return one(calls, "phase", phase)

        def task(phase):
            read = one(reads, "phase", phase)
            return (read or {}).get("public_observation", {}).get("task")

        tasks = []
        for read in reads:
            observation = read.get("public_observation") or read.get("refused_public_observation")
            starts = [row for row in raw_events if row.get("kind") == "public-task-read-start" and row.get("phase") == read.get("phase")]
            self.need(len(starts) == 1, prefix + "read_start_census:" + str(read.get("phase")))
            if observation:
                public_task, query = observation.get("task", {}), observation.get("query", {})
                self.need(public_task.get("id") == query.get("id") and query.get("historyLength") == 100, prefix + "public_query_task_id_or_history_mismatch")
                if len(starts) == 1:
                    held = starts[0].get("query", {})
                    same_authority = public_task.get("id") == held.get("id") and public_task.get("contextId") == held.get("caller_context")
                    self.need(same_authority if "public_observation" in read else not same_authority, prefix + "public_task_authority_disposition_mismatch")
                tasks.append({"phase": read.get("phase"), "disposition": "returned" if "public_observation" in read else "refused_by_owned_read",
                              "task": task_summary(public_task)})
        pending = task("initial-payment-task")
        final = task("waiting-payment-task" if declared["otp_response"] is None else "after-original-otp")
        repeated = task("after-repeated-original-otp")
        if actor:
            self.need(equal(actor.get("public_pending_task"), pending), prefix + "actor_pending_not_exact_initial_public_read")
            self.need(equal(actor.get("public_final_task"), final), prefix + "actor_final_not_exact_final_public_read")
        if final is not None:
            required_kinds = {"human-cart-selection", "human-wallet-consent", "public-shipping-display",
                              "human-payment-selection", "human-cart-confirmation", "public-otp-request", "explicit-human-otp"}
            self.need(required_kinds <= {row.get("kind") for row in events}, prefix + "final_task_missing_prior_public_choice_or_challenge_events")
            base_phases = ["catalog", "cart-selection", "shipping", "payment-methods", "credential-token", "checkout",
                           "checkout-mandate", "payment-mandate", "credential-association", "payment-start"]
            self.need([row.get("phase") for row in calls[:len(base_phases)]] == base_phases,
                      prefix + "final_task_missing_original_business_sequence")
            if declared["fault"] == "other_original_context":
                self.need({"received-public-authority-fault", "adverse-read-disposition", "recover-from-prior-public-task"}
                          <= {row.get("kind") for row in events}, prefix + "foreign_context_final_missing_refusal_recovery_events")
        for subsequent in (final, repeated):
            if type(pending) is dict and type(subsequent) is dict:
                self.need(subsequent.get("id") == pending.get("id") and subsequent.get("contextId") == pending.get("contextId"),
                          prefix + "continuation_changed_prior_public_task_authority")

        cart, payment = event("human-cart-selection"), event("human-payment-selection")
        selected = cart.get("selected") if cart else None
        if cart:
            offered = cart.get("offered", [])
            self.need(type(offered) is list and len(offered) > declared["cart_index"] and equal(selected, offered[declared["cart_index"]]), prefix + "cart_not_exact_offered_index")
            catalog = call("catalog")
            self.need(catalog is not None and equal(catalog.get("public_return"), offered), prefix + "cart_offers_not_original_catalog_return")
            self.need(type(selected) is dict and all(key in selected for key in ("cart_id", "item_label", "amount", "currency")), prefix + "original_cart_display_fields_missing")
        if payment:
            offered = payment.get("offered", {})
            aliases = offered.get("payment_method_aliases", []) if type(offered) is dict else []
            methods = call("payment-methods")
            self.need(type(aliases) is list and len(aliases) > declared["payment_method_index"] and equal(payment.get("selected"), aliases[declared["payment_method_index"]]), prefix + "payment_not_exact_offered_index")
            self.need(methods is not None and equal(methods.get("public_return"), offered), prefix + "payment_offers_not_original_return")
        wallet, shipping, approval = event("human-wallet-consent"), event("public-shipping-display"), event("human-cart-confirmation")
        if wallet:
            self.need(wallet.get("consent") is declared["wallet_consent"] and wallet.get("user_email") == declared["user_email"], prefix + "wallet_facts_mismatch")
        if shipping:
            shipping_call = call("shipping")
            self.need(shipping_call is not None and equal(shipping.get("address"), shipping_call.get("public_return")), prefix + "shipping_not_original_return")
        if approval:
            self.need(approval.get("approved") is declared["confirm_cart"] and equal(approval.get("cart"), selected)
                      and shipping is not None and equal(approval.get("shipping"), shipping.get("address"))
                      and payment is not None and equal(approval.get("payment_method"), payment.get("selected")), prefix + "cart_confirmation_display_mismatch")
        checkout_call = call("checkout")
        checkout = checkout_call.get("public_return") if checkout_call else None
        if type(checkout) is dict and type(selected) is dict:
            self.need(all(equal(checkout.get(key), selected.get(key)) for key in ("cart_id", "item_label", "amount", "currency")), prefix + "checkout_does_not_match_selected_original_offer")
            if type(checkout.get("checkout_jwt")) is str:
                expected_hash = base64.urlsafe_b64encode(hashlib.sha256(checkout["checkout_jwt"].encode()).digest()).rstrip(b"=").decode()
                self.need(checkout.get("checkout_hash") == expected_hash, prefix + "checkout_hash_not_returned_jwt_hash")

        ch = challenge(pending)
        otp_request, human = event("public-otp-request"), event("explicit-human-otp")
        if otp_request:
            self.need(ch is not None and equal(otp_request.get("challenge"), ch) and otp_request.get("merchant_task_id") == pending.get("id")
                      and otp_request.get("context_id") == pending.get("contextId"), prefix + "otp_request_not_initial_public_challenge")
        if human:
            self.need(equal(human.get("response"), declared["otp_response"]), prefix + "human_reply_changed")
        if declared["otp_response"] is None:
            self.need(not any(row.get("phase") in {"payment-otp", "adverse-original-payment-otp", "repeat-original-otp"} for row in calls), prefix + "otp_dispatched_without_human_reply")
        final_summary = task_summary(final)
        current_receipts = receipts(final)
        for receipt in current_receipts + receipts(repeated):
            self.need(type(receipt) is dict, prefix + "receipt_not_public_object")
            if type(receipt) is not dict:
                continue
            self.need(all(key in receipt for key in ("status", "iss", "iat", "reference", "payment_id")), prefix + "receipt_base_fields_missing")
            if receipt.get("status") == "Success":
                self.need(type(receipt.get("iat")) is int and type(receipt.get("iss")) is str
                          and all(type(receipt.get(key)) is str and receipt.get(key) for key in ("reference", "payment_id", "psp_confirmation_id", "network_confirmation_id")), prefix + "success_receipt_field_types_missing")
                self.need(receipt.get("payment_id") == receipt.get("psp_confirmation_id") == receipt.get("network_confirmation_id"), prefix + "original_receipt_confirmation_fields_differ")
            elif receipt.get("status") == "Error":
                self.need(all(type(receipt.get(key)) is str for key in ("error", "error_description")), prefix + "error_receipt_fields_missing")
            else:
                self.need(False, prefix + "receipt_status_outside_original_schema")
            mandate = call("payment-mandate")
            token = mandate.get("public_return") if mandate else None
            if type(token) is str:
                closed_jwt = token.rsplit("~~", 1)[-1].split("~", 1)[0]
                expected_reference = base64.urlsafe_b64encode(hashlib.sha256(closed_jwt.encode()).digest()).rstrip(b"=").decode()
                self.need(receipt.get("reference") == expected_reference, prefix + "receipt_reference_not_prior_returned_closed_payment_mandate")

        authority = {"fault_event": event("received-public-authority-fault"), "disposition_event": event("adverse-read-disposition"),
                     "original_rpc_error_event": event("adverse-original-rpc-error"), "recovery_event": event("recover-from-prior-public-task")}
        fault, recovery = authority["fault_event"], authority["recovery_event"]
        if fault:
            self.need(declared["fault"] == "other_original_context" and fault.get("fault") == declared["fault"]
                      and type(pending) is dict and type(fault.get("received")) is str and fault.get("received") != pending.get("contextId")
                      and call("other-original-catalog") is not None, prefix + "adverse_context_not_distinct_original_call_observation")
            adverse = one(reads, "phase", "adverse-authority-read")
            disposition = authority["disposition_event"]
            if disposition:
                self.need(disposition.get("disposition") == "owned_caller_context_check_refused_actual_public_task"
                          and adverse is not None and "refused_public_observation" in adverse,
                          prefix + "owned_refusal_disposition_without_actual_refused_task")
            if adverse and "refused_public_observation" in adverse:
                refused = adverse["refused_public_observation"].get("task", {})
                self.need(adverse.get("error_type") == "PublicTaskAuthorityError" and adverse.get("query", {}).get("caller_context") == fault.get("received")
                          and refused.get("id") == pending.get("id") and refused.get("contextId") == pending.get("contextId"), prefix + "adverse_refusal_not_actual_prior_task_foreign_held_context")
        if recovery:
            self.need(type(pending) is dict and recovery.get("task_id") == pending.get("id") and recovery.get("context_id") == pending.get("contextId"), prefix + "recovery_not_prior_returned_public_authority")
            positions = {kind: [i for i, row in enumerate(raw_events) if row.get("kind") == kind] for kind in ("received-public-authority-fault", "recover-from-prior-public-task")}
            refused_positions = [i for i, row in enumerate(raw_events) if row.get("kind") == "public-task-read-error" and row.get("phase") == "adverse-authority-read"]
            self.need(len(refused_positions) == 1 and len(positions["received-public-authority-fault"]) == 1 and len(positions["recover-from-prior-public-task"]) == 1
                      and positions["received-public-authority-fault"][0] < refused_positions[0] < positions["recover-from-prior-public-task"][0], prefix + "recovery_before_actual_adverse_refusal")

        repeat_event = event("public-repeat-observation")
        if repeat_event:
            self.need(equal(repeat_event.get("task"), repeated) and equal(repeat_event.get("receipts"), receipts(repeated)), prefix + "repeat_event_not_actual_repeated_public_read")
            self.need(type(final) is dict and final.get("status", {}).get("state") == "completed" and len(current_receipts) == 1
                      and call("repeat-original-otp") is not None, prefix + "repeat_without_prior_completed_receipt_and_call")
            prior_positions = [i for i, row in enumerate(raw_events) if row.get("kind") == "public-task-read-return" and row.get("phase") == "after-original-otp"]
            repeat_positions = [i for i, row in enumerate(raw_events) if row.get("kind") == "original-call-start" and row.get("phase") == "repeat-original-otp"]
            repeated_positions = [i for i, row in enumerate(raw_events) if row.get("kind") == "public-task-read-return" and row.get("phase") == "after-repeated-original-otp"]
            self.need(len(prior_positions) == len(repeat_positions) == len(repeated_positions) == 1
                      and prior_positions[0] < repeat_positions[0] < repeated_positions[0], prefix + "repeat_read_order_not_after_prior_completion_and_repeat_call")
        semantic_capture = any("public_return" in row for row in calls) or bool(tasks)
        completed = bool(final_summary and final_summary["state"] == "completed" and len(current_receipts) == 1)
        wrong_observed = bool(declared["otp_response"] == "wrong-human-reply" and human and final_summary
                              and final_summary["state"] == "input-required" and not current_receipts
                              and "Challenge response incorrect." in final_summary["status_text"]
                              and call("payment-otp") is not None)
        waiting_observed = bool(declared["otp_response"] is None and human and ch and final_summary
                                and final_summary["state"] == "input-required" and not current_receipts
                                and equal(final_summary["otp_challenge"], ch))
        failed = bool(actor and actor.get("error")) or parent.get("status") not in {"executed_returned", None}
        refusal_in_case = [row for row in self.local_refusals
                           if parent.get("started_at") and parent.get("finished_at")
                           and parent["started_at"] <= row.get("time", "") <= parent["finished_at"]]
        local_budget_message = bool(final_summary and any("owned_provider_budget_or_prior_failure" in text for text in final_summary["status_text"]))
        owned_byte_stop = bool(local_budget_message and refusal_in_case and self.byte_boundary_by_exclusion)
        disposition = ("no_semantic_response_captured" if not semantic_capture else
                       "owned_byte_budget_stop_before_repeat_prerequisite_completed" if owned_byte_stop and declared["repeat_after_completed"] else
                       "owned_byte_budget_stop_with_partial_public_observations" if owned_byte_stop else
                       "failed_or_partial_attempt_with_public_observations" if failed else
                       "wrong_reply_public_refusal_observed" if wrong_observed else
                       "waiting_without_human_reply_observed" if waiting_observed else
                       "completed_public_receipt_observed" if completed else "partial_public_observations_retained")
        return {"case_id": case_id, "declared_public_facts": declared, "parent_status": parent.get("status"),
                "caller_status": actor.get("status") if actor else None, "caller_error": actor.get("error") if actor else None,
                "disposition": disposition, "semantic_response_captured": semantic_capture,
                "actor_result_present": actor is not None, "raw_public_event_count": len(raw_events),
                "original_call_started_count": sum(row.get("kind") == "original-call-start" for row in raw_events),
                "original_call_terminal_count": len(calls), "original_call_return_count": sum("public_return" in row for row in calls),
                "original_call_phases": [row.get("phase") for row in calls],
                "original_call_errors": [{key: row.get(key) for key in ("phase", "error_type", "error")} for row in calls if "error_type" in row],
                "public_offered_cart_selection": cart, "public_offered_payment_selection": payment,
                "wallet_consent": wallet, "shipping_display": shipping, "cart_confirmation": approval,
                "checkout_display_fields": {key: checkout.get(key) for key in ("cart_id", "item_label", "amount", "amount_cents", "currency", "checkout_hash")} if type(checkout) is dict else None,
                "public_tasks": tasks, "initial_task": task_summary(pending), "final_task": final_summary,
                "otp_request": otp_request, "explicit_human_reply": human,
                "exact_reply_in_actor_event": bool(human and equal(human.get("response"), declared["otp_response"])),
                "exact_reply_present_in_retained_task_messages": bool(final_summary and declared["otp_response"] in final_summary["retained_task_message_challenge_responses"]),
                "wrong_reply_public_refusal_observed": wrong_observed, "waiting_without_human_reply_observed": waiting_observed,
                "prior_completed_receipt_observed": completed, "authority_observations": authority,
                "owned_budget_stop_observed": bool(local_budget_message and refusal_in_case),
                "owned_total_request_byte_branch_inferred_by_exclusion": owned_byte_stop,
                "case_window_local_refusals": refusal_in_case,
                "failure_attribution": "owned_accounting_boundary_then_original_failed_public_task; upstream model/server failure not established" if owned_byte_stop else None,
                "repeat_task": task_summary(repeated), "repeat_event": repeat_event,
                "repeat_receipts_equal_prior_receipts": equal(receipts(repeated), current_receipts) if repeated is not None else None,
                "consistency_questions": self.issues[question_start:], "whole_task_grade": None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retained-root", type=Path, required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    analysis = Analysis(args.retained_root.resolve(strict=True))
    retention = analysis.read_json(analysis.retained / "retention.json", required=True)
    analysis.need(retention.get("run_id") == EXPECTED_RUN and retention.get("head_sha") == EXPECTED_HEAD
                  and retention.get("archive_sha256") == args.archive_sha256 and retention.get("digest_matches_api") is True, "root_retention_run_head_archive_binding_mismatch")
    manifest = analysis.read_json(analysis.retained / "extracted-manifest.json", required=True)
    analysis.members = {row["path"]: {key: row[key] for key in ("bytes", "sha256")} for row in manifest.get("files", [])}
    analysis.need(len(analysis.members) == len(manifest.get("files", [])), "duplicate_root_manifest_member")
    plan = analysis.read_json(analysis.capture / "plan/plan.json", required=True)
    result = analysis.read_json(analysis.capture / "execution/result.json", required=True)
    declared = facts()
    analysis.need(plan.get("schema_version") == "ap2-original-native-provider-screen/2" and equal(plan.get("facts"), declared), "plan_not_five_fixed_v2_cases")
    rows = result.get("cases", [])
    analysis.need(result.get("schema_version") == "ap2-original-native-provider-screen-result/2"
                  and [row.get("case_id") for row in rows] == [row["case_id"] for row in declared], "closing_five_case_census_mismatch")
    parent = {row["case_id"]: row for row in rows}
    analysis.local_refusals = analysis.lines(analysis.capture / "execution/provider/local-refusals.jsonl")
    provider, limits = result.get("provider", {}), plan.get("limits", {})
    analysis.byte_boundary_by_exclusion = bool(
        len(analysis.local_refusals) == 1 and provider.get("failed") is False
        and provider.get("upstream_allocations", 0) < limits.get("upstream_calls_including_smoke", 0)
        and provider.get("observed_usage_tokens", 0) < limits.get("maximum_observed_usage_tokens_before_stopping", 0)
        and provider.get("cumulative_request_bytes", 0) <= limits.get("maximum_total_request_bytes", 0))
    cases = [analysis.case(row, parent.get(row["case_id"], {})) for row in declared]
    report = {"schema_version": "ap2-original-native-provider-public-semantic-observations/2",
              "completed_at": datetime.now(timezone.utc).isoformat(), "expected_run_id": EXPECTED_RUN,
              "expected_head_sha": EXPECTED_HEAD, "root_retention": retention,
              "analyzer_source": {"path": str(Path(__file__).resolve()), **digest(Path(__file__).read_bytes())},
              "status": "retained_public_observations_consistent" if not analysis.issues else "public_capture_consistency_questions_retained",
              "integrity_questions": analysis.issues, "cases": cases,
              "case_disposition_counts": dict(Counter(row["disposition"] for row in cases)),
              "semantic_response_case_count": sum(row["semantic_response_captured"] for row in cases),
              "public_receipt_case_count": sum(row["prior_completed_receipt_observed"] for row in cases),
              "owned_boundary_observations": {"closing_provider_summary": provider, "fixed_limits": limits,
                                              "local_refusals": analysis.local_refusals,
                                              "total_request_byte_branch_inferred_by_exclusion": analysis.byte_boundary_by_exclusion,
                                              "inference_limit": "The refused request payload and byte count were not retained. The byte branch is inferred from the bound implementation, first local refusal, no prior provider failure, and remaining call/token limits; raw provider reconciliation is separate."},
              "evidence_bindings": analysis.evidence,
              "original_app_sdk_model_actor_solver_evaluator_checker_imports_or_executions": 0,
              "provider_requests_by_analyzer": 0, "human_gold_qualified": False, "whole_task_grade": None,
              "limitations": ["Root's separate independent raw review owns archive/native/runtime/provider reconciliation.",
                              "Actor choices and source-bound calls establish caller observations; retained Task message fields add public evidence but do not establish exact wire attribution.",
                              "An observed public receipt is a sample artifact, not real-world settlement or human-qualified gold.",
                              "Repeated public Tasks/receipts do not establish idempotency, hidden-effect uniqueness or durability.",
                              "All partial, failed and unexecuted branches remain in the five-case census; no scientific checkpoint, unchanged ADK shopper or bridge qualification is granted."]}
    args.output.mkdir(parents=True, exist_ok=False)
    with (args.output / "analysis.json").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"status": report["status"], "semantic_response_cases": report["semantic_response_case_count"],
                      "public_receipt_cases": report["public_receipt_case_count"], "questions": len(analysis.issues),
                      "analysis_path": str(args.output / "analysis.json")}))


if __name__ == "__main__":
    main()
