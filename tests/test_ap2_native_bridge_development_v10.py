"""Constructed V10 allocation, source, TCP and process-guard controls.

These tests supply no original-application purchases or hosted study outcomes.
"""
from __future__ import annotations

import asyncio
import ast
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'src')]
import run_ap2_native_bridge_matrix_v10 as allocation
import ap2_native_bridge_runtime_v10 as runtime
import evaluate_ap2_native_bridge_matrix_v10 as evaluator


def read(path):
    return json.loads(path.read_bytes())


class FrozenAllocationControls(unittest.TestCase):
    def test_frozen_cases_and_five_policies_preserved_exactly(self):
        old = read(ROOT / 'benchmark/ap2-application-development-v5/application.json')
        new = read(allocation.PUBLIC)
        self.assertEqual(new['cases'], old['cases'])
        self.assertEqual([{key: value for key, value in row.items() if key != 'description'} for row in new['arms'][:5]],
                         [{key: value for key, value in row.items() if key != 'description'} for row in old['arms']])
        self.assertTrue(all('ASGI' not in row['description'] for row in new['arms'][:5]))
        self.assertEqual(new['declared_cells'], 104)
        self.assertEqual(new['source_bank_candidates'], 34)
        self.assertEqual(new['node_version'], 'v22.23.2')
        cells = allocation.public_cells(new)
        self.assertEqual(len(cells), 104)
        self.assertEqual(sum(row['arm_id'] in ('amir_typed', 'mg_typed', 'mg_raw') for row in cells), 39)

    def test_cannot_change_prospective_denominator(self):
        manifest = read(allocation.PUBLIC)
        manifest['declared_cells'] = 103
        with self.assertRaises(ValueError):
            allocation.public_cells(manifest)

    def test_preallocate_then_finalize_all_missing_without_launch(self):
        with tempfile.TemporaryDirectory(prefix='ap2-v10-allocation-control-') as temp:
            directory = Path(temp)
            arguments = ['--output', str(directory / 'allocation'), '--site-packages', temp,
                         '--bridge-runtime', temp, '--node', sys.executable]
            self.assertEqual(allocation.main(arguments + ['--prepare-only']), 0)
            frozen = (directory / 'allocation/allocation-manifest.json').read_bytes()
            self.assertFalse((directory / 'allocation/execution-results.json').exists())
            self.assertEqual(allocation.main(arguments + ['--finalize-unexecuted']), 0)
            self.assertEqual((directory / 'allocation/allocation-manifest.json').read_bytes(), frozen)
            results = read(directory / 'allocation/execution-results.json')['cells']
            self.assertEqual(len(results), 104)
            self.assertTrue(all(row['returncode'] is None for row in results))
            self.assertFalse((directory / 'allocation/attempts').exists())
            checked = evaluator.evaluate(directory / 'allocation', crypto_enabled=False)
            self.assertEqual(checked['declared_cells'], 104)
            self.assertEqual(checked['totals']['missing_cells'], 104)
            self.assertEqual(checked['totals']['verified_captures'], 0)

    def test_interrupted_finalization_preserves_closed_started_and_cell_result_history(self):
        with tempfile.TemporaryDirectory(prefix='ap2-v10-interrupted-finalization-control-') as temp:
            output = Path(temp) / 'allocation'
            arguments = ['--output', str(output), '--site-packages', temp, '--bridge-runtime', temp, '--node', sys.executable]
            allocation.main(arguments + ['--prepare-only'])
            closed, started, result_only = allocation.public_cells(read(allocation.PUBLIC))[:3]
            for cell in (closed, started):
                attempt = output / 'attempts' / cell['id']; attempt.mkdir(parents=True)
                allocation.write(attempt / 'before-dispatch.json', dict(cell, command=['constructed-no-process']))
            receipt = dict(closed, allocation_status='actor_process_finished', returncode=0,
                           business_goal_decided_by_actor=False, constructed_no_process_fixture=True)
            path = output / 'attempts' / closed['id'] / 'after-dispatch.json'
            allocation.write(path, receipt); original = path.read_bytes()
            retained = output / 'cells' / result_only['id']; retained.mkdir(parents=True)
            allocation.write(retained / 'result.json', {'returncode': 4, 'constructed_no_process_fixture': True})
            allocation.main(arguments + ['--finalize-unexecuted'])
            rows = read(output / 'execution-results.json')['cells']
            self.assertEqual(len(rows), 104)
            self.assertEqual(rows[0]['allocation_status'], receipt['allocation_status'])
            self.assertEqual(rows[0]['returncode'], 0)
            self.assertEqual(path.read_bytes(), original)
            self.assertNotIn('not_executed', rows[1]['allocation_status'])
            self.assertIsNone(rows[1]['returncode'])
            self.assertEqual(rows[2]['returncode'], 4)
            self.assertIn('without_matrix_after_receipt', rows[2]['allocation_status'])
            self.assertIn('not_executed', rows[3]['allocation_status'])

    def test_sealed_original_bridge_graph_and_archive(self):
        raw_graph, raw_archive, graph, nodes = runtime.pinned_inputs()
        self.assertEqual(runtime.sha(raw_graph), runtime.GRAPH_SHA)
        self.assertEqual(runtime.sha(raw_archive), runtime.ARCHIVE_SHA)
        self.assertEqual(len(graph['files']), 2938)
        self.assertEqual({row['alias'] for row in graph['roots']}, {'a2a-to-mcp', 'mcp-a2a'})
        self.assertEqual(len(nodes), 15)

    def test_original_outgoing_sources_are_exact_byte_snapshots(self):
        public = read(allocation.PUBLIC)
        self.assertTrue(runtime.verify_outgoing_sources(public['original_outgoing_source_records'])[
            'source_copies_equal_executed_original_package_sources'])
        for name, row in public['original_outgoing_source_records'].items():
            raw = (ROOT / row['retained_path']).read_bytes()
            self.assertEqual(allocation.digest(raw), {key: row[key] for key in ('bytes', 'sha256')})
            original = ROOT / name
            if original.is_file():
                self.assertEqual(original.read_bytes(), raw)


class NodeProcessControls(unittest.TestCase):
    def run_node(self, mode, *arguments):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node unavailable for constructed controls')
        environment = {key: os.environ[key] for key in ('PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP') if key in os.environ}
        result = subprocess.run([node, str(ROOT / 'tests/ap2_native_bridge_controls_v10.mjs'), mode, *arguments],
                                env=environment, capture_output=True, timeout=15, check=False)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))

    def test_two_independent_typed_maps_and_legal_raw_mapping(self):
        self.run_node('mappings')

    def test_guards_allow_owned_socket_but_block_keys_network_and_unallocated_child(self):
        with tempfile.TemporaryDirectory(prefix='ap2-v10-node-guard-control-') as temp:
            state, package = Path(temp) / 'state', Path(temp) / 'runtime'
            state.mkdir(); package.mkdir()
            self.run_node('guard', str(state), str(package))
            rows = [json.loads(line) for line in (state / 'guard.jsonl').read_bytes().splitlines()]
            self.assertEqual(sum(row['kind'] == 'private_evaluator_probe_blocked' for row in rows), 1)
            self.assertEqual(sum(row['kind'] == 'external_network_probe_blocked' for row in rows), 1)


class CleanupFaultControl(unittest.IsolatedAsyncioTestCase):
    async def test_actual_finally_keeps_primary_error_and_attempts_every_owned_closer(self):
        # Execute the exact production finally statements with constructed
        # objects. No original module, socket, bridge or provider is loaded.
        tree = ast.parse((ROOT / 'scripts/ap2_reference_development_v10.py').read_text())
        application = next(row for row in tree.body if isinstance(row, ast.AsyncFunctionDef) and row.name == 'application')
        final = next(row.finalbody for row in reversed(application.body) if isinstance(row, ast.Try) and row.finalbody)
        source = ast.parse('async def constructed_cleanup():\n    try:\n        raise primary_error\n    finally:\n        pass\n')
        source.body[0].body[0].finalbody = deepcopy(final)
        ast.fix_missing_locations(source)
        calls, retained = [], {}
        class Closer:
            is_closed = False
            def __init__(self, name, fail=False): self.name, self.fail = name, fail
            async def aclose(self):
                calls.append(self.name)
                if self.fail: raise RuntimeError('constructed_closer_failure')
                self.is_closed = True
        class Group:
            cleanup_complete = False
            async def close(self): calls.append('group_close'); self.cleanup_complete = True
        original_json, restored_init, restored_genai = object(), object(), object()
        observer = SimpleNamespace(capture_complete=True, active_calls=0, records=[], serializer=original_json)
        def restore_failure(): calls.append('lease_restore'); raise RuntimeError('constructed_restore_failure')
        wrapper = SimpleNamespace(finish=lambda: calls.append('raw_finish'), report=lambda: {'constructed_only': True})
        recorder = SimpleNamespace(finish_stream=lambda *args: calls.append('stream_finish'),
            publish=lambda **kw: calls.append('recorder_publish'), close=lambda: calls.append('recorder_close'))
        namespace = {'primary_error': RuntimeError('constructed_primary_application_failure'), 'lease': SimpleNamespace(
            restore=restore_failure, bindings=SimpleNamespace(merchant=observer, credentials=observer)),
            'clients': [Closer('client_0', True), Closer('client_1')],
            'transports': {0: Closer('transport_0', True), 1: Closer('transport_1')},
            'group': Group(), 'cleanup_failures': [], 'restored': True,
            'httpx': SimpleNamespace(AsyncClient=SimpleNamespace()), 'genai': SimpleNamespace(),
            'binding': SimpleNamespace(SourceBinding=SimpleNamespace()), 'execution': SimpleNamespace(),
            'mandate_module': SimpleNamespace(), 'original_init': restored_init, 'original_genai': restored_genai,
            'original_validator': object(), 'original_marshal': object(), 'original_function_check': object(),
            'original_public_json': original_json, 'original_log_path': 'constructed_only',
            'PEERS': [('merchant', None, None, 8001, None), ('credentials', None, None, 8002, None), ('processor', None, None, 8003, None)],
            'wrappers': {role: wrapper for role in ('merchant', 'credentials', 'processor')}, 'recorder': recorder,
            'write': lambda path, value: retained.update({path.name: value}), 'output': Path('constructed_no_artifacts'),
            'transport_rows': [], 'callable_checks': [], 'imported_inventory': lambda *_: {},
            'site_packages': None, 'inventory': lambda *_: {}, 'runtime_files': {}, 'source_contract': lambda: (None, {}),
            'source_files': {}, 'TaskState': SimpleNamespace(input_required=SimpleNamespace(value='constructed_only')),
            'admission_boundary': SimpleNamespace(finish=lambda: calls.append('admission_finish'))}
        exec(compile(source, '<constructed V10 cleanup fault control>', 'exec'), namespace)
        with self.assertRaisesRegex(RuntimeError, 'constructed_primary_application_failure'):
            await namespace['constructed_cleanup']()
        for required in ('lease_restore', 'client_0', 'client_1', 'transport_0', 'transport_1', 'group_close', 'recorder_close'):
            self.assertIn(required, calls)
        self.assertIs(namespace['httpx'].AsyncClient.__init__, restored_init)
        self.assertIs(namespace['genai'].Client, restored_genai)
        self.assertFalse(retained['cleanup.json']['caller_aliases_restored'])
        self.assertEqual(len(retained['cleanup.json']['owned_cleanup_failures']), 3)


@unittest.skipUnless(importlib.util.find_spec('httpx') and importlib.util.find_spec('uvicorn'), 'HTTPX/Uvicorn unavailable')
class NativeTcpControls(unittest.IsolatedAsyncioTestCase):
    async def test_actual_tcp_entity_and_strict_owned_socket_cleanup(self):
        import httpx
        from interoperability.ap2_native_transport_v10 import OwnedPeerGroup
        received = []
        async def echo(scope, receive, send):
            body = b''
            while True:
                item = await receive(); body += item.get('body', b'')
                if not item.get('more_body', False):
                    break
            received.append((scope['server'], scope['client'], body, scope))
            await send({'type': 'http.response.start', 'status': 200, 'headers': [(b'content-type', b'application/json')]})
            await send({'type': 'http.response.body', 'body': body})
        with tempfile.TemporaryDirectory(prefix='ap2-v10-tcp-control-') as temp:
            output = Path(temp)
            probe = socket.socket(); probe.bind(('127.0.0.1', 0)); port = probe.getsockname()[1]; probe.close()
            group = OwnedPeerGroup(output, lambda path, value: path.write_text(json.dumps(value), encoding='utf-8'))
            transport = group.allocate('merchant', echo, port)
            payload = b'{"public_fixture":{"parts":[null,"123"]}}'
            try:
                async with httpx.AsyncClient(transport=transport, trust_env=False) as client:
                    response = await client.post(f'http://127.0.0.1:{port}/constructed-control?public=1%2B2', content=payload)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, payload)
                self.assertEqual(received[0][0], ('127.0.0.1', port))
                self.assertEqual(received[0][1][0], '127.0.0.1')
                self.assertEqual(received[0][2], payload)
                witness = json.loads((output / 'native-wire-attempts.jsonl').read_bytes().splitlines()[0])
                self.assertEqual(witness['request_query'], 'public=1%2B2')
                self.assertEqual(witness['request_raw_path'].encode(), received[0][3]['raw_path'])
                self.assertEqual(sorted((key.lower(), value) for key, value in witness['request_headers']),
                                 sorted((key.decode().lower(), value.decode('latin-1')) for key, value in received[0][3]['headers']))
                self.assertEqual(witness['request_entity'], allocation.digest(payload))
            finally:
                await transport.aclose()
                self.assertTrue(await group.close())
            self.assertTrue(read(output / 'native-socket-cleanup.json')['strict_cleanup_passed'])

    async def test_borrowed_listening_socket_is_not_closed_or_reused(self):
        from interoperability.ap2_native_transport_v10 import OwnedPeerGroup
        with tempfile.TemporaryDirectory(prefix='ap2-v10-borrowed-socket-control-') as temp:
            borrowed = socket.socket(); borrowed.bind(('127.0.0.1', 0)); borrowed.listen(1)
            port = borrowed.getsockname()[1]
            group = OwnedPeerGroup(Path(temp), lambda *_: None)
            try:
                with self.assertRaises(OSError):
                    group.allocate('merchant', lambda *_: None, port)
                self.assertGreaterEqual(borrowed.fileno(), 0)
                self.assertEqual(group.peers, {})
            finally:
                borrowed.close()


if __name__ == '__main__':
    unittest.main()
