"""Fresh streamed artifact download after a retained first timeout; no rerun."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import zipfile

BASE = Path(__file__).resolve().parent
PRIOR = BASE / 'hosted-42859288563'
OUT = BASE / 'hosted-42859288563-2'
OUT.mkdir(exist_ok=False)
for name in ('github-run.json', 'github-artifacts.json'):
    shutil.copyfile(PRIOR / name, OUT / name)
run = json.loads((OUT / 'github-run.json').read_bytes())
assert run['head_sha'] == '014c9d902c35629f27e68290f59872560b67ea17'
assert run['conclusion'] == 'success' and run['status'] == 'completed'
artifacts = json.loads((OUT / 'github-artifacts.json').read_bytes())['artifacts']
artifact = next(item for item in artifacts if item['id'] == 13784182896)
assert not artifact['expired']
archive_path = OUT / 'artifact.zip'
command = ['gh', 'api', 'repos/Eshiv-Pandey/Ai_Interoperability/actions/artifacts/13784182896/zip']
started = datetime.now(timezone.utc).isoformat()
try:
    with archive_path.open('xb') as stream, (OUT / 'download.stderr').open('xb') as errors:
        completed = subprocess.run(command, stdout=stream, stderr=errors, timeout=180, check=False)
    assert completed.returncode == 0
except BaseException as error:
    (OUT / 'download-failure.json').write_text(json.dumps({'status':'retained_download_failed',
        'started_at_utc':started,'finished_at_utc':datetime.now(timezone.utc).isoformat(),
        'exception':type(error).__name__,'error':str(error),
        'partial_zip_bytes_retained':archive_path.stat().st_size if archive_path.exists() else 0,
        'application_run_failed':False},indent=2)+'\n',encoding='utf-8')
    raise
def hash_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1_048_576):
            digest.update(chunk)
    return digest.hexdigest()
archive_hash = hash_file(archive_path)
assert artifact['digest'] == 'sha256:' + archive_hash, 'Artifact digest mismatch'
destination = OUT / 'extracted'
destination.mkdir()
with zipfile.ZipFile(archive_path) as archive:
    names = archive.namelist()
    assert len(names) == len(set(names))
    for member in archive.infolist():
        path = PurePosixPath(member.filename)
        assert not path.is_absolute() and '..' not in path.parts and '\\' not in member.filename
        assert ((member.external_attr >> 16) & 0o170000) != 0o120000
        assert destination.joinpath(*path.parts).resolve().is_relative_to(destination.resolve())
    archive.extractall(destination)
inventory = [{'path':path.relative_to(destination).as_posix(),'bytes':path.stat().st_size,'sha256':hash_file(path)}
             for path in sorted(destination.rglob('*')) if path.is_file()]
receipt = {'schema_version':'hosted-agentops-governed-app-artifact-retention/2',
    'run_id':42859288563,'head_sha':run['head_sha'],'artifact_id':artifact['id'],
    'artifact_name':artifact['name'],'run_conclusion':run['conclusion'],
    'raw_zip_sha256':archive_hash,'raw_zip_bytes':archive_path.stat().st_size,
    'api_digest':artifact['digest'],'digest_matches_api':True,'zip_members':len(names),
    'extracted_files':len(inventory),'inventory':inventory,
    'started_at_utc':started,'finished_at_utc':datetime.now(timezone.utc).isoformat(),
    'metadata_reused_from_retained_first_attempt':str(PRIOR),
    'new_application_or_model_requests':0,'human_review':False,
    'scope':'Streamed raw artifact retention and byte integrity only; first failed download remains unchanged.'}
(OUT / 'retention.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:receipt[k] for k in ('run_id','raw_zip_sha256','raw_zip_bytes','zip_members','extracted_files')},indent=2))
