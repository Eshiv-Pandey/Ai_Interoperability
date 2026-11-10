"""Independent bounded V9 public-certificate/guard/evaluator peer controls."""
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
import types

ROOT = Path(__file__).resolve().parents[1]
FILES = ('scripts/ap2_public_certificate_guard_v9.py', 'scripts/ap2_reference_development_v9.py',
         'scripts/evaluate_ap2_native_bridge_matrix_v9.py', 'scripts/run_ap2_native_bridge_matrix_v9.py',
         'scripts/ap2_bridge_client_v9.mjs', 'scripts/ap2_bridge_network_guard_v9.mjs',
         'scripts/ap2_native_bridge_runtime_v9.py', 'src/interoperability/ap2_native_transport_v9.py',
         '.github/workflows/ap2-native-bridge-development-v9.yml',
         'benchmark/ap2-native-bridge-development-v9/application.json',
         'benchmark/ap2-native-bridge-development-v9/evaluator.json',
         'docs/research/ap2-native-bridge-development-v9.md')


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def load(name, source):
    module = types.ModuleType(name)
    module.__file__ = str(ROOT / source)
    exec(compile((ROOT / source).read_bytes(), str(module.__file__), 'exec'), module.__dict__)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--markdown', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.markdown.exists():
        raise ValueError('fresh_V9_peer_receipts_required')
    blobs = {name: (ROOT / name).read_bytes() for name in FILES}
    helper = load('_v9_public_certificate_independent_peer', FILES[0])
    evaluator = load('_v9_public_certificate_evaluator_independent_peer', FILES[2])
    actor = ast.parse(blobs[FILES[1]])
    worker = next(node for node in actor.body if isinstance(node, ast.FunctionDef) and node.name == 'worker')
    hook = next(node for node in worker.body if isinstance(node, ast.FunctionDef) and node.name == 'public_only_actor')
    controls = {}

    def check(label, condition, detail=None):
        controls[label] = {'passed': bool(condition), 'detail': detail}

    def rejects(label, callback):
        try:
            callback()
        except (ValueError, PermissionError, UnicodeError, OSError) as error:
            check(label, True, {'error_type': type(error).__name__, 'reason': str(error)[:500]})
        else:
            check(label, False, 'unexpected acceptance')

    with tempfile.TemporaryDirectory(prefix='ap2-v9-independent-cert-peer-') as temporary:
        base = Path(temporary).resolve()
        source, runtime, output = base / 'source', base / 'runtime', base / 'output'
        output.mkdir()
        originals = {}
        for name, pinned in helper.SOURCE_PUBLIC_CERTIFICATES.items():
            raw = (ROOT / 'runs/ap2-environment-preparation/source-stage-v1/ap2' / name).read_bytes()
            check('original_pinned_public_certificate_' + Path(name).stem, identity(raw) == pinned
                  and raw.startswith(b'-----BEGIN CERTIFICATE-----') and b'PRIVATE KEY' not in raw)
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            originals[name] = identity(raw)
        bundle = b'\n'.join((source / name).read_bytes() for name in originals)
        runtime_files = {}
        for name in helper.RUNTIME_PUBLIC_CA_PATHS:
            path = runtime / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(bundle)
            runtime_files[name] = identity(bundle)
        allowed = helper.prepare_public_certificates(output, source, runtime, write)
        receipt_path = output / 'public-certificate-admission.json'
        receipt = json.loads(receipt_path.read_bytes())
        write(output / 'runtime-manifest.json', {'root': str(runtime), 'files': runtime_files})
        check('exact_five_declared_source_runtime_public_files', len(allowed) == 5 and allowed == {
            source / name for name in originals} | {runtime / name for name in runtime_files})
        check('independent_evaluator_accepts_all_bound_public_copies',
              evaluator.verify_public_certificate_admissions(output, originals) == 5)
        check('admitted_original_files_unchanged', helper.admitted_certificates_unchanged(output))
        changed = deepcopy(receipt)
        changed['records'].append(deepcopy(changed['records'][0]))
        write(receipt_path, changed)
        rejects('duplicate_public_certificate_record_rejected', lambda: evaluator.verify_public_certificate_admissions(output, originals))
        changed = deepcopy(receipt)
        changed['records'][0]['source_path'] = str(base / 'unbound/certificate.pem')
        write(receipt_path, changed)
        rejects('original_source_path_rebinding_rejected', lambda: evaluator.verify_public_certificate_admissions(output, originals))
        changed = deepcopy(receipt)
        changed['records'][-1]['identity']['sha256'] = '0' * 64
        write(receipt_path, changed)
        rejects('runtime_copy_hash_rebinding_rejected', lambda: evaluator.verify_public_certificate_admissions(output, originals))
        write(receipt_path, receipt)
        extra = output / 'public-certificate-admission/undeclared.key'
        extra.write_bytes(b'CONSTRUCTED_NOT_A_SAVED_KEY')
        rejects('extra_undeclared_public_copy_rejected', lambda: evaluator.verify_public_certificate_admissions(output, originals))
        extra.unlink()
        path = runtime / helper.RUNTIME_PUBLIC_CA_PATHS[0]
        path.write_bytes(bundle + b'# changed after admission\n')
        check('admitted_runtime_CA_change_detected', not helper.admitted_certificates_unchanged(output))
        path.write_bytes(bundle)
        rejects('private_key_label_not_a_public_certificate', lambda: helper.certificate_count(
            b'-----BEGIN PRIVATE KEY-----\nCONSTRUCTED_NOT_A_SAVED_KEY\n-----END PRIVATE KEY-----\n'))
        rejects('malformed_X509_not_a_public_certificate', lambda: helper.certificate_count(
            b'-----BEGIN CERTIFICATE-----\nQUJD\n-----END CERTIFICATE-----\n'))
        rejects('non_comment_extra_PEM_payload_rejected', lambda: helper.certificate_count(bundle + b'\nCONSTRUCTED_PAYLOAD\n'))
        check('certificate_only_public_comment_bundle_accepted', helper.certificate_count(bundle + b'\n# public fixture comment\n') == 2)
        state = {'private_root': None, 'bridge_client_dispatched': False, 'diagnostic_rows': 0,
                 'expected_private_evaluator_probe': False}
        roots = {'SOURCE': source, 'SITE_PACKAGES': runtime, 'REPOSITORY': base}
        namespace = {'Path': Path, 'os': os, 'ROOT': base, 'output': output, 'audit_state': state,
                     'public_CA_bundles': allowed, 'record_denial': helper.record_denial, 'guard_roots': lambda: roots,
                     'denials': {'private_reads_blocked': 0, 'external_network_operations_blocked': 0,
                                 'allowed_owned_loopback_operations': 0, 'unallocated_descendant_processes_blocked': 0,
                                 'allowed_allocated_bridge_client_processes': 0},
                     'plan': {'node': {'executable': '/nonexecuted-node'}, 'policy': {}}}
        extracted = ast.fix_missing_locations(ast.Module(body=[deepcopy(hook)], type_ignores=[]))
        exec(compile(extracted, '<exact V9 peer audit hook>', 'exec'), namespace)
        guard = namespace['public_only_actor']
        modes_passed = True
        for path in allowed:
            for mode in (None, 'r', 'rb'):
                try:
                    guard('open', (str(path), mode, os.O_RDONLY))
                except PermissionError:
                    modes_passed = False
        check('every_declared_public_file_read_modes_accepted', modes_passed)
        public = next(iter(allowed))
        for label, mode, flags in (('write', 'w', os.O_WRONLY), ('readwrite', 'r+', os.O_RDWR),
                                   ('flag_readwrite', None, os.O_RDWR), ('flag_create', None, os.O_CREAT),
                                   ('flag_truncate', None, os.O_TRUNC), ('flag_append', None, os.O_APPEND)):
            rejects('public_certificate_' + label + '_bypass_rejected',
                    lambda mode=mode, flags=flags: guard('open', (str(public), mode, flags)))
        for label, path in (('saved_PEM', base / 'saved-key.pem'), ('saved_KEY', base / 'saved-key.key'),
                            ('neighbor_CA_basename', runtime / 'unbound/cacert.pem'),
                            ('dotenv', base / '.env'), ('Gemini_key_name', base / 'gemini-api-key-secret.txt'),
                            ('private_evaluator', base / 'benchmark/ap2-native-bridge-development-v9/evaluator.json')):
            rejects(label + '_read_rejected', lambda path=path: guard('open', (str(path), 'r', os.O_RDONLY)))
        rejects('external_network_operation_still_rejected', lambda: guard('socket.getaddrinfo',
                ('CONSTRUCTED_SECRET_HOST.invalid', 443, 0, 0, 0)))
        check('strict_external_operation_counter_not_masked', namespace['denials']['external_network_operations_blocked'] == 1)
        rejects('subprocess_arguments_not_admitted', lambda: guard('subprocess.Popen',
                ('outside', ['CONSTRUCTED_SECRET_ARGUMENT'], None, None)))
        diagnostics = (output / 'actor-guard-denials.jsonl').read_text()
        rows = [json.loads(row) for row in diagnostics.splitlines()]
        check('diagnostics_omit_argument_and_external_host_values', 'CONSTRUCTED_SECRET_ARGUMENT' not in diagnostics
              and 'CONSTRUCTED_SECRET_HOST' not in diagnostics)
        check('diagnostics_only_bounded_frames_without_sensitive_fields', all(
            0 < len(row['frames']) <= 24 and row['contents_arguments_locals_headers_and_environment_retained'] is False
            and all(set(frame) == {'file', 'function', 'line'} for frame in row['frames']) for row in rows))
        for _ in range(66):
            helper.record_denial(output, state, 'constructed_guard_operation', 'constructed_guard_code', roots,
                                 path=base.parent / 'CONSTRUCTED_SECRET_PATH.pem')
        rows = [json.loads(row) for row in (output / 'actor-guard-denials.jsonl').read_text().splitlines()]
        check('diagnostics_stop_at_64_ordered_rows', len(rows) == 64 and state.get('diagnostic_bound_reached') is True
              and [row['index'] for row in rows] == list(range(64)))
        check('outside_declared_path_name_redacted', 'CONSTRUCTED_SECRET_PATH' not in json.dumps(rows))
    code = blobs[FILES[2]].decode()
    check('evaluator_requires_zero_external_network_operations', "separation['denials']['external_network_operations_blocked'] == 0" in code)
    old = json.loads((ROOT / 'benchmark/ap2-native-bridge-development-v8/application.json').read_bytes())
    new = json.loads(blobs[FILES[9]])
    check('same_13_cases_and_eight_policy_flags', new['cases'] == old['cases'] and len(new['cases']) == 13
          and [{k: v for k, v in row.items() if k != 'description'} for row in new['arms']] ==
              [{k: v for k, v in row.items() if k != 'description'} for row in old['arms']])
    check('same_104_cell_denominator_and_34_source_candidates', new['declared_cells'] == 104 and new['source_bank_candidates'] == 34)
    normalized_equal = {}
    for name in FILES[3:8]:
        old_name = name.replace('v9', 'v8')
        text = blobs[name].decode().replace('\r\n', '\n')
        normalized = text.replace('v9', 'v8').replace('V9', 'V8').replace('/9', '/8').replace("'9.0.0'", "'8.0.0'")
        normalized_equal[name] = normalized == (ROOT / old_name).read_text()
    check('five_low_level_components_unchanged_after_version_normalization', all(normalized_equal.values()), normalized_equal)
    report = {'schema_version': 'ap2-v9-public-certificate-guard-independent-peer-review/1',
              'reviewed_utc': datetime.now(timezone.utc).isoformat(), 'passed': all(row['passed'] for row in controls.values()),
              'controls': controls, 'reviewed_source_identities': {name: identity(raw) for name, raw in blobs.items()},
              'original_public_certificate_identities': originals,
              'constructed_fixture_only': True, 'new_application_or_provider_calls': 0,
              'new_actor_or_bridge_processes_executed': 0, 'saved_private_key_or_evaluator_files_read': 0,
              'scope': 'Exact extracted production read guard, public-certificate helper and separate evaluator executed against owned supplied public fixtures. Diagnostics contain bounded declared-root path/frame metadata only. Source-bound controls are not an OS sandbox. Actual V8 external-operation caller remains unknown; strict V9 zero-operation gate was preserved.'}
    for path in (args.output, args.markdown):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    args.markdown.write_text('\n'.join(['# AP2 V9 focused independent public-certificate and guard review', '',
        f"{len(controls)} bounded independent controls passed: {report['passed']}. The receipt hashes {len(FILES)} reviewed files. "
        'No original application, provider, actor or bridge process was executed.', '',
        'The helper admits the exact two pinned original public certificates and three declared installed public CA paths, '
        'parses certificate-only PEM with stdlib SSL, and retains identified copies. The separate evaluator checks source/runtime/copy identity, '
        'record completeness, X.509 structure and hidden extra files. Public read modes are accepted; writable flags, neighboring paths, saved PEM/KEY, '
        'dotenv, Gemini key names and private evaluator reads are denied.', '',
        'Diagnostics are capped at 64 ordered rows with 24 bounded frame records. Supplied arguments, external hosts, undeclared paths and frame locals '
        'are absent from the constructed diagnostic output. Original task/policy inputs, 104-cell denominator and the five low-level transport/bridge '
        'components are unchanged after explicit version-label normalization.', '',
        'The strict evaluator still requires zero blocked external network operations. V8 recorded one unidentified operation; this review neither '
        'attributes it nor allows it. A future actual diagnostic receipt must establish any further obstruction. '
        'These source-bound controls do not qualify canonical runtime, application performance, human gold or checkpoint credit.', '',
    ]), encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'controls': len(controls),
                      'failed': [name for name, row in controls.items() if not row['passed']]}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
