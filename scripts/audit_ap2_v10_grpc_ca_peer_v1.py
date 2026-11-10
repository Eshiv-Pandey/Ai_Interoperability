"""Actual V10 capture plus exact pip-pinned public gRPC wheel reconstruction."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import ssl
import types
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MEMBER = 'grpc/_cython/_credentials/roots.pem'
PEM = rb'-----BEGIN CERTIFICATE-----\s+[A-Za-z0-9+/=\r\n]+-----END CERTIFICATE-----'


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('fresh_V10_grpc_reconstruction_peer_receipt_required')
    base = args.base.resolve()
    retention_raw = (base / 'retention.json').read_bytes()
    retention = json.loads(retention_raw)
    if retention['status'] != 'retained' or retention['run_id'] != 42905259371 or retention['digest_matches_api'] is not True:
        raise ValueError('completed_expected_V10_retention_required')
    archive = base / 'artifact.zip'
    hasher = hashlib.sha256()
    with archive.open('rb') as handle:
        for raw in iter(lambda: handle.read(1024 * 1024), b''):
            hasher.update(raw)
    values, identities = {}, {}
    selected = ('pip-install-report.json', 'smoke/conventional/worker-failure.json',
                'smoke/conventional/worker-stages.jsonl', 'smoke/conventional/result.json',
                'smoke/conventional/owned-source/scripts/ap2_public_certificate_guard_v10.py',
                'matrix/execution-results.json', 'independent-evaluation/result.json')
    with zipfile.ZipFile(archive) as capture:
        names = set(capture.namelist())
        for name in selected:
            raw = capture.read(name)
            if len(raw) > 4 * 1024 * 1024 or raw != (base / 'extracted' / name).read_bytes():
                raise ValueError('capture_archive_extraction_identity_required')
            identities[name] = identity(raw)
            values[name] = raw
        copied = sorted(name for name in names if name.startswith('smoke/conventional/public-certificate-admission/') and not name.endswith('/'))
        copies = {name: identity(capture.read(name)) for name in copied}
    pip = json.loads(values['pip-install-report.json'])
    package = next(row for row in pip['install'] if row['metadata']['name'].lower() == 'grpcio')
    pinned = package['download_info']['archive_info']['hashes']['sha256']
    wheel_raw = args.wheel.read_bytes()
    if hashlib.sha256(wheel_raw).hexdigest() != pinned:
        raise ValueError('actual_V10_pip_pinned_wheel_identity_required')
    with zipfile.ZipFile(args.wheel) as wheel:
        roots = wheel.read(MEMBER)
        license_name = 'grpcio-1.85.0.dist-info/licenses/LICENSE'
        license_raw = wheel.read(license_name)
    blocks = re.findall(PEM, roots)
    remainder = re.sub(PEM, b'', roots)
    starts = re.findall(rb'-----BEGIN ([A-Z0-9 ]+)-----', roots)
    ends = re.findall(rb'-----END ([A-Z0-9 ]+)-----', roots)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(cadata=b'\n'.join(blocks).decode('ascii'))
    der_ids = [hashlib.sha256(ssl.PEM_cert_to_DER_cert(raw.decode('ascii'))).hexdigest() for raw in blocks]
    failure = json.loads(values['smoke/conventional/worker-failure.json'])
    stages = [json.loads(raw) for raw in values['smoke/conventional/worker-stages.jsonl'].splitlines()]
    helper_source = values['smoke/conventional/owned-source/scripts/ap2_public_certificate_guard_v10.py']
    helper = types.ModuleType('_frozen_V10_certificate_peer')
    helper.__file__ = str(base / 'extracted' / selected[4])
    exec(compile(helper_source, helper.__file__, 'exec'), helper.__dict__)
    reconstructed_reason = None
    try:
        helper.certificate_count(roots)
    except ValueError as error:
        reconstructed_reason = str(error)
    execution = json.loads(values['matrix/execution-results.json'])
    evaluation = json.loads(values['independent-evaluation/result.json'])
    expected_copies = {'smoke/conventional/public-certificate-admission/original_source/' + name
                       for name in helper.SOURCE_PUBLIC_CERTIFICATES}
    expected_copies.add('smoke/conventional/public-certificate-admission/installed_runtime/certifi/cacert.pem')
    absent = ('public-certificate-admission.json', 'actor-guard-denials.jsonl', 'actor-input-separation.json',
              'runtime-manifest.json', 'native-servers-started.json', 'native-wire-attempts.jsonl', 'observations/events.jsonl')
    checks = {
        'actual_capture_matches_API_digest_and_selected_extraction': archive.stat().st_size == retention['archive_bytes']
            and hasher.hexdigest() == retention['archive_sha256'] == retention['api_digest'].removeprefix('sha256:'),
        'actual_failure_is_public_certificate_noncomment_content': failure['error_type'] == 'ValueError'
            and failure['reason'] == 'non_certificate_non_comment_PEM_content'
            and any(frame['function'] == 'certificate_count' and frame['line'] == 50 for frame in failure['frames']),
        'only_first_stage_and_three_preceding_public_copies_retained': len(stages) == 1
            and stages[0]['stage'] == 'before_declared_public_certificate_admission' and set(copied) == expected_copies,
        'ordered_next_declared_CA_is_grpc': helper.RUNTIME_PUBLIC_CA_PATHS[:2] == ('certifi/cacert.pem', MEMBER),
        'wheel_is_exact_actual_pip_linux_cp313_grpcio_1_85_0': package['metadata']['version'] == '1.85.0'
            and identity(wheel_raw)['sha256'] == pinned and 'cp313-cp313-manylinux2014_x86_64' in package['download_info']['url'],
        '99_certificate_only_PEM_blocks_parse_as_99_distinct_CA_certificates': len(blocks) == len(starts) == len(ends) == 99
            and starts == ends and set(starts) == {b'CERTIFICATE'} and b'PRIVATE KEY' not in roots and b'PUBLIC KEY' not in roots
            and len(set(der_ids)) == 99 and context.cert_store_stats()['x509_ca'] == 99,
        'public_annotation_remainder_reproduces_exact_frozen_parser_failure': len(remainder) == 379861
            and any(line.strip() and not line.lstrip().startswith(b'#') for line in remainder.splitlines())
            and reconstructed_reason == failure['reason'],
        'no_guard_or_native_runtime_observation_retained': not any('smoke/conventional/' + name in names for name in absent),
        'all104_untouched_and_zero_verified_application_results': len(execution['cells']) == execution['declared_cells'] == 104
            and all(row['returncode'] is None and row['allocation_status'] == 'not_executed_before_workflow_finalization' for row in execution['cells'])
            and evaluation['totals']['missing_cells'] == 104 and evaluation['totals']['verified_captures'] == evaluation['totals']['verified_purchases'] == 0,
    }
    report = {'schema_version': 'ap2-v10-public-grpc-CA-pinned-wheel-independent-peer-audit/1',
              'reviewed_utc': datetime.now(timezone.utc).isoformat(), 'passed': all(checks.values()), 'controls': checks,
              'run_id': retention['run_id'], 'head_sha': retention['head_sha'], 'retention_identity': identity(retention_raw),
              'archive_identity': {'bytes': archive.stat().st_size, 'sha256': hasher.hexdigest()},
              'actual_capture_input_identities': identities, 'actual_failure': failure, 'actual_stages': stages,
              'actual_preceding_copy_identities': copies, 'pinned_wheel': {'path': str(args.wheel.resolve()),
                  'url': package['download_info']['url'], 'identity': identity(wheel_raw)},
              'reconstructed_public_bundle': {'member': MEMBER, 'identity': identity(roots),
                  'remainder_identity': identity(remainder), 'PEM_blocks': 99, 'DER_sha256': der_ids,
                  'parsed_SSL_store': context.cert_store_stats(), 'license_member': license_name, 'license_identity': identity(license_raw)},
              'reproduced_frozen_parser_reason': reconstructed_reason,
              'actual_failed_grpc_file_bytes_retained': False,
              'attribution_precision': 'The actual failure is at certificate_count before gRPC copy retention. The exact gRPC wheel is bound by the actual pip install report, and its roots.pem reproduces the failure with 99 valid CA certificates plus OpenSSL public text. Ordered preceding copies attribute the next declared input to gRPC; the original failing installed-file bytes were not retained, so this is a trusted pinned-wheel reconstruction rather than a newly observed raw failing file.',
              'new_application_or_provider_calls': 0, 'new_actor_or_bridge_processes_executed': 0,
              'original_grpc_or_SDK_module_imported': False, 'frozen_sources_mutated': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'controls': len(checks), 'CA_certificates': len(blocks),
                      'reproduced_reason': reconstructed_reason}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
