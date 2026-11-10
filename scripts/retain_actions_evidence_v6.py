"""Resume a preserved partial transfer into a fresh, bounded evidence allocation.

Credentials and the temporary signed archive URL never enter receipts or output.
The V5 collector still verifies the complete GitHub digest and every ZIP member.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

sys.path.insert(0, str(Path(__file__).resolve().parent))
import retain_actions_evidence_v5 as collector

BUFFER = 256 * 1024


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def resume_command(original, partial_base, argv, output, *, limit=180):
    if not argv[-1].endswith('/zip'):
        return original(argv, output, limit=limit)
    started = datetime.now(timezone.utc).isoformat()
    source = partial_base / 'artifact.zip'
    prior = json.loads((partial_base / 'artifact.zip.receipt.json').read_bytes())
    partial_hash = collector.file_sha256(source)
    partial_bytes = source.stat().st_size
    old_artifacts = json.loads((partial_base / 'github-artifacts.json').read_bytes())['artifacts']
    new_artifacts = json.loads((output.parent / 'github-artifacts.json').read_bytes())['artifacts']
    artifact_id = int(argv[-1].split('/')[-2])
    old = next(a for a in old_artifacts if a['id'] == artifact_id)
    new = next(a for a in new_artifacts if a['id'] == artifact_id)
    if (source.is_symlink() or not 0 < partial_bytes < new['size_in_bytes'] <= 300_000_000
            or prior['stdout_bytes'] != partial_bytes or prior['stdout_sha256'] != partial_hash
            or old['digest'] != new['digest'] or old['size_in_bytes'] != new['size_in_bytes']):
        raise ValueError('Preserved partial identity or artifact binding differs')
    received = 0
    status = 'failed'
    safe_error = None
    digest = hashlib.sha256()
    try:
        with source.open('rb') as stream, output.open('xb') as target:
            copied = 0
            while block := stream.read(BUFFER):
                copied += len(block)
                if copied > partial_bytes:
                    raise ValueError('Partial source changed while copying')
                target.write(block)
                digest.update(block)
            if copied != partial_bytes or digest.hexdigest() != partial_hash:
                raise ValueError('Copied partial source differs')
            token = subprocess.run(['gh', 'auth', 'token'], capture_output=True, check=True,
                                   timeout=30).stdout.decode().strip()
            request = Request('https://api.github.com/' + argv[-1], headers={
                'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
                'User-Agent': 'bounded-research-evidence-retention'})
            opener = build_opener(NoRedirect())
            try:
                response = opener.open(request, timeout=30)
                response.close()
                raise ValueError('Expected signed archive redirect')
            except HTTPError as error:
                if error.code != 302:
                    raise ValueError('Archive API did not return a redirect') from None
                location = error.headers.get('Location', '')
                error.close()
            token = None
            parsed = urlparse(location)
            allowed = ('.blob.core.windows.net', '.actions.githubusercontent.com', '.githubusercontent.com')
            if parsed.scheme != 'https' or not any((parsed.hostname or '').endswith(s) for s in allowed):
                raise ValueError('Unexpected signed archive host')
            deadline = time.monotonic() + limit
            with opener.open(Request(location, headers={'Range': f'bytes={partial_bytes}-',
                    'Accept-Encoding': 'identity'}), timeout=30) as response:
                expected_range = f'bytes {partial_bytes}-{new["size_in_bytes"] - 1}/{new["size_in_bytes"]}'
                if response.status != 206 or response.headers.get('Content-Range') != expected_range:
                    raise ValueError('Server did not confirm the exact remaining byte range')
                while block := response.read(BUFFER):
                    received += len(block)
                    if time.monotonic() > deadline or partial_bytes + received > new['size_in_bytes']:
                        raise ValueError('Resumed transfer exceeded its time or byte bound')
                    target.write(block)
                    digest.update(block)
            if partial_bytes + received != new['size_in_bytes'] or 'sha256:' + digest.hexdigest() != new['digest']:
                raise ValueError('Resumed archive does not match the API identity')
            status = 'completed'
    except BaseException as error:
        safe_error = type(error).__name__
        raise ValueError('Resumed transfer failed; preserved partial allocation remains consumed (' + safe_error + ')') from None
    finally:
        collector.write(output.with_suffix('.zip.receipt.json'), {
            'argv': argv, 'started_at_utc': started,
            'finished_at_utc': datetime.now(timezone.utc).isoformat(),
            'returncode': 0 if status == 'completed' else 1, 'status': status,
            'timeout_seconds': limit, 'timed_out': False,
            'resume_source': str(partial_base.relative_to(collector.ROOT)).replace('\\', '/'),
            'copied_prefix_bytes': partial_bytes, 'copied_prefix_sha256': partial_hash,
            'resumed_bytes': received, 'stdout_bytes': output.stat().st_size if output.exists() else 0,
            'stdout_sha256': collector.file_sha256(output) if output.exists() else None,
            'error_type': safe_error, 'copy_buffer_bytes': BUFFER,
            'credential_or_signed_url_retained': False})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--artifact-name', required=True)
    parser.add_argument('--resume-from', type=Path, required=True)
    parser.add_argument('--transfer-timeout-seconds', type=int, default=600)
    args = parser.parse_args()
    base = args.resume_from.resolve()
    if not base.is_relative_to(collector.ROOT / 'runs'):
        raise ValueError('Workspace partial transfer required')
    if json.loads((base / 'plan.json').read_bytes())['run_id'] != args.run_id:
        raise ValueError('Resume source run differs')
    original = collector.command
    collector.command = lambda argv, output, **kwargs: resume_command(original, base, argv, output, **kwargs)
    print(json.dumps(collector.retain(args.run_id, args.output, args.artifact_name, args.transfer_timeout_seconds)))
