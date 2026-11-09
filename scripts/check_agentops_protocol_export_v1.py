"""Recheck actual v9 export with local sealed validators; never execute exported code."""
import argparse
import json
from pathlib import Path

import agentops_protocol_preparation_v2 as preparation_contract
import check_agentops_socket_resume_v8 as prior
from check_agentops_linux_workspace_v5 import load, record, relative_file, require, verify_rows, zero
from check_agentops_protocol_v1 import check as check_protocol
from check_agentops_effect_v2 import seed_snapshot
from verify_agentops_protocol_preparation_v1 import verify_software_preparation

ROOT = Path(__file__).resolve().parents[1]
PRIOR = ROOT / 'runs/agentops-native-eligibility/linux-socket-resume-v8'
SEAL = ROOT / preparation_contract.SEAL_RELATIVE


def check(run):
    seal = load(SEAL)
    preparation_contract.validate_seal(ROOT, seal, load(PRIOR / 'result.json'))
    verify_software_preparation(ROOT)
    # This is a read-only recheck of the completed prerequisite, not its rerun.
    require(prior.check(PRIOR)['status'] == 'artifact_integrity_and_semantics_verified', 'v8 prerequisite recheck')
    result, execution, manifest = (load(run / name) for name in ('result.json', 'execution.json', 'export-manifest.json'))
    require(result['schema_version'] == execution['schema_version'] == 'agentops-linux-protocol/9', 'attempt schema')
    require(result['status'] == 'native_protocol_controls_passed', 'both native protocol controls must pass')
    require(result['linux_workspace'] == load(PRIOR / 'result.json')['linux_workspace'] == manifest['original_linux_root'], 'original Linux workspace')
    for key in ('installations', 'live_model_calls', 'research_gate_credit_added'):
        require(zero(result[key]), 'no ' + key)
    require(result['qualified_second_domain'] is False and result['parent_inputs_unchanged'] is True
            and result['export_reference_failures'] == manifest['reference_failures'] == [], 'preservation and scope')
    expected = load(PRIOR / 'execution.json')['inputs'] + seal['launch_inputs'] + [record(SEAL, ROOT)]
    require(execution['inputs'] == expected and execution['seal'] == record(SEAL, ROOT)
            and execution['prior_result'] == record(PRIOR / 'result.json', ROOT)
            and execution['prior_export'] == record(PRIOR / 'export-manifest.json', ROOT), 'attempt bound to sealed inputs')
    exported = run / 'workspace'
    names = verify_rows(exported, manifest['files'])
    verify_rows(exported, expected)
    verify_rows(exported, load(PRIOR / 'export-manifest.json')['files'])
    actual = set()
    for path in exported.rglob('*'):
        require(not path.is_symlink() and not getattr(path, 'is_junction', lambda: False)(), 'no export links')
        if path.is_file():
            actual.add(path.relative_to(exported).as_posix())
    require(names == actual and len(names) == result['exported_files'], 'complete export enumeration')
    require(manifest['bytes'] == sum(row['bytes'] for row in manifest['files']), 'export bytes')
    seed = seed_snapshot(exported / 'external/agentops-c806b7f1/agents/data/incidents.db')
    inventory = load(exported / prior.NATIVE / 'prepared-runtime.stdout.bin')
    source = load(exported / prior.NATIVE / 'plan.json')['source_files']
    linux_root = result['linux_workspace']
    reports = {}
    outer_times = prior.interval(result)
    last_end = outer_times[0]
    for case in ('sync', 'stream'):
        directory = f'runs/agentops-http-control/protocol-v1-{case}'
        target = exported / directory
        outcome, plan = load(target / 'result.json'), load(target / 'plan.json')
        stage = load(run / f'{case}.json')
        require(stage['argv'][1:] == ['-B', '-X', 'utf8', 'scripts/agentops_protocol_control_v1.py', case]
                and stage['cwd'] == linux_root and stage['timed_out'] is False and zero(stage['returncode']), 'controller argv/exit')
        begin, end = prior.interval(stage)
        require(last_end <= begin <= end <= outer_times[1], 'ordered stages')
        last_end = end
        for stream in stage['streams']:
            require(record(relative_file(run, stream['path']), run) == stream, 'controller captured streams')
        require({r['path'] for r in stage['streams']} == {f'{case}.stdout.bin', f'{case}.stderr.bin'}, 'both controller streams')
        require(outcome['schema_version'] == 'agentops-protocol-result/1' and outcome['status'] == 'protocol_and_effect_checks_passed'
                and outcome['case'] == case and outcome['source_unchanged_after'] is True and zero(outcome['live_model_calls'])
                and outcome['forced_service_stop'] is False and zero(outcome['service_returncode'])
                and not outcome.get('cleanup_errors'), 'successful clean case')
        require(result['cases'][case] == {'returncode': 0, 'status': outcome['status']}, 'outer case binding')
        verify_rows(exported, outcome['files'], [directory + '/' + name for name in ('plan.json', 'check.json',
                    'service-process.json', 'service-result.json', 'execution-runtime.stdout.bin', 'boundaries.json')])
        require(plan['source_files'] == source and plan['launch_seal'] == record(SEAL, ROOT)
                and plan['service'] == record(exported / 'scripts/serve_agentops_http_v2.py', exported)
                and plan['native_prerequisite'] == record(exported / prior.NATIVE / 'result.json', exported), 'original fixture/native bindings')
        require(load(target / 'execution-runtime.stdout.bin') == inventory, 'same installed runtime')
        prior.capture_receipt(exported, directory, 'execution-runtime',
            [prior.linux_path(linux_root, prior.RUNTIME), '-I', prior.linux_path(linux_root, prior.INSPECTOR)], linux_root)
        prior.verify_boundary_sources(exported, inventory, plan['runtime_sources'])
        module_prefix = 'external/runtime-agentops-linux-v7/venv/lib/python3.13/site-packages/'
        require(plan['runtime_sources'] == [{'path': module_prefix + r['module'], 'bytes': r['bytes'], 'sha256': r['sha256']}
                                           for r in seal['runtime_sources']], 'all pinned protocol modules')
        process = load(target / 'service-process.json')
        require(process['argv'] == [prior.linux_path(linux_root, prior.RUNTIME), '-B',
            prior.linux_path(linux_root, 'scripts/serve_agentops_http_v2.py'), '--output', prior.linux_path(linux_root, directory),
            '--port', str(plan['port'])], 'original service command')
        require(type(process['pid']) is int and process['pid'] > 0, 'service process identity')
        service = load(target / 'service-result.json')
        require(service['socket_policy']['capability_source']['installed_path'] == prior.linux_path(linux_root,
            module_prefix + 'urllib3/util/connection.py'), 'socket probe provider path')
        semantic = check_protocol(target, seed)
        require(load(target / 'check.json') == semantic, 'recorded checker equals recomputation')
        reports[case] = semantic
    require(set(result['cases']) == {'sync', 'stream'}, 'exact case set')
    return {'schema_version': 'agentops-protocol-export-check/1', 'status': 'artifact_integrity_and_semantics_verified',
        'files_checked': len(names), 'cases': reports, 'fresh_experiment': False,
        'qualified_second_domain': False, 'scientific_gate_credit_added': 0,
        'limitation': 'Retained evidence consistency, not capture authenticity, full runtime authentication or scientific review'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, default=ROOT / 'runs/agentops-native-eligibility/linux-protocol-v9')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Preserve prior checks')
    report = {'schema_version': 'agentops-protocol-export-check/1', 'status': 'failed'}
    try:
        report.update(check(args.run.resolve()))
    except Exception as error:
        report['error'] = f'{type(error).__name__}: {error}'
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['status'] == 'artifact_integrity_and_semantics_verified' else 1)
