"""Constructed planner controls; no AP2/SDK/native/model execution."""
import base64
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("_ap2_reference_plan_test", ROOT / "src/interoperability/ap2_hp_reference_plan_v1.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
NONCE = "a" * 32


def task(phase, *data, state="completed"):
    return {"kind": "task", "id": "constructed-" + phase, "contextId": "returned-context",
            "status": {"state": state}, "artifacts": [{"artifactId": phase,
                "parts": [{"kind": "data", "data": value} for value in data]}]}


class ReferencePlanTests(unittest.TestCase):
    def setUp(self):
        self.plan = module.ReferencePlan({"catalog_search": "coffee maker", "user_email": "declared-demo@example.test",
            "currency": "USD", "max_amount_cents": 10000})
        self.cart = {"cart_id": "returned-cart-7", "item_label": "Returned coffee maker", "amount": 25.0, "currency": "USD"}
        self.catalog = task("catalog", {module.CART_KEY: self.cart})
        self.address = {"recipient": "Demo person", "address_line": ["Demo street"], "phone_number": None}
        self.alias = "Returned eligible payment alias"

    def prefix(self, until="approval"):
        values = {
            "catalog": self.catalog, "cart_selection": self.cart["cart_id"],
            "shipping": task("shipping", {module.ADDRESS_KEY: self.address}),
            "payment_methods": task("methods", {"payment_method_aliases": [self.alias]}),
            "payment_selection": self.alias,
            "credential_token": {"task": task("token", {"token": "returned-token"}),
                "agent_card": {"url": "http://returned-card.example.test/provider"}},
        }
        jwt = "constructed.checkout.jwt"
        checkout = {**self.cart, "amount_cents": 2500, "checkout_jwt": jwt,
            "checkout_hash": base64.urlsafe_b64encode(hashlib.sha256(jwt.encode()).digest()).decode().rstrip("=")}
        values["checkout"] = task("checkout", {"ap2.checkout": checkout})
        for phase in module.PHASES:
            if phase == until:
                break
            self.plan.observe(phase, deepcopy(values[phase]))

    def payment_prefix(self):
        self.prefix()
        self.plan.observe("approval", {"approved": True, "summary": self.plan.approval_summary()})
        self.plan.observe("checkout_mandate", "supplied-original-checkout-mandate~")
        self.plan.observe("payment_mandate", "supplied-original-payment-mandate~")
        self.plan.observe("cp_association", task("association"))

    def pending(self):
        value = task("payment", state="input_required")
        value["status"]["message"] = {"kind": "message", "messageId": "forwarded-child-message", "taskId": "public-child-task",
            "contextId": "returned-context", "role": "agent", "parts": [{"kind": "text", "text": "Provide OTP"},
                {"kind": "data", "data": {"challenge": {"type": "otp", "display_text": "Original public OTP request"}}}]}
        return value

    def test_initial_source_message_and_falsey_omission(self):
        action = self.plan.next_action(message_id=NONCE)
        message = action["message"]
        self.assertEqual(message["parts"][0]["text"], "Find products that match the user's request.")
        self.assertNotIn("contextId", message)
        self.assertNotIn("taskId", message)
        self.assertEqual([next(iter(part["data"])) for part in message["parts"][1:]],
            ["catalog_search", "risk_data", "shopping_agent_id"])
        self.assertEqual(action["transport_preconditions"]["extension_header"], "X-A2A-Extensions")
        self.assertFalse(action["dispatch_eligible"])

    def test_falsey_data_omitted_with_order_preserved(self):
        message = module.exact_message("source text", [("false", False), ("empty", ""), ("zero", 0),
            ("none", None), ("first", "one"), ("second", {"k": None})], message_id=NONCE)
        self.assertEqual([next(iter(part["data"])) for part in message["parts"][1:]], ["first", "second"])

    def test_dynamic_cart_alias_context_and_token_card_url(self):
        self.prefix()
        self.assertEqual(self.plan.state["chosen_cart_id"], "returned-cart-7")
        self.assertEqual(self.plan.state["payment_method_alias"], self.alias)
        self.assertEqual(self.plan.state["shopping_context_id"], "returned-context")
        self.assertEqual(self.plan.state["payment_credential_token"], {"value": "returned-token", "url": "http://returned-card.example.test/provider"})

    def test_unreturned_cart_refused_without_state_advancement(self):
        self.plan.observe("catalog", self.catalog)
        before = self.plan.report()
        with self.assertRaisesRegex(module.PlanningError, "returned cart"):
            self.plan.observe("cart_selection", "invented-cart")
        self.assertEqual(self.plan.report(), before)

    def test_duplicate_cart_identity_refused(self):
        self.catalog["artifacts"][0]["parts"].append(deepcopy(self.catalog["artifacts"][0]["parts"][0]))
        with self.assertRaisesRegex(module.PlanningError, "Duplicate"):
            self.plan.observe("catalog", self.catalog)

    def test_selection_exceeding_contract_refused(self):
        self.cart["amount"] = 101.0
        self.plan.observe("catalog", self.catalog)
        with self.assertRaisesRegex(module.PlanningError, "spending contract"):
            self.plan.observe("cart_selection", self.cart["cart_id"])

    def test_alias_must_be_actually_returned(self):
        self.prefix("payment_selection")
        with self.assertRaisesRegex(module.PlanningError, "returned eligible alias"):
            self.plan.observe("payment_selection", "invented-alias")

    def test_cross_context_prelude_refused(self):
        self.prefix("shipping")
        value = task("shipping", {module.ADDRESS_KEY: self.address})
        value["contextId"] = "other-context"
        with self.assertRaisesRegex(module.PlanningError, "different shopping context"):
            self.plan.observe("shipping", value)

    def test_new_prelude_reusing_task_refused(self):
        self.prefix("shipping")
        value = task("shipping", {module.ADDRESS_KEY: self.address})
        value["id"] = self.catalog["id"]
        with self.assertRaisesRegex(module.PlanningError, "reused"):
            self.plan.observe("shipping", value)

    def test_checkout_must_bind_selected_offer_and_exact_hash(self):
        self.prefix("checkout")
        value = task("checkout", {"ap2.checkout": {**self.cart, "amount_cents": 2500,
            "checkout_jwt": "constructed.jwt", "checkout_hash": "wrong-hash"}})
        with self.assertRaisesRegex(module.PlanningError, "exact JWT"):
            self.plan.observe("checkout", value)

    def test_checkout_bool_major_amount_not_zero_price(self):
        self.cart["amount"] = 0.0
        self.prefix("checkout")
        jwt = "constructed.jwt"
        value = task("checkout", {"ap2.checkout": {**self.cart, "amount": False, "amount_cents": 0,
            "checkout_jwt": jwt, "checkout_hash": base64.urlsafe_b64encode(hashlib.sha256(jwt.encode()).digest()).decode().rstrip("=")}})
        with self.assertRaisesRegex(module.PlanningError, "major amount"):
            self.plan.observe("checkout", value)

    def test_address_known_field_types_checked(self):
        self.prefix("shipping")
        with self.assertRaisesRegex(module.PlanningError, "string/null"):
            self.plan.observe("shipping", task("shipping", {module.ADDRESS_KEY: {"recipient": False}}))
        with self.assertRaisesRegex(module.PlanningError, "no source ContactAddress field"):
            self.plan.observe("shipping", task("shipping", {module.ADDRESS_KEY: {"bogus": "address"}}))

    def test_explicit_approval_is_actual_summary_and_typed(self):
        self.prefix()
        summary = self.plan.approval_summary()
        wrong = deepcopy(summary); wrong["amount_cents"] = 2500.0
        with self.assertRaisesRegex(module.PlanningError, "typed"):
            self.plan.observe("approval", {"approved": True, "summary": wrong})
        wrong = deepcopy(summary); wrong["shipping_address"]["phone_number"] = False
        with self.assertRaisesRegex(module.PlanningError, "typed"):
            self.plan.observe("approval", {"approved": True, "summary": wrong})
        self.plan.observe("approval", {"approved": True, "summary": summary})
        self.assertEqual(self.plan.phase, "checkout_mandate")

    def test_out_of_order_signing_refused(self):
        self.prefix()
        with self.assertRaisesRegex(module.PlanningError, "out of order"):
            self.plan.observe("payment_mandate", "invented-signer-result")

    def test_exact_source_payment_forms_and_merchant_resume_only(self):
        self.payment_prefix()
        start = self.plan.next_action(message_id=NONCE)
        self.assertEqual(start["endpoint"], module.MERCHANT)
        self.assertNotIn("taskId", start["message"])
        self.assertEqual([next(iter(part["data"])) for part in start["message"]["parts"][1:]],
            [module.MANDATE_KEY, "risk_data", "shopping_agent_id", module.CHECKOUT_MANDATE_KEY])
        self.plan.observe("payment_start", self.pending())
        self.plan.observe("otp_response", "wrong-otp")
        resume = self.plan.next_action(message_id="b" * 32)
        self.assertEqual(resume["endpoint"], module.MERCHANT)
        self.assertEqual(resume["message"]["taskId"], "constructed-payment")
        self.assertEqual(resume["message"]["contextId"], "returned-context")
        self.assertNotIn("public-child-task", json.dumps(resume))
        self.assertEqual([next(iter(part["data"])) for part in resume["message"]["parts"][1:]],
            [module.MANDATE_KEY, "shopping_agent_id", "challenge_response", "risk_data", module.CHECKOUT_MANDATE_KEY])

    def test_empty_otp_is_original_falsey_omission(self):
        self.payment_prefix()
        self.plan.observe("payment_start", self.pending())
        self.plan.observe("otp_response", "")
        message = self.plan.next_action(message_id=NONCE)["message"]
        self.assertFalse(any("challenge_response" in part.get("data", {}) for part in message["parts"]))

    def test_hidden_frontend_challenge_does_not_make_otp_available(self):
        self.payment_prefix()
        value = task("payment", state="input_required")
        value["status"]["challenge"] = {"type": "otp", "display_text": "hidden"}
        with self.assertRaisesRegex(module.PlanningError, "public merchant challenge"):
            self.plan.observe("payment_start", value)

    def test_malformed_part_cannot_hide_extra_challenge(self):
        self.payment_prefix()
        value = self.pending()
        value["status"]["message"]["parts"].append({"data": {"challenge": {"type": "otp"}}})
        with self.assertRaisesRegex(module.PlanningError, "Part shape"):
            self.plan.observe("payment_start", value)

    def test_wrong_final_merchant_task_refused(self):
        self.payment_prefix(); self.plan.observe("payment_start", self.pending()); self.plan.observe("otp_response", "123")
        with self.assertRaisesRegex(module.PlanningError, "original pending task"):
            self.plan.observe("payment_resume", task("other", state="completed"))

    def test_observed_source_failure_retained_without_native_or_task_grade(self):
        self.payment_prefix(); self.plan.observe("payment_start", self.pending()); self.plan.observe("otp_response", "123")
        value = task("payment", state="failed")
        self.plan.observe("payment_resume", value)
        report = self.plan.report()
        self.assertEqual(report["next_phase"], "finished")
        self.assertEqual(report["caller_state"]["supplied_merchant_after"], value)
        self.assertFalse(report["caller_state"]["supplied_continuation_target_observed"])
        self.assertIsNone(report["aggregate_task_grade"])
        self.assertFalse(report["native_execution_enabled"])
        self.assertEqual(report["credential_transaction_association"], "unknown")

    def test_nonfinite_or_nonjson_observation_refused(self):
        value = deepcopy(self.catalog); value["extra"] = float("nan")
        with self.assertRaisesRegex(module.PlanningError, "finite plain JSON"):
            self.plan.observe("catalog", value)
        with self.assertRaisesRegex(module.PlanningError, "plain JSON"):
            module.exact_message("text", [("tuple", (1, 2))], message_id=NONCE)

    def test_source_footprint_exact_bytes_without_import(self):
        src = ROOT / "docs/research/source-evidence/ap2-procurement-screen-v1/source/code/samples/python/src"
        files = {name: (src / name).read_bytes() for name in module.CALLER_FILES}
        result = module.inspect_caller_footprint(files)
        self.assertEqual(len(result["files"]), 4)
        self.assertFalse(result["imports_executed"])
        files[next(iter(files))] += b"\n"
        with self.assertRaisesRegex(module.PlanningError, "digest differs"):
            module.inspect_caller_footprint(files)

    def test_inputs_and_returned_report_do_not_mutate_plan(self):
        original = deepcopy(self.catalog)
        self.plan.observe("catalog", self.catalog)
        self.assertEqual(self.catalog, original)
        self.catalog["contextId"] = "modified"
        report = self.plan.report(); report["caller_state"]["shopping_context_id"] = "modified"
        self.assertEqual(self.plan.state["shopping_context_id"], "returned-context")

    def test_execute_refuses_before_missing_input_or_original_import(self):
        result = subprocess.run([sys.executable, "-I", "-S", "-B", str(ROOT / "scripts/ap2_hp_reference_client_v1.py"),
            "--execute", "--input", str(ROOT / "tests/does-not-exist-ap2-input.json")], capture_output=True, check=False)
        self.assertEqual(result.returncode, 3, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["status"], "refused_before_original_import")
        self.assertEqual([value[key] for key in ("original_imports", "key_accesses", "client_attempts", "model_attempts")], [0, 0, 0, 0])


if __name__ == "__main__":
    unittest.main()
