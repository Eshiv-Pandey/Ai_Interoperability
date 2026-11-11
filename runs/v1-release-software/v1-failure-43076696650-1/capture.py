"""Retain terminal hosted preflight failure and inspect bank source packaging."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent

def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')

commands = (
    ('github-run.json', ['gh', 'api', 'repos/Eshiv-Pandey/Ai_Interoperability/actions/runs/43076696650']),
    ('github-artifacts.json', ['gh', 'api', 'repos/Eshiv-Pandey/Ai_Interoperability/actions/runs/43076696650/artifacts']),
    ('failed-step.log', ['gh', 'run', 'view', '43076696650', '--repo', 'Eshiv-Pandey/Ai_Interoperability', '--log-failed']),
)
receipts = []
for name, argv in commands:
    with (OUT / name).open('xb') as stdout, (OUT / (name + '.stderr')).open('xb') as stderr:
        process = subprocess.run(argv, cwd=ROOT, stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL, timeout=90)
    if process.returncode:
        raise ValueError('terminal_failure_capture_transfer_failed')
    raw = (OUT / name).read_bytes()
    receipts.append({'argv': argv, 'returncode': process.returncode, 'output': name,
                     'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
run = json.loads((OUT / 'github-run.json').read_bytes())
assert run['status'] == 'completed' and run['conclusion'] == 'failure'
assert run['head_sha'] == '03590f3d54c100caef411d0102f319b9e6133c1d'
assert json.loads((OUT / 'github-artifacts.json').read_bytes())['artifacts'] == []
write(OUT / 'retention.json', {'run_id': run['id'], 'head_sha': run['head_sha'],
    'status': 'failed_before_source_capture_tests_or_demo', 'artifact_count': 0,
    'artifact_upload_failed_because_allocation_was_not_created': True,
    'failure': 'Missing or nonregular input: external/agentops-c806b7f1/agents/data/incidents.db',
    'root_same_failure_reproduced_in_clean_worktree': True, 'commands': receipts,
    'new_application_or_provider_calls': 0, 'software_acceptance_credit': 0})
spec = importlib.util.spec_from_file_location('_bank', ROOT / 'scripts/validate_task_banks_v1.py')
bank = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bank)
indexed = set(subprocess.check_output(['git', 'ls-files'], cwd=ROOT).decode().splitlines())
files = set()
for domain in ('agentops', 'ap2'):
    values = [json.loads((ROOT / f'benchmark/tasks-v1/{domain}/{kind}.json').read_bytes())
              for kind in ('application', 'evaluator')]
    report = bank.validate_pair(*values, lambda path: bank.read_regular(ROOT, path))
    files.update(report['source_files'])
missing = []
for name in sorted(files - indexed):
    raw = (ROOT / name).read_bytes()
    missing.append({'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
write(OUT / 'bank-source-index-gaps.json', {'source_files_checked': len(files), 'missing': missing})
print(json.dumps({'source_files_checked': len(files), 'unindexed_sources': missing}))
