"""Inert local source copies; no application, imported source, or signal."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import agentops_diagnostic_sources_v1 as collector


class DiagnosticSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.workspace = self.base / 'workspace'
        self.case = self.workspace / 'runs/case'
        self.diag = self.case / 'service/shutdown-diagnostics'
        self.diag.mkdir(parents=True)
        self.sources = self.workspace / 'scripts'
        self.sources.mkdir()
        (self.diag / 'teardown-stacks.txt').write_bytes(b'')

    def source(self, name='source.py', raw=b'raise RuntimeError("must never import")\n'):
        path = self.sources / name
        path.write_bytes(raw)
        return path

    def lifecycle(self, names):
        frames = [{'file': str(name), 'line': 1, 'function': 'inert'} for name in names]
        event = {'schema_version': 'agentops-shutdown-event/2', 'sequence': 1, 'pid': 123,
                 'monotonic_ns': 1, 'at_utc': '2026-10-28T00:00:00+00:00',
                 'phase': 'coroutine_finished', 'tasks': [
                     {'current': True, 'done': False, 'cancelling': 0, 'stack': frames}],
                 'threads': []}
        (self.diag / 'lifecycle.jsonl').write_text(json.dumps(event) + '\n', encoding='utf-8')

    def capture(self):
        return collector.capture_sources(self.case, self.workspace)

    def test_utf8_filename_and_source_bytes_are_copied_exactly_without_import(self):
        raw = '# नमस्ते\r\nraise RuntimeError("must never import")\n'.encode('utf-8')
        source = self.source('नमूना.py', raw)
        self.lifecycle([source])
        report = self.capture()
        self.assertEqual(report['status'], 'captured')
        self.assertFalse(report['preexecution_module_fidelity'])
        row = report['sources'][0]
        self.assertEqual(row['original_linux_path'], str(source))
        self.assertEqual(row['original_workspace_relative_path'], 'scripts/नमूना.py')
        self.assertEqual((self.workspace / row['snapshot']['path']).read_bytes(), raw)
        self.assertEqual(row['snapshot']['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(source.read_bytes(), raw)

    def test_nonutf8_source_bytes_are_preserved_without_decoding(self):
        raw = b'# invalid UTF8 \xff\x00\r\n'
        source = self.source(raw=raw)
        self.lifecycle([source])
        row = self.capture()['sources'][0]
        self.assertEqual((self.workspace / row['snapshot']['path']).read_bytes(), raw)

    def test_trace_and_lifecycle_references_share_one_copy_with_all_origins(self):
        source = self.source()
        self.lifecycle([source, source])
        (self.diag / 'teardown-stacks.txt').write_text(
            f'Timeout (0:00:05)!\nThread 0x1:\n  File "{source}", line 1 in inert\n', encoding='utf-8')
        report = self.capture()
        self.assertEqual(report['copied_sources'], 1)
        self.assertEqual(len(report['sources'][0]['origins']), 3)

    def test_traversal_is_a_gap_and_outside_source_is_not_read(self):
        outside = self.base / 'outside.py'
        outside.write_bytes(b'outside sentinel')
        traversal = self.workspace / '..' / 'outside.py'
        self.lifecycle([traversal])
        report = self.capture()
        self.assertEqual(report['copied_sources'], 0)
        self.assertEqual(report['closure_gaps'][0]['reason'], 'nonabsolute_or_traversal_frame_path')
        self.assertEqual(outside.read_bytes(), b'outside sentinel')

    def test_absolute_outside_source_is_a_gap(self):
        outside = self.base / 'outside.py'
        outside.write_bytes(b'outside sentinel')
        self.lifecycle([outside])
        report = self.capture()
        self.assertEqual(report['copied_sources'], 0)
        self.assertEqual(report['closure_gaps'][0]['reason'], 'source_outside_workspace')

    def test_symlink_resolution_outside_workspace_is_rejected_before_read(self):
        source = self.source('alias.py')
        outside = self.base / 'outside.py'
        outside.write_bytes(b'outside sentinel')
        self.lifecycle([source])
        original = Path.resolve

        def resolved(path, *args, **kwargs):
            return outside if path == source else original(path, *args, **kwargs)

        with patch.object(Path, 'resolve', resolved):
            report = self.capture()
        self.assertEqual(report['copied_sources'], 0)
        self.assertEqual(report['closure_gaps'][0]['reason'], 'source_symlink_outside_workspace')

    def test_actual_outside_symlink_is_rejected(self):
        outside = self.base / 'outside.py'
        outside.write_bytes(b'outside sentinel')
        link = self.sources / 'alias.py'
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError) as error:
            self.skipTest('Host cannot create test symlinks: ' + type(error).__name__)
        self.lifecycle([link])
        report = self.capture()
        self.assertEqual(report['copied_sources'], 0)
        self.assertEqual(report['closure_gaps'][0]['reason'], 'source_symlink_outside_workspace')

    def test_missing_and_pseudo_frames_are_explicit_gaps(self):
        self.lifecycle([self.sources / 'missing.py', '<frozen importlib._bootstrap>', 'relative.py'])
        report = self.capture()
        self.assertEqual(report['copied_sources'], 0)
        self.assertEqual(len(report['closure_gaps']), 3)
        self.assertTrue(any(row.get('error_type') == 'FileNotFoundError' for row in report['closure_gaps']))
        self.assertFalse(report['recorded_frame_source_closure'])

    def test_non_python_frame_is_not_copied(self):
        source = self.source('native.so', b'not Python')
        self.lifecycle([source])
        report = self.capture()
        self.assertEqual(report['closure_gaps'][0]['reason'], 'not_python_source_path')

    def test_per_file_limit_preserves_other_eligible_sources(self):
        small, large = self.source('a.py', b'abcd'), self.source('b.py', b'abcde')
        self.lifecycle([small, large])
        with patch.object(collector, 'MAX_FILE_BYTES', 4):
            report = self.capture()
        self.assertEqual(report['copied_bytes'], 4)
        self.assertEqual(report['copied_sources'], 1)
        self.assertEqual(report['closure_gaps'][0]['reason'], 'source_byte_limit')

    def test_total_limit_never_writes_excess_source_bytes(self):
        first, second = self.source('a.py', b'abcd'), self.source('b.py', b'efgh')
        self.lifecycle([first, second])
        with patch.object(collector, 'MAX_TOTAL_BYTES', 6):
            report = self.capture()
        self.assertEqual(report['copied_bytes'], 4)
        self.assertEqual(report['closure_gaps'][0]['reason'], 'total_source_byte_limit')
        self.assertEqual(sum(p.stat().st_size for p in (self.case / 'diagnostic-sources').glob('*.py')), 4)

    def test_existing_capture_is_never_overwritten(self):
        self.lifecycle([self.source()])
        self.capture()
        result = self.case / 'diagnostic-sources/result.json'
        before = result.read_bytes()
        with self.assertRaises(FileExistsError):
            self.capture()
        self.assertEqual(result.read_bytes(), before)

    def test_case_directory_outside_workspace_rejected_before_output(self):
        outside_case = self.base / 'outside-case'
        outside_case.mkdir()
        with self.assertRaises(ValueError):
            collector.capture_sources(outside_case, self.workspace)
        self.assertFalse((outside_case / 'diagnostic-sources').exists())

    def test_missing_inputs_and_malformed_trace_are_retained_as_gaps(self):
        (self.diag / 'teardown-stacks.txt').write_text('  File incomplete frame\n', encoding='utf-8')
        report = self.capture()
        reasons = [row['reason'] for row in report['closure_gaps']]
        self.assertIn('diagnostic_input_unavailable', reasons)
        self.assertIn('unparsed_trace_frame', reasons)

    def test_bad_record_does_not_erase_later_valid_frame(self):
        self.lifecycle([self.source()])
        path = self.diag / 'lifecycle.jsonl'
        path.write_text('{not JSON}\n' + path.read_text(), encoding='utf-8')
        report = self.capture()
        self.assertEqual(report['copied_sources'], 1)
        self.assertEqual(report['closure_gaps'][0]['reason'], 'unparsed_lifecycle_record')


if __name__ == '__main__':
    unittest.main()
