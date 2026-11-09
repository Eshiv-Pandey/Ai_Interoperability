"""Once-only focused accounting/refusal checks using synthetic quota fixtures.

No authentic quota is supplied, no native guard is installed, and no provider
or application is contacted. All temporary test ledgers remain in the capture.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/interoperability/ap2_hp_gemini_usage_v1.py"
OUTPUT = ROOT / "runs/ap2-gemini-usage-software/core-v1"
NOW = "2026-10-30T16:00:00+00:00"


def digest(body):
    return hashlib.sha256(body).hexdigest()


def main():
    if OUTPUT.exists():
        raise ValueError("Exclusive accounting capture already exists; do not rerun")
    source, driver = SOURCE.read_bytes(), Path(__file__).read_bytes()
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "accounting-core.py").write_bytes(source)
    (OUTPUT / "test-driver.py").write_bytes(driver)
    plan = {"scope": "Focused synthetic accounting/refusal tests only", "source_sha256": digest(source),
            "driver_sha256": digest(driver), "actual_quota_evidence_supplied": False,
            "provider_requests": 0, "original_application_imports": 0, "native_guard_enabled": False}
    (OUTPUT / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    def deny(event, arguments):
        if event.startswith("socket.") or event in {"subprocess.Popen", "os.system", "os.spawn", "os.posix_spawn", "os.exec"}:
            raise RuntimeError("Accounting software capture denies network/process launch")
    sys.addaudithook(deny)
    module = {"__name__": "accounting_core_capture", "__file__": str(SOURCE)}
    exec(compile(source, str(SOURCE), "exec"), module)

    class Checks(unittest.TestCase):
        def setUp(self):
            self.directory = OUTPUT / self._testMethodName
            self.directory.mkdir()
            evidence = self.directory / "synthetic-evidence.txt"
            evidence.write_text("SYNTHETIC TEST INPUT. NOT A PROVIDER QUOTA OR HUMAN REVIEW.\n", encoding="utf-8")
            self.policy = {"schema_version": module["POLICY_SCHEMA"], "model": module["MODEL"],
                "project_alias": "synthetic-project", "run_id": "a" * 32, "configuration_sha256": "b" * 64,
                "observed_at_utc": NOW, "expires_at_utc": "2026-10-30T17:00:00+00:00",
                "billing_mode": "reviewed_free_tier", "allowance_evidence": [{"path": str(evidence), "sha256": digest(evidence.read_bytes())}],
                "remaining_total_tokens": 1000, "remaining_day_requests": 20,
                "requests_per_minute": 100, "input_tokens_per_minute": 10000,
                "initial_minute_requests": 0, "initial_minute_input_tokens": 0,
                "full_input_upper_bound": 100, "maximum_output_upper_bound": 20,
                **{name: True for name in module["VERIFIED"]}}
            self.ledger = self.directory / "ledger.sqlite"

        def initialize(self):
            initialized = module["create_ledger"](self.ledger, self.policy, now=NOW)
            self.policy_digest = initialized["policy_sha256"]
            self.assertFalse(initialized["native_dispatch_enabled"])

        def reserve(self, role="merchant", **values):
            return module["reserve_attempt"](self.ledger, expected_policy_sha256=self.policy_digest,
                role=role, request_sha256="c" * 64, now=values.get("now", NOW))

        def reply(self, attempt, **values):
            return module["record_provider_result"](self.ledger, attempt["attempt_id"],
                expected_policy_sha256=self.policy_digest, **values)

        def test_missing_policy_refuses_before_file_creation(self):
            with self.assertRaises(module["UsageRefused"]):
                module["create_ledger"](self.ledger, {}, now=NOW)
            self.assertFalse(self.ledger.exists())

        def test_unverified_limit_or_billing_refuses(self):
            self.policy["remaining_allowance_verified"] = False
            with self.assertRaises(module["UsageRefused"]):
                module["create_ledger"](self.ledger, self.policy, now=NOW)
            self.assertFalse(self.ledger.exists())

        def test_boolean_limit_refuses(self):
            self.policy["remaining_total_tokens"] = True
            with self.assertRaises(module["UsageRefused"]):
                module["create_ledger"](self.ledger, self.policy, now=NOW)

        def test_locked_twenty_percent_is_not_available(self):
            self.policy["remaining_total_tokens"] = 250
            self.initialize()
            self.assertEqual(self.reserve()["reserved_total_tokens"], 120)
            with self.assertRaises(module["UsageRefused"]):
                self.reserve()

        def test_request_slots_never_refund(self):
            self.policy["remaining_day_requests"] = 5
            self.initialize()
            for _ in range(4):
                self.reply(self.reserve(), usage_metadata={"totalTokenCount": 0}, http_status=200)
            with self.assertRaises(module["UsageRefused"]):
                self.reserve()

        def test_existing_minute_usage_blocks_attempt(self):
            self.policy["initial_minute_input_tokens"] = 7950
            self.initialize()
            with self.assertRaises(module["UsageRefused"]):
                self.reserve()

        def test_unknown_usage_keeps_full_bound(self):
            self.initialize()
            result = self.reply(self.reserve(), usage_metadata=None, http_status=None)
            self.assertEqual(result["charged_total_tokens"], 120)
            self.assertFalse(result["usage_total_observed"])
            self.assertTrue(result["future_attempts_halted"])
            self.assertIn("usage_metadata_absent_or_malformed", result["usage_validation_reasons"])
            with self.assertRaises(module["UsageRefused"]):
                self.reserve()

        def test_provider_total_is_not_added_twice(self):
            self.initialize()
            result = self.reply(self.reserve(), usage_metadata={"promptTokenCount": 45,
                "candidatesTokenCount": 10, "thoughtsTokenCount": 5,
                "cachedContentTokenCount": 30, "totalTokenCount": 60}, http_status=200)
            self.assertEqual(result["charged_total_tokens"], 60)
            self.assertEqual(result["usage_validation_reasons"], [])
            self.assertFalse(result["future_attempts_halted"])

        def test_contradictory_total_cannot_release_bound(self):
            self.initialize()
            result = self.reply(self.reserve(), usage_metadata={"promptTokenCount": 45,
                "candidatesTokenCount": 10, "totalTokenCount": 0}, http_status=200)
            self.assertEqual(result["charged_total_tokens"], 120)
            self.assertEqual(result["reported_total_tokens"], 0)
            self.assertFalse(result["usage_metadata_consistent"])
            self.assertFalse(result["usage_total_observed"])
            self.assertIn("primary_components_exceed_reported_total", result["usage_validation_reasons"])
            self.assertTrue(result["future_attempts_halted"])
            with self.assertRaises(module["UsageRefused"]):
                self.reserve()

        def test_contradictory_overrun_keeps_worst_bound_and_halts(self):
            self.initialize()
            result = self.reply(self.reserve(), usage_metadata={"promptTokenCount": 101,
                "candidatesTokenCount": 40, "totalTokenCount": 130}, http_status=200)
            self.assertEqual(result["charged_total_tokens"], 141)
            self.assertEqual(result["reported_total_tokens"], 130)
            self.assertFalse(result["usage_metadata_consistent"])
            self.assertTrue(result["token_bound_exceeded"])
            with self.assertRaises(module["UsageRefused"]):
                self.reserve()

        def test_malformed_count_cannot_release_bound_and_halts(self):
            self.initialize()
            result = self.reply(self.reserve(), usage_metadata={"totalTokenCount": True}, http_status=200)
            self.assertEqual(result["charged_total_tokens"], 120)
            self.assertFalse(result["usage_total_observed"])
            self.assertIn("malformed_count:totalTokenCount", result["usage_validation_reasons"])
            with self.assertRaises(module["UsageRefused"]):
                self.reserve()

        def test_cached_count_exceeding_prompt_is_unknown(self):
            self.initialize()
            result = self.reply(self.reserve(), usage_metadata={"promptTokenCount": 45,
                "cachedContentTokenCount": 46, "totalTokenCount": 60}, http_status=200)
            self.assertEqual(result["charged_total_tokens"], 120)
            self.assertFalse(result["usage_metadata_consistent"])
            self.assertTrue(result["future_attempts_halted"])
            self.assertIn("cached_count_exceeds_prompt", result["usage_validation_reasons"])

        def test_cached_subset_overrun_retains_larger_input_lower_bound(self):
            self.initialize()
            result = self.reply(self.reserve(), usage_metadata={"promptTokenCount": 45,
                "cachedContentTokenCount": 150, "candidatesTokenCount": 10,
                "totalTokenCount": 60}, http_status=200)
            self.assertEqual(result["charged_total_tokens"], 160)
            self.assertEqual(result["usage_counts"]["cachedContentTokenCount"], 150)
            self.assertTrue(result["token_bound_exceeded"])
            self.assertIn("cached_count_exceeds_prompt", result["usage_validation_reasons"])
            with self.assertRaises(module["UsageRefused"]):
                self.reserve()

        def test_cached_without_prompt_cannot_undercount_known_input(self):
            self.initialize()
            result = self.reply(self.reserve(), usage_metadata={"cachedContentTokenCount": 100,
                "totalTokenCount": 60}, http_status=200)
            self.assertEqual(result["charged_total_tokens"], 120)
            self.assertFalse(result["usage_metadata_consistent"])
            self.assertIn("cached_input_lower_bound_exceeds_reported_total", result["usage_validation_reasons"])
            with self.assertRaises(module["UsageRefused"]):
                self.reserve()

        def test_error_response_cannot_release_token_bound(self):
            self.initialize()
            result = self.reply(self.reserve(), usage_metadata={"totalTokenCount": 0}, http_status=503)
            self.assertEqual(result["charged_total_tokens"], 120)
            with self.assertRaises(module["UsageRefused"]):
                self.reserve()

        def test_reported_overrun_halts_future_attempt(self):
            self.initialize()
            result = self.reply(self.reserve(), usage_metadata={"totalTokenCount": 121}, http_status=200)
            self.assertTrue(result["token_bound_exceeded"])
            with self.assertRaises(module["UsageRefused"]):
                self.reserve()

        def test_rate_failure_halts_background_retry(self):
            self.initialize()
            self.reply(self.reserve(), usage_metadata=None, http_status=429)
            with self.assertRaises(module["UsageRefused"]):
                self.reserve()

        def test_two_services_cannot_double_book_last_bound(self):
            self.policy["remaining_total_tokens"] = 250
            self.initialize()
            def attempt(role):
                try:
                    self.reserve(role)
                    return "reserved"
                except module["UsageRefused"]:
                    return "refused"
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(attempt, ["merchant", "processor"]))
            self.assertEqual(sorted(results), ["refused", "reserved"])

        def test_mutated_policy_cannot_match_bound_digest(self):
            self.initialize()
            changed = deepcopy(self.policy)
            changed["remaining_total_tokens"] = 2000
            body = module["encoded"](changed)
            with sqlite3.connect(self.ledger) as db:
                db.execute("UPDATE policy SET body=?,digest=?", (body.decode(), digest(body)))
            with self.assertRaises(module["UsageRefused"]):
                self.reserve()

        def test_expiry_does_not_reset_or_replenish(self):
            self.initialize()
            with self.assertRaises(module["UsageRefused"]):
                self.reserve(now="2026-10-31T16:00:00+00:00")

        def test_refusal_hook_cannot_claim_native_contract(self):
            result = module["install_guard"](plan={}, service={}, configuration_sha256="b" * 64)
            self.assertFalse(result["installed"])
            self.assertNotEqual(result["contract"], "enforce_before_every_provider_request")

    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    (OUTPUT / "stdout.txt").write_text(stream.getvalue(), encoding="utf-8")
    receipt = {**plan, "status": "passed" if result.wasSuccessful() else "failed", "tests": result.testsRun,
               "failures": len(result.failures), "errors": len(result.errors), "skips": len(result.skipped),
               "source_unchanged": SOURCE.read_bytes() == source, "driver_unchanged": Path(__file__).read_bytes() == driver,
               "synthetic_quota_fixtures_only": True, "actual_quota_reserved": False}
    (OUTPUT / "result.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
