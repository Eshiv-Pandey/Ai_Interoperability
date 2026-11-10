"""Constructed exact-source policy controls; no AP2/SDK app or provider runs.

The copied urllib3 connection module uses supplied import dependencies and a
socket wrapper. It exercises its unchanged compiled import-time helper but
does not call bind/connect/listen/send on the operating system.
"""
from __future__ import annotations

import ast
import builtins
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import ap2_native_guard_policy_v12 as guard


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NativeGuardPolicyControls(unittest.TestCase):
    def fixture(self, base):
        source = Path(base) / guard.RELATIVE_SOURCE
        source.parent.mkdir(parents=True)
        source.write_bytes((ROOT / 'docs/research/source-evidence/ap2-v12-runtime-guard-fixtures-v1/connection.py').read_bytes())
        return source

    def copied_module(self, policy):
        decisions = []
        real_factory = socket.socket
        class Probe:
            def __init__(self, family): self.actual = real_factory(family)
            def bind(self, address):
                accepted = policy.admit_ipv6_capability_bind('socket.bind', (self.actual, address), sys._getframe(1))
                decisions.append(accepted)
                if not accepted: raise PermissionError('constructed_guard_refusal')
            def close(self): self.actual.close()
        socket_fixture = SimpleNamespace(socket=Probe, has_ipv6=True, AF_INET6=socket.AF_INET6,
                                         AF_INET=socket.AF_INET, AF_UNSPEC=socket.AF_UNSPEC)
        def supplied_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == 'socket' and level == 0: return socket_fixture
            if name == 'exceptions' and level == 2: return SimpleNamespace(LocationParseError=ValueError)
            if name == 'timeout' and level == 1: return SimpleNamespace(_DEFAULT_TIMEOUT=object(), _TYPE_TIMEOUT=object)
            return builtins.__import__(name, globals, locals, fromlist, level)
        namespace = {'__builtins__': dict(vars(builtins), __import__=supplied_import),
                     '__name__': '_constructed_copied_connection', '__package__': '_constructed_package.util'}
        exec(policy.module_code, namespace)
        return namespace, decisions

    def test_exact_literal_normalization_has_no_decoding_or_external_host_expansion(self):
        for raw, expected in [('127.0.0.1', '127.0.0.1'), ('::1', '::1'), ('localhost', 'localhost'),
                              (b'127.0.0.1', '127.0.0.1'), (b'::1', '::1'), (b'localhost', 'localhost')]:
            self.assertEqual(guard.normalized_owned_host(raw), expected)
        for value in ['127.0.0.2', 'LOCALHOST', 'localhost.', 'localhost.evil', '::', '8.8.8.8',
                      b'127.0.0.1\x00', b'localhost.', b'8.8.8.8', b'\xff', bytearray(b'localhost'), None, 1]:
            self.assertIsNone(guard.normalized_owned_host(value))

    @unittest.skipUnless(socket.has_ipv6 and os.name != 'nt', 'Positive fresh-unbound endpoint witness requires hosted POSIX sockets')
    def test_exact_compiled_import_probe_admitted_once_and_closes_socket(self):
        with tempfile.TemporaryDirectory(prefix='ap2-v12-exact-probe-control-') as temp:
            self.fixture(temp); policy = guard.NativeGuardPolicy(temp)
            namespace, decisions = self.copied_module(policy)
            self.assertEqual(decisions, [True]); self.assertTrue(namespace['HAS_IPV6'])
            receipt = policy.receipt()
            self.assertEqual(receipt['allowed_ipv6_capability_binds'], 1)
            self.assertTrue(receipt['admitted_capability_sockets_closed'])
            self.assertEqual(receipt['capability_rows'][0]['relative_source'], guard.RELATIVE_SOURCE)
            namespace, decisions = self.copied_module(policy)
            self.assertEqual(decisions, [False]); self.assertFalse(namespace['HAS_IPV6'])
            self.assertEqual(policy.receipt()['allowed_ipv6_capability_binds'], 1)

    @unittest.skipUnless(socket.has_ipv6 and os.name != 'nt', 'Positive fresh-unbound endpoint witness requires hosted POSIX sockets')
    def test_later_same_function_call_outside_exact_import_site_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix='ap2-v12-later-probe-control-') as temp:
            self.fixture(temp); policy = guard.NativeGuardPolicy(temp)
            namespace, _ = self.copied_module(policy)
            policy.admitted_sockets.clear(); policy.allowed_rows.clear()
            self.assertFalse(namespace['_has_ipv6']('::1'))
            self.assertEqual(policy.receipt()['allowed_ipv6_capability_binds'], 0)

    def test_wrong_endpoint_family_socket_operation_and_unbound_caller_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix='ap2-v12-negative-probe-control-') as temp:
            self.fixture(temp); policy = guard.NativeGuardPolicy(temp)
            sock = socket.socket()
            try:
                for operation in ['socket.bind', 'socket.connect', 'socket.connect_ex', 'socket.sendto', 'socket.getaddrinfo']:
                    for address in [('::1', 0), ('::1', 8001), ('::', 0), ('8.8.8.8', 443), (b'::1', 0)]:
                        self.assertFalse(policy.admit_ipv6_capability_bind(operation, (sock, address), sys._getframe()))
                self.assertFalse(policy.admit_ipv6_capability_bind('socket.bind', (object(), ('::1', 0)), sys._getframe()))
            finally:
                sock.close()
            self.assertEqual(policy.receipt()['allowed_ipv6_capability_binds'], 0)

    def test_changed_source_is_rejected_and_post_admission_source_changes_are_reported(self):
        with tempfile.TemporaryDirectory(prefix='ap2-v12-source-guard-control-') as temp:
            source = self.fixture(temp); policy = guard.NativeGuardPolicy(temp)
            source.write_bytes(source.read_bytes() + b'\n# Changed public source\n')
            self.assertFalse(policy.receipt()['source_unchanged'])
            with self.assertRaisesRegex(ValueError, 'pinned_urllib3_capability_source_changed'):
                guard.NativeGuardPolicy(temp)

    def test_real_platform_metadata_call_uses_cache_with_descendant_creation_refused(self):
        with tempfile.TemporaryDirectory(prefix='ap2-v12-platform-cache-control-') as temp:
            self.fixture(temp); policy = guard.NativeGuardPolicy(temp)
            import subprocess
            original = subprocess.Popen
            def refused(*args, **kwargs): raise AssertionError('guarded_platform_call_requested_child')
            subprocess.Popen = refused
            try:
                self.assertTrue(policy.receipt()['guarded_platform_metadata_equals_cached_value'])
            finally:
                subprocess.Popen = original

    def test_application_and_existing_denial_gate_AST_are_frozen_after_version_normalization(self):
        old = ast.parse((ROOT / 'scripts/ap2_reference_development_v11.py').read_text())
        new = ast.parse((ROOT / 'scripts/ap2_reference_development_v12.py').read_text().replace('v12', 'v11').replace('V12', 'V11').replace('/12', '/11'))
        function = lambda tree: next(row for row in tree.body if isinstance(row, ast.AsyncFunctionDef) and row.name == 'application')
        self.assertEqual(ast.dump(function(old), include_attributes=False), ast.dump(function(new), include_attributes=False))
        old = ast.parse((ROOT / 'scripts/evaluate_ap2_native_bridge_matrix_v11.py').read_text())
        new = ast.parse((ROOT / 'scripts/evaluate_ap2_native_bridge_matrix_v12.py').read_text().replace('v12', 'v11').replace('V12', 'V11').replace('/12', '/11'))
        find = lambda tree: next(row for row in tree.body if isinstance(row, ast.FunctionDef) and row.name == 'verify_native_capture')
        candidate = deepcopy(find(new))
        candidate.body = [row for row in candidate.body if not (isinstance(row, ast.Expr) and isinstance(row.value, ast.Call)
                           and isinstance(row.value.func, ast.Name) and row.value.func.id == 'verify_native_guard_policy')]
        self.assertEqual(ast.dump(find(old), include_attributes=False), ast.dump(candidate, include_attributes=False))

    def test_independent_receipt_checker_rejects_changed_binding_count_cleanup_or_probe(self):
        evaluator = load('_constructed_v12_policy_evaluator', ROOT / 'scripts/evaluate_ap2_native_bridge_matrix_v12.py')
        with tempfile.TemporaryDirectory(prefix='ap2-v12-receipt-check-control-') as temp:
            base = Path(temp); self.fixture(base / 'runtime'); policy = guard.NativeGuardPolicy(base / 'runtime')
            receipt = policy.receipt()
            (base / 'runtime-manifest.json').write_text(json.dumps({'files': {guard.RELATIVE_SOURCE: guard.SOURCE_IDENTITY}}))
            (base / 'actor-input-separation.json').write_text(json.dumps({'denials': {'allowed_owned_loopback_operations': 0}}))
            def check(row):
                (base / 'native-guard-policy.json').write_text(json.dumps(row))
                return evaluator.verify_native_guard_policy(base)
            self.assertEqual(check(receipt), 0)
            for key, value in [('allowed_ipv6_capability_binds', 2), ('allowed_ipv6_capability_binds', True),
                               ('source_identity', {'bytes': 1, 'sha256': 'changed'}),
                               ('admitted_capability_sockets_closed', False),
                               ('guarded_platform_metadata_equals_cached_value', False),
                               ('normalized_bytes_owned_operations', 1),
                               ('capability_rows', [{'operation': 'socket.connect'}])]:
                changed = deepcopy(receipt); changed[key] = value
                with self.assertRaises(ValueError): check(changed)

    def test_v2_safe_printer_emits_only_bounded_policy_metadata(self):
        printer = load('_constructed_v12_safe_printer', ROOT / 'scripts/print_ap2_owned_cell_diagnostics_v2.py')
        with tempfile.TemporaryDirectory(prefix='ap2-v12-printer-policy-control-') as temp:
            base = Path(temp); self.fixture(base / 'runtime'); policy = guard.NativeGuardPolicy(base / 'runtime')
            receipt = policy.receipt(); receipt['secret_extra'] = 'CONSTRUCTED_SECRET'; receipt['capability_rows'] = ['CONSTRUCTED_SECRET']
            (base / 'native-guard-policy.json').write_text(json.dumps(receipt))
            emitted = []; printer.print_diagnostics(base, 0, emit=emitted.append)
            self.assertNotIn('CONSTRUCTED_SECRET', '\n'.join(emitted))
            self.assertEqual(next(json.loads(row) for row in emitted if json.loads(row)['kind'] == 'owned_native_guard_policy')['allowed_ipv6_capability_binds'], 0)


if __name__ == '__main__':
    unittest.main()
