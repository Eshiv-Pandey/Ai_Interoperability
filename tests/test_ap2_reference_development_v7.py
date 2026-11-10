"""Constructed public-fixture controls, separate from original ADK execution."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from interoperability.ap2_original_shopper_fixture_v7 import PublicDialogueFixture, render_public_address


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


orchestrator = module("_ap2_v7_constructed_orchestrator", "scripts/run_ap2_original_shopper_bank_v7.py")
evaluator = module("_ap2_v7_constructed_evaluator", "scripts/evaluate_ap2_original_shopper_bank_v7.py")
MANIFEST = json.loads((ROOT / "benchmark/ap2-shopper-development-v7/application.json").read_bytes())


def case(name="ap2-dev-001"):
    return deepcopy(next(row for row in MANIFEST["records"] if row["id"] == name))


def response(name, value):
    return {"contents": [{"role": "user", "parts": [{"functionResponse": {"name": name, "response": {"result": value}}}]}]}


ALL_TOOLS = ["transfer_to_agent", "find_products", "select_cart", "get_shipping_address", "get_payment_methods",
             "get_payment_credential_token", "create_checkout", "create_checkout_mandate", "create_payment_mandate",
             "send_signed_mandates_to_credentials_provider", "initiate_payment", "initiate_payment_with_otp"]


def constructed_prefix(fixture):
    observed = []
    def step(request=None):
        value = fixture.step(request or {"contents": []}, ALL_TOOLS)
        observed.append(value)
        return value
    def reply(value):
        return fixture.human_reply(value["text"])
    step()  # original root transfer
    step()  # offered original shopper find
    carts = [{"cart_id": "constructed-visible-cart", "item_label": "Constructed shoes", "currency": "USD", "amount": 12.5}]
    reply(step(response("find_products", carts)))
    step()
    step(response("select_cart", "Cart constructed-visible-cart selected."))
    step()
    reply(step())
    reply(step())
    step()
    if fixture.case["shipping_mode"] == "wallet":
        step(response("get_shipping_address", {"addressLine": "Constructed wallet address", "country": "US"}))
    step()
    step()
    reply(step(response("get_payment_methods", {"payment_method_aliases": ["constructed-visible-card"]})))
    step()
    step(response("get_payment_credential_token", {"status": "success", "token": "constructed-token"}))
    step()
    reply(step(response("create_checkout", carts[0])))
    return observed, step


class DialogueControls(unittest.TestCase):
    def test_address_renderer_retains_actual_list_and_scalar_shape(self):
        address = {"address_line": ["123 Main St", "Suite 2"], "city": "Sample City", "country": "US",
                   "postal_code": "00000", "recipient": "Bugs Bunny", "dependent_locality": None}
        rendered = render_public_address(address)
        for component in ("123 Main St", "Suite 2", "Sample City", "US", "00000", "Bugs Bunny"):
            self.assertIn(component, rendered)
        self.assertNotIn("None", rendered)

    def test_wallet_transfer_displays_original_list_address_return(self):
        fixture = PublicDialogueFixture(case("ap2-ho-003"), MANIFEST)
        fixture.phase = "return_wallet_shipping"
        address = {"address_line": ["123 Main St"], "city": "Sample City", "region": "ST", "postal_code": "00000", "country": "US"}
        transfer = fixture.step(response("get_shipping_address", address), ALL_TOOLS)
        self.assertEqual(transfer["name"], "transfer_to_agent")
        self.assertIn("123 Main St", transfer["text"])
        self.assertIn("Sample City", transfer["text"])

    def test_actual_question_required_before_public_cart_selection(self):
        fixture = PublicDialogueFixture(case(), MANIFEST)
        fixture.step({"contents": []}, ALL_TOOLS)
        fixture.step({"contents": []}, ALL_TOOLS)
        offered = fixture.step(response("find_products", [{"cart_id": "constructed-cart", "item_label": "Test", "currency": "USD", "amount": 1}]), ALL_TOOLS)
        with self.assertRaisesRegex(ValueError, "question_not_observed"):
            fixture.human_reply("a different actual assistant message")
        self.assertIsNone(fixture.selected_cart)
        self.assertIn("constructed-cart", fixture.human_reply(offered["text"]))

    def test_generic_original_tool_status_never_causes_unsolicited_otp(self):
        fixture = PublicDialogueFixture(case(), MANIFEST)
        observed, step = constructed_prefix(fixture)
        self.assertEqual(step()["name"], "create_checkout_mandate")
        self.assertEqual(step(response("create_checkout_mandate", "constructed-checkout-presentation"))["name"], "create_payment_mandate")
        self.assertEqual(step(response("create_payment_mandate", "constructed-payment-presentation"))["name"], "send_signed_mandates_to_credentials_provider")
        self.assertEqual(step(response("send_signed_mandates_to_credentials_provider", "Successfully sent mandates to the credentials provider."))["name"], "initiate_payment")
        result = step(response("initiate_payment", "Status: TaskState.input_required"))
        self.assertEqual(fixture.terminal_reason, "original_generic_payment_status_has_no_otp_request")
        self.assertIsNone(fixture.human_reply(result["text"]))
        self.assertEqual(fixture.otp_index, 0)
        self.assertFalse(any(row.get("name") == "initiate_payment_with_otp" for row in observed))

    def test_withheld_cart_confirmation_stops_before_signing(self):
        fixture = PublicDialogueFixture(case("ap2-ho-005"), MANIFEST)
        observed, step = constructed_prefix(fixture)
        value = step()
        self.assertEqual(value["kind"], "text")
        self.assertEqual(fixture.terminal_reason, "human_cart_confirmation_withheld")
        self.assertFalse(any(row.get("name") in {"create_checkout_mandate", "create_payment_mandate", "initiate_payment"} for row in observed))

    def test_wallet_consent_precedes_original_address_tool(self):
        fixture = PublicDialogueFixture(case("ap2-ho-003"), MANIFEST)
        observed, _ = constructed_prefix(fixture)
        consent = next(i for i, row in enumerate(observed) if "Is that ok?" in (row.get("text") or ""))
        fetch = next(i for i, row in enumerate(observed) if row.get("name") == "get_shipping_address")
        self.assertLess(consent, fetch)
        self.assertIn("bugsbunny@gmail.com", observed[consent]["text"])

    def test_wrong_public_otp_reply_is_not_replaced_by_demo_hint(self):
        fixture = PublicDialogueFixture(case("ap2-dev-003"), MANIFEST)
        fixture.phase = "payment_return"
        question = fixture.step(response("initiate_payment", "Verification required: constructed issuer challenge"), ALL_TOOLS)
        self.assertEqual(fixture.human_reply(question["text"]), "000")
        call = fixture.step({"contents": []}, ALL_TOOLS)
        self.assertEqual(call["args"]["challenge_response"], "000")

    def test_model_budget_and_unoffered_tools_refuse(self):
        fixture = PublicDialogueFixture(case(), MANIFEST)
        with self.assertRaisesRegex(ValueError, "not_offered"):
            fixture.step({"contents": []}, [])
        fixture.rows = [{}] * MANIFEST["actor_model_call_bound"]
        with self.assertRaisesRegex(ValueError, "budget_exhausted"):
            fixture.step({"contents": []}, ALL_TOOLS)


class BankDenominatorControls(unittest.TestCase):
    def test_all_original_bank_ids_and_split_counts_preserved(self):
        cells = orchestrator.manifest_cells(MANIFEST)
        self.assertEqual(len(cells), 34)
        self.assertEqual(sum(len(row["original_processes"]) for row in cells), 29)
        self.assertEqual(sum(row["execution_mode"] == "prior_source_boundary_capture" for row in cells), 6)
        original = json.loads((ROOT / "benchmark/tasks-v1/ap2/application.json").read_bytes())
        self.assertEqual([row["id"] for row in MANIFEST["records"]], [row["id"] for row in original["records"]])

    def test_missing_processes_remain_in_34_candidate_denominator(self):
        cells = orchestrator.manifest_cells(MANIFEST)
        public_raw = (ROOT / "benchmark/ap2-shopper-development-v7/application.json").read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            (base / "public-manifest.json").write_bytes(public_raw)
            plan = {"candidate_denominator": 34, "public_manifest": evaluator.digest(public_raw)}
            (base / "allocation-manifest.json").write_text(json.dumps(plan))
            rows = []
            for row in cells:
                rows.append(dict(row, process_attempts=[dict(process, returncode=None, allocation_status="not_executed_allocation_budget_exhausted")
                    for process in row["original_processes"]]))
            (base / "execution-results.json").write_text(json.dumps({"candidate_denominator": 34, "cells": rows}))
            (base / "prior-source-boundary-actor-output.json").write_bytes((ROOT / MANIFEST["source_boundary_capture"]).read_bytes())
            result = evaluator.evaluate_allocation(base, MANIFEST, False)
            self.assertEqual(result["candidate_denominator"], 34)
            self.assertEqual(result["totals"]["missing_processes"], 29)
            self.assertEqual(result["totals"]["actual_purchase_processes"], 0)

    def test_actor_private_read_probe_and_evaluator_independence_are_explicit(self):
        actor = (ROOT / "scripts/ap2_reference_development_v7.py").read_text(encoding="utf-8")
        self.assertIn("sys.addaudithook(public_only_actor)", actor)
        self.assertIn("except PermissionError:", actor)
        self.assertIn("evaluator_probe_blocked = True", actor)
        source = (ROOT / "scripts/evaluate_ap2_original_shopper_bank_v7.py").read_text(encoding="utf-8")
        self.assertNotIn("from interoperability.ap2_original_shopper", source)


if __name__ == "__main__":
    unittest.main()
