"""Record actual v8 success without rewriting its sealed evidence."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'docs/research/source-evidence/agentops-success-integration-v8'


def digest(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    result_path = ROOT / 'runs/agentops-native-eligibility/linux-socket-resume-v8/result.json'
    audit_path = ROOT / 'runs/agentops-native-eligibility/socket-resume-parent-check-v8.json'
    result = json.loads(result_path.read_bytes())
    audit = json.loads(audit_path.read_bytes())
    assert result['status'] == 'native_and_http_controls_passed'
    assert audit['status'] == 'artifact_integrity_and_semantics_verified'
    assert result['exported_files'] == audit['files_checked'] == 1046
    assert result['parent_inputs_unchanged'] and not result['export_reference_failures']
    context = ['RESEARCH_WORKFLOW.md', 'docs/research/execution-handoff.md',
               'docs/research/checkpoint-status.json']
    PACKAGE.mkdir(parents=True, exist_ok=False)
    before = []
    for name in context:
        path = ROOT / name
        saved = PACKAGE / 'pre-edit' / name
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.write_bytes(path.read_bytes())
        before.append(digest(saved))
    note = '''**Actual v8 controls completed and checked (26 October 2026):**
The [native/HTTP result note](docs/research/agentops-native-http-results-v8.md)
records the user-run attempt and passing retained-evidence parent check.
All 1,046 exported files verify; the original task completes after confirmation
with one expected service-state change and one attributed audit row. The
initialization socket probe remains blocked, the permitted HTTP listener stops
cleanly, parent inputs remain unchanged, and no installation or live model call
occurred. **Do not rerun scripts/run_agentops_wsl_v8.ps1.** The old failed
attempts and preparation/verifier seals remain unchanged.

This resolves the native/HTTP execution blocker. It is retained-evidence checking,
not full runtime authentication, an independent semantic oracle or human review.
The actual HTTP profile is no-header A2A 0.3 (`message/stream`, `tasks/get`);
it does not establish canonical A2A 1.0 bridge compatibility. Next, inspect the
installed version/card dispatch and freeze matched native/unchanged-bridge
controls using public confirmation bindings and all permitted alternatives.
The managed shell's WSL restriction remains; no further launch is requested
until a new bounded experiment and checker are prepared.

CP1 passed; CP2 in progress; verified credit **5%**. C1 advantage, source/model
fidelity, unchanged bridge/second-domain qualification, human review, reviewed
corpus, frozen evaluations, reproduction and the complete paper remain open.
The distinct-method objective is unchanged.

'''
    for name, end_marker in [(context[0], '**Original AgentOps archive (25 October):**'),
                             (context[1], 'Updated 25 October 2026')]:
        path = ROOT / name
        content = path.read_text(encoding='utf-8')
        start = content.index('**Parent verifier ready (26 October 2026):**')
        end = content.index(end_marker, start)
        replacement = note if name == context[0] else note.replace('docs/research/agentops-', 'agentops-')
        path.write_text(content[:start] + replacement + content[end:], encoding='utf-8', newline='\n')
    path = ROOT / context[2]
    status = json.loads(path.read_bytes())
    assert status['progress_percent'] == 5 and not status['novelty_demonstrated']
    cp2 = next(row for row in status['checkpoints'] if row['id'] == 'CP2')
    assert cp2['status'] == 'in_progress'
    cp2['evidence'].extend(['agentops-native-http-results-v8.md',
        '../../runs/agentops-native-eligibility/linux-socket-resume-v8/result.json',
        '../../runs/agentops-native-eligibility/socket-resume-parent-check-v8.json'])
    cp2['source_leads'].update({
        'agentops': 'Original commit-labeled archive and Linux native/HTTP controls verified; unchanged bridge profile and human domain validity remain open.',
        'agentops_runtime_setup': 'Persistent Linux v7 setup reused; v8 native-v7 test and boundary/effect check passed. Historical v7 observer failure unchanged.',
        'agentops_http_control': 'HTTP-v5 passed original-task confirmation/effect checks on actual no-version-header A2A 0.3 wire; canonical 1.0 and bridges untested.',
        'agentops_wsl_entry': 'User ran v8 successfully; do not repeat. Managed WSL access remains restricted; next versioned experiment is not yet ready for launch.',
        'agentops_resume_verification': 'Actual v8 parent check passed: 1046 files, selected provider/setup bytes, native and HTTP effects rechecked; no scientific gate credit.'})
    path.write_text(json.dumps(status, indent=2) + '\n', encoding='utf-8', newline='\n')
    receipt = {'schema_version': 'agentops-success-integration/8', 'pre_edit_files': before,
               'result_inputs': [digest(result_path), digest(audit_path)],
               'updated_files': [digest(ROOT / name) for name in context],
               'new_files': [digest(Path(__file__).resolve()), digest(ROOT / 'docs/research/agentops-native-http-results-v8.md')],
               'progress_percent': 5, 'paper_edited': False, 'scope_changed': False}
    (PACKAGE / 'context-update.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'integrated', 'progress_percent': 5, 'snapshots': len(before)}))


if __name__ == '__main__':
    main()
