"""Constructed retention integrity controls; no application or provider execution."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import public_archive_parts_v3 as parts


class ArchiveIntegrityControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='archive-v3-integrity-')
        self.root = Path(self.temp.name).resolve()
        self.base = self.root / 'runs/control'
        self.base.mkdir(parents=True)
        self.raw = bytes(range(256)) * 80
        self.whole = {'bytes': len(self.raw), 'sha256': hashlib.sha256(self.raw).hexdigest()}
        (self.base / 'artifact.zip').write_bytes(self.raw)
        (self.base / 'retention.json').write_text(json.dumps({'run_id': 1,
            'archive_bytes': len(self.raw), 'archive_sha256': self.whole['sha256'],
            'api_digest': 'sha256:' + self.whole['sha256']}))
        self.patches = [patch.object(parts, 'ROOT', self.root), patch.object(parts, 'PART_BYTES', 8192),
                        patch.object(parts, 'BUFFER_BYTES', 1024)]
        for item in self.patches:
            item.start()
        self.index = self.base / 'archive-parts-v3/index.json'

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def test_exact_roundtrip_no_clobber_and_prefix_part_sizes(self):
        report = parts.pack(self.base)
        self.assertEqual(report['parts'], 3)
        self.assertEqual([p['bytes'] for p in json.loads(self.index.read_bytes())['parts']], [8192, 8192, 4096])
        self.assertEqual(parts.restore(self.index)['status'], 'existing_exact_archive_verified')
        (self.base / 'artifact.zip').unlink()
        self.assertEqual(parts.restore(self.index)['status'], 'exact_archive_restored')
        self.assertEqual((self.base / 'artifact.zip').read_bytes(), self.raw)
        with self.assertRaises(FileExistsError):
            parts.pack(self.base)

    def test_tampered_part_and_api_identity_rejected_before_restore(self):
        parts.pack(self.base)
        (self.base / 'artifact.zip').unlink()
        member = self.index.parent / 'part-0000.bin'
        original = member.read_bytes()
        member.write_bytes(b'X' + original[1:])
        with self.assertRaises(ValueError):
            parts.restore(self.index)
        self.assertFalse((self.base / 'artifact.zip').exists())
        member.write_bytes(original)
        index = json.loads(self.index.read_bytes()); index['api_digest'] = 'sha256:' + '0' * 64
        self.index.write_text(json.dumps(index))
        with self.assertRaises(ValueError):
            parts.restore(self.index)
        self.assertFalse((self.base / 'artifact.zip').exists())

    def test_existing_mismatch_and_oversized_claim_rejected(self):
        parts.pack(self.base)
        (self.base / 'artifact.zip').write_bytes(b'different-existing-evidence')
        with self.assertRaises(ValueError):
            parts.restore(self.index)
        self.assertEqual((self.base / 'artifact.zip').read_bytes(), b'different-existing-evidence')
        index = json.loads(self.index.read_bytes()); index['identity']['bytes'] = 300_000_001
        self.index.write_text(json.dumps(index))
        with self.assertRaises(ValueError):
            parts.restore(self.index)


if __name__ == '__main__':
    unittest.main()
