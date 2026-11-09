"""Integrate checked native protocol evidence and the user's revised deadline."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'docs/research/source-evidence/agentops-protocol-integration-v9'
RUN = 'runs/agentops-native-eligibility/linux-protocol-v9'
CHECK = 'runs/agentops-native-eligibility/protocol-parent-check-v9.json'
NOTE = 'docs/research/agentops-native-protocol-results-v9.md'


def record(name):
    raw = (ROOT / name).read_bytes()
    return {'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    if (PACKAGE / 'context-update.json').exists() or (ROOT / NOTE).exists():
        raise FileExistsError('Preserve existing integration')
    result = json.loads((ROOT / RUN / 'result.json').read_bytes())
    checked = json.loads((ROOT / CHECK).read_bytes())
    assert result['status'] == 'native_protocol_controls_passed'
    assert checked['status'] == 'artifact_integrity_and_semantics_verified'
    assert result['exported_files'] == checked['files_checked']
    assert result['parent_inputs_unchanged'] and not result['export_reference_failures']
    assert result['installations'] == result['live_model_calls'] == 0
    assert set(checked['cases']) == {'sync', 'stream'}
    for case, data in checked['cases'].items():
        assert data['status'] == 'passed' and data['case'] == case and data['new_audit_rows'] == 1
        assert data['cards_equal'] and set(data['card_protocol_versions'].values()) == {'0.3'}
        assert all(row['error']['code'] == -32009 for row in data['omitted_header_results'].values())
    before = json.loads((PACKAGE / 'pre-edit-manifest.json').read_bytes())['files']
    for row in before:
        actual = record(row['original_path'])
        assert actual['sha256'] == row['sha256'] and actual['bytes'] == row['bytes']
        assert (ROOT / row['snapshot_path']).read_bytes() == (ROOT / row['original_path']).read_bytes()
    files = checked['files_checked']
    note = f'''# AgentOps native protocol controls: checked v9 results

Recorded 27 October 2026. These are development controls on the original
application factory and upstream deterministic model double, not bridge runs,
live-model results, a novel method or a qualified second benchmark domain.

The [frozen protocol](source-evidence/agentops-protocol-control-v1/protocol.md)
ran once as two fresh isolated cases, sync then stream. The
[terminal result](../../{RUN}/result.json) reports both controls passed.
The [parent check](../../{CHECK}) recomputes wire/effect checks and verifies
all **{files:,} exported files**, historical evidence and the unchanged parent inputs.
Do not rerun `scripts/run_agentops_protocol_wsl_v9.ps1` or completed v8.

| Fixed case | Observed result |
| --- | --- |
| Canonical synchronous `SendMessage` with `A2A-Version: 1.0` | Original task/context completes after the public bound DataPart confirmation; one expected inventory status change and one attributed audit row |
| Canonical `SendStreamingMessage` with that header | Same requirements pass from the complete captured stream and final `GetTask` |
| Identical canonical `GetTask` and confirmation requests with the header omitted | JSON-RPC `-32009` in both cases; no domain effect before the accepted confirmation |
| Agent card with and without the header | Equal card contents; both contain top-level `protocolVersion: "0.3"` while canonical handlers accept the explicit 1.0 profile |
| Cleanup and resources | Both services exit cleanly; expected initialization socket probe remains blocked; no unexpected network attempts, installations or live model calls |

The observed execution interval was `{result['started_at_utc']}` through
`{result['finished_at_utc']}`. This includes capture and export; it is not a
method-performance measurement. The inventory restart changes simulated SQLite
service state, not infrastructure. Synthetic A2A approver identity is not
authenticated human approval. Terminal status or model prose alone is not the
success criterion: the checker also requires the original task/context, bound
confirmation, exactly one complete audit row and no unrelated domain changes.

## Preparation and retained failures

The previous Windows temporary-directory failure remains in
[preparation v1-5](../../runs/agentops-native-eligibility/protocol-preparation-v1-5/result.json).
The unchanged 18 tests passed under the current environment in v1-6. A separate
preparation defect was corrected before any v9 application execution: the
verifier had retained older launch/prerequisite lists. Both preparation and
export checkers now use the same exact seal contract and reject stale or narrowed
software receipts. Ten added regression tests bring the final
[software preparation](../../runs/agentops-native-eligibility/protocol-preparation-v1-7/result.json)
to **28 passing tests**. Original checker/contract bytes are retained in
`runs/agentops-native-eligibility/protocol-preparation-correction-v2/`.

A read-only installed-source inspection pins **150 A2A/ADK Python modules**.
The [new manifest](source-evidence/agentops-protocol-control-v1/manifest-v2.json)
and [pre-execution check](../../runs/agentops-native-eligibility/protocol-preparation-check-v2.json)
bind those modules, tests, scripts, and v8 evidence; the check also compares
module hashes with installed distribution RECORD entries. Earlier preparation
seals and failed attempts are retained. This is evidence consistency checking,
not full runtime/capture authentication, independent semantic validation or
human scientific review.

## Consequence for the next experiment

A no-header card's `protocolVersion` cannot alone determine which canonical
requests the server accepts. Preserve each bridge's actual discovery headers,
request defaults and permitted configuration. The
[bridge profile plan](agentops-bridge-profile-plan-v1.md) separates unchanged
default behavior from explicit header/fetch configuration and keeps every legal
confirmation route in scope. It is an unexecuted proposal; its harness/checker
and prospective seal still need completion before application execution.

Native v9 does not match every typed bridge's nonblocking, polling, Tasks or
callback behavior. Add those matched native controls before interpreting such
bridge results. Do not infer full-interface failure from a text-only send or
count a header intervention as default behavior.

The [C1 effect assessment](c1-agentops-effect-screen-v1.md) finds that these
bindings still fit the established source-recipe comparator; no new algorithm
or performance trial follows from the native result.

CP1 remains passed, CP2 in progress, verified gate credit **5%**. C1 advantage,
whole-route source/model fidelity, unchanged bridge/second-domain qualification,
actual human review, reviewed corpus, frozen evaluations, independent scientific
reproduction and the complete paper remain open. The original distinct-method
objective is unchanged. The user's revised delivery date is **10 November 2026**;
see the [deadline plan](deadline-plan-v2.md).
'''
    (ROOT / NOTE).write_text(note, encoding='utf-8', newline='\n')
    current = f'''**Current evidence (27 October 2026):** the [native protocol v9 results](docs/research/agentops-native-protocol-results-v9.md)
verify synchronous and streaming canonical A2A 1.0 confirmation with one original-task
effect per case. The parent check verifies {files:,} exported files. Matched omitted-header
requests return -32009 without effects; both card variants still advertise 0.3.
All 28 preparation tests pass; 150 protocol modules are pinned. No installation
or live model call occurred. WSL execution succeeded in the current environment.
**Do not rerun completed v8 or v9.** Historical failures/seals are preserved.

Next, implement and freeze the [matched unchanged-bridge controls](docs/research/agentops-bridge-profile-plan-v1.md),
including default versus configured headers and all permitted confirmation alternatives.
Native success is not bridge qualification or C1 novelty. CP1 passed; CP2 in progress;
verified credit remains **5%**. The distinct method, reviewed corpus, frozen evaluations,
independent reproduction, human review and complete paper remain open.

**Current deadline: 10 November 2026**, following the user's 27 October two-week
instruction. The [deadline plan](docs/research/deadline-plan-v2.md) supersedes the
old 45-day calendar without reducing the approved requirements.

'''
    workflow = ROOT / 'RESEARCH_WORKFLOW.md'
    text = workflow.read_text(encoding='utf-8')
    begin = text.index('Prepared:')
    end = text.index('\n\nRegistered project title', begin)
    text = text[:begin] + ('Prepared: 23 October 2026; local execution began 24 October. '
        'Updated deadline: **10 November 2026**, from the user\'s 27 October two-week instruction. '
        'The original 45-day calendar is historical; the approved research scope and gates remain unchanged.') + text[end:]
    text = text.replace('within 1.5 months.', 'by the revised 10 November 2026 deadline.')
    begin = text.index('**Actual v8 controls completed and checked')
    end = text.index('**Original AgentOps archive', begin)
    text = text[:begin] + current + '**Historical acquisition notes below describe their capture-time state. Current runtime status is above.**\n\n' + text[end:]
    text = text.replace('## 12. Forty-five-day student execution plan',
        '## 12. Historical forty-five-day allocation\n\nThe current calendar is [deadline plan v2](docs/research/deadline-plan-v2.md), ending 10 November 2026. The table below preserves the original allocation and requirements; its dates no longer govern delivery.')
    workflow.write_text(text, encoding='utf-8', newline='\n')
    handoff = ROOT / 'docs/research/execution-handoff.md'
    text = handoff.read_text(encoding='utf-8')
    end = text.index('Updated 25 October 2026')
    handoff.write_text('# Current execution handoff\n\n' + current.replace('docs/research/', '') +
        '**Historical handoff entries follow; newer evidence above supersedes their runtime and calendar status.**\n\n' + text[end:], encoding='utf-8', newline='\n')
    readme = ROOT / 'README.md'
    text = readme.read_text(encoding='utf-8')
    readme.write_text(text.replace('# Agent interoperability research\n', '# Agent interoperability research\n\n' + current, 1), encoding='utf-8', newline='\n')
    gate = ROOT / 'docs/research/implementation-novelty-gate.md'
    text = gate.read_text(encoding='utf-8')
    text = text.replace('## What the fresh source audit changes\n', '## What the fresh source audit changes\n\n' + current.replace('docs/research/', '') +
        'The entries below are historical source screens, not current runtime status.\n', 1)
    gate.write_text(text, encoding='utf-8', newline='\n')
    path = ROOT / 'docs/research/checkpoint-status.json'
    status = json.loads(path.read_bytes())
    assert status['progress_percent'] == 5 and not status['novelty_demonstrated']
    status['as_of'] = '2026-10-27'
    status['delivery_deadline'] = '2026-11-10'
    status['deadline_source'] = 'User instruction 2026-10-27: deadline in two weeks; scope and gates unchanged'
    status['deadline_plan'] = 'deadline-plan-v2.md'
    cp2 = next(row for row in status['checkpoints'] if row['id'] == 'CP2')
    cp2['evidence'].extend(['agentops-native-protocol-results-v9.md',
        'source-evidence/agentops-protocol-control-v1/manifest-v2.json',
        '../../runs/agentops-native-eligibility/protocol-preparation-v1-7/result.json',
        '../../runs/agentops-native-eligibility/protocol-preparation-check-v2.json',
        '../../' + RUN + '/result.json', '../../' + CHECK, 'agentops-bridge-profile-plan-v1.md',
        'c1-agentops-effect-screen-v1.md'])
    cp2['source_leads'].update({
        'agentops': 'Original commit-labeled source; v8 native/0.3 and v9 canonical sync/stream effect controls checked. Unchanged bridges and human domain validity remain open.',
        'agentops_http_control': 'v9 explicit-header 1.0 sync and stream pass; paired no-header canonical probes reject without effects; both cards advertise 0.3. Not all bridge profiles are matched.',
        'agentops_wsl_entry': 'Current WSL execution succeeded; v8/v9 complete and must not be repeated.',
        'agentops_resume_verification': f'v9 parent check verifies {files} exported files and both protocol/effect cases; evidence consistency, no scientific gate credit.',
    })
    path.write_text(json.dumps(status, indent=2) + '\n', encoding='utf-8', newline='\n')
    report = {'schema_version': 'agentops-protocol-integration/9', 'pre_edit_files': before,
        'result_inputs': [record(RUN + '/result.json'), record(CHECK)],
        'updated_files': [record(row['original_path']) for row in before],
        'new_files': [record(NOTE), record('docs/research/deadline-plan-v2.md'),
                      record('docs/research/agentops-bridge-profile-plan-v1.md'),
                      record('docs/research/c1-agentops-effect-screen-v1.md'),
                      record('scripts/integrate_agentops_protocol_v9.py')],
        'progress_percent': 5, 'scope_changed': False, 'deadline': '2026-11-10',
        'paper_edited': False, 'goal_complete': False}
    with (PACKAGE / 'context-update.json').open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'status': 'integrated', 'files_checked': files, 'progress_percent': 5,
                      'deadline': '2026-11-10', 'goal_complete': False}))


if __name__ == '__main__':
    main()
