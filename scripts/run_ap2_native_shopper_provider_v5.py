"""Prospective V5 retains sanitized guard diagnostics and equivalent loopback forms.

No historical source, failed case, original SDK/client, model payload or public
actor grammar is replaced. Live execution requires root review and dispatch;
preparation and constructed controls import only owned standard-library code.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V1 = load('scripts/run_ap2_native_shopper_provider_v1.py', '_original_native_shopper_provider_v1_helpers')
B = load('scripts/ap2_native_shopper_provider_boundary_v2.py', '_original_native_shopper_provider_v5_boundary')
H = V1.H
WORKER = ROOT / 'scripts/ap2_native_shopper_provider_worker_v3.py'
W = load('scripts/ap2_native_shopper_provider_worker_v3.py', '_original_native_shopper_public_actor_v5')
CASE_ID = 'ap2-native-shopper-provider-v5-correct-human'
OWNED = (*V1.OWNED, 'scripts/ap2_native_shopper_provider_boundary_v2.py',
         'scripts/run_ap2_native_shopper_provider_v4.py', 'scripts/ap2_native_shopper_provider_worker_v2.py',
         'scripts/run_ap2_native_shopper_provider_v5.py', 'scripts/ap2_native_shopper_provider_worker_v3.py',
         'scripts/ap2_native_shopper_actor_guard_v5.py')


def fixed_plan_fields():
    value = V1.fixed_plan_fields()
    value.update(schema_version='ap2-native-shopper-provider-plan/5',
            prospective_successor_to_run=43074319113,
            inherited_v4_owned_network_denials_and_upstream_503_remain_retained=True,
            inherited_v4_rejected_socket_arguments_not_retained=True,
            prospective_loopback_representation_normalization_and_sanitized_diagnostics=True,
            inherited_v3_case_failed_before_ADK_import_and_shopper_model_calls=True,
            selected_worker_relative_path=WORKER.relative_to(ROOT).as_posix(),
            selected_worker_public_facts_preflight_before_provider_smoke=True,
            inherited_v2_case_unexecuted_before_provider_and_application_calls=True,
            original_venv_interpreter_symlink_preserved=True,
            inherited_case_remains_failed_and_usage_unknown=True,
            bounded_provider_handler_drain_before_proxy_shutdown=True,
            late_capture_after_drain_deadline_prevented=True,
            original_SDK_client_timeouts_unchanged=True)
    value['public_human_facts'] = dict(value['public_human_facts'], case_id=CASE_ID)
    value['limits'] = dict(value['limits'], request_timeout_seconds=B.REQUEST_TIMEOUT_SECONDS,
            maximum_provider_drain_seconds=B.MAXIMUM_DRAIN_SECONDS,
            request_timeout_is_independent_whole_request_wall_cap=False)
    value['actor_network_guard'] = {'classifier_schema': W.G.CLASSIFIER_SCHEMA,
            'separation_schema': W.G.SEPARATION_SCHEMA, 'denial_schema': W.G.DIAGNOSTIC_SCHEMA,
            'guard_relative_path': W.GUARD_PATH.relative_to(ROOT).as_posix(),
            'declared_native_ports': sorted(W.G.NATIVE_PORTS), 'provider_port': 'allocated_proxy_listener',
            'exact_loopback_names': sorted(W.G.LOOPBACK_NAMES),
            'ASCII_bytes_host_and_numeric_string_service_equivalents_allowed': True,
            'all_other_hosts_and_ports_denied': True,
            'maximum_diagnostic_records': W.G.MAX_DIAGNOSTICS,
            'maximum_diagnostic_bytes': W.G.MAX_DIAGNOSTIC_BYTES,
            'maximum_single_diagnostic_bytes': W.G.MAX_SINGLE_DIAGNOSTIC_BYTES,
            'external_names_unrestricted_args_socket_objects_and_payloads_not_retained': True}
    return value


def public_facts_preflight(plan):
    """Compare only owned public facts/source before provider or App execution."""
    facts, expected = plan.get('public_human_facts'), W.public_facts()
    if (not isinstance(facts, dict) or expected['case_id'] != CASE_ID
            or json.dumps(facts, sort_keys=True, allow_nan=False) != json.dumps(expected, sort_keys=True, allow_nan=False)):
        raise ValueError('selected_worker_public_human_facts_mismatch')
    if Path(W.__file__).resolve() != WORKER.resolve():
        raise ValueError('selected_worker_import_source_mismatch')
    return {'case_id': CASE_ID, 'selected_worker': WORKER.relative_to(ROOT).as_posix(),
            'selected_worker_source_identity': H.digest(WORKER.read_bytes()),
            'exact_public_field_agreement': True, 'before_provider_smoke': True,
            'original_application_or_SDK_imported_by_check': False}


def worker_command(python, facts_path, source_root, output):
    return [str(python), '-B', str(WORKER), '--public-human-facts', str(facts_path),
            '--source-root', str(source_root), '--output', str(output)]


def prepare(output):
    if output.exists():
        raise ValueError('fresh_plan_directory_required')
    fields = fixed_plan_fields()
    public_facts_preflight(fields)
    sources, versions, x402 = H.source_records(), H.expected_versions(), H.x402_source_records()
    output.mkdir(parents=True)
    owned = {}
    for name in OWNED:
        raw = (ROOT / name).read_bytes()
        owned[name] = H.digest(raw)
        target = output / 'owned-source' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    H.write(output / 'plan.json', {**fields, 'prepared_at': H.now(),
            'sources': sources, 'x402_sources': x402, 'versions': versions, 'owned_sources': owned})
    (output / 'requirements.txt').write_text(''.join(f'{name}=={version}\n' for name, version in sorted(versions.items())), encoding='utf-8')


def check_plan(plan_dir):
    plan = json.loads((plan_dir / 'plan.json').read_bytes())
    if any(json.dumps(plan.get(key), sort_keys=True) != json.dumps(value, sort_keys=True) for key, value in fixed_plan_fields().items()):
        raise ValueError('prospective_fixed_plan_or_public_facts_changed')
    if plan['sources'] != H.source_records() or plan['x402_sources'] != H.x402_source_records() or plan['versions'] != H.expected_versions():
        raise ValueError('prospective_original_source_or_versions_changed')
    if set(plan['owned_sources']) != set(OWNED):
        raise ValueError('prospective_owned_source_membership_changed')
    for name, expected in plan['owned_sources'].items():
        if H.digest((ROOT / name).read_bytes()) != expected or H.digest((plan_dir / 'owned-source' / name).read_bytes()) != expected:
            raise ValueError('prospective_owned_source_or_retained_snapshot_changed')
    public_facts_preflight(plan)
    return plan


def execute(plan_dir, output, python, site_packages, pip_report, mode):
    if output.exists():
        raise ValueError('fresh_execution_directory_required')
    plan = check_plan(plan_dir)
    public_preflight = public_facts_preflight(plan)
    if sys.platform != 'linux' or mode != 'live':
        raise ValueError('explicit_live_mode_and_linux_PID_ownership_required')
    secret = os.environ.get('GOOGLE_API_KEY', '')
    if not secret or secret == H.SYNTHETIC_KEY:
        raise ValueError('real_provider_secret_missing')
    output.mkdir(parents=True)
    H.write(output / 'worker-public-facts-preflight.json', public_preflight)
    deadline = time.monotonic() + plan['limits']['screen_timeout_seconds']
    case = {'case_id': CASE_ID, 'status': 'unexecuted', 'reason': 'runtime_and_provider_smoke_not_passed'}
    H.write(output / 'opening.json', {'time': H.now(), 'plan': H.file_record(plan_dir / 'plan.json'),
            'allocated_task_count': 1, 'prospective_cases': [case.copy()], 'actual_secret_persisted': False,
            'original_ADK_and_native_service_route': True, 'owned_public_user_actor_intervention': True})
    try:
        _, runtime_sha = H.portable_runtime(python, site_packages, pip_report, output, plan['versions'])
    except Exception as error:
        H.write(output / 'result.json', {'schema_version': 'ap2-native-shopper-provider-result/5',
                'completed_at': H.now(), 'cases': [case], 'allocated_task_count': 1, 'unexecuted_count': 1,
                'status': 'runtime_preflight_failed_before_provider_or_application_calls',
                'error': H.safe_exception(error, secret), 'provider': {'upstream_allocations': 0},
                'whole_task_grade': None, 'all_attempts_and_missing_tasks_retained': True})
        H.write(output / 'archive-safety.json', {'checked_files': H.archive_safety(output, secret), 'provider_secret_or_private_key_found': False})
        return
    boundary = B.ProviderBoundary(output / 'provider', secret, mode=mode)
    server = thread = None
    failure = None
    try:
        smoke = H.smoke(boundary)
        H.write(output / 'provider-access-smoke.json', smoke)
        if not smoke['forced_tool_observed']:
            return
        server, thread = H.make_proxy(boundary)
        proxy_url = f'http://127.0.0.1:{server.server_port}'
        case_dir = output / 'cases' / CASE_ID
        case_dir.mkdir(parents=True, exist_ok=False)
        facts_path = case_dir / 'public-human-facts.json'
        H.write(facts_path, plan['public_human_facts'])
        case.update(status='started', reason=None, started_at=H.now())
        H.append(output / 'task-ledger.jsonl', case)
        processes, handles = [], []
        with tempfile.TemporaryDirectory(prefix='ap2-native-shopper-v5-private-') as private:
            work = Path(private)
            for name in ('state', '.logs', 'tmp'):
                (work / name).mkdir()
            roots = V1.private_sources(work, plan)
            try:
                H.require_free_ports(timeout=max(0, min(H.PORT_PREFLIGHT_WAIT_SECONDS, deadline - time.monotonic())), record=lambda row: H.append(case_dir / 'native-port-preflight.jsonl', row))
                environment = V1.original_environment(work, site_packages, proxy_url, roots)
                for name, module, _, _ in H.SERVICE_ENTRIES:
                    handle = (case_dir / f'{name}.stdout.log').open('xb')
                    handles.append(handle)
                    processes.append(subprocess.Popen([str(python), '-B', '-m', module], cwd=work, env=environment, stdout=handle, stderr=subprocess.STDOUT))
                cards = H.wait_cards(processes, case_dir, timeout=max(0, min(45, deadline - time.monotonic())))
                H.write(case_dir / 'native-launch.json', {'entries': [{'module': module, 'port': port, 'rpc_path': route} for _, module, port, route in H.SERVICE_ENTRIES],
                        'public_cards': cards, 'original_entrypoints': True, 'original_genai_Client_replaced': False,
                        'owned_accounting_base_url': proxy_url, 'real_secret_in_children': False,
                        'byte_identical_original_source_copy': True, 'original_source_copy_roots': {name: str(path) for name, path in roots.items()},
                        'exact_native_PID_listener_ownership_verified_before_card_requests': True})
                handle = (case_dir / 'shopper.stdout.log').open('xb')
                handles.append(handle)
                command = worker_command(python, facts_path, roots['ap2'], case_dir / 'shopper')
                shopper = subprocess.Popen(command, cwd=work, env=environment, stdout=handle, stderr=subprocess.STDOUT)
                processes.append(shopper)
                try:
                    shopper.wait(timeout=max(0, min(W.WORKER_SECONDS + 15, deadline - time.monotonic())))
                except subprocess.TimeoutExpired:
                    case.update(status='executed_timeout_retained', reason='owned_parent_worker_deadline')
                else:
                    case.update(status='executed_returned' if shopper.returncode == 0 else 'executed_nonzero_retained', shopper_returncode=shopper.returncode)
            except BaseException as error:
                case.update(status='executed_launch_or_readiness_failure_retained', reason=type(error).__name__, error=H.safe_exception(error, secret))
            finally:
                boundary.begin_shutdown()
                case['process_cleanup'] = H.stop_processes(processes)
                for handle in handles:
                    handle.close()
                watch = work / '.logs/watch.log'
                if watch.is_file():
                    (case_dir / 'original-watch.log').write_bytes(boundary.redact(watch.read_bytes()))
                mandate_log = roots['ap2'] / 'code/sdk/.logs/mandate_operations.log'
                if mandate_log.is_file():
                    (case_dir / 'original-mandate-operations.jsonl').write_bytes(boundary.redact(mandate_log.read_bytes()))
                public_dir = case_dir / 'public-verification'
                public_dir.mkdir()
                for path in (work / 'state').glob('*.pub'):
                    (public_dir / path.name).write_bytes(path.read_bytes())
                case.update(finished_at=H.now(), original_private_state_retained=False, private_original_source_bytes_unchanged=V1.private_source_unchanged(roots, plan))
                H.append(output / 'task-ledger.jsonl', case)
    except BaseException as error:
        failure = H.safe_exception(error, secret)
    finally:
        drain = boundary.drain_and_freeze(max(0, min(B.MAXIMUM_DRAIN_SECONDS, deadline - time.monotonic())))
        summary = V1.accounted_summary(boundary)
        drain['unclosed_allocation_ids'] = summary['all_response_usage']['unclosed_allocation_ids']
        drain['allocations_with_unmeasured_usage'] = summary['all_response_usage']['allocations_with_unmeasured_usage']
        H.write(output / 'provider-drain.json', drain)
        if server is not None:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        unchanged = H.source_records() == plan['sources'] and H.x402_source_records() == plan['x402_sources']
        H.write(output / 'result.json', {'schema_version': 'ap2-native-shopper-provider-result/5', 'completed_at': H.now(),
                'cases': [case], 'allocated_task_count': 1, 'unexecuted_count': int(case['status'] == 'unexecuted'),
                'failure': failure, 'provider': summary, 'provider_drain': drain, 'portable_runtime_sha256': runtime_sha,
                'source_tree_unchanged_after_original_run': unchanged, 'original_run_sh_provisioning_qualified': False,
                'human_gold_qualified': False, 'whole_task_grade': None,
                'original_ADK_route_observed_requires_raw_validation': True, 'all_attempts_and_missing_tasks_retained': True})
        H.write(output / 'archive-safety.json', {'checked_files': H.archive_safety(output, secret), 'provider_secret_or_private_key_found': False})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'execute'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--python', type=Path)
    parser.add_argument('--site-packages', type=Path)
    parser.add_argument('--pip-report', type=Path)
    parser.add_argument('--provider-mode', choices=('live',))
    args = parser.parse_args()
    if args.mode == 'prepare':
        prepare(args.output.resolve())
    else:
        if any(value is None for value in (args.plan, args.python, args.site_packages, args.pip_report, args.provider_mode)):
            parser.error('execute requires plan/python/site-packages/pip-report/provider-mode')
        execute(args.plan.resolve(), args.output.resolve(), args.python.absolute(), args.site_packages.resolve(), args.pip_report.resolve(), args.provider_mode)


if __name__ == '__main__':
    main()
