"""Constructed read-auditor controls; no benchmark solver or checker executes."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import audit_common_cost_results_v1 as auditor


class MemoryCapture:
    def __init__(self, completed=False):
        self.data = {}
        package = ROOT / 'benchmark/common-cost-v1'
        protocol = auditor.parse((package / 'protocol.json').read_bytes())
        for name in ['protocol.json', 'order.json', *[r['path'] for r in protocol['sources'] + protocol['profiles']]]:
            self.data['snapshot/' + name] = (package / name).read_bytes()
        for name in ('common_cost_worker_v1.py', 'run_common_cost_benchmark_v1.py'):
            self.data['driver/' + name] = (ROOT / 'scripts' / name).read_bytes()
        for key, filename in [('source_suite', 'prior-suite.json'), ('source_input_manifest', 'prior-input-manifest.json')]:
            self.data['snapshot/provenance/' + filename] = (ROOT / protocol[key]['original_path']).read_bytes()
        self.cells = auditor.parse(self.data['snapshot/order.json'])['cells']
        self.protocol = protocol
        self.rows = []
        profiles = {p['id']: p for p in protocol['profiles']}; methods = {m['id']: m for m in protocol['methods']}
        for cell in self.cells:
            prefix = 'cells/' + cell['id'] + '/'
            self.put(prefix + 'job.json', {'schema_version': 'common-cost-job/1', 'cell': cell,
                'snapshot_root': '/tmp/constructed-common-cost/snapshot', 'profile': profiles[cell['profile_id']],
                'method': methods[cell['method_id']], 'sources': protocol['sources'], 'checker': protocol['checker'],
                'caps': auditor.CAPS, 'evaluation_clock': 100})
            if completed:
                index = [m[0] for m in auditor.METHODS].index(cell['method_id']) + 1
                cpu, wall, rss = 10000 * index * (cell['repeat'] + 1), 20000 * index * (cell['repeat'] + 1), 1048576 + index * 1024
                resources = {'returncode': 0, 'wait_status': 0, 'pid': 1000 + cell['index'],
                    'owned_process_group': 1000 + cell['index'], 'wall_cap_kill_requested': False,
                    'cpu_user_ns': cpu, 'cpu_system_ns': 0, 'cpu_total_ns': cpu, 'outer_wall_ns': wall,
                    'peak_rss_bytes': rss, 'resource_source': 'sole terminal os.wait4 per-child rusage after termination',
                    'owned_group_cleanup_requested_before_terminal_reap': True, 'parent_interruption_type': None,
                    'group_cleanup_error_type': None, 'caps_applied_before_exec': auditor.CAPS}
                reason = sorted(auditor.REASONS[cell['method_id']]['supported'])[0]
                model = auditor.parse(self.data['snapshot/' + profiles[cell['profile_id']]['path']])
                certificate = {'constructed': True, 'kind': 'recipe-path', 'checked_at': 100,
                    'horizon': model['model']['horizon'], 'valid_until': model['model']['evidence']['valid_until'],
                    'profile_sha256': hashlib.sha256(json.dumps(model, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()}
                result = {'decision': 'supported', 'reason': reason, 'certificate': certificate,
                          'stats': {'budget': 100000000, 'work_units': 1}}
                self.put(prefix + 'solver-result.json', result, newline=False)
                reply = {'schema_version': 'common-cost-worker/1', 'cell': cell, 'status': 'certified',
                    'decision': 'supported', 'certificate_valid': True, 'caps_observed': auditor.CAPS,
                    'phase_resources': {name: {'cpu_ns': 1, 'wall_ns': 2} for name in auditor.PHASES},
                    'worker_entry_to_pre_reply_cpu_ns': 10, 'worker_entry_to_pre_reply_wall_ns': 20,
                    'peak_rss_before_reply_bytes': 524288,
                    'interpreter_flags': {'no_site': 1, 'safe_path': True, 'isolated': 0, 'ignore_environment': 0},
                    'hash_seed_probe': 7, 'profile_identity': auditor.id_fields(profiles[cell['profile_id']]),
                    'solver_result_identity': auditor.identity(self.data[prefix + 'solver-result.json']),
                    'method_meter': {'budget': 100000000, 'work_units': 1, 'reason': reason},
                    'solver_logical_cap_nonbinding': True, 'checker_internal_cap_nonbinding_for_accepted_proof': True}
                self.put(prefix + 'reply.json', reply)
                self.data[prefix + 'stdout.bin'] = b''; self.data[prefix + 'stderr.bin'] = b''
                row = {'cell': cell, 'resources': resources,
                       **{k: v for k, v in reply.items() if k not in {'schema_version', 'cell', 'resources'}}}
                self.put(prefix + 'after.json', row); self.rows.append(row)
            else:
                self.rows.append({'cell': cell, 'status': 'not_started', 'decision': None,
                                  'certificate_valid': None, 'resources': None})
        frozen = [dict(path=n, **auditor.identity(raw)) for n, raw in self.data.items()
                  if n.startswith(('snapshot/', 'driver/')) or n.endswith('/job.json')]
        allocation = {'schema_version': 'common-cost-allocation/1', 'declared_cells': 1650,
            'created_utc': '2026-11-11T00:00:00+00:00', 'cells': self.cells, 'frozen_files': frozen,
            'protocol_identity': auditor.PINNED['snapshot/protocol.json'], 'order_identity': auditor.PINNED['snapshot/order.json'],
            'all_input_source_order_and_job_hashes_frozen_before_execution': True, 'new_application_or_provider_runs': 0,
            'runtime': {'platform': 'linux', 'python': '3.13.1 (constructed control)', 'executable': '/constructed/python',
                        'executable_identity': auditor.identity(b'constructed executable identity only')}}
        self.put('allocation.json', allocation)
        if completed:
            self.put('execution-start.json', {'created_utc': '2026-11-11T00:00:01+00:00',
                'allocation_identity': auditor.identity(self.data['allocation.json']), 'one_serial_hosted_runner': True})
            for cell in self.cells:
                prefix = 'cells/' + cell['id'] + '/'
                self.put(prefix + 'before.json', {'cell': cell, 'job_identity': auditor.identity(self.data[prefix + 'job.json']),
                    'caps': auditor.CAPS, 'hash_seed': cell['hash_seed'], 'started_utc': '2026-11-11T00:00:02+00:00',
                    'argv': ['/constructed/python', '-S', '-P', '-B', '/tmp/constructed-common-cost/driver/common_cost_worker_v1.py',
                             '--job', '/tmp/constructed-common-cost/' + prefix + 'job.json']})
        # Expected uniform fixture summary is specified by direct known medians.
        methods = [m[0] for m in auditor.METHODS]; pairs = {}
        for left_index, left in enumerate(methods, 1):
            for right_index, right in enumerate(methods[left_index:], left_index + 1):
                cohort = []
                if completed:
                    for i in range(1, 67):
                        item = {'profile_id': f'scale-{i:04d}', 'paired_repeats': 5}
                        for field, a, b in [('cpu_total_ns', 30000 * left_index, 30000 * right_index),
                                            ('outer_wall_ns', 60000 * left_index, 60000 * right_index),
                                            ('peak_rss_bytes', 1048576 + left_index * 1024, 1048576 + right_index * 1024)]:
                            item[field] = {'left_median': a, 'right_median': b, 'left_over_right': a / b}
                        cohort.append(item)
                pairs[left + '__' + right] = {'complete_same_decision_certified_profile_count': 66 if completed else 0,
                    'required_paired_repeats_per_profile': 5, 'per_profile': cohort}
        summary = {'allocated_cells': 1650, 'by_method_status_counts': {m: {'certified' if completed else 'not_started': 330} for m in methods},
            'hash_seed_probe_disagreements': [], 'certified_contradictions': [],
            'all_five_method_certified_same_decision_profile_repeat_blocks': 330 if completed else 0,
            'paired_costs': pairs, 'comparison_unit': '66 related authored profiles; five dependent timing replicates',
            'adverse_allocations_excluded_from_cost_ratios_but_retained_in_status_denominator': True,
            'no_novelty_or_superiority_assumed': True, 'certified_cost_cohorts_usable': True}
        self.put('results.json', {'schema_version': 'common-cost-results/1', 'cells': self.rows, 'summary': summary,
            'frozen_integrity_verified': True, 'allocation_identity': auditor.identity(self.data['allocation.json'])})
        self.put('manifest.json', {'files': [dict(path=n, **auditor.identity(raw)) for n, raw in self.data.items()]})
        self.refresh()

    def put(self, name, value, newline=True): self.data[name] = auditor.canonical(value) + (b'\n' if newline else b'')
    def refresh(self): self.files = {n: auditor.identity(raw) for n, raw in self.data.items()}
    def raw(self, name): return self.data[name]
    def json(self, name): return auditor.parse(self.raw(name))
    def verify(self, name, row): auditor.need(self.files.get(name) == auditor.id_fields(row), 'constructed_frozen_bytes_changed')


class CommonCostReadAuditControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stopped = MemoryCapture()
        cls.complete = MemoryCapture(completed=True)

    def test_duplicate_keys_nonfinite_values_and_unsafe_archive_members_are_refused(self):
        for raw in [b'{"id":1,"id":2}', b'{"cost":NaN}', b'{"cost":Infinity}']:
            with self.assertRaises(ValueError): auditor.parse(raw)
        for name in ['../x', '/x', 'C:/x', 'x\\y', './x', 'x//y']:
            with self.assertRaises(ValueError): auditor.member_name(name)

    def test_saved_API_archive_and_extracted_bytes_are_bound(self):
        with tempfile.TemporaryDirectory(prefix='common-cost-constructed-retained-control-') as temp:
            base = Path(temp) / f'retained-{auditor.RUN_ID}-1'; (base / 'extracted').mkdir(parents=True)
            (base / 'extracted/x.json').write_bytes(b'{}')
            with zipfile.ZipFile(base / 'artifact.zip', 'w') as archive: archive.writestr('x.json', b'{}')
            raw = auditor.file_identity(base / 'artifact.zip'); name = f'common-cost-development-v1-{auditor.RUN_ID}-1'
            metadata = {'github-run.json': {'id': auditor.RUN_ID, 'status': 'completed', 'run_attempt': 1,
                'head_sha': auditor.HEAD_SHA, 'event': 'workflow_dispatch', 'path': '.github/workflows/common-cost-benchmark-v1.yml',
                'html_url': f'https://github.com/{auditor.REPOSITORY}/actions/runs/{auditor.RUN_ID}', 'conclusion': 'success'},
                'plan.json': {'run_id': auditor.RUN_ID, 'repository': auditor.REPOSITORY, 'application_rerun': False, 'artifact_name': name},
                'github-artifacts.json': {'artifacts': [{'id': 123, 'name': name, 'digest': 'sha256:' + raw['sha256'],
                    'size_in_bytes': raw['bytes'], 'expired': False, 'workflow_run': {'id': auditor.RUN_ID, 'head_sha': auditor.HEAD_SHA}}]},
                'retention.json': {'status': 'retained', 'run_id': auditor.RUN_ID, 'head_sha': auditor.HEAD_SHA,
                    'workflow_conclusion': 'success', 'artifact_name': name, 'artifact_id': 123,
                    'archive_bytes': raw['bytes'], 'archive_sha256': raw['sha256'], 'api_digest': 'sha256:' + raw['sha256'],
                    'digest_matches_api': True, 'extracted_files': 1},
                'extracted-manifest.json': {'files': [dict(path='x.json', **auditor.identity(b'{}'))]}}
            for filename, value in metadata.items(): (base / filename).write_bytes(auditor.canonical(value))
            self.assertEqual(auditor.Capture(base).files, {'x.json': auditor.identity(b'{}')})
            (base / 'extracted/x.json').write_bytes(b'{changed')
            with self.assertRaises(ValueError): auditor.Capture(base)
            (base / 'extracted/x.json').write_bytes(b'{}')
            metadata['retention.json']['api_digest'] = 'sha256:' + '0' * 64
            (base / 'retention.json').write_bytes(auditor.canonical(metadata['retention.json']))
            with self.assertRaises(ValueError): auditor.Capture(base)

    def test_all_1650_unstarted_allocations_and_ten_empty_cohorts_remain(self):
        result = auditor.analyze_capture(self.stopped)
        self.assertEqual(result['launched_opening_receipts'], 0); self.assertEqual(len(result['cells']), 1650)
        self.assertEqual(len(result['paired_profile_costs']), 10)
        self.assertTrue(all(p['complete_same_decision_certified_profile_count'] == 0 for p in result['paired_profile_costs'].values()))
        self.assertTrue(all(t['all_status_counts']['not_started'] == 330 for t in result['method_totals']))

    def test_complete_raw_five_repeat_cohorts_match_known_profile_medians(self):
        result = auditor.analyze_capture(self.complete)
        self.assertEqual(result['launched_opening_receipts'], 1650); self.assertEqual(len(result['cells']), 1650)
        self.assertFalse(result['independent_cost_cohorts_differ_from_frozen_runner'])
        self.assertEqual(result['logical_headroom_raw_label_discrepancies'], [])
        self.assertTrue(all(p['complete_same_decision_certified_profile_count'] == 66 for p in result['paired_profile_costs'].values()))
        pair = result['paired_profile_costs']['legacy_direct__goal_pruned_direct']['per_profile'][0]
        self.assertEqual(pair['cpu_total_ns'], {'left_median': 30000, 'right_median': 60000, 'left_over_right': 0.5})
        self.assertTrue(all(t['all_status_counts']['certified'] == 330 for t in result['method_totals']))

    def test_resource_status_and_reply_projection_corruption_are_refused(self):
        cell = self.complete.cells[0]; capture = deepcopy(self.complete); name = 'cells/' + cell['id'] + '/after.json'
        row = capture.json(name); row['resources']['returncode'] = -9; capture.put(name, row); capture.refresh()
        with self.assertRaises(ValueError): auditor.audit_cell(capture, cell, capture.json('allocation.json'), '/tmp/constructed-common-cost/snapshot')
        capture = deepcopy(self.complete); row = capture.json(name); row['resources']['cpu_total_ns'] += 1000
        capture.put(name, row); capture.refresh()
        with self.assertRaises(ValueError): auditor.audit_cell(capture, cell, capture.json('allocation.json'), '/tmp/constructed-common-cost/snapshot')

    def test_reply_profile_and_certificate_header_identity_corruption_are_refused(self):
        cell = self.complete.cells[0]; capture = deepcopy(self.complete); prefix = 'cells/' + cell['id'] + '/'
        reply = capture.json(prefix + 'reply.json'); reply['profile_identity'] = auditor.identity(b'other-profile')
        capture.put(prefix + 'reply.json', reply); capture.refresh()
        with self.assertRaises(ValueError): auditor.audit_cell(capture, cell, capture.json('allocation.json'), '/tmp/constructed-common-cost/snapshot')
        profile = capture.json('snapshot/' + capture.json(prefix + 'job.json')['profile']['path'])
        result = capture.json(prefix + 'solver-result.json'); result['certificate']['checked_at'] = 99
        with self.assertRaises(ValueError): auditor.certificate_binding(profile, result, cell['method_id'])
        result = capture.json(prefix + 'solver-result.json'); result['certificate']['checked_at'] = 100.0
        with self.assertRaises(ValueError): auditor.certificate_binding(profile, result, cell['method_id'])

    def test_exhaustion_reason_overrides_counter_and_profile_contradiction_quarantines_all_pairs(self):
        self.assertEqual(auditor.logical_headroom('legacy_direct', 'unknown',
            {'budget': 100000000, 'work_units': 1, 'reason': 'work_budget_exhausted'}, True),
            (False, 'binding_work_budget_exhausted_reason', True))
        rows = deepcopy(self.complete.rows); profile = 'scale-0001'
        for row in rows: row['static_method_reason_catalogue_match'] = True
        changed = next(r for r in rows if r['cell']['profile_id'] == profile)
        changed['decision'] = 'unsupported'
        summary, pairs = auditor.reconstruct_summary(rows, conservative=True)
        self.assertEqual(summary['certified_contradictions'], [{'profile_id': profile, 'verdicts': ['supported', 'unsupported']}])
        self.assertTrue(all(p['complete_same_decision_certified_profile_count'] == 65 for p in pairs.values()))
        rows = deepcopy(self.complete.rows)
        for row in rows: row['static_method_reason_catalogue_match'] = True
        changed = next(r for r in rows if r['cell']['profile_id'] == profile)
        changed['method_meter']['reason'] = 'work_budget_exhausted'
        changed['solver_logical_cap_nonbinding'] = False
        _, pairs = auditor.reconstruct_summary(rows, conservative=True)
        self.assertEqual(sum(p['complete_same_decision_certified_profile_count'] == 65 for p in pairs.values()), 4)

    def test_malformed_closure_keeps_failure_identity_and_raw_diagnostics(self):
        capture = deepcopy(self.complete); cell = capture.cells[0]; name = 'cells/' + cell['id'] + '/after.json'
        capture.data[name] = b'{partial'; capture.refresh()
        row, details, _ = auditor.audit_cell(capture, cell, capture.json('allocation.json'), '/tmp/constructed-common-cost/snapshot')
        self.assertEqual(row['status'], 'failure'); self.assertIsNone(row['resources'])
        self.assertEqual(row['retained_closing_identity'], auditor.identity(b'{partial'))
        self.assertTrue(details['raw_result_meter_verified']); self.assertTrue(details['retained_raw_files'])

    def test_frozen_source_bytes_and_per_cell_job_tampering_are_refused(self):
        capture = deepcopy(self.stopped)
        capture.data['driver/common_cost_worker_v1.py'] += b'# altered'; capture.refresh()
        with self.assertRaises(ValueError): auditor.verify_protocol_allocation(capture)
        capture = deepcopy(self.stopped); cell = capture.cells[0]; name = 'cells/' + cell['id'] + '/job.json'
        job = capture.json(name); job['cell']['hash_seed'] += 1; capture.put(name, job); capture.refresh()
        with self.assertRaises(ValueError): auditor.verify_protocol_allocation(capture)


if __name__ == '__main__':
    unittest.main()
