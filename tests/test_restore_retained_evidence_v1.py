"""Constructed offline corruption, traversal and no-clobber restoration controls."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import restore_retained_evidence_v1 as restore_tool


def byte_id(raw): return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
def write_json(path, value): path.write_text(json.dumps(value), encoding='utf-8')


def fixture(base, schema=3, members=None, inventory=None, existing_archive=False):
    members = members or [('nested/input.json', b'{"constructed":true}'), ('empty.bin', b'')]
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in members: archive.writestr(name, raw)
    raw_archive = stream.getvalue(); whole = byte_id(raw_archive)
    if inventory is None: inventory = [{'path': n, **byte_id(raw)} for n, raw in members]
    receipt = {'status': 'retained', 'run_id': 12345, 'head_sha': 'a' * 40,
        'workflow_conclusion': 'success', 'artifact_id': 67890, 'artifact_name': 'constructed-evidence',
        'archive_bytes': whole['bytes'], 'archive_sha256': whole['sha256'],
        'api_digest': 'sha256:' + whole['sha256'], 'digest_matches_api': True, 'extracted_files': len(inventory)}
    metadata = {'retention.json': receipt,
        'github-run.json': {'id': 12345, 'run_attempt': 1, 'status': 'completed', 'head_sha': 'a' * 40,
            'conclusion': 'success', 'html_url': 'https://github.com/constructed/fixture/actions/runs/12345'},
        'plan.json': {'run_id': 12345, 'application_rerun': False, 'repository': 'constructed/fixture'},
        'github-artifacts.json': {'artifacts': [{'id': 67890, 'name': 'constructed-evidence',
            'digest': 'sha256:' + whole['sha256'], 'size_in_bytes': whole['bytes'], 'expired': False,
            'workflow_run': {'id': 12345, 'head_sha': 'a' * 40}}]},
        'extracted-manifest.json': {'files': inventory}}
    for name, value in metadata.items(): write_json(base / name, value)
    directory = base / ('archive-parts-v3' if schema == 3 else 'archive-parts-v2'); directory.mkdir()
    (directory / 'part-0000.bin').write_bytes(raw_archive)
    index = {'schema_version': f'public-retained-archive-parts/{schema}', 'archive': 'artifact.zip',
        'run_id': 12345, 'api_digest': 'sha256:' + whole['sha256'], 'identity': whole,
        'part_byte_limit': restore_tool.PART_BYTES, 'parts': [{'name': 'part-0000.bin', **whole}],
        'original_archive_modified': False}
    if schema == 3: index.update(archive_max_bytes=300000000, copy_buffer_bytes=262144)
    write_json(directory / 'index.json', index)
    if existing_archive: (base / 'artifact.zip').write_bytes(raw_archive)
    return directory / 'index.json', raw_archive, members


class OfflineRestoreControls(unittest.TestCase):
    def test_V3_parts_restore_fresh_archive_and_exact_extraction_then_no_mutation(self):
        with tempfile.TemporaryDirectory(prefix='retained-offline-V3-control-') as temp:
            base = Path(temp); index, raw, members = fixture(base)
            result = restore_tool.restore(base, index)
            self.assertTrue(result['archive_restored']); self.assertEqual(result['extracted_files_restored'], 2)
            self.assertEqual((base / 'artifact.zip').read_bytes(), raw)
            for name, expected in members: self.assertEqual((base / 'extracted' / name).read_bytes(), expected)
            times = {p: p.stat().st_mtime_ns for p in base.rglob('*') if p.is_file()}
            again = restore_tool.restore(base, index, verify_only=True)
            self.assertFalse(again['archive_restored']); self.assertEqual(again['extracted_files_restored'], 0)
            self.assertEqual(times, {p: p.stat().st_mtime_ns for p in times})

    def test_legacy_V1_schema_in_V2_directory_and_existing_ZIP_without_index(self):
        with tempfile.TemporaryDirectory(prefix='retained-offline-legacy-control-') as temp:
            base = Path(temp); index, _, _ = fixture(base, schema=1, existing_archive=True)
            self.assertEqual(restore_tool.restore(base, index)['part_index_schema'], 'public-retained-archive-parts/1')
            self.assertEqual(restore_tool.restore(base, verify_only=True)['parts_verified'], 0)

    def test_changed_part_or_API_digest_is_refused_before_retained_output(self):
        with tempfile.TemporaryDirectory(prefix='retained-offline-corruption-control-') as temp:
            base = Path(temp); index, raw, _ = fixture(base)
            (index.parent / 'part-0000.bin').write_bytes(b'x' + raw[1:])
            with self.assertRaises(ValueError): restore_tool.restore(base, index)
            self.assertFalse((base / 'artifact.zip').exists()); self.assertFalse((base / 'extracted').exists())
            (index.parent / 'part-0000.bin').write_bytes(raw)
            receipt = json.loads((base / 'retention.json').read_bytes()); receipt['api_digest'] = 'sha256:' + '0' * 64
            write_json(base / 'retention.json', receipt)
            with self.assertRaises(ValueError): restore_tool.restore(base, index)
            self.assertFalse((base / 'artifact.zip').exists()); self.assertFalse((base / 'extracted').exists())

    def test_traversal_and_symbolic_link_ZIP_members_are_refused_before_output(self):
        for member in ['../outside.bin', 'C:/outside.bin', 'a\\outside.bin']:
            with self.subTest(member=member), tempfile.TemporaryDirectory(prefix='retained-offline-traversal-control-') as temp:
                base = Path(temp); index, _, _ = fixture(base, members=[(member, b'x')],
                    inventory=[{'path': 'safe.bin', **byte_id(b'x')}])
                with self.assertRaises(ValueError): restore_tool.restore(base, index)
                self.assertFalse((base / 'artifact.zip').exists()); self.assertFalse((base / 'extracted').exists())
        item = zipfile.ZipInfo('linked.bin'); item.create_system = 3
        item.external_attr = (stat.S_IFLNK | 0o777) << 16
        with tempfile.TemporaryDirectory(prefix='retained-offline-ZIP-link-control-') as temp:
            base = Path(temp); index, _, _ = fixture(base, members=[(item, b'target')],
                inventory=[{'path': 'linked.bin', **byte_id(b'target')}])
            with self.assertRaises(ValueError): restore_tool.restore(base, index)
            self.assertFalse((base / 'artifact.zip').exists()); self.assertFalse((base / 'extracted').exists())

    def test_Windows_casefolded_file_prefix_and_directory_alias_refuse_before_output(self):
        for members in [[('a', b'x'), ('A/b', b'y')], [('A/f', b'x'), ('a/g', b'y')]]:
            with self.subTest(members=members), tempfile.TemporaryDirectory(prefix='retained-offline-case-prefix-control-') as temp:
                base = Path(temp); index, _, _ = fixture(base, members=members)
                with self.assertRaises(ValueError): restore_tool.restore(base, index)
                self.assertFalse((base / 'artifact.zip').exists()); self.assertFalse((base / 'extracted').exists())

    def test_changed_or_partial_existing_extraction_is_never_repaired_or_overwritten(self):
        with tempfile.TemporaryDirectory(prefix='retained-offline-no-clobber-control-') as temp:
            base = Path(temp); index, _, members = fixture(base)
            (base / 'extracted/nested').mkdir(parents=True)
            changed = base / 'extracted/nested/input.json'; changed.write_bytes(b'preserve this evidence')
            with self.assertRaises(ValueError): restore_tool.restore(base, index)
            self.assertEqual(changed.read_bytes(), b'preserve this evidence')
            self.assertFalse((base / 'extracted/empty.bin').exists()); self.assertFalse((base / 'artifact.zip').exists())
            (base / 'extracted/empty.bin').write_bytes(b'')
            with self.assertRaises(ValueError): restore_tool.restore(base, index)
            self.assertEqual(changed.read_bytes(), b'preserve this evidence'); self.assertFalse((base / 'artifact.zip').exists())

    def test_existing_changed_archive_and_manifest_hash_corruption_refuse_no_overwrite(self):
        with tempfile.TemporaryDirectory(prefix='retained-offline-ZIP-no-clobber-control-') as temp:
            base = Path(temp); index, raw, _ = fixture(base, existing_archive=True)
            (base / 'artifact.zip').write_bytes(b'preserve archive')
            with self.assertRaises(ValueError): restore_tool.restore(base, index)
            self.assertEqual((base / 'artifact.zip').read_bytes(), b'preserve archive'); self.assertFalse((base / 'extracted').exists())
            (base / 'artifact.zip').write_bytes(raw)
            inventory = json.loads((base / 'extracted-manifest.json').read_bytes())
            inventory['files'][0]['sha256'] = '0' * 64
            write_json(base / 'extracted-manifest.json', inventory)
            with self.assertRaises(ValueError): restore_tool.restore(base, index)
            self.assertEqual((base / 'artifact.zip').read_bytes(), raw); self.assertFalse((base / 'extracted').exists())

    def test_explicit_missing_mode_preflights_exact_subset_and_never_changes_present_bytes(self):
        with tempfile.TemporaryDirectory(prefix='retained-offline-exact-subset-control-') as temp:
            base = Path(temp); index, _, members = fixture(base)
            (base / 'extracted/nested').mkdir(parents=True)
            present = base / 'extracted/nested/input.json'; present.write_bytes(members[0][1])
            original_time = present.stat().st_mtime_ns
            with self.assertRaises(ValueError): restore_tool.restore(base, index)
            self.assertFalse((base / 'artifact.zip').exists())
            result = restore_tool.restore(base, index, restore_missing=True)
            self.assertEqual(result['extracted_files_restored'], 1); self.assertEqual(result['existing_exact_files_verified'], 1)
            self.assertEqual(present.read_bytes(), members[0][1]); self.assertEqual(present.stat().st_mtime_ns, original_time)
            self.assertEqual((base / 'extracted/empty.bin').read_bytes(), b'')
        for corrupt in [True, False]:
            with self.subTest(corrupt=corrupt), tempfile.TemporaryDirectory(prefix='retained-offline-invalid-subset-control-') as temp:
                base = Path(temp); index, _, members = fixture(base)
                (base / 'extracted/nested').mkdir(parents=True)
                present = base / 'extracted/nested/input.json'
                kept = b'preserve corrupt bytes' if corrupt else members[0][1]; present.write_bytes(kept)
                if not corrupt: (base / 'extracted/extra.bin').write_bytes(b'preserve extra bytes')
                with self.assertRaises(ValueError): restore_tool.restore(base, index, restore_missing=True)
                self.assertEqual(present.read_bytes(), kept)
                self.assertFalse((base / 'artifact.zip').exists()); self.assertFalse((base / 'extracted/empty.bin').exists())


if __name__ == '__main__': unittest.main()
