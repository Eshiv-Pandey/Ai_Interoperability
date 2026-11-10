"""Constructed v5 controls; none of these fixtures is original application gold."""
from __future__ import annotations

import ast
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from interoperability import ap2_application_profile_v5 as profile
from interoperability import refinement_oracle


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


prior_controls = module("_ap2_v5_constructed_prior_fixture", "tests/test_ap2_reference_development_v4.py")
orchestrator = module("_ap2_v5_matrix_orchestrator", "scripts/run_ap2_application_matrix_v5.py")
evaluator = module("_ap2_v5_matrix_evaluator", "scripts/evaluate_ap2_application_matrix_v5.py")
NOW = 1_900_000_000


class ProfileTests(unittest.TestCase):
    def prepare(self, mutation=None, associated=True, validity=15):
        task, caller, message, _ = prior_controls.fixture()
        if mutation:
            mutation(message)
        value = profile.prepare_profile(task, caller, message, association_completed=associated,
                                        now=NOW, valid_for_seconds=validity)
        return task, caller, message, value

    def test_positive_exact_received_request_and_independent_certificate(self):
        task, caller, message, prepared = self.prepare()
        before = deepcopy(prepared)
        receipt = profile.evaluate_prepared(prepared, NOW)
        self.assertTrue(receipt["dispatch_permitted"])
        self.assertTrue(refinement_oracle.check_certificate(prepared["profile"], receipt["solver_result"], NOW))
        self.assertEqual(receipt["solver_result"]["certificate"]["steps"][0]["request"]["message"], profile.wire_message(message))
        self.assertEqual(prepared, before)
        self.assertFalse(prepared["profile"]["coverage"]["complete"])
        self.assertFalse(receipt["actual_task_completion_established_by_certificate"])

    def test_wrong_authority_context_otp_or_mandate_is_unknown_not_route_negative(self):
        mutations = [lambda value: value.update(taskId="constructed_other_actual_task"),
                     lambda value: value.update(contextId="constructed_other_actual_context"),
                     lambda value: value["parts"][3]["data"].update(challenge_response="000"),
                     lambda value: value["parts"][1]["data"].update({profile.PAYMENT: "constructed_checkout_token"}),
                     lambda value: value["parts"].pop(1)]
        for change in mutations:
            with self.subTest(change=change):
                task, caller, message, prepared = self.prepare(change)
                receipt = profile.evaluate_prepared(prepared, NOW)
                self.assertEqual(receipt["decision"], "unknown")
                self.assertFalse(receipt["dispatch_permitted"])
                self.assertFalse(receipt["whole_route_non_support_inference_allowed"])
                self.assertEqual(refinement_oracle.evaluate(prepared["profile"], NOW)["decision"], "unknown")

    def test_missing_actual_credential_association_is_unknown(self):
        receipt = profile.evaluate_prepared(self.prepare(associated=False)[3], NOW)
        self.assertEqual(receipt["decision"], "unknown")
        self.assertFalse(receipt["dispatch_permitted"])

    def test_real_dispatch_clock_beyond_declared_interval_is_refused(self):
        prepared = self.prepare(validity=1)[3]
        receipt = profile.evaluate_prepared(prepared, NOW)
        self.assertTrue(receipt["dispatch_permitted"])
        with self.assertRaisesRegex(ValueError, "fresh_independent_certificate"):
            profile.verify_supported(prepared, receipt["solver_result"], NOW + 2)

    def test_frozen_original_source_and_v4_helpers_preserved(self):
        self.assertEqual(profile.frozen.SOURCE_PIN, "e1ea56db72a6385bce3e5c1112b3a56ce60acb43")
        self.assertEqual(profile.frozen.EDGE, "original_merchant_otp_continuation")
        self.assertEqual(profile.frozen.VALID_FOR_SECONDS, 15)


class DenominatorAndSeparationTests(unittest.TestCase):
    def test_public_fixed_case_major_denominator(self):
        public = json.loads((ROOT / "benchmark/ap2-application-development-v5/application.json").read_bytes())
        cells = orchestrator.public_cells(public)
        self.assertEqual(len(cells), 65)
        self.assertEqual(len({row["id"] for row in cells}), 65)
        self.assertEqual([row["arm_id"] for row in cells[:5]], ["reference", "conventional", "recovery", "shared", "recovery_shared"])
        self.assertEqual(public["source_bank_candidates"], 34)

    def test_missing_cells_remain_in_independent_denominator(self):
        public_raw = (ROOT / "benchmark/ap2-application-development-v5/application.json").read_bytes()
        public = json.loads(public_raw)
        cells = orchestrator.public_cells(public)
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            (base / "public-manifest.json").write_bytes(public_raw)
            (base / "allocation-manifest.json").write_text(json.dumps({"declared_cells": 65, "public_manifest": evaluator.digest(public_raw), "cells": cells}))
            retained = [dict(row, allocation_status="not_executed_matrix_budget_exhausted", returncode=None) for row in cells]
            (base / "execution-results.json").write_text(json.dumps({"declared_cells": 65, "cells": retained}))
            result = evaluator.evaluate(base, False)
            self.assertEqual(result["declared_cells"], 65)
            self.assertEqual(result["totals"]["missing_cells"], 65)
            self.assertEqual(result["totals"]["verified_purchases"], 0)

    def test_actor_has_no_private_evaluator_or_gold_reads(self):
        for path in ("scripts/ap2_reference_development_v5.py", "scripts/run_ap2_application_matrix_v5.py",
                     "src/interoperability/ap2_application_coordinator_v5.py", "src/interoperability/ap2_application_profile_v5.py"):
            tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
            strings = [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)]
            self.assertFalse(any(value.endswith("evaluator.json") or "evaluate_ap2_application_matrix_v5" in value for value in strings), path)
        tree = ast.parse((ROOT / "scripts/evaluate_ap2_application_matrix_v5.py").read_text(encoding="utf-8"))
        imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        self.assertFalse(any("ap2_application" in name or "ap2_reference_development" in name for name in imports))

    def test_decoder_rejects_byte_hash_and_duplicate_key_tampering(self):
        from interoperability.ap2_hp_durable_observer_v1 import encode_value
        tagged = encode_value({"raw": b"real recorded bytes", "state": "input-required"})
        self.assertEqual(evaluator.decode_tag(tagged), {"raw": b"real recorded bytes", "state": "input-required"})
        corrupted = deepcopy(tagged)
        corrupted["entries"][0][1]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "identity_mismatch"):
            evaluator.decode_tag(corrupted)
        duplicate = deepcopy(tagged)
        duplicate["entries"].append(deepcopy(duplicate["entries"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate_decoded"):
            evaluator.decode_tag(duplicate)


if __name__ == "__main__":
    unittest.main()
