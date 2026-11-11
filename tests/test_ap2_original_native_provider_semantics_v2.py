"""Constructed semantic-capture controls; retained public Tasks are not gold."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("owned_v2_semantic_analyzer", ROOT / "scripts/analyze_ap2_original_native_provider_v2.py")
ANALYZER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ANALYZER)
FIXTURES = ROOT / "tests/fixtures/ap2-public-continuation-v1"


class Capture:
    def __init__(self, retained, variation):
        self.analysis = ANALYZER.Analysis(retained)
        self.facts = next(row for row in ANALYZER.facts() if row["case_id"].endswith("-" + variation))
        fixture = "wrong" if variation == "wrong-reply" else "correct"
        self.pending = json.loads((FIXTURES / ("v13-" + fixture + "-pending-task.json")).read_bytes())
        self.final = (deepcopy(self.pending) if variation == "no-reply" else
                      json.loads((FIXTURES / ("v13-" + fixture + "-final-task.json")).read_bytes()))
        self.raw, self.calls, self.events, self.reads = [], [], [], []
        self.folder = self.analysis.capture / "execution/cases" / self.facts["case_id"]
        self.folder.mkdir(parents=True)
        self.write(self.folder / (self.facts["case_id"] + ".public-human-facts.json"), self.facts)

    def write(self, path, value, *, lines=False):
        raw = ("\n".join(json.dumps(row, sort_keys=True) for row in value) + "\n").encode() if lines else json.dumps(value).encode()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        self.analysis.members[path.relative_to(self.analysis.capture).as_posix()] = ANALYZER.digest(raw)

    def call(self, phase, returned="constructed original return", *, error=False):
        call = {"index": len(self.calls), "phase": phase, "callable": "constructed.fixture." + phase.replace("-", "_")}
        self.raw.append({"kind": "original-call-start", **deepcopy(call)})
        call.update({"error_type": "A2AClientJSONRPCError", "error": "constructed context refusal"} if error else {"public_return": returned})
        self.calls.append(call)
        self.raw.append({"kind": "original-call-error" if error else "original-call-return", **deepcopy(call)})

    def event(self, kind, **values):
        row = {"index": len(self.events), "kind": kind, **values}
        self.events.append(row)
        self.raw.append(deepcopy(row))

    def read(self, phase, task, *, foreign=None):
        held = {"id": task["id"], "caller_context": foreign or task["contextId"]}
        self.raw.append({"kind": "public-task-read-start", "phase": phase, "query": held})
        observation = {"query": {"id": task["id"], "historyLength": 100}, "task": deepcopy(task)}
        row = ({"phase": phase, "query": held, "error_type": "PublicTaskAuthorityError", "error": "constructed refused authority",
                "refused_public_observation": observation} if foreign else {"phase": phase, "public_observation": observation})
        self.reads.append(row)
        self.raw.append({"kind": "public-task-read-error" if foreign else "public-task-read-return", **deepcopy(row)})

    def prepare(self, *, repeat_changed=False):
        cart = {"cart_id": "constructed-offer", "item_label": "Constructed walking shoes", "amount": 12.5, "currency": "USD"}
        methods, address = {"payment_method_aliases": ["constructed card alias"]}, {"address_line": ["constructed address"]}
        checkout = {**cart, "checkout_jwt": "constructed-checkout-jwt", "amount_cents": 1250}
        checkout["checkout_hash"] = ANALYZER.base64.urlsafe_b64encode(hashlib.sha256(checkout["checkout_jwt"].encode()).digest()).rstrip(b"=").decode()
        mandate = next(part["data"]["ap2.mandates.PaymentMandateSdJwt"] for message in self.pending["history"]
                       for part in message.get("parts") or [] if "ap2.mandates.PaymentMandateSdJwt" in part.get("data", {}))
        returns = {"catalog": [cart], "shipping": address, "payment-methods": methods, "checkout": checkout, "payment-mandate": mandate}
        for phase in ("catalog", "cart-selection", "shipping", "payment-methods", "credential-token", "checkout",
                      "checkout-mandate", "payment-mandate", "credential-association", "payment-start"):
            self.call(phase, returns.get(phase, "constructed original return"))
        self.event("human-cart-selection", offered=[cart], selected=cart)
        self.event("human-wallet-consent", consent=True, user_email=self.facts["user_email"])
        self.event("public-shipping-display", address=address)
        self.event("human-payment-selection", offered=methods, selected=methods["payment_method_aliases"][0])
        self.event("human-cart-confirmation", approved=True, cart=cart, shipping=address, payment_method=methods["payment_method_aliases"][0])
        self.read("initial-payment-task", self.pending)
        self.event("public-otp-request", challenge=ANALYZER.challenge(self.pending), merchant_task_id=self.pending["id"], context_id=self.pending["contextId"])
        self.event("explicit-human-otp", response=self.facts["otp_response"])
        if self.facts["fault"] == "other_original_context":
            self.call("other-original-catalog", [cart])
            self.event("received-public-authority-fault", fault="other_original_context", received="constructed-other-context")
            self.call("adverse-original-payment-otp", error=True)
            self.event("adverse-original-rpc-error", public_rpc_error={"code": -32602, "message": "constructed context refusal"})
            self.read("adverse-authority-read", self.pending, foreign="constructed-other-context")
            self.event("adverse-read-disposition", disposition="owned_caller_context_check_refused_actual_public_task",
                       error_type="PublicTaskAuthorityError", error="constructed refused authority")
            self.event("recover-from-prior-public-task", task_id=self.pending["id"], context_id=self.pending["contextId"])
        if self.facts["otp_response"] is None:
            self.read("waiting-payment-task", self.final)
        else:
            self.call("payment-otp", "constructed original status")
            self.read("after-original-otp", self.final)
            self.event("public-payment-observation", state=self.final["status"]["state"], receipts=ANALYZER.receipts(self.final))
        if self.facts["repeat_after_completed"]:
            repeated = deepcopy(self.final)
            if repeat_changed:
                receipt = ANALYZER.receipts(repeated)[0]
                for key in ("payment_id", "psp_confirmation_id", "network_confirmation_id"):
                    receipt[key] = "constructed-different-confirmation"
            self.call("repeat-original-otp", "constructed repeated original status")
            self.read("after-repeated-original-otp", repeated)
            self.event("public-repeat-observation", task=repeated, receipts=ANALYZER.receipts(repeated))
        self.actor = {"schema_version": "ap2-owned-public-scripted-continuation/2", "case_id": self.facts["case_id"],
                      "public_human_facts": self.facts, "grade": None, "evaluator_or_private_journal_inputs": [],
                      "status": "constructed fixture outcome", "error": None, "original_business_calls": self.calls,
                      "actor_public_events": self.events, "public_task_reads": self.reads,
                      "public_pending_task": self.pending, "public_final_task": self.final}

    def finish(self, *, failed=False):
        self.write(self.folder / "caller/result.json", self.actor)
        self.write(self.folder / "caller/actor-public-events.jsonl", self.raw, lines=True)
        return self.analysis.case(self.facts, {"status": "executed_nonzero_retained" if failed else "executed_returned"})


class SemanticControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def capture(self, variation):
        return Capture(Path(self.temp.name), variation)

    def test_all_five_constructed_cases_preserve_public_observations(self):
        for variation in ("correct-reply", "wrong-reply", "no-reply", "foreign-context-recovery", "repeat-completed"):
            with self.subTest(variation=variation):
                retained = Path(self.temp.name) / variation
                capture = Capture(retained, variation)
                capture.prepare()
                row = capture.finish()
                self.assertEqual([], row["consistency_questions"])
                self.assertTrue(row["semantic_response_captured"])
                self.assertIsNone(row["whole_task_grade"])
                if variation == "wrong-reply":
                    self.assertTrue(row["wrong_reply_public_refusal_observed"])
                    # This older public fixture used a different wrong string.
                    # An exact actor event alone must not create Task evidence.
                    self.assertFalse(row["exact_reply_present_in_retained_task_messages"])
                if variation == "no-reply":
                    self.assertTrue(row["waiting_without_human_reply_observed"])
                if variation == "repeat-completed":
                    self.assertTrue(row["repeat_receipts_equal_prior_receipts"])

    def test_otp_call_without_human_reply_is_retained_question(self):
        capture = self.capture("no-reply")
        capture.prepare()
        capture.call("payment-otp", "constructed impermissible extra call")
        row = capture.finish()
        self.assertTrue(any("otp_dispatched_without_human_reply" in issue for issue in row["consistency_questions"]))

    def test_changed_recovery_authority_is_refused(self):
        capture = self.capture("foreign-context-recovery")
        capture.prepare()
        for rows in (capture.events, capture.raw):
            for row in rows:
                if row.get("kind") == "recover-from-prior-public-task":
                    row["context_id"] = "constructed-unreturned-authority"
        row = capture.finish()
        self.assertTrue(any("recovery_not_prior_returned_public_authority" in issue for issue in row["consistency_questions"]))

    def test_different_repeated_receipt_is_observation_not_hidden_effect_grade(self):
        capture = self.capture("repeat-completed")
        capture.prepare(repeat_changed=True)
        row = capture.finish()
        self.assertEqual([], row["consistency_questions"])
        self.assertFalse(row["repeat_receipts_equal_prior_receipts"])
        self.assertIsNone(row["whole_task_grade"])

    def test_later_failure_preserves_prior_completed_receipt(self):
        capture = self.capture("repeat-completed")
        capture.prepare()
        capture.actor["error"] = {"type": "TimeoutError", "message": "constructed later failure"}
        row = capture.finish(failed=True)
        self.assertTrue(row["prior_completed_receipt_observed"])
        self.assertEqual("failed_or_partial_attempt_with_public_observations", row["disposition"])

    def test_actor_final_is_checked_against_exact_raw_read(self):
        capture = self.capture("correct-reply")
        capture.prepare()
        capture.actor["public_final_task"] = deepcopy(capture.final)
        capture.actor["public_final_task"]["contextId"] = "constructed-mismatching-result"
        row = capture.finish()
        self.assertTrue(any("actor_final_not_exact_final_public_read" in issue for issue in row["consistency_questions"]))

    def test_no_actor_or_public_response_is_zero_semantic_capture(self):
        capture = self.capture("correct-reply")
        row = capture.analysis.case(capture.facts, {"status": "executed_nonzero_retained"})
        self.assertFalse(row["semantic_response_captured"])
        self.assertEqual("no_semantic_response_captured", row["disposition"])
        self.assertIsNone(row["whole_task_grade"])


if __name__ == "__main__":
    unittest.main()
