"""All 21/22 obligations with SYNTHETIC logical boundary snapshots only.

No database, source runtime, SDK, Presidio or model is executed. Source JSON is
read solely to select obligations. Invented rows never become native evidence.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from interoperability import agentops_source_case_effects_v1 as effects

USER, SESSION = "SYNTHETIC_EFFECT_USER", "SYNTHETIC_EFFECT_SESSION"


def business():
    names = {"services": ["name", "description", "status", "owner"],
             "incidents": ["id", "service", "title", "severity", "status", "runbook", "opened_at", "resolved_at", "summary"],
             "audit_log": ["id", "schema_version", "ts", "actor", "approved_by", "rationale", "context_summary", "session_id", "invocation_id", "action", "target", "detail"],
             "sqlite_sequence": ["name", "seq"]}
    columns = {}
    for table, items in names.items():
        columns[table] = []
        for cid, name in enumerate(items):
            kind = "" if table == "sqlite_sequence" else "INTEGER" if table == "audit_log" and name in ("id", "schema_version") else "TEXT"
            nullable = table == "sqlite_sequence" or (table == "services" and name == "name") or (table == "incidents" and name in ("id", "resolved_at")) or (table == "audit_log" and name == "id")
            columns[table].append({"cid": cid, "name": name, "type": kind, "notnull": 0 if nullable else 1,
                                   "dflt_value": "1" if name == "schema_version" else None,
                                   "pk": int((table == "services" and name == "name") or (table in ("incidents", "audit_log") and name == "id"))})
    audit = {name: "SYNTHETIC old audit " + name for name in names["audit_log"]}
    audit.update(id=7, schema_version=1)
    return {"path": "state/incidents.db", "path_base": "SYNTHETIC_run", "user_tables": ["audit_log", "incidents", "services"],
            "user_version": 0, "columns": columns,
            "schema": [{"type": "table", "name": table, "tbl_name": table, "sql": "SYNTHETIC declared table " + table}
                       for table in sorted(names)],
            "tables": {"services": [{"name": "api-gateway", "description": "SYNTHETIC gateway", "status": "degraded", "owner": "SYNTHETIC owner"},
                                     {"name": "inventory", "description": "SYNTHETIC inventory", "status": "down", "owner": "SYNTHETIC owner"}],
                       "incidents": [{"id": "INC-010", "service": "api-gateway", "title": "SYNTHETIC incident", "severity": "SEV1",
                                      "status": "open", "runbook": "service-down", "opened_at": "2026-10-29T00:00:00Z", "resolved_at": None, "summary": "SYNTHETIC"}],
                       "audit_log": [audit], "sqlite_sequence": [{"name": "audit_log", "seq": 9}]}}


def absent():
    return {"schema_version": "agentops-memory-snapshot/1", "status": "absent", "exists_observed": False,
            "notes": [], "sqlite_sequence": [], "errors": []}


def memory(notes=(), sequence=None):
    return {"schema_version": "agentops-memory-snapshot/1", "status": "recorded", "exists_observed": True,
            "transaction_snapshot": True, "user_version": 0, "errors": [], "row_count": len(notes),
            "columns": [[0, "id", "INTEGER", 0, None, 1], [1, "ts", "TEXT", 1, None, 0], [2, "user_id", "TEXT", 1, None, 0],
                        [3, "incident_id", "TEXT", 1, None, 0], [4, "note", "TEXT", 1, None, 0]],
            "schema": [{"type": "index", "name": "idx_notes_user_incident", "table_name": "incident_notes",
                        "sql": "CREATE INDEX idx_notes_user_incident ON incident_notes (user_id, incident_id)"},
                       {"type": "table", "name": "incident_notes", "table_name": "incident_notes",
                        "sql": "CREATE TABLE incident_notes (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, user_id TEXT NOT NULL, incident_id TEXT NOT NULL, note TEXT NOT NULL)"},
                       {"type": "table", "name": "sqlite_sequence", "table_name": "sqlite_sequence", "sql": "CREATE TABLE sqlite_sequence(name,seq)"}],
            "notes": deepcopy(list(notes)), "sqlite_sequence": [] if sequence is None else [{"name": "incident_notes", "seq": sequence}]}


def row(identifier=1, user=USER, note=effects.NOTE):
    return {"id": identifier, "ts": "2026-10-30T12:00:00Z", "user_id": user, "incident_id": "INC-010", "note": note}


def boundaries(obligation, old_memory=None):
    base_memory = absent() if old_memory is None else deepcopy(old_memory)
    base = {"business": business(), "memory": base_memory}
    result = {"schema_version": "agentops-source-case-boundaries/1",
              "source_case": {"eval_set_id": obligation["eval_set_id"], "eval_id": obligation["eval_id"]},
              "startup": {**deepcopy(base), "readiness_before": deepcopy(base)}, "turns": []}
    current_memory = deepcopy(base_memory)
    if obligation["key"] == effects.MEMORY_KEY:
        sequence = base_memory["sqlite_sequence"][0]["seq"] if base_memory["sqlite_sequence"] else 0
        current_memory = memory([*base_memory["notes"], row(sequence + 1)], sequence + 1)
    for index, turn in enumerate(obligation["turns"], 1):
        before = deepcopy(base_memory if index == 1 else current_memory)
        terminal = deepcopy(current_memory)
        result["turns"].append({"turn_index": index, "source_invocation_label": turn["source_invocation_label"],
                                "native_user_id": USER, "native_session_id": SESSION,
                                "samples": [{"sample_ordinal": 1, "stage": "before", "business": business(), "memory": before},
                                            {"sample_ordinal": 2, "stage": "in_progress", "business": business(), "memory": deepcopy(terminal)},
                                            {"sample_ordinal": 3, "stage": "terminal", "business": business(), "memory": terminal}]})
    result["retained_close"] = {"business": business(), "memory": deepcopy(current_memory)}
    return result


def profile(value, representation="raw", fixture=False):
    notes = value["turns"][0]["samples"][-1]["memory"]["notes"]
    inserted = notes[-1]
    transform = (lambda text: text) if representation == "raw" else (lambda text: effects.PREFIX + "\n" + text + "\n" + effects.SUFFIX)
    selected = [item for item in reversed(notes) if item["user_id"] == USER and item["incident_id"] == "INC-010"][:20]
    result = {"schema_version": "agentops-source-memory-note-observation/1", "native_user_id": USER, "native_session_id": SESSION,
              "incident_id": "INC-010", "source_note_input": effects.NOTE, "save_reply_representation": representation,
              "save_reply": {"saved": {"incident_id": "INC-010", "ts": inserted["ts"], "note": transform(inserted["note"])}},
              "recall_reply": {"count": len(selected), "notes": [{"ts": item["ts"], "incident_id": item["incident_id"], "note": transform(item["note"])} for item in selected]}}
    if fixture:
        result["original_sanitizer_fixture"] = {"schema_version": "agentops-original-note-sanitizer-fixture/1", "status": "validated",
                "original_sanitizer_executed": True, "model_calls": 0, "input_note": effects.NOTE.strip(), "output_note": inserted["note"],
                "source_bindings": deepcopy(effects.SOURCE_BINDINGS)}
    return result


class SourceCaseEffectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.obligations = json.loads((ROOT / "docs/research/upstream-agentops-grading-obligations-v1.json").read_bytes())["case_obligations"]
        cls.memory_case = next(item for item in cls.obligations if item["key"] == effects.MEMORY_KEY)

    def assess(self, obligation, value, captured=None):
        return effects.assess_source_case_effects(obligation, value, expected_native_user_id=USER,
                                                 expected_native_session_id=SESSION, sanitized_note_profile=captured)

    def test_all_21_cases_22_turns_have_only_the_declared_sampled_effects(self):
        self.assertEqual(len(self.obligations), 21)
        self.assertEqual(sum(item["turn_count"] for item in self.obligations), 22)
        self.assertEqual({item["key"] for item in self.obligations}, set(effects.CASES))
        for item in self.obligations:
            with self.subTest(case=item["key"]):
                result = self.assess(item, boundaries(item))
                self.assertEqual(result["business"]["status"], "consistent")
                self.assertEqual(result["memory_structure"]["status"], "consistent")
                self.assertFalse(result["native_source_case_qualification"])
                self.assertFalse(result["full_task_grade_assigned"])
                self.assertFalse(result["continuous_mutation_absence_proven"])
                self.assertFalse(result["cross_store_atomicity_proven"])
                if item["key"] == effects.MEMORY_KEY:
                    self.assertEqual(result["memory_save_reply"]["status"], "unknown")
                    self.assertEqual(result["sanitizer_fidelity"]["status"], "pending")

    def test_all_21_cases_detect_business_mutation_at_intermediate_boundary(self):
        for item in self.obligations:
            value = boundaries(item)
            value["turns"][0]["samples"][1]["business"]["tables"]["services"][1]["status"] = "operational"
            self.assertEqual(self.assess(item, value)["business"]["status"], "inconsistent", item["key"])

    def test_all_21_cases_detect_extra_memory_writes_without_deduplication(self):
        for item in self.obligations:
            value = boundaries(item)
            target = value["turns"][0]["samples"][-1]
            if item["key"] == effects.MEMORY_KEY:
                target["memory"] = memory([row(1), row(2)], 2)
            else:
                target["memory"] = memory([row(1)], 1)
            self.assertEqual(self.assess(item, value)["memory_structure"]["status"], "inconsistent", item["key"])

    def test_audit_rows_sequence_and_schema_change_are_business_effects(self):
        item = self.obligations[0]
        for change in ("audit", "sequence", "schema"):
            value = boundaries(item); target = value["retained_close"]["business"]
            if change == "audit": target["tables"]["audit_log"][0]["detail"] += " changed"
            elif change == "sequence": target["tables"]["sqlite_sequence"][0]["seq"] += 1
            else: target["schema"][0]["sql"] += " changed"
            self.assertEqual(self.assess(item, value)["business"]["status"], "inconsistent")

    def test_missing_startup_does_not_use_first_business_request_as_baseline(self):
        for item in self.obligations:
            value = boundaries(item); value["startup"] = None
            result = self.assess(item, value)
            self.assertEqual(result["business"]["status"], "unknown")
            self.assertEqual(result["memory_structure"]["status"], "unknown")
            self.assertFalse(result["business"]["all_business_tables_compared"])

    def test_missing_turn_terminal_or_retained_close_remains_unknown(self):
        for change in ("terminal", "close"):
            value = boundaries(self.memory_case)
            if change == "terminal": value["turns"][0]["samples"] = value["turns"][0]["samples"][:-1]
            else: del value["retained_close"]
            result = self.assess(self.memory_case, value)
            self.assertEqual(result["business"]["status"], "unknown")
            self.assertEqual(result["memory_structure"]["status"], "unknown")

    def test_lazy_absence_is_not_an_empty_materialized_store(self):
        item = self.obligations[0]
        value = boundaries(item)
        value["retained_close"]["memory"] = memory()
        self.assertEqual(self.assess(item, value)["memory_structure"]["status"], "inconsistent")
        value = boundaries(item, memory())
        self.assertEqual(self.assess(item, value)["memory_structure"]["status"], "consistent")

    def test_memory_schema_can_appear_before_intended_insert_only_during_turn1(self):
        value = boundaries(self.memory_case)
        value["turns"][0]["samples"][1]["memory"] = memory()
        self.assertEqual(self.assess(self.memory_case, value)["memory_structure"]["status"], "consistent")
        value["turns"][0]["samples"][-1]["memory"] = memory()
        self.assertEqual(self.assess(self.memory_case, value)["memory_structure"]["status"], "inconsistent")

    def test_observed_lazy_materialization_cannot_disappear_and_reappear(self):
        value = boundaries(self.memory_case)
        first = value["turns"][0]["samples"]
        first[1]["memory"] = memory()
        first.insert(2, {"sample_ordinal": 3, "stage": "in_progress", "business": business(), "memory": absent()})
        first[-1]["sample_ordinal"] = 4
        result = self.assess(self.memory_case, value)
        self.assertEqual(result["memory_structure"]["status"], "inconsistent")
        self.assertTrue(any("materialized memory store disappeared" in reason for reason in result["memory_structure"]["reasons"]))

    def test_prior_duplicate_notes_unrelated_users_and_sequence_gaps_are_preserved(self):
        prior = [row(5, user="SYNTHETIC_OTHER", note="SYNTHETIC duplicate"), row(7, user=USER, note="SYNTHETIC duplicate"), row(8, user=USER, note="SYNTHETIC duplicate")]
        value = boundaries(self.memory_case, memory(prior, 13))
        result = self.assess(self.memory_case, value, profile(value))
        self.assertEqual(result["memory_structure"]["status"], "consistent")
        self.assertEqual(result["inserted_memory_row"]["id"], 14)
        self.assertEqual(result["memory_recall_reply"]["status"], "consistent")
        value["turns"][0]["samples"][-1]["memory"]["notes"][0]["note"] = "SYNTHETIC changed unrelated user"
        self.assertEqual(self.assess(self.memory_case, value)["memory_structure"]["status"], "inconsistent")

    def test_insert_identity_timestamp_and_sequence_must_match_source_contract(self):
        for change in ("user", "incident", "id", "sequence", "timestamp"):
            value = boundaries(self.memory_case); target = value["turns"][0]["samples"][-1]["memory"]
            if change == "user": target["notes"][0]["user_id"] = "SYNTHETIC_OTHER"
            elif change == "incident": target["notes"][0]["incident_id"] = "INC-001"
            elif change == "id": target["notes"][0]["id"] = 2; target["sqlite_sequence"][0]["seq"] = 2
            elif change == "sequence": target["sqlite_sequence"][0]["seq"] = 2
            else: target["notes"][0]["ts"] = "2026-02-30T12:00:00Z"
            self.assertEqual(self.assess(self.memory_case, value)["memory_structure"]["status"], "inconsistent")

    def test_missing_incident_in_startup_state_cannot_authorize_orphan_note(self):
        value = boundaries(self.memory_case)
        value["startup"]["business"]["tables"]["incidents"] = []
        self.assertEqual(self.assess(self.memory_case, value)["memory_structure"]["status"], "inconsistent")

    def test_turn2_or_retained_close_cannot_change_the_observed_committed_note(self):
        for target in ("turn2", "close"):
            value = boundaries(self.memory_case)
            point = value["turns"][1]["samples"][1] if target == "turn2" else value["retained_close"]
            point["memory"]["notes"][0]["note"] += " changed"
            self.assertEqual(self.assess(self.memory_case, value)["memory_structure"]["status"], "inconsistent")

    def test_raw_and_source_spotlight_replies_bind_rows_without_sanitizer_assumption(self):
        for representation in ("raw", "source_spotlight"):
            value = boundaries(self.memory_case)
            result = self.assess(self.memory_case, value, profile(value, representation))
            self.assertEqual(result["memory_save_reply"]["status"], "consistent")
            self.assertEqual(result["memory_recall_reply"]["status"], "consistent")
            self.assertEqual(result["sanitizer_fidelity"]["status"], "pending")
            self.assertFalse(result["sanitizer_fidelity"]["generic_sanitizer_equivalence_proven"])

    def test_save_reply_and_recall_reply_failures_are_separate(self):
        value = boundaries(self.memory_case); captured = profile(value)
        captured["recall_reply"]["count"] = True
        result = self.assess(self.memory_case, value, captured)
        self.assertEqual(result["memory_save_reply"]["status"], "consistent")
        self.assertEqual(result["memory_recall_reply"]["status"], "inconsistent")
        captured = profile(value); captured["save_reply"]["saved"]["ts"] = "SYNTHETIC_WRONG_TIMESTAMP"
        result = self.assess(self.memory_case, value, captured)
        self.assertEqual(result["memory_save_reply"]["status"], "inconsistent")
        self.assertEqual(result["memory_recall_reply"]["status"], "consistent")

    def test_missing_save_reply_is_unknown_while_supplied_contradiction_is_inconsistent(self):
        for missing in ("omitted", "null"):
            value = boundaries(self.memory_case); captured = profile(value)
            if missing == "omitted": del captured["save_reply"]
            else: captured["save_reply"] = None
            result = self.assess(self.memory_case, value, captured)
            self.assertEqual(result["memory_structure"]["status"], "consistent")
            self.assertEqual(result["memory_save_reply"]["status"], "unknown")
            self.assertEqual(result["memory_recall_reply"]["status"], "consistent")
        value = boundaries(self.memory_case); captured = profile(value)
        captured["save_reply"] = {"error": "SYNTHETIC contradiction"}
        self.assertEqual(self.assess(self.memory_case, value, captured)["memory_save_reply"]["status"], "inconsistent")

    def test_supplied_single_sanitizer_fixture_is_exactly_bound_not_general_equivalence(self):
        value = boundaries(self.memory_case)
        captured = profile(value, fixture=True)
        result = self.assess(self.memory_case, value, captured)
        self.assertEqual(result["sanitizer_fidelity"]["status"], "consistent_with_supplied_single_fixture")
        self.assertFalse(result["sanitizer_fidelity"]["generic_sanitizer_equivalence_proven"])
        captured["original_sanitizer_fixture"]["source_bindings"]["pii.py"] = "0" * 64
        result = self.assess(self.memory_case, value, captured)
        self.assertEqual(result["sanitizer_fidelity"]["status"], "unknown")
        self.assertEqual(result["memory_save_reply"]["status"], "consistent")

    def test_unknown_sanitizer_output_is_not_assumed_to_equal_unredacted_source_note(self):
        value = boundaries(self.memory_case)
        for point in [*value["turns"][0]["samples"][1:], *value["turns"][1]["samples"], value["retained_close"]]:
            point["memory"]["notes"][0]["note"] = "SYNTHETIC observed transformed note"
        result = self.assess(self.memory_case, value, profile(value))
        self.assertEqual(result["memory_structure"]["status"], "consistent")
        self.assertEqual(result["memory_save_reply"]["status"], "consistent")
        self.assertEqual(result["sanitizer_fidelity"]["status"], "pending")

    def test_recall_source_order_limit20_duplicates_and_user_partition_are_preserved(self):
        prior = [row(index, user=USER if index % 2 else "SYNTHETIC_OTHER", note="SYNTHETIC duplicate") for index in range(1, 45)]
        value = boundaries(self.memory_case, memory(prior, 44))
        captured = profile(value)
        self.assertEqual(captured["recall_reply"]["count"], 20)
        self.assertEqual(self.assess(self.memory_case, value, captured)["memory_recall_reply"]["status"], "consistent")
        captured["recall_reply"]["notes"].reverse()
        # Distinct new note must stay first even when older content is duplicated.
        self.assertEqual(self.assess(self.memory_case, value, captured)["memory_recall_reply"]["status"], "inconsistent")

    def test_unsupported_store_schema_and_boolean_descriptors_stay_unknown(self):
        item = self.obligations[0]
        value = boundaries(item); value["retained_close"]["memory"] = {"schema_version": "agentops-memory-snapshot/1", "status": "unsupported", "errors": []}
        self.assertEqual(self.assess(item, value)["memory_structure"]["status"], "unknown")
        value = boundaries(item); value["retained_close"]["business"]["columns"]["audit_log"][0]["cid"] = False
        self.assertEqual(self.assess(item, value)["business"]["status"], "unknown")

    def test_business_baseline_sequence_behind_old_audit_is_unsupported(self):
        item = self.obligations[0]
        value = boundaries(item)
        value["startup"]["business"]["tables"]["sqlite_sequence"][0]["seq"] = 6
        result = self.assess(item, value)
        self.assertEqual(result["business"]["status"], "unknown")
        self.assertFalse(result["business"]["all_business_tables_compared"])

    def test_wrong_source_case_context_order_and_nonjson_inputs_are_rejected(self):
        for change in ("case", "user", "session", "order"):
            value = boundaries(self.memory_case)
            if change == "case": value["source_case"]["eval_id"] = "SYNTHETIC_OTHER"
            elif change == "user": value["turns"][0]["native_user_id"] = "SYNTHETIC_OTHER"
            elif change == "session": value["turns"][1]["native_session_id"] = "SYNTHETIC_OTHER"
            else: value["turns"][0]["samples"][0]["sample_ordinal"] = True
            with self.assertRaises(ValueError): self.assess(self.memory_case, value)
        value = boundaries(self.memory_case); value["nonjson"] = object()
        with self.assertRaises(ValueError): self.assess(self.memory_case, value)

    def test_caller_proof_flags_are_not_inherited_and_inputs_are_not_mutated(self):
        value = boundaries(self.memory_case)
        value.update(native_qualification_established=True, source_closed_proven=True, cross_store_atomicity_proven=True)
        before = deepcopy(value)
        result = self.assess(self.memory_case, value)
        self.assertEqual(value, before)
        for key in ("native_qualification_established", "source_closed_proven", "cross_store_atomicity_proven", "source_authentication_proven",
                    "native_authentication_proven", "causal_tool_execution_order_proven", "benchmark_grade_proven", "full_task_grade_assigned"):
            self.assertIs(result[key], False)

    def test_result_inserted_row_does_not_alias_caller_boundary_evidence(self):
        value = boundaries(self.memory_case)
        before = deepcopy(value)
        result = self.assess(self.memory_case, value)
        result["inserted_memory_row"]["note"] = "SYNTHETIC result-only edit"
        self.assertEqual(value, before)


if __name__ == "__main__":
    unittest.main()
