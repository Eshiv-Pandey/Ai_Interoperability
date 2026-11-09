"""Constructed parent-check mutations; no application or SDK is launched."""
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import check_agentops_bridge_group_v1 as checker


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def clean_group(pid):
    return {'schema_version': 'agentops-owned-process-group/1', 'pgid': pid,
        'initially_empty': True, 'final_empty': True, 'forced_cleanup': False,
        'members': [], 'final_members': [], 'errors': [], 'signals': [],
        'snapshots': [{'phase': 'initial', 'monotonic_ns': 100, 'members': [], 'errors': []}]}


class GroupAccountingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.run = Path(self.temporary.name)
        self.exported = self.run / 'workspace'
        self.exported.mkdir()
        self.base_time = datetime(2026, 10, 27, tzinfo=timezone.utc)
        self.linux = '/var/tmp/agentops-research-v7-test'
        self.runtime = self.linux + '/external/runtime-agentops-bridges-v1'
        self.seal = {'prepared_at_utc': self.at(-10), 'runtime_root': self.runtime}
        self.result = {'cases': {}, 'linux_workspace': self.linux, 'status': 'matrix_attempts_recorded',
                       'started_at_utc': self.at(0), 'finished_at_utc': self.at(200)}
        self.reports = {}
        self.addCleanup(patch.stopall)
        patch.object(checker, 'case_bindings', return_value=True).start()
        patch.object(checker, 'check_case', side_effect=lambda target, seed: self.reports[target.name[10:]]).start()

    def at(self, seconds):
        return (self.base_time + timedelta(seconds=seconds)).isoformat()

    def matrix(self, positive=True, stop_after=None):
        for index, (case_id, definition) in enumerate(checker.design.CASES.items()):
            if stop_after is not None and index > stop_after:
                self.result['status'] = 'failed'
                self.result['error'] = 'ValueError: retained stop'
                row = {'status': 'unexecuted', 'reason': 'Group stopped before this planned case',
                       'group_error': self.result['error']}
                self.result['cases'][case_id] = row
                write(self.run / (case_id + '.unexecuted.json'), row)
                continue
            failed = [] if positive else definition['native_prerequisites']
            if failed:
                row = {'status': 'skipped', 'reason': 'Native positive control did not qualify', 'failed_prerequisites': failed}
                self.result['cases'][case_id] = row
                write(self.run / (case_id + '.skipped.json'), row)
                continue
            target = self.exported / (checker.CASE_PREFIX + case_id)
            semantic = {'schema_version': 'agentops-bridge-case-check/1', 'valid': True, 'complete': True,
                'strict_success': positive, 'outcome': 'strict_success' if positive else 'observed_non_success'}
            self.reports[case_id] = semantic
            write(target / 'case-check.json', semantic)
            outcome = {'status': 'recorded', 'service_strict_success': positive, 'service_returncode': 0,
                'client_returncode': 0, 'client_timed_out': False, 'client_forced_kill': False,
                'forced_service_stop': False, 'source_unchanged_after': True, 'cleanup_errors': []}
            if definition['kind'] == 'bridge':
                outcome.update(bridge_clean_exit=True, bridge_forced_kill=False)
            write(target / 'result.json', outcome)
            write(target / 'client.started.json', {'pid': 102})
            write(target / 'service-process.json', {'pid': 103})
            row = {'argv': ['/usr/bin/python3', '-B', self.linux + '/scripts/agentops_bridge_control_v1.py',
                '--case', case_id, '--runtime-root', self.runtime, '--seal', self.linux + '/' + checker.SEAL],
                'cwd': self.linux, 'pid': 101, 'started_at_utc': self.at(index * 10 + 1),
                'finished_at_utc': self.at(index * 10 + 8), 'returncode': 0, 'timed_out': False,
                'cleanup_errors': [], 'owned_groups': {label: clean_group(pid) for label, pid in
                    (('controller', 101), ('client', 102), ('service', 103))}}
            if stop_after == index:
                row['owned_groups']['client'] = {'status': 'identity_unconfirmed'}
            for suffix in ('stdout', 'stderr'):
                (self.run / f'{case_id}.{suffix}.bin').write_bytes(b'')
            row['streams'] = [checker.record(self.run / f'{case_id}.{suffix}.bin', self.run) for suffix in ('stdout', 'stderr')]
            write(self.run / (case_id + '.json'), row)
            write(self.run / (case_id + '.started.json'), {key: row[key] for key in ('argv', 'cwd', 'pid', 'started_at_utc')})
            self.result['cases'][case_id] = {key: outcome[key] for key in
                ('status', 'service_strict_success', 'service_returncode', 'client_returncode')}
            self.result['cases'][case_id]['strict_success'] = positive

    def check(self):
        return checker.check_stages(self.run, self.exported, self.result, self.seal, {})

    def change_receipt(self, case_id, mutate):
        path = self.run / (case_id + '.json')
        row = checker.load(path)
        mutate(row)
        write(path, row)

    def test_complete_positive_matrix_is_accounted(self):
        self.matrix()
        reports, gaps, counts = self.check()
        self.assertEqual(counts, {'executed': 18, 'skipped': 0, 'unexecuted': 0})
        self.assertEqual(gaps, [])
        self.assertTrue(all(row['strict_success'] for row in reports.values()))

    def test_complete_non_success_is_valid_and_bridges_skip_only_outer(self):
        self.matrix(positive=False)
        reports, gaps, counts = self.check()
        self.assertEqual(counts, {'executed': 11, 'skipped': 7, 'unexecuted': 0})
        self.assertEqual(reports['N1']['outcome'], 'observed_non_success')
        self.assertEqual(reports['B1']['outcome'], 'unknown_or_partial')
        self.assertEqual(len(gaps), 7)

    def test_missing_extra_or_reordered_case_rejected(self):
        self.matrix()
        cases = self.result['cases']
        for candidate in ({key: value for key, value in cases.items() if key != 'N2'},
                          dict(cases, Z1={}), dict(reversed(list(cases.items())))):
            self.result['cases'] = candidate
            with self.subTest(keys=list(candidate)), self.assertRaisesRegex(ValueError, 'ordered matrix'):
                self.check()

    def test_reordered_capture_intervals_rejected(self):
        self.matrix()
        self.change_receipt('N2', lambda row: row.update(started_at_utc=self.at(1)))
        with self.assertRaisesRegex(ValueError, 'stage order'):
            self.check()

    def test_fabricated_skip_prerequisite_rejected(self):
        self.matrix(positive=False)
        row = self.result['cases']['B1']
        row['failed_prerequisites'] = ['N1']
        write(self.run / 'B1.skipped.json', row)
        with self.assertRaisesRegex(ValueError, 'recomputed failed native'):
            self.check()

    def test_case_directory_for_group_skip_rejected(self):
        self.matrix(positive=False)
        (self.exported / (checker.CASE_PREFIX + 'B1')).mkdir()
        with self.assertRaisesRegex(ValueError, 'execution footprint'):
            self.check()

    def test_unplanned_case_footprint_rejected(self):
        self.matrix()
        (self.exported / (checker.CASE_PREFIX + 'B99')).mkdir()
        with self.assertRaisesRegex(ValueError, 'Unplanned bridge case footprint'):
            self.check()

    def test_cleanup_unknown_stops_group_and_preserves_partial_result(self):
        self.matrix(stop_after=0)
        reports, gaps, counts = self.check()
        self.assertEqual(counts, {'executed': 1, 'skipped': 0, 'unexecuted': 17})
        self.assertIn('N1:group_cleanup_stop', gaps)
        self.assertEqual(reports['N2']['outcome'], 'unknown_or_partial')

    def test_continuation_after_unknown_cleanup_rejected(self):
        self.matrix()
        self.change_receipt('N1', lambda row: row['owned_groups'].update(client={'status': 'receipt_absent'}))
        with self.assertRaisesRegex(ValueError, 'No execution after stop'):
            self.check()

    def test_retained_case_report_mismatch_rejected(self):
        self.matrix()
        write(self.exported / (checker.CASE_PREFIX + 'N1') / 'case-check.json', dict(self.reports['N1'], strict_success=False))
        with self.assertRaisesRegex(ValueError, 'independent recomputation'):
            self.check()

    def test_outer_success_claim_cannot_override_recomputed_report(self):
        self.matrix(positive=False)
        self.result['cases']['N1']['strict_success'] = True
        with self.assertRaisesRegex(ValueError, 'summary binds recomputed'):
            self.check()

    def test_missing_case_check_stays_unknown_and_cannot_enable_bridge(self):
        self.matrix(positive=False)
        (self.exported / (checker.CASE_PREFIX + 'N1') / 'case-check.json').unlink()
        _, gaps, _ = self.check()
        self.assertIn('N1:missing_retained_case_check', gaps)

    def test_missing_positive_native_report_does_not_qualify_bridge(self):
        self.matrix(positive=False)
        target = self.exported / (checker.CASE_PREFIX + 'N3')
        (target / 'case-check.json').unlink()
        self.reports['N3'].update(strict_success=True, outcome='strict_success')
        _, gaps, counts = self.check()
        self.assertEqual(counts['skipped'], 7)
        self.assertIn('N3:missing_retained_case_check', gaps)


class IntegrityTests(unittest.TestCase):
    def test_cleanup_positive_claim_requires_matching_empty_membership(self):
        self.assertTrue(checker.owned_group(clean_group(100), 100))
        for mutate in (lambda row: row.update(pgid=999),
                       lambda row: row['final_members'].append({'pid': 8}),
                       lambda row: row.update(snapshots=[]),
                       lambda row: row.update(forced_cleanup=True)):
            row = clean_group(100)
            mutate(row)
            with self.subTest(row=row), self.assertRaises(ValueError):
                checker.owned_group(row, 100)
        self.assertFalse(checker.owned_group({'status': 'receipt_absent'}, None))

    def test_linux_configuration_rebases_embedded_script_without_windows_paths(self):
        config = checker.expected_config(checker.design.CASES['B7'], '/var/tmp/replica', '/var/tmp/runtime')
        self.assertEqual(config['bridge']['args'][0], '/var/tmp/replica/scripts/agentops_mgcrea_embed_v1.mjs')
        self.assertEqual(config['bridge']['cwd'], '/var/tmp/runtime')
        self.assertEqual(config['bridge']['env']['A2A_STATE_DIR'], '/var/tmp/replica/' + checker.CASE_PREFIX + 'B7/bridge-state')

    def test_export_omission_extra_and_changed_inputs_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'one').write_bytes(b'original')
            row = checker.record(root / 'one', root)
            manifest = {'files': [row], 'bytes': row['bytes'], 'reference_failures': []}
            result = {'exported_files': 1, 'export_reference_failures': [], 'parent_inputs_unchanged': True}
            self.assertEqual(checker.complete_export(root, manifest, result, [row], []), {'one'})
            (root / 'extra').write_bytes(b'')
            with self.assertRaisesRegex(ValueError, 'Complete export'):
                checker.complete_export(root, manifest, result, [row], [])
            (root / 'extra').unlink()
            with self.assertRaises(ValueError):
                checker.complete_export(root, dict(manifest, files=[]), result, [row], [])
            (root / 'one').write_bytes(b'mutated')
            with self.assertRaisesRegex(ValueError, 'Changed/missing file'):
                checker.complete_export(root, manifest, result, [row], [])

    def test_prospective_definition_and_launch_input_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'input').write_bytes(b'pinned')
            seal = {'schema_version': 'agentops-bridge-preparation/1', 'cases': list(checker.design.CASES.values()),
                'application_requests': 0, 'live_model_calls': 0, 'research_gate_credit_added': 0,
                'launch_inputs': [checker.record(root / 'input', root)], 'prerequisites': []}
            write(root / checker.SEAL, dict(seal, cases=list(reversed(seal['cases']))))
            with self.assertRaisesRegex(ValueError, 'prospectively ordered'):
                checker.validate_preparation(root)
            write(root / checker.SEAL, seal)
            with patch.object(checker.preparation, 'LAUNCH_FILES', ['input', 'omitted']):
                with self.assertRaisesRegex(ValueError, 'launch input inventory'):
                    checker.validate_preparation(root)
            (root / 'input').write_bytes(b'changed')
            with patch.object(checker.preparation, 'LAUNCH_FILES', ['input']):
                with self.assertRaisesRegex(ValueError, 'Changed/missing file'):
                    checker.validate_preparation(root)

    def test_real_frozen_archive_and_mutations(self):
        source = ROOT / checker.preparation.RUNTIME_PREP
        verified = checker.verify_archive(source)
        self.assertEqual(verified['runtime_receipt']['files'], 2938)
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            for name in ('graph.json', 'archive.json', 'runtime.zip', 'materialization.json',
                         'runtime-verification.json', 'runtime-bytes-verification.json'):
                shutil.copyfile(source / name, target / name)
            receipt = checker.load(target / 'archive.json')
            write(target / 'archive.json', dict(receipt, graph_sha256='0' * 64))
            with self.assertRaisesRegex(ValueError, 'graph/archive hashes'):
                checker.verify_archive(target)
            write(target / 'archive.json', receipt)
            with zipfile.ZipFile(target / 'runtime.zip', 'a') as bundle:
                bundle.writestr('unplanned', b'changed runtime')
            with self.assertRaisesRegex(ValueError, 'archive binding'):
                checker.verify_archive(target)
            changed = checker.record(target / 'runtime.zip', target)
            write(target / 'archive.json', dict(receipt, bytes=changed['bytes'], archive_sha256=changed['sha256']))
            with self.assertRaisesRegex(ValueError, 'archive entries'):
                checker.verify_archive(target)


class CaseBindingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.target = self.root / (checker.CASE_PREFIX + 'N1')
        self.linux = '/var/tmp/agentops-research-v7-test'
        self.seal = {'runtime_root': self.linux + '/external/runtime-agentops-bridges-v1'}
        self.begin = checker.timestamp('2026-10-27T00:00:00+00:00')
        self.end = checker.timestamp('2026-10-27T00:00:10+00:00')
        write(self.root / checker.SEAL, self.seal)
        write(self.root / 'scripts/serve_agentops_bridge_v1.py', {'inert_fixture': True})
        write(self.root / 'runs/agentops-native-eligibility/native-probe-v7/plan.json', {'source_files': []})
        config = checker.expected_config(checker.design.CASES['N1'], self.linux, self.seal['runtime_root'])
        write(self.target / 'client-config.json', config)
        write(self.target / 'agents.json', {'agents': {'agentops': {
            'cardUrl': 'http://127.0.0.1:18764/.well-known/agent-card.json'}}})
        self.plan = {'schema_version': 'agentops-bridge-case-plan/1', **checker.design.CASES['N1'],
            'port': 18764, 'bridge_port': 18765, 'prepared_at_utc': '2026-10-27T00:00:01+00:00',
            'seal': checker.record(self.root / checker.SEAL, self.root), 'source_files': [],
            'service_source': checker.record(self.root / 'scripts/serve_agentops_bridge_v1.py', self.root),
            'client_config': checker.record(self.target / 'client-config.json', self.root)}
        write(self.target / 'plan.json', self.plan)
        client = {'argv': ['/usr/bin/node', self.linux + '/scripts/agentops_native_profile_client_v1.mjs',
            '--config', self.linux + '/' + checker.CASE_PREFIX + 'N1/client-config.json'],
            'cwd': self.linux, 'pid': 102, 'started_at_utc': '2026-10-27T00:00:04+00:00',
            'finished_at_utc': '2026-10-27T00:00:06+00:00', 'owned_group': clean_group(102)}
        for suffix in ('stdout', 'stderr'):
            (self.target / ('client.' + suffix + '.bin')).write_bytes(b'')
        client['streams'] = [checker.record(self.target / ('client.' + suffix + '.bin'), self.root)
                             for suffix in ('stdout', 'stderr')]
        write(self.target / 'client-process.json', client)
        write(self.target / 'client.started.json', client)
        write(self.target / 'service-process.json', {'pid': 103, 'started_at_utc': '2026-10-27T00:00:03+00:00',
            'argv': [self.linux + '/external/runtime-agentops-linux-v7/venv/bin/python', '-B',
                self.linux + '/scripts/serve_agentops_bridge_v1.py', '--output',
                self.linux + '/' + checker.CASE_PREFIX + 'N1/service', '--port', '18764']})
        write(self.target / 'service/terminal.snapshot.json', {'monotonic_ns': 101})
        self.outcome = {'schema_version': 'agentops-bridge-case-result/1', 'case_id': 'N1', 'kind': 'native',
            'status': 'recorded', 'started_at_utc': '2026-10-27T00:00:02+00:00',
            'finished_at_utc': '2026-10-27T00:00:09+00:00', 'live_model_calls': 0, 'research_gate_credit_added': 0,
            'client_group_cleanup': clean_group(102), 'service_group_cleanup': clean_group(103)}

    def check(self):
        self.outcome['files'] = [checker.record(path, self.root) for path in self.target.rglob('*') if path.is_file()]
        gaps = []
        clean = checker.case_bindings(self.root, 'N1', self.seal, self.linux, self.outcome, self.begin, self.end, gaps)
        return clean, gaps

    def test_case_binds_actual_v7_source_and_linux_configuration(self):
        self.assertEqual(self.check(), (True, []))

    def test_rehashed_unplanned_client_input_is_rejected(self):
        config = checker.load(self.target / 'client-config.json')
        config['representation'] = 'data'
        write(self.target / 'client-config.json', config)
        self.plan['client_config'] = checker.record(self.target / 'client-config.json', self.root)
        write(self.target / 'plan.json', self.plan)
        with self.assertRaisesRegex(ValueError, 'prospective client configuration'):
            self.check()

    def test_terminal_snapshot_cannot_precede_service_cleanup(self):
        write(self.target / 'service/terminal.snapshot.json', {'monotonic_ns': 99})
        with self.assertRaisesRegex(ValueError, 'cleanup precedes terminal'):
            self.check()

    def test_client_cleanup_result_must_equal_receipt(self):
        self.outcome['client_group_cleanup'] = {'status': 'receipt_absent'}
        with self.assertRaisesRegex(ValueError, 'cleanup/result binding'):
            self.check()


if __name__ == '__main__':
    unittest.main()
