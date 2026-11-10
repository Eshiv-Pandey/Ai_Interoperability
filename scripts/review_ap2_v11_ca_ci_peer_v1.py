"""Independent real pinned-CA, safe diagnostic and source-delta V11 controls."""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = ('scripts/ap2_public_certificate_guard_v11.py', 'scripts/evaluate_ap2_native_bridge_matrix_v11.py',
         'scripts/ap2_reference_development_v11.py', 'scripts/run_ap2_native_bridge_matrix_v11.py',
         'scripts/ap2_bridge_client_v11.mjs', 'scripts/ap2_bridge_network_guard_v11.mjs',
         'scripts/ap2_native_bridge_runtime_v11.py', 'src/interoperability/ap2_native_transport_v11.py',
         'scripts/print_ap2_owned_cell_diagnostics_v1.py', 'scripts/run_ap2_cell_with_safe_diagnostics_v1.py',
         '.github/workflows/ap2-native-bridge-development-v11.yml',
         'benchmark/ap2-native-bridge-development-v11/application.json',
         'benchmark/ap2-native-bridge-development-v11/evaluator.json',
         'docs/research/ap2-native-bridge-development-v11.md')
WHEEL_SHA = '55cee7cfe71b29f6b377681936f9a5f35e59f5c941a4d84e2712cb309753e7a9'
MEMBER = 'grpc/_cython/_credentials/roots.pem'


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def load(name, path):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
    return module


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def normalized(raw):
    return raw.decode('utf-8-sig').replace('\r\n', '\n').replace('v11', 'v10').replace('V11', 'V10') \
        .replace('/11', '/10').replace("'11.0.0'", "'10.0.0'")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('fresh_V11_real_CA_CI_peer_receipt_required')
    blobs = {name: (ROOT / name).read_bytes() for name in FILES}
    wheel_raw = args.wheel.read_bytes()
    if identity(wheel_raw)['sha256'] != WHEEL_SHA:
        raise ValueError('exact_actual_V10_pip_pinned_wheel_required')
    with zipfile.ZipFile(args.wheel) as wheel:
        roots = wheel.read(MEMBER)
    helper = load('_v11_real_CA_independent_peer', ROOT / FILES[0])
    evaluator = load('_v11_CA_evaluator_independent_peer', ROOT / FILES[1])
    printer = load('_safe_AP2_CI_printer_independent_peer', ROOT / FILES[8])
    launcher = load('_safe_AP2_CI_launcher_independent_peer', ROOT / FILES[9])
    checks = {}

    def check(name, value, detail=None):
        checks[name] = {'passed': bool(value), 'detail': detail}

    def reject(name, callback):
        try:
            callback()
        except (ValueError, OSError, UnicodeError) as error:
            check(name, True, type(error).__name__ + ': ' + str(error)[:300])
        else:
            check(name, False, 'unexpected acceptance')

    check('real_pinned_grpc_99_certificates_accepted_only_at_declared_path',
          helper.certificate_count(roots, declared_runtime_path=MEMBER) == 99)
    reject('same_exact_metadata_without_runtime_path_rejected', lambda: helper.certificate_count(roots))
    reject('same_exact_metadata_at_certifi_path_rejected', lambda: helper.certificate_count(roots, declared_runtime_path='certifi/cacert.pem'))
    reject('changed_public_annotation_hash_rejected', lambda: helper.certificate_count(roots + b'\nChanged public text\n', declared_runtime_path=MEMBER))
    reject('added_private_PEM_block_rejected', lambda: helper.certificate_count(roots + b'\n-----BEGIN PRIVATE KEY-----\nQUJD\n-----END PRIVATE KEY-----\n', declared_runtime_path=MEMBER))
    reject('extra_certificate_block_breaks_exact_bundle_binding', lambda: helper.certificate_count(roots + roots[roots.index(b'-----BEGIN CERTIFICATE-----'):], declared_runtime_path=MEMBER))
    with tempfile.TemporaryDirectory(prefix='ap2-v11-real-CA-CI-peer-') as temporary:
        base = Path(temporary).resolve()
        source, runtime, output = base / 'source', base / 'runtime', base / 'output'
        output.mkdir()
        originals, runtime_files = {}, {}
        original_bytes = []
        for name, pinned in helper.SOURCE_PUBLIC_CERTIFICATES.items():
            raw = (ROOT / 'runs/ap2-environment-preparation/source-stage-v1/ap2' / name).read_bytes()
            if identity(raw) != pinned:
                raise ValueError('actual_original_public_certificate_fixture_changed')
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            originals[name] = identity(raw)
            original_bytes.append(raw)
        for name in helper.RUNTIME_PUBLIC_CA_PATHS:
            raw = roots if name == MEMBER else b'\n'.join(original_bytes)
            path = runtime / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            runtime_files[name] = identity(raw)
        admitted = helper.prepare_public_certificates(output, source, runtime, write)
        write(output / 'runtime-manifest.json', {'root': str(runtime), 'files': runtime_files})
        check('actual_grpc_fixture_full_five_file_admission_and_independent_evaluation',
              len(admitted) == 5 and evaluator.verify_public_certificate_admissions(output, originals) == 5)
        receipt_path = output / 'public-certificate-admission.json'
        receipt = json.loads(receipt_path.read_bytes())
        grpc_record = next(row for row in receipt['records'] if row['relative_path'] == MEMBER)
        check('retained_grpc_bytes_and_99_count_bound_to_actual_fixture',
              (output / grpc_record['retained_path']).read_bytes() == roots
              and grpc_record['identity'] == identity(roots) and grpc_record['certificate_blocks'] == 99)
        retained = output / grpc_record['retained_path']
        retained.write_bytes(roots + b'\nChanged public text\n')
        changed = deepcopy(receipt)
        next(row for row in changed['records'] if row['relative_path'] == MEMBER)['identity'] = identity(retained.read_bytes())
        write(receipt_path, changed)
        reject('evaluator_modified_copy_and_receipt_hash_not_runtime_binding', lambda: evaluator.verify_public_certificate_admissions(output, originals))
        write(receipt_path, receipt)
        retained.write_bytes(roots)
        cell = base / 'diagnostic-cell'
        cell.mkdir()
        frame = {'file': '<REPOSITORY>/scripts/ap2_reference_development_v11.py', 'function': 'worker', 'line': 721}
        write(cell / 'worker-failure.json', {'error_type': 'ValueError', 'reason': 'CONSTRUCTED_SECRET_REASON',
              'frames': [frame, {'file': '/outside/CONSTRUCTED_SECRET_PATH', 'function': 'CONSTRUCTED_SECRET_FUNCTION', 'line': 1}],
              'headers': {'authorization': 'CONSTRUCTED_SECRET_HEADER'}, 'locals': 'CONSTRUCTED_SECRET_LOCAL'})
        (cell / 'actor-guard-denials.jsonl').write_text(json.dumps({'operation': 'socket.bind',
            'guard_code': 'native_actor_unowned_network_operation_denied', 'path': '/outside/CONSTRUCTED_SECRET_KEY.pem',
            'network_endpoint': {'host': 'CONSTRUCTED_SECRET_HOST', 'port': 443, 'socket_family': 10, 'socket_type': 1},
            'frames': [{'file': '<SITE_PACKAGES>/urllib3/util/connection.py', 'function': '_has_ipv6', 'line': 109}]}))
        (cell / 'worker-stages.jsonl').write_text(json.dumps({'stage': 'before_declared_public_certificate_admission', 'extra': 'CONSTRUCTED_SECRET_EXTRA'}))
        emitted = []
        printer.print_diagnostics(cell, 3, emit=emitted.append)
        safe = '\n'.join(emitted)
        safe_rows = [json.loads(row) for row in emitted]
        check('safe_printer_retains_returncode_error_type_and_known_frames', safe_rows[0]['returncode'] == 3
              and any(row.get('error_type') == 'ValueError' for row in safe_rows)
              and any(frame == item for row in safe_rows for item in row.get('frames', [])))
        check('safe_printer_omits_reason_key_path_host_header_locals_extras', 'CONSTRUCTED_SECRET' not in safe)
        check('safe_printer_output_under_32KiB_and_frame_row_bounds', len(safe.encode()) + 1 <= printer.MAX_OUTPUT_BYTES
              and all(len(row.get('frames', [])) <= printer.MAX_FRAMES for row in safe_rows))
        (cell / 'worker-failure.json').write_bytes(b'x' * (printer.MAX_INPUT_BYTES + 1))
        emitted = []
        printer.print_diagnostics(cell, 3, emit=emitted.append)
        check('oversized_diagnostic_not_read_or_printed', any(json.loads(row).get('status') == 'input_bound_exceeded' for row in emitted))
        count = base / 'constructed-child-count.txt'
        child = base / 'constructed-only-diagnostic-program.py'
        child.write_text('from pathlib import Path\nimport sys\np=Path(sys.argv[1]);p.write_text(str(int(p.read_text())+1) if p.exists() else "1")\nprint("CONSTRUCTED_SECRET_RAW_STDOUT")\nprint("CONSTRUCTED_SECRET_RAW_STDERR",file=sys.stderr)\nraise SystemExit(3)\n')
        printed = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = printed
        try:
            returncode = launcher.run_once(cell, base / 'launcher-logs', [sys.executable, '-I', '-S', '-B', str(child), str(count)])
        finally:
            sys.stdout = old_stdout
        check('once_only_constructed_command_preserves_actual_nonzero_code', returncode == 3 and count.read_text() == '1')
        check('raw_streams_retained_locally_but_not_echoed_by_safe_launcher', 'CONSTRUCTED_SECRET' not in printed.getvalue()
              and 'CONSTRUCTED_SECRET_RAW_STDOUT' in (base / 'launcher-logs/stdout.txt').read_text()
              and 'CONSTRUCTED_SECRET_RAW_STDERR' in (base / 'launcher-logs/stderr.txt').read_text())
        reject('existing_launcher_attempt_not_replayed', lambda: launcher.run_once(cell, base / 'launcher-logs', [sys.executable, '-c', 'raise SystemExit(0)']))
        check('existing_attempt_control_did_not_repeat_constructed_child', count.read_text() == '1')
    actor = ast.dump(ast.parse(normalized(blobs[FILES[2]])), include_attributes=False)
    old_actor = ast.dump(ast.parse((ROOT / 'scripts/ap2_reference_development_v10.py').read_bytes()), include_attributes=False)
    check('actor_executable_AST_unchanged_after_version_labels', actor == old_actor)
    normalized_equal = {name: normalized(blobs[name]) == (ROOT / name.replace('v11', 'v10')).read_text() for name in FILES[4:8]}
    check('four_native_Node_bridge_components_unchanged', all(normalized_equal.values()), normalized_equal)
    check('strict_zero_external_network_gate_retained', "separation['denials']['external_network_operations_blocked'] == 0" in blobs[FILES[1]].decode())
    old = json.loads((ROOT / 'benchmark/ap2-native-bridge-development-v10/application.json').read_bytes())
    new = json.loads(blobs[FILES[11]])
    check('13_cases_eight_flags_104_slots_and_34_candidates_unchanged', new['cases'] == old['cases']
          and len(new['cases']) == 13 and len(new['arms']) == 8 and new['declared_cells'] == 104 and new['source_bank_candidates'] == 34
          and [{key: value for key, value in row.items() if key != 'description'} for row in new['arms']] ==
              [{key: value for key, value in row.items() if key != 'description'} for row in old['arms']])
    report = {'schema_version': 'ap2-v11-real-pinned-CA-and-CI-independent-peer-review/1',
              'reviewed_utc': datetime.now(timezone.utc).isoformat(), 'passed': all(row['passed'] for row in checks.values()),
              'controls': checks, 'source_identities': {name: identity(raw) for name, raw in blobs.items()},
              'trusted_wheel_identity': identity(wheel_raw), 'trusted_root_bundle_identity': identity(roots),
              'new_original_application_or_provider_calls': 0, 'new_original_actor_or_bridge_processes': 0,
              'constructed_diagnostic_program_dispatches': 1, 'original_grpc_or_SDK_modules_imported': False,
              'scope': 'Real CA fixture comes from exact wheel pinned by actual V10 install report. Narrow path/file/remainder/X509 acceptance and independent evaluator binding checked. Safe output exercised with supplied sentinel diagnostics and one constructed Python program, not original AP2 code. V10 failed installed-file bytes remain absent; frozen V10 and original application/SDK bodies were not changed.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'controls': len(checks), 'real_CA_certificates': 99,
                      'failed': [name for name, row in checks.items() if not row['passed']]}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
