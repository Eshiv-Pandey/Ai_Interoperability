"""Independent read-only audit of the retained V8 pre-capture guard failure."""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CERTIFICATES = ('code/samples/certs/ds_cert_sdjwt.pem', 'code/samples/certs/issuer_cert_sdjwt.pem')


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--markdown', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.markdown.exists():
        raise ValueError('fresh_actual_failure_audit_required')
    archive = args.archive.absolute()
    hasher = hashlib.sha256()
    with archive.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            hasher.update(block)
    raw_inputs = {}
    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())

        def get(name):
            info = bundle.getinfo(name)
            if info.file_size > 4 * 1024 * 1024:
                raise ValueError('selected_capture_entry_bound')
            value = bundle.read(info)
            raw_inputs[name] = identity(value)
            return value

        def read(name):
            return json.loads(get(name))

        base = 'smoke/conventional/'
        result = read(base + 'result.json')
        failure = read(base + 'worker-failure.json')
        separation = read(base + 'actor-input-separation.json')
        plan = read(base + 'plan.json')
        runner = get(base + 'source-runner.py')
        owned_runner = get(base + 'owned-source/scripts/ap2_reference_development_v8.py')
        stderr, stdout = get(base + 'stderr.txt'), get(base + 'stdout.txt')
        stage = read(base + 'source-stage-manifest.json')
        public = read('matrix/public-manifest.json')
        allocation = read('matrix/allocation-manifest.json')
        execution = read('matrix/execution-results.json')
        evaluated = read('independent-evaluation/result.json')
        certificate_rows = []
        for name in CERTIFICATES:
            raw = get(base + 'original-source/' + name)
            stage_row = next(row for row in stage['files'] if row['project'] == 'ap2' and row['path'] == name)
            certificate_rows.append({'source_path': name, 'identity': identity(raw),
                'manifest_identity_matches': identity(raw) == {key: stage_row[key] for key in ('bytes', 'sha256')},
                'public_certificate_marker': raw.startswith(b'-----BEGIN CERTIFICATE-----'),
                'private_key_marker_present': b'PRIVATE KEY' in raw})
    tree = ast.parse(runner)
    worker = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'worker')
    declaration = next(node for node in worker.body if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == 'public_CA_bundles' for target in node.targets))
    hook = next(node for node in worker.body if isinstance(node, ast.FunctionDef) and node.name == 'public_only_actor')
    original_guard_rejections = {}
    with tempfile.TemporaryDirectory(prefix='ap2-v8-failure-guard-peer-') as temporary:
        site = Path(temporary).resolve() / 'supplied-nonexecuted-site-packages'
        namespace = {'Path': Path, 'os': os, 'ROOT': ROOT, 'site_packages': site,
                     'audit_state': {'private_root': Path(temporary).resolve() / 'owned-private-profile'},
                     'denials': {'private_reads_blocked': 0}, 'plan': {}, 'output': Path(temporary)}
        extracted = ast.fix_missing_locations(ast.Module(body=[deepcopy(declaration), deepcopy(hook)], type_ignores=[]))
        exec(compile(extracted, str(archive) + ':source-runner.py', 'exec'), namespace)
        for name in CERTIFICATES:
            represented_path = ROOT / 'runs/ap2-environment-preparation/source-stage-v1/ap2' / name
            try:
                namespace['public_only_actor']('open', (str(represented_path), 'r', None))
                denied, reason = False, None
            except PermissionError as error:
                denied, reason = True, str(error)
            original_guard_rejections[name] = {'denied': denied, 'reason': reason,
                'constructed_open_event_only': True, 'represented_file_opened': False}
        pip_path = site / 'pip/_vendor/certifi/cacert.pem'
        try:
            namespace['public_only_actor']('open', (str(pip_path), 'r', None))
            pip_denied = False
        except PermissionError:
            pip_denied = True
    excluded = ['runtime-manifest.json', 'original-callable-code-checks.json', 'source-tool-invocations.json',
                'native-servers-started.json', 'native-wire-attempts.jsonl', 'native-wire-responses.jsonl',
                'native-socket-cleanup.json', 'original-state-before.json', 'original-state-after.json',
                'application-outcome.json', 'observations/events.jsonl', 'observations/terminal.json']
    present = [name for name in excluded if base + name in names]
    expected = [(case['id'], arm['id']) for case in public['cases'] for arm in public['arms']]
    controls = {
        'retained_runner_equals_declared_and_owned_copy': identity(runner) == plan['owned_components']['scripts/ap2_reference_development_v8.py']
            and runner == owned_runner and identity(runner) == allocation['runner'],
        'actual_guard_error_retained': result['returncode'] == 3 and failure['error_type'] == 'PermissionError'
            and failure['reason'] == 'actor_private_evaluator_or_saved_credential_read_denied',
        'no_first_SDK_callable_or_native_capture_retained': present == [],
        'empty_stdout_stderr_and_no_traceback_retained': stdout == stderr == b'' and 'traceback' not in failure,
        'all_104_preallocated_cells_untouched': len(expected) == allocation['declared_cells'] == execution['declared_cells'] == len(execution['cells']) == 104
            and [(row['case_id'], row['arm_id']) for row in execution['cells']] == expected
            and all(row['returncode'] is None and row['allocation_status'] == 'not_executed_before_workflow_finalization' for row in execution['cells'])
            and not any(name.startswith('matrix/attempts/') for name in names),
        'independent_matrix_evaluation_preserves_104_missing_zero_verified': evaluated['declared_cells'] == evaluated['totals']['missing_cells'] == 104
            and evaluated['totals']['verified_captures'] == evaluated['totals']['verified_purchases'] == 0,
        'both_original_source_snapshots_are_declared_public_certificates': all(row['manifest_identity_matches']
            and row['public_certificate_marker'] and not row['private_key_marker_present'] for row in certificate_rows),
        'exact_retained_guard_rejects_both_required_public_source_cert_paths': all(row['denied'] for row in original_guard_rejections.values()),
    }
    lines = runner.decode().splitlines()
    anchors = {label: [i + 1 for i, line in enumerate(lines) if text in line] for label, text in (
        ('source_inventory_reads_every_file', 'result[path.relative_to(directory).as_posix()] = digest(path.read_bytes())'),
        ('source_contract_verifies_complete_original_union', 'need(inventory(SOURCE) == expected'),
        ('source_contract_before_runtime_inventory', 'stage_raw, source_files = source_contract()'),
        ('runtime_inventory_before_runtime_manifest', 'runtime_files = inventory(site_packages)'),
        ('two_installed_CA_paths_only', 'public_CA_bundles ='),
        ('other_outside_profile_PEM_denied', "path.suffix.lower() in {'.pem', '.key'}"),
        ('failure_handler_omits_traceback', "write(output / 'worker-failure.json'"))}
    report = {'schema_version': 'ap2-v8-actual-smoke-failure-independent-peer-audit/1',
              'reviewed_utc': datetime.now(timezone.utc).isoformat(), 'run_id': 42897325489,
              'archive': {'path': str(archive), 'bytes': archive.stat().st_size, 'sha256': hasher.hexdigest()},
              'passed': all(controls.values()), 'controls': controls, 'input_identities': raw_inputs,
              'actual_smoke_result': result, 'actual_worker_failure': failure, 'actual_separation_receipt': separation,
              'declared_cells': 104, 'actual_matrix_evaluation_totals': evaluated['totals'],
              'retained_capture_files_present': present, 'missing_expected_capture_files': excluded,
              'public_original_certificates': certificate_rows, 'production_guard_constructed_rejections': original_guard_rejections,
              'retained_runner_line_anchors': anchors,
              'additional_runtime_inventory_gap': {'relative_path': 'pip/_vendor/certifi/cacert.pem',
                    'production_guard_rejects_supplied_path': pip_denied,
                    'actual_V8_installed_file_or_denied_path_retained': False,
                    'status': 'additional_source_conflict_if_present_in_fresh_installed_runtime'},
              'actual_cause_precision': 'The actual exception is a private-read guard denial. V8 omitted the denied path and traceback, so the exact observed file cannot be identified. Independently reconstructed exact guard necessarily rejects its required original-source public certificate paths during source_contract, before runtime inventory, if that source-verification statement is reached.',
              'new_application_or_provider_calls': 0, 'new_actor_or_bridge_processes_executed': 0,
              'represented_key_or_evaluator_files_opened': 0, 'frozen_V8_or_original_source_mutated': False}
    for path in (args.output, args.markdown):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    args.markdown.write_text('\n'.join([
        '# AP2 V8 actual smoke failure: independent peer audit', '',
        'Hosted run 42897325489 retained a conventional smoke return code 3 and PermissionError '
        'actor_private_evaluator_or_saved_credential_read_denied. The actual stdout and stderr are empty; '
        'the failure handler retained neither traceback nor denied path.', '',
        'No runtime manifest, first SDK callable check, source-tool invocation, native-server/wire receipt or durable observation was retained. '
        'All 104 prospectively allocated matrix cells stayed untouched and missing. The separate matrix evaluator retained 104 missing, '
        'zero verified captures and zero verified purchases. This is a harness guard failure before retained application observation, '
        'not an observed interoperability or algorithm failure.', '',
        'The captured source has a concrete conflict: source_contract inventories every original source file, including the declared public '
        'ds_cert_sdjwt.pem and issuer_cert_sdjwt.pem certificates. Their actual archived bytes match the frozen stage manifest, begin with '
        'BEGIN CERTIFICATE and contain no PRIVATE KEY marker. The exact retained audit hook rejects both reconstructed original-source paths '
        'because its PEM exemptions name only the two installed certifi/gRPC CA files. This source conflict occurs before runtime inventory '
        'when source verification is reached; it does not identify the omitted actual denied path.', '',
        'The same retained guard also rejects a supplied pip/_vendor/certifi/cacert.pem path. The actual V8 installed-runtime file inventory '
        'is absent, so that additional conflict is conditional on the fresh runtime containing the vendored public CA.', '',
        f"The JSON receipt binds the actual archive and selected input bytes and records {len(controls)} passing audit controls. "
        'The reconstructed guard checks opened no represented certificate/key/evaluator file and executed no original application, provider or bridge. '
        'V8 code, earlier controls, the allocation and original application/SDK bodies remain unchanged.', '',
        'A prospective successor should retain the exact denied-path/traceback diagnostics and exempt only declared, source/runtime-bound public '
        'certificate files needed for its inventory. Saved/private signing keys, credentials, private evaluators and unowned network operations '
        'remain outside those exemptions.', '',
    ]), encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'controls': len(controls), 'run_id': report['run_id'],
                      'actual_captured_native_exchanges': 0, 'declared_unexecuted_matrix_cells': 104}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
