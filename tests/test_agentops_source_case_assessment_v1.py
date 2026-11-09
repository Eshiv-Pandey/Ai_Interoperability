"""All source projections over explicitly SYNTHETIC temporary observations.

These fabricated journal-shaped reports test pure binding/metric logic; they
are never evidence that a source agent ran. One extra integration fixture uses
only the stdlib journal and reader with a synthetic dictionary event producer.
No SDK, original application, model, tool or native process is executed.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from interoperability.agentops_source_case_assessment_v1 import assess_source_case
from interoperability.agentops_runtime_stream_evidence_v1 import read_closed_journal
from agentops_runtime_stream_v1 import RunAsyncJournal

USER = "SYNTHETIC_NATIVE_USER"
SESSION = "SYNTHETIC_NATIVE_SESSION"


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def identity(value):
    raw = value if type(value) is bytes else encoded(value)
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def synthetic_report(application, expectation):
    """Deliberately fabricate call observations from requirements for testing."""
    calls, all_records = [], []
    global_sequence = 0
    for index, (turn, expected) in enumerate(zip(application["conversation"], expectation["conversation"]), 1):
        actual_id = f"SYNTHETIC_GENERATED_INVOCATION_{index}"
        events = [{"id": f"SYNTHETIC_EVENT_{index}_1", "invocation_id": actual_id, "author": "SYNTHETIC_AGENT",
                   "partial": True, "content": {"role": "model", "parts": [
                       {"function_call": deepcopy(call)} for call in expected["intermediate_data"]["tool_uses"]]}},
                  {"id": f"SYNTHETIC_EVENT_{index}_2", "invocation_id": actual_id, "author": "SYNTHETIC_AGENT",
                   "content": {"role": "model", "parts": [{"text": "SYNTHETIC non-reference answer; no semantic claim."}]}}]
        records = []
        for ordinal, event in enumerate(events, 1):
            global_sequence += 1
            record = {"event_ordinal": ordinal, "batch_ordinal": ordinal, "global_yield_sequence": global_sequence,
                      "actual_event_id": event["id"], "actual_invocation_id": actual_id,
                      "captured_before_downstream_yield": True, "path": f"invocations/{index:06d}/events/{ordinal:06d}.json",
                      "part_count_in_original_yield": len(event["content"]["parts"]), **identity(event)}
            records.append(record)
            all_records.append({**record, "invocation_sequence": index, "event": event})
        receipt = {"schema_version": "agentops-runtime-stream/1", "status": "recorded", "invocation_sequence": index,
                   "capture_disabled": False, "capture_errors": [], "original_termination": "normal_exhaustion",
                   "original_error_type": None, "cleanup_error_type": None, "original_call_attempts": 1,
                   "events_seen": 2, "events_recorded": 2, "downstream_yields_entered": 2,
                   "events": records, "observed_invocation_ids": [actual_id]}
        for key in ("capture_complete", "durable_receipt_written", "inputs_complete", "directory_created_exclusively",
                    "original_aclose_attempted", "original_aclose_completed", "event_identity_fields_complete"):
            receipt[key] = True
        inputs = {"user_id": USER, "session_id": SESSION, "new_message": deepcopy(turn["user_content"]), "invocation_id": None}
        calls.append({"invocation_sequence": index, "inputs": inputs, "events": events,
                      "event_records": records, "receipt": receipt, "receipt_identity": identity(receipt)})
    return {"schema_version": "agentops-runtime-stream-evidence/1", "status": "validated",
            "SYNTHETIC_TEST_OBSERVATIONS_ONLY": True, "receipt_identity": identity(b"SYNTHETIC ROOT RECEIPT"),
            "observer_identity": identity(b"SYNTHETIC OBSERVER SOURCE"), "calls": calls,
            "ordered_events": [row["event"] for row in all_records], "ordered_event_records": all_records,
            "recorded_publication_order_validated": True, "source_authentication_proven": False,
            "native_qualification_established": False, "benchmark_grade_proven": False}


def rebuild_events(report):
    """Synchronize synthetic in-memory records; never reseal real evidence."""
    all_records = []
    global_sequence = 0
    for index, call in enumerate(report["calls"], 1):
        records, identities = [], []
        for ordinal, event in enumerate(call["events"], 1):
            global_sequence += 1
            record = {"event_ordinal": ordinal, "batch_ordinal": ordinal, "global_yield_sequence": global_sequence,
                      "actual_event_id": event["id"], "actual_invocation_id": event["invocation_id"],
                      "captured_before_downstream_yield": True, "path": f"invocations/{index:06d}/events/{ordinal:06d}.json",
                      "part_count_in_original_yield": len(event.get("content", {}).get("parts", [])), **identity(event)}
            records.append(record)
            all_records.append({**record, "invocation_sequence": index, "event": event})
            if event["invocation_id"] not in identities:
                identities.append(event["invocation_id"])
        call["event_records"] = records
        call["receipt"].update(events=records, observed_invocation_ids=identities,
                               events_seen=len(records), events_recorded=len(records), downstream_yields_entered=len(records))
    report["ordered_event_records"] = all_records
    report["ordered_events"] = [row["event"] for row in all_records]


class SourceCaseAssessmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.applications = json.loads((ROOT / "runs/upstream-agentops-cases/v1/application/cases.json").read_bytes())["cases"]
        cls.expectations = json.loads((ROOT / "runs/upstream-agentops-cases/v1/evaluator/expectations.json").read_bytes())["cases"]

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="SYNTHETIC-source-case-assessment-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.application = deepcopy(self.applications[0])
        self.expectation = deepcopy(self.expectations[0])
        self.report = synthetic_report(self.application, self.expectation)

    def assess(self, report=None, application=None, expectation=None, user=USER, session=SESSION):
        # Temporary JSON makes the pure API consume plain serialized test data.
        path = self.directory / "SYNTHETIC-OBSERVATIONS-NOT-NATIVE-EVIDENCE.json"
        path.write_bytes(encoded(self.report if report is None else report))
        return assess_source_case(json.loads(path.read_bytes()), self.application if application is None else application,
                                  self.expectation if expectation is None else expectation,
                                  expected_native_user_id=user, expected_native_session_id=session)

    def reject(self, **kwargs):
        with self.assertRaises(ValueError):
            self.assess(**kwargs)

    def test_all_21_cases_22_turns_score_only_configured_original_metric(self):
        self.assertEqual(len(self.applications), 21)
        self.assertEqual(sum(len(case["conversation"]) for case in self.applications), 22)
        for application, expectation in zip(self.applications, self.expectations):
            with self.subTest(case=application["eval_id"]):
                result = self.assess(synthetic_report(application, expectation), application, expectation)
                self.assertEqual(result["configured_metric"]["overall_score"], 1.0)
                self.assertEqual(result["configured_metric"]["metric_name"], "tool_trajectory_avg_score")
                self.assertEqual(result["configured_metric"]["threshold"], 1.0)
                self.assertEqual(result["turn_count"], len(application["conversation"]))
                self.assertFalse(result["full_task_grade_assigned"])
                self.assertFalse(result["native_source_case_qualification"])
                self.assertFalse(result["benchmark_grade_proven"])
                self.assertEqual(result["separate_assessments"]["state"]["status"], "unavailable")
                for lane in ("response", "dependency", "schema", "answer"):
                    self.assertEqual(result["separate_assessments"][lane]["status"], "pending")

    def test_all_21_cases_missing_required_call_fail_without_other_grade(self):
        for application, expectation in zip(self.applications, self.expectations):
            with self.subTest(case=application["eval_id"]):
                report = synthetic_report(application, expectation)
                report["calls"][0]["events"][0]["content"]["parts"] = report["calls"][0]["events"][0]["content"]["parts"][1:]
                rebuild_events(report)
                result = self.assess(report, application, expectation)
                self.assertEqual(result["configured_metric"]["overall_eval_status"], "failed")
                self.assertFalse(result["state_effects_proven"])

    def test_copied_reference_answer_cannot_replace_missing_calls(self):
        self.report["calls"][0]["events"][0]["content"]["parts"] = []
        self.report["calls"][0]["events"][1]["content"] = deepcopy(self.expectation["conversation"][0]["final_response"])
        rebuild_events(self.report)
        result = self.assess()
        self.assertEqual(result["configured_metric"]["overall_score"], 0.0)
        self.assertFalse(result["reference_answer_used_as_passing_oracle"])

    def test_wrong_answer_does_not_change_calls_only_metric(self):
        self.report["calls"][0]["events"][1]["content"]["parts"][0]["text"] = "SYNTHETIC deliberately incorrect answer"
        rebuild_events(self.report)
        result = self.assess()
        self.assertEqual(result["configured_metric"]["overall_score"], 1.0)
        self.assertEqual(result["separate_assessments"]["answer"]["status"], "pending")

    def test_extra_calls_same_batch_and_partial_duplicates_preserve_source_semantics(self):
        parts = self.report["calls"][0]["events"][0]["content"]["parts"]
        parts.insert(0, {"function_call": {"name": "SYNTHETIC_additional_tool", "args": {}}})
        parts.append(deepcopy(parts[1]))
        rebuild_events(self.report)
        result = self.assess()
        self.assertEqual(result["configured_metric"]["overall_score"], 1.0)
        self.assertFalse(result["causal_tool_execution_order_proven"])

    def test_case_identity_turn_labels_counts_and_timestamps_must_match(self):
        for change in ("case", "family", "timestamp", "label", "turn_timestamp", "count"):
            with self.subTest(change=change):
                expected = deepcopy(self.expectation)
                if change == "case": expected["eval_id"] = "SYNTHETIC_WRONG_CASE"
                elif change == "family": expected["eval_set_id"] = "agentops_incident_workflow"
                elif change == "timestamp": expected["creation_timestamp"] = 99
                elif change == "label": expected["conversation"][0]["invocation_id"] = "SYNTHETIC_WRONG_LABEL"
                elif change == "turn_timestamp": expected["conversation"][0]["creation_timestamp"] = 99
                else: expected["conversation"] = []
                self.reject(expectation=expected)

    def test_application_projection_cannot_contain_evaluator_reference_fields(self):
        application = deepcopy(self.application)
        application["conversation"][0]["final_response"] = deepcopy(self.expectation["conversation"][0]["final_response"])
        self.reject(application=application)

    def test_source_user_label_is_not_the_expected_native_user(self):
        self.assertNotEqual(self.application["session_input"]["user_id"], USER)
        self.assertEqual(self.assess()["configured_metric"]["overall_score"], 1.0)
        self.reject(user=self.application["session_input"]["user_id"])

    def test_native_generated_invocation_id_is_not_source_evaluator_label(self):
        result = self.assess()
        self.assertNotEqual(result["native_invocation_ids"][0], self.application["conversation"][0]["invocation_id"])

    def test_wrong_native_user_session_missing_message_or_prompt_is_rejected(self):
        for change in ("user_id", "session_id", "new_message", "prompt"):
            with self.subTest(change=change):
                report = deepcopy(self.report)
                if change == "prompt": report["calls"][0]["inputs"]["new_message"]["parts"][0]["text"] += " "
                elif change == "new_message": del report["calls"][0]["inputs"][change]
                else: report["calls"][0]["inputs"][change] = "SYNTHETIC_WRONG_CONTEXT"
                self.reject(report=report)
        self.reject(user="")
        self.reject(session=None)

    def test_only_harmless_original_converter_text_part_defaults_are_allowed(self):
        for extras in ({"thought": None}, {"thought": False}, {"part_metadata": None}, {"part_metadata": {}},
                       {"thought": False, "part_metadata": {}}):
            report = deepcopy(self.report)
            report["calls"][0]["inputs"]["new_message"]["parts"][0].update(extras)
            self.assertEqual(self.assess(report)["configured_metric"]["overall_score"], 1.0)
        for extras in ({"thought": True}, {"thought": 0}, {"part_metadata": {"SYNTHETIC": True}},
                       {"part_metadata": []}, {"thought_signature": "SYNTHETIC"}, {"inline_data": None},
                       {"function_call": {"name": "SYNTHETIC", "args": {}}}, {"unknown": None}):
            report = deepcopy(self.report)
            report["calls"][0]["inputs"]["new_message"]["parts"][0].update(extras)
            self.reject(report=report)

    def test_role_extra_parts_and_content_fields_cannot_change_original_prompt(self):
        for change in ("role", "parts", "field"):
            report = deepcopy(self.report)
            content = report["calls"][0]["inputs"]["new_message"]
            if change == "role": content["role"] = "model"
            elif change == "parts": content["parts"].append({"text": "SYNTHETIC_EXTRA"})
            else: content["unknown"] = None
            self.reject(report=report)

    def test_incomplete_or_forged_validation_header_does_not_score(self):
        for key, value in (("status", "partial"), ("schema_version", "wrong/1"),
                           ("recorded_publication_order_validated", False), ("receipt_identity", {}), ("observer_identity", None)):
            report = deepcopy(self.report); report[key] = value
            self.reject(report=report)

    def test_partial_call_flags_or_untyped_counts_are_rejected(self):
        for key, value in (("capture_complete", False), ("original_aclose_completed", False),
                           ("capture_disabled", True), ("original_termination", "consumer_aclose"),
                           ("events_seen", True), ("original_call_attempts", 2)):
            report = deepcopy(self.report); report["calls"][0]["receipt"][key] = value
            self.reject(report=report)

    def test_calls_events_receipts_and_global_order_must_agree(self):
        for change in ("call_order", "record_order", "ordered_event", "missing_global", "record_identity"):
            report = deepcopy(self.report)
            if change == "call_order": report["calls"][0]["invocation_sequence"] = True
            elif change == "record_order": report["calls"][0]["event_records"].reverse()
            elif change == "ordered_event": report["ordered_events"][0]["id"] = "SYNTHETIC_OTHER_EVENT"
            elif change == "missing_global": report["ordered_event_records"] = report["ordered_event_records"][1:]
            else: report["calls"][0]["event_records"][0]["actual_event_id"] = "SYNTHETIC_WRONG_EVENT_ID"
            self.reject(report=report)

    def test_multiple_invocation_groups_in_one_turn_or_wrong_supplied_id_are_rejected(self):
        report = deepcopy(self.report)
        report["calls"][0]["events"][1]["invocation_id"] = "SYNTHETIC_WRONG_GROUP"
        rebuild_events(report)
        self.reject(report=report)
        report = deepcopy(self.report)
        report["calls"][0]["inputs"]["invocation_id"] = "SYNTHETIC_WRONG_SUPPLIED_ID"
        self.reject(report=report)

    def test_two_turn_case_cannot_reuse_or_swap_native_invocation_groups(self):
        application = next(deepcopy(case) for case in self.applications if len(case["conversation"]) == 2)
        expectation = next(deepcopy(case) for case in self.expectations if case["eval_id"] == application["eval_id"])
        report = synthetic_report(application, expectation)
        for event in report["calls"][1]["events"]:
            event["invocation_id"] = report["calls"][0]["events"][0]["invocation_id"]
        rebuild_events(report)
        self.reject(report=report, application=application, expectation=expectation)
        report = synthetic_report(application, expectation)
        # Reverse publication order while retaining valid per-call order.
        for index, call in enumerate(report["calls"]):
            for record in call["event_records"]:
                record["global_yield_sequence"] += 2 if index == 0 else -2
        report["ordered_event_records"] = sorted(
            [{**record, "invocation_sequence": index, "event": event} for index, call in enumerate(report["calls"], 1)
             for record, event in zip(call["event_records"], call["events"])], key=lambda row: row["global_yield_sequence"])
        report["ordered_events"] = [row["event"] for row in report["ordered_event_records"]]
        self.reject(report=report, application=application, expectation=expectation)

    def test_two_turn_required_calls_cannot_be_flattened_into_another_turn(self):
        application = next(deepcopy(case) for case in self.applications if len(case["conversation"]) == 2)
        expectation = next(deepcopy(case) for case in self.expectations if case["eval_id"] == application["eval_id"])
        report = synthetic_report(application, expectation)
        report["calls"][1]["events"][0]["content"]["parts"].extend(report["calls"][0]["events"][0]["content"]["parts"])
        report["calls"][0]["events"][0]["content"]["parts"] = []
        rebuild_events(report)
        result = self.assess(report, application, expectation)
        self.assertEqual(result["configured_metric"]["overall_eval_status"], "failed")
        self.assertEqual(result["configured_metric"]["per_invocation_results"][0]["score"], 0.0)

    def test_inputs_are_not_mutated_and_qualification_claims_cannot_be_inherited(self):
        report = deepcopy(self.report)
        report.update(source_authentication_proven=True, native_qualification_established=True, benchmark_grade_proven=True)
        before = deepcopy((report, self.application, self.expectation))
        result = self.assess(report)
        self.assertEqual((report, self.application, self.expectation), before)
        for key in ("source_authentication_proven", "native_authentication_proven", "source_closed_proven", "process_exit_proven",
                    "public_raw_binding_checked", "benchmark_grade_proven", "native_qualification_established", "state_effects_proven"):
            self.assertIs(result[key], False)
        self.assertTrue(result["journal_validation_is_caller_supplied"])
        self.assertFalse(result["filesystem_journal_revalidated_here"])

    def test_nonfinite_nonjson_or_deep_observations_are_rejected(self):
        for value in (float("inf"), object()):
            report = deepcopy(self.report); report["unsupported"] = value
            with self.assertRaises(ValueError):
                assess_source_case(report, self.application, self.expectation,
                                   expected_native_user_id=USER, expected_native_session_id=SESSION)
        report = deepcopy(self.report)
        nested = report
        for _ in range(50): nested["nested"] = {}; nested = nested["nested"]
        with self.assertRaises(ValueError):
            assess_source_case(report, self.application, self.expectation,
                               expected_native_user_id=USER, expected_native_session_id=SESSION)

    def test_real_stdlib_recorder_reader_shape_with_only_synthetic_producer(self):
        output = self.directory / "SYNTHETIC-JOURNAL-NOT-NATIVE"
        events = deepcopy(self.report["calls"][0]["events"])
        async def synthetic_producer(**kwargs):
            for event in events:
                yield event
        async def capture():
            journal = RunAsyncJournal(synthetic_producer, output, event_serializer=encoded, content_serializer=encoded, config_serializer=encoded)
            async for _ in journal.run_async(user_id=USER, session_id=SESSION, new_message=deepcopy(self.application["conversation"][0]["user_content"])):
                pass
            journal.finish()
        asyncio.run(capture())
        validation = read_closed_journal(output)
        result = self.assess(validation)
        self.assertEqual(result["configured_metric"]["overall_score"], 1.0)
        self.assertFalse(result["native_qualification_established"])


if __name__ == "__main__":
    unittest.main()
