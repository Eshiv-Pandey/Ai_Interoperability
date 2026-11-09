"""Verifier tests over actual new-client journals from a local stdio double.

The double has no network, service, database or model access. These are software
tests, not native protocol results or an application-effect demonstration.
"""
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
from test_pending_admission import authored_snapshot

spec = importlib.util.spec_from_file_location('admitted_check', ROOT / 'scripts/check_agentops_admitted_client_v1.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def load(path):
    return json.loads(path.read_bytes())


def events(path):
    return [json.loads(line) for line in path.read_bytes().splitlines()]


def save_events(path, records):
    path.write_text(''.join(json.dumps(row) + '\n' for row in records), encoding='utf-8')


class AdmittedClientVerifier(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='admitted-client-verifier-')
        cls.root = Path(cls.temporary.name)
        node = shutil.which('node')
        if not node:
            raise RuntimeError('Node is required for the actual-client verifier software test')
        cls.bundles = {}
        for mode in ('supported', 'unknown', 'missing_call', 'changed_state'):
            fixture = authored_snapshot()
            fixtures = {name: row['body'] for name, row in fixture['observations'].items()}
            fixtures['tools']['tools'].extend([{'name': 'a2a_send_message'}, {'name': 'a2a_get_task'}])
            worker = r'''
const readline = require('node:readline');
const fixtures = FIXTURES;
const mode = MODE;
let completed = false, rawReads = 0;
readline.createInterface({input:process.stdin}).on('line', line => {
 const request = JSON.parse(line); if (!Object.hasOwn(request, 'id')) return;
 const copied = name => JSON.parse(JSON.stringify(fixtures[name]));
 let result;
 if (request.method === 'initialize') result = {protocolVersion:'2025-11-25',capabilities:{},serverInfo:{name:'local-stdio-double',version:'1'}};
 else if (request.method === 'tools/list') result = copied('tools');
 else {
  const name = request.params.name, args = request.params.arguments;
  if (name === 'a2a_discover_agent') result = copied('discovery');
  else if (name === 'a2a_send_message') result = copied('initial');
  else if (name === 'a2a_get_task') {
   result = copied('pending'); if (completed) result.structuredContent.state = 'completed';
  } else if (name === 'a2a_request' && args.method === 'GetTask') {
   result = copied('raw'); result.structuredContent.id = 'raw-' + (++rawReads);
   if (mode === 'missing_call') result.structuredContent.result.status.message.parts = [];
   if (mode === 'changed_state' && rawReads > 1) result.structuredContent.result.status.state = 'TASK_STATE_WORKING';
  } else if (name === 'a2a_request' && args.method === 'SendMessage') {
   completed = true; result = {content:[{type:'text',text:JSON.stringify({acknowledged:true})}]};
  } else throw new Error('Unexpected mock request');
 }
 process.stdout.write(JSON.stringify({jsonrpc:'2.0',id:request.id,result})+'\n');
});
'''.replace('FIXTURES', json.dumps(fixtures)).replace('MODE', json.dumps(mode))
            output = cls.root / mode
            config = {'schema_version': 'agentops-admitted-client-config/1', 'arm': 'B7',
                      'output_dir': str(output), 'agent_base_url': fixture['route']['agent_base_url'],
                      'agent_alias': 'agentops', 'rationale': fixture['rationale'],
                      'bridge': {'command': str(Path(node).resolve()), 'args': ['-e', worker],
                                 'cwd': str(cls.root), 'env': {}},
                      'limits': {'request_timeout_ms': 10000, 'poll_interval_ms': 1, 'poll_attempts': 2,
                                 'total_timeout_ms': 30000, 'max_response_bytes': 1048576},
                      'admission': {'python': sys.executable, 'budget': 100000, 'timeout_ms': 10000,
                                    'deployment': fixture['deployment']}}
            if mode == 'unknown':
                config['admission']['deployment']['header_mode'] = 'unknown'
            config_path = cls.root / (mode + '-config.json')
            write_json(config_path, config)
            execution = subprocess.run([node, str(ROOT / 'scripts/agentops_admission_client_v1.mjs'),
                                        '--config', str(config_path)], cwd=ROOT, capture_output=True, timeout=40)
            if execution.returncode:
                raise AssertionError((mode, execution.returncode, execution.stdout.decode(), execution.stderr.decode()))
            cls.bundles[mode] = output

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def copy_bundle(self, mode='supported'):
        target = self.root / ('copy-' + self._testMethodName)
        shutil.copytree(self.bundles[mode], target)
        return target

    def assert_rejected(self, bundle, contains=None):
        report = checker.check_client(bundle)
        self.assertFalse(report['client_scope_verified'], report)
        if contains:
            self.assertIn(contains, ' '.join(report['errors']))
        return report

    def test_actual_standalone_positive_journal_and_certificate_verify(self):
        report = checker.check_client(self.bundles['supported'])
        self.assertTrue(report['client_scope_verified'], report['errors'])
        self.assertEqual(report['continuation_stdin_write_completions'], 1)
        self.assertEqual(report['admission_decision'], 'supported')
        self.assertTrue(report['certificate_valid'])
        self.assertEqual(report['public_task_final_state'], 'completed')
        self.assertFalse(report['application_effect_verified'])
        self.assertFalse(report['loaded_source_fidelity_verified'])

    def test_unknown_missing_binding_and_changed_state_preserve_no_dispatch(self):
        for mode in ('unknown', 'missing_call', 'changed_state'):
            report = checker.check_client(self.bundles[mode])
            with self.subTest(mode=mode):
                self.assertTrue(report['client_scope_verified'], report['errors'])
                self.assertEqual(report['continuation_stdin_write_completions'], 0)
                self.assertEqual(report['continuation_transport_attempts'], 0)

    def test_old_client_config_schema_is_rejected(self):
        bundle = self.copy_bundle()
        value = load(bundle / 'config.json'); value['schema_version'] = 'agentops-bridge-client-config/1'
        write_json(bundle / 'config.json', value)
        self.assert_rejected(bundle, 'config schema')

    def test_raw_byte_hash_tampering_is_rejected(self):
        bundle = self.copy_bundle(); journal = events(bundle / 'mcp.jsonl')
        next(row for row in journal if row['kind'] == 'mcp-message')['raw']['sha256'] = '0' * 64
        save_events(bundle / 'mcp.jsonl', journal)
        self.assert_rejected(bundle, 'Raw-byte hash')

    def test_parsed_reply_cannot_differ_from_captured_bytes(self):
        bundle = self.copy_bundle(); journal = events(bundle / 'mcp.jsonl')
        row = next(row for row in journal if row['kind'] == 'mcp-message' and row['direction'] == 'bridge_to_client')
        row['parsed']['result'] = {'forged': True}
        save_events(bundle / 'mcp.jsonl', journal)
        self.assert_rejected(bundle, 'Raw/parsed')

    def test_omitted_completed_write_cannot_leave_true_sent_flag(self):
        bundle = self.copy_bundle(); journal = events(bundle / 'mcp.jsonl')
        outgoing = next(row for row in journal if row['kind'] == 'mcp-message' and row['direction'] == 'client_to_bridge' and row['phase'] == 'raw_answer')
        write = next(row for row in journal if row['kind'] == 'stdio-written' and row['source_seq'] == outgoing['seq'])
        write['kind'] = 'discarded-write'
        save_events(bundle / 'mcp.jsonl', journal)
        self.assert_rejected(bundle, 'stdin write')

    def test_forged_write_count_is_rejected(self):
        bundle = self.copy_bundle('unknown'); value = load(bundle / 'result.json')
        value['continuation_stdin_write_completions'] = 1; value['answer_sent'] = True
        write_json(bundle / 'result.json', value)
        self.assert_rejected(bundle, 'stdin-write count')

    def test_snapshot_file_cannot_be_swapped_after_admission(self):
        bundle = self.copy_bundle(); value = load(bundle / 'admission/snapshot.json')
        value['rationale'] += ' changed'
        write_json(bundle / 'admission/snapshot.json', value)
        self.assert_rejected(bundle, 'snapshot digest')

    def test_retained_profile_must_rebuild_from_public_snapshot(self):
        bundle = self.copy_bundle(); value = load(bundle / 'admission/result.json')
        value['profile']['initial_bindings']['call'] = 'forged'
        write_json(bundle / 'admission/result.json', value)
        self.assert_rejected(bundle, 'profile differs')

    def test_forged_certificate_is_independently_rejected(self):
        bundle = self.copy_bundle(); value = load(bundle / 'admission/result.json')
        value['result']['certificate']['steps'][0]['request'] = {'forged': True}
        write_json(bundle / 'admission/result.json', value)
        self.assert_rejected(bundle, 'certificate rejection')

    def test_python_source_receipt_must_match_verifier_source(self):
        bundle = self.copy_bundle(); value = load(bundle / 'admission/result.json')
        value['source_sha256']['oracle.py'] = '0' * 64
        write_json(bundle / 'admission/result.json', value)
        self.assert_rejected(bundle, 'source bytes')

    def test_recheck_record_cannot_reuse_pre_admission_observation(self):
        bundle = self.copy_bundle(); value = load(bundle / 'result.json')
        snapshot = load(bundle / 'admission/snapshot.json')
        value['admission']['rechecks'][0]['raw'] = snapshot['observations']['raw']
        write_json(bundle / 'result.json', value)
        self.assert_rejected(bundle, 'Recheck lacks')

    def test_dispatch_event_cannot_be_relabelled_as_an_unknown_admission(self):
        bundle = self.copy_bundle(); value = load(bundle / 'admission/result.json')
        value.update(decision='unknown', dispatch_permitted=False, request=None, certificate_valid=None, result=None, profile=None)
        write_json(bundle / 'admission/result.json', value)
        journal = events(bundle / 'mcp.jsonl')
        event = next(row for row in journal if row['kind'] == 'admission-result')
        old_path = event['receipt_path']; metadata = {key: event[key] for key in checker.META}
        event.clear(); event.update(metadata); event.update(value, receipt_path=old_path)
        save_events(bundle / 'mcp.jsonl', journal)
        result = load(bundle / 'result.json'); result['admission']['admissions'] = [checker.event_payload(event)]
        write_json(bundle / 'result.json', result)
        self.assert_rejected(bundle, 'Continuation after')

    def test_client_cannot_claim_verified_application_effect(self):
        bundle = self.copy_bundle(); value = load(bundle / 'result.json')
        value['live_effect_verified_by_client'] = True
        write_json(bundle / 'result.json', value)
        self.assert_rejected(bundle, 'success claim')

    def test_bridge_process_must_match_recorded_configuration(self):
        bundle = self.copy_bundle(); value = load(bundle / 'config.json')
        value['bridge']['args'] = ['-e', 'different source']
        write_json(bundle / 'config.json', value)
        self.assert_rejected(bundle, 'process/config linkage')

    def test_subprocess_result_cannot_predate_its_execution(self):
        bundle = self.copy_bundle(); value = load(bundle / 'admission/result.json')
        value['recorded_at_utc'] = '2000-01-01T00:00:00+00:00'
        write_json(bundle / 'admission/result.json', value)
        self.assert_rejected(bundle, 'subprocess lifetime')

    def test_optional_prospective_source_hashes_are_checked(self):
        source = 'scripts/agentops_admission_client_v1.mjs'
        expected = {source: hashlib.sha256((ROOT / source).read_bytes()).hexdigest()}
        report = checker.check_client(self.bundles['supported'], expected_sources=expected)
        self.assertTrue(report['client_scope_verified'], report['errors'])
        report = checker.check_client(self.bundles['supported'], expected_sources={source: '0' * 64})
        self.assertFalse(report['client_scope_verified'])


if __name__ == '__main__':
    unittest.main()
