"""Read-only AP2 v4 application and pre-dispatch shared-admission verification."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import shutil
import sys

STAGE_SHA = '78828cea09bdd387230a2fc0772b542beabfe07b72c3a2f24b24c02c1a2f4463'
EXTENSION = 'https://github.com/google-agentic-commerce/ap2/v1'


def need(condition, label):
    if not condition:
        raise ValueError(label)


def digest(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def read_json(path):
    def pairs(values):
        result = {}
        for key, value in values:
            need(key not in result, 'duplicate_json_key')
            result[key] = value
        return result
    def invalid(_):
        raise ValueError('nonfinite_json')
    return json.loads(Path(path).read_bytes(), object_pairs_hook=pairs, parse_constant=invalid)


def receipts(task):
    return [part['data']['ap2.PaymentReceipt'] for artifact in task.get('artifacts') or []
            for part in artifact['parts'] if part.get('kind') == 'data'
            and 'ap2.PaymentReceipt' in part.get('data', {})]


def message_parts(message):
    return [{'kind': part['kind'], part['kind']: part[part['kind']]}
            for part in message['parts']]


def assess_admission(application, journal_raw, durable, reference, caller):
    package_path = application / 'owned-source/src/interoperability'
    name = '_retained_ap2_v4_admission_package'
    spec = importlib.util.spec_from_file_location(name, package_path / '__init__.py',
                                                submodule_search_locations=[str(package_path)])
    package = importlib.util.module_from_spec(spec)
    sys.modules[name] = package
    spec.loader.exec_module(package)
    admission = importlib.import_module(name + '.ap2_pending_admission_v4')
    base = application / 'admission'
    prepared = read_json(base / 'pending-input.json')
    profile = read_json(base / 'profile.json')
    result = read_json(base / 'solver-result.json')
    receipt = read_json(base / 'admission-before-send.json')
    dispatch = read_json(base / 'raw-dispatch.json')
    observed = read_json(base / 'observed-continuation.json')
    boundary = read_json(base / 'boundary-result.json')
    need(profile == prepared['profile'] and result == receipt['solver_result'],
         'retained_admission_profile_or_solver_result_mismatch')
    need(receipt['dispatch_permitted'] is True and receipt['certificate_valid'] is True
         and receipt['decision'] == result['decision'] == 'supported'
         and receipt['input_sha256'] == admission.digest(prepared)
         and receipt['profile_sha256'] == admission.refinement.digest(profile),
         'admission_identity_or_positive_decision_mismatch')
    need(profile['model']['evidence']['complete'] is False and profile['coverage']['complete'] is False
         and receipt['actual_task_completion_established_by_certificate'] is False
         and receipt['whole_route_non_support_inference_allowed'] is False
         and prepared['assumptions'] == receipt['assumptions'] == admission.ASSUMPTIONS,
         'admission_claim_limit_or_coverage_changed')
    pending = prepared['pending_task']
    response = admission.demo_response(admission.public_challenge(pending))
    rebuilt = admission.prepare_profile(pending, caller, prepared['original_request']['message'],
                                         response, receipt['evaluation_clock'])
    need(rebuilt == prepared, 'pending_profile_does_not_rebuild_from_actual_caller_values')
    admission.verify_supported(profile, result, prepared['original_request'], receipt['evaluation_clock'])
    pending_records = [row for row in reference['public_records'] if row['boundary'] == 'returned'
                       and row['endpoint'] == admission.MERCHANT and row.get('public_value') == pending]
    need(len(pending_records) == 1, 'admission_pending_task_not_the_actual_public_observation')
    before = receipt['journal_checkpoint_before_admission']
    checkpoint, exchanges = admission.decode_journal(journal_raw[:before['bytes']], durable)
    need(checkpoint == before and admission.bind_pending_raw(pending, exchanges) == receipt['pending_raw_binding'],
         'pre_admission_journal_or_raw_pending_binding_mismatch')
    expected_files = {'pending-input.json', 'profile.json', 'solver-result.json', 'admission-before-send.json'}
    need(set(dispatch['admission_artifacts']) == expected_files, 'admission_artifact_union_mismatch')
    for filename, expected in dispatch['admission_artifacts'].items():
        need(digest((base / filename).read_bytes()) == expected, 'pre_dispatch_admission_artifact_changed')
    rebound = admission.verify_observed(prepared, receipt, dispatch, journal_raw, durable, reference['public_records'])
    need(rebound == observed and rebound['actual_original_task_completed'] is True
         and boundary['admission_attempted'] is True and boundary['original_continuation_dispatched'] is True
         and boundary['checked_witness_bound_to_observed_original_completion'] is True,
         'checked_admission_not_bound_to_actual_original_completion')
    return {'decision': result['decision'], 'independent_certificate_valid': True,
            'profile_sha256': receipt['profile_sha256'], 'certificate_kind': result['certificate']['kind'],
            'evaluation_clock': receipt['evaluation_clock'], 'raw_dispatch_clock': dispatch['checked_at'],
            'valid_until': receipt['valid_until'], 'same_actual_original_builder_and_raw_request': True,
            'admission_preceded_original_raw_continuation': True,
            'original_merchant_task_id': observed['original_merchant_task_id'],
            'original_context_id': observed['original_context_id'],
            'raw_continuation_exchange': observed['raw_continuation_exchange'],
            'raw_continuation_first_global_index': observed['raw_continuation_first_global_index'],
            'journal_prefix_before_admission': before,
            'projected_completion_was_separately_observed': True,
            'coverage_complete': False, 'whole_route_non_support_inference_allowed': False}


def assess(application):
    plan = read_json(application / 'plan.json')
    reference = read_json(application / 'reference-result.json')
    state = reference['planning_report']['caller_state']
    caller = read_json(application / 'caller-final-state.json')
    cleanup = read_json(application / 'cleanup.json')
    runner_hash = digest((application / 'source-runner.py').read_bytes())
    need(runner_hash == plan['owned_components']['scripts/ap2_reference_development_v4.py'], 'runner_snapshot_mismatch')
    for name, expected in plan['owned_components'].items():
        need(digest((application / 'owned-source' / name).read_bytes()) == expected, 'owned_source_snapshot_mismatch')
    stage_raw = (application / 'source-stage-manifest.json').read_bytes()
    need(digest(stage_raw)['sha256'] == STAGE_SHA, 'source_stage_snapshot_mismatch')
    stage = json.loads(stage_raw)
    sources = {row['path']: {'bytes': row['bytes'], 'sha256': row['sha256']}
               for row in stage['files'] if row['project'] == 'ap2'}
    actual_sources = {path.relative_to(application / 'original-source').as_posix(): digest(path.read_bytes())
                      for path in (application / 'original-source').rglob('*') if path.is_file()}
    need(len(sources) == 136 and actual_sources == sources, 'original_source_union_mismatch')

    helper_path = application / 'owned-source/src/interoperability/ap2_hp_durable_observer_v1.py'
    spec = importlib.util.spec_from_file_location('_retained_ap2_semantic_decoder', helper_path)
    durable = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = durable
    spec.loader.exec_module(durable)
    terminal = read_json(application / 'observations/terminal.json')
    journal_raw = (application / 'observations/events.jsonl').read_bytes()
    need(digest(journal_raw) == terminal['journal'], 'durable_journal_identity_mismatch')
    events = [json.loads(line) for line in journal_raw.splitlines()]
    need(terminal['capture_complete_for_declared_intervals'] is True
         and terminal['missing_global_indices'] == []
         and len(events) == terminal['durably_committed_events'] == terminal['attempted_events'], 'durable_capture_incomplete')
    next_sequence = {}
    exchanges = {}
    for index, event in enumerate(events):
        need(event['global_index'] == index, 'global_event_sequence_gap')
        stream = event['stream']
        row = durable.decode_value(event['payload'])
        expected = next_sequence.get(stream, 0)
        need(event['source_index'] == row['sequence'] == expected, 'source_event_sequence_gap')
        next_sequence[stream] = expected + 1
        if stream.endswith('_raw'):
            exchange = exchanges.setdefault((stream, row['exchange']), {'request_body': b'', 'response_body': b''})
            if row['boundary'] == 'scope':
                exchange['scope'] = row['value']
            elif row['boundary'] == 'receive_returned' and row['value'].get('type') == 'http.request':
                exchange['request_body'] += row['value'].get('body', b'')
            elif row['boundary'] == 'send_completed' and row['value'].get('type') == 'http.response.body':
                exchange['response_body'] += row['value'].get('body', b'')
            elif row['boundary'] == 'application_returned':
                exchange['closed'] = True
    for stream, value in terminal['streams'].items():
        need(value['final_witness']['source_complete'] is True
             and value['final_witness']['active_operations'] == 0
             and value['next_source_index'] == next_sequence.get(stream, 0), 'unclosed_source_witness')

    requests = []
    for (stream, number), exchange in exchanges.items():
        need(exchange.get('closed') is True, 'unclosed_raw_exchange')
        if exchange['scope']['method'] != 'POST':
            continue
        request, response = json.loads(exchange['request_body']), json.loads(exchange['response_body'])
        need(request['jsonrpc'] == response['jsonrpc'] == '2.0'
             and request['id'] == response['id'] and 'result' in response, 'rpc_correlation_mismatch')
        headers = dict(exchange['scope']['headers'])
        need(EXTENSION.encode() in headers.get(b'x-a2a-extensions', b'').split(b', '), 'rpc_extension_missing')
        requests.append({'stream': stream, 'exchange': number, 'request': request, 'response': response})
    messages = {}
    for row in requests:
        identity = row['request']['params']['message']['messageId']
        need(identity not in messages, 'reused_public_message_id')
        messages[identity] = row
    public_by_call = {(row['endpoint'], row['call']): row for row in reference['public_records']
                      if row['boundary'] == 'returned'}
    for row in reference['public_records']:
        if row['boundary'] != 'attempt' or row['operation'] != 'send_a2a_message':
            continue
        message = row['public_value']
        raw = messages[message['messageId']]
        raw_message = raw['request']['params']['message']
        need(message.get('taskId') == raw_message.get('taskId')
             and message.get('contextId') == raw_message.get('contextId')
             and message_parts(message) == message_parts(raw_message), 'caller_message_raw_mismatch')
        returned = public_by_call[(row['endpoint'], row['call'])]['public_value']
        task = raw['response']['result']
        need(returned['id'] == task['id'] and returned['contextId'] == task['contextId']
             and returned['status']['state'] == task['status']['state'], 'caller_result_raw_mismatch')

    final = state['supplied_merchant_after']
    starts = [row['public_value'] for row in reference['public_records'] if row['boundary'] == 'returned'
              and row['endpoint'].endswith('/merchant_agent') and row['public_value'].get('status', {}).get('state') == 'input-required']
    need(len(starts) == 1, 'one_public_merchant_challenge_required')
    start = starts[0]
    need(reference['phase'] == 'finished' and reference['error_type'] is None
         and start['id'] == final['id'] == state['initiate_payment_task_id']
         and start['contextId'] == final['contextId'] == state['shopping_context_id']
         and final['status']['state'] == 'completed' and state['supplied_continuation_target_observed'] is True, 'merchant_continuation_not_completed')
    processor_id = start['status']['message']['taskId']
    processor_rows = [row for row in requests if row['stream'] == 'processor_raw']
    need(len(processor_rows) == 2, 'original_processor_start_resume_required')
    first, later = processor_rows
    need(first['response']['result']['id'] == processor_id == later['response']['result']['id']
         and later['request']['params']['message']['taskId'] == processor_id
         and later['response']['result']['status']['state'] == 'completed', 'processor_task_continuation_mismatch')
    actual_receipts = receipts(final)
    need(len(actual_receipts) == 1, 'unique_original_receipt_required')
    receipt = actual_receipts[0]
    need(receipt == caller['payment_receipt'] == receipts(later['response']['result'])[0]
         and receipt['status'] == 'Success', 'original_receipt_correspondence_mismatch')
    delivery = [row for row in requests if row['stream'] == 'credentials_raw'
                and any('ap2.PaymentReceipt' in part.get('data', {}) for part in row['request']['params']['message']['parts'])]
    need(len(delivery) == 1 and delivery[0]['response']['result']['status']['state'] == 'completed'
         and [part['data']['ap2.PaymentReceipt'] for part in delivery[0]['request']['params']['message']['parts']
              if 'ap2.PaymentReceipt' in part.get('data', {})] == [receipt], 'credentials_receipt_delivery_mismatch')
    leaf = state['payment_mandate_sdjwt'].rsplit('~~', 1)[-1].split('~', 1)[0]
    expected_reference = base64.urlsafe_b64encode(hashlib.sha256(leaf.encode()).digest()).decode().rstrip('=')
    need(receipt['reference'] == expected_reference, 'receipt_closed_mandate_reference_mismatch')
    need(cleanup['clients_closed'] is True and cleanup['caller_aliases_restored'] is True
         and cleanup['public_observer_serializer_unchanged'] is True
         and cleanup['source_tree_unchanged'] is True and cleanup['runtime_tree_unchanged'] is True
         and all(value['active_operations'] == 0 and value['source_complete'] is True for value in cleanup['raw'].values()), 'application_cleanup_incomplete')
    admission = assess_admission(application, journal_raw, durable, reference, caller)
    return {'status': 'offline_original_application_and_checked_admission_verified', 'source_runner': runner_hash,
            'shared_lift_admission': admission,
            'original_source_files_checked': 136, 'durable_events_checked': len(events),
            'raw_exchanges_checked': len(exchanges), 'rpc_requests_checked': len(requests),
            'merchant_task_id': final['id'], 'processor_task_id': processor_id,
            'shopping_context_id': final['contextId'], 'receipt': receipt,
            'receipt_reference_freshly_recomputed': True, 'same_original_merchant_and_processor_tasks_resumed': True,
            'original_receipt_matches_processor_merchant_caller_and_credentials_delivery': True,
            'cleanup_verified': True, 'provider_requests': 0, 'native_qualification_established': False,
            'scope': 'offline model/ASGI/owned-helper development integration only; caller/raw correlation is not native peer authentication'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--application', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, args.output / 'source-analyzer.py')
    try:
        result = assess(args.application.resolve())
        code = 0
    except BaseException as error:
        result = {'status': 'semantic_analysis_refused', 'error_type': type(error).__name__, 'reason': str(error)[:1000],
                  'native_qualification_established': False}
        code = 2
    result['created_utc'] = datetime.now(timezone.utc).isoformat()
    (args.output / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'output': str(args.output)}))
    return code


if __name__ == '__main__':
    sys.exit(main())
