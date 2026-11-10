"""Execute actual owned stage/certificate prelude with real actor globals.

This control stops before installing the audit hook or starting the SDK event
loop. No original application, bridge or provider runs; no helper is stubbed.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_actor(version):
    path = ROOT / ('scripts/ap2_reference_development_v' + str(version) + '.py')
    spec = importlib.util.spec_from_file_location('_constructed_ap2_stage_actor_v' + str(version), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, ast.parse(path.read_text(encoding='utf-8'))


def actual_certificate_stage_prelude(module, tree):
    worker = next(row for row in tree.body if isinstance(row, ast.FunctionDef) and row.name == 'worker')
    first = next(index for index, row in enumerate(worker.body) if isinstance(row, ast.Expr)
                 and isinstance(row.value, ast.Call) and isinstance(row.value.func, ast.Name)
                 and row.value.func.id == 'append')
    helper_import = next(row for row in worker.body if isinstance(row, ast.ImportFrom)
                         and row.module.startswith('ap2_public_certificate_guard_v'))
    # The exact three consecutive production statements, using the module's
    # own append/now/write and its actual declared certificate helper import.
    body = [deepcopy(helper_import)] + deepcopy(worker.body[first:first + 3])
    body.append(ast.Return(value=ast.Name(id='public_CA_bundles', ctx=ast.Load())))
    control = ast.FunctionDef(name='_constructed_certificate_stage_prelude', args=deepcopy(worker.args),
                              body=body, decorator_list=[])
    program = ast.fix_missing_locations(ast.Module(body=[control], type_ignores=[]))
    exec(compile(program, '<exact owned certificate-stage prelude>', 'exec'), module.__dict__)
    return module._constructed_certificate_stage_prelude


class WorkerStagePreludeControls(unittest.TestCase):
    def output_and_runtime(self, base, actor):
        output, runtime = Path(base) / 'output', Path(base) / 'runtime'
        output.mkdir()
        source_names = ('code/samples/certs/ds_cert_sdjwt.pem', 'code/samples/certs/issuer_cert_sdjwt.pem')
        bundle = b'\n'.join((actor.SOURCE / name).read_bytes() for name in source_names)
        for name in ('certifi/cacert.pem', 'grpc/_cython/_credentials/roots.pem', 'pip/_vendor/certifi/cacert.pem'):
            path = runtime / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(bundle)
        return output, runtime

    def test_frozen_V9_exact_prelude_reproduces_first_missing_append_dependency(self):
        actor, tree = load_actor(9)
        self.assertNotIn('append', actor.__dict__)
        self.assertNotIn('now', actor.__dict__)
        prelude = actual_certificate_stage_prelude(actor, tree)
        with tempfile.TemporaryDirectory(prefix='ap2-v9-owned-prelude-failure-control-') as temporary:
            output, runtime = self.output_and_runtime(temporary, actor)
            with self.assertRaisesRegex(NameError, "name 'append' is not defined"):
                prelude(output, runtime)
            self.assertFalse((output / 'worker-stages.jsonl').exists())
            self.assertFalse((output / 'public-certificate-admission.json').exists())

    def test_V12_exact_prelude_uses_real_helpers_and_completes_public_certificate_admission(self):
        actor, tree = load_actor(11)
        self.assertIs(actor.append.__globals__, actor.__dict__)
        self.assertIs(actor.now.__globals__, actor.__dict__)
        prelude = actual_certificate_stage_prelude(actor, tree)
        with tempfile.TemporaryDirectory(prefix='ap2-v12-owned-prelude-success-control-') as temporary:
            output, runtime = self.output_and_runtime(temporary, actor)
            admitted = prelude(output, runtime)
            self.assertEqual(len(admitted), 5)
            receipt = json.loads((output / 'public-certificate-admission.json').read_bytes())
            self.assertEqual(receipt['schema_version'], 'ap2-declared-public-certificate-admission/12')
            self.assertEqual(len(receipt['records']), 5)
            rows = [json.loads(row) for row in (output / 'worker-stages.jsonl').read_bytes().splitlines()]
            self.assertEqual([row['stage'] for row in rows], ['before_declared_public_certificate_admission',
                                                             'declared_public_certificate_admission_completed'])
            self.assertTrue(all(datetime.fromisoformat(row['utc']).utcoffset() == timezone.utc.utcoffset(None) for row in rows))
            self.assertFalse((output / 'native-servers-started.json').exists())

    def test_all_nine_actual_journal_call_sites_execute_with_real_module_globals(self):
        actor, tree = load_actor(11)
        sites = [row for row in ast.walk(tree) if isinstance(row, ast.Expr) and isinstance(row.value, ast.Call)
                 and isinstance(row.value.func, ast.Name) and row.value.func.id == 'append']
        self.assertEqual(len(sites), 9)
        with tempfile.TemporaryDirectory(prefix='ap2-v12-owned-journal-sites-control-') as temporary:
            output = Path(temporary)
            for site in sorted(sites, key=lambda row: row.lineno):
                program = ast.fix_missing_locations(ast.Module(body=[deepcopy(site)], type_ignores=[]))
                exec(compile(program, '<exact owned stage-journal call>', 'exec'), actor.__dict__, {'output': output})
            rows = [json.loads(row) for row in (output / 'worker-stages.jsonl').read_bytes().splitlines()]
            self.assertEqual(len(rows), 9)
            self.assertEqual(len({row['stage'] for row in rows}), 9)
            self.assertTrue(all(set(row) == {'stage', 'utc'} for row in rows))
            self.assertTrue(all(datetime.fromisoformat(row['utc']).utcoffset() == timezone.utc.utcoffset(None) for row in rows))

    def test_real_append_preserves_prior_entries_and_refuses_invalid_or_oversized_json(self):
        actor, _ = load_actor(11)
        with tempfile.TemporaryDirectory(prefix='ap2-v12-owned-journal-bound-control-') as temporary:
            path = Path(temporary) / 'journal.jsonl'
            actor.append(path, {'stage': 'constructed_one', 'utc': actor.now()})
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                actor.append(path, {'bad': float('nan')})
            with self.assertRaisesRegex(ValueError, 'journal_entry_size_bound'):
                actor.append(path, {'oversized': 'x' * (64 * 1024)})
            self.assertEqual(path.read_bytes(), before)
            actor.append(path, {'stage': 'constructed_two', 'utc': actor.now()})
            self.assertTrue(path.read_bytes().startswith(before))
            self.assertEqual(len(path.read_bytes().splitlines()), 2)


if __name__ == '__main__':
    unittest.main()
