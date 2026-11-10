"""Meaningful order, retention and generic Linux resource controls."""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import run_common_cost_benchmark_v1 as runner


class CommonCostProtocolControls(unittest.TestCase):
    def test_exact_existing_profiles_and_sources_and_balanced_1650_order(self):
        protocol, cells = runner.verify_package()
        prior = runner.read(ROOT / protocol['source_input_manifest']['original_path'])
        original = {c['profile_id']: c for c in prior['cases']}
        for profile in protocol['profiles']:
            expected = original[profile['id']]['input']
            self.assertEqual({k: profile[k] for k in ('bytes', 'sha256')}, {k: expected[k] for k in ('bytes', 'sha256')})
            self.assertEqual((runner.PACKAGE / profile['path']).read_bytes(),
                             (ROOT / 'runs/refinement-scaling/v2/inputs' / expected['path']).read_bytes())
        for source in protocol['sources']:
            self.assertEqual((runner.PACKAGE / source['path']).read_bytes(), (ROOT / source['original_path']).read_bytes())
        self.assertEqual(len(cells), 1650)
        for profile in protocol['profiles']:
            for method in protocol['methods']:
                rows = [c for c in cells if c['profile_id'] == profile['id'] and c['method_id'] == method['id']]
                self.assertEqual({c['position'] for c in rows}, set(range(5)))
            for repeat in range(5):
                self.assertEqual(len({c['hash_seed'] for c in cells if c['profile_id'] == profile['id'] and c['repeat'] == repeat}), 1)

    def test_order_tampering_and_missing_allocation_are_refused(self):
        protocol, _ = runner.verify_package(); order = runner.read(runner.PACKAGE / 'order.json')
        changed = deepcopy(order); changed['cells'][0], changed['cells'][1] = changed['cells'][1], changed['cells'][0]
        with self.assertRaises(ValueError): runner.verify_order(protocol, changed)
        changed = deepcopy(order); changed['cells'].pop()
        with self.assertRaises(ValueError): runner.verify_order(protocol, changed)

    def test_atomic_publication_retains_interruption_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory(prefix='common-cost-publication-control-') as temp:
            target = Path(temp) / 'after.json'
            with patch.object(runner.os, 'link', side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt): runner.write(target, {'constructed': True})
            self.assertFalse(target.exists())
            pending = list(Path(temp).glob('.after.json.pending-*'))
            self.assertEqual(len(pending), 1)
            runner.write(target, {'completed': True}); before = target.read_bytes()
            with self.assertRaises(FileExistsError): runner.write(target, {'overwrite': True})
            self.assertEqual(target.read_bytes(), before)
            self.assertEqual(runner.read(pending[0]), {'constructed': True})

    def test_post_link_manifest_alias_is_retained_and_partial_pending_is_inventoried(self):
        with tempfile.TemporaryDirectory(prefix='common-cost-manifest-alias-control-') as temp:
            output = Path(temp)
            partial = output / ('.manifest.json.pending-' + '1' * 32)
            partial.write_bytes(b'{partial')
            retained = output / 'result.json'; retained.write_bytes(b'{}')
            expected = {'files': [dict(path=p.relative_to(output).as_posix(), **runner.identity(p.read_bytes()))
                                  for p in runner.artifact_files(output)]}
            original_unlink = Path.unlink
            def interrupt_manifest_unlink(path, *args, **kwargs):
                if path.name.startswith('.manifest.json.pending-'):
                    raise KeyboardInterrupt
                return original_unlink(path, *args, **kwargs)
            with patch.object(Path, 'unlink', interrupt_manifest_unlink):
                with self.assertRaises(KeyboardInterrupt): runner.write(output / 'manifest.json', expected)
            aliases = [p for p in output.glob('.manifest.json.pending-*') if p != partial]
            self.assertEqual(len(aliases), 1)
            self.assertEqual(aliases[0].read_bytes(), (output / 'manifest.json').read_bytes())
            files = runner.artifact_files(output)
            self.assertEqual({p.relative_to(output).as_posix() for p in files},
                             {r['path'] for r in runner.read(output / 'manifest.json')['files']})
            for row in runner.read(output / 'manifest.json')['files']:
                runner.verify_record(output, row)
            self.assertTrue(aliases[0].exists()); self.assertEqual(partial.read_bytes(), b'{partial')
            # Detach the hard link so only the pending pathname changes.
            aliases[0].unlink()
            aliases[0].write_bytes(b'{changed')
            self.assertIn(aliases[0], runner.artifact_files(output))

    def test_full_stopped_census_malformed_closure_and_missing_manifest_recover_without_launch(self):
        with tempfile.TemporaryDirectory(prefix='common-cost-stopped-census-control-') as temp:
            output = Path(temp) / 'allocation'; allocation = runner.prepare(output)
            cells = allocation['cells']; first = output / 'cells' / cells[0]['id']
            runner.write(first / 'before.json', {'cell': cells[0], 'constructed_no_process': True})
            runner.write(first / 'after.json', {'cell': cells[0], 'status': 'unknown', 'decision': 'unknown',
                         'certificate_valid': None, 'resources': None, 'constructed_no_process': True})
            second = output / 'cells' / cells[1]['id']; runner.write(second / 'before.json', {'constructed_no_process': True})
            third = output / 'cells' / cells[2]['id']; (third / 'after.json').write_bytes(b'{partial')
            with patch.object(runner, 'owned_process', side_effect=AssertionError('finalizer must not launch')):
                result = runner.finalize(output)
                self.assertEqual(len(result['cells']), 1650)
                self.assertEqual(result['cells'][0]['status'], 'unknown')
                self.assertEqual(result['cells'][1]['status'], 'stopped_without_closing_receipt')
                self.assertEqual(result['cells'][2]['failure_kind'], 'malformed_or_unbound_closing_receipt')
                self.assertEqual(sum(r['status'] == 'not_started' for r in result['cells']), 1647)
                original = (first / 'after.json').read_bytes()
                (output / 'manifest.json').unlink()
                self.assertEqual(runner.finalize(output), result)
                self.assertTrue((output / 'manifest.json').is_file())
                self.assertEqual((first / 'after.json').read_bytes(), original)

    def test_paired_costs_require_five_certified_agreeing_repeats_and_quarantine_contradictions(self):
        protocol, cells = runner.verify_package(); rows = [{'cell': c, 'status': 'not_started', 'decision': None,
                                                          'certificate_valid': None, 'resources': None} for c in cells]
        profile = protocol['profiles'][0]['id']
        for row in rows:
            if row['cell']['profile_id'] == profile:
                row.update(status='certified', decision='supported', certificate_valid=True,
                           solver_logical_cap_nonbinding=True,
                           resources={'cpu_total_ns': 100, 'outer_wall_ns': 200, 'peak_rss_bytes': 300})
        methods = [m['id'] for m in protocol['methods']]
        summary = runner.summarize(rows, methods)
        self.assertEqual(summary['allocated_cells'], 1650)
        self.assertTrue(all(v['complete_same_decision_certified_profile_count'] == 1 for v in summary['paired_costs'].values()))
        next(r for r in rows if r['cell']['profile_id'] == profile and r['cell']['repeat'] == 1)['decision'] = 'unsupported'
        summary = runner.summarize(rows, methods)
        self.assertEqual(summary['certified_contradictions'][0]['profile_id'], profile)
        self.assertTrue(all(v['complete_same_decision_certified_profile_count'] == 0 for v in summary['paired_costs'].values()))


@unittest.skipUnless(sys.platform == 'linux', 'Actual cap/wait4 controls require the declared Linux platform')
class CommonCostLinuxControls(unittest.TestCase):
    def generic(self, program, caps=None):
        caps = caps or {'cpu_soft_seconds': 1, 'cpu_hard_seconds': 2, 'wall_seconds': 2,
                        'address_space_bytes': 134217728}
        with tempfile.TemporaryDirectory(prefix='common-cost-generic-child-control-') as temp:
            folder = Path(temp)
            result = runner.owned_process([sys.executable, '-S', '-P', '-B', '-c', program],
                {'PYTHONHASHSEED': '7'}, folder, caps)
            return result, (folder / 'stdout.bin').read_bytes(), (folder / 'stderr.bin').read_bytes()

    def test_caps_applied_before_body_and_actual_wait4_costs_include_failed_children(self):
        result, stdout, _ = self.generic("import json,resource,signal;print(json.dumps({'cpu':resource.getrlimit(resource.RLIMIT_CPU),'as':resource.getrlimit(resource.RLIMIT_AS),'wall':signal.getitimer(signal.ITIMER_REAL)[0]}));raise SystemExit(3)")
        observed = json.loads(stdout)
        self.assertEqual(observed['cpu'], [1, 2]); self.assertEqual(observed['as'], [134217728] * 2)
        self.assertGreater(observed['wall'], 0); self.assertLessEqual(observed['wall'], 2)
        self.assertEqual(result['returncode'], 3)
        self.assertGreater(result['cpu_total_ns'], 0); self.assertGreater(result['peak_rss_bytes'], 0)
        self.assertTrue(result['owned_group_cleanup_requested_before_terminal_reap'])

    def test_wall_and_cpu_exhaustion_are_measured_after_terminal_reap(self):
        caps = {'cpu_soft_seconds': 1, 'cpu_hard_seconds': 2, 'wall_seconds': 0.1, 'address_space_bytes': 134217728}
        wall, _, _ = self.generic('import time;time.sleep(5)', caps)
        self.assertIn(wall['returncode'], [-signal.SIGALRM, -signal.SIGKILL])
        self.assertGreater(wall['peak_rss_bytes'], 0)
        cpu, _, _ = self.generic('while True: pass')
        self.assertIn(cpu['returncode'], [-signal.SIGXCPU, -signal.SIGKILL])
        self.assertGreaterEqual(cpu['cpu_total_ns'], 900000000)

    def test_address_space_exhaustion_retains_actual_cpu_and_peak_rss(self):
        result, _, _ = self.generic('buffer=bytearray(256*1024*1024)')
        self.assertNotEqual(result['returncode'], 0)
        self.assertGreater(result['peak_rss_bytes'], 0); self.assertGreater(result['cpu_total_ns'], 0)

    def test_scrubbed_nonisolated_children_honor_the_same_hash_seed(self):
        values = [self.generic("print(hash('common-cost-hash-seed-probe'))")[1] for _ in range(3)]
        self.assertEqual(len(set(values)), 1)

    def test_constructed_common_worker_checker_acceptance_and_rejection(self):
        # These tiny stubs are software controls, not preserved-method attempts.
        for accepted in [True, False]:
            with self.subTest(accepted=accepted), tempfile.TemporaryDirectory(prefix='common-cost-stub-worker-control-') as temp:
                folder = Path(temp); snapshot = folder / 'snapshot'
                source = snapshot / 'source/interoperability'; source.mkdir(parents=True)
                stubs = {'__init__.py': '', 'stub_solver.py':
                    "def evaluate(profile, now, budget):\n"
                    "    return {'decision': 'unsupported', 'certificate': {'constructed': True}, "
                    "'stats': {'work_units': 1, 'budget': budget}}\n",
                    'direct_goal_pruned_v2.py':
                    f"def check_certificate(profile, result, now):\n    return {accepted}\n",
                    'refinement_oracle.py': 'CHECK_BUDGET = 2000000\n'}
                sources = []
                for name, body in stubs.items():
                    path = source / name; path.write_text(body, encoding='utf-8')
                    sources.append(dict(path=path.relative_to(snapshot).as_posix(), **runner.identity(path.read_bytes())))
                profile = snapshot / 'profile.json'
                runner.write(profile, {'id': 'constructed-profile', 'schema_version': 'recipe-continuation/1'})
                caps = {'cpu_soft_seconds': 5, 'cpu_hard_seconds': 6, 'wall_seconds': 10,
                        'address_space_bytes': 536870912, 'rss_hard_cap_claimed': False,
                        'solver_logical_allowance': 100000000}
                cell = {'id': 'constructed-worker-control', 'profile_id': 'constructed-profile', 'hash_seed': 7}
                job = {'cell': cell, 'snapshot_root': str(snapshot), 'sources': sources,
                       'profile': dict(path='profile.json', **runner.identity(profile.read_bytes())),
                       'method': {'module': 'interoperability.stub_solver'},
                       'checker': {'preserved_fixed_internal_budget': 2000000}, 'caps': caps, 'evaluation_clock': 100}
                runner.write(folder / 'job.json', job)
                result = runner.owned_process([sys.executable, '-S', '-P', '-B', str(runner.WORKER),
                    '--job', str(folder / 'job.json')], {'PYTHONHASHSEED': '7'}, folder, caps)
                self.assertEqual(result['returncode'], 0)
                reply = runner.read(folder / 'reply.json')
                self.assertEqual(reply['status'], 'certified' if accepted else 'failure')
                self.assertIs(reply['certificate_valid'], accepted)
                self.assertEqual(reply['decision'], 'unsupported')
                if not accepted:
                    self.assertEqual(reply['failure_kind'], 'checker_rejected_or_internal_soft_cap')
                self.assertIn('independent_checker_import_and_check', reply['phase_resources'])
                self.assertTrue((folder / 'solver-result.json').is_file())
                self.assertGreater(result['cpu_total_ns'], 0); self.assertGreater(result['peak_rss_bytes'], 0)


if __name__ == '__main__':
    unittest.main()
