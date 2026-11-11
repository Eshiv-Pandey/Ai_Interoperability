"""Check the release's exact evidence bindings, staged bytes and entry links."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'verification.json'
need = lambda value, reason: value or (_ for _ in ()).throw(ValueError(reason))
need(not OUT.exists(), 'fresh_packet_check_required')
status = json.loads((ROOT / 'docs/research/v1-release-status-20261112.json').read_bytes())
need(status['V1_complete'] is True and status['V1_progress_percent'] == 100
     and status['accepted_criteria'] == status['total_criteria'] == 8
     and status['whole_original_research_project_complete'] is False
     and status['whole_project_work_estimate_percent'] == 80, 'release_scope_or_score_changed')
staged = {}
for entry in subprocess.check_output(['git', 'ls-files', '--stage', '-z'], cwd=ROOT).split(b'\0'):
    if entry:
        header, name = entry.split(b'\t', 1)
        mode, blob, stage = header.split()
        need(stage == b'0', 'unmerged_index')
        staged[name.decode()] = blob.decode()
bindings = []
for row in status['evidence_identities']:
    path = ROOT / row['path']
    raw = path.read_bytes()
    need(len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'], 'bound_evidence_changed')
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    need(staged.get(row['path']) == blob, 'bound_evidence_not_exact_in_Git_index')
    bindings.append(row)
documents = ['docs/research/v1-release-status-20261112.md', 'docs/research/v1-release-entrypoint-20261112.md',
             'docs/research/v1-release-independent-acceptance-v2-20261112.md',
             'docs/research/paper-v15-offline-restoration-guide-v2.md']
links = []
for name in documents:
    path = ROOT / name
    for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
        parsed = urlparse(target.strip('<>'))
        if parsed.scheme or target.startswith('#'):
            continue
        resolved = (path.parent / unquote(parsed.path)).resolve()
        need(resolved.is_relative_to(ROOT) and resolved.exists(), 'release_entry_link_missing:' + target)
        links.append({'document': name, 'target': target})
result = {'status': 'passed_release_evidence_index_and_entry_links', 'evidence_bindings_checked': bindings,
          'local_links_checked': links, 'V1_progress_percent': 100, 'whole_project_estimate_percent': 80,
          'whole_project_complete': False, 'human_review_or_publication_granted': False,
          'new_solver_application_or_provider_calls': 0,
          'verifier_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
with OUT.open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(result, stream, indent=2, sort_keys=True)
    stream.write('\n')
print(json.dumps({'status': result['status'], 'bindings': len(bindings), 'links': len(links)}))
