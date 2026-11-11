"""Fresh original ADK shopper and native AP2 services, accounted actual Gemini.

Preparation imports only owned standard-library helpers. This singleton is an
adaptive development observation, separate from all original 96-task study
slots and from the historical scripted-caller and offline-model allocations.
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
HELPER = ROOT / 'scripts/run_ap2_original_native_repeat_v3.py'
WORKER = ROOT / 'scripts/ap2_native_shopper_provider_worker_v1.py'
OWNED = ('scripts/run_ap2_native_shopper_provider_v1.py',
         'scripts/ap2_native_shopper_provider_worker_v1.py',
         'scripts/run_ap2_original_native_repeat_v3.py')


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


H = load(HELPER, '_original_native_shopper_provider_helpers')
W = load(WORKER, '_original_native_shopper_public_actor')


def fixed_plan_fields():
    return {'schema_version': 'ap2-native-shopper-provider-plan/1',
            'source_stage_sha256': H.STAGE_SHA, 'original_windows_environment_sha256': H.ENVIRONMENT_SHA,
            'model': H.MODEL, 'provider_origin': H.API_ORIGIN, 'provider_path': H.API_PATH,
            'limits': {'upstream_calls_including_smoke': H.MAX_CALLS,
                       'minimum_interval_seconds': H.MIN_INTERVAL,
                       'maximum_total_request_bytes': H.MAX_TOTAL_REQUEST_BYTES,
                       'maximum_observed_usage_tokens_before_stopping': H.MAX_TOTAL_USAGE_TOKENS,
                       'request_timeout_seconds': 45, 'worker_timeout_seconds': W.WORKER_SECONDS,
                       'screen_timeout_seconds': 900, 'maximum_public_user_turns': W.MAX_TURNS,
                       'maximum_ADK_events': W.MAX_EVENTS, 'maximum_event_bytes': W.MAX_EVENT_BYTES},
            'allocated_task_count': 1, 'public_human_facts': W.public_facts(),
            'adaptive_development_followup': True, 'held_out_study': False,
            'human_gold_qualified': False, 'original_run_sh_provisioning_qualified': False,
            'source_and_sdk_unchanged': True, 'original_ADK_root_and_subagents': True,
            'original_genai_Client_replaced': False, 'deterministic_BaseLlm_replacement': False,
            'original_tools_and_instructions_replaced': False, 'owned_public_user_actor': True,
            'public_actor_never_uses_session_state_or_tool_payloads': True,
            'linux_native_pid_listener_ownership_required': True,
            'byte_identical_original_source_copy_in_fresh_private_allocation': True,
            'original_source_log_destinations_unchanged_and_isolated': True,
            'owned_accounting_base_url_proxy': True, 'streaming_mode': 'NONE',
            'unknown_provider_usage_never_converted_to_zero': True,
            'whole_task_grade': None}


def prepare(output):
    if output.exists():
        raise ValueError('fresh_plan_directory_required')
    sources, versions, x402 = H.source_records(), H.expected_versions(), H.x402_source_records()
    output.mkdir(parents=True)
    owned = {}
    for name in OWNED:
        raw = (ROOT / name).read_bytes()
        owned[name] = H.digest(raw)
        target = output / 'owned-source' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    H.write(output / 'plan.json', {**fixed_plan_fields(), 'prepared_at': H.now(),
            'sources': sources, 'x402_sources': x402, 'versions': versions, 'owned_sources': owned})
    (output / 'requirements.txt').write_text(''.join(f'{name}=={version}\n' for name, version in sorted(versions.items())), encoding='utf-8')


def check_plan(plan_dir):
    plan = json.loads((plan_dir / 'plan.json').read_bytes())
    if any(json.dumps(plan.get(key), sort_keys=True) != json.dumps(value, sort_keys=True)
           for key, value in fixed_plan_fields().items()):
        raise ValueError('prospective_fixed_plan_or_public_facts_changed')
    if plan['sources'] != H.source_records() or plan['x402_sources'] != H.x402_source_records() or plan['versions'] != H.expected_versions():
        raise ValueError('prospective_original_source_or_versions_changed')
    if set(plan['owned_sources']) != set(OWNED):
        raise ValueError('prospective_owned_source_membership_changed')
    for name, expected in plan['owned_sources'].items():
        if H.digest((ROOT / name).read_bytes()) != expected or H.digest((plan_dir / 'owned-source' / name).read_bytes()) != expected:
            raise ValueError('prospective_owned_source_or_retained_snapshot_changed')
    return plan


def private_sources(work, plan):
    roots = {'ap2': work / 'original-ap2', 'x402': work / 'original-x402'}
    for name, original, records in (('ap2', H.SOURCE, plan['sources']),
            ('x402', H.STAGE.parent / 'a2a-x402', plan['x402_sources'])):
        roots[name].mkdir()
        for relative, expected in records.items():
            raw = (original / relative).read_bytes()
            if H.digest(raw) != expected:
                raise ValueError('original_source_changed_before_private_copy')
            target = roots[name] / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            if H.digest(target.read_bytes()) != expected:
                raise ValueError('private_original_source_copy_differs')
    return roots


def original_environment(work, site_packages, proxy_url, roots):
    environment = H.child_environment(work, site_packages, proxy_url)
    environment['PYTHONPATH'] = os.pathsep.join(map(str, (ROOT / 'src',
            roots['ap2'] / 'code/samples/python/src', roots['ap2'] / 'code/sdk/python',
            roots['x402'] / 'python/x402_a2a/src', site_packages)))
    return environment


def private_source_unchanged(roots, plan):
    return all(H.digest((roots[name] / relative).read_bytes()) == expected
            for name, records in (('ap2', plan['sources']), ('x402', plan['x402_sources']))
            for relative, expected in records.items())


def all_response_usage(provider_dir):
    """Raw-response accounting including failed and unclosed allocations.

    The immutable inherited summary's unknown counter covers HTTP 200 only.
    This additive census never treats missing/invalid failed-response usage as
    a measured zero and binds each parsed payload to its terminal ledger hash.
    """
    ledger_path = provider_dir / 'ledger.jsonl'
    entries = [json.loads(line) for line in ledger_path.read_bytes().splitlines()] if ledger_path.is_file() else []
    started = [row['allocation'] for row in entries if row.get('phase') == 'started']
    finished = [row for row in entries if row.get('phase') == 'finished']
    questions = []
    if len(started) != len(set(started)) or len(finished) != len({row['allocation'] for row in finished}):
        questions.append('duplicate_start_or_terminal_allocation')
    if {row['allocation'] for row in finished} - set(started):
        questions.append('terminal_without_opening_allocation')
    observations = []
    for row in finished:
        path = provider_dir / f"{row['allocation']:03d}.response.json"
        total, reason = None, 'missing_usage'
        try:
            raw = path.read_bytes()
            if H.digest(raw) != row['response']:
                questions.append('response_digest_mismatch:' + str(row['allocation']))
                reason = 'response_digest_mismatch'
            else:
                payload = json.loads(raw)
                usage = payload.get('usageMetadata') if type(payload) is dict else None
                candidate = usage.get('totalTokenCount') if type(usage) is dict else None
                if type(candidate) is int and candidate >= 0 and (candidate > 0 or row['http_status'] != 200):
                    total, reason = candidate, None
                elif candidate is not None:
                    reason = 'invalid_or_success_zero_usage'
        except (OSError, ValueError, TypeError):
            reason = 'unreadable_or_non_JSON_response'
        observations.append({'allocation': row['allocation'], 'http_status': row['http_status'],
                'known_reported_tokens': total, 'unknown_usage_reason': reason,
                'transport_or_parse_error_type': row.get('transport_error_type')})
    unclosed = sorted(set(started) - {row['allocation'] for row in finished})
    unknown = [row for row in observations if row['known_reported_tokens'] is None]
    return {'schema_version': 'ap2-provider-all-response-usage/1',
            'upstream_allocations': len(started), 'terminal_responses': len(finished),
            'known_reported_tokens': sum(row['known_reported_tokens'] for row in observations if row['known_reported_tokens'] is not None),
            'successful_responses_missing_or_invalid_usage': sum(row['http_status'] == 200 for row in unknown),
            'failed_responses_missing_or_invalid_usage': sum(row['http_status'] != 200 for row in unknown),
            'responses_missing_or_invalid_usage': len(unknown), 'unclosed_allocation_ids': unclosed,
            'allocations_with_unmeasured_usage': len(unknown) + len(unclosed),
            'fully_measured': not unknown and not unclosed and not questions,
            'unknown_usage_is_zero': False, 'observations': observations, 'consistency_questions': questions}


def accounted_summary(boundary):
    summary = boundary.summary()
    summary['observed_usage_tokens_meaning'] = 'Known reported partial sum; unknown successful/failed/transport outcomes are excluded, never measured zero.'
    summary['inherited_unknown_response_counter_scope'] = 'HTTP200 only; use all_response_usage for every allocated outcome.'
    summary['all_response_usage'] = all_response_usage(boundary.output)
    if summary['all_response_usage']['upstream_allocations'] != boundary.calls:
        summary['all_response_usage']['consistency_questions'].append('opening_ledger_and_boundary_allocation_count_differ')
        summary['all_response_usage']['fully_measured'] = False
    return summary


def execute(plan_dir, output, python, site_packages, pip_report, mode):
    if output.exists():
        raise ValueError('fresh_execution_directory_required')
    plan = check_plan(plan_dir)
    if sys.platform != 'linux' or mode != 'live':
        raise ValueError('explicit_live_mode_and_linux_PID_ownership_required')
    secret = os.environ.get('GOOGLE_API_KEY', '')
    if not secret or secret == H.SYNTHETIC_KEY:
        raise ValueError('real_provider_secret_missing')
    output.mkdir(parents=True)
    deadline = time.monotonic() + plan['limits']['screen_timeout_seconds']
    case = {'case_id': plan['public_human_facts']['case_id'], 'status': 'unexecuted',
            'reason': 'runtime_and_provider_smoke_not_passed'}
    H.write(output / 'opening.json', {'time': H.now(), 'plan': H.file_record(plan_dir / 'plan.json'),
            'allocated_task_count': 1, 'prospective_cases': [case.copy()],
            'actual_secret_persisted': False, 'original_ADK_and_native_service_route': True,
            'owned_public_user_actor_intervention': True})
    try:
        runtime_path, runtime_sha = H.portable_runtime(python, site_packages, pip_report, output, plan['versions'])
    except Exception as error:
        H.write(output / 'result.json', {'schema_version': 'ap2-native-shopper-provider-result/1',
                'completed_at': H.now(), 'cases': [case], 'allocated_task_count': 1, 'unexecuted_count': 1,
                'status': 'runtime_preflight_failed_before_provider_or_application_calls',
                'error': H.safe_exception(error, secret), 'provider': {'upstream_allocations': 0},
                'whole_task_grade': None, 'all_attempts_and_missing_tasks_retained': True})
        H.write(output / 'archive-safety.json', {'checked_files': H.archive_safety(output, secret),
                'provider_secret_or_private_key_found': False})
        return
    boundary = H.ProviderBoundary(output / 'provider', secret, mode=mode)
    server = thread = None
    failure = None
    try:
        smoke = H.smoke(boundary)
        H.write(output / 'provider-access-smoke.json', smoke)
        if not smoke['forced_tool_observed']:
            return
        server, thread = H.make_proxy(boundary)
        proxy_url = f'http://127.0.0.1:{server.server_port}'
        case_dir = output / 'cases' / case['case_id']
        case_dir.mkdir(parents=True, exist_ok=False)
        facts_path = case_dir / 'public-human-facts.json'
        H.write(facts_path, plan['public_human_facts'])
        case.update(status='started', reason=None, started_at=H.now())
        H.append(output / 'task-ledger.jsonl', case)
        processes, handles = [], []
        with tempfile.TemporaryDirectory(prefix='ap2-native-shopper-private-') as private:
            work = Path(private)
            for name in ('state', '.logs', 'tmp'):
                (work / name).mkdir()
            roots = private_sources(work, plan)
            try:
                H.require_free_ports(timeout=max(0, min(H.PORT_PREFLIGHT_WAIT_SECONDS, deadline - time.monotonic())),
                        record=lambda row: H.append(case_dir / 'native-port-preflight.jsonl', row))
                environment = original_environment(work, site_packages, proxy_url, roots)
                for name, module, port, route in H.SERVICE_ENTRIES:
                    handle = (case_dir / f'{name}.stdout.log').open('xb')
                    handles.append(handle)
                    command = [str(python), '-B', '-m', module]
                    processes.append(subprocess.Popen(command, cwd=work, env=environment, stdout=handle, stderr=subprocess.STDOUT))
                cards = H.wait_cards(processes, case_dir, timeout=max(0, min(45, deadline - time.monotonic())))
                H.write(case_dir / 'native-launch.json', {'entries': [{'module': module, 'port': port, 'rpc_path': route}
                        for _, module, port, route in H.SERVICE_ENTRIES], 'public_cards': cards,
                        'original_entrypoints': True, 'original_genai_Client_replaced': False,
                        'owned_accounting_base_url': proxy_url, 'real_secret_in_children': False,
                        'byte_identical_original_source_copy': True,
                        'original_source_copy_roots': {name: str(path) for name, path in roots.items()},
                        'exact_native_PID_listener_ownership_verified_before_card_requests': True})
                handle = (case_dir / 'shopper.stdout.log').open('xb')
                handles.append(handle)
                # Unlike the historical scripted caller, this worker needs the
                # synthetic proxy credential for the unchanged original ADK Gemini.
                command = [str(python), '-B', str(WORKER), '--public-human-facts', str(facts_path),
                           '--source-root', str(roots['ap2']), '--output', str(case_dir / 'shopper')]
                shopper = subprocess.Popen(command, cwd=work, env=environment, stdout=handle, stderr=subprocess.STDOUT)
                processes.append(shopper)
                try:
                    shopper.wait(timeout=max(0, min(W.WORKER_SECONDS + 15, deadline - time.monotonic())))
                except subprocess.TimeoutExpired:
                    case.update(status='executed_timeout_retained', reason='owned_parent_worker_deadline')
                else:
                    case.update(status='executed_returned' if shopper.returncode == 0 else 'executed_nonzero_retained',
                                shopper_returncode=shopper.returncode)
            except BaseException as error:
                case.update(status='executed_launch_or_readiness_failure_retained', reason=type(error).__name__,
                            error=H.safe_exception(error, secret))
            finally:
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
                case.update(finished_at=H.now(), original_private_state_retained=False,
                            private_original_source_bytes_unchanged=private_source_unchanged(roots, plan))
                H.append(output / 'task-ledger.jsonl', case)
    except BaseException as error:
        failure = H.safe_exception(error, secret)
    finally:
        boundary.stopped = True
        if server is not None:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        with boundary.lock:
            boundary.stopped = True
        unchanged = H.source_records() == plan['sources'] and H.x402_source_records() == plan['x402_sources']
        H.write(output / 'result.json', {'schema_version': 'ap2-native-shopper-provider-result/1',
                'completed_at': H.now(), 'cases': [case], 'allocated_task_count': 1,
                'unexecuted_count': int(case['status'] == 'unexecuted'), 'failure': failure,
                'provider': accounted_summary(boundary), 'portable_runtime_sha256': runtime_sha,
                'source_tree_unchanged_after_original_run': unchanged,
                'original_run_sh_provisioning_qualified': False, 'human_gold_qualified': False,
                'whole_task_grade': None, 'original_ADK_route_observed_requires_raw_validation': True,
                'all_attempts_and_missing_tasks_retained': True})
        H.write(output / 'archive-safety.json', {'checked_files': H.archive_safety(output, secret),
                'provider_secret_or_private_key_found': False})


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
    print(json.dumps({'mode': args.mode, 'provider_secret_printed': False, 'output': str(args.output)}))


if __name__ == '__main__':
    main()
