"""Isolated SYNTHETIC JSON observations; no SDK, source app or model runs."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
from interoperability import agentops_answer_schema_v1 as answer
import test_agentops_reply_dependencies_v1 as fixture


class AnswerSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.obligations = json.loads((ROOT / "docs/research/upstream-agentops-grading-obligations-v1.json").read_bytes())["case_obligations"]
        cls.by_id = {o["eval_id"]: o for o in cls.obligations}
        cls.application = {(c["eval_set_id"], c["eval_id"]): c for c in json.loads(
            (ROOT / "runs/upstream-agentops-cases/v1/application/cases.json").read_bytes())["cases"]}

    def build(self, name="inventory-incident-report"):
        self.obligation = deepcopy(self.by_id[name])
        self.journal = fixture.synthetic_journal(self.obligation)
        family = self.obligation["family"]
        author = "triage_workflow" if family == "workflow" else "triage_report_agent" if family == "report" else "agentops_agent"
        self.bindings = {"schema_version": answer.BINDING_SCHEMA, "family": family,
                         "selection_profile": answer.SELECTION_PROFILE, "source_bindings": deepcopy(answer.SOURCE_BINDINGS), "turns": []}
        original = self.application[(self.obligation["eval_set_id"], name)]
        for index, (call, turn) in enumerate(zip(self.journal["calls"], self.obligation["turns"]), 1):
            call["inputs"]["new_message"] = deepcopy(original["conversation"][index - 1]["user_content"])
            nodes = {}
            for event in call["events"]:
                event["author"] = author
                if family == "workflow": event["node_info"] = {"path": "SYNTHETIC/workflow/investigate"}
            if family == "workflow":
                for stage in answer.STAGES:
                    nodes[stage] = {"author": author, "node_path": "SYNTHETIC/workflow/" + stage, "branch": None}
                call["events"].insert(0, self.text_event("SYNTHETIC plan", author, nodes["plan"]["node_path"]))
                for stage in answer.STAGES[1:]:
                    call["events"].append(self.text_event("SYNTHETIC " + stage, author, nodes[stage]["node_path"]))
            else:
                nodes["answer"] = {"author": author, "node_path": None, "branch": None}
                if family == "report":
                    incident = call["events"][1]["content"]["parts"][0]["function_response"]["response"]["incident"]
                    self.body = {"incident_id": incident["id"], "severity": incident["severity"],
                                 "affected_services": [incident["service"]], "hypothesis": "SYNTHETIC unassessed hypothesis",
                                 "evidence": ["SYNTHETIC unassessed evidence"], "recommended_runbook": incident["runbook"]}
                    call["events"].append(self.text_event(json.dumps(self.body), author))
                elif name not in {"restart-needs-approval", "resolve-needs-approval"}:
                    call["events"].append(self.text_event("SYNTHETIC unassessed answer", author))
            self.bindings["turns"].append({"turn_index": index, "native_invocation_id": f"SYNTHETIC-NATIVE-INVOCATION-{index}",
                                         "source_invocation_label": turn["source_invocation_label"], "nodes": nodes})
        fixture.rebuild(self.journal)

    @staticmethod
    def text_event(text, author="triage_report_agent", path=None, **kwargs):
        e = fixture.event([{"text": text}], author=author, **kwargs)
        if path is not None: e["node_info"] = {"path": path, "output_for": [path]}
        return e

    def assess(self, bindings="default"):
        supplied = self.bindings if bindings == "default" else bindings
        return answer.assess_answer_schema(self.journal, self.obligation, expected_native_user_id=fixture.USER,
                                           expected_native_session_id=fixture.SESSION, source_extraction_bindings=supplied)

    def write_body(self, body=None, text=None):
        self.journal["calls"][0]["events"][-1]["content"]["parts"] = [{"text": json.dumps(body) if text is None else text}]
        fixture.rebuild(self.journal)

    def test_all_original_21_cases_22_turns_keep_semantic_and_prose_lanes_pending(self):
        self.assertEqual(len(self.obligations), 21)
        self.assertEqual(sum(o["turn_count"] for o in self.obligations), 22)
        for o in self.obligations:
            with self.subTest(case=o["key"]):
                self.build(o["eval_id"])
                result = self.assess()
                for turn in result["turns"]:
                    self.assertEqual(turn["prompt_binding"]["status"], "consistent_with_pinned_source")
                    self.assertEqual(turn["semantic_manual_assessment"]["status"], "pending")
                    self.assertEqual(turn["prose_lexical_assessment"]["status"], "pending")
                    self.assertIsNone(turn["workflow_formal_output_schema"])
                for key in ("full_task_grade_assigned", "native_qualification_established", "original_metric_modified", "semantic_judge_executed"):
                    self.assertIs(result[key], False)

    def test_three_report_cases_pass_only_strict_structure_and_direct_observed_bindings(self):
        for name in answer.REPORT_TARGETS:
            self.build(name)
            turn = self.assess()["turns"][0]
            self.assertEqual(turn["strict_report_JSON"]["status"], "passed")
            self.assertEqual(turn["report_declared_schema_projection"]["status"], "passed")
            self.assertEqual(turn["report_direct_source_bindings"]["status"], "passed")
            self.assertFalse(turn["report_declared_schema_projection"]["installed_Pydantic_equivalence_proven"])

    def test_empty_individual_evidence_actions_and_duplicate_services_are_not_invented_schema_rules(self):
        self.build()
        self.body.update(hypothesis=" ", evidence=[""], proposed_actions=[""], affected_services=["inventory", "inventory"])
        self.write_body(self.body)
        turn = self.assess()["turns"][0]
        self.assertEqual(turn["report_declared_schema_projection"]["status"], "passed")
        self.assertEqual(turn["semantic_manual_assessment"]["status"], "pending")

    def test_declared_fields_types_enums_patterns_lengths_and_extra_fields(self):
        for field, bad in (("incident_id", "BAD"), ("severity", "SEV4"), ("severity", True),
                           ("affected_services", []), ("affected_services", [2]), ("affected_services", ["Upper"]),
                           ("hypothesis", ""), ("evidence", []), ("evidence", [True]),
                           ("recommended_runbook", "not_a_slug"), ("proposed_actions", None), ("extra", "forbidden")):
            with self.subTest(field=field, value=bad):
                self.build(); body = deepcopy(self.body); body[field] = bad; self.write_body(body)
                self.assertEqual(self.assess()["turns"][0]["report_declared_schema_projection"]["status"], "failed")
        self.build(); del self.body["evidence"]; self.write_body(self.body)
        self.assertEqual(self.assess()["turns"][0]["report_declared_schema_projection"]["status"], "failed")

    def test_strict_json_rejects_fences_prose_duplicate_keys_constants_and_nonobjects(self):
        for text in ("```json\n{}\n```", "Here is {}", '{"a":1,"a":2}', '{"evidence":[NaN]}', "[]", "{} {}", "null"):
            self.build(); self.write_body(text=text)
            self.assertEqual(self.assess()["turns"][0]["strict_report_JSON"]["status"], "failed")

    def test_parser_resource_limits_do_not_invent_syntax_or_schema_failure(self):
        for text in (" " * (1024 * 1024) + "{}", '{"hypothesis":1e400}', '{"extra":' + "[" * 60 + "0" + "]" * 60 + "}"):
            self.build(); self.write_body(text=text)
            self.assertEqual(self.assess()["turns"][0]["strict_report_JSON"]["status"], "unknown")

    def test_report_does_not_coerce_numbers_or_boolean_to_strings(self):
        self.build(); self.body["hypothesis"] = 1; self.write_body(self.body)
        self.assertEqual(self.assess()["turns"][0]["report_declared_schema_projection"]["status"], "failed")

    def test_wrong_target_severity_service_or_slug_fails_direct_binding(self):
        for field, value in (("incident_id", "INC-010"), ("severity", "SEV3"), ("affected_services", ["cache"]), ("recommended_runbook", "memory-leak")):
            self.build(); self.body[field] = value; self.write_body(self.body)
            self.assertEqual(self.assess()["turns"][0]["report_direct_source_bindings"]["status"], "failed")

    def test_adversarial_user_mentions_do_not_replace_original_report_target(self):
        self.build("resolved-cache-report-rejects-user-override")
        self.body.update(incident_id="INC-002", affected_services=["inventory"]); self.write_body(self.body)
        self.assertEqual(self.assess()["turns"][0]["report_direct_source_bindings"]["status"], "failed")

    def test_extra_service_support_stays_unknown_without_singleton_schema_requirement(self):
        self.build(); self.body["affected_services"].append("database"); self.write_body(self.body)
        turn = self.assess()["turns"][0]
        self.assertEqual(turn["report_declared_schema_projection"]["status"], "passed")
        self.assertEqual(turn["report_direct_source_bindings"]["status"], "unknown")

    def test_reference_seed_is_not_substituted_for_actual_incident_reply(self):
        self.build()
        incident = self.journal["calls"][0]["events"][1]["content"]["parts"][0]["function_response"]["response"]["incident"]
        incident["severity"] = "SEV3"; self.body["severity"] = "SEV3"; self.write_body(self.body)
        self.assertEqual(self.assess()["turns"][0]["report_direct_source_bindings"]["status"], "passed")

    def test_missing_or_ambiguous_incident_reply_remains_unknown(self):
        for duplicate in (False, True):
            self.build(); events = self.journal["calls"][0]["events"]
            if duplicate: events.insert(2, deepcopy(events[1]))
            else: events.pop(1)
            fixture.rebuild(self.journal)
            self.assertEqual(self.assess()["turns"][0]["report_direct_source_bindings"]["status"], "unknown")

    def test_incident_call_reply_and_answer_need_same_author_branch_and_node(self):
        for change in ("author", "branch", "node"):
            self.build(); events = self.journal["calls"][0]["events"]
            for e in events[:2]:
                if change == "author": e["author"] = "SYNTHETIC_OTHER_AGENT"
                elif change == "branch": e["branch"] = "SYNTHETIC_OTHER_BRANCH"
                else: e["node_info"] = {"path": "SYNTHETIC_OTHER_NODE"}
            fixture.rebuild(self.journal)
            self.assertEqual(self.assess()["turns"][0]["report_direct_source_bindings"]["status"], "unknown")

    def test_standalone_sdk_empty_default_node_path_is_explicitly_bindable(self):
        self.build(); self.bindings["turns"][0]["nodes"]["answer"]["node_path"] = ""
        for e in self.journal["calls"][0]["events"]: e["node_info"] = {"path": ""}
        fixture.rebuild(self.journal)
        self.assertEqual(self.assess()["turns"][0]["report_direct_source_bindings"]["status"], "passed")

    def test_multipart_non_thought_join_keeps_raw_parts_and_exact_offsets(self):
        self.build(); text = json.dumps(self.body); middle = len(text) // 2
        parts = [{"text": "SYNTHETIC private thought", "thought": True}, {"text": text[:middle]}, {"text": text[middle:]}]
        self.journal["calls"][0]["events"][-1]["content"]["parts"] = parts; fixture.rebuild(self.journal)
        extracted = self.assess()["turns"][0]["answer_extraction"]["answer"]
        self.assertEqual(extracted["text"], text)
        self.assertEqual(extracted["part_spans"][0]["part_index"], 1)
        self.assertEqual(extracted["part_spans"][1]["answer_start"], middle)
        self.assertEqual(extracted["evidence_ref"]["event"]["content"]["parts"], parts)

    def test_two_complete_terminal_answers_are_unknown_without_cherry_picking(self):
        self.build(); self.journal["calls"][0]["events"].append(deepcopy(self.journal["calls"][0]["events"][-1])); fixture.rebuild(self.journal)
        self.assertEqual(self.assess()["turns"][0]["answer_extraction"]["answer"]["status"], "unknown")

    def test_terminal_partial_and_unsupported_modal_surface_are_unknown(self):
        for kind in ("partial", "image"):
            self.build(); e = self.text_event("SYNTHETIC fragment", partial=kind == "partial")
            if kind == "image": e["content"]["parts"][0]["inline_data"] = {"mime_type": "image/png", "data": "SYNTHETIC"}
            self.journal["calls"][0]["events"].append(e); fixture.rebuild(self.journal)
            self.assertEqual(self.assess()["turns"][0]["answer_extraction"]["answer"]["status"], "unknown")

    def test_user_authored_or_function_reply_text_is_not_observed_answer(self):
        self.build(); self.journal["calls"][0]["events"][-1]["author"] = "user"; fixture.rebuild(self.journal)
        self.assertEqual(self.assess()["turns"][0]["answer_extraction"]["answer"]["status"], "unknown")

    def test_terminal_error_is_unavailable_not_fabricated_prose(self):
        self.build(); e = self.text_event("SYNTHETIC provider error"); e["error_code"] = "SYNTHETIC_FAILURE"
        self.journal["calls"][0]["events"].append(e); fixture.rebuild(self.journal)
        self.assertEqual(self.assess()["turns"][0]["answer_extraction"]["answer"]["status"], "unavailable")

    def test_source_guarded_pause_requires_actual_request_and_can_have_no_prose(self):
        for name in ("restart-needs-approval", "resolve-needs-approval"):
            self.build(name); extracted = self.assess()["turns"][0]["answer_extraction"]["answer"]
            self.assertEqual(extracted["status"], "unavailable"); self.assertIn("source_confirmation_pause", extracted["reason"])
            self.assertTrue(extracted["scope_events"])
            self.journal["calls"][0]["events"].pop(); fixture.rebuild(self.journal)
            self.assertEqual(self.assess()["turns"][0]["answer_extraction"]["answer"]["status"], "unknown")

    def test_post_pause_unrelated_tool_or_same_yield_extra_tool_cannot_claim_terminal_pause(self):
        for same_yield in (False, True):
            self.build("restart-needs-approval"); events = self.journal["calls"][0]["events"]
            part = {"function_call": fixture.function("get_runbook", {"slug": "service-down"}, "SYNTHETIC_EXTRA_CALL")}
            if same_yield: events[-1]["content"]["parts"].append(part)
            else: events.append(fixture.event([part], author="agentops_agent"))
            fixture.rebuild(self.journal)
            self.assertEqual(self.assess()["turns"][0]["answer_extraction"]["answer"]["status"], "unknown")

    def test_missing_text_pause_with_request_or_later_output_surface_stays_unknown(self):
        for same_event in (False, True):
            self.build("restart-needs-approval"); events = self.journal["calls"][0]["events"]
            if same_event:
                events[-1]["output"] = "SYNTHETIC ambiguous output"
            else:
                later = self.text_event("", author="agentops_agent"); later["output"] = "SYNTHETIC output-only answer"
                events.append(later)
            fixture.rebuild(self.journal)
            self.assertEqual(self.assess()["turns"][0]["answer_extraction"]["answer"]["status"], "unknown")

    def test_workflow_uses_explicit_paths_even_when_all_authors_match(self):
        self.build("checkout-evidence-review"); turn = self.assess()["turns"][0]
        self.assertEqual(set(turn["answer_extraction"]), set(answer.STAGES))
        self.assertEqual(turn["workflow_stage_order"]["status"], "unknown")
        self.assertEqual(turn["selected_candidate_order_consistency"]["status"], "consistent")
        self.assertEqual(turn["strict_report_JSON"]["status"], "not_applicable")

    def test_workflow_missing_stage_and_reordered_outputs_remain_separate(self):
        self.build("checkout-evidence-review"); self.journal["calls"][0]["events"].pop(); fixture.rebuild(self.journal)
        self.assertEqual(self.assess()["turns"][0]["workflow_stage_order"]["status"], "unknown")
        self.build("checkout-evidence-review"); events = self.journal["calls"][0]["events"]; events[-1], events[-2] = events[-2], events[-1]; fixture.rebuild(self.journal)
        self.assertEqual(self.assess()["turns"][0]["selected_candidate_order_consistency"]["status"], "inconsistent")

    def test_workflow_investigation_activity_before_plan_output_is_inconsistent(self):
        self.build("checkout-evidence-review"); events = self.journal["calls"][0]["events"]
        events[0], events[1] = events[1], events[0]; fixture.rebuild(self.journal)
        self.assertEqual(self.assess()["turns"][0]["selected_candidate_order_consistency"]["status"], "inconsistent")

    def test_caller_workflow_path_labels_never_prove_original_stage_identity(self):
        self.build("checkout-evidence-review")
        nodes = self.bindings["turns"][0]["nodes"]
        nodes["plan"], nodes["recommend"] = nodes["recommend"], nodes["plan"]
        turn = self.assess()["turns"][0]
        self.assertEqual(turn["workflow_stage_order"]["status"], "unknown")
        self.assertFalse(turn["selected_candidate_order_consistency"]["original_stage_order_proven"])

    def test_missing_or_wrong_source_bindings_and_original_input_are_unknown(self):
        self.build(); self.assertEqual(self.assess(None)["turns"][0]["answer_extraction"]["answer"]["status"], "unknown")
        self.bindings["source_bindings"]["models.py"] = "0" * 64
        self.assertEqual(self.assess()["turns"][0]["answer_extraction"]["answer"]["status"], "unknown")
        self.build(); self.journal["calls"][0]["inputs"]["new_message"]["parts"][0]["text"] += " SYNTHETIC changed question"; fixture.rebuild(self.journal)
        self.assertEqual(self.assess()["turns"][0]["prompt_binding"]["status"], "unknown")

    def test_sdk_null_defaults_do_not_rewrite_the_original_text_projection(self):
        self.build(); part = self.journal["calls"][0]["inputs"]["new_message"]["parts"][0]; part.update(thought=None, inline_data=None)
        fixture.rebuild(self.journal)
        self.assertEqual(self.assess()["turns"][0]["prompt_binding"]["status"], "consistent_with_pinned_source")

    def test_empty_user_part_metadata_default_matches_but_nonempty_metadata_stays_unknown(self):
        self.build(); part = self.journal["calls"][0]["inputs"]["new_message"]["parts"][0]; part["part_metadata"] = {}
        fixture.rebuild(self.journal)
        self.assertEqual(self.assess()["turns"][0]["prompt_binding"]["status"], "consistent_with_pinned_source")
        part["part_metadata"] = {"SYNTHETIC": "nondefault"}; fixture.rebuild(self.journal)
        self.assertEqual(self.assess()["turns"][0]["prompt_binding"]["status"], "unknown")

    def test_explicit_runtime_and_stage_binding_errors_raise(self):
        self.build(); self.bindings["turns"][0]["native_invocation_id"] = "SYNTHETIC_WRONG"
        with self.assertRaises(ValueError): self.assess()
        self.build("checkout-evidence-review"); self.bindings["turns"][0]["nodes"]["recommend"] = deepcopy(self.bindings["turns"][0]["nodes"]["plan"])
        with self.assertRaises(ValueError): self.assess()

    def test_report_output_defaults_match_but_incompatible_structured_output_is_unknown(self):
        self.build(); event = self.journal["calls"][0]["events"][-1]; event["output"] = {**self.body, "proposed_actions": []}; fixture.rebuild(self.journal)
        self.assertEqual(self.assess()["turns"][0]["report_output_surface_consistency"]["status"], "consistent")
        event["output"]["incident_id"] = "INC-010"; fixture.rebuild(self.journal)
        self.assertEqual(self.assess()["turns"][0]["report_direct_source_bindings"]["status"], "unknown")

    def test_later_output_only_event_cannot_silently_replace_selected_answer(self):
        self.build(); later = self.text_event(""); later["output"] = {**self.body, "incident_id": "INC-010"}
        self.journal["calls"][0]["events"].append(later); fixture.rebuild(self.journal)
        turn = self.assess()["turns"][0]
        self.assertEqual(turn["report_output_surface_consistency"]["status"], "unknown")
        self.assertEqual(turn["report_direct_source_bindings"]["status"], "unknown")
        self.build("inventory-status"); later = self.text_event("", author="agentops_agent"); later["output"] = "SYNTHETIC different output"
        self.journal["calls"][0]["events"].append(later); fixture.rebuild(self.journal)
        self.assertEqual(self.assess()["turns"][0]["answer_extraction"]["answer"]["status"], "unknown")

    def test_nonreport_structured_output_and_malformed_node_metadata_are_unknown(self):
        self.build("inventory-status"); e = self.journal["calls"][0]["events"][-1]; e["output"] = {"invented": "schema"}; fixture.rebuild(self.journal)
        self.assertEqual(self.assess()["turns"][0]["answer_extraction"]["answer"]["status"], "unknown")
        self.build(); self.journal["calls"][0]["events"][-1]["node_info"] = "SYNTHETIC malformed"; fixture.rebuild(self.journal)
        self.assertEqual(self.assess()["turns"][0]["answer_extraction"]["answer"]["status"], "unknown")

    def test_nonjson_source_extraction_bindings_are_rejected(self):
        self.build(); self.bindings["unsupported"] = float("nan")
        with self.assertRaises(ValueError): self.assess()

    def test_inputs_and_returned_provenance_are_isolated_and_proof_flags_not_inherited(self):
        self.build(); self.journal["native_qualification_established"] = True
        before, bindings = deepcopy(self.journal), deepcopy(self.bindings)
        result = self.assess(); self.assertEqual(self.journal, before); self.assertEqual(self.bindings, bindings)
        result["turns"][0]["answer_extraction"]["answer"]["evidence_ref"]["event"]["content"]["parts"][0]["text"] = "SYNTHETIC result edit"
        self.assertEqual(self.journal, before); self.assertFalse(result["native_qualification_established"])


if __name__ == "__main__":
    unittest.main()
