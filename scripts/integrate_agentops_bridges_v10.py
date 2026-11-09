"""Prepare/apply a data-driven documentation update after final v10 verification.

No bridge, application, checker, solver or experiment is launched. Without
--apply this validates existing final receipts and prints the proposed summary.
An applied integration is exclusive and retains all six documents' exact prior
bytes before writing any update. A partial integration is never silently retried.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'docs/research/source-evidence/agentops-bridge-integration-v10'
RUN = 'runs/agentops-native-eligibility/linux-bridge-v10'
CHECK = 'runs/agentops-native-eligibility/bridge-parent-check-v10.json'
SEAL = 'docs/research/source-evidence/agentops-bridge-control-v1/manifest.json'
SOFTWARE = 'runs/agentops-native-eligibility/bridge-software-preparation-v1/result.json'
PRECHECK = 'runs/agentops-native-eligibility/bridge-preparation-parent-check-v1.json'
METHOD = 'docs/research/c1-callsite-factoring-screen-v1.md'
NOTE = 'docs/research/agentops-bridge-results-v10.md'
SCRIPT = 'scripts/integrate_agentops_bridges_v10.py'
TARGETS = ('README.md', 'RESEARCH_WORKFLOW.md', 'docs/research/execution-handoff.md',
           'docs/research/checkpoint-status.json', 'docs/research/implementation-novelty-gate.md',
           'docs/research/deadline-plan-v2.md')
CASE_IDS = ['N' + str(index) for index in range(1, 12)] + ['B' + str(index) for index in range(1, 8)]
BRIDGE_LABELS = {
    'B1': 'Amir ordinary typed text', 'B2': 'Amir Tasks form',
    'B3': 'Amir MRTR opaque-state continuation', 'B4': 'mgcrea typed polling text',
    'B5': 'mgcrea stock raw request', 'B6': 'mgcrea public factory, passthrough fetch',
    'B7': 'mgcrea public factory, explicit version-header fetch',
}
OUTCOMES = {'strict_success', 'unknown_or_partial', 'completed_without_required_effect', 'observed_non_success'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def local(name):
    value = PurePosixPath(name)
    require(not value.is_absolute() and '..' not in value.parts, 'Expected workspace-relative path')
    target = ROOT / name
    require(target.resolve().is_relative_to(ROOT.resolve()), 'Path escaped the workspace')
    return target


def load(name):
    return json.loads(local(name).read_bytes())


def record(name):
    raw = local(name).read_bytes()
    return {'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def verify_record(row):
    require(record(row['path']) == row, 'Changed retained input: ' + row['path'])


def write_json(name, value):
    with local(name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def preparation_count(software):
    require(software.get('schema_version') == 'agentops-bridge-software-preparation/1'
            and software.get('status') == 'passed' and software.get('inputs_unchanged') is True,
            'Passing final preparation required')
    require(software.get('application_requests') == software.get('live_model_calls') == 0,
            'Preparation must remain an offline software check')
    require([row['label'] for row in software['commands']] == ['python-bridge', 'python-observer', 'node'],
            'Exact preparation stages')
    counts = {}
    for row in software['commands']:
        require(type(row.get('returncode')) is int and row['returncode'] == 0 and not row.get('timed_out'),
                'Preparation command did not finish successfully')
        streams = {}
        for item in row['streams']:
            verify_record(item)
            streams[PurePosixPath(item['path']).name] = local(item['path']).read_text(encoding='utf-8')
        if row['label'].startswith('python-'):
            text = streams[row['label'] + '.stderr.bin']
            matches = re.findall(r'^Ran (\d+) tests? in ', text, re.MULTILINE)
            require(len(matches) == 1 and re.search(r'^OK\s*$', text, re.MULTILINE), 'Passing unittest count')
            counts[row['label']] = int(matches[0])
        else:
            text = streams['node.stdout.bin']
            metrics = {name: re.findall(r'^# ' + name + r' (\d+)\s*$', text, re.MULTILINE)
                       for name in ('tests', 'pass', 'fail', 'cancelled', 'skipped', 'todo')}
            require(all(len(values) == 1 for values in metrics.values()), 'Complete Node test totals')
            metrics = {name: int(values[0]) for name, values in metrics.items()}
            require(metrics['tests'] == metrics['pass'] and all(metrics[name] == 0
                    for name in ('fail', 'cancelled', 'skipped', 'todo')), 'All Node tests passed')
            counts['node'] = metrics['pass']
    require(sum(counts.values()) == 128, 'Expected the sealed 128 passing preparation tests')
    return counts


def validated_inputs():
    result, checked, seal, software, precheck = (load(name) for name in
        (RUN + '/result.json', CHECK, SEAL, SOFTWARE, PRECHECK))
    require(checked.get('schema_version') == 'agentops-bridge-group-check/1'
            and checked.get('status') == 'artifact_integrity_and_semantics_verified'
            and checked.get('valid') is True, 'Final parent bridge integrity/semantics verification required')
    require(result.get('schema_version') == 'agentops-bridge-group/1'
            and result.get('status') == checked.get('recorded_group_status'), 'Parent/group terminal status binding')
    require(checked.get('all_planned_cases_accounted') is True
            and list(checked['cases']) == list(result['cases']) == CASE_IDS,
            'Exactly 18 ordered planned cases must be accounted for')
    require(seal.get('schema_version') == 'agentops-bridge-preparation/1'
            and [row['case_id'] for row in seal['cases']] == CASE_IDS, 'Exact sealed case identities')
    require(result.get('parent_inputs_unchanged') is True and result.get('export_reference_failures') == []
            and type(checked.get('files_checked')) is int
            and checked['files_checked'] == result.get('exported_files'), 'Verified complete export and parent inputs')
    require(all(type(result.get(key)) is int and result[key] == 0
                for key in ('installations', 'live_model_calls', 'research_gate_credit_added'))
            and result.get('qualified_second_domain') is False
            and checked.get('qualified_second_domain') is False
            and checked.get('scientific_gate_credit_added') == 0, 'No new scientific credit or domain qualification')
    require(precheck.get('status') == 'prospective_preparation_verified' and precheck.get('valid') is True
            and precheck.get('cases') == 18, 'Retained prospective parent preparation check')
    for row in seal['launch_inputs'] + seal['prerequisites']:
        verify_record(row)
    tests = preparation_count(software)
    definitions = {row['case_id']: row for row in seal['cases']}
    counts = Counter(executed=0, skipped=0, unexecuted=0)
    rows = []
    for case_id in CASE_IDS:
        outer, report, definition = result['cases'][case_id], checked['cases'][case_id], definitions[case_id]
        accounting = outer['status'] if outer['status'] in ('skipped', 'unexecuted') else 'executed'
        counts[accounting] += 1
        require(report.get('outcome') in OUTCOMES and type(report.get('strict_success')) is bool
                and type(report.get('complete')) is bool, 'Explicit checked outcome for ' + case_id)
        require(report.get('status') == outer['status'], 'Case status binding for ' + case_id)
        if accounting != 'executed':
            require(report['strict_success'] is False and report['complete'] is False, 'No success for absent execution')
        else:
            require(report.get('valid') is True and report.get('case_id') == case_id
                    and report.get('kind') == definition['kind'], 'Valid bound case check for ' + case_id)
            require(outer.get('strict_success') is report['strict_success'], 'Group/case strict result binding')
        require(not report['strict_success'] or report['complete'] and report['outcome'] == 'strict_success',
                'Strict success requires complete evidence')
        service = report.get('service') or {}
        effect = service.get('effect') or {}
        reasons = ([outer['reason']] if outer.get('reason') else [])
        reasons.extend(report.get('observation_gaps', []))
        reasons.extend(report.get('policy_deviations', []))
        rows.append({'case_id': case_id, 'kind': definition['kind'], 'definition': definition,
                     'accounting': accounting, 'status': outer['status'], 'outcome': report['outcome'],
                     'strict_success': report['strict_success'], 'complete': report['complete'],
                     'final_state': service.get('final_state'), 'effect_classification': effect.get('classification'),
                     'new_audit_rows': effect.get('new_audit_rows'), 'reasons': reasons,
                     'failed_prerequisites': outer.get('failed_prerequisites', [])})
    require(dict(counts) == checked['counts'] and sum(counts.values()) == 18, 'Parent exact execution accounting')
    require(checked.get('complete_matrix') is (counts['executed'] == 18), 'Complete-matrix flag')
    method = local(METHOD).read_text(encoding='utf-8')
    require('Decision: unselected' in method and 'no additional C1 construction' in method,
            'Expected retained callsite method screen with no demonstrated C1 construction')
    summary = {'planned': 18, **dict(counts), 'strict_success': sum(row['strict_success'] for row in rows),
               'complete_recorded_non_success': sum(row['accounting'] == 'executed' and row['complete']
                                                    and not row['strict_success'] for row in rows),
               'unknown_or_partial_executed': sum(row['accounting'] == 'executed' and not row['complete'] for row in rows),
               'files_checked': checked['files_checked'], 'all_evidence_complete': checked['all_evidence_complete'],
               'recorded_group_status': result['status'], 'preparation_tests': tests,
               'cases': rows, 'progress_percent': 5, 'deadline': '2026-11-10', 'scope_changed': False}
    return result, checked, seal, summary


def cell(value):
    if value is None:
        return 'not observed'
    return str(value).replace('|', '\\|').replace('\r', ' ').replace('\n', ' ')


def table_row(row):
    case_id = row['case_id']
    definition = row['definition']
    label = (definition['profile'] + ' / ' + definition['representation']) if row['kind'] == 'native' else BRIDGE_LABELS[case_id]
    suffix = '.json' if row['accounting'] == 'executed' else '.' + row['accounting'] + '.json'
    values = [f'[{case_id}](../../{RUN}/{case_id}{suffix})', label, row['status'], row['outcome'],
              row['final_state'], row['effect_classification'], row['new_audit_rows']]
    return '| ' + ' | '.join(cell(value) for value in values) + ' |'


def render_note(result, checked, seal, summary, date):
    rows = '\n'.join(table_row(row) for row in summary['cases'])
    diagnostic_rows = []
    for row in summary['cases']:
        if row['reasons'] or row['failed_prerequisites']:
            reasons = '; '.join(row['reasons']) or 'No further diagnostic recorded'
            if row['failed_prerequisites']:
                reasons += '; required native controls: ' + ', '.join(row['failed_prerequisites'])
            diagnostic_rows.append(f"- **{row['case_id']}:** {cell(reasons)}.")
    diagnostics = '\n'.join(diagnostic_rows) or 'No case-level observation gap, policy deviation or non-execution reason was reported.'
    tests = summary['preparation_tests']
    return f'''# AgentOps bridge and matched native controls: checked v10 results

Integrated {date}. This is one bounded development matrix using a reproduced
original AgentOps confirmation fixture and the upstream deterministic model
double. It is not a live-model study, a C1 performance experiment or a qualified
second benchmark domain. The simulated inventory effect is a SQLite state
change; synthetic A2A approver identity is not authenticated human approval.

The [prospective protocol](source-evidence/agentops-bridge-control-v1/protocol.md)
and [seal](source-evidence/agentops-bridge-control-v1/manifest.json) specify
**18 cases: 11 native profile/representation controls and 7 bridge deployment
controls**. The [terminal group](../../{RUN}/result.json) records
`{cell(result['status'])}`. The [final parent check](../../{CHECK}) verifies
**{summary['files_checked']:,} exported files** and accounts for every planned case:
**{summary['executed']} executed, {summary['skipped']} skipped, {summary['unexecuted']} unexecuted**.
The executed cases contain **{summary['strict_success']} strict successes,
{summary['complete_recorded_non_success']} complete recorded non-successes, and
{summary['unknown_or_partial_executed']} unknown or partial outcomes**. Skips and
unexecuted cases remain unknown; they are not negative bridge observations.
No outcome is inferred from a case name or from the source screen.

| Case and receipt | Frozen profile | Recorded status | Independent outcome | Final origin state | Effect classification | New audit rows |
| --- | --- | --- | --- | --- | --- | --- |
{rows}

The outcome column comes from the recomputed whole-case checks. Strict success
requires the original task/context, a legal publicly supplied continuation,
the required completed origin state, exactly one attributed guarded effect,
no early or unrelated domain changes, the declared profile, and complete clean
process evidence. Terminal status or success prose alone is insufficient.
`not observed` records missing evidence and never means zero effects.

## Gaps, deviations and non-execution reasons

{diagnostics}

The full [parent report](../../{CHECK}) retains every nested client, origin,
effect and process diagnostic. Artifact integrity verification is distinct
from complete observations: `all_evidence_complete` is
`{str(checked['all_evidence_complete']).lower()}`. Unknown or partial cases must
not be promoted to observed non-support. A complete recorded non-success is
limited to its fixed attempt and policy; it is not a whole-interface negative
certificate and does not eliminate other legal values, guesses or routes.

## Preparation, deployment and interpretation

The sealed [software preparation](../../{SOFTWARE}) contains **128 passing
tests**: {tests['python-bridge']} Python bridge/checker/supervision tests,
{tests['python-observer']} observer tests and {tests['node']} Node policy/SDK
serialization tests. These are software checks, not 128 application trials.
The [prospective parent check](../../{PRECHECK}) predates this execution.
The [runtime seal](source-evidence/agentops-bridge-control-v1/runtime/preparation-seal.json),
[dependency graph](source-evidence/agentops-bridge-control-v1/runtime/graph.json)
and [runtime verification](source-evidence/agentops-bridge-control-v1/runtime/runtime-verification.json)
retain the deployed package bytes and resolution checks. The frozen Node pin
is `{cell(seal['node']['version'])}` on Linux.

B1-B3 use Amir's ordinary, Tasks and MRTR public routes. B4-B5 use mgcrea's
stock typed and raw tools. B6-B7 use its unchanged public factory with explicit
fetch configuration; B6 forwards the fetch arguments and B7 inserts the scoped
`A2A-Version: 1.0` header. B7 is a configured deployment intervention, not the
stock raw default. Each bridge case depends on the prospectively declared
positive native profile checks. No native effect is itself bridge qualification.

The recorded execution interval is `{result['started_at_utc']}` through
`{result['finished_at_utc']}`. It includes capture and export and is not a method
performance measurement. The group records zero installations and zero live
model calls. Earlier failures, source audits, preparation receipts, and
[v8](agentops-native-http-results-v8.md)/[v9](agentops-native-protocol-results-v9.md)
evidence remain retained. **Do not rerun the completed/attempted v8, v9 or v10
groups, or fill skipped/unexecuted rows by silently resuming this sealed matrix.**
Any additional execution requires a separately specified and versioned study.

## Method and checkpoint consequence

The [callsite-factoring screen](c1-callsite-factoring-screen-v1.md) assesses a
concrete shared serializer/continuation-summary construction and reduces it to
the equally informed interprocedural/shared-DAG comparator. No additional C1
step or advantage is demonstrated. Its separate AI critique is not independent
human scientific review. These controls strengthen bounded evidence only;
they do not repair the method distinction by themselves.

CP1 remains passed; CP2 remains in progress; verified progress stays **5%**.
A distinct method with a fair-comparator advantage, full source-to-model
fidelity, substantive second-domain qualification, actual human review,
reviewed corpus, frozen evaluations, independent scientific reproduction and
the complete paper remain open. The approved objective and scope are unchanged.
The delivery deadline remains **10 November 2026**; see the
[deadline plan](deadline-plan-v2.md).
'''


def current_block(summary, date, prefix):
    return f'''**Current evidence ({date}):** the [checked v10 bridge/native results]({prefix}agentops-bridge-results-v10.md)
account for all 18 planned controls: **{summary['executed']} executed,
{summary['skipped']} skipped and {summary['unexecuted']} unexecuted**. Executed cases
contain {summary['strict_success']} strict successes,
{summary['complete_recorded_non_success']} complete recorded non-successes and
{summary['unknown_or_partial_executed']} unknown or partial outcomes. The parent
check verifies {summary['files_checked']:,} exported files. All **128 preparation
tests pass**. Skips, partial records and fixed-policy non-successes do not prove
whole-interface non-support; configured header behavior remains separately labelled.
**Do not rerun or silently resume the v8/v9/v10 groups.** Historical attempts
and seals are retained.

The [callsite-factoring method screen]({prefix}c1-callsite-factoring-screen-v1.md)
finds no construction beyond the strong shared-summary comparator. CP1 passed;
**CP2 remains open and verified progress stays 5%**. The distinct method,
substantive second domain, reviewed corpus, frozen evaluations, independent
reproduction, actual human review and complete paper remain required.

**Current deadline: 10 November 2026.** The [deadline plan]({prefix}deadline-plan-v2.md)
preserves the full approved scope. Next work must resolve substantive method and
qualification gaps; another source audit or integrity pass cannot pass CP2.

'''


def replace_region(text, start, end, replacement):
    require(text.count(start) == 1, 'Expected one current-section start: ' + start)
    begin = text.index(start)
    finish = text.find(end, begin + len(start))
    require(finish >= 0, 'Missing current-section end: ' + end)
    return text[:begin] + replacement + text[finish:]


def prepare_updates(before, summary, date):
    texts = {name: raw.decode('utf-8') for name, raw in before.items()}
    replacements = (
        ('README.md', '\n\nRegistered project:', 'docs/research/'),
        ('RESEARCH_WORKFLOW.md', '**Historical acquisition notes below', 'docs/research/'),
        ('docs/research/execution-handoff.md', '**Historical handoff entries follow', ''),
        ('docs/research/implementation-novelty-gate.md', 'The entries below are historical source screens', ''),
    )
    for name, end, prefix in replacements:
        texts[name] = replace_region(texts[name], '**Current evidence (', end, current_block(summary, date, prefix))
    deadline = 'docs/research/deadline-plan-v2.md'
    texts[deadline] = replace_region(texts[deadline], 'The [native protocol v9 results]',
        'In parallel, work on a concrete extra method step', current_block(summary, date, ''))
    name = 'docs/research/checkpoint-status.json'
    status = json.loads(texts[name])
    require(status['progress_percent'] == 5 and status['novelty_demonstrated'] is False,
            'Integration must not award novelty or checkpoint credit')
    cp1 = next(row for row in status['checkpoints'] if row['id'] == 'CP1')
    cp2 = next(row for row in status['checkpoints'] if row['id'] == 'CP2')
    require(cp1['status'] == 'passed' and cp2['status'] == 'in_progress', 'Preserve existing checkpoint statuses')
    status.update(as_of=datetime.now(timezone.utc).date().isoformat(), delivery_deadline='2026-11-10',
                  deadline_plan='deadline-plan-v2.md')
    additions = ['agentops-bridge-results-v10.md', 'c1-callsite-factoring-screen-v1.md',
                 'source-evidence/agentops-bridge-control-v1/manifest.json',
                 'source-evidence/agentops-bridge-control-v1/runtime/preparation-seal.json',
                 'source-evidence/agentops-bridge-integration-v10/context-update.json',
                 '../../' + SOFTWARE, '../../' + PRECHECK, '../../' + RUN + '/result.json', '../../' + CHECK]
    cp2['evidence'].extend(name for name in additions if name not in cp2['evidence'])
    cp2['source_leads'].update({
        'agentops': f"v10 accounts for all 18 bounded native/bridge controls: {summary['executed']} executed, {summary['skipped']} skipped, {summary['unexecuted']} unexecuted; substantive second-domain and human validity review remain open.",
        'agentops_http_control': 'v8/v9 retained; v10 supplies profile-matched native and public bridge/configured-deployment observations. Fixed-policy non-success and unknown evidence are not whole-interface negatives.',
        'agentops_wsl_entry': 'v10 attempted once in the existing Linux workspace; do not rerun or silently resume v8/v9/v10.',
        'agentops_resume_verification': f"v10 parent check verifies {summary['files_checked']} exported files and exact 18-case accounting; {summary['strict_success']} strict successes, {summary['complete_recorded_non_success']} complete recorded non-successes, {summary['unknown_or_partial_executed']} partial executed outcomes; no scientific gate credit.",
        'callsite_factoring_method': 'Source-supported shared continuation summaries reduce to the equally informed interprocedural/shared-DAG comparator; candidate unselected, no C1 advantage established.',
    })
    texts[name] = json.dumps(status, indent=2, ensure_ascii=False) + '\n'
    return {name: text.encode('utf-8') for name, text in texts.items()}


def main(apply=False):
    require(not local(PACKAGE).exists() and not local(NOTE).exists(), 'Preserve every prior or partial integration')
    result, checked, seal, summary = validated_inputs()
    before = {name: local(name).read_bytes() for name in TARGETS}
    date = datetime.now(timezone.utc).strftime('%d %B %Y').lstrip('0')
    updates = prepare_updates(before, summary, date)
    note = render_note(result, checked, seal, summary, date).encode('utf-8')
    inputs = [record(name) for name in (RUN + '/result.json', RUN + '/export-manifest.json',
              CHECK, SEAL, SOFTWARE, PRECHECK, METHOD, SCRIPT)]
    if not apply:
        print(json.dumps({'status': 'validated_not_applied', 'summary': summary,
                          'would_update': list(TARGETS), 'would_create': [NOTE, PACKAGE]}, indent=2))
        return
    local(PACKAGE).mkdir(parents=True, exist_ok=False)
    local(PACKAGE + '/pre-edit').mkdir()
    local(PACKAGE + '/proposed').mkdir()
    snapshots = []
    for index, name in enumerate(TARGETS, 1):
        snapshot = PACKAGE + '/pre-edit/' + f'{index:02d}-' + PurePosixPath(name).name
        proposed = PACKAGE + '/proposed/' + f'{index:02d}-' + PurePosixPath(name).name
        local(snapshot).write_bytes(before[name])
        local(proposed).write_bytes(updates[name])
        snapshots.append({'original_path': name, 'snapshot_path': snapshot, 'proposed_path': proposed,
                          'bytes': len(before[name]), 'sha256': hashlib.sha256(before[name]).hexdigest()})
    write_json(PACKAGE + '/pre-edit-manifest.json', {'schema_version': 'agentops-bridge-integration-pre-edit/10',
               'created_at_utc': datetime.now(timezone.utc).isoformat(), 'files': snapshots, 'result_inputs': inputs})
    write_json(PACKAGE + '/result-summary.json', summary)
    # Finish staging and verify every prior byte before changing the first document.
    for name in TARGETS:
        require(local(name).read_bytes() == before[name], 'Document changed during integration preparation: ' + name)
    for row in inputs:
        verify_record(row)
    with local(NOTE).open('xb') as stream:
        stream.write(note)
    for name, raw in updates.items():
        local(name).write_bytes(raw)
    write_json(PACKAGE + '/context-update.json', {
        'schema_version': 'agentops-bridge-integration/10', 'integrated_at_utc': datetime.now(timezone.utc).isoformat(),
        'pre_edit_files': snapshots, 'result_inputs': inputs, 'updated_files': [record(name) for name in TARGETS],
        'new_files': [record(NOTE), record(PACKAGE + '/result-summary.json'), record(SCRIPT)],
        'progress_percent': 5, 'cp2_status': 'in_progress', 'scope_changed': False,
        'deadline': '2026-11-10', 'paper_edited': False, 'fresh_experiment': False,
        'goal_complete': False, 'case_accounting': {key: summary[key] for key in
            ('planned', 'executed', 'skipped', 'unexecuted', 'strict_success',
             'complete_recorded_non_success', 'unknown_or_partial_executed')},
    })
    print(json.dumps({'status': 'integrated', 'planned': 18, 'progress_percent': 5,
                      'deadline': '2026-11-10', 'goal_complete': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Write staged updates after final parent verification')
    main(parser.parse_args().apply)
