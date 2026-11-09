"""Recheck the prepared bridge matrix and retained group without executing it.

Only trusted parent validators are imported. ZIP entries are read, never
extracted; exported code, applications, SDKs and launchers are never executed.
Integrity verification does not make an incomplete observation a non-support
result, and a completely observed non-success does not fail this checker.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import posixpath
import zipfile

import agentops_bridge_diagnostic_plan_v1 as design
import prepare_agentops_bridge_diagnostic_v1 as preparation
from agentops_bridge_runtime_archive_v1 import check_graph, safe_name
from check_agentops_bridge_v1 import check_case, check_service
from check_agentops_effect_v2 import seed_snapshot
from check_agentops_bridge_diagnostic_v1 import validate_diagnostics
from check_agentops_bridge_group_v1 import validate_preparation as validate_original
from check_agentops_linux_workspace_v5 import load, record, relative_file, require, verify_rows, zero
from check_agentops_socket_resume_v8 import interval

ROOT = Path(__file__).resolve().parents[1]
PRIOR = 'runs/agentops-native-eligibility/linux-bridge-v10'
SEAL = preparation.PACKAGE + '/manifest.json'
CASE_PREFIX = design.CASE_PREFIX


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(parsed.tzinfo is not None, 'Timezone-aware timestamp required')
    return parsed


def scope(value, fields):
    require(all(zero(value.get(key)) for key in fields), 'Resource/claim scope differs')


def validate_preparation(root=ROOT):
    original, runtime = validate_original(root)
    seal = load(root / SEAL)
    require(seal.get('schema_version') == 'agentops-bridge-diagnostic-preparation/1'
            and seal.get('cases') == list(design.CASES.values())
            and seal.get('case_prefix') == CASE_PREFIX, 'Exact diagnostic allocation')
    scope(seal, ('application_requests', 'live_model_calls', 'research_gate_credit_added'))
    require([row['path'] for row in seal['launch_inputs']] == preparation.LAUNCH_FILES,
            'Exact new launch source inventory')
    verify_rows(root, seal['launch_inputs'] + seal['reuse_inputs'] + seal['prerequisites'])
    require(seal['reuse_inputs'] == load(root / PRIOR / 'execution.json')['inputs'], 'Exact reused v10 inputs')
    require(seal['runtime_root'] == runtime['runtime_root'] and seal['node'] == runtime['node'], 'Retained runtime pin')
    verify_rows(root, [seal['software']])
    tested = load(root / seal['software']['path'])
    require(tested.get('schema_version') == 'agentops-bridge-diagnostic-software/1'
            and tested.get('status') == 'passed' and tested.get('inputs_unchanged') is True,
            'Passing diagnostic software receipt')
    scope(tested, ('application_requests', 'live_model_calls'))
    require(tested['inputs'] == [record(root / name, root) for name in preparation.SOFTWARE_FILES],
            'Exactly tested current diagnostic software')
    require(len(tested['commands']) == len(preparation.PATTERNS), 'All five test stages')
    last = timestamp(tested['started_at_utc'])
    for index, (command, pattern) in enumerate(zip(tested['commands'], preparation.PATTERNS), 1):
        argv = command['argv']
        require(command['label'] == f'stage-{index}' and PurePosixPath(argv[0]).is_absolute()
                and argv[1:] == ['-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', pattern, '-v']
                and zero(command.get('returncode')) and command.get('timed_out') is False, 'Exact passing test stage')
        begin, end = interval(command)
        require(last <= begin <= end <= timestamp(seal['prepared_at_utc']), 'Software precedes seal')
        last = end
        verify_rows(root, command['streams'])
    require(load(root / 'runs/agentops-native-eligibility/bridge-parent-check-v10.json').get('valid') is True,
            'Retained v10 parent check')
    return seal, runtime


def complete_export(exported, manifest, result, expected, prior_files):
    require(result.get('parent_inputs_unchanged') is True, 'Parent inputs changed or unconfirmed')
    require(result.get('export_reference_failures') == manifest.get('reference_failures') == [],
            'Export references incomplete')
    names = verify_rows(exported, manifest['files'])
    verify_rows(exported, expected)
    verify_rows(exported, prior_files)
    actual = set()
    for path in exported.rglob('*'):
        require(not path.is_symlink() and not getattr(path, 'is_junction', lambda: False)(), 'No materialized export links')
        if path.is_file():
            actual.add(path.relative_to(exported).as_posix())
        else:
            require(path.is_dir(), 'Only regular export files/directories')
    require(names == actual and result.get('exported_files') == len(names), 'Complete export file enumeration')
    require(manifest.get('bytes') == sum(row['bytes'] for row in manifest['files']), 'Export byte count')
    inert = set()
    for link in manifest.get('inert_symlinks', []):
        relative_file(exported, link['path'])
        require(link['path'] not in names and link['path'] not in inert and
                not (exported / link['path']).exists(), 'Inert links remain metadata only')
        inert.add(link['path'])
    return names


def owned_group(group, pid):
    """Return cleanup certainty; malformed positive claims are not accepted."""
    if not group or group.get('status') in ('receipt_absent', 'identity_unconfirmed'):
        return False
    require(group.get('schema_version') == 'agentops-owned-process-group/1'
            and group.get('pgid') == pid and type(pid) is int and pid > 1, 'Owned process group identity')
    for key in ('initially_empty', 'final_empty', 'forced_cleanup'):
        require(type(group.get(key)) is bool, 'Explicit process cleanup flags')
    for key in ('members', 'final_members', 'snapshots', 'signals', 'errors'):
        require(type(group.get(key)) is list, 'Retained process membership evidence')
    snapshots = group['snapshots']
    if snapshots:
        require(snapshots[0]['phase'] == 'initial'
                and snapshots[0]['members'] == group['members']
                and snapshots[-1]['members'] == group['final_members'], 'Cleanup snapshots bind membership')
        times = [row['monotonic_ns'] for row in snapshots]
        require(all(type(value) is int and value >= 0 for value in times) and times == sorted(times), 'Cleanup observation order')
    require(group['forced_cleanup'] is bool(group['signals']), 'Forced cleanup agrees with signals')
    if group['initially_empty'] or group['final_empty']:
        require(bool(snapshots) and not group['errors'], 'Empty group claim requires observed error-free membership')
    if group['initially_empty']:
        require(not group['members'] and not snapshots[0]['errors'], 'Initially empty group binding')
    if group['final_empty']:
        require(not group['final_members'] and not snapshots[-1]['errors'], 'Finally empty group binding')
    return group['initially_empty'] and group['final_empty'] and not group['forced_cleanup'] and not group['errors']


def expected_config(definition, linux_root, runtime_root):
    case = PurePosixPath(linux_root) / (CASE_PREFIX + definition['case_id'])
    config = design.client_config(definition, case, PurePosixPath(runtime_root))
    if definition.get('arm') in ('B6', 'B7'):
        config['bridge']['args'][0] = str(PurePosixPath(linux_root) / 'scripts/agentops_mgcrea_embed_v1.mjs')
    return config


def case_bindings(exported, case_id, seal, linux_root, outcome, begin, end, gaps):
    """Check launch/config/source/cleanup evidence whenever that evidence exists."""
    definition = design.CASES[case_id]
    directory = CASE_PREFIX + case_id
    target = exported / directory
    plan_path = target / 'plan.json'
    if not plan_path.exists():
        gaps.append(case_id + ':missing_plan')
        return False
    plan = load(plan_path)
    require(plan.get('schema_version') == 'agentops-bridge-case-plan/1'
            and all(plan.get(key) == value for key, value in definition.items())
            and plan.get('port') == design.PORT and plan.get('bridge_port') == design.BRIDGE_PORT,
            'Case matches prospective definition')
    require(begin <= timestamp(plan['prepared_at_utc']) <= end, 'Case preparation within controller interval')
    require(plan['seal'] == record(exported / SEAL, exported)
            and plan['service_source'] == record(exported / 'scripts/serve_agentops_bridge_diagnostic_v2.py', exported), 'Case sealed harness binding')
    prior_source = load(exported / 'runs/agentops-native-eligibility/native-probe-v7/plan.json')['source_files']
    require(plan['source_files'] == prior_source, 'Original source inventory preserved')
    verify_rows(exported, plan['source_files'])
    config = load(target / 'client-config.json')
    require(config == expected_config(definition, linux_root, seal['runtime_root'])
            and plan['client_config'] == record(target / 'client-config.json', exported), 'Exact prospective client configuration')
    require(load(target / 'agents.json') == {'agents': {'agentops': {
        'cardUrl': f'http://127.0.0.1:{design.PORT}/.well-known/agent-card.json'}}}, 'Exact agent card configuration')
    if outcome:
        require(outcome.get('schema_version') == 'agentops-bridge-case-result/1'
                and outcome.get('case_id') == case_id and outcome.get('kind') == definition['kind']
                and outcome.get('status') in ('recorded', 'failed'), 'Executed case result identity')
        scope(outcome, ('live_model_calls', 'research_gate_credit_added'))
        start, finish = interval(outcome)
        require(timestamp(plan['prepared_at_utc']) <= start <= finish <= end, 'Case result interval')
        case_names = verify_rows(exported, outcome['files'])
        actual = {path.relative_to(exported).as_posix() for path in target.rglob('*') if path.is_file()}
        later = {directory + '/' + name for name in ('result.json', 'case-check.json', 'case-check-error.json', 'diagnostic-check.json', 'diagnostic-source-unavailable.json')}
        later.update(name for name in actual if name.startswith(directory + '/diagnostic-sources/'))
        require(case_names == actual - later and all(name.startswith(directory + '/') for name in case_names),
                'Complete case inventory before terminal result/check')
    else:
        gaps.append(case_id + ':missing_result')
    clean = True
    process_rows = {}
    for label, filename, script in (
            ('client', 'client-process.json', 'agentops_native_profile_client_v1.mjs' if definition['kind'] == 'native' else 'agentops_bridge_client_v1.mjs'),
            ('service', 'service-process.json', 'serve_agentops_bridge_diagnostic_v2.py')):
        if not (target / filename).exists():
            gaps.append(case_id + ':missing_' + label + '_process_receipt')
            clean = False
            continue
        row = load(target / filename)
        process_rows[label] = row
        argv = (['/usr/bin/node', linux_root + '/scripts/' + script, '--config', linux_root + '/' + directory + '/client-config.json']
                if label == 'client' else [linux_root + '/external/runtime-agentops-linux-v7/venv/bin/python', '-B',
                linux_root + '/scripts/' + script, '--output', linux_root + '/' + directory + '/service', '--port', str(design.PORT)])
        require(row['argv'] == argv, 'Exact case process command')
        if 'pid' not in row:
            gaps.append(case_id + ':' + label + '_process_not_started')
            clean = False
            continue
        require(type(row['pid']) is int and row['pid'] > 1, 'Exact case process identity')
        require(begin <= timestamp(row['started_at_utc']) <= end, 'Case child launched during controller interval')
        if label == 'client':
            if (target / 'client.started.json').exists():
                started = load(target / 'client.started.json')
                require(all(row.get(key) == started.get(key) for key in ('argv', 'cwd', 'pid', 'started_at_utc'))
                        and row.get('cwd') == linux_root, 'Client launch/terminal receipt binding')
            else:
                clean = False
                gaps.append(case_id + ':client_start_unconfirmed')
            require(interval(row)[1] <= end, 'Client exits before controller')
            require(verify_rows(exported, row['streams']) == {directory + '/client.' + suffix + '.bin'
                    for suffix in ('stdout', 'stderr')}, 'Both retained client streams')
            require(row.get('owned_group', {}) == outcome.get('client_group_cleanup', {}), 'Client cleanup/result binding')
        cleanup = outcome.get(label + '_group_cleanup', {})
        if not owned_group(cleanup, row['pid']):
            clean = False
            gaps.append(case_id + ':' + label + '_cleanup_unconfirmed_or_forced')
        if label == 'service' and (target / 'service/terminal.snapshot.json').exists() and cleanup.get('snapshots'):
            terminal = load(target / 'service/terminal.snapshot.json')
            require(cleanup['snapshots'][-1]['monotonic_ns'] <= terminal['monotonic_ns'], 'Service cleanup precedes terminal snapshot')
    if 'client' in process_rows and 'service' in process_rows:
        require(timestamp(process_rows['service']['started_at_utc']) <= timestamp(process_rows['client']['started_at_utc']),
                'Service precedes client')
    return clean


def check_stages(run, exported, result, seal, seed):
    """Validate the fixed order, observed outcomes and conditional bridge skips."""
    require(list(result['cases']) == list(design.CASES), 'Exact ordered matrix accounting')
    case_parent = exported / 'runs/agentops-http-control'
    if case_parent.exists():
        require(all(path.name.removeprefix('bridge-diagnostic-v1-') in design.CASES for path in case_parent.iterdir()
                    if path.name.startswith('bridge-diagnostic-v1-')), 'Unplanned bridge case footprint')
    outer_start, outer_end = interval(result)
    require(timestamp(seal['prepared_at_utc']) <= outer_start, 'Prospective seal precedes any attempt')
    last_end = outer_start
    reports, gaps, counts = {}, [], {'executed': 0, 'skipped': 0, 'unexecuted': 0}
    qualified = set()
    stopped = False
    linux_root = result['linux_workspace']
    for case_id, definition in design.CASES.items():
        summary = result['cases'][case_id]
        status = summary.get('status')
        target = exported / (CASE_PREFIX + case_id)
        failed = [name for name in definition['native_prerequisites'] if name not in qualified]
        if status in ('skipped', 'unexecuted'):
            counts[status] += 1
            require(not target.exists() and not any((run / (case_id + suffix)).exists()
                    for suffix in ('.json', '.started.json', '.stdout.bin', '.stderr.bin')), 'Unexecuted cases have no execution footprint')
            require(load(run / (case_id + '.' + status + '.json')) == summary, 'Outer skip/unexecuted receipt binding')
            other = 'unexecuted' if status == 'skipped' else 'skipped'
            require(not (run / (case_id + '.' + other + '.json')).exists(), 'Exclusive case accounting receipt')
            if status == 'skipped':
                require(not stopped and definition['kind'] == 'bridge' and bool(failed)
                        and summary == {'status': 'skipped', 'reason': 'Native positive control did not qualify',
                                        'failed_prerequisites': failed}, 'Skip requires recomputed failed native prerequisites')
            else:
                require(bool(result.get('error')) and summary == {'status': 'unexecuted',
                        'reason': 'Group stopped before this planned case', 'group_error': result['error']},
                        'Unexecuted case requires retained group-stop reason')
                stopped = True
            reports[case_id] = dict(summary, outcome='unknown_or_partial', strict_success=False, complete=False)
            gaps.append(case_id + ':' + status)
            continue
        require(not stopped and not failed, 'No execution after stop or before qualifying native prerequisites')
        require(not any((run / (case_id + '.' + label + '.json')).exists() for label in ('skipped', 'unexecuted')),
                'Executed case has no skip receipt')
        counts['executed'] += 1
        receipt = load(run / (case_id + '.json'))
        argv = receipt['argv']
        require(PurePosixPath(argv[0]).is_absolute() and argv[1:] == ['-B', linux_root + '/scripts/agentops_bridge_diagnostic_control_v1.py',
                '--case', case_id, '--runtime-root', seal['runtime_root'], '--seal', linux_root + '/' + SEAL]
                and receipt.get('cwd') == linux_root, 'Exact outer controller command')
        begin, end = interval(receipt)
        require(last_end <= begin <= end <= outer_end, 'Fixed nonoverlapping stage order')
        last_end = end
        require(verify_rows(run, receipt['streams']) == {case_id + '.' + suffix + '.bin' for suffix in ('stdout', 'stderr')},
                'Both outer controller streams')
        if (run / (case_id + '.started.json')).exists():
            started = load(run / (case_id + '.started.json'))
            require(all(receipt.get(key) == started.get(key) for key in ('argv', 'cwd', 'pid', 'started_at_utc')),
                    'Outer launch/terminal receipt binding')
        else:
            gaps.append(case_id + ':controller_start_unconfirmed')
        outcome = load(target / 'result.json') if (target / 'result.json').exists() else {}
        if outcome and not receipt.get('error') and receipt.get('timed_out') is False:
            require(type(receipt.get('returncode')) is int
                    and receipt['returncode'] == (0 if outcome.get('status') == 'recorded' else 1),
                    'Controller exit agrees with recorded case result')
        clean = case_bindings(exported, case_id, seal, linux_root, outcome, begin, end, gaps)
        semantic = check_case(target, seed)
        retained = target / 'case-check.json'
        if retained.exists():
            require(load(retained) == semantic, 'Retained whole-case report differs from independent recomputation')
        else:
            gaps.append(case_id + ':missing_retained_case_check')
        if (target / 'check.json').exists():
            require(load(target / 'check.json') == check_service(target / 'service', seed), 'Retained service report differs from recomputation')
        require(summary == {**{key: outcome.get(key) for key in
                ('status', 'service_strict_success', 'service_returncode', 'client_returncode')},
                'status': outcome.get('status', 'missing_result'),
                'strict_success': semantic['strict_success'] is True if retained.exists() else False}, 'Outer summary binds recomputed case')
        groups = receipt.get('owned_groups', {})
        group_clean = set(groups) == {'controller', 'client', 'service'}
        for label in ('controller', 'client', 'service'):
            pid = receipt.get('pid') if label == 'controller' else None
            name = 'client.started.json' if label == 'client' else 'service-process.json'
            if label != 'controller' and (target / name).exists():
                pid = load(target / name).get('pid')
            if not owned_group(groups.get(label, {}), pid):
                group_clean = False
        stopped = (not clean or not group_clean or receipt.get('timed_out') is not False or bool(receipt.get('error'))
                   or bool(receipt.get('cleanup_errors')) or outcome.get('client_timed_out') is not False
                   or outcome.get('client_forced_kill') is not False or outcome.get('forced_service_stop') is not False
                   or bool(outcome.get('cleanup_errors')) or outcome.get('service_returncode') != 0
                   or outcome.get('source_unchanged_after') is not True
                   or (definition['kind'] == 'bridge' and (outcome.get('bridge_clean_exit') is not True
                                                         or outcome.get('bridge_forced_kill') is not False)))
        diagnostic = validate_diagnostics(target, semantic)
        require(diagnostic.get('valid') is True, 'Malformed diagnostic evidence: ' + case_id)
        require(load(target / 'diagnostic-check.json') == diagnostic, 'Retained diagnostic check differs')
        if not diagnostic.get('complete'):
            stopped = True
            gaps.append(case_id + ':diagnostic_capture_incomplete')
        if stopped:
            gaps.append(case_id + ':group_cleanup_stop')
        if definition['kind'] == 'native' and retained.exists() and semantic['strict_success'] is True and not stopped:
            qualified.add(case_id)
        reports[case_id] = semantic
    require(result['status'] != 'matrix_attempts_recorded' or not stopped, 'Completed group cannot conceal cleanup stop')
    return reports, gaps, counts


def check(run, root=ROOT):
    seal, runtime = validate_preparation(root)
    result, execution, manifest = (load(run / name) for name in ('result.json', 'execution.json', 'export-manifest.json'))
    require(result.get('schema_version') == execution.get('schema_version') == 'agentops-bridge-diagnostic-group/11', 'Group schema')
    require(result.get('status') in ('matrix_attempts_recorded', 'failed', 'failed_runtime_integrity',
            'failed_export_references', 'failed_export', 'failed_parent_integrity'), 'Terminal group status')
    for receipt in (result, execution):
        scope(receipt, ('installations', 'live_model_calls', 'research_gate_credit_added'))
        require(receipt.get('qualified_second_domain') is False, 'No new domain qualification')
    require(execution.get('cases') == {} and execution.get('status') == 'failed'
            and execution['started_at_utc'] == result['started_at_utc'], 'Empty pre-execution receipt')
    linux_root = result['linux_workspace']
    require(linux_root == execution['linux_workspace'] == manifest['original_linux_root']
            == load(root / PRIOR / 'result.json')['linux_workspace'], 'Same retained Linux workspace')
    require(runtime['runtime_root'] == linux_root + '/external/runtime-agentops-bridges-v1'
            and execution['runtime_root'] == runtime['runtime_root'], 'Same pinned bridge runtime')
    seal_row = record(root / SEAL, root)
    expected = seal['reuse_inputs'] + seal['launch_inputs'] + [seal_row]
    require(execution['inputs'] == expected and execution['seal'] == seal_row, 'Exact execution inputs')
    require(result['runtime_before'] == execution['runtime_before'] == runtime['runtime_receipt'], 'Runtime before launch')
    require(timestamp(seal['prepared_at_utc']) <= timestamp(result['started_at_utc']), 'Prospective seal')
    exported = run / 'workspace'
    names = complete_export(exported, manifest, result, expected, load(root / PRIOR / 'export-manifest.json')['files'])
    reports, gaps, counts = check_stages(run, exported, result, seal,
        seed_snapshot(exported / 'external/agentops-c806b7f1/agents/data/incidents.db'))
    if result.get('runtime_after') != runtime['runtime_receipt']:
        require(bool(result.get('runtime_after_error')), 'Post-run runtime mismatch lacks error')
        gaps.append('runtime_after_not_verified')
    require(not [name for name, report in reports.items() if report.get('valid') is False], 'Invalid case evidence')
    diagnostics = {name: load(exported / (CASE_PREFIX + name) / 'diagnostic-check.json')
                   for name, report in reports.items() if report.get('status') not in ('skipped', 'unexecuted')}
    source_reports = {}
    for name in diagnostics:
        folder = exported / (CASE_PREFIX + name)
        source_path = folder / 'diagnostic-sources/result.json'
        if source_path.exists():
            source = load(source_path)
            require(source.get('schema_version') == 'agentops-diagnostic-source-capture/1'
                    and source.get('status') in ('captured', 'captured_with_gaps'), 'Source inspection receipt')
            expected_sources = verify_rows(exported, [row['snapshot'] for row in source['sources']])
            actual_sources = {path.relative_to(exported).as_posix() for path in source_path.parent.iterdir() if path.is_file()}
            require(actual_sources == expected_sources | {source_path.relative_to(exported).as_posix()}, 'Exact diagnostic source snapshots')
            require(source['copied_sources'] == len(source['sources'])
                    and source['copied_bytes'] == sum(row['snapshot']['bytes'] for row in source['sources']), 'Source copy accounting')
            source_reports[name] = {'copied_sources': source['copied_sources'],
                                    'recorded_frame_source_closure': source['recorded_frame_source_closure'],
                                    'closure_gaps': source['closure_gaps']}
        else:
            require((folder / 'diagnostic-source-unavailable.json').exists(), 'Missing source inspection reason')
            source_reports[name] = {'recorded_frame_source_closure': False,
                                    'reason': load(folder / 'diagnostic-source-unavailable.json')}
    return {'schema_version': 'agentops-bridge-diagnostic-group-check/1', 'valid': True,
            'status': 'artifact_integrity_and_semantics_verified', 'recorded_group_status': result['status'],
            'files_checked': len(names), 'all_planned_cases_accounted': True,
            'complete_matrix': counts['executed'] == len(design.CASES),
            'all_evidence_complete': not gaps and all(row.get('complete') is True for row in reports.values()),
            'counts': counts, 'observation_gaps': gaps, 'cases': reports, 'diagnostics': diagnostics,
            'source_inspection': source_reports,
            'fresh_experiment': False, 'qualified_second_domain': False, 'scientific_gate_credit_added': 0,
            'limitation': 'New diagnostic evidence only; v10 outcomes unchanged; no authenticity or novelty claim'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, default=ROOT / 'runs/agentops-native-eligibility/linux-bridge-diagnostic-v11')
    parser.add_argument('--prepared-only', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Preserve every diagnostic check')
    report = {'schema_version': 'agentops-bridge-diagnostic-group-check/1', 'status': 'failed', 'valid': False}
    try:
        if args.prepared_only:
            seal, runtime = validate_preparation()
            report.update(status='prospective_preparation_verified', valid=True, cases=len(seal['cases']),
                          runtime=runtime, fresh_experiment=False, qualified_second_domain=False,
                          scientific_gate_credit_added=0)
        else:
            report.update(check(args.run.resolve()))
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({key: value for key, value in report.items() if key not in ('cases', 'diagnostics')}, indent=2))
    raise SystemExit(0 if report['valid'] else 1)
