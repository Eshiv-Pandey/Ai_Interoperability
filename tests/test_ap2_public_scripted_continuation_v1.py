"""Owned caller controls; business doubles do not establish original outcomes."""
from copy import deepcopy
import ast
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import sys

from ap2_public_control_support_v1 import RPCError, fixture, sdk_doubles
from interoperability.ap2_public_scripted_continuation_v1 import PublicScriptedContinuation


def facts(response="123", fault="none", repeat=False):
    return {"case_id": "constructed-caller-control", "catalog_search": "user request", "user_email": "public@example.invalid",
            "cart_index": 0, "payment_method_index": 0, "wallet_consent": True, "confirm_cart": True,
            "otp_response": response, "fault": fault, "repeat_after_completed": repeat}


class ScriptedContinuationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def caller(self, supplied, reads):
        pending = reads[0]
        otp_calls = []
        def find_products(query, context, debug_mode=False):
            context.state["shopping_context_id"] = pending["contextId"] if not context.state.get("other") else "unused"
            return [{"cart_id": "constructed-offered-cart"}]
        def select_cart(choice, context):
            context.state["chosen_cart_id"] = choice
            return "selected"
        def get_shipping(user, context):
            return {"street": "constructed displayed address"}
        def methods(user, context):
            return {"payment_method_aliases": ["constructed offered method"]}
        def token(user, alias, context):
            context.state["payment_credential_token"] = {"value": "constructed token"}
            return {"status": "success"}
        def checkout(context, debug_mode=False):
            context.state["checkout_data"] = {"cart_id": "constructed-offered-cart"}
            return context.state["checkout_data"]
        def checkout_mandate(context):
            context.state["checkout_mandate_sdjwt"] = "constructed signer output"
            return "constructed signer output"
        def payment_mandate(context):
            context.state["payment_mandate_sdjwt"] = "constructed signer output"
            return "constructed signer output"
        def associate(context, debug_mode=False):
            return "Successfully sent mandates to the credentials provider."
        def start(context, debug_mode=False):
            context.state["initiate_payment_task_id"] = pending["id"]
            return "Status: TaskState.input_required"
        def otp(response, context, debug_mode=False):
            otp_calls.append((response, deepcopy(context.state)))
            return "constructed original-tool result"
        business = SimpleNamespace(AGENT_PROVIDER_KEY_PATH=Path(self.temp.name) / "absent-key.pem",
            create_checkout=checkout, create_checkout_mandate=checkout_mandate, create_payment_mandate=payment_mandate,
            send_signed_mandates_to_credentials_provider=associate, initiate_payment=start, initiate_payment_with_otp=otp)
        modules = {"roles.shopping_agent.tools": business,
            "roles.shopping_agent.subagents.shopper.tools": SimpleNamespace(find_products=find_products, select_cart=select_cart),
            "roles.shopping_agent.subagents.shipping_address_collector.tools": SimpleNamespace(get_shipping_address=get_shipping),
            "roles.shopping_agent.subagents.payment_method_collector.tools": SimpleNamespace(get_payment_methods=methods, get_payment_credential_token=token)}
        events = []
        caller = PublicScriptedContinuation(modules, {}, supplied, lambda kind, row: events.append((kind, deepcopy(row))))
        queue = list(reads)
        async def read(phase):
            value = queue.pop(0)
            if isinstance(value, Exception):
                raise value
            caller.public_reads.append({"phase": phase, "public_observation": {"task": deepcopy(value)}})
            return deepcopy(value)
        caller.read = read
        return caller, otp_calls, events

    def test_exact_retained_wire_state_and_nullable_artifacts(self):
        pending = fixture("v7-pending-task.json")
        self.assertEqual(pending["status"]["state"], "input-required")
        self.assertEqual(PublicScriptedContinuation.challenge(pending)["type"], "otp")
        self.assertEqual(PublicScriptedContinuation.receipts(pending), [])
        pending["status"]["state"] = "input_required"
        with self.assertRaisesRegex(ValueError, "actual unique public OTP"):
            PublicScriptedContinuation.challenge(pending)

    def test_actual_retained_completed_receipt_is_observable(self):
        final = fixture("v13-correct-final-task.json")
        self.assertEqual(final["status"]["state"], "completed")
        self.assertEqual(len(PublicScriptedContinuation.receipts(final)), 1)

    def test_known_platform_bootstrap_precedes_strict_descendant_guard(self):
        source = Path(__file__).resolve().parents[1] / "scripts/ap2_public_scripted_continuation_v1.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
        calls = {ast.unparse(node.value.func): index for index, node in enumerate(main.body)
                 if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)}
        audit_index = calls["sys.addaudithook"]
        for method in ("platform.uname", "platform.processor", "platform.platform", "platform.architecture"):
            self.assertLess(calls[method], audit_index)
        guard = next(node for node in main.body if isinstance(node, ast.FunctionDef) and node.name == "guard")
        descendant_branch = next(node for node in guard.body if isinstance(node, ast.If) and "subprocess.Popen" in ast.unparse(node.test))
        self.assertTrue(any(isinstance(node, ast.Raise) for node in ast.walk(descendant_branch)))

    async def test_no_reply_never_dispatches_otp_or_claims_completion(self):
        pending = fixture("v13-correct-pending-task.json")
        caller, calls, _ = self.caller(facts(None), [pending, pending])
        result = await caller.run()
        self.assertEqual(calls, [])
        self.assertEqual(result["status"], "waiting_for_explicit_human_otp")
        self.assertFalse(result["unchanged_adk_root_tool_qualification"])

    async def test_wrong_human_reply_is_preserved_and_remains_incomplete(self):
        pending, final = fixture("v13-wrong-pending-task.json"), fixture("v13-wrong-final-task.json")
        caller, calls, _ = self.caller(facts("wrong explicit reply"), [pending, final])
        result = await caller.run()
        self.assertEqual([row[0] for row in calls], ["wrong explicit reply"])
        self.assertEqual(result["status"], "public_continuation_remains_incomplete")
        self.assertEqual(result["public_final_task"], final)
        self.assertEqual(result["grade"], None)

    async def test_explicit_correct_reply_observes_actual_receipt(self):
        pending, final = fixture("v13-correct-pending-task.json"), fixture("v13-correct-final-task.json")
        caller, calls, _ = self.caller(facts(), [pending, final])
        result = await caller.run()
        self.assertEqual([row[0] for row in calls], ["123"])
        self.assertEqual(result["status"], "completed_with_public_receipt")
        self.assertFalse(result["bridge_qualification_established"])

    async def test_fault_transport_failure_is_not_counted_as_authority_refusal(self):
        pending = fixture("v13-correct-pending-task.json")
        with sdk_doubles() as (_, _):
            caller, calls, events = self.caller(facts(fault="public_nested_processor_task"), [pending, TimeoutError("constructed transport timeout")])
            result = await caller.run()
        self.assertEqual(result["status"], "actual_failed_or_partial_attempt_retained")
        self.assertEqual(len(calls), 1)
        self.assertFalse(any(row[1].get("kind") == "adverse-read-disposition" for row in events))
        self.assertTrue(any(row[1].get("kind") == "unexpected-adverse-read-error" for row in events))

    async def test_actual_task_not_found_code_allows_prior_public_authority_recovery(self):
        pending, final = fixture("v13-correct-pending-task.json"), fixture("v13-correct-final-task.json")
        with sdk_doubles() as (_, _):
            caller, calls, events = self.caller(facts(fault="public_nested_processor_task"), [pending, RPCError(-32001), final])
            result = await caller.run()
        self.assertEqual(result["status"], "completed_with_public_receipt")
        self.assertEqual([row[0] for row in calls], ["123", "123"])
        self.assertEqual(calls[1][1]["initiate_payment_task_id"], pending["id"])
        self.assertEqual(calls[1][1]["shopping_context_id"], pending["contextId"])
        self.assertTrue(any(row[1].get("disposition") == "original_merchant_task_store_returned_task_not_found" for row in events))

    async def test_unexpected_rpc_code_does_not_qualify_authority_fault(self):
        pending = fixture("v13-correct-pending-task.json")
        with sdk_doubles() as (_, _):
            caller, calls, events = self.caller(facts(fault="public_nested_processor_task"), [pending, RPCError(-32000)])
            result = await caller.run()
        self.assertEqual(result["status"], "actual_failed_or_partial_attempt_retained")
        self.assertEqual(len(calls), 1)
        self.assertFalse(any(row[1].get("kind") == "adverse-read-disposition" for row in events))

    async def test_withheld_confirmation_never_signs_or_starts_payment(self):
        supplied = facts()
        supplied["confirm_cart"] = False
        pending = fixture("v13-correct-pending-task.json")
        caller, calls, _ = self.caller(supplied, [pending])
        result = await caller.run()
        self.assertEqual(result["status"], "waiting_for_cart_confirmation")
        self.assertEqual(calls, [])
        phases = [row["phase"] for row in result["original_business_calls"]]
        self.assertFalse(set(phases) & {"checkout-mandate", "payment-mandate", "payment-start"})


if __name__ == "__main__":
    unittest.main()
