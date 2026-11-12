"""Independent reviewer accounting/sanitization controls; no runtime execution."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('_V5_lifecycle_reader_controls', ROOT / 'scripts/review_ap2_native_shopper_v5_lifecycle_v1.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def fixture():
    plan = {'maximum_diagnostic_records': 160, 'maximum_diagnostic_bytes': 262144,
            'maximum_single_diagnostic_bytes': 4096}
    record = {'schema_version': M.DENIAL_SCHEMA, 'time': '2026-11-12T00:00:00+00:00',
              'event': 'socket.connect', 'classification': {'schema_version': M.CLASSIFIER_SCHEMA,
                  'allowed': False, 'normalized_host': '127.0.0.1', 'normalized_port': 8004,
                  'reason': 'port_not_declared', 'address_length': 2},
              'sanitized_arguments': {'audit_values_type': 'tuple', 'audit_values_count': 2,
                  'address_type': 'tuple', 'address_length': 2,
                  'host': {'type': 'bytes', 'length': 9, 'safe_value': '127.0.0.1'},
                  'port': {'type': 'int', 'safe_value': 8004}},
              'socket_object_or_send_payload_retained': False,
              'external_host_or_unrestricted_argument_retained': False}
    raw = (json.dumps(record, sort_keys=True) + '\n').encode('utf-8')
    separation = {'schema_version': M.SEPARATION_SCHEMA, 'network_classifier_schema': M.CLASSIFIER_SCHEMA,
                  'network_diagnostic_schema': M.DENIAL_SCHEMA, 'network_diagnostic_stream': 'actor-network-denials.jsonl',
                  'network_diagnostic_bounds': {'records': 160, 'total_bytes': 262144, 'single_record_bytes': 4096},
                  'public_user_replies_use_visible_final_text_only': True,
                  'provider_credential_is_synthetic_downstream_only': True,
                  'denials': {'private_reads': 0, 'external_network': 1, 'descendants': 0,
                      'diagnostic_write_failures': 0, 'network_diagnostics_logged': 1,
                      'network_diagnostics_dropped': 0, 'network_diagnostic_bytes': len(raw)}}
    return plan, separation, record, raw


class UsageAccountingControls(unittest.TestCase):
    def test_missing_failed_usage_is_unknown_and_explicit_failed_zero_is_known(self):
        self.assertIsNone(M.usage_observation({'error': {'message': 'high demand'}}, 503))
        self.assertEqual(M.usage_observation({'usageMetadata': {'totalTokenCount': 0}}, 503), 0)

    def test_missing_or_zero_successful_usage_does_not_become_measured_zero(self):
        self.assertIsNone(M.usage_observation({}, 200))
        self.assertIsNone(M.usage_observation({'usageMetadata': {'totalTokenCount': 0}}, 200))

    def test_reported_token_integer_excludes_boolean_float_and_string(self):
        for value in (True, False, 4.0, '4', -1):
            with self.subTest(value=value):
                self.assertIsNone(M.usage_observation({'usageMetadata': {'totalTokenCount': value}}, 200))
        self.assertEqual(M.usage_observation({'usageMetadata': {'totalTokenCount': 4}}, 200), 4)


class GuardEvidenceControls(unittest.TestCase):
    def test_exact_safe_denial_record_binds_raw_bytes(self):
        plan, separation, record, raw = fixture()
        result = M.guard_review(separation, raw, plan)
        self.assertEqual(result['diagnostic_records'], [record])
        self.assertEqual(result['diagnostic_bytes'], len(raw))
        self.assertTrue(result['diagnostic_coverage_complete'])
        self.assertFalse(result['historical_V4_rejected_argument_cause_inferred'])

    def test_missing_diagnostics_remain_missing_coverage(self):
        plan, separation, _, raw = fixture()
        separation['denials'].update(external_network=4, network_diagnostics_dropped=2, diagnostic_write_failures=1)
        self.assertFalse(M.guard_review(separation, raw, plan)['diagnostic_coverage_complete'])

    def test_mismatched_raw_counts_bytes_and_boolean_counter_are_rejected(self):
        for key, value in [('network_diagnostic_bytes', 0), ('network_diagnostics_logged', 0),
                           ('external_network', 2), ('network_diagnostics_logged', True)]:
            with self.subTest(key=key, value=value):
                plan, separation, _, raw = fixture()
                separation['denials'][key] = value
                with self.assertRaises(ValueError):
                    M.guard_review(separation, raw, plan)

    def test_unrestricted_external_scalar_is_rejected_even_with_redaction_claim(self):
        plan, separation, record, _ = fixture()
        record['sanitized_arguments']['host']['safe_value'] = 'secret.example.invalid'
        raw = (json.dumps(record) + '\n').encode('utf-8')
        separation['denials']['network_diagnostic_bytes'] = len(raw)
        with self.assertRaisesRegex(ValueError, 'unrestricted_host_in_diagnostic'):
            M.guard_review(separation, raw, plan)

    def test_additional_payload_field_is_rejected(self):
        plan, separation, record, _ = fixture()
        record['sanitized_arguments']['payload'] = 'untrusted packet data'
        raw = (json.dumps(record) + '\n').encode('utf-8')
        separation['denials']['network_diagnostic_bytes'] = len(raw)
        with self.assertRaisesRegex(ValueError, 'actor_diagnostic_unsafe_argument_fields'):
            M.guard_review(separation, raw, plan)

    def test_no_original_sdk_or_application_imported(self):
        self.assertFalse(any(name == 'roles' or name.startswith(('roles.', 'google.adk', 'google.genai')) for name in sys.modules))


if __name__ == '__main__':
    unittest.main()
