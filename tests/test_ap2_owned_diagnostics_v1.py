"""Constructed safe-output and exact-once launcher controls; no AP2 app runs."""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import print_ap2_owned_cell_diagnostics_v1 as diagnostics
import run_ap2_cell_with_safe_diagnostics_v1 as launcher


class OwnedDiagnosticControls(unittest.TestCase):
    def output(self, cell, code=3):
        rows = []
        diagnostics.print_diagnostics(cell, code, emit=rows.append)
        return '\n'.join(rows), [json.loads(row) for row in rows]

    def test_only_allowlisted_metadata_is_printed_and_secret_like_fields_are_omitted(self):
        with tempfile.TemporaryDirectory(prefix='ap2-owned-safe-diagnostic-control-') as temporary:
            cell = Path(temporary)
            frame = {'file': '<REPOSITORY>/scripts/ap2_reference_development_v10.py', 'function': 'worker', 'line': 721,
                     'locals': {'credential': 'CONSTRUCTED_SECRET_LOCALS'}}
            (cell / 'worker-failure.json').write_text(json.dumps({'error_type': 'ValueError', 'frames': [frame],
                'reason': 'CONSTRUCTED_SECRET_REASON', 'headers': {'authorization': 'CONSTRUCTED_SECRET_HEADER'},
                'environment': {'key': 'CONSTRUCTED_SECRET_ENV'}}))
            guards = [{'operation': 'socket.bind', 'guard_code': 'native_actor_unowned_network_operation_denied',
                'network_endpoint': {'host': '::1', 'port': 0, 'socket_family': 10, 'socket_type': 1},
                'frames': [{'file': '<SITE_PACKAGES>/urllib3/util/connection.py', 'function': '_has_ipv6', 'line': 109}]},
                {'operation': 'CONSTRUCTED_SECRET_OPERATION', 'guard_code': 'CONSTRUCTED_SECRET_CODE',
                 'path': '/outside/CONSTRUCTED_SECRET_PATH.pem', 'network_endpoint': {'host': 'CONSTRUCTED_SECRET_HOST', 'port': 443},
                 'frames': [{'file': '<REPOSITORY>/scripts/CONSTRUCTED_SECRET_FILE.py',
                             'function': 'CONSTRUCTED_SECRET_FUNCTION', 'line': 'CONSTRUCTED_SECRET_LINE'}]}]
            (cell / 'actor-guard-denials.jsonl').write_text('\n'.join(json.dumps(row) for row in guards))
            (cell / 'worker-stages.jsonl').write_text('\n'.join(json.dumps({'stage': label, 'extra': 'CONSTRUCTED_SECRET_EXTRA'})
                for label in ('before_declared_public_certificate_admission', 'CONSTRUCTED_SECRET_STAGE')))
            text, rows = self.output(cell)
            self.assertNotIn('CONSTRUCTED_SECRET', text)
            self.assertEqual(rows[0], {'kind': 'owned_actor_returncode', 'returncode': 3})
            failure = next(row for row in rows if row['kind'] == 'owned_worker_failure')
            self.assertEqual(failure['error_type'], 'ValueError')
            self.assertEqual(failure['frames'][0]['function'], 'worker')
            guard = next(row for row in rows if row['kind'] == 'owned_guard_denial')
            self.assertEqual(guard['network_endpoint']['host'], '::1')
            self.assertEqual(guard['network_endpoint']['port'], 0)
            self.assertEqual(guard['frames'][0]['function'], '_has_ipv6')

    def test_unknown_error_types_outside_frames_and_malformed_files_are_redacted(self):
        with tempfile.TemporaryDirectory(prefix='ap2-owned-diagnostic-redaction-control-') as temporary:
            cell = Path(temporary)
            (cell / 'worker-failure.json').write_text(json.dumps({'error_type': 'CONSTRUCTED_SECRET_TYPE',
                'frames': [{'file': '/private/CONSTRUCTED_SECRET_FILE.py', 'function': 'CONSTRUCTED_SECRET_FUNCTION', 'line': 1}]}))
            (cell / 'actor-guard-denials.jsonl').write_text('CONSTRUCTED_SECRET_NOT_JSON')
            text, rows = self.output(cell)
            self.assertNotIn('CONSTRUCTED_SECRET', text)
            self.assertTrue(any(row.get('status') == 'unavailable_or_malformed' for row in rows))
            self.assertTrue(any(row.get('status') == 'absent' for row in rows))

    def test_input_frame_row_and_total_output_bounds(self):
        with tempfile.TemporaryDirectory(prefix='ap2-owned-diagnostic-bounds-control-') as temporary:
            cell = Path(temporary)
            frame = {'file': '<SITE_PACKAGES>/urllib3/util/connection.py', 'function': '_has_ipv6', 'line': 109}
            guards = [{'operation': 'socket.bind', 'guard_code': 'native_actor_unowned_network_operation_denied',
                       'frames': [frame] * 20} for _ in range(10)]
            (cell / 'actor-guard-denials.jsonl').write_text('\n'.join(json.dumps(row) for row in guards))
            (cell / 'worker-stages.jsonl').write_text('\n'.join(json.dumps({'stage': 'application_entry'}) for _ in range(20)))
            text, rows = self.output(cell)
            self.assertLessEqual(len(text.encode()) + 1, diagnostics.MAX_OUTPUT_BYTES)
            self.assertLessEqual(sum(row['kind'] == 'owned_guard_denial' for row in rows), diagnostics.MAX_GUARD_ROWS)
            self.assertTrue(all(len(row['frames']) <= diagnostics.MAX_FRAMES for row in rows if 'frames' in row))
            self.assertTrue(any(row.get('status') == 'row_bound_reached' for row in rows))
            (cell / 'worker-failure.json').write_bytes(b'x' * (diagnostics.MAX_INPUT_BYTES + 1))
            _, rows = self.output(cell)
            self.assertTrue(any(row.get('status') == 'input_bound_exceeded' for row in rows))

    def test_isolated_exact_once_launcher_preserves_failure_and_captures_raw_streams(self):
        with tempfile.TemporaryDirectory(prefix='ap2-owned-exact-once-launch-control-') as temporary:
            base = Path(temporary)
            actor = base / 'constructed_program.py'
            actor.write_text("from pathlib import Path\nimport json,sys\ncounter=Path(sys.argv[1])\n"
                "counter.write_text(str(int(counter.read_text())+1) if counter.exists() else '1')\n"
                "cell=Path(sys.argv[2]);cell.mkdir()\n"
                "(cell/'worker-failure.json').write_text(json.dumps({'error_type':'NameError','frames':[]}))\n"
                "print('CONSTRUCTED_SECRET_RAW_STDOUT')\nprint('CONSTRUCTED_SECRET_RAW_STDERR',file=sys.stderr)\n"
                "raise SystemExit(3)\n")
            cell, logs, counter = base / 'cell', base / 'logs', base / 'count.txt'
            result = subprocess.run([sys.executable, '-I', '-S', '-B', str(ROOT / 'scripts/run_ap2_cell_with_safe_diagnostics_v1.py'),
                '--cell', str(cell), '--launcher-logs', str(logs), '--', sys.executable, '-I', '-S', '-B',
                str(actor), str(counter), str(cell)], capture_output=True, text=True, check=False, timeout=15)
            self.assertEqual(result.returncode, 3)
            self.assertEqual(counter.read_text(), '1')
            self.assertNotIn('CONSTRUCTED_SECRET', result.stdout + result.stderr)
            self.assertIn('CONSTRUCTED_SECRET_RAW_STDOUT', (logs / 'stdout.txt').read_text())
            self.assertIn('CONSTRUCTED_SECRET_RAW_STDERR', (logs / 'stderr.txt').read_text())
            rows = [json.loads(row) for row in result.stdout.splitlines()]
            self.assertEqual(rows[0]['returncode'], 3)

    def test_printer_exception_does_not_replace_actual_child_returncode(self):
        with tempfile.TemporaryDirectory(prefix='ap2-owned-diagnostic-printer-fault-control-') as temporary:
            base = Path(temporary)
            def broken_printer(*_):
                raise SystemExit('CONSTRUCTED_SECRET_PRINTER_ERROR')
            output = io.StringIO()
            with redirect_stdout(output):
                code = launcher.run_once(base / 'absent-cell', base / 'logs',
                                         [sys.executable, '-I', '-S', '-B', '-c', 'raise SystemExit(3)'],
                                         printer=broken_printer)
            self.assertEqual(code, 3)
            self.assertNotIn('CONSTRUCTED_SECRET', output.getvalue())
            self.assertIn('printer_unavailable', output.getvalue())

    def test_isolated_printer_handles_absent_files_without_importing_an_actor(self):
        with tempfile.TemporaryDirectory(prefix='ap2-owned-diagnostic-isolation-control-') as temporary:
            result = subprocess.run([sys.executable, '-I', '-S', '-B',
                str(ROOT / 'scripts/print_ap2_owned_cell_diagnostics_v1.py'), '--cell', temporary, '--returncode', '3'],
                capture_output=True, text=True, check=False, timeout=15)
            self.assertEqual(result.returncode, 0)
            rows = [json.loads(row) for row in result.stdout.splitlines()]
            self.assertEqual(rows[0]['returncode'], 3)
            self.assertEqual(sum(row.get('status') == 'absent' for row in rows), 3)


if __name__ == '__main__':
    unittest.main()
