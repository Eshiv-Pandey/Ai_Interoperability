"""Restore bounded retained ZIP/extraction bytes offline, never overwrite evidence.

Verify saved run/API/retention metadata, optional V1/V3 parts, every ZIP member
and the extraction inventory before publishing missing retained files. Existing
extraction must be complete and exact; partial or changed evidence is refused.
No source application, actor, solver, checker, model or remote API executes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat
import tempfile
import zipfile

BUFFER_BYTES = 262144
PART_BYTES = 33554432
ARCHIVE_MAX_BYTES = 300000000
EXPANDED_MAX_BYTES = 2000000000
METADATA_MAX_BYTES = 32 * 1024 * 1024
MEMBER_COUNT_MAX = 200000
RESERVED = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def linked(path):
    return path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction())


def clean_path(path):
    """Check the supplied absolute spelling before resolving any existing link."""
    path = Path(os.path.abspath(path))
    for ancestor in (path, *path.parents):
        need(not linked(ancestor), 'linked_or_junction_path_refused:' + str(ancestor))
    need(path.resolve() == path, 'path_resolves_through_an_alias')
    return path


def parse(raw):
    def unique(pairs):
        value = {}
        for key, child in pairs:
            need(key not in value, 'duplicate_JSON_key')
            value[key] = child
        return value
    def nonfinite(value):
        raise ValueError('nonfinite_JSON_value:' + value)
    return json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)


def load(path):
    path = clean_path(path)
    need(path.is_file() and path.stat().st_size <= METADATA_MAX_BYTES, 'bounded_regular_metadata_required:' + str(path))
    return parse(path.read_bytes())


def identity(row):
    need(type(row) is dict and type(row.get('bytes')) is int and row['bytes'] >= 0
         and type(row.get('sha256')) is str and re.fullmatch('[0-9a-f]{64}', row['sha256']), 'invalid_byte_identity')
    return {key: row[key] for key in ('bytes', 'sha256')}


def stream_identity(stream, limit, target=None):
    count, digest = 0, hashlib.sha256()
    while block := stream.read(BUFFER_BYTES):
        count += len(block)
        need(count <= limit, 'stream_byte_bound_exceeded')
        digest.update(block)
        if target is not None: target.write(block)
    return {'bytes': count, 'sha256': digest.hexdigest()}


def file_identity(path, limit):
    path = clean_path(path)
    need(path.is_file() and path.stat().st_size <= limit, 'bounded_regular_file_required:' + str(path))
    with path.open('rb') as stream: return stream_identity(stream, limit)


def member_name(name, directory=False):
    need(type(name) is str and name and '\\' not in name and '\x00' not in name and ':' not in name,
         'noncanonical_ZIP_name')
    canonical = name[:-1] if directory and name.endswith('/') else name
    parts = PurePosixPath(canonical)
    need(canonical and not parts.is_absolute() and not PureWindowsPath(canonical).drive
         and '..' not in parts.parts and parts.as_posix() == canonical, 'unsafe_ZIP_member_path')
    for part in parts.parts:
        need(not part.endswith(('.', ' ')) and part.split('.', 1)[0].upper() not in RESERVED,
             'Windows_alias_or_reserved_ZIP_path')
    return canonical


def verify_metadata(base):
    receipt, run, plan, listing = [load(base / name) for name in
        ('retention.json', 'github-run.json', 'plan.json', 'github-artifacts.json')]
    whole = identity({'bytes': receipt['archive_bytes'], 'sha256': receipt['archive_sha256']})
    need(0 < whole['bytes'] <= ARCHIVE_MAX_BYTES and receipt['status'] == 'retained'
         and receipt['api_digest'] == 'sha256:' + whole['sha256'] and receipt['digest_matches_api'] is True,
         'retention_whole_archive_or_API_identity_changed')
    need(type(run['id']) is int and run['id'] > 0 and run['status'] == 'completed'
         and type(run['run_attempt']) is int and run['run_attempt'] > 0
         and type(run['head_sha']) is str and re.fullmatch('[0-9a-f]{40}', run['head_sha'])
         and receipt['run_id'] == run['id'] and receipt['head_sha'] == run['head_sha']
         and receipt['workflow_conclusion'] == run['conclusion'] and plan['run_id'] == run['id']
         and plan['application_rerun'] is False, 'saved_completed_run_binding_changed')
    repository = plan['repository']
    need(type(repository) is str and re.fullmatch('[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository)
         and run['html_url'] == f'https://github.com/{repository}/actions/runs/{run["id"]}',
         'saved_repository_or_run_URL_changed')
    artifacts = [row for row in listing['artifacts'] if row['id'] == receipt['artifact_id']]
    need(len(artifacts) == 1, 'saved_API_artifact_not_unique')
    artifact = artifacts[0]
    need(artifact['name'] == receipt['artifact_name'] and artifact['digest'] == receipt['api_digest']
         and artifact['size_in_bytes'] == whole['bytes'] and artifact['expired'] is False
         and artifact['workflow_run']['id'] == run['id'] and artifact['workflow_run']['head_sha'] == run['head_sha'],
         'saved_API_artifact_not_bound_to_retained_run')
    inventory = load(base / 'extracted-manifest.json')['files']
    need(type(inventory) is list and 0 < len(inventory) <= MEMBER_COUNT_MAX
         and len(inventory) == receipt['extracted_files'], 'bounded_extraction_inventory_required')
    expected, folded, expanded = {}, set(), 0
    for row in inventory:
        name = member_name(row['path']); row_id = identity(row); expanded += row_id['bytes']
        need(name.casefold() not in folded and expanded <= EXPANDED_MAX_BYTES, 'duplicate_or_oversized_extraction_inventory')
        expected[name] = row_id; folded.add(name.casefold())
    return receipt, whole, expected


def verify_parts(index_path, base, receipt, whole, target=None):
    index_path = clean_path(index_path)
    need(index_path.parent.parent == base and index_path.name == 'index.json', 'part_index_must_belong_to_specified_retained_base')
    index = load(index_path); version = index['schema_version']
    need(version in {'public-retained-archive-parts/1', 'public-retained-archive-parts/3'}
         and index_path.parent.name in ({'archive-parts-v1', 'archive-parts-v2'} if version.endswith('/1') else {'archive-parts-v3'})
         and index['archive'] == 'artifact.zip' and index['part_byte_limit'] == PART_BYTES
         and index['run_id'] == receipt['run_id'] and index['api_digest'] == receipt['api_digest']
         and identity(index['identity']) == whole and index['original_archive_modified'] is False,
         'part_index_version_or_retention_binding_changed')
    if version.endswith('/3'):
        need(index['archive_max_bytes'] == ARCHIVE_MAX_BYTES and index['copy_buffer_bytes'] == BUFFER_BYTES,
             'V3_streaming_bounds_changed')
    rows = index['parts']
    need(type(rows) is list and 0 < len(rows) <= (ARCHIVE_MAX_BYTES + PART_BYTES - 1) // PART_BYTES,
         'bounded_part_sequence_required')
    total, combined = 0, hashlib.sha256()
    for number, row in enumerate(rows):
        part_id = identity(row)
        need(row['name'] == f'part-{number:04d}.bin' and 0 < part_id['bytes'] <= PART_BYTES
             and (number == len(rows) - 1 or part_id['bytes'] == PART_BYTES), 'part_sequence_or_size_changed')
        part = clean_path(index_path.parent / row['name'])
        need(part.is_file() and part.stat().st_size == part_id['bytes'], 'part_file_size_changed')
        count, digest = 0, hashlib.sha256()
        with part.open('rb') as source:
            while block := source.read(BUFFER_BYTES):
                count += len(block); total += len(block)
                need(count <= PART_BYTES and total <= ARCHIVE_MAX_BYTES, 'part_stream_byte_bound_exceeded')
                digest.update(block); combined.update(block)
                if target is not None: target.write(block)
        need({'bytes': count, 'sha256': digest.hexdigest()} == part_id, 'part_content_identity_changed')
    need({'bytes': total, 'sha256': combined.hexdigest()} == whole, 'concatenated_whole_archive_identity_changed')
    if target is not None: target.seek(0)
    return len(rows), version


def verify_existing_extraction(extracted, expected):
    if not extracted.exists(): return False
    extracted = clean_path(extracted)
    need(extracted.is_dir(), 'existing_extraction_is_not_a_directory')
    names = set()
    for path in extracted.rglob('*'):
        clean_path(path)
        if path.is_file(): names.add(path.relative_to(extracted).as_posix())
        else: need(path.is_dir(), 'special_existing_extraction_path')
    need(names == set(expected), 'existing_extraction_membership_differs_no_mutation')
    for name, row in expected.items():
        need(file_identity(extracted / name, row['bytes']) == row, 'existing_extraction_bytes_differ_no_mutation:' + name)
    return True


def verify_zip(source, base, expected):
    seen, folded, files, directories, expanded = set(), set(), {}, set(), 0
    infos = source.infolist()
    need(0 < len(infos) <= MEMBER_COUNT_MAX, 'ZIP_member_count_bound_exceeded')
    for item in infos:
        name = member_name(item.filename, item.is_dir())
        mode = stat.S_IFMT(item.external_attr >> 16)
        need(name not in seen and name.casefold() not in folded and mode in {0, stat.S_IFREG, stat.S_IFDIR}
             and not item.flag_bits & 1 and item.compress_type in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED},
             'duplicate_linked_encrypted_or_special_ZIP_member')
        seen.add(name); folded.add(name.casefold()); expanded += item.file_size
        need(expanded <= EXPANDED_MAX_BYTES, 'ZIP_expansion_bound_exceeded')
        target = clean_path(base / 'extracted' / name)
        need(target.is_relative_to(base / 'extracted'), 'ZIP_target_outside_intended_extraction')
        if item.is_dir():
            need(item.file_size == 0, 'nonempty_ZIP_directory_entry')
            directories.add(name)
        else:
            need(name in expected and item.file_size == expected[name]['bytes'], 'ZIP_and_extracted_manifest_members_differ')
            files[name] = item
    need(set(files) == set(expected), 'ZIP_and_extracted_manifest_membership_changed')
    for name in seen:
        need(not any(p.as_posix() in files for p in PurePosixPath(name).parents if p.as_posix() != '.'),
             'ZIP_file_directory_prefix_conflict')
    for name, item in files.items():
        with source.open(item) as stream:
            need(stream_identity(stream, item.file_size) == expected[name], 'ZIP_member_hash_differs_from_saved_extraction:' + name)
    return files, directories, expanded


def restore(base, index_path=None, verify_only=False):
    base = clean_path(base)
    need(base.is_dir(), 'existing_retained_base_required')
    archive, extracted = base / 'artifact.zip', base / 'extracted'
    receipt, whole, expected = verify_metadata(base)
    archive_present = archive.exists()
    extraction_present = verify_existing_extraction(extracted, expected)
    if verify_only: need(archive_present and extraction_present, 'offline_restore_required_missing_archive_or_extraction')
    if archive_present:
        need(file_identity(archive, ARCHIVE_MAX_BYTES) == whole, 'existing_archive_differs_no_overwrite')
    else:
        need(index_path is not None, 'missing_archive_requires_saved_part_index')
    # An OS-managed temporary seekable file holds a missing ZIP during complete
    # preflight. No retained file is created until all identities/paths pass.
    with tempfile.TemporaryFile(mode='w+b') as temporary:
        part_count, version = (0, None)
        if index_path is not None:
            part_count, version = verify_parts(index_path, base, receipt, whole, None if archive_present else temporary)
        input_archive = archive if archive_present else temporary
        with zipfile.ZipFile(input_archive) as source:
            files, directories, expanded = verify_zip(source, base, expected)
            if not archive_present:
                clean_path(archive)
                temporary.seek(0)
                with archive.open('xb') as target:
                    need(stream_identity(temporary, ARCHIVE_MAX_BYTES, target) == whole, 'archive_changed_during_exclusive_restore')
                    target.flush(); os.fsync(target.fileno())
                need(file_identity(archive, ARCHIVE_MAX_BYTES) == whole, 'restored_archive_identity_changed_failed_bytes_retained')
            restored = 0
            if not extraction_present:
                clean_path(extracted)
                extracted.mkdir(exist_ok=False)
                for name in sorted(directories):
                    target = clean_path(extracted / name)
                    need(target.is_relative_to(extracted), 'restoration_directory_outside_intended_base')
                    target.mkdir(parents=True, exist_ok=True)
                for name, item in files.items():
                    target = clean_path(extracted / name)
                    need(target.is_relative_to(extracted), 'restoration_file_outside_intended_base')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with source.open(item) as member, target.open('xb') as output:
                        need(stream_identity(member, item.file_size, output) == expected[name],
                             'member_changed_during_exclusive_restore_failed_bytes_retained')
                        output.flush()
                    restored += 1
                need(verify_existing_extraction(extracted, expected), 'restored_extraction_not_exact')
    return {'status': 'exact_offline_archive_and_extraction_verified', 'retained_base': str(base),
        'run_id': receipt['run_id'], 'archive_identity': whole, 'archive_restored': not archive_present,
        'part_index_schema': version, 'parts_verified': part_count, 'extracted_files_verified': len(expected),
        'extracted_files_restored': restored, 'expanded_bytes_verified': expanded, 'copy_buffer_bytes': BUFFER_BYTES,
        'archive_max_bytes': ARCHIVE_MAX_BYTES, 'expanded_max_bytes': EXPANDED_MAX_BYTES,
        'existing_evidence_overwritten': False, 'new_remote_application_solver_checker_or_provider_calls': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--index', type=Path)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    print(json.dumps(restore(args.base, args.index, args.verify_only), sort_keys=True))
