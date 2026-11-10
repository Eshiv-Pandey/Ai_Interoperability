"""Bound public-certificate admission and content-free actor diagnostics.

Only five declared public files can be admitted outside the fresh private
profile. This helper reads no evaluator, saved credential or signing key.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import ssl
import sys


SOURCE_PUBLIC_CERTIFICATES = {
    'code/samples/certs/ds_cert_sdjwt.pem': {
        'bytes': 1066, 'sha256': 'a4b92cd66960d4ddcdcb8ca8b2887dafdec06cbcd42bc10fcc8ede41ffef1306'},
    'code/samples/certs/issuer_cert_sdjwt.pem': {
        'bytes': 1005, 'sha256': '120abde3087907911c3c9de00c536657a6a503a88849a24653f6c35030c982ba'},
}
RUNTIME_PUBLIC_CA_PATHS = (
    'certifi/cacert.pem',
    'grpc/_cython/_credentials/roots.pem',
    'pip/_vendor/certifi/cacert.pem',
)


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def certificate_count(raw):
    """Parse bounded certificate-only PEM, without retaining its contents."""
    if not raw or len(raw) > 4 * 1024 * 1024:
        raise ValueError('public_certificate_size_bound')
    begins = re.findall(rb'-----BEGIN ([A-Z0-9 ]+)-----', raw)
    ends = re.findall(rb'-----END ([A-Z0-9 ]+)-----', raw)
    if not begins or len(begins) > 1000 or begins != ends or set(begins) != {b'CERTIFICATE'}:
        raise ValueError('certificate_only_PEM_required')
    if b'PRIVATE KEY' in raw or b'PUBLIC KEY' in raw:
        raise ValueError('key_material_not_a_public_certificate')
    blocks = re.findall(rb'-----BEGIN CERTIFICATE-----\s+[A-Za-z0-9+/=\r\n]+-----END CERTIFICATE-----', raw)
    if len(blocks) != len(begins):
        raise ValueError('malformed_public_certificate_block')
    remainder = re.sub(rb'-----BEGIN CERTIFICATE-----\s+[A-Za-z0-9+/=\r\n]+-----END CERTIFICATE-----', b'', raw)
    if any(line.strip() and not line.lstrip().startswith(b'#') for line in remainder.splitlines()):
        raise ValueError('non_certificate_non_comment_PEM_content')
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(cadata=raw.decode('ascii'))
    return len(blocks)


def prepare_public_certificates(output, source, site_packages, writer):
    output, source, site_packages = map(lambda value: Path(value).resolve(), (output, source, site_packages))
    destination = output / 'public-certificate-admission'
    destination.mkdir(exist_ok=False)
    records = []
    roots = [('original_source', source, tuple(SOURCE_PUBLIC_CERTIFICATES)),
             ('installed_runtime', site_packages, RUNTIME_PUBLIC_CA_PATHS)]
    for category, root, names in roots:
        for relative in names:
            path = root / relative
            if category == 'installed_runtime' and relative.startswith('pip/') and not path.exists():
                continue
            if not path.is_file() or path.is_symlink() or path.resolve() != path:
                raise ValueError('declared_public_certificate_missing_or_linked')
            raw = path.read_bytes()
            current = identity(raw)
            if category == 'original_source' and current != SOURCE_PUBLIC_CERTIFICATES[relative]:
                raise ValueError('pinned_original_public_certificate_changed')
            count = certificate_count(raw)
            retained = destination / category / relative
            retained.parent.mkdir(parents=True, exist_ok=True)
            retained.write_bytes(raw)
            records.append({'category': category, 'relative_path': relative, 'source_path': str(path),
                            'retained_path': retained.relative_to(output).as_posix(),
                            'identity': current, 'certificate_blocks': count,
                            'private_key_contents_retained': False})
    receipt = {'schema_version': 'ap2-declared-public-certificate-admission/9',
               'source_root': str(source), 'site_packages_root': str(site_packages), 'records': records,
               'validation': 'bounded certificate-only PEM labels, comments and stdlib SSL X.509 parsing',
               'scope': 'exact declared public files, not a general PEM or credential exception'}
    writer(output / 'public-certificate-admission.json', receipt)
    return {Path(row['source_path']) for row in records}


def admitted_certificates_unchanged(output):
    """Recheck admitted originals; the separate evaluator checks retained copies."""
    output = Path(output)
    receipt = json.loads((output / 'public-certificate-admission.json').read_bytes())
    return all(identity(Path(row['source_path']).read_bytes()) == row['identity'] for row in receipt['records'])


def safe_path(value, roots):
    """Represent declared code roots; redact undeclared or credential names."""
    if not isinstance(value, (str, bytes, os.PathLike)):
        return '<non_path>'
    path = Path(os.fsdecode(value)).absolute()
    for label, base in roots.items():
        if base is not None and path.is_relative_to(Path(base).absolute()):
            relative = path.relative_to(Path(base).absolute())
            if path.name.lower().startswith('gemini-api-key'):
                return '<' + label + '>/<saved_credential>'
            return '<' + label + '>/' + relative.as_posix()[:400]
    return '<outside_declared_roots>'


def frame_metadata(frame, roots):
    result = []
    while frame is not None and len(result) < 24:
        result.append({'file': safe_path(frame.f_code.co_filename, roots),
                       'function': frame.f_code.co_name[:120], 'line': frame.f_lineno})
        frame = frame.f_back
    return result


def exception_frame_metadata(error, roots):
    result, trace = [], error.__traceback__
    while trace is not None and len(result) < 24:
        result.append({'file': safe_path(trace.tb_frame.f_code.co_filename, roots),
                       'function': trace.tb_frame.f_code.co_name[:120], 'line': trace.tb_lineno})
        trace = trace.tb_next
    return result


def record_denial(output, audit_state, operation, code, roots, path=None, network_endpoint=None):
    index = audit_state.get('diagnostic_rows', 0)
    if index >= 64:
        audit_state['diagnostic_bound_reached'] = True
        return
    row = {'index': index, 'utc': datetime.now(timezone.utc).isoformat(), 'operation': operation,
           'guard_code': code, 'path': safe_path(path, roots) if path is not None else None,
           'expected_private_evaluator_probe': audit_state.get('expected_private_evaluator_probe', False),
           'frames': frame_metadata(sys._getframe(1), roots),
           'contents_arguments_locals_headers_and_environment_retained': False}
    if network_endpoint is not None:
        host, port, family, socket_type = network_endpoint
        row['network_endpoint'] = {
            'host': host if host in {'127.0.0.1', '::1', 'localhost'} else '<redacted_external_or_unrecognized>',
            'port': port if type(port) is int and 0 <= port <= 65535 else None,
            'socket_family': int(family) if family in {2, 10, 23} else None,
            'socket_type': int(socket_type) if socket_type in {1, 2} else None}
    with (Path(output) / 'actor-guard-denials.jsonl').open('ab') as handle:
        handle.write((json.dumps(row, sort_keys=True, allow_nan=False) + '\n').encode())
        handle.flush()
        os.fsync(handle.fileno())
    audit_state['diagnostic_rows'] = index + 1
