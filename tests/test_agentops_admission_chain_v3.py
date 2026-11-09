"""Inert launch-gating regressions; no WSL or application process is created."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('admission_chain_v3', ROOT / 'scripts/run_agentops_admission_chain_v3.py')
chain = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chain)


class ChainGatingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'workspace'
        self.scripts = self.root / 'scripts'
        self.scripts.mkdir(parents=True)
        self.group = self.root / 'runs/agentops-admission-live-v1'
        self.group.mkdir(parents=True)
        (self.group / 'stage-manifest.json').write_text(json.dumps({
            'linux_workspace': str(self.root.resolve()), 'reuse_root': '/owned/reused'}), encoding='utf-8')
        for name in ('run_agentops_admission_chain_v3.py', 'execute_agentops_admission_phase_v3.py',
                     'export_agentops_admission_v3.py'):
            (self.scripts / name).write_bytes(b'# inert captured test source\n')
        self.export = self.base / 'export'

    def execute(self, codes):
        calls, exports = [], []

        def popen(argv, **kwargs):
            phase = argv[-1]
            calls.append(phase)
            if phase == 'prepare' and codes.get(phase, 0) == 0:
                folder = self.group / 'preparation'
                folder.mkdir()
                (folder / 'plan.json').write_text('{}', encoding='utf-8')
            kwargs['stdout'].write(('inert ' + phase + '\n').encode())
            self.assertEqual(kwargs['cwd'], self.root.resolve())

            class Child:
                pid = 100 + len(calls)

                def wait(self):
                    return codes.get(phase, 0)

            return Child()

        def export(argv, **kwargs):
            exports.append(argv)
            report = json.loads((self.group / 'phase-chain/result.json').read_bytes())
            self.assertEqual([r['phase'] for r in report['commands']], calls)
            # Stable evidence must exist before export begins.
            for phase in calls:
                self.assertTrue((self.group / f'phase-chain/{phase}.receipt.json').exists())

            class Completed:
                returncode = 0

            return Completed()

        with patch.object(chain, '__file__', str(self.scripts / 'run_agentops_admission_chain_v3.py')), \
             patch.object(chain.subprocess, 'Popen', side_effect=popen), \
             patch.object(chain.subprocess, 'run', side_effect=export), patch('builtins.print'):
            code = chain.main(['--workspace', str(self.root), '--export-output', str(self.export)])
        report = json.loads((self.group / 'phase-chain/result.json').read_bytes())
        return code, calls, exports, report

    def test_software_failure_never_reaches_preparation_or_launch(self):
        code, calls, exports, report = self.execute({'software': 1})
        self.assertEqual((code, calls, exports), (1, ['software'], []))
        self.assertEqual(report['unexecuted_phases'], ['prepare', 'preflight', 'launch', 'after'])

    def test_preparation_failure_never_reaches_preflight_or_launch(self):
        code, calls, exports, report = self.execute({'prepare': 2})
        self.assertEqual((code, calls, exports), (1, ['software', 'prepare'], []))
        self.assertEqual(report['status'], 'phase_failed')

    def test_failed_preflight_exports_record_but_cannot_launch(self):
        code, calls, exports, report = self.execute({'preflight': 1})
        self.assertEqual(code, 1)
        self.assertEqual(calls, ['software', 'prepare', 'preflight'])
        self.assertEqual(len(exports), 1)
        self.assertEqual(report['unexecuted_phases'], ['launch', 'after'])

    def test_failed_launch_still_gets_after_inspection_and_stable_export(self):
        code, calls, exports, report = self.execute({'launch': 1})
        self.assertEqual(code, 1)
        self.assertEqual(calls, ['software', 'prepare', 'preflight', 'launch', 'after'])
        self.assertEqual(len(exports), 1)
        self.assertEqual(report['status'], 'phase_failed')

    def test_successful_phases_do_not_claim_application_success(self):
        code, calls, exports, report = self.execute({})
        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 5)
        self.assertEqual(len(exports), 1)
        self.assertEqual(report['status'], 'phases_passed')
        self.assertIsInstance(report['application_success'], str)
        self.assertIn('not live admission acceptance', report['application_success'])
        self.assertNotIn('strict_success', report)

    def test_existing_chain_or_export_cannot_start_another_process(self):
        output = self.group / 'phase-chain'
        output.mkdir()
        with patch.object(chain, '__file__', str(self.scripts / 'run_agentops_admission_chain_v3.py')), \
             patch.object(chain.subprocess, 'Popen', side_effect=AssertionError('unexpected process')):
            with self.assertRaises(FileExistsError):
                chain.main(['--workspace', str(self.root), '--export-output', str(self.export)])
            self.export.mkdir()
            with self.assertRaises(FileExistsError):
                chain.main(['--workspace', str(self.root), '--export-output', str(self.export)])

    def test_overlapping_export_is_rejected_before_any_phase(self):
        with patch.object(chain.subprocess, 'Popen', side_effect=AssertionError('unexpected process')):
            for destination in (self.root, self.root / 'export', self.base):
                with self.subTest(destination=destination), self.assertRaises(ValueError):
                    chain.main(['--workspace', str(self.root), '--export-output', str(destination)])
        self.assertFalse((self.group / 'phase-chain').exists())


if __name__ == '__main__':
    unittest.main()
