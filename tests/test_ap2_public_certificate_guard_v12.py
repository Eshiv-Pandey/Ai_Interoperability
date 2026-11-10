"""Focused controls for declared public PEM admission and safe V12 diagnostics.

No original application, bridge or provider executes in these controls.
"""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import ap2_public_certificate_guard_v12 as certificates
import evaluate_ap2_native_bridge_matrix_v12 as evaluator


class PublicCertificateControls(unittest.TestCase):
    def fresh_files(self, temporary):
        base = Path(temporary)
        source, runtime, output = base / 'source', base / 'runtime', base / 'output'
        output.mkdir()
        for relative in certificates.SOURCE_PUBLIC_CERTIFICATES:
            target = source / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / 'runs/ap2-environment-preparation/source-stage-v1/ap2' / relative).read_bytes())
        bundle = b'\n'.join((source / relative).read_bytes() for relative in certificates.SOURCE_PUBLIC_CERTIFICATES)
        for relative in certificates.RUNTIME_PUBLIC_CA_PATHS:
            target = runtime / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bundle)
        return source, runtime, output

    def admit(self, source, runtime, output):
        return certificates.prepare_public_certificates(output, source, runtime,
            lambda path, value: path.write_text(json.dumps(value), encoding='utf-8'))

    def actual_guard(self, base, source, runtime, output, paths):
        tree = ast.parse((ROOT / 'scripts/ap2_reference_development_v12.py').read_text())
        worker = next(row for row in tree.body if isinstance(row, ast.FunctionDef) and row.name == 'worker')
        guard = next(row for row in worker.body if isinstance(row, ast.FunctionDef) and row.name == 'public_only_actor')
        state = {'private_root': None, 'bridge_client_dispatched': False, 'diagnostic_rows': 0,
                 'expected_private_evaluator_probe': False}
        roots = {'SOURCE': source, 'SITE_PACKAGES': runtime, 'REPOSITORY': base}
        namespace = {'Path': Path, 'os': os, 'ROOT': base, 'output': output,
                     'audit_state': state, 'public_CA_bundles': paths,
                     'denials': {'private_reads_blocked': 0, 'external_network_operations_blocked': 0,
                                 'allowed_owned_loopback_operations': 0, 'unallocated_descendant_processes_blocked': 0,
                                 'allowed_allocated_bridge_client_processes': 0},
                     'guard_roots': lambda: roots, 'record_denial': certificates.record_denial,
                     'plan': {'node': {'executable': sys.executable}, 'policy': {}}}
        exec(compile(ast.Module(body=[guard], type_ignores=[]), '<exact V12 actor guard control>', 'exec'), namespace)
        return namespace['public_only_actor'], state

    def test_exact_five_public_files_allowed_and_all_other_PEMs_denied(self):
        with tempfile.TemporaryDirectory(prefix='ap2-v12-public-cert-control-') as temporary:
            source, runtime, output = self.fresh_files(temporary)
            paths = self.admit(source, runtime, output)
            self.assertEqual(len(paths), 5)
            self.assertTrue(certificates.admitted_certificates_unchanged(output))
            guard, state = self.actual_guard(Path(temporary), source, runtime, output, paths)
            for path in paths:
                guard('open', (str(path), 'r'))
                with self.assertRaises(PermissionError):
                    guard('open', (str(path), 'w', os.O_WRONLY | os.O_TRUNC))
            for path in (source / 'unexpected.pem', runtime / 'other-package/cacert.pem',
                         Path(temporary) / 'saved-signing-key.pem', Path(temporary) / '.env',
                         Path(temporary) / 'benchmark/ap2-native-bridge-development-v12/evaluator.json'):
                with self.assertRaises(PermissionError):
                    guard('open', (str(path), 'r'))
            self.assertEqual(state['diagnostic_rows'], 10)

    def test_changed_original_public_certificate_is_refused(self):
        with tempfile.TemporaryDirectory(prefix='ap2-v12-pinned-cert-control-') as temporary:
            source, runtime, output = self.fresh_files(temporary)
            first, second = certificates.SOURCE_PUBLIC_CERTIFICATES
            (source / first).write_bytes((source / second).read_bytes())
            with self.assertRaisesRegex(ValueError, 'pinned_original_public_certificate_changed'):
                self.admit(source, runtime, output)

    def test_key_block_at_declared_CA_path_is_refused_without_retaining_it(self):
        with tempfile.TemporaryDirectory(prefix='ap2-v12-key-refusal-control-') as temporary:
            source, runtime, output = self.fresh_files(temporary)
            relative = certificates.RUNTIME_PUBLIC_CA_PATHS[0]
            (runtime / relative).write_bytes(b'-----BEGIN PRIVATE KEY-----\nCONSTRUCTED_NOT_A_SAVED_KEY\n-----END PRIVATE KEY-----\n')
            with self.assertRaisesRegex(ValueError, 'certificate_only_PEM_required'):
                self.admit(source, runtime, output)
            self.assertFalse((output / 'public-certificate-admission/installed_runtime' / relative).exists())

    def test_changed_admitted_CA_is_detected(self):
        with tempfile.TemporaryDirectory(prefix='ap2-v12-cert-change-control-') as temporary:
            source, runtime, output = self.fresh_files(temporary)
            self.admit(source, runtime, output)
            path = runtime / certificates.RUNTIME_PUBLIC_CA_PATHS[0]
            path.write_bytes(path.read_bytes() + b'# changed after admission\n')
            self.assertFalse(certificates.admitted_certificates_unchanged(output))

    def test_optional_pip_CA_absence_does_not_admit_a_different_path(self):
        with tempfile.TemporaryDirectory(prefix='ap2-v12-optional-pip-control-') as temporary:
            source, runtime, output = self.fresh_files(temporary)
            (runtime / certificates.RUNTIME_PUBLIC_CA_PATHS[-1]).unlink()
            paths = self.admit(source, runtime, output)
            self.assertEqual(len(paths), 4)
            self.assertNotIn(runtime / certificates.RUNTIME_PUBLIC_CA_PATHS[-1], paths)

    def evaluator_inputs(self, runtime, output):
        rows = {relative: certificates.identity((runtime / relative).read_bytes())
                for relative in certificates.RUNTIME_PUBLIC_CA_PATHS if (runtime / relative).is_file()}
        (output / 'runtime-manifest.json').write_text(json.dumps({'root': str(runtime), 'files': rows}), encoding='utf-8')
        return dict(certificates.SOURCE_PUBLIC_CERTIFICATES)

    def test_independent_evaluator_verifies_public_source_and_runtime_copy_bindings(self):
        with tempfile.TemporaryDirectory(prefix='ap2-v12-certificate-evaluation-control-') as temporary:
            source, runtime, output = self.fresh_files(temporary)
            self.admit(source, runtime, output)
            original = self.evaluator_inputs(runtime, output)
            self.assertEqual(evaluator.verify_public_certificate_admissions(output, original), 5)
            admission_path = output / 'public-certificate-admission.json'
            receipt = json.loads(admission_path.read_bytes())
            receipt['records'].append(receipt['records'][0])
            admission_path.write_text(json.dumps(receipt), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'public_certificate_admission_missing_duplicate_or_undeclared'):
                evaluator.verify_public_certificate_admissions(output, original)

    def test_independent_evaluator_rejects_key_even_if_supplied_hashes_are_changed_together(self):
        with tempfile.TemporaryDirectory(prefix='ap2-v12-certificate-key-evaluation-control-') as temporary:
            source, runtime, output = self.fresh_files(temporary)
            self.admit(source, runtime, output)
            original = self.evaluator_inputs(runtime, output)
            admission_path = output / 'public-certificate-admission.json'
            receipt = json.loads(admission_path.read_bytes())
            row = next(value for value in receipt['records'] if value['category'] == 'installed_runtime')
            raw = b'-----BEGIN PRIVATE KEY-----\nCONSTRUCTED_NOT_A_SAVED_KEY\n-----END PRIVATE KEY-----\n'
            (output / row['retained_path']).write_bytes(raw)
            row['identity'] = certificates.identity(raw)
            admission_path.write_text(json.dumps(receipt), encoding='utf-8')
            runtime_path = output / 'runtime-manifest.json'
            runtime_receipt = json.loads(runtime_path.read_bytes())
            runtime_receipt['files'][row['relative_path']] = row['identity']
            runtime_path.write_text(json.dumps(runtime_receipt), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'public_certificate_contains_key_or_exceeds_bound'):
                evaluator.verify_public_certificate_admissions(output, original)

    def test_loopback_probe_is_diagnosed_and_still_denied_without_a_declared_exception(self):
        with tempfile.TemporaryDirectory(prefix='ap2-v12-network-diagnostic-control-') as temporary:
            source, runtime, output = self.fresh_files(temporary)
            guard, state = self.actual_guard(Path(temporary), source, runtime, output,
                                             self.admit(source, runtime, output))
            sock = SimpleNamespace(family=10, type=1)
            with self.assertRaises(PermissionError):
                guard('socket.bind', (sock, ('::1', 0, 0, 0)))
            with self.assertRaises(PermissionError):
                guard('socket.connect', (sock, ('CONSTRUCTED_SECRET_IN_EXTERNAL_HOST', 443)))
            guard('socket.bind', (sock, ('127.0.0.1', 8001)))
            rows = [json.loads(row) for row in (output / 'actor-guard-denials.jsonl').read_bytes().splitlines()]
            self.assertEqual(rows[0]['network_endpoint'], {'host': '::1', 'port': 0, 'socket_family': 10, 'socket_type': 1})
            self.assertEqual(rows[1]['network_endpoint']['host'], '<redacted_external_or_unrecognized>')
            self.assertNotIn('CONSTRUCTED_SECRET_IN_EXTERNAL_HOST', (output / 'actor-guard-denials.jsonl').read_text())
            self.assertEqual(state['diagnostic_rows'], 2)

    def test_diagnostics_are_bounded_and_never_capture_arguments_or_outside_paths(self):
        with tempfile.TemporaryDirectory(prefix='ap2-v12-denial-diagnostic-control-') as temporary:
            source, runtime, output = self.fresh_files(temporary)
            guard, state = self.actual_guard(Path(temporary), source, runtime, output,
                                              self.admit(source, runtime, output))
            for index in range(66):
                with self.assertRaises(PermissionError):
                    guard('subprocess.Popen', ('outside', ['CONSTRUCTED_SECRET_ARGUMENT']))
            rows = [json.loads(row) for row in (output / 'actor-guard-denials.jsonl').read_bytes().splitlines()]
            self.assertEqual(len(rows), 64)
            self.assertTrue(state['diagnostic_bound_reached'])
            self.assertNotIn('CONSTRUCTED_SECRET_ARGUMENT', (output / 'actor-guard-denials.jsonl').read_text())
            self.assertTrue(all(row['frames'] and len(row['frames']) <= 24 for row in rows))
            self.assertTrue(all(row['contents_arguments_locals_headers_and_environment_retained'] is False for row in rows))
            self.assertEqual(certificates.safe_path(Path(temporary).parent / 'outside-private-key.pem',
                                                    {'REPOSITORY': Path(temporary)}), '<outside_declared_roots>')


if __name__ == '__main__':
    unittest.main()
