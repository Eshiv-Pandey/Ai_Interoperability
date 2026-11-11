"""Constructed full-analyzer integration controls; no application/SDK/provider.

All runtime, event, session and archive identities here are fabricated test
fixtures. They cannot supply actual-run, task-success or scientific evidence.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


M = load('_V5_full_analysis_control', 'scripts/analyze_ap2_native_shopper_provider_v5.py')
G = load('_V5_analysis_guard_fixture', 'scripts/ap2_native_shopper_actor_guard_v5.py')
SHOPPER = 'execution/cases/' + M.CASE + '/shopper/'
CASE_ROOT = 'execution/cases/' + M.CASE + '/'
STAMP = '2026-11-12T00:00:00+00:00'


def encoded(value):
    return json.dumps(value, sort_keys=True, allow_nan=False).encode('utf-8')


class ConstructedRead:
    def __init__(self, values):
        self.values = copy.deepcopy(values)
        self.reads = {}
        self.receipt = {'run_id': 0, 'head_sha': 'constructed-not-GitHub',
                        'archive_sha256': 'constructed-not-an-archive', 'archive_bytes': 0}

    @property
    def manifest(self):
        return {key: {} for key in self.values}

    def raw(self, name, optional=False):
        if name not in self.values:
            if optional:
                return None
            raise ValueError('constructed_missing_member:' + name)
        value = self.values[name]
        raw = value if type(value) is bytes else encoded(value)
        self.reads[name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        return raw

    def json(self, name, optional=False):
        raw = self.raw(name, optional=optional)
        return json.loads(raw) if raw is not None else None

    def rows(self, name):
        raw = self.raw(name, optional=True)
        return [json.loads(line) for line in raw.splitlines()] if raw is not None else []


def rows(values):
    return b''.join(encoded(value) + b'\n' for value in values)


def fixture(*, preflight=False):
    facts = {'case_id': M.CASE, 'initial_request': 'Constructed public-only test request.',
             'maximum_budget_USD': 100, 'otp_response': '123'}
    source = b'constructed-original-source-not-an-application'
    owned = b'constructed-owned-source-not-a-real-worker'
    plan = {'schema_version': 'ap2-native-shopper-provider-plan/5', 'allocated_task_count': 1,
            'prepared_at': 'constructed', 'public_human_facts': facts,
            'owned_sources': {'scripts/constructed-guard.py': M.V1.digest(owned)},
            'sources': {'code/samples/python/src/roles/shopping_agent/agent.py':
                        {'sha256': hashlib.sha256(source).hexdigest()}},
            'versions': {}, 'limits': {'upstream_calls_including_smoke': 80,
                    'maximum_total_request_bytes': 200000, 'request_timeout_seconds': 120,
                    'maximum_provider_drain_seconds': 150},
            'actor_network_guard': {'classifier_schema': G.CLASSIFIER_SCHEMA,
                    'separation_schema': G.SEPARATION_SCHEMA, 'denial_schema': G.DIAGNOSTIC_SCHEMA,
                    'maximum_diagnostic_records': G.MAX_DIAGNOSTICS,
                    'maximum_diagnostic_bytes': G.MAX_DIAGNOSTIC_BYTES,
                    'maximum_single_diagnostic_bytes': G.MAX_SINGLE_DIAGNOSTIC_BYTES}}
    usage = {'upstream_allocations': 0, 'terminal_responses': 0, 'known_reported_tokens': 0,
             'successful_responses_missing_or_invalid_usage': 0,
             'failed_responses_missing_or_invalid_usage': 0, 'responses_missing_or_invalid_usage': 0,
             'unclosed_allocation_ids': [], 'allocations_with_unmeasured_usage': 0,
             'fully_measured': True, 'unknown_usage_is_zero': False}
    case = {'case_id': M.CASE, 'status': 'unexecuted' if preflight else 'constructed_returned',
            'process_cleanup': []}
    result = {'schema_version': 'ap2-native-shopper-provider-result/5', 'allocated_task_count': 1,
              'unexecuted_count': int(preflight), 'cases': [case],
              'provider': {'upstream_allocations': 0, 'cumulative_request_bytes': 0,
                           'all_response_usage': usage}}
    values = {'plan/plan.json': plan, 'plan/owned-source/scripts/constructed-guard.py': owned,
              'execution/result.json': result}
    if preflight:
        result['status'] = 'runtime_preflight_failed_before_provider_or_application_calls'
        return ConstructedRead(values), copy.deepcopy(plan)
    runtime = {'required_original_versions': {}, 'distributions': {}, 'files': {},
               'python_version': 'constructed-not-executed'}
    result['portable_runtime_sha256'] = hashlib.sha256(encoded(runtime)).hexdigest()
    values['execution/portable-runtime.json'] = runtime
    drain = {'schema_version': 'ap2-provider-drain/2', 'time': STAMP,
             'admission_closed': True, 'capture_frozen': True,
             'unfinished_allocations_require_unknown_usage': True, 'late_sender_outcomes_retained': False,
             'active_handlers_at_capture_freeze': 0, 'all_handlers_completed': True,
             'maximum_drain_seconds': 150, 'elapsed_drain_seconds': 0,
             'allocated_upstream_calls_at_capture_freeze': 0, 'request_bytes_at_capture_freeze': 0,
             'unclosed_allocation_ids': [], 'allocations_with_unmeasured_usage': 0}
    values['execution/provider-drain.json'] = drain
    result['provider_drain'] = copy.deepcopy(drain)
    result['provider'].update(admission_closed=True, capture_frozen=True, active_handlers=0,
                             request_transport_timeout_seconds=120, request_timeout_is_independent_whole_request_wall_cap=False)
    separation = {'schema_version': G.SEPARATION_SCHEMA,
                  'denials': {'private_reads': 0, 'external_network': 0, 'descendants': 0,
                      'network_diagnostics_logged': 0, 'network_diagnostics_dropped': 0,
                      'diagnostic_write_failures': 0, 'network_diagnostic_bytes': 0},
                  'network_classifier_schema': G.CLASSIFIER_SCHEMA, 'network_diagnostic_schema': G.DIAGNOSTIC_SCHEMA,
                  'network_diagnostic_stream': 'actor-network-denials.jsonl',
                  'network_diagnostic_bounds': {'records': G.MAX_DIAGNOSTICS,
                      'total_bytes': G.MAX_DIAGNOSTIC_BYTES, 'single_record_bytes': G.MAX_SINGLE_DIAGNOSTIC_BYTES},
                  'public_user_replies_use_visible_final_text_only': True,
                  'provider_credential_is_synthetic_downstream_only': True,
                  'scope': 'constructed Python audit fixture'}
    values.update({CASE_ROOT + 'public-human-facts.json': facts,
        SHOPPER + 'ADK-events.jsonl': b'',
        SHOPPER + 'public-conversation.jsonl': rows([{'turn': 0, 'role': 'user', 'text': facts['initial_request']}]),
        SHOPPER + 'public-actor-decisions.jsonl': rows([{'turn': 0, 'reply': None,
            'visible_prompt_sha256': hashlib.sha256(b'').hexdigest(), 'session_or_tool_state_used': False}]),
        SHOPPER + 'original-root-binding.json': {'original_root_source_sha256': hashlib.sha256(source).hexdigest(),
            'root_model': M.V1.MODEL, 'official_ADK_runner': True, 'genai_Client_replaced': False,
            'deterministic_BaseLlm_replacement': False, 'session_id': 'constructed-session'},
        SHOPPER + 'worker-result.json': {'schema_version': 'ap2-native-shopper-provider-worker/3',
            'case_id': M.CASE, 'ADK_event_count': 0, 'whole_task_grade': None,
            'original_remote_http_clients_closed': [True, True]},
        SHOPPER + 'actor-input-separation.json': separation,
        SHOPPER + 'actor-network-denials.jsonl': b'',
        SHOPPER + 'turn-00-session.json': {'id': 'constructed-session', 'events': [], 'state': {}}})
    return ConstructedRead(values), copy.deepcopy(plan)


def add_denial(read):
    values = (object(), ('127.0.0.1', 8004))
    decision = G.classify_network_event('socket.connect', values, {8001, 8002, 8003})
    diagnostic = G.safe_network_diagnostic('socket.connect', values, decision)
    diagnostic['time'] = STAMP
    raw = rows([diagnostic])
    read.values[SHOPPER + 'actor-network-denials.jsonl'] = raw
    read.values[SHOPPER + 'actor-input-separation.json']['denials'].update(
        external_network=1, network_diagnostics_logged=1, network_diagnostic_bytes=len(raw))
    return diagnostic


class FullAnalyzerActorSeparationControls(unittest.TestCase):
    def test_complete_constructed_empty_stream_has_no_integrity_question(self):
        read, plan = fixture()
        result = M.analyze(read, plan)
        self.assertEqual(result['consistency_questions'], [])
        self.assertEqual(result['actual_provider_requests_by_analyzer'], 0)
        self.assertIsNone(result['whole_task_grade'])

    def test_real_shaped_denial_record_and_exact_raw_byte_counter_join(self):
        read, plan = fixture()
        add_denial(read)
        result = M.analyze(read, plan)
        self.assertEqual(result['consistency_questions'], [])
        self.assertIn(SHOPPER + 'actor-network-denials.jsonl', read.reads)

    def test_separation_schema_and_public_only_flags_are_checked(self):
        changes = [('schema_version', 'ap2-native-shopper-actor-separation/4'),
                   ('public_user_replies_use_visible_final_text_only', False),
                   ('provider_credential_is_synthetic_downstream_only', False)]
        for key, value in changes:
            with self.subTest(key=key):
                read, plan = fixture()
                read.values[SHOPPER + 'actor-input-separation.json'][key] = value
                self.assertIn('actor_separation_schema_or_flags_differs', M.analyze(read, plan)['consistency_questions'])

    def test_declared_diagnostic_file_and_bounds_must_match_frozen_plan(self):
        for mutation in ('missing', 'unsafe-name', 'record-bound', 'byte-bound', 'record-byte-bound'):
            with self.subTest(mutation=mutation):
                read, plan = fixture()
                separation = read.values[SHOPPER + 'actor-input-separation.json']
                if mutation == 'missing':
                    del read.values[SHOPPER + 'actor-network-denials.jsonl']
                elif mutation == 'unsafe-name':
                    separation['network_diagnostic_stream'] = '../evaluator.json'
                else:
                    key = {'record-bound': 'records', 'byte-bound': 'total_bytes', 'record-byte-bound': 'single_record_bytes'}[mutation]
                    separation['network_diagnostic_bounds'][key] += 1
                self.assertIn('actor_network_diagnostic_membership_or_bounds_differs', M.analyze(read, plan)['consistency_questions'])

    def test_counter_types_counts_and_raw_bytes_are_not_trusted(self):
        for key, value in [('external_network', 2), ('network_diagnostics_logged', 0),
                           ('network_diagnostics_logged', True), ('network_diagnostic_bytes', 0),
                           ('diagnostic_write_failures', -1)]:
            with self.subTest(key=key, value=value):
                read, plan = fixture()
                add_denial(read)
                read.values[SHOPPER + 'actor-input-separation.json']['denials'][key] = value
                self.assertIn('actor_network_diagnostic_counter_or_record_differs', M.analyze(read, plan)['consistency_questions'])

    def test_allowed_record_wrong_schema_or_wrong_event_is_not_denial_evidence(self):
        for area, key, value in [('record', 'schema_version', 'wrong'), ('record', 'event', 'socket.send'),
                                 ('classification', 'allowed', True), ('classification', 'schema_version', 'wrong')]:
            with self.subTest(area=area, key=key):
                read, plan = fixture()
                diagnostic = add_denial(read)
                target = diagnostic if area == 'record' else diagnostic['classification']
                target[key] = value
                raw = rows([diagnostic])
                read.values[SHOPPER + 'actor-network-denials.jsonl'] = raw
                read.values[SHOPPER + 'actor-input-separation.json']['denials']['network_diagnostic_bytes'] = len(raw)
                self.assertIn('actor_network_diagnostic_counter_or_record_differs', M.analyze(read, plan)['consistency_questions'])

    def test_legitimate_dropped_diagnostics_remain_explicit_missing_coverage(self):
        read, plan = fixture()
        add_denial(read)
        read.values[SHOPPER + 'actor-input-separation.json']['denials'].update(external_network=3, network_diagnostics_dropped=2)
        result = M.analyze(read, plan)
        self.assertEqual(result['consistency_questions'], [])
        self.assertEqual(result['actor_separation']['denials']['external_network'], 3)
        self.assertEqual(result['actor_separation']['denials']['network_diagnostics_dropped'], 2)
        self.assertFalse(result['actor_network_diagnostics']['all_denied_network_arguments_retained'])
        self.assertEqual(result['actor_network_diagnostics']['unrecorded_denial_count'], 2)
        self.assertFalse(result['actor_network_diagnostics']['historical_V4_denial_cause_inferred'])


class FullAnalyzerPreflightAndSessionControls(unittest.TestCase):
    def test_clean_runtime_preflight_failure_has_no_application_observation(self):
        read, plan = fixture(preflight=True)
        self.assertEqual(M.analyze(read, plan)['consistency_questions'], [])

    def test_preflight_failure_rejects_even_zero_event_application_receipts(self):
        for kind in ('facts', 'worker', 'separation', 'conversation', 'decisions', 'snapshot'):
            with self.subTest(kind=kind):
                read, plan = fixture(preflight=True)
                executed, _ = fixture()
                member = {'facts': CASE_ROOT + 'public-human-facts.json',
                          'worker': SHOPPER + 'worker-result.json',
                          'separation': SHOPPER + 'actor-input-separation.json',
                          'conversation': SHOPPER + 'public-conversation.jsonl',
                          'decisions': SHOPPER + 'public-actor-decisions.jsonl',
                          'snapshot': SHOPPER + 'turn-00-session.json'}[kind]
                read.values[member] = copy.deepcopy(executed.values[member])
                self.assertIn('runtime_preflight_failure_has_application_observations', M.analyze(read, plan)['consistency_questions'])

    def test_worker_schema_case_and_event_count_are_bound(self):
        for key, value in [('schema_version', 'ap2-native-shopper-provider-worker/2'),
                           ('case_id', 'prior-case'), ('ADK_event_count', 1), ('ADK_event_count', False)]:
            with self.subTest(key=key, value=value):
                read, plan = fixture()
                read.values[SHOPPER + 'worker-result.json'][key] = value
                self.assertIn('worker_schema_case_or_ADK_count_differs', M.analyze(read, plan)['consistency_questions'])

    def test_snapshot_session_identity_is_bound_even_when_no_events(self):
        read, plan = fixture()
        read.values[SHOPPER + 'turn-00-session.json']['id'] = 'other-session'
        self.assertIn('snapshot_session_identity_differs', M.analyze(read, plan)['consistency_questions'])

    def test_snapshot_extra_or_type_changed_events_are_detected(self):
        for snapshot_event in ({'id': 'constructed-event-0', 'author': 'shopper', 'customMetadata': {'numeric': 0}},
                               {'id': 'constructed-event-0', 'author': 'shopper', 'customMetadata': {'numeric': False}}):
            with self.subTest(snapshot_event=snapshot_event):
                read, plan = fixture()
                raw_event = {'id': 'constructed-event-0', 'author': 'shopper', 'customMetadata': {'numeric': 0}}
                read.values[SHOPPER + 'ADK-events.jsonl'] = rows([{'turn': 0, 'event': raw_event}])
                read.values[SHOPPER + 'worker-result.json']['ADK_event_count'] = 1
                read.values[SHOPPER + 'turn-00-session.json']['events'] = [snapshot_event, {'author': 'shopper'}] if encoded(snapshot_event) == encoded(raw_event) else [snapshot_event]
                self.assertIn('snapshot_and_raw_ADK_events_differ', M.analyze(read, plan)['consistency_questions'])

    def test_remote_client_close_flags_are_real_booleans(self):
        for flags in ([True, False], [1, 1], ['true', 'true'], [True]):
            with self.subTest(flags=flags):
                read, plan = fixture()
                read.values[SHOPPER + 'worker-result.json']['original_remote_http_clients_closed'] = flags
                self.assertIn('worker_remote_clients_not_closed', M.analyze(read, plan)['consistency_questions'])

    def test_actual_runner_preparation_identity_dicts_are_accepted_by_analyzer(self):
        runner = load('_V5_prepare_analysis_shape', 'scripts/run_ap2_native_shopper_provider_v5.py')
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary) / 'plan'
            runner.prepare(base)
            expected = json.loads((base / 'plan.json').read_bytes())
            values = {'plan/plan.json': expected}
            for name, identity in expected['owned_sources'].items():
                self.assertIs(type(identity), dict)
                self.assertEqual(set(identity), {'bytes', 'sha256'})
                values['plan/owned-source/' + name] = (base / 'owned-source' / name).read_bytes()
            self.assertEqual(M.check_plan(ConstructedRead(values), expected), expected)

    def test_source_fact_type_drift_stops_before_analysis(self):
        read, plan = fixture()
        read.values['plan/plan.json']['public_human_facts']['maximum_budget_USD'] = '100'
        with self.assertRaisesRegex(ValueError, 'reviewed_frozen_plan_differs'):
            M.analyze(read, plan)

    def test_no_official_application_or_sdk_imported(self):
        self.assertFalse(any(name == 'roles' or name.startswith(('roles.', 'google.adk', 'google.genai')) for name in sys.modules))


if __name__ == '__main__':
    unittest.main()
