"""Independent exact diagnostic-prelude coverage; no original app or worker run."""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib
import json
from pathlib import Path
import tempfile
import types

ROOT = Path(__file__).resolve().parents[1]


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def load(name, path):
    raw = path.read_bytes()
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module, raw


def journal_statement(node):
    if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
        return False
    call = node.value
    return isinstance(call.func, ast.Name) and call.func.id == 'append' and call.args and any(
        isinstance(item, ast.Constant) and item.value == 'worker-stages.jsonl' for item in ast.walk(call.args[0]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('fresh_V10_stage_peer_receipt_required')
    v9, raw9 = load('_frozen_v9_stage_dependency_peer', ROOT / 'scripts/ap2_reference_development_v9.py')
    v10, raw10 = load('_prospective_v10_stage_dependency_peer', ROOT / 'scripts/ap2_reference_development_v10.py')
    tree9, tree10 = ast.parse(raw9), ast.parse(raw10)
    worker9 = next(node for node in tree9.body if isinstance(node, ast.FunctionDef) and node.name == 'worker')
    first9 = next(node for node in worker9.body if journal_statement(node))
    worker10 = next(node for node in tree10.body if isinstance(node, ast.FunctionDef) and node.name == 'worker')
    first = next(index for index, node in enumerate(worker10.body) if journal_statement(node))
    prelude = worker10.body[first:first + 3]
    if not journal_statement(prelude[0]) or not isinstance(prelude[1], ast.Assign) or not journal_statement(prelude[2]):
        raise ValueError('exact_diagnostic_admission_prelude_structure_changed')
    helper_import = next(node for node in worker10.body if isinstance(node, ast.ImportFrom)
                         and node.module == 'ap2_public_certificate_guard_v10')
    controls = {}
    old_name_error = None
    with tempfile.TemporaryDirectory(prefix='ap2-v10-exact-stage-peer-') as temporary:
        base = Path(temporary).resolve()
        output, source, runtime = base / 'output', base / 'source', base / 'runtime'
        output.mkdir()
        v9.output = output
        try:
            exec(compile(ast.fix_missing_locations(ast.Module(body=[deepcopy(first9)], type_ignores=[])),
                         '<exact frozen V9 first-stage statement>', 'exec'), v9.__dict__)
        except NameError as error:
            old_name_error = error.name
        controls['frozen_V9_first_stage_reproduces_append_NameError'] = old_name_error == 'append'
        controls['frozen_V9_now_also_missing'] = not hasattr(v9, 'now')
        controls['V10_real_append_and_now_globals_resolve'] = callable(getattr(v10, 'append', None)) and callable(getattr(v10, 'now', None))
        helper = importlib.import_module('ap2_public_certificate_guard_v10')
        for name, pinned in helper.SOURCE_PUBLIC_CERTIFICATES.items():
            raw = (ROOT / 'runs/ap2-environment-preparation/source-stage-v1/ap2' / name).read_bytes()
            if identity(raw) != pinned:
                raise ValueError('public_source_certificate_fixture_changed')
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        bundle = b'\n'.join((source / name).read_bytes() for name in helper.SOURCE_PUBLIC_CERTIFICATES)
        for name in helper.RUNTIME_PUBLIC_CA_PATHS:
            path = runtime / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(bundle)
        # Supply public fixture roots and exact local helper import; do not
        # stub/replace actor append(), now(), write() or certificate admission.
        v10.__dict__.update(output=output, SOURCE=source, site_packages=runtime)
        exact = ast.fix_missing_locations(ast.Module(body=[deepcopy(helper_import)] + deepcopy(prelude), type_ignores=[]))
        exec(compile(exact, '<exact V10 diagnostic admission prelude>', 'exec'), v10.__dict__)
        rows = [json.loads(line) for line in (output / 'worker-stages.jsonl').read_text().splitlines()]
        controls['exact_three_production_prelude_statements_execute'] = len(rows) == 2 and rows[0]['stage'] == 'before_declared_public_certificate_admission' \
            and rows[1]['stage'] == 'declared_public_certificate_admission_completed'
        controls['real_public_certificate_admission_executed_between_stages'] = len(v10.public_CA_bundles) == 5 \
            and helper.admitted_certificates_unchanged(output)
        journal_nodes = [node for node in ast.walk(tree10) if journal_statement(node)]
        covered = {prelude[0].lineno, prelude[2].lineno}
        for node in sorted(journal_nodes, key=lambda item: item.lineno):
            if node.lineno in covered:
                continue
            exec(compile(ast.fix_missing_locations(ast.Module(body=[deepcopy(node)], type_ignores=[])),
                         '<exact V10 journal call dependency coverage>', 'exec'), v10.__dict__)
            covered.add(node.lineno)
        rows = [json.loads(line) for line in (output / 'worker-stages.jsonl').read_text().splitlines()]
        controls['all_nine_exact_journal_call_sites_execute_with_real_globals'] = len(rows) == len(journal_nodes) == len(covered) == 9
        controls['all_stage_records_have_only_stage_and_valid_UTC_timestamp'] = all(set(row) == {'stage', 'utc'}
            and datetime.fromisoformat(row['utc']).utcoffset().total_seconds() == 0 for row in rows)
        helper_raw = (ROOT / 'scripts/ap2_public_certificate_guard_v10.py').read_bytes()
        helper_old = (ROOT / 'scripts/ap2_public_certificate_guard_v9.py').read_text()
        normalized_helper = helper_raw.decode().replace('\r\n', '\n').replace('v10', 'v9').replace('V10', 'V9').replace('/10', '/9')
        controls['certificate_guard_semantics_unchanged_after_version_labels'] = normalized_helper == helper_old
        evaluator_raw = (ROOT / 'scripts/evaluate_ap2_native_bridge_matrix_v10.py').read_bytes()
        controls['strict_zero_external_network_operation_gate_preserved'] = \
            "separation['denials']['external_network_operations_blocked'] == 0" in evaluator_raw.decode()
    report = {'schema_version': 'ap2-v10-exact-stage-prelude-independent-peer-control/1',
              'reviewed_utc': datetime.now(timezone.utc).isoformat(), 'passed': all(controls.values()), 'controls': controls,
              'source_identities': {'scripts/ap2_reference_development_v9.py': identity(raw9),
                'scripts/ap2_reference_development_v10.py': identity(raw10),
                'scripts/ap2_public_certificate_guard_v10.py': identity(helper_raw),
                'scripts/evaluate_ap2_native_bridge_matrix_v10.py': identity(evaluator_raw)},
              'frozen_V9_constructed_error_name': old_name_error,
              'covered_V10_journal_source_lines': sorted(covered), 'constructed_stage_records': rows,
              'new_application_or_provider_calls': 0, 'new_actor_or_bridge_processes_executed': 0,
              'append_now_writer_and_certificate_admission_stubbed': False,
              'scope': 'Executes exact extracted new journal/admission statements against owned public source/CA fixtures using actual actor globals and actual certificate helper. The remaining journal calls are independent dependency controls, not execution of original application/SDK/guarded worker. V9 stays frozen; V8 unknown external operation remains unqualified.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'controls': len(controls), 'covered_journal_calls': len(covered),
                      'failed': [name for name, passed in controls.items() if not passed]}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
