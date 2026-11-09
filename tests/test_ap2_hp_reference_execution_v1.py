"""Constructed injected reference/capture tests; no original application import."""
from __future__ import annotations

import asyncio
import base64
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
import uuid


ROOT = Path(__file__).absolute().parents[1]


def load(name, relative):
    import sys
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


execution = load("_ap2_injected_execution", "src/interoperability/ap2_hp_reference_execution_v1.py")
capture = load("_ap2_injected_capture", "src/interoperability/ap2_hp_passive_capture_v1.py")
planner = load("_ap2_frozen_planning_dependency", "src/interoperability/ap2_hp_reference_plan_v1.py")


class PublicModel:
    def __init__(self, payload):
        self.payload = payload

    def model_dump(self, **kwargs):
        return deepcopy(self.payload)


class InjectedBuilder:
    """Disclosed stand-in; its UUIDs are not original SDK execution evidence."""
    def __init__(self):
        self.message = {"kind": "message", "role": "agent", "messageId": uuid.uuid4().hex, "parts": []}

    def set_context_id(self, value):
        self.message["contextId"] = value
        return self

    def set_task_id(self, value):
        self.message["taskId"] = value
        return self

    def add_text(self, value):
        self.message["parts"].append({"kind": "text", "text": value})
        return self

    def add_data(self, key, value):
        if value:
            self.message["parts"].append({"kind": "data", "data": {key: deepcopy(value)}})
        return self

    def build(self):
        return self.message


def task(identity, key=None, value=None, state="completed", context="shopping", challenge=False):
    result = {"kind": "task", "id": identity, "contextId": context, "status": {"state": state}, "artifacts": []}
    if key is not None:
        result["artifacts"] = [{"parts": [{"kind": "data", "data": {key: value}}]}]
    if challenge:
        result["status"]["message"] = {"kind": "message", "parts": [{"kind": "data", "data": {
            "challenge": {"type": "otp", "display_text": "Enter the supplied code"}}}]}
    return PublicModel(result)


class QueueClient:
    def __init__(self, values, card=None):
        self.values, self.messages = list(values), []
        self.card = card

    async def send_a2a_message(self, message):
        self.messages.append(message)
        value = self.values.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value

    async def get_agent_card(self):
        return self.card


def fixture(*, response="123", association_state="completed", hidden_challenge=False, final_id="payment", duplicate_cart=False):
    cart = {"cart_id": "cart", "item_label": "Coffee maker", "amount": 10, "currency": "USD"}
    address = {"address_line": ["1 Public Street"], "city": "Example"}
    jwt = "constructed-checkout-jwt"
    checkout = {**cart, "amount_cents": 1000, "checkout_jwt": jwt,
                "checkout_hash": base64.urlsafe_b64encode(hashlib.sha256(jwt.encode()).digest()).decode().rstrip("=")}
    catalog = task("catalog", "ap2.cart", cart)
    if duplicate_cart:
        catalog.payload["artifacts"] *= 2
    start = task("payment", state="input_required", challenge=not hidden_challenge)
    if hidden_challenge:
        start.payload["status"]["challenge"] = {"type": "otp", "display_text": "Hidden projection"}
    final = task(final_id, state="completed" if response == "123" else "input_required")
    association = task("association", state=association_state)
    merchant_raw = QueueClient([catalog, task("checkout", "ap2.checkout", checkout), start, final])
    cp_raw = QueueClient([task("shipping", planner.ADDRESS_KEY, address),
                          task("methods", "payment_method_aliases", ["alias"]),
                          task("token", "token", "constructed-public-token"), association],
                         PublicModel({"url": execution.CREDENTIALS}))
    merchant = execution.PublicClientObserver(merchant_raw, execution.MERCHANT)
    cp = execution.PublicClientObserver(cp_raw, execution.CREDENTIALS)
    operations = []

    async def products(search, context, debug_mode=False):
        returned = await merchant.send_a2a_message({"constructed_phase": "catalog"})
        context.state.update(shopping_context_id=returned.payload["contextId"], available_carts=[cart], risk_data=planner.RISK_DATA)
        return [PublicModel(cart)]

    def select(identity, context):
        context.state["chosen_cart_id"] = identity
        return "Selected returned cart"

    async def shipping(email, context):
        await cp.send_a2a_message({"constructed_phase": "shipping"})
        return PublicModel(address)

    async def methods(email, context):
        await cp.send_a2a_message({"constructed_phase": "methods"})
        return {"payment_method_aliases": ["alias"]}

    async def token(email, alias, context):
        await cp.send_a2a_message({"constructed_phase": "token"})
        card = await cp.get_agent_card()
        context.state["payment_credential_token"] = {"value": "constructed-public-token", "url": card.payload["url"]}
        return {"status": "success", "token": "constructed-public-token"}

    async def create_checkout(context, debug_mode=False):
        await merchant.send_a2a_message({"constructed_phase": "checkout"})
        context.state["checkout_data"] = deepcopy(checkout)
        return deepcopy(checkout)

    def checkout_mandate(context):
        operations.append("checkout_signer")
        context.state.update(checkout_mandate_sdjwt="constructed-checkout-mandate", checkout_hash=checkout["checkout_hash"])
        return context.state["checkout_mandate_sdjwt"]

    def payment_mandate(context):
        operations.append("payment_signer")
        context.state["payment_mandate_sdjwt"] = "constructed-payment-mandate"
        return context.state["payment_mandate_sdjwt"]

    async def associate(context, debug_mode=False):
        await cp.send_a2a_message({"constructed_phase": "association"})
        return "Successfully sent mandates to the credentials provider."

    def receipt(returned, context):
        operations.append(("public_receipt_extract", returned))

    bindings = execution.ReferenceBindings(merchant, cp, InjectedBuilder, products, select, shipping,
        methods, token, create_checkout, checkout_mandate, payment_mandate, associate, receipt)
    coordinator = execution.ReferenceCoordinator(bindings, planner.ReferencePlan,
        {"catalog_search": "coffee maker", "user_email": "declared@example.test", "currency": "USD", "max_amount_cents": 2000})
    decisions = {"choose_cart": lambda carts: "cart", "choose_alias": lambda aliases: "alias",
                 "approve": lambda summary: {"approved": True, "summary": summary},
                 "respond_otp": lambda challenge: response}
    return SimpleNamespace(coordinator=coordinator, bindings=bindings, decisions=decisions, operations=operations,
                           merchant=merchant_raw, cp=cp_raw, association=association, start=start, final=final)


class ReferenceExecutionTests(unittest.TestCase):
    def setUp(self):
        self.artifacts = []

    def tearDown(self):
        root = os.environ.get("AP2_EXECUTION_TEST_ARTIFACT_ROOT")
        if root:
            target = Path(root) / (self._testMethodName + ".json")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("x", encoding="utf-8") as stream:
                json.dump({"test": self.id(), "constructed_artifacts": self.artifacts}, stream, indent=2, allow_nan=False)

    def run_reference(self, f):
        outcome = asyncio.run(f.coordinator.run(**f.decisions))
        self.artifacts.append(outcome.report())
        return outcome

    def test_full_public_sequence_and_exact_payment_forms(self):
        f = fixture()
        outcome = self.run_reference(f)
        self.assertEqual(outcome.status, "public_sequence_observed")
        self.assertIs(outcome.final_task, f.final)
        self.assertIn(f.association, [call["returned"] for call in outcome.public_calls])
        self.assertIn(("cp_association", "Successfully sent mandates to the credentials provider."), outcome.tool_returns)
        start, resume = f.merchant.messages[-2:]
        self.assertEqual(start["parts"][0]["text"], "Initiate a payment")
        self.assertEqual(resume["parts"][0]["text"], "Initiate a payment. Include the challenge response.")
        self.assertEqual([next(iter(part["data"])) for part in start["parts"][1:]],
                         [execution.PAYMENT, "risk_data", "shopping_agent_id", execution.CHECKOUT])
        self.assertEqual([next(iter(part["data"])) for part in resume["parts"][1:]],
                         [execution.PAYMENT, "shopping_agent_id", "challenge_response", "risk_data", execution.CHECKOUT])
        self.assertEqual(resume["taskId"], "payment")
        self.assertEqual(resume["contextId"], start["contextId"])
        self.assertNotEqual(start["messageId"], resume["messageId"])
        self.assertIsNone(outcome.report()["aggregate_task_grade"])
        attempts = [row for row in outcome.public_records if row["boundary"] == "attempt"]
        self.assertEqual([row["endpoint"] for row in attempts[:6]],
                         [execution.MERCHANT, execution.CREDENTIALS, execution.CREDENTIALS,
                          execution.CREDENTIALS, execution.CREDENTIALS, execution.MERCHANT])
        self.assertEqual([row["global_sequence"] for row in outcome.public_records], list(range(len(outcome.public_records))))

    def test_empty_and_wrong_otp_remain_explicit_without_correction(self):
        for response in ("", "wrong"):
            f = fixture(response=response)
            outcome = self.run_reference(f)
            self.assertEqual(outcome.status, "public_sequence_observed")
            parts = f.merchant.messages[-1]["parts"]
            supplied = [part["data"]["challenge_response"] for part in parts if "challenge_response" in part.get("data", {})]
            self.assertEqual(supplied, [] if response == "" else [response])
            self.assertEqual(outcome.planning_report["caller_state"]["supplied_merchant_after"]["status"]["state"], "input_required")

    def test_invalid_or_ambiguous_cart_stops_before_credentials(self):
        for duplicate in (False, True):
            f = fixture(duplicate_cart=duplicate)
            f.decisions["choose_cart"] = lambda carts: "invented"
            outcome = self.run_reference(f)
            self.assertEqual(outcome.status, "refused_or_partial_reference")
            self.assertEqual(f.cp.messages, [])
            self.assertEqual(f.operations, [])

    def test_typed_actual_checkout_approval_precedes_signers(self):
        f = fixture()
        def bad_approval(summary):
            summary["amount_cents"] = 1000.0
            return {"approved": True, "summary": summary}
        f.decisions["approve"] = bad_approval
        outcome = self.run_reference(f)
        self.assertEqual(outcome.phase, "approval")
        self.assertEqual(f.operations, [])
        self.assertEqual(len(f.cp.messages), 3)

    def test_hidden_challenge_cannot_drive_public_otp(self):
        f = fixture(hidden_challenge=True)
        f.decisions["respond_otp"] = lambda _: self.fail("Hidden challenge reached responder")
        outcome = self.run_reference(f)
        self.assertEqual(outcome.phase, "payment_start")
        self.assertEqual(len(f.merchant.messages), 3)
        self.assertIn(f.start, [call["returned"] for call in outcome.public_calls])

    def test_cross_task_resume_is_retained_and_rejected(self):
        f = fixture(final_id="processor-child")
        outcome = self.run_reference(f)
        self.assertEqual(outcome.phase, "payment_resume")
        self.assertIs(outcome.final_task, f.final)
        self.assertEqual(f.merchant.messages[-1]["taskId"], "payment")
        self.assertFalse(outcome.report()["native_qualification_established"])

    def test_discarded_failed_association_task_prevents_payment(self):
        f = fixture(association_state="failed")
        outcome = self.run_reference(f)
        self.assertEqual(outcome.phase, "cp_association")
        self.assertEqual(len(f.merchant.messages), 2)
        self.assertIn(f.association, [call["returned"] for call in outcome.public_calls])
        self.assertIn(("cp_association", "Successfully sent mandates to the credentials provider."), outcome.tool_returns)

    def test_public_observer_preserves_return_and_original_error_identity(self):
        returned, error = PublicModel({"kind": "task"}), RuntimeError("constructed error")
        raw = QueueClient([returned, error])
        observer = execution.PublicClientObserver(raw, execution.MERCHANT)
        self.assertIs(asyncio.run(observer.send_a2a_message({"kind": "message"})), returned)
        with self.assertRaises(RuntimeError) as caught:
            asyncio.run(observer.send_a2a_message({"kind": "message"}))
        self.assertIs(caught.exception, error)
        self.assertIs(observer.calls[-1]["error"], error)
        returned.payload["kind"] = "mutated-later"
        self.assertEqual(observer.calls[0]["public_result"], {"kind": "task"})
        self.artifacts.append(observer.records)

    def test_public_sink_failure_is_neutral_and_coordinator_refuses_continuation(self):
        f = fixture()
        def broken_sink(row):
            raise OSError("constructed recording failure")
        f.bindings.merchant.sink = broken_sink
        outcome = self.run_reference(f)
        self.assertEqual(len(f.merchant.messages), 1)
        self.assertEqual(f.cp.messages, [])
        self.assertIsNotNone(f.bindings.merchant.calls[0]["returned"])
        self.assertFalse(f.bindings.merchant.capture_complete)
        self.assertEqual(outcome.phase, "catalog")

    def test_asgi_exact_scope_events_chunk_order_and_public_field_projection(self):
        scope = {"type": "http", "method": "POST", "path": "/a2a/merchant_agent", "raw_path": b"/a2a/%6derchant_agent",
                 "query_string": b"a=1&a=2", "headers": [(b"x-a2a-extensions", execution.EXTENSION.encode()),
                 (b"x-repeat", b"1"), (b"x-repeat", b"2")], "app": object(), "private_store": object()}
        incoming = [{"type": "http.request", "body": b"\x00first", "more_body": True},
                    {"type": "http.request", "body": b"last\xff", "more_body": False}]
        outgoing = [{"type": "http.response.start", "status": 200, "headers": [(b"x-repeat", b"1"), (b"x-repeat", b"2")]},
                    {"type": "http.response.body", "body": b"a\x00", "more_body": True},
                    {"type": "http.response.body", "body": b"\xffb", "more_body": False}]
        sent = []
        async def receive():
            return incoming.pop(0)
        expected_incoming = list(incoming)
        async def send(event):
            sent.append(event)
        async def app(actual, recv, emit):
            self.assertIs(actual, scope)
            for expected in expected_incoming:
                self.assertIs(await recv(), expected)
            for event in outgoing:
                await emit(event)
            return "original-result"
        wrapper = capture.PassiveAsgiCapture(app)
        self.assertEqual(asyncio.run(wrapper(scope, receive, send)), "original-result")
        self.assertTrue(all(left is right for left, right in zip(sent, outgoing)))
        public_scope = wrapper.records[0]["value"]
        self.assertNotIn("private_store", public_scope)
        self.assertNotIn("app", public_scope)
        self.assertEqual(base64.b64decode(public_scope["raw_path"]["data"]), scope["raw_path"])
        bodies = [row["value"]["body"] for row in wrapper.records if row["boundary"] == "send_completed" and "body" in row["value"]]
        self.assertEqual([base64.b64decode(item["data"]) for item in bodies], [b"a\x00", b"\xffb"])
        self.artifacts.append(wrapper.report())

    def test_asgi_recording_failure_never_changes_delivery(self):
        event, delivered = {"type": "http.response.body", "body": b"same"}, []
        async def app(scope, receive, send):
            await send(event)
        async def receive():
            return {"type": "http.disconnect"}
        async def send(actual):
            delivered.append(actual)
        def broken_sink(row):
            raise OSError("constructed failure")
        wrapper = capture.PassiveAsgiCapture(app, broken_sink)
        asyncio.run(wrapper({"type": "http"}, receive, send))
        self.assertIs(delivered[0], event)
        self.assertFalse(wrapper.capture_complete)
        self.artifacts.append(wrapper.report())

    def test_asgi_send_receive_and_application_errors_preserve_identity(self):
        for boundary in ("send", "receive", "application"):
            original = RuntimeError("constructed " + boundary)
            async def receive():
                raise original
            async def send(event):
                raise original
            async def app(scope, recv, emit):
                if boundary == "send":
                    await emit({"type": "http.response.body", "body": b"attempted"})
                elif boundary == "receive":
                    await recv()
                else:
                    raise original
            wrapper = capture.PassiveAsgiCapture(app)
            with self.assertRaises(RuntimeError) as caught:
                asyncio.run(wrapper({"type": "http"}, receive, send))
            self.assertIs(caught.exception, original)
            self.assertEqual(wrapper.records[-1]["boundary"], "application_error")
            self.artifacts.append(wrapper.report())

    def test_owned_factory_failure_still_settles_group(self):
        group = self.group()
        failure = RuntimeError("constructed adapter refusal")
        def factory(actual):
            self.assertIs(actual, group)
            raise failure
        outcome = asyncio.run(execution.run_owned_reference(lambda: group, factory, {}, lambda report: None))
        self.assertTrue(outcome.settled)
        self.assertIs(outcome.error, failure)
        self.assertIs(outcome.group, group)
        self.artifacts.append(outcome.report())

    def test_publication_failure_retains_incomplete_cleanup_authority(self):
        group = self.group(settle=False)
        f = fixture()
        failure = OSError("constructed publication failure")
        def publish(report):
            raise failure
        outcome = asyncio.run(execution.run_owned_reference(lambda: group, lambda _: f.coordinator, f.decisions, publish))
        self.assertIs(outcome.error, failure)
        self.assertFalse(outcome.settled)
        self.assertIs(outcome.group, group)
        self.assertTrue(outcome.report()["live_authority_retained"])
        self.assertEqual(outcome.report()["status"], "cleanup_incomplete_authority_retained")
        self.artifacts.append(outcome.report())

    def test_consumed_coordinator_and_opaque_observation_fail_without_extra_calls(self):
        f = fixture()
        self.run_reference(f)
        counts = (len(f.merchant.messages), len(f.cp.messages))
        repeat = self.run_reference(f)
        self.assertEqual(repeat.status, "refused_or_partial_reference")
        self.assertEqual(counts, (len(f.merchant.messages), len(f.cp.messages)))
        raw = QueueClient([object()])
        observer = execution.PublicClientObserver(raw, execution.MERCHANT)
        returned = asyncio.run(observer.send_a2a_message({"kind": "message"}))
        self.assertIs(returned, observer.calls[0]["returned"])
        self.assertFalse(observer.capture_complete)
        self.assertIsNone(observer.calls[0]["public_result"])
        for invalid in ({1: "converted-key"}, {"nested": [{False: "converted-key"}]}, {"nested": float("nan")}):
            with self.assertRaises(execution.ExecutionError):
                execution.public_json(invalid)
        f.coordinator.context.state["nested"] = {"value": [True]}
        f.coordinator.plan.state["nested"] = {"value": [1]}
        with self.assertRaises(execution.ExecutionError):
            f.coordinator._state_matches("nested")

    @staticmethod
    def group(settle=True):
        group = SimpleNamespace(report={"status": "owned_original_services_ready_without_case_execution"}, owners=[object()])
        def stop():
            if settle:
                group.owners = []
            return settle
        group.stop = stop
        return group


if __name__ == "__main__":
    unittest.main(verbosity=2)
