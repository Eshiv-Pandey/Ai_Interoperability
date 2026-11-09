"""Inert export regressions; no archived code, application or service executes."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import export_agentops_diagnostic_workspace_v1 as diagnostic
import export_agentops_workspace_v7 as previous
from run_agentops_linux_workspace_v5 import record


class DiagnosticExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'workspace'
        self.root.mkdir()
        self.case = 'runs/agentops-http-control/bridge-diagnostic-v1-B6'

    def write(self, name, raw):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return path

    def write_json(self, name, value):
        return self.write(name, (json.dumps(value) + '\n').encode('utf-8'))

    @staticmethod
    def named_record(name, raw=b'captured'):
        return {'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

    def report(self, rows, *, path=None, **extra):
        return self.write_json(path or self.case + '/diagnostic-check.json',
                               {'schema_version': 'agentops-shutdown-diagnostic-check/1',
                                'case_id': 'B6', 'files': rows, **extra})

    def export(self, label='new', inputs=()):
        target = self.base / label
        return diagnostic.export_evidence(self.root, target, list(inputs)), target

    def test_actual_case_relative_report_exports_without_false_missing_reference(self):
        body = self.write(self.case + '/service/shutdown-diagnostics/teardown-stacks.txt', b'captured')
        self.report([record(body, self.root / self.case)])
        report_before = (self.root / self.case / 'diagnostic-check.json').read_bytes()
        old = previous.export_evidence(self.root, self.base / 'old', [])
        self.assertTrue(old['reference_failures'], 'Regression requires v7 path-base failure')
        new, exported = self.export()
        self.assertEqual(new['reference_failures'], [])
        self.assertEqual((exported / body.relative_to(self.root)).read_bytes(), b'captured')
        self.assertEqual((exported / self.case / 'diagnostic-check.json').read_bytes(), report_before)
        self.assertEqual((self.root / self.case / 'diagnostic-check.json').read_bytes(), report_before)

    def test_all_three_exact_case_contexts_rebase(self):
        for case_id in ('N11', 'B6', 'B7'):
            case = 'runs/agentops-http-control/bridge-diagnostic-v1-' + case_id
            self.write(case + '/result.json', b'captured')
            self.write_json(case + '/diagnostic-check.json', {
                'schema_version': 'agentops-shutdown-diagnostic-check/1', 'case_id': case_id,
                'files': [self.named_record('result.json')]})
        report, _ = self.export()
        self.assertEqual(report['reference_failures'], [])

    def test_ordinary_nested_and_top_level_workspace_references_are_not_rebased(self):
        body = self.write(self.case + '/service/body.bin', b'captured')
        source = self.write('external/source.py', b'# unchanged workspace ref\n')
        self.report([record(body, self.root / self.case)],
                    source=record(source, self.root), nested={'again': [record(source, self.root)]})
        report, exported = self.export()
        self.assertEqual(report['reference_failures'], [])
        self.assertEqual((exported / 'external/source.py').read_bytes(), source.read_bytes())
        self.assertFalse((exported / self.case / 'external/source.py').exists())

    def test_same_schema_outside_exact_filename_remains_workspace_relative(self):
        source = self.write('external/source.py', b'captured')
        self.report([record(source, self.root)], path=self.case + '/other-report.json')
        report, exported = self.export()
        self.assertEqual(report['reference_failures'], [])
        self.assertTrue((exported / 'external/source.py').is_file())

    def test_same_schema_outside_exact_case_prefix_remains_workspace_relative(self):
        source = self.write('external/source.py', b'captured')
        self.report([record(source, self.root)], path='runs/unrelated/diagnostic-check.json')
        report, _ = self.export()
        self.assertEqual(report['reference_failures'], [])

    def test_wrong_schema_at_exact_filename_remains_workspace_relative(self):
        source = self.write('external/source.py', b'captured')
        self.report([record(source, self.root)], schema_version='ordinary-workspace-report/1')
        report, _ = self.export()
        self.assertEqual(report['reference_failures'], [])

    def test_case_identity_mismatch_is_retained_failure(self):
        self.write(self.case + '/result.json', b'captured')
        self.report([self.named_record('result.json')], case_id='B7')
        report, _ = self.export()
        self.assertTrue(any('case identity mismatch' in value for value in report['reference_failures']))

    def test_absolute_traversal_and_noncanonical_paths_are_rejected(self):
        paths = ['/etc/fixture.py', '../B7/result.json', 'service/../../outside',
                 'C:/fixture.py', 'service\\body.bin', './result.json', 'service//body.bin', '']
        for index, name in enumerate(paths):
            with self.subTest(path=name):
                self.report([self.named_record(name)])
                report, _ = self.export('invalid-' + str(index))
                self.assertTrue(any('Invalid case-relative evidence path' in value
                                    for value in report['reference_failures']))

    def test_missing_reference_is_reported_with_rebased_path(self):
        self.report([self.named_record('service/missing.bin')])
        report, _ = self.export()
        self.assertTrue(any(self.case + '/service/missing.bin' in value
                            for value in report['reference_failures']))

    def test_hash_and_byte_mismatches_are_retained_without_rewriting_report(self):
        self.write(self.case + '/service/body.bin', b'captured')
        for index, mutation in enumerate(({'bytes': 99}, {'sha256': '0' * 64})):
            with self.subTest(mutation=mutation):
                row = {**self.named_record('service/body.bin'), **mutation}
                source = self.report([row])
                before = source.read_bytes()
                report, exported = self.export('mismatch-' + str(index))
                self.assertTrue(any('Missing/changed referenced bytes' in value
                                    for value in report['reference_failures']))
                self.assertEqual((exported / self.case / 'diagnostic-check.json').read_bytes(), before)

    def test_malformed_diagnostic_file_records_are_not_silently_ignored(self):
        bad = self.named_record('service/body.bin')
        bad['bytes'] = True
        self.report([bad])
        report, _ = self.export()
        self.assertTrue(any('Malformed case-relative file record' in value
                            for value in report['reference_failures']))

    def test_v7_general_export_behavior_is_unchanged_without_diagnostic_context(self):
        source = self.write('external/source.py', b'# source\n')
        native = self.write('external/native.so', b'inert native bytes')
        supplemental = self.write('external/runtime/google/adk/a2a/extra.py', b'# extra\n')
        initial = self.write('src/initial.py', b'# explicit input\n')
        self.write_json('runs/ordinary.json', {'files': [record(source, self.root)]})
        self.write_json('runs/inspection.stdout.bin', {
            'fcntl_extension': {'path': str(native), 'sha256': hashlib.sha256(native.read_bytes()).hexdigest()},
            'schema_version': 'agentops-installed-runtime-inspection/6',
            'packages': [{'name': 'google-adk', 'location': 'external/runtime'}]})
        self.write('runs/not-json.stdout.bin', b'opaque console output\n')
        inputs = [record(initial, self.root)]
        old = previous.export_evidence(self.root, self.base / 'old', inputs)
        new, exported = self.export(inputs=inputs)
        old.pop('export_root')
        compared = copy.deepcopy(new)
        compared.pop('export_root')
        self.assertEqual(compared, old)
        self.assertTrue((exported / supplemental.relative_to(self.root)).exists())

    def test_export_size_guard_and_exclusive_destination_are_preserved(self):
        self.write('runs/body.bin', b'12345')
        with patch.object(diagnostic, 'MAX_EXPORT_BYTES', 4), self.assertRaises(ValueError):
            self.export('limited')
        self.assertFalse((self.base / 'limited').exists())
        self.export()
        with self.assertRaises(FileExistsError):
            self.export()


if __name__ == '__main__':
    unittest.main()
