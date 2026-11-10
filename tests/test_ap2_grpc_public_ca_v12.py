"""Exact pinned grpcio public CA controls; no SDK/app/provider/bridge execution."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import ap2_public_certificate_guard_v12 as certificates
import evaluate_ap2_native_bridge_matrix_v12 as evaluator

FIXTURE = ROOT / 'benchmark/ap2-native-bridge-development-v12/public-ca-fixtures/grpcio-1.85.0'


class PinnedGrpcPublicCaControls(unittest.TestCase):
    def raw(self):
        return (FIXTURE / 'roots.pem').read_bytes()

    def test_exact_pinned_wheel_fixture_and_all_99_X509_blocks(self):
        provenance = json.loads((FIXTURE / 'provenance.json').read_bytes())
        self.assertEqual(provenance['wheel']['sha256'], '55cee7cfe71b29f6b377681936f9a5f35e59f5c941a4d84e2712cb309753e7a9')
        raw = self.raw()
        self.assertEqual(certificates.identity(raw), certificates.GRPC_PUBLIC_BUNDLE_IDENTITY)
        self.assertEqual(certificates.identity(raw), {key: provenance['bundle'][key] for key in ('bytes', 'sha256')})
        self.assertEqual(certificates.certificate_count(raw, declared_runtime_path=certificates.GRPC_PUBLIC_BUNDLE_PATH), 99)
        remainder = re.sub(rb'-----BEGIN CERTIFICATE-----\s+[A-Za-z0-9+/=\r\n]+-----END CERTIFICATE-----', b'', raw)
        self.assertEqual(certificates.identity(remainder), certificates.GRPC_PUBLIC_METADATA_IDENTITY)
        self.assertTrue(any(line.strip() and not line.lstrip().startswith(b'#') for line in remainder.splitlines()))

    def test_frozen_V10_rejects_the_actual_pinned_public_CA_bytes(self):
        spec = importlib.util.spec_from_file_location('_frozen_V10_public_ca_control', ROOT / 'scripts/ap2_public_certificate_guard_v10.py')
        old = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(old)
        with self.assertRaisesRegex(ValueError, 'non_certificate_non_comment_PEM_content'):
            old.certificate_count(self.raw())

    def test_public_text_requires_the_exact_declared_runtime_path(self):
        for path in (None, 'certifi/cacert.pem', 'other-package/roots.pem'):
            with self.assertRaisesRegex(ValueError, 'non_certificate_non_comment_PEM_content'):
                certificates.certificate_count(self.raw(), declared_runtime_path=path)

    def test_changed_text_private_key_and_extra_PEM_blocks_are_refused(self):
        changed = self.raw().replace(b'Certificate:', b'Certificate ', 1)
        with self.assertRaisesRegex(ValueError, 'non_certificate_non_comment_PEM_content'):
            certificates.certificate_count(changed, declared_runtime_path=certificates.GRPC_PUBLIC_BUNDLE_PATH)
        for label in (b'PRIVATE KEY', b'PUBLIC KEY', b'OTHER'):
            extra = b'\n-----BEGIN ' + label + b'-----\nCONSTRUCTED_NOT_SAVED_MATERIAL\n-----END ' + label + b'-----\n'
            with self.assertRaises(ValueError):
                certificates.certificate_count(self.raw() + extra, declared_runtime_path=certificates.GRPC_PUBLIC_BUNDLE_PATH)

    def prepared(self, temporary):
        output, runtime = Path(temporary) / 'output', Path(temporary) / 'runtime'
        output.mkdir()
        source = ROOT / 'runs/ap2-environment-preparation/source-stage-v1/ap2'
        plain = (source / 'code/samples/certs/issuer_cert_sdjwt.pem').read_bytes()
        for name in certificates.RUNTIME_PUBLIC_CA_PATHS:
            path = runtime / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(self.raw() if name == certificates.GRPC_PUBLIC_BUNDLE_PATH else plain)
        certificates.prepare_public_certificates(output, source, runtime,
            lambda path, value: path.write_text(json.dumps(value), encoding='utf-8'))
        identities = {name: certificates.identity((runtime / name).read_bytes()) for name in certificates.RUNTIME_PUBLIC_CA_PATHS}
        (output / 'runtime-manifest.json').write_text(json.dumps({'root': str(runtime), 'files': identities}), encoding='utf-8')
        return output

    def test_real_bundle_admission_copy_and_independent_evaluator(self):
        with tempfile.TemporaryDirectory(prefix='ap2-v12-real-grpc-admission-control-') as temporary:
            output = self.prepared(temporary)
            self.assertTrue(certificates.admitted_certificates_unchanged(output))
            self.assertEqual(evaluator.verify_public_certificate_admissions(output, certificates.SOURCE_PUBLIC_CERTIFICATES), 5)
            receipt = json.loads((output / 'public-certificate-admission.json').read_bytes())
            row = next(row for row in receipt['records'] if row['relative_path'] == certificates.GRPC_PUBLIC_BUNDLE_PATH)
            self.assertEqual(row['certificate_blocks'], 99)
            self.assertEqual((output / row['retained_path']).read_bytes(), self.raw())

    def test_independent_evaluator_rejects_changed_text_even_with_jointly_changed_supplied_hashes(self):
        with tempfile.TemporaryDirectory(prefix='ap2-v12-grpc-metadata-evaluation-control-') as temporary:
            output = self.prepared(temporary)
            admission_path = output / 'public-certificate-admission.json'
            receipt = json.loads(admission_path.read_bytes())
            row = next(row for row in receipt['records'] if row['relative_path'] == certificates.GRPC_PUBLIC_BUNDLE_PATH)
            raw = self.raw().replace(b'Certificate:', b'Certificate ', 1)
            (output / row['retained_path']).write_bytes(raw)
            row['identity'] = certificates.identity(raw)
            admission_path.write_text(json.dumps(receipt), encoding='utf-8')
            runtime_path = output / 'runtime-manifest.json'
            runtime = json.loads(runtime_path.read_bytes())
            runtime['files'][certificates.GRPC_PUBLIC_BUNDLE_PATH] = row['identity']
            runtime_path.write_text(json.dumps(runtime), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'public_certificate_non_comment_content'):
                evaluator.verify_public_certificate_admissions(output, certificates.SOURCE_PUBLIC_CERTIFICATES)


if __name__ == '__main__':
    unittest.main()
