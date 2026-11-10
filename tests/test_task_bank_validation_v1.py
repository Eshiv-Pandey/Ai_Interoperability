"""Adversarial controls for task-bank source and evaluator isolation boundaries."""
import copy
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location(
    "task_bank_validator", Path(__file__).resolve().parents[1] / "scripts/validate_task_banks_v1.py")
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)
SOURCE = b"first line\nsecond line\n"


def fixture():
    meta = {"id": "case-1", "split": "development", "template_family": "family-1",
            "distinct_obligation": "Read the original current record."}
    claim = {"claim": "The original returns the record.", "source_refs": ["original"],
             "status": "source_supported"}
    common = {"schema_version": "source-task-bank/1", "domain": "fixture",
              "source_pin": {}, "qualification": {"human_review": "pending",
              "runtime_execution": "not_executed", "gold_validation": "pending"}}
    application = {**copy.deepcopy(common), "records": [{**meta, "public": {"task": "Read it."}}]}
    gold = {**meta, **{key: [copy.deepcopy(claim)] for key in validator.GOLD_KEYS
                       - {"source_refs", "review_status"}},
            "source_refs": {"original": {"path": "original.py", "sha256": validator.digest(SOURCE),
                                          "lines": [1, 2]}}, "review_status": "not_reviewed"}
    return application, {**copy.deepcopy(common), "records": [gold]}


class BankBoundaryTests(unittest.TestCase):
    def validate(self, pair):
        return validator.validate_pair(*pair, lambda path: SOURCE)

    def test_incomplete_bank_stays_unqualified(self):
        result = self.validate(fixture())
        self.assertFalse(result["allocation_complete"])
        self.assertFalse(result["gold_semantics_validated"])
        self.assertFalse(result["runtime_execution_performed"])
        self.assertEqual(result["research_checkpoint_credit_added"], 0)

    def test_nested_gold_leak_rejected(self):
        pair = fixture()
        pair[0]["records"][0]["public"]["fixture"] = {"near_misses": ["private"]}
        with self.assertRaisesRegex(ValueError, "leaked"):
            self.validate(pair)

    def test_wrong_source_hash_rejected(self):
        pair = fixture()
        pair[1]["records"][0]["source_refs"]["original"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.validate(pair)

    def test_invalid_source_bounds_rejected(self):
        for bounds in ([0, 1], [2, 3], [True, 2], [2, 1]):
            pair = fixture()
            pair[1]["records"][0]["source_refs"]["original"]["lines"] = bounds
            with self.subTest(bounds=bounds), self.assertRaisesRegex(ValueError, "range"):
                self.validate(pair)

    def test_uncited_or_unbound_supported_claim_rejected(self):
        for refs in ([], ["different-source"]):
            pair = fixture()
            pair[1]["records"][0]["expected_facts"][0]["source_refs"] = refs
            with self.subTest(refs=refs), self.assertRaises(ValueError):
                self.validate(pair)

    def test_wrong_join_and_duplicate_template_rejected(self):
        pair = fixture()
        pair[1]["records"][0]["distinct_obligation"] = "A different task."
        with self.assertRaisesRegex(ValueError, "metadata mismatch"):
            self.validate(pair)
        pair = fixture()
        for value in pair:
            value["records"].append(copy.deepcopy(value["records"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.validate(pair)

    def test_unknown_split_and_overallocation_rejected(self):
        pair = fixture()
        for value in pair:
            value["records"][0]["split"] = "unregistered"
        with self.assertRaisesRegex(ValueError, "Unknown split"):
            self.validate(pair)
        pair = fixture()
        for value in pair:
            original = copy.deepcopy(value["records"][0])
            value["records"] = []
            for index in range(7):
                row = copy.deepcopy(original)
                for key in ("id", "template_family", "distinct_obligation"):
                    row[key] += str(index)
                value["records"].append(row)
        with self.assertRaisesRegex(ValueError, "over allocation"):
            self.validate(pair)


if __name__ == "__main__":
    unittest.main()
