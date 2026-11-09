"""Audit draft links and retained numerical evidence; no test/service rerun."""
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / 'paper'
DRAFT = PAPER / 'working-draft-v0.md'
LEDGER = PAPER / 'claim-ledger-v0.json'
OUTPUT = (Path(sys.argv[sys.argv.index('--output') + 1]).resolve()
          if '--output' in sys.argv else PAPER / 'draft-audit-v0.json')
if not OUTPUT.is_relative_to(ROOT):
    raise SystemExit('Audit output must be within this workspace.')

def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))

def entry(path):
    data = path.read_bytes()
    return {'path':path.relative_to(ROOT).as_posix(), 'bytes':len(data),
            'sha256':hashlib.sha256(data).hexdigest()}

if OUTPUT.exists():
    raise SystemExit('Refusing to replace the retained draft audit.')
text = DRAFT.read_text(encoding='utf-8')
title = 'Benchmarking Framework for LLM-Based Agent Interoperability: Measuring Interoperability Loss Across Heterogeneous Agent Boundaries'
assert text.splitlines()[0] == '# ' + title
assert 'not a completed' in text and 'Distinct method: pending.' in text
status = read('paper/draft-status-v0.json')
assert status['complete_paper'] is False and status['human_review_completed'] is False
checkpoint = read('docs/research/checkpoint-status.json')
assert checkpoint['progress_percent'] == 5 and checkpoint['novelty_demonstrated'] is False
assert checkpoint['human_review_completed'] is False
links = []
for target in re.findall(r'\]\(([^)]+)\)', text):
    if target.startswith(('https://','http://')):
        continue
    path = (PAPER / target.split('#',1)[0]).resolve()
    assert path.is_relative_to(ROOT) and path.is_file(), target
    links.append(path)
ledger = read('paper/claim-ledger-v0.json')
evidence = set()
for claim in ledger['claims']:
    assert claim['limit'] and claim['kind'] and claim['evidence']
    for relative in claim['evidence']:
        path = (ROOT / relative).resolve()
        assert path.is_relative_to(ROOT) and path.is_file(), relative
        evidence.add(path)

foundation = read('runs/foundation/verification-v1.json')
clean = read('runs/foundation/clean-replay-v1.json')
assert foundation['exit_code'] == 0 and 'Ran 65 tests' in foundation['stderr']
assert clean['checks'][0]['exit_code'] == 0 and 'Ran 65 tests' in clean['checks'][0]['stderr']
source_matches = {}
for relative in ['src/interoperability/baseline.py','src/interoperability/oracle.py','src/interoperability/manifest.py']:
    source_matches[relative] = entry(ROOT / relative)['sha256'] == foundation['source_sha256'][relative]
assert all(source_matches.values())

group = read('runs/official-handler-bridge-control/group-status-v2.json')
assert group['ordered_variants'] == ['B1','B2','B3','B4']
assert group['service_cases_executed_once'] == 4 and group['service_reruns'] == 0
assert group['native_control_requests'] == 12 and group['evaluator_only_requests'] == 4
assert group['model_calls'] == 0 and group['checker_correction_disclosed'] is True
archive_count = mutation_count = 0
cases = []
for case in group['cases']:
    variant = case['variant']
    assert case['attempts'] == 1 and case['native_eligible'] is True
    assert case['bridge_goal_achieved'] is False
    assert case['evaluator_original_state'] == 'TASK_STATE_INPUT_REQUIRED'
    if variant == 'B4':
        assert case['answer_http_status'] == 500
        assert isinstance(case['answer_rpc_error'], dict) and case['answer_rpc_error']['code'] == -32009
        assert case['answer_version_header'] is None
    else:
        assert case['answer_http_status'] == 200 and case['answer_reference_task_ids'] == []
        assert case['answer_version_header'] == '1.0'
    original = read(f'runs/official-handler-bridge-control/clean-replay-{variant}-v2.json')
    replay_path = f'runs/official-handler-bridge-control/clean-replay-{variant}-v2.1.json'
    replay = read(replay_path)
    assert original['valid'] is False
    assert replay['valid'] is True and replay['archive_unchanged'] is True
    result = replay['result']
    assert result['valid'] is True and result['complete'] is True
    assert result['service_requests'] == 0 and result['sdk_imported'] is False
    mutations = result['mutation_checks']
    assert all(m['claim_rejected'] is True and 'mutation_setup_error' not in m for m in mutations)
    assert entry(ROOT / result['report_path'])['sha256'] == result['report_sha256']
    assert entry(ROOT / case['report']['path']) == case['report']
    evidence.add(ROOT / result['report_path'])
    archive_count += replay['archive_files']
    mutation_count += len(mutations)
    cases.append({'variant':variant,'retained_original_replay_failed':True,
                  'retained_corrected_replay_passed':True,'archive_files':replay['archive_files'],
                  'mutations_rejected':len(mutations),'runtime_report_sha256':result['report_sha256']})
assert archive_count == group['corrected_archive_files'] == 8834
assert mutation_count == group['corrected_mutations_rejected'] == 109
assert sum(c['derived_costs']['native_control_requests'] for c in group['cases']) == 12
assert sum(c['derived_costs']['evaluator_only_requests'] for c in group['cases']) == 4
for receipt in group['evidence']:
    assert entry(ROOT / receipt['path']) == receipt
    evidence.add(ROOT / receipt['path'])

files = evidence | set(links) | {DRAFT,LEDGER,PAPER/'draft-status-v0.json',Path(__file__).resolve(),
                               PAPER/'draft-audit-initial-source-v0.txt',PAPER/'draft-audit-initial-failure-v0.json',
                               PAPER/'draft-audit-v0.json',PAPER/'draft-audit-passing-source-v0.txt'}
report = {'schema_version':'working-paper-draft-audit/1', 'checked_at_utc':datetime.now(UTC).isoformat(),
          'status':'passed', 'title_preserved':True,'draft_complete':False,
          'initial_auditor_development_failure_preserved':'paper/draft-audit-initial-failure-v0.json',
          'draft_words':len(text.split()),'claims_with_evidence_paths':len(ledger['claims']),
          'local_links_checked':len(links),'foundation_current_source_hash_matches':source_matches,
          'retained_foundation_tests':65,'retained_bridge_cases':cases,
          'retained_archive_files':archive_count,'retained_rejected_mutations':mutation_count,
          'files':[entry(p) for p in sorted(files)],'new_service_requests':0,'new_model_calls':0,
          'scope':'Draft links, evidence paths, current core source hashes and consistency of retained reports; no new tests, archive replay or human/scientific validation.'}
with OUTPUT.open('x',encoding='utf-8',newline='\n') as stream:
    json.dump(report,stream,indent=2)
    stream.write('\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['files','retained_bridge_cases']},indent=2))
