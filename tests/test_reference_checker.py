"""Independent-checker tests using saved native data and labelled derivatives.

Mutations are software validation controls, never naturally observed defects.
No capture driver, application, projector or solver is imported.
"""

import base64
import copy
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import unittest

from interoperability.reference_checker import check_reference_trace


ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "runs/native-reference-continuation/carol-run-20261023T204701107557Z-24356/report.json"


def observed():
    return json.loads(CAPTURE.read_text(encoding="utf-8"))


def derivative():
    report = copy.deepcopy(observed())
    report["controlled_derivative"] = "Independent reference-checker semantic mutation"
    return report


def phase(report, suffix):
    return next(item for item in report["http_exchanges"] if item["phase"] == suffix)


def set_body(record, value=None, raw=None):
    if raw is None:
        raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    encoded = raw.encode("utf-8")
    record.update(raw=raw, raw_base64=base64.b64encode(encoded).decode("ascii"),
                  sha256=hashlib.sha256(encoded).hexdigest(),
                  json=json.loads(raw))


def costs(report):
    report["costs"] = {
        "native_http_requests": len(report["http_exchanges"]),
        "native_rpc_requests": sum(item["request"]["json"] is not None for item in report["http_exchanges"]),
        "request_bytes": sum(len(base64.b64decode(item["request"]["raw_base64"] or "")) for item in report["http_exchanges"]),
        "response_bytes": sum(len(base64.b64decode(item["response"]["raw_base64"])) for item in report["http_exchanges"]),
    }


def response_task(report, phase_name, mutate, control_field=None, control_index=0):
    exchange = phase(report, phase_name)
    response = copy.deepcopy(exchange["response"]["json"])
    mutate(response["result"])
    set_body(exchange["response"], response)
    if control_field:
        report["controls"][control_index][control_field] = copy.deepcopy(response["result"])
    costs(report)


class ReferenceChecker(unittest.TestCase):
    def test_actual_original_native_capture_checks(self):
        self.assertTrue(check_reference_trace(observed()))

    def test_false_summary_claims_cannot_override_raw_records(self):
        for index, key, value in [(0, "native_completion_observed", False),
                                  (1, "native_completion_observed", True),
                                  (2, "same_task_answer_id", True),
                                  (0, "same_context_answer", False),
                                  (1, "with_refs", True),
                                  (2, "with_task_id", True)]:
            with self.subTest(index=index, key=key):
                report = derivative()
                report["controls"][index][key] = value
                self.assertFalse(check_reference_trace(report))

    def test_deleted_decisive_evidence_is_not_replaced_by_summary(self):
        for name in ["agent_card", "N1_same_task_with_reference:get_pending",
                     "N1_same_task_with_reference:answer",
                     "N1_same_task_with_reference:get_original_after_answer",
                     "N3_context_only_without_reference:get_answer_created_task"]:
            with self.subTest(name=name):
                report = derivative()
                report["http_exchanges"] = [item for item in report["http_exchanges"] if item["phase"] != name]
                costs(report)
                self.assertFalse(check_reference_trace(report))

    def test_all_control_summaries_are_required(self):
        report = derivative()
        report["controls"].pop()
        self.assertFalse(check_reference_trace(report))

    def test_rehashed_wrong_reply_id_is_rejected(self):
        report = derivative()
        record = phase(report, "N1_same_task_with_reference:answer")["response"]
        value = copy.deepcopy(record["json"])
        value["id"] = "another-request"
        set_body(record, value)
        costs(report)
        self.assertFalse(check_reference_trace(report))

    def test_rehashed_native_error_cannot_back_a_success(self):
        report = derivative()
        record = phase(report, "N1_same_task_with_reference:get_original_after_answer")["response"]
        value = copy.deepcopy(record["json"])
        value["error"] = {"code": -32001, "message": "Native get failed"}
        set_body(record, value)
        costs(report)
        self.assertFalse(check_reference_trace(report))

    def test_rehashed_empty_native_snapshot_cannot_back_a_success(self):
        report = derivative()
        response_task(report, "N1_same_task_with_reference:get_original_after_answer",
                      lambda task: task.clear(), "final_original_task")
        self.assertFalse(check_reference_trace(report))

    def test_rehashed_wrong_task_is_rejected_even_with_matching_summary(self):
        report = derivative()
        response_task(report, "N1_same_task_with_reference:get_original_after_answer",
                      lambda task: task.update(id="some-other-task"), "final_original_task")
        self.assertFalse(check_reference_trace(report))

    def test_rehashed_wrong_context_is_rejected_even_with_matching_summary(self):
        report = derivative()
        response_task(report, "N1_same_task_with_reference:get_original_after_answer",
                      lambda task: task.update(contextId="some-other-context"), "final_original_task")
        self.assertFalse(check_reference_trace(report))

    def test_rehashed_false_completion_for_near_miss_is_rejected(self):
        report = derivative()
        for name, summary in [("answer", "answer_reply"),
                              ("get_original_after_answer", "final_original_task")]:
            response_task(report, "N2_same_task_without_reference:" + name,
                          lambda task: task["status"].update(state="completed"), summary, 1)
        report["controls"][1]["native_completion_observed"] = True
        self.assertFalse(check_reference_trace(report))

    def test_omitted_completed_artifacts_do_not_change_status_only_goal(self):
        report = derivative()
        for name, summary in [("answer", "answer_reply"),
                              ("get_original_after_answer", "final_original_task")]:
            response_task(report, "N1_same_task_with_reference:" + name,
                          lambda task: task.pop("artifacts", None), summary)
        self.assertTrue(check_reference_trace(report))

    def test_rehashed_reference_omission_is_rejected(self):
        report = derivative()
        record = phase(report, "N1_same_task_with_reference:answer")["request"]
        value = copy.deepcopy(record["json"])
        value["params"]["message"]["referenceTaskIds"] = []
        set_body(record, value)
        report["controls"][0]["with_refs"] = False
        costs(report)
        self.assertFalse(check_reference_trace(report))

    def test_rehashed_reference_to_another_task_is_rejected(self):
        report = derivative()
        record = phase(report, "N1_same_task_with_reference:answer")["request"]
        value = copy.deepcopy(record["json"])
        value["params"]["message"]["referenceTaskIds"] = [report["controls"][1]["task_id"]]
        set_body(record, value)
        costs(report)
        self.assertFalse(check_reference_trace(report))

    def test_rehashed_wrong_answer_text_and_role_are_rejected(self):
        for role, text in [("agent", "Well done!"), ("user", "shuffle again")]:
            with self.subTest(role=role, text=text):
                report = derivative()
                record = phase(report, "N1_same_task_with_reference:answer")["request"]
                value = copy.deepcopy(record["json"])
                value["params"]["message"].update(role=role, parts=[{"kind": "text", "text": text}])
                set_body(record, value)
                costs(report)
                self.assertFalse(check_reference_trace(report))

    def test_context_only_control_cannot_silently_supply_task_id(self):
        report = derivative()
        record = phase(report, "N3_context_only_without_reference:answer")["request"]
        value = copy.deepcopy(record["json"])
        value["params"]["message"]["taskId"] = report["controls"][2]["task_id"]
        set_body(record, value)
        costs(report)
        self.assertFalse(check_reference_trace(report))

    def test_context_only_new_task_get_cannot_be_an_original_task_get(self):
        report = derivative()
        response_task(report, "N3_context_only_without_reference:get_answer_created_task",
                      lambda task: task.update(id=report["controls"][2]["task_id"]),
                      "answer_created_task_get", 2)
        self.assertFalse(check_reference_trace(report))

    def test_raw_parsed_hash_and_base64_consistency_are_all_required(self):
        for field, value in [("sha256", "0" * 64), ("raw", "{}"),
                             ("raw_base64", "e30="), ("json", {})]:
            with self.subTest(field=field):
                report = derivative()
                phase(report, "N1_same_task_with_reference:answer")["response"][field] = value
                self.assertFalse(check_reference_trace(report))

    def test_raw_duplicate_json_keys_are_rejected_after_rehash(self):
        report = derivative()
        record = phase(report, "N1_same_task_with_reference:answer")["response"]
        raw = record["raw"].replace('"jsonrpc":"2.0"', '"jsonrpc":"1.0","jsonrpc":"2.0"')
        set_body(record, raw=raw)
        costs(report)
        self.assertFalse(check_reference_trace(report))

    def test_nonfinite_json_constants_are_rejected_after_rehash(self):
        report = derivative()
        record = phase(report, "N1_same_task_with_reference:answer")["response"]
        set_body(record, raw=record["raw"][:-1] + ',"invalid_number":NaN}')
        costs(report)
        self.assertFalse(check_reference_trace(report))

    def test_invalid_utf8_and_base64_are_rejected(self):
        for bad in ["not-base64!", base64.b64encode(b"\xff").decode()]:
            with self.subTest(bad=bad):
                report = derivative()
                phase(report, "N1_same_task_with_reference:answer")["response"]["raw_base64"] = bad
                self.assertFalse(check_reference_trace(report))

    def test_duplicate_and_wrong_phase_records_are_rejected(self):
        for field, value in [("exchange_id", "native-2"), ("phase", "unknown:cancel")]:
            with self.subTest(field=field):
                report = derivative()
                phase(report, "N2_same_task_without_reference:answer")[field] = value
                self.assertFalse(check_reference_trace(report))

    def test_chronology_must_match_utc_and_monotonic_clocks(self):
        for field in ["started_at_utc", "monotonic_ns"]:
            with self.subTest(field=field):
                report = derivative()
                request = phase(report, "N2_same_task_without_reference:answer")["request"]
                if field == "started_at_utc":
                    stamp = datetime.fromisoformat(request[field].replace("Z", "+00:00")) - timedelta(seconds=10)
                    request[field] = stamp.isoformat()
                else:
                    request[field] = 0
                self.assertFalse(check_reference_trace(report))

    def test_body_byte_and_request_costs_are_recomputed(self):
        for name in ["native_http_requests", "native_rpc_requests", "request_bytes", "response_bytes"]:
            with self.subTest(name=name):
                report = derivative()
                report["costs"][name] += 1
                self.assertFalse(check_reference_trace(report))

    def test_bool_is_not_an_integer_cost_or_status(self):
        for name in ["cost", "status", "elapsed", "exit", "models"]:
            with self.subTest(name=name):
                report = derivative()
                if name == "cost":
                    report["costs"]["native_rpc_requests"] = True
                elif name == "status":
                    phase(report, "N1_same_task_with_reference:answer")["response"]["status"] = True
                elif name == "elapsed":
                    phase(report, "N1_same_task_with_reference:answer")["elapsed_ms"] = True
                elif name == "exit":
                    report["exit_code"] = False
                else:
                    report["model_calls"] = False
                self.assertFalse(check_reference_trace(report))

    def test_wrong_protocol_source_and_nonloopback_endpoint_are_rejected(self):
        for key, value in [("source_commit", "0" * 40), ("protocol", "A2A 1.0 JSONRPC"),
                           ("endpoint", "https://remote.example"), ("model_calls", 1)]:
            with self.subTest(key=key):
                report = derivative()
                report[key] = value
                self.assertFalse(check_reference_trace(report))

    def test_rehashed_agent_card_protocol_change_is_rejected(self):
        report = derivative()
        card = copy.deepcopy(report["observed_card"])
        card["protocolVersion"] = "1.0"
        set_body(report["http_exchanges"][0]["response"], card)
        report["observed_card"] = card
        costs(report)
        self.assertFalse(check_reference_trace(report))

    def test_wrong_state_schema_and_http_error_are_rejected(self):
        report = derivative()
        response_task(report, "N1_same_task_with_reference:get_original_after_answer",
                      lambda task: task["status"].update(state="TASK_STATE_COMPLETED"), "final_original_task")
        self.assertFalse(check_reference_trace(report))
        report = derivative()
        phase(report, "N1_same_task_with_reference:get_original_after_answer")["response"]["status"] = 500
        self.assertFalse(check_reference_trace(report))

    def test_failed_control_and_unverified_cleanup_are_rejected(self):
        report = derivative()
        report["controls"][1].update(outcome="failed", error="Timeout")
        self.assertFalse(check_reference_trace(report))
        report = derivative()
        report["process"]["terminal_verified"] = False
        self.assertFalse(check_reference_trace(report))

    def test_windows_termination_code_does_not_invalidate_completed_observations(self):
        report = derivative()
        report["process"]["exit_code"] = 1
        self.assertTrue(check_reference_trace(report))

    def test_malformed_inputs_return_false(self):
        for value in [None, True, 1, "report", [], {}, {"schema_version": "native-reference-continuation/1"}]:
            with self.subTest(value=value):
                self.assertFalse(check_reference_trace(value))
        report = derivative()
        report["http_exchanges"] = [None]
        self.assertFalse(check_reference_trace(report))

    def test_deep_malformed_json_returns_false_without_exception(self):
        report = derivative()
        record = phase(report, "N1_same_task_with_reference:answer")["response"]
        raw = ("[" * 1500 + "0" + "]" * 1500).encode("utf-8")
        record.update(raw=raw.decode("utf-8"), raw_base64=base64.b64encode(raw).decode(),
                      sha256=hashlib.sha256(raw).hexdigest(), json=0)
        costs(report)
        self.assertFalse(check_reference_trace(report))


if __name__ == "__main__":
    unittest.main()
