"""Reject stale or incomplete preparation evidence without starting AgentOps."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import agentops_protocol_preparation_v2 as contract
import check_agentops_protocol_export_v1 as export_checker
import verify_agentops_protocol_preparation_v1 as verifier


class PreparationReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='protocol-preparation-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / 'preparation'
        self.directory.mkdir()
        self.paths = ['source.py', 'tests.py']
        for name in self.paths:
            (self.root / name).write_text('# exact constructed input\n', encoding='utf-8')
        self.enterContext(patch.object(contract, 'PREPARATION_RELATIVE', 'preparation'))
        self.enterContext(patch.object(contract, 'SOFTWARE_INPUT_PATHS', self.paths))
        self.receipt = {
            'schema_version': 'agentops-protocol-software-preparation/2',
            'argv': [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests',
                     '-p', 'test_agentops_protocol*.py', '-v'],
            'started_at_utc': '2026-10-27T00:00:00+00:00',
            'finished_at_utc': '2026-10-27T00:00:01+00:00',
            'returncode': 0, 'inputs_unchanged': True,
            'inputs': [contract.file_record(self.root, name) for name in self.paths],
            'application_execution_performed': False,
        }
        (self.directory / 'tests.stdout.bin').write_bytes(b'')
        (self.directory / 'tests.stderr.bin').write_bytes(b'Ran 23 tests in 0.125s\n\nOK\n')
        self.write_receipt()

    def write_receipt(self):
        (self.directory / 'result.json').write_text(json.dumps(self.receipt), encoding='utf-8')

    def test_current_success_reports_actual_test_count(self):
        self.assertEqual(verifier.verify_software_preparation(self.root), 23)

    def test_omitted_or_reordered_tested_input_is_rejected(self):
        original = copy.deepcopy(self.receipt['inputs'])
        for rows in (original[:-1], list(reversed(original))):
            with self.subTest(rows=rows):
                self.receipt['inputs'] = rows
                self.write_receipt()
                with self.assertRaisesRegex(ValueError, 'path set/order'):
                    verifier.verify_software_preparation(self.root)

    def test_success_for_stale_source_bytes_is_rejected(self):
        (self.root / 'source.py').write_text('# changed after tests\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Changed sealed file'):
            verifier.verify_software_preparation(self.root)

    def test_failed_changed_or_application_run_is_rejected(self):
        for key, value in [('returncode', 1), ('returncode', False),
                           ('inputs_unchanged', False), ('application_execution_performed', True)]:
            with self.subTest(key=key, value=value):
                original = self.receipt[key]
                self.receipt[key] = value
                self.write_receipt()
                with self.assertRaisesRegex(ValueError, 'Successful unchanged'):
                    verifier.verify_software_preparation(self.root)
                self.receipt[key] = original

    def test_narrower_discovery_command_is_rejected(self):
        self.receipt['argv'][-2] = 'test_agentops_protocol_v1.py'
        self.write_receipt()
        with self.assertRaisesRegex(ValueError, 'discovery command'):
            verifier.verify_software_preparation(self.root)

    def test_missing_or_nonpassing_test_summary_is_rejected(self):
        for stderr in (b'OK\n', b'Ran 0 tests in 0.000s\n\nOK\n',
                       b'Ran 23 tests in 0.1s\n\nFAILED (errors=1)\n',
                       b'Ran 23 tests in 0.1s\n\nOK\nlate failure\n'):
            with self.subTest(stderr=stderr):
                (self.directory / 'tests.stderr.bin').write_bytes(stderr)
                with self.assertRaisesRegex(ValueError, 'test summary'):
                    verifier.verify_software_preparation(self.root)


class PreparationSealTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='protocol-seal-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.prior = {'linux_workspace': '/var/tmp/agentops-research-v7-constructed'}
        for name in contract.ARTIFACT_PATHS:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'constructed artifact\n')
        self.modules = [{'module': name, 'bytes': 1, 'sha256': '0' * 64}
                        for name in sorted(contract.REQUIRED_MODULES)]
        inspection = {
            'schema_version': 'agentops-protocol-runtime-sources/1',
            'replica': self.prior['linux_workspace'],
            'python': self.prior['linux_workspace'] + '/external/runtime-agentops-linux-v7/venv/bin/python',
            'site_packages': self.prior['linux_workspace'] + '/external/runtime-agentops-linux-v7/venv/lib/python3.13/site-packages',
            'source_trees': list(contract.SOURCE_TREES), 'source_files': list(contract.SOURCE_FILES),
            'modules': self.modules, 'application_imports': 0, 'application_requests': 0, 'live_model_calls': 0,
        }
        (self.root / contract.INSPECTION_RELATIVE).write_text(json.dumps(inspection), encoding='utf-8')
        (self.root / contract.PRIOR_RELATIVE / 'result.json').write_text(json.dumps(self.prior), encoding='utf-8')
        self.seal = {
            'schema_version': contract.SCHEMA, 'prepared_at_utc': '2026-10-27T00:00:00+00:00',
            'launch_inputs': [contract.file_record(self.root, name) for name in contract.LAUNCH_PATHS],
            'prerequisites': [contract.file_record(self.root, name) for name in contract.PREREQUISITE_PATHS],
            'artifacts': [contract.file_record(self.root, name) for name in contract.ARTIFACT_PATHS],
            'runtime_sources': self.modules,
            'prior_result': contract.file_record(self.root, contract.PRIOR_RELATIVE + '/result.json'),
            'prior_export': contract.file_record(self.root, contract.PRIOR_RELATIVE + '/export-manifest.json'),
            'prior_parent_check': contract.file_record(self.root, contract.PARENT_CHECK_RELATIVE),
            'preflight_manifest': contract.file_record(self.root, contract.PREFLIGHT_RELATIVE),
            'runtime_source_inspection': contract.file_record(self.root, contract.INSPECTION_RELATIVE),
            'application_execution_performed': False, 'live_model_calls': 0,
            'research_gate_credit_added': 0, 'scope': 'Constructed contract test only',
        }

    def test_complete_contract_is_accepted(self):
        self.assertEqual(contract.validate_seal(self.root, self.seal, self.prior)['modules'], self.modules)

    def test_omitted_launch_prerequisite_or_artifact_is_rejected(self):
        for field in ('launch_inputs', 'prerequisites', 'artifacts'):
            with self.subTest(field=field):
                seal = copy.deepcopy(self.seal)
                seal[field].pop()
                with self.assertRaisesRegex(ValueError, 'path set/order'):
                    contract.validate_seal(self.root, seal, self.prior)

    def test_omitted_runtime_module_is_rejected(self):
        seal = copy.deepcopy(self.seal)
        seal['runtime_sources'].pop()
        with self.assertRaisesRegex(ValueError, 'Runtime sources differ'):
            contract.validate_seal(self.root, seal, self.prior)

    def test_both_checkers_reject_omitted_launch_before_runtime_checking(self):
        seal = copy.deepcopy(self.seal)
        seal['launch_inputs'].pop()
        seal_path = self.root / contract.SEAL_RELATIVE
        seal_path.write_text(json.dumps(seal), encoding='utf-8')
        prior_path = self.root / contract.PRIOR_RELATIVE
        with patch.object(verifier, 'ROOT', self.root), patch.object(verifier.resume, 'PRIOR', prior_path), \
                patch.object(verifier.prior, 'check') as check_prior:
            with self.assertRaisesRegex(ValueError, 'path set/order'):
                verifier.check()
            check_prior.assert_not_called()
        with patch.object(export_checker, 'ROOT', self.root), patch.object(export_checker, 'PRIOR', prior_path), \
                patch.object(export_checker, 'SEAL', seal_path), patch.object(export_checker.prior, 'check') as check_prior:
            with self.assertRaisesRegex(ValueError, 'path set/order'):
                export_checker.check(self.root / 'unexecuted')
            check_prior.assert_not_called()


if __name__ == '__main__':
    unittest.main()
