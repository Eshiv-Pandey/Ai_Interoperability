"""Pack/restore exact public archives up to 300 MB using 256 KiB buffers.

V3 uses a fresh namespace; previous archives and failed transfers stay unchanged.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PART_BYTES = 32 * 1024 * 1024
BUFFER_BYTES = 256 * 1024
ARCHIVE_MAX_BYTES = 300_000_000


def digest(path):
    value, count = hashlib.sha256(), 0
    with path.open('rb') as stream:
        while block := stream.read(BUFFER_BYTES):
            value.update(block)
            count += len(block)
    return {'bytes': count, 'sha256': value.hexdigest()}


def workspace(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT / 'runs'):
        raise ValueError('Workspace retained run required')
    return path


def pack(base):
    base = workspace(base)
    receipt = json.loads((base / 'retention.json').read_bytes())
    archive = base / 'artifact.zip'
    if archive.is_symlink():
        raise ValueError('Regular retained archive required')
    whole = digest(archive)
    if (not 0 < whole['bytes'] <= ARCHIVE_MAX_BYTES
            or whole != {'bytes': receipt['archive_bytes'], 'sha256': receipt['archive_sha256']}
            or receipt['api_digest'] != 'sha256:' + whole['sha256']):
        raise ValueError('Archive/API byte identity differs')
    output = base / 'archive-parts-v3'
    output.mkdir(exist_ok=False)
    records, copied, combined = [], 0, hashlib.sha256()
    with archive.open('rb') as source:
        while copied < whole['bytes']:
            name = f'part-{len(records):04d}.bin'
            part_hash, count = hashlib.sha256(), 0
            with (output / name).open('xb') as target:
                while count < PART_BYTES:
                    block = source.read(min(BUFFER_BYTES, PART_BYTES - count))
                    if not block:
                        break
                    target.write(block)
                    part_hash.update(block)
                    combined.update(block)
                    count += len(block)
                    copied += len(block)
            if count == 0 or copied > whole['bytes']:
                raise ValueError('Archive changed during copy; failed output retained')
            records.append({'name': name, 'bytes': count, 'sha256': part_hash.hexdigest()})
        if source.read(1) or {'bytes': copied, 'sha256': combined.hexdigest()} != whole:
            raise ValueError('Archive changed during copy; failed output retained')
    for row in records:
        if digest(output / row['name']) != {k: row[k] for k in ('bytes', 'sha256')}:
            raise ValueError('Written part differs; failed output retained')
    index = {'schema_version': 'public-retained-archive-parts/3', 'archive': 'artifact.zip',
        'run_id': receipt['run_id'], 'api_digest': receipt['api_digest'], 'identity': whole,
        'part_byte_limit': PART_BYTES, 'archive_max_bytes': ARCHIVE_MAX_BYTES,
        'parts': records, 'original_archive_modified': False, 'copy_buffer_bytes': BUFFER_BYTES,
        'created_at_utc': datetime.now(timezone.utc).isoformat()}
    with (output / 'index.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(index, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return {'status': 'exact_archive_stored_in_streaming_parts', 'parts': len(records), 'identity': whole}


def restore(index_path):
    index_path = workspace(index_path)
    index = json.loads(index_path.read_bytes())
    if (index['schema_version'] != 'public-retained-archive-parts/3' or index['archive'] != 'artifact.zip'
            or index['part_byte_limit'] != PART_BYTES or index['archive_max_bytes'] != ARCHIVE_MAX_BYTES
            or type(index['identity']['bytes']) is not int
            or not 0 < index['identity']['bytes'] <= ARCHIVE_MAX_BYTES
            or not 0 < len(index['parts']) <= (ARCHIVE_MAX_BYTES + PART_BYTES - 1) // PART_BYTES):
        raise ValueError('Unsupported or unbounded archive index')
    combined, total = hashlib.sha256(), 0
    for number, row in enumerate(index['parts']):
        if (row['name'] != f'part-{number:04d}.bin' or type(row['bytes']) is not int
                or not 0 < row['bytes'] <= PART_BYTES
                or (number < len(index['parts']) - 1 and row['bytes'] != PART_BYTES)):
            raise ValueError('Invalid bounded part sequence')
        part = index_path.parent / row['name']
        if part.is_symlink() or digest(part) != {k: row[k] for k in ('bytes', 'sha256')}:
            raise ValueError('Part identity differs')
        with part.open('rb') as stream:
            while block := stream.read(BUFFER_BYTES):
                combined.update(block)
                total += len(block)
                if total > ARCHIVE_MAX_BYTES:
                    raise ValueError('Archive bound exceeded')
    whole = {'bytes': total, 'sha256': combined.hexdigest()}
    if whole != index['identity'] or index['api_digest'] != 'sha256:' + whole['sha256']:
        raise ValueError('Combined archive/API identity differs')
    archive = index_path.parent.parent / 'artifact.zip'
    if archive.exists() or archive.is_symlink():
        if archive.is_symlink() or digest(archive) != whole:
            raise ValueError('Existing archive differs; no overwrite')
        return {'status': 'existing_exact_archive_verified', 'identity': whole}
    with archive.open('xb') as target:
        for row in index['parts']:
            with (index_path.parent / row['name']).open('rb') as source:
                while block := source.read(BUFFER_BYTES):
                    target.write(block)
    if digest(archive) != whole:
        raise ValueError('Restored archive differs; failed output retained')
    return {'status': 'exact_archive_restored', 'identity': whole}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--pack', type=Path)
    mode.add_argument('--restore', type=Path)
    args = parser.parse_args()
    print(json.dumps(pack(args.pack) if args.pack else restore(args.restore)))
