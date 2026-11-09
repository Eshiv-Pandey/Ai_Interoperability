"""Constructed public-flow observations, never original/native AP2 outcomes."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("ap2_hp_public_assessment_v1",
    Path(__file__).resolve().parents[1] / "src/interoperability/ap2_hp_public_assessment_v1.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def message(data, task_id=None):
    value = {"kind": "message", "messageId": "constructed-message", "role": "agent", "contextId": "context-1",
             "parts": [{"kind": "data", "data": {key: val}} for key, val in data.items()]}
    if task_id is not None:
        value["taskId"] = task_id
    return value


def task(task_id, state, receipt=None):
    result = {"kind": "task", "id": task_id, "contextId": "context-1", "status": {"state": state}, "artifacts": []}
    if state == "input_required":
        result["status"]["message"] = message({"challenge": {"type": "otp", "display_text": "Demo code 123"}}, task_id)
    if receipt is not None:
        result["artifacts"] = [{"artifactId": "receipt-1", "parts": [{"kind": "data", "data": {module.RECEIPT_KEY: receipt}}]}]
    return result


class PublicPaymentAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.mandate = "open.jwt.signature~~leaf.jwt.signature~disclosure~"
        self.initial = message({module.MANDATE_KEY: self.mandate})
        self.pending = task("merchant-1", "input_required")
        self.resume = message({module.MANDATE_KEY: self.mandate, "challenge_response": "123"}, "merchant-1")
        self.receipt = {"status": "Success", "iss": "", "iat": 12345,
            "reference": module.receipt_reference(self.mandate), "payment_id": "0123456789ab4def8123456789abcdef",
            "psp_confirmation_id": "0123456789ab4def8123456789abcdef", "network_confirmation_id": "0123456789ab4def8123456789abcdef"}
        self.after = task("merchant-1", "completed", self.receipt)

    def assess(self, **extras):
        return module.assess_public_payment(self.initial, self.pending, self.resume, self.after, **extras)

    def lane(self, name):
        return self.assess()["lanes"][name]["status"]

    def test_success_projection_and_empty_issuer_without_task_grade(self):
        result = self.assess()
        for name in ("merchant_task_continuity", "merchant_public_challenge", "initial_mandate_preserved",
                     "merchant_after_state", "receipt_projection", "receipt_reference", "source_confirmation_ids"):
            self.assertEqual(result["lanes"][name]["status"], "consistent", name)
        self.assertIsNone(result["aggregate_task_grade"])
        self.assertFalse(result["native_qualification_established"])
        self.assertEqual(result["credential_transaction_association"], "unknown")

    def test_closed_leaf_not_whole_presentation(self):
        self.assertEqual(module.receipt_reference(self.mandate), module.receipt_reference("leaf.jwt.signature"))
        self.assertEqual(module.receipt_reference("open~~mid~d~~leaf.jwt.signature~"), module.receipt_reference(self.mandate))
        self.assertIsNone(module.receipt_reference("open~~"))

    def test_wrong_merchant_task(self):
        self.resume["taskId"] = "another-task"
        self.assertEqual(self.lane("merchant_task_continuity"), "discrepant")

    def test_wrong_context(self):
        self.after["contextId"] = "another-context"
        self.assertEqual(self.lane("merchant_task_continuity"), "discrepant")

    def test_missing_identity_unknown(self):
        del self.pending["contextId"]
        self.assertEqual(self.lane("merchant_task_continuity"), "unknown")

    def test_missing_continuation_identity_unknown(self):
        del self.resume["taskId"]
        self.assertEqual(self.lane("merchant_task_continuity"), "unknown")

    def test_old_frontend_challenge_field_is_not_public_data(self):
        self.pending["status"] = {"state": "challenge", "challenge": {"display_text": "123"}}
        self.assertEqual(self.lane("merchant_public_challenge"), "unknown")

    def test_invalid_otp_does_not_expect_completion(self):
        self.resume["parts"][1]["data"]["challenge_response"] = "wrong"
        self.after = task("merchant-1", "input_required")
        self.assertEqual(self.lane("merchant_after_state"), "consistent")
        self.assertEqual(self.lane("receipt_reference"), "unknown")

    def test_invalid_otp_with_completion_is_discrepant(self):
        self.resume["parts"][1]["data"]["challenge_response"] = "wrong"
        self.assertEqual(self.lane("merchant_after_state"), "discrepant")

    def test_incorrect_otp_pending_with_success_receipt_is_discrepant(self):
        self.resume["parts"][1]["data"]["challenge_response"] = "wrong"
        self.after["status"]["state"] = "input_required"
        self.assertEqual(self.lane("merchant_after_state"), "consistent")
        self.assertEqual(self.lane("merchant_incorrect_otp_success_receipt_absence"), "discrepant")

    def test_pending_receipt_is_discrepant(self):
        self.pending["artifacts"] = deepcopy(self.after["artifacts"])
        self.assertEqual(self.lane("merchant_pending_success_receipt_absence"), "discrepant")

    def test_changed_mandate_reference_is_current_mandate(self):
        self.resume["parts"][0]["data"][module.MANDATE_KEY] = "other.jwt.signature~"
        self.receipt["reference"] = module.receipt_reference("other.jwt.signature~")
        result = self.assess()
        self.assertEqual(result["lanes"]["initial_mandate_preserved"]["status"], "discrepant")
        self.assertEqual(result["lanes"]["receipt_reference"]["status"], "consistent")
        self.assertIsNone(result["aggregate_task_grade"])

    def test_wrong_receipt_reference(self):
        self.receipt["reference"] = "another-reference"
        self.assertEqual(self.lane("receipt_reference"), "discrepant")

    def test_duplicate_receipts_cannot_be_selected(self):
        self.after["artifacts"].append(deepcopy(self.after["artifacts"][0]))
        self.assertEqual(self.lane("receipt_reference"), "unknown")

    def test_duplicate_mandates_cannot_be_selected(self):
        self.resume["parts"].append(deepcopy(self.resume["parts"][0]))
        self.assertEqual(self.lane("receipt_reference"), "unknown")

    def test_bool_timestamp_is_not_original_integer(self):
        self.receipt["iat"] = True
        self.assertEqual(self.lane("receipt_projection"), "discrepant")

    def test_source_confirmation_ids_have_same_value(self):
        self.receipt["network_confirmation_id"] = "other-id"
        self.assertEqual(self.lane("source_confirmation_ids"), "discrepant")

    def test_equal_non_uuid_ids_are_separate_constructor_discrepancy(self):
        for key in ("payment_id", "psp_confirmation_id", "network_confirmation_id"):
            self.receipt[key] = "non-uuid"
        self.assertEqual(self.lane("receipt_projection"), "consistent")
        self.assertEqual(self.lane("source_confirmation_ids"), "discrepant")

    def test_hex_ids_without_uuid4_bits_do_not_match_constructor(self):
        for key in ("payment_id", "psp_confirmation_id", "network_confirmation_id"):
            self.receipt[key] = "0123456789abcdef0123456789abcdef"
        self.assertEqual(self.lane("source_confirmation_ids"), "discrepant")

    def test_optional_processor_receipt_propagation(self):
        pending = task("processor-1", "input_required")
        self.pending["status"]["message"] = deepcopy(pending["status"]["message"])
        resume = deepcopy(self.resume); resume["taskId"] = "processor-1"
        after = task("processor-1", "completed", deepcopy(self.receipt))
        result = self.assess(processor_pending=pending, processor_resume_message=resume, processor_after=after)
        for name in ("processor_task_continuity", "processor_receipt_reference", "receipt_propagation",
                     "distinct_child_task_shared_context", "child_challenge_propagation", "otp_forwarding", "mandate_forwarding"):
            self.assertEqual(result["lanes"][name]["status"], "consistent", name)
        after["artifacts"][0]["parts"][0]["data"][module.RECEIPT_KEY]["payment_id"] = "other"
        self.assertEqual(self.assess(processor_pending=pending, processor_resume_message=resume,
                                    processor_after=after)["lanes"]["receipt_propagation"]["status"], "discrepant")

    def test_changed_forwarded_otp_or_mandate_is_discrepant(self):
        resume = deepcopy(self.resume); resume["taskId"] = "processor-1"
        resume["parts"][1]["data"]["challenge_response"] = "other"
        resume["parts"][0]["data"][module.MANDATE_KEY] = "other"
        result = self.assess(processor_resume_message=resume)
        self.assertEqual(result["lanes"]["otp_forwarding"]["status"], "discrepant")
        self.assertEqual(result["lanes"]["mandate_forwarding"]["status"], "discrepant")

    def test_rewritten_child_message_identity_is_discrepant(self):
        pending = task("processor-1", "input_required")
        self.assertEqual(self.assess(processor_pending=pending)["lanes"]["child_challenge_propagation"]["status"], "discrepant")

    def test_typed_receipt_propagation_does_not_merge_bool_with_integer(self):
        after = task("processor-1", "completed", deepcopy(self.receipt))
        self.receipt["iat"] = 1
        after["artifacts"][0]["parts"][0]["data"][module.RECEIPT_KEY]["iat"] = True
        self.assertEqual(self.assess(processor_after=after)["lanes"]["receipt_propagation"]["status"], "discrepant")

    def test_optional_fields_and_extra_json_are_preserved(self):
        self.receipt.update(error=None, error_description=None, extra={"typed": [1, True, 1.0]})
        after = task("processor-1", "completed", deepcopy(self.receipt))
        self.assertEqual(self.assess(processor_after=after)["lanes"]["receipt_propagation"]["status"], "consistent")
        after["artifacts"][0]["parts"][0]["data"][module.RECEIPT_KEY]["extra"]["typed"][0] = 1.0
        self.assertEqual(self.assess(processor_after=after)["lanes"]["receipt_propagation"]["status"], "discrepant")

    def test_success_optional_error_strings_are_schema_admissible_only(self):
        self.receipt.update(error="allowed-by-generated-type", error_description="allowed-string")
        self.assertEqual(self.lane("strict_json_receipt_schema_projection"), "consistent")
        self.assertEqual(self.lane("receipt_projection"), "discrepant")
        self.assertEqual(self.lane("source_confirmation_ids"), "discrepant")

    def test_error_receipt_schema_and_propagation_are_not_payment_success(self):
        self.receipt.update(status="Error", error="declined", error_description="Constructed error")
        del self.receipt["psp_confirmation_id"]
        self.receipt["network_confirmation_id"] = None
        after = task("processor-1", "failed", deepcopy(self.receipt))
        result = self.assess(processor_after=after)
        self.assertEqual(result["lanes"]["strict_json_receipt_schema_projection"]["status"], "consistent")
        self.assertEqual(result["lanes"]["receipt_propagation"]["status"], "consistent")
        self.assertEqual(result["lanes"]["receipt_projection"]["status"], "discrepant")
        self.assertIsNone(result["aggregate_task_grade"])

    def test_error_receipt_missing_required_error_is_discrepant(self):
        self.receipt["status"] = "Error"
        self.assertEqual(self.lane("strict_json_receipt_schema_projection"), "discrepant")

    def test_correct_otp_failed_downstream_is_unmet_target(self):
        self.after = task("merchant-1", "failed")
        self.assertEqual(self.lane("merchant_after_state"), "discrepant")
        self.assertIsNone(self.assess()["aggregate_task_grade"])

    def test_non_json_values_rejected_before_assessment(self):
        for value in (float("nan"), float("inf"), {1: "non-string-key"}, object()):
            self.receipt["extra"] = value
            with self.assertRaisesRegex(ValueError, "finite JSON"):
                self.assess()

    def test_matching_malformed_receipts_cannot_pass_propagation(self):
        self.after["artifacts"][0]["parts"][0]["data"][module.RECEIPT_KEY] = "invalid"
        after = deepcopy(self.after); after["id"] = "processor-1"
        self.assertEqual(self.assess(processor_after=after)["lanes"]["receipt_propagation"]["status"], "discrepant")

    def test_malformed_part_cannot_prove_receipt_absence(self):
        self.pending["artifacts"] = [{"parts": [{"data": {module.RECEIPT_KEY: self.receipt}}]}]
        self.assertEqual(self.lane("merchant_pending_success_receipt_absence"), "unknown")

    def test_malformed_part_cannot_hide_duplicate_mandate(self):
        self.resume["parts"].append({"data": {module.MANDATE_KEY: "different"}})
        self.assertEqual(self.lane("receipt_reference"), "unknown")

    def test_inputs_remain_unchanged(self):
        before = deepcopy((self.initial, self.pending, self.resume, self.after))
        self.assess()
        self.assertEqual(before, (self.initial, self.pending, self.resume, self.after))


if __name__ == "__main__":
    unittest.main()
