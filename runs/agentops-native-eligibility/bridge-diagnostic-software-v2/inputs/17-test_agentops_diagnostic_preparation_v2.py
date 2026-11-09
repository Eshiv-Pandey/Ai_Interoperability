"""Pre-seal absence guards for the unexecuted v11 -> v12 supersession."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import prepare_agentops_bridge_diagnostic_v2 as preparation


class AbsenceGuards(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='diagnostic-preseal-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.replica = self.root / 'native'
        self.replica.mkdir()
        receipt = self.root / preparation.PRIOR / 'result.json'
        receipt.parent.mkdir(parents=True)
        receipt.write_text(json.dumps({'linux_workspace': str(self.replica)}), encoding='utf-8')
        self.addCleanup(patch.stopall)
        patch.object(preparation, 'ROOT', self.root).start()
        patch.object(preparation.sys, 'platform', 'linux').start()

    def test_absent_outputs_and_cases_record_exact_paths(self):
        result = preparation.require_no_prior_attempt()
        self.assertTrue(result['parent_groups_absent'])
        self.assertTrue(result['native_cases_absent'])
        self.assertEqual(result['parent_group_paths'], preparation.GROUP_PATHS)
        self.assertEqual(result['native_case_paths'], [preparation.design.CASE_PREFIX + name
                                                     for name in ('N11', 'B6', 'B7')])
        self.assertEqual(result['application_requests'], 0)

    def test_either_parent_output_blocks_supersession(self):
        for name in preparation.GROUP_PATHS:
            with self.subTest(path=name):
                path = self.root / name
                path.mkdir()
                with self.assertRaisesRegex(FileExistsError, 'group output'):
                    preparation.require_no_prior_attempt()
                path.rmdir()

    def test_any_consumed_native_case_blocks_seal(self):
        for name in preparation.design.CASES:
            with self.subTest(case=name):
                path = self.replica / (preparation.design.CASE_PREFIX + name)
                path.mkdir(parents=True)
                with self.assertRaisesRegex(FileExistsError, 'native case'):
                    preparation.require_no_prior_attempt()
                path.rmdir()

    def test_unavailable_native_workspace_is_not_absence(self):
        self.replica.rmdir()
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            preparation.require_no_prior_attempt()

    def test_parent_windows_path_is_not_native_observation(self):
        with patch.object(preparation.sys, 'platform', 'win32'):
            with self.assertRaisesRegex(ValueError, 'retained Linux'):
                preparation.require_no_prior_attempt()

    def test_inventory_binds_superseded_seal_and_exact_test_streams(self):
        receipt = {'commands': [{'streams': [{'path': 'runs/example/stderr.bin'}]}]}
        actual = preparation.prerequisite_paths('runs/example/result.json', receipt)
        self.assertIn(preparation.SUPERSEDED_SEAL, actual)
        self.assertEqual(actual[-1], 'runs/example/stderr.bin')
        self.assertEqual(len(actual), len(set(actual)))


if __name__ == '__main__':
    unittest.main()
