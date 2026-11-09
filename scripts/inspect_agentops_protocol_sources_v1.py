"""Hash installed A2A/ADK protocol sources without importing application code."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import agentops_protocol_preparation_v2 as preparation

SOURCE_TREES = preparation.SOURCE_TREES
SOURCE_FILES = preparation.SOURCE_FILES


def row(path, site):
    raw = path.read_bytes()
    return {'module': path.relative_to(site).as_posix(), 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest()}


def inspect(replica):
    if sys.platform != 'linux':
        raise ValueError('Run this read-only inspection inside Linux')
    if (not replica.is_absolute() or replica.is_symlink() or not replica.is_dir()
            or not replica.name.startswith('agentops-research-v7-')):
        raise ValueError('Expected the retained absolute Linux replica')
    site = replica / 'external/runtime-agentops-linux-v7/venv/lib/python3.13/site-packages'
    modules = []
    for name in SOURCE_FILES:
        path = site / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Missing regular protocol source: ' + name)
        modules.append(row(path, site))
    for name in SOURCE_TREES:
        folder = site / name
        if folder.is_symlink() or not folder.is_dir():
            raise ValueError('Missing protocol source tree: ' + name)
        for path in sorted(folder.rglob('*.py')):
            if path.is_symlink() or not path.is_file():
                raise ValueError('Non-regular protocol source: ' + str(path))
            modules.append(row(path, site))
    modules.sort(key=lambda item: item['module'])
    if len({item['module'] for item in modules}) != len(modules):
        raise ValueError('Duplicate protocol source')
    missing = sorted(preparation.REQUIRED_MODULES - {item['module'] for item in modules})
    if missing:
        raise ValueError('Missing required protocol sources: ' + ', '.join(missing))
    return {
        'schema_version': 'agentops-protocol-runtime-sources/1',
        'inspected_at_utc': datetime.now(timezone.utc).isoformat(),
        'replica': str(replica),
        'python': sys.executable,
        'site_packages': str(site),
        'source_trees': list(SOURCE_TREES),
        'source_files': list(SOURCE_FILES),
        'modules': modules,
        'application_imports': 0,
        'application_requests': 0,
        'live_model_calls': 0,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replica', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Preserve the earlier runtime-source inspection')
    report = inspect(args.replica)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'modules'} | {
        'module_count': len(report['modules'])}, indent=2))
