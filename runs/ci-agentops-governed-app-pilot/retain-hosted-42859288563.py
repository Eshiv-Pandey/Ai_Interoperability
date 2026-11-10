"""Retain the actual GitHub artifact bytes and metadata once; no experiment rerun."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import zipfile

RUN = 42859288563
HEAD = '014c9d902c35629f27e68290f59872560b67ea17'
REPO = 'Eshiv-Pandey/Ai_Interoperability'
BASE = Path(__file__).resolve().parent
OUT = BASE / ('hosted-' + str(RUN))
OUT.mkdir(exist_ok=False)

def fetch(endpoint, name):
    started = datetime.now(timezone.utc).isoformat()
    completed = subprocess.run(['gh', 'api', endpoint], capture_output=True, timeout=60, check=False)
    path = OUT / name
    path.write_bytes(completed.stdout)
    (OUT / (name + '.stderr')).write_bytes(completed.stderr)
    if completed.returncode:
        raise RuntimeError('GitHub capture failed for ' + endpoint)
    return completed.stdout, {'endpoint': endpoint, 'started_at_utc': started,
        'finished_at_utc': datetime.now(timezone.utc).isoformat(),
        'returncode': completed.returncode, 'path': path.name,
        'bytes': len(completed.stdout), 'sha256': hashlib.sha256(completed.stdout).hexdigest(),
        'format': 'gh API response-body/output bytes, not authenticated HTTP wire'}

run_raw, run_capture = fetch('repos/' + REPO + '/actions/runs/' + str(RUN), 'github-run.json')
run = json.loads(run_raw)
assert run['head_sha'] == HEAD and run['status'] == 'completed' and run['conclusion'] == 'success'
artifact_raw, artifact_capture = fetch('repos/' + REPO + '/actions/runs/' + str(RUN) + '/artifacts', 'github-artifacts.json')
artifacts = json.loads(artifact_raw)['artifacts']
selected = [item for item in artifacts if item['name'] == 'agentops-governed-app-pilot-42859288563-1' and not item['expired']]
assert len(selected) == 1
artifact = selected[0]
zip_raw, zip_capture = fetch('repos/' + REPO + '/actions/artifacts/' + str(artifact['id']) + '/zip', 'artifact.zip')
assert zip_raw.startswith(b'PK')
expected = artifact.get('digest')
assert expected == 'sha256:' + zip_capture['sha256'], 'Artifact digest mismatch'
destination = OUT / 'extracted'
destination.mkdir()
with zipfile.ZipFile(OUT / 'artifact.zip') as archive:
    names = archive.namelist()
    assert len(names) == len(set(names)), 'Duplicate ZIP member'
    for member in archive.infolist():
        path = PurePosixPath(member.filename)
        assert not path.is_absolute() and '..' not in path.parts and '\\' not in member.filename
        assert ((member.external_attr >> 16) & 0o170000) != 0o120000, 'ZIP symlink refused'
        target = destination.joinpath(*path.parts).resolve()
        assert target.is_relative_to(destination.resolve())
    archive.extractall(destination)
inventory = []
for path in sorted(destination.rglob('*')):
    if path.is_file():
        raw = path.read_bytes()
        inventory.append({'path': path.relative_to(destination).as_posix(), 'bytes':len(raw),
                          'sha256':hashlib.sha256(raw).hexdigest()})
receipt = {'schema_version':'hosted-agentops-governed-app-artifact-retention/1', 'run_id':RUN, 'head_sha':HEAD,
    'run_conclusion':run['conclusion'], 'artifact_id':artifact['id'], 'artifact_name':artifact['name'],
    'api_digest':expected, 'raw_zip_sha256':zip_capture['sha256'], 'raw_zip_bytes':len(zip_raw),
    'digest_matches_api':True, 'zip_members':len(names), 'extracted_files':len(inventory),
    'captured_at_utc':datetime.now(timezone.utc).isoformat(),
    'captures':[run_capture, artifact_capture, zip_capture], 'inventory':inventory,
    'new_solver_application_or_model_requests':0, 'human_review':False,
    'scope':'Artifact retention and byte integrity only; actual admission/task/receipt claims need independent capture review.'}
(OUT / 'retention.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps({key:receipt[key] for key in ('run_id','head_sha','artifact_id','raw_zip_sha256','raw_zip_bytes','zip_members','extracted_files')}, indent=2))
