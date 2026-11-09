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

import agentops_bridge_plan_v1 as design
import prepare_agentops_bridge_v1 as preparation
from agentops_bridge_runtime_archive_v1 import check_graph, safe_name
from check_agentops_bridge_v1 import check_case, check_service
from check_agentops_effect_v2 import seed_snapshot
from check_agentops_linux_workspace_v5 import load, record, relative_file, require, verify_rows, zero
from check_agentops_socket_resume_v8 import interval

ROOT = Path(__file__).resolve().parents[1]
PRIOR = 'runs/agentops-native-eligibility/linux-protocol-v9'
SEAL = preparation.PACKAGE + '/manifest.json'
CASE_PREFIX = 'runs/agentops-http-control/bridge-v1-'


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(parsed.tzinfo is not None, 'Timezone-aware timestamp required')
    return parsed


def scope(value, fields):
    require(all(zero(value.get(key)) for key in fields), 'Resource/claim scope differs')


def verify_archive(directory):
    """Check every archived runtime byte and all copied preparation bindings."""
    graph = load(directory / 'graph.json')
    nodes = check_graph(graph)
    raw_graph = (directory / 'graph.json').read_bytes()
    graph_hash = hashlib.sha256(raw_graph).hexdigest()
    archive = load(directory / 'archive.json')
    materialization = load(directory / 'materialization.json')
    verified = load(directory / 'runtime-verification.json')
    byte_report = load(directory / 'runtime-bytes-verification.json')
    archive_record = record(directory / 'runtime.zip', directory)
    require(archive.get('schema_version') == 'agentops-bridge-runtime-archive/1'
            and archive.get('status') == 'archive_verified'
            and archive.get('archive') == 'runtime.zip'
            and archive.get('archive_sha256') == archive_record['sha256']
            and archive.get('bytes') == archive_record['bytes']
            and archive.get('package_count') == len(nodes)
            and archive.get('files') == len(graph['files']), 'Prepared runtime archive binding')
    expected = {row['path']: row for row in graph['files']}
    with zipfile.ZipFile(directory / 'runtime.zip') as bundle:
        infos = bundle.infolist()
        require(len(infos) == len(expected) + 1
                and {row.filename for row in infos} == set(expected) | {'graph.json'},
                'Exact unique runtime archive entries')
        require(len({row.filename.casefold() for row in infos}) == len(infos), 'Colliding runtime archive entries')
        for entry in infos:
            safe_name(entry.filename)
            require(not entry.is_dir() and not entry.flag_bits & 1
                    and (entry.external_attr >> 16) & 0o170000 in (0, 0o100000),
                    'Only unencrypted regular runtime entries')
            size = len(raw_graph) if entry.filename == 'graph.json' else expected[entry.filename]['bytes']
            require(type(size) is int and entry.file_size == size, 'Bounded runtime entry size')
            raw = bundle.read(entry)
            require(raw == raw_graph if entry.filename == 'graph.json' else
                    hashlib.sha256(raw).hexdigest() == expected[entry.filename]['sha256'],
                    'Runtime archive entry bytes differ: ' + entry.filename)
    runtime_root = materialization.get('runtime_root')
    require(PurePosixPath(runtime_root).is_absolute() and '..' not in PurePosixPath(runtime_root).parts,
            'Absolute prepared Linux runtime')
    require(materialization.get('schema_version') == 'agentops-bridge-runtime-materialization/1'
            and materialization.get('status') == 'materialized_import_check_pending'
            and materialization.get('files') == len(expected)
            and materialization.get('packages') == len(nodes)
            and materialization.get('bytes') == graph['total_bytes'], 'Runtime materialization receipt')
    links = {nodes[row['from']]['destination'] + '/node_modules/' + row['name']:
             nodes[row['to']]['destination'] for row in graph['edges']}
    links.update({'external/' + row['alias']: nodes[row['node']]['destination'] for row in graph['roots']})
    require(len(materialization['links']) == len(links)
            and {row['path']: row['resolved'] for row in materialization['links']} == links,
            'Runtime links match exact dependency graph')
    require(all(row['target'] == posixpath.relpath(row['resolved'], posixpath.dirname(row['path']))
                for row in materialization['links']), 'Literal runtime link targets')
    for receipt in (archive, materialization, verified):
        scope(receipt, ('application_requests', 'live_model_calls', 'installations'))
        require(receipt.get('graph_sha256') == graph_hash
                and receipt.get('archive_sha256') == archive_record['sha256'], 'Runtime graph/archive hashes')
    expected_report = {'status': 'runtime_bytes_and_links_verified', 'files': len(expected),
                       'packages': len(nodes), 'links': len(links), 'graph_sha256': graph_hash}
    require(byte_report == expected_report, 'Runtime byte verification receipt')
    require(verified.get('schema_version') == 'agentops-bridge-runtime-verification/1'
            and verified.get('status') == 'runtime_files_resolution_and_imports_verified'
            and verified.get('runtime_root') == runtime_root and verified.get('files') == len(expected)
            and verified.get('packages') == len(nodes) and verified.get('resolved_edges') == len(graph['edges'])
            and verified.get('absent_optional_dependencies') == len(graph['missing_optional']),
            'Passive runtime verification receipt')
    bridges = {name: {'package_root': runtime_root + '/external/' + name,
                      'cli': runtime_root + '/external/' + name + '/dist/cli.js',
                      'entry': runtime_root + '/external/' + name + '/dist/index.js'}
               for name in ('a2a-to-mcp', 'mcp-a2a')}
    require(verified.get('bridges') == materialization.get('bridges') == bridges, 'Bridge alias bindings')
    require(verified['node']['path'] == '/usr/bin/node' and verified['node']['platform'] == 'linux'
            and set(verified.get('exports', {})) == set(bridges), 'Prepared passive Node/import evidence')
    require(interval(archive)[1] <= interval(materialization)[0]
            <= interval(materialization)[1] <= timestamp(verified['checked_at_utc']), 'Runtime preparation order')
    return {'runtime_root': runtime_root, 'node': verified['node'], 'runtime_receipt': expected_report}


def validate_preparation(root=ROOT):
    """Validate the current externally retained prospective seal before launch."""
    seal = load(root / SEAL)
    require(seal.get('schema_version') == 'agentops-bridge-preparation/1'
            and seal.get('cases') == list(design.CASES.values()), 'Exact prospectively ordered cases')
    scope(seal, ('application_requests', 'live_model_calls', 'research_gate_credit_added'))
    require([row['path'] for row in seal['launch_inputs']] == preparation.LAUNCH_FILES,
            'Exact prospective launch input inventory')
    verify_rows(root, seal['launch_inputs'])
    verify_rows(root, seal['prerequisites'])
    runtime_dir = root / preparation.PACKAGE / 'runtime'
    runtime_seal = load(runtime_dir / 'preparation-seal.json')
    require(runtime_seal.get('schema_version') == 'agentops-bridge-runtime-preparation-seal/1', 'Runtime preparation seal')
    scope(runtime_seal, ('application_requests', 'live_model_calls', 'installations'))
    verify_rows(root, runtime_seal['files'])
    require((runtime_dir / 'preparation-seal.json').read_bytes() ==
            (root / preparation.RUNTIME_PREP / 'preparation-seal.json').read_bytes(), 'Original runtime seal copy')
    frozen_runtime = {row['path']: row for row in runtime_seal['files']}
    for name in preparation.RUNTIME_FILES:
        if name == 'preparation-seal.json':
            continue
        original = preparation.RUNTIME_PREP + '/' + name
        require(original in frozen_runtime, 'Runtime evidence omitted from preparation seal')
        require(record(runtime_dir / name, runtime_dir) == dict(frozen_runtime[original], path=name),
                'Copied runtime evidence differs from original seal')
    runtime = verify_archive(runtime_dir)
    require(seal['runtime_root'] == runtime['runtime_root'] == runtime_seal['runtime_root']
            and seal['node'] == runtime['node'], 'Prospective runtime/node bindings')
    software = load(root / preparation.SOFTWARE / 'result.json')
    require(software.get('schema_version') == 'agentops-bridge-software-preparation/1'
            and software.get('status') == 'passed' and software.get('inputs_unchanged') is True,
            'Passing final software preparation')
    scope(software, ('application_requests', 'live_model_calls'))
    require(software['inputs'] == [record(root / name, root) for name in preparation.SOFTWARE_FILES],
            'Exact tested software input bytes')
    commands = software['commands']
    require([row['label'] for row in commands] == ['python-bridge', 'python-observer', 'node'], 'Exact software test stages')
    python = commands[0]['argv'][0]
    require(PurePosixPath(python).is_absolute(), 'Recorded Linux test interpreter')
    expected_commands = [
        [python, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_agentops_bridge*.py', '-v'],
        [python, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_agentops_asgi_capture_v1.py', '-v'],
        ['/usr/bin/node', '--test', *[name for name in preparation.TEST_FILES if name.endswith('.mjs')]],
    ]
    last_end = timestamp(runtime_seal['prepared_at_utc'])
    for row, argv in zip(commands, expected_commands):
        require(row['argv'] == argv and zero(row.get('returncode')) and not row.get('timed_out'),
                'Successful exact software test command')
        begin, end = interval(row)
        require(last_end <= begin <= end <= timestamp(seal['prepared_at_utc']), 'Tests precede prospective seal')
        last_end = end
        names = verify_rows(root, row['streams'])
        require(names == {preparation.SOFTWARE + '/' + row['label'] + '.' + suffix + '.bin'
                          for suffix in ('stdout', 'stderr')}, 'Both software test streams')
    prerequisites = preparation.TEST_FILES + ['scripts/prepare_agentops_bridge_v1.py', preparation.SOFTWARE + '/result.json',
        PRIOR + '/result.json', PRIOR + '/export-manifest.json', PRIOR + '/execution.json',
        'runs/agentops-native-eligibility/protocol-parent-check-v9.json']
    prerequisites += [stream['path'] for row in commands for stream in row['streams']]
    require([row['path'] for row in seal['prerequisites']] == prerequisites, 'Exact prerequisite inventory')
    require(load(root / 'runs/agentops-native-eligibility/protocol-parent-check-v9.json')['status'] ==
            'artifact_integrity_and_semantics_verified', 'Retained prior native check')
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
            and plan['service_source'] == record(exported / 'scripts/serve_agentops_bridge_v1.py', exported), 'Case sealed harness binding')
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
        later = {directory + '/' + name for name in ('result.json', 'case-check.json', 'case-check-error.json')}
        require(case_names == actual - later and all(name.startswith(directory + '/') for name in case_names),
                'Complete case inventory before terminal result/check')
    else:
        gaps.append(case_id + ':missing_result')
    clean = True
    process_rows = {}
    for label, filename, script in (
            ('client', 'client-process.json', 'agentops_native_profile_client_v1.mjs' if definition['kind'] == 'native' else 'agentops_bridge_client_v1.mjs'),
            ('service', 'service-process.json', 'serve_agentops_bridge_v1.py')):
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
        require(all(path.name.removeprefix('bridge-v1-') in design.CASES for path in case_parent.iterdir()
                    if path.name.startswith('bridge-v1-')), 'Unplanned bridge case footprint')
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
        require(PurePosixPath(argv[0]).is_absolute() and argv[1:] == ['-B', linux_root + '/scripts/agentops_bridge_control_v1.py',
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
        if stopped:
            gaps.append(case_id + ':group_cleanup_stop')
        if definition['kind'] == 'native' and retained.exists() and semantic['strict_success'] is True and not stopped:
            qualified.add(case_id)
        reports[case_id] = semantic
    require(result['status'] != 'matrix_attempts_recorded' or not stopped, 'Completed group cannot conceal cleanup stop')
    return reports, gaps, counts


def check(run, root=ROOT):
    seal, runtime = validate_preparation(root)
    # Read-only prerequisite recheck; this never reruns completed v8/v9 controls.
    from check_agentops_protocol_export_v1 import check as check_prior
    require(check_prior(root / PRIOR)['status'] == 'artifact_integrity_and_semantics_verified', 'Prior native evidence recheck')
    result, execution, manifest = (load(run / name) for name in ('result.json', 'execution.json', 'export-manifest.json'))
    require(result.get('schema_version') == execution.get('schema_version') == 'agentops-bridge-group/1', 'Group schema')
    require(result.get('status') in ('matrix_attempts_recorded', 'failed', 'failed_runtime_integrity',
            'failed_export_references', 'failed_export', 'failed_parent_integrity'), 'Recorded group terminal status')
    for receipt in (result, execution):
        scope(receipt, ('installations', 'live_model_calls', 'research_gate_credit_added'))
        require(receipt.get('qualified_second_domain') is False, 'No second-domain qualification claim')
    require(execution.get('cases') == {} and execution.get('status') == 'failed'
            and execution['started_at_utc'] == result['started_at_utc'], 'Prospective empty execution receipt')
    linux_root = result['linux_workspace']
    require(linux_root == execution['linux_workspace'] == manifest['original_linux_root']
            == load(root / PRIOR / 'result.json')['linux_workspace'], 'Original Linux replica binding')
    require(runtime['runtime_root'] == linux_root + '/external/runtime-agentops-bridges-v1'
            and execution['runtime_root'] == runtime['runtime_root'], 'Prepared runtime location')
    seal_row = record(root / SEAL, root)
    expected = load(root / PRIOR / 'execution.json')['inputs'] + seal['launch_inputs'] + [seal_row]
    require(execution['inputs'] == expected and execution['seal'] == seal_row, 'Execution bound to exact prospective inputs')
    require(result['runtime_before'] == execution['runtime_before'] == runtime['runtime_receipt'], 'Runtime verified before launch')
    exported = run / 'workspace'
    names = complete_export(exported, manifest, result, expected, load(root / PRIOR / 'export-manifest.json')['files'])
    reports, gaps, counts = check_stages(run, exported, result, seal,
        seed_snapshot(exported / 'external/agentops-c806b7f1/agents/data/incidents.db'))
    if result.get('runtime_after') != runtime['runtime_receipt']:
        require(bool(result.get('runtime_after_error')), 'Runtime postcheck mismatch lacks retained error')
        gaps.append('runtime_after_not_verified')
    invalid = [case_id for case_id, report in reports.items() if report.get('valid') is False]
    require(not invalid, 'Retained case validation errors: ' + ','.join(invalid))
    return {'schema_version': 'agentops-bridge-group-check/1', 'status': 'artifact_integrity_and_semantics_verified',
        'valid': True, 'recorded_group_status': result['status'], 'files_checked': len(names),
        'all_planned_cases_accounted': True, 'complete_matrix': counts['executed'] == len(design.CASES),
        'all_evidence_complete': not gaps and all(report.get('complete') is True for report in reports.values()),
        'counts': counts, 'observation_gaps': gaps, 'cases': reports, 'fresh_experiment': False,
        'qualified_second_domain': False, 'scientific_gate_credit_added': 0,
        'limitation': 'Retained evidence consistency; no capture authenticity, novelty, full-interface or second-domain claim'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, default=ROOT / 'runs/agentops-native-eligibility/linux-bridge-v10')
    parser.add_argument('--prepared-only', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Preserve every prior parent check')
    report = {'schema_version': 'agentops-bridge-group-check/1', 'status': 'failed', 'valid': False}
    try:
        if args.prepared_only:
            seal, runtime = validate_preparation()
            report.update(status='prospective_preparation_verified', valid=True, cases=len(seal['cases']),
                          runtime=runtime, fresh_experiment=False, qualified_second_domain=False, scientific_gate_credit_added=0)
        else:
            report.update(check(args.run.resolve()))
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['valid'] else 1)
