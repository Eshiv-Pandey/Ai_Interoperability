"""Offline native/provider shopper reconstruction from root-retained evidence.

Standard library only. Recorded public/SDK/provider observations are distinct
from semantic gold, original wire capture, hidden effects and settlement.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import zipfile

EXPECTED_RUN = 43038234376
EXPECTED_HEAD = 'f8bc3028fd936490bef80de89efe57e4e4fcf6eb'
CASE_ID = 'ap2-native-shopper-provider-v1-correct-human'
MODEL = 'gemini-3.1-flash-lite-preview'
STAGES = ('root_agent', 'shopper', 'shipping_address_collector', 'payment_method_collector')
BUSINESS_TOOLS = {
    'root_agent': ('create_checkout', 'create_checkout_mandate', 'create_payment_mandate',
                   'send_signed_mandates_to_credentials_provider', 'initiate_payment', 'initiate_payment_with_otp'),
    'shopper': ('find_products', 'select_cart'),
    'shipping_address_collector': ('get_shipping_address',),
    'payment_method_collector': ('get_payment_methods', 'get_payment_credential_token'),
}


def digest(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def file_hash(path):
    hasher = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(262144):
            hasher.update(block)
    return hasher.hexdigest()


class Retained:
    def __init__(self, base, run_id=EXPECTED_RUN, head=EXPECTED_HEAD):
        self.base, self.reads = base, {}
        self.receipt = json.loads((base / 'retention.json').read_bytes())
        self.run = json.loads((base / 'github-run.json').read_bytes())
        receipt = self.receipt
        if receipt['run_id'] != run_id or receipt['head_sha'] != head or self.run['id'] != run_id or self.run['head_sha'] != head:
            raise ValueError('retained_run_or_head_binding_differs')
        archive = base / 'artifact.zip'
        if archive.stat().st_size != receipt['archive_bytes'] or file_hash(archive) != receipt['archive_sha256']:
            raise ValueError('retained_archive_identity_differs')
        if receipt.get('api_digest') != 'sha256:' + receipt['archive_sha256'] or self.run.get('status') != 'completed':
            raise ValueError('complete_API_digest_binding_required')
        manifest = json.loads((base / 'extracted-manifest.json').read_bytes())['files']
        self.manifest = {row['path']: {k: row[k] for k in ('bytes', 'sha256')} for row in manifest}
        if len(self.manifest) != len(manifest) or len(manifest) != receipt['extracted_files']:
            raise ValueError('retained_member_denominator_differs')
        self.root = base / 'extracted'
        for name in self.manifest:
            path = (self.root / name).resolve()
            if not path.is_relative_to(self.root.resolve()) or path.is_symlink() or not path.is_file():
                raise ValueError('unsafe_or_absent_retained_member')
        with zipfile.ZipFile(archive) as zipped:
            members = [row for row in zipped.infolist() if not row.is_dir()]
            if len(members) != len({row.filename for row in members}) or {row.filename for row in members} != set(self.manifest):
                raise ValueError('archive_and_extracted_manifest_membership_differs')
            for member in members:
                if digest(zipped.read(member)) != self.manifest[member.filename]:
                    raise ValueError('archive_and_extracted_manifest_digest_differs:' + member.filename)

    def raw(self, name, *, optional=False):
        if name not in self.manifest:
            if optional:
                return None
            raise ValueError('required_retained_member_absent:' + name)
        raw = (self.root / name).read_bytes()
        if digest(raw) != self.manifest[name]:
            raise ValueError('retained_member_digest_differs:' + name)
        self.reads[name] = digest(raw)
        return raw

    def json(self, name, *, optional=False):
        raw = self.raw(name, optional=optional)
        return json.loads(raw) if raw is not None else None

    def rows(self, name):
        raw = self.raw(name, optional=True)
        return [json.loads(line) for line in raw.splitlines() if line.strip()] if raw else []


def parts(event):
    return (event.get('content') or {}).get('parts', [])


def function(part, kind):
    return part.get(kind) or part.get({'function_call': 'functionCall', 'function_response': 'functionResponse'}[kind])


def visible_text(event):
    if event.get('author') == 'user' or (event.get('content') or {}).get('role') != 'model':
        return ''
    if any(function(part, 'function_call') or function(part, 'function_response') for part in parts(event)):
        return ''
    actions = event.get('actions') or {}
    forced_final = actions.get('skipSummarization', actions.get('skip_summarization')) or event.get('longRunningToolIds', event.get('long_running_tool_ids'))
    if event.get('partial') and not forced_final:
        return ''
    if not forced_final and parts(event) and any(parts(event)[-1].get(key) is not None for key in ('codeExecutionResult', 'code_execution_result')):
        return ''
    return '\n'.join(part['text'] for part in parts(event) if part.get('text') and not part.get('thought'))


def tool_key(row):
    return row['turn'], row['author'], row.get('id'), row['name']


def unwrap(value):
    if isinstance(value, dict) and set(value) == {'result'}:
        return unwrap(value['result'])
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def displayed_price(text, budget, first_option):
    """Independently reconstruct the frozen narrow public price grammar.

    This never imports the actor or reads private/session facts. A successful
    check concerns only the visible USD amount, not a merchant's actual charge.
    """
    candidate = text
    if first_option:
        rows = list(re.finditer(r'(?m)^\s*(?:\*\*)?(\d+)[.)]\s+', text))
        if (not rows or text[:rows[0].start()].strip()
                or [int(row[1]) for row in rows] != list(range(1, len(rows) + 1))
                or re.search(r'(?m)^\s*(?:[-*]\s+|\(\d+\)\s+)', text)):
            return None
        candidate = text[rows[0].start():rows[1].start() if len(rows) > 1 else len(text)]
    if re.search(r'\b(?:EUR|GBP|CAD|AUD|NZD|INR|JPY|CNY|CHF|HKD|SGD|MXN)\b|[\u20ac\u00a3\u00a5\u20b9]', candidate, re.I):
        return None
    if any(row[1].upper() not in {'US', 'USD'} for row in re.finditer(r'(?<![A-Za-z])([A-Za-z]{1,4})\$', candidate)):
        return None
    if re.search(r'\b(?:C|A|CA|AU|NZ|HK|SG|NT|CN)\s+\$', candidate):
        return None
    if any(row[1].casefold() not in {'us', 'american', 'states'} for row in re.finditer(r'\b([A-Za-z]+)\s+dollars?\b', candidate, re.I)):
        return None
    if re.search(r'\d(?:\s*[-\u2013\u2014]\s*|\s+(?:to|through|up to)\s*)(?:USD\s*|US\$\s*|\$\s*)?\d', candidate, re.I):
        return None
    token = r'[-+]?\d+(?:,\d+)*(?:\.\d+)?(?:[eE][-+]?\d+)?'
    valid = r'(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?'
    amounts = re.findall(r'(?<![A-Za-z])(?:USD\s*|US\s*\$\s*|\$\s*)(' + token + r')(?![A-Za-z0-9]|[.,]\d)|(?<![A-Za-z0-9.,])(' + token + r')\s+USD\b', candidate, re.I)
    tokens = [left or right for left, right in amounts]
    if not tokens or any(not re.fullmatch(valid, value) for value in tokens):
        return None
    values = [Decimal(value.replace(',', '')) for value in tokens]
    if any(value > Decimal(str(budget)) for value in values):
        return None
    if first_option:
        return values[0] if len(set(values)) == 1 else None
    label = r'(?:grand total|order total|total amount|total due|amount due)'
    lines = [line for line in candidate.splitlines() if re.search(r'\b' + label + r'\b', line, re.I)]
    if len(lines) != 1:
        return None
    line = re.sub(r'\*\*', '', lines[0]).strip()
    total = re.fullmatch(r'(?:[-*]\s*)?' + label + r'\s*[:=]?\s*(?:USD\s*(' + token + r')|US\$\s*(' + token + r')|(' + token + r')\s+USD)\s*[.!]?', line, re.I)
    if not total:
        return None
    value = next(value for value in total.groups() if value is not None)
    return Decimal(value.replace(',', '')) if re.fullmatch(valid, value) else None


def first_displayed_cart_id(text):
    rows = list(re.finditer(r'(?m)^\s*(?:\*\*)?(\d+)[.)]\s+', text))
    if not rows or int(rows[0][1]) != 1:
        return None
    block = text[rows[0].start():rows[1].start() if len(rows) > 1 else len(text)]
    plain = block.replace('**', '').replace('`', '')
    ids = re.findall(r'\bcart[ _]+id\b\s*[:=]?\s*([A-Za-z0-9][A-Za-z0-9_.:-]*)', plain, re.I)
    return ids[0].rstrip('.:') if len(ids) == 1 else None


def catalog_analysis(events, delivered, snapshots):
    """Corroborate visible selection using raw original SDK returns, not gold."""
    catalogs, selections, visible = [], [], []
    for index, row in enumerate(events):
        event = row['event']
        text = visible_text(event)
        if text:
            visible.append({'event_order': index, 'turn': row['turn'], 'text': text})
        for part in parts(event):
            call, response = function(part, 'function_call'), function(part, 'function_response')
            if call and call['name'] == 'select_cart':
                selections.append({'event_order': index, 'turn': row['turn'], 'author': event.get('author'), **call})
            if response and response['name'] == 'find_products':
                value = unwrap(response.get('response'))
                if isinstance(value, list):
                    catalogs.append({'event_order': index, 'turn': row['turn'], 'carts': value})
    records = []
    for reply in delivered:
        if reply['category'] != 'cart-selection':
            continue
        prompt = reply['visible_prompt']
        prompts = [row for row in visible if row['turn'] == reply['decision_turn'] and row['text'] == prompt]
        prompt_order = prompts[-1]['event_order'] if prompts else None
        preceding = [row for row in catalogs if prompt_order is not None and row['event_order'] < prompt_order]
        catalog = preceding[-1] if preceding else None
        displayed_id = first_displayed_cart_id(prompt)
        carts = [cart for cart in catalog['carts'] if isinstance(cart, dict) and cart.get('cart_id') == displayed_id] if catalog and displayed_id else []
        cart = carts[0] if len(carts) == 1 else None
        calls = [row for row in selections if row['turn'] >= reply['delivered_turn']]
        call = calls[0] if calls else None
        state_ids = [{'snapshot': name, 'chosen_cart_id': (snapshot.get('state') or {}).get('chosen_cart_id')}
                     for name, snapshot in snapshots if (snapshot.get('state') or {}).get('chosen_cart_id') is not None]
        response_values = []
        if call:
            for row in events[call['event_order'] + 1:]:
                for part in parts(row['event']):
                    response = function(part, 'function_response')
                    if response and response.get('id') == call.get('id') and response.get('name') == 'select_cart':
                        response_values.append(unwrap(response.get('response')))
        price_equal = None
        if cart:
            try:
                price_equal = (cart.get('currency') == 'USD' and Decimal(str(cart['amount']))
                               == Decimal(reply['visible_price_check']['visible_amount']))
            except (InvalidOperation, KeyError, TypeError):
                price_equal = False
        records.append({'decision_turn': reply['decision_turn'], 'delivered_turn': reply['delivered_turn'],
                        'first_displayed_cart_id': displayed_id, 'preceding_original_catalog_event_order': catalog['event_order'] if catalog else None,
                        'preceding_original_catalog_cart_count': len(catalog['carts']) if catalog else None,
                        'matching_original_cart': cart, 'unique_displayed_ID_in_preceding_original_catalog': cart is not None,
                        'visible_amount_and_original_cart_currency_amount_match': price_equal,
                        'actual_select_cart_call': call, 'select_cart_argument_matches_first_displayed_ID': bool(call and displayed_id and (call.get('args') or {}).get('cart_id') == displayed_id),
                        'original_select_cart_return_values': response_values,
                        'original_selection_success_text_matches_displayed_ID': bool(displayed_id and f'Cart {displayed_id} selected.' in response_values),
                        'chosen_cart_state_records': state_ids,
                        'chosen_cart_state_matches_displayed_ID': bool(state_ids and displayed_id and all(row['chosen_cart_id'] == displayed_id for row in state_ids)),
                        'displayed_order_assumed_to_equal_catalog_order': False,
                        'whole_task_grade': None})
    return {'delivered_cart_selections': len(records), 'records': records,
            'evidence_scope': 'Visible first ordinal selection joined to preceding raw original ADK tool return, later original select_cart and retained session state; full A2A wire and semantic human gold are absent.'}


def public_analysis(events, conversation, decisions, snapshots, facts):
    questions, behavior = [], []
    calls, responses, actual_visible, pending_tools = [], [], [], Counter()
    for row in events:
        event = row['event']
        for part in parts(event):
            if fn := function(part, 'function_call'):
                call = {'turn': row['turn'], 'author': event.get('author'), **fn}
                calls.append(call)
                pending_tools[tool_key(call)] += 1
            if fn := function(part, 'function_response'):
                response = {'turn': row['turn'], 'author': event.get('author'), **fn}
                responses.append(response)
                key = tool_key(response)
                if not pending_tools[key]:
                    questions.append('raw_ADK_function_response_precedes_or_lacks_call')
                else:
                    pending_tools[key] -= 1
        text = visible_text(event)
        if text:
            actual_visible.append({'turn': row['turn'], 'author': event.get('author'), 'text': text})
    recorded_visible = [{key: row.get(key) for key in ('turn', 'author', 'text')} for row in conversation if row['role'] == 'model']
    if actual_visible != recorded_visible:
        questions.append('visible_conversation_and_raw_ADK_final_text_differ')
    if Counter(tool_key(row) for row in calls) != Counter(tool_key(row) for row in responses):
        questions.append('raw_ADK_function_call_response_census_differs')
    if any(not row.get('id') for row in calls):
        questions.append('raw_ADK_function_call_identity_missing')
    if len(calls) != len({(row['author'], row.get('id')) for row in calls}):
        questions.append('raw_ADK_function_call_identity_reused')
    for row in calls:
        if row['author'] not in BUSINESS_TOOLS or row['name'] not in (*BUSINESS_TOOLS.get(row['author'], ()), 'transfer_to_agent'):
            behavior.append({'kind': 'outside_declared_original_tool_surface', 'call': row})
    users = {row['turn']: row['text'] for row in conversation if row['role'] == 'user'}
    if users and users.get(0) != facts['initial_request']:
        questions.append('first_public_user_request_differs_from_frozen_fact')
    proposed, delivered = [], []
    for decision in decisions:
        visible = [row['text'] for row in recorded_visible if row['turn'] == decision['turn']]
        prompt = visible[-1] if visible else ''
        if hashlib.sha256(prompt.encode()).hexdigest() != decision['visible_prompt_sha256']:
            questions.append('actor_prompt_hash_not_bound_to_last_visible_text')
        if decision.get('session_or_tool_state_used') is not False:
            questions.append('public_actor_state_separation_record_not_false')
        reply = decision.get('reply')
        if reply is None:
            continue
        item = {'decision_turn': decision['turn'], 'category': reply['category'], 'text': reply['text'],
                'visible_prompt': prompt, 'visible_price_check': reply.get('visible_price_check')}
        proposed.append(item)
        if users.get(decision['turn'] + 1) == reply['text']:
            delivered.append(dict(item, delivered_turn=decision['turn'] + 1))
        elif decision['turn'] + 1 in users:
            questions.append('recorded_actor_reply_differs_from_next_public_user_turn')
        asks_otp = (('?' in prompt or re.search(r'\b(?:please enter|please provide|provide the|enter the)\b', prompt, re.I))
                    and re.search(r'\b(?:otp|one[- ]time (?:password|code)|verification code)\b', prompt, re.I)
                    and re.search(r'\b(?:provide|enter|send|what)\b|code\?', prompt, re.I))
        if reply['category'] == 'otp' and (facts['otp_response'] != reply['text'] or not asks_otp):
            behavior.append({'kind': 'OTP_reply_without_exact_frozen_fact_or_visible_request', 'decision_turn': decision['turn']})
        if reply['category'] in {'cart-selection', 'checkout-confirmation'}:
            price = reply.get('visible_price_check') or {}
            try:
                reconstructed = displayed_price(prompt, facts['maximum_budget_USD'], reply['category'] == 'cart-selection')
                valid = (price.get('currency') == 'USD' and reconstructed is not None
                         and Decimal(price['visible_amount']) == reconstructed
                         and price.get('maximum_budget_USD') == facts['maximum_budget_USD']
                         and price.get('exchange_rate_or_hidden_state_used') is False)
            except (InvalidOperation, KeyError, TypeError):
                valid = False
            if not valid:
                behavior.append({'kind': 'actor_price_record_not_independently_bound_to_visible_USD_amount', 'decision_turn': decision['turn']})
    def prior(category, turn):
        return any(row['category'] == category and row['delivered_turn'] <= turn for row in delivered)
    for call in calls:
        required = {'get_shipping_address': 'wallet-consent', 'select_cart': 'cart-selection',
                    'get_payment_credential_token': 'payment-selection',
                    'create_checkout_mandate': 'checkout-confirmation', 'create_payment_mandate': 'checkout-confirmation',
                    'initiate_payment_with_otp': 'otp'}.get(call['name'])
        if required and not prior(required, call['turn']):
            behavior.append({'kind': 'original_tool_request_before_required_public_reply', 'required_reply': required, 'call': call})
        if call['name'] == 'initiate_payment_with_otp' and (call.get('args') or {}).get('challenge_response') != facts['otp_response']:
            behavior.append({'kind': 'original_OTP_tool_argument_differs_from_delivered_fact', 'call': call})
    known_business = [row for row in calls if row['name'] != 'transfer_to_agent']
    milestones = {name: {'requested': sum(row['name'] == name for row in calls),
                         'returned': sum(row['name'] == name for row in responses)}
                  for tools in BUSINESS_TOOLS.values() for name in tools}
    receipt_rows = []
    state_identity = set()
    for path, snapshot in snapshots:
        state_identity.add(snapshot.get('id'))
        receipt = unwrap((snapshot.get('state') or {}).get('payment_receipt'))
        if receipt is not None:
            receipt_rows.append({'snapshot': path, 'receipt': receipt})
    if len(state_identity) > 1:
        questions.append('recorded_session_identity_changes_between_snapshots')
    receipts = []
    for row in receipt_rows:
        receipt = row['receipt']
        if isinstance(receipt, dict) and isinstance(receipt.get('root'), dict):
            receipt = receipt['root']
        required = ('iss', 'reference', 'payment_id', 'psp_confirmation_id', 'network_confirmation_id')
        shape = isinstance(receipt, dict) and receipt.get('status') == 'Success' and type(receipt.get('iat')) is int and all(isinstance(receipt.get(key), str) for key in required)
        receipts.append({'snapshot': row['snapshot'], 'receipt': receipt, 'sample_success_receipt_shape': bool(shape),
                         'signature_or_settlement_proven': False})
    catalog = catalog_analysis(events, delivered, snapshots)
    errors = [{'turn': row['turn'], 'author': row['event'].get('author'),
               'error_message': row['event'].get('errorMessage', row['event'].get('error_message')),
               'error_code': row['event'].get('errorCode', row['event'].get('error_code')),
               'metadata': row['event'].get('customMetadata', row['event'].get('custom_metadata'))}
              for row in events if any(row['event'].get(key) is not None for key in ('errorMessage', 'error_message', 'errorCode', 'error_code'))]
    return {'consistency_questions': list(dict.fromkeys(questions)), 'behavior_observations': behavior,
            'raw_ADK_events': len(events), 'official_authors': sorted({row['event'].get('author', '') for row in events}),
            'raw_ADK_error_events': errors,
            'function_calls': calls, 'function_responses': responses, 'business_call_count': len(known_business),
            'function_call_IDs_present': all(row.get('id') for row in calls) if calls else None,
            'visible_model_messages': recorded_visible, 'public_user_messages': len(users),
            'actor_proposed_replies': proposed, 'actor_delivered_replies': delivered,
            'cart_selection_corroboration': catalog,
            'milestones': milestones, 'unrequested_later_business_tools': [name for name, value in milestones.items() if not value['requested']],
            'retained_receipts': receipts, 'unique_success_receipt_records': len({json.dumps(row['receipt'], sort_keys=True) for row in receipts if row['sample_success_receipt_shape']}),
            'session_snapshot_ids': sorted(value for value in state_identity if value is not None),
            'whole_task_grade': None, 'human_gold': False}


def provider_analysis(read, result):
    root = 'execution/provider/'
    ledger = read.rows(root + 'ledger.jsonl')
    starts = [row for row in ledger if row.get('phase') == 'started']
    closes = [row for row in ledger if row.get('phase') == 'finished']
    questions, observations = [], []
    if len(starts) != len({row['allocation'] for row in starts}) or len(closes) != len({row['allocation'] for row in closes}):
        questions.append('duplicate_provider_allocation_identity')
    if {row['allocation'] for row in closes} - {row['allocation'] for row in starts}:
        questions.append('provider_terminal_without_opening_allocation')
    for row in starts:
        raw = read.raw(root + f"{row['allocation']:03d}.request.json")
        if digest(raw) != row['request']:
            questions.append('provider_request_ledger_digest_differs')
    for row in closes:
        raw = read.raw(root + f"{row['allocation']:03d}.response.json", optional=True)
        total, version = None, None
        if raw is not None and digest(raw) == row['response']:
            try:
                payload = json.loads(raw)
                usage = payload.get('usageMetadata') if isinstance(payload, dict) else None
                candidate = usage.get('totalTokenCount') if isinstance(usage, dict) else None
                version = payload.get('modelVersion') if isinstance(payload, dict) else None
                if type(candidate) is int and candidate >= 0 and (candidate > 0 or row['http_status'] != 200):
                    total = candidate
            except ValueError:
                pass
        elif raw is not None:
            questions.append('provider_response_ledger_digest_differs')
        observations.append({'allocation': row['allocation'], 'http_status': row['http_status'],
                             'known_reported_tokens': total, 'model_version': version,
                             'transport_or_parse_error_type': row.get('transport_error_type')})
    unclosed = sorted({row['allocation'] for row in starts} - {row['allocation'] for row in closes})
    unknown = [row for row in observations if row['known_reported_tokens'] is None]
    measured = {'upstream_allocations': len(starts), 'terminal_responses': len(closes),
                'known_reported_tokens': sum(row['known_reported_tokens'] for row in observations if row['known_reported_tokens'] is not None),
                'successful_responses_missing_or_invalid_usage': sum(row['http_status'] == 200 for row in unknown),
                'failed_responses_missing_or_invalid_usage': sum(row['http_status'] != 200 for row in unknown),
                'responses_missing_or_invalid_usage': len(unknown), 'unclosed_allocation_ids': unclosed,
                'allocations_with_unmeasured_usage': len(unknown) + len(unclosed),
                'fully_measured': not unknown and not unclosed and not questions}
    recorded = (result.get('provider') or {}).get('all_response_usage')
    if recorded is not None and any(recorded.get(key) != value for key, value in measured.items()):
        questions.append('all_response_usage_result_differs_from_retained_responses')
    if result.get('provider', {}).get('upstream_allocations') != len(starts):
        questions.append('closing_provider_allocation_count_differs')
    times = [datetime.fromisoformat(row['time']) for row in starts]
    gaps = [(later - earlier).total_seconds() for earlier, later in zip(times, times[1:])]
    opening = {row['allocation']: row for row in starts}
    durations = [{'allocation': row['allocation'], 'seconds': (datetime.fromisoformat(row['time']) - datetime.fromisoformat(opening[row['allocation']]['time'])).total_seconds()}
                 for row in closes if row['allocation'] in opening and row.get('time')]
    return {**measured, 'responses': observations, 'HTTP_status_census': dict(Counter(str(row['http_status']) for row in closes)),
            'local_proxy_refusals': read.rows(root + 'local-refusals.jsonl'),
            'recorded_allocation_to_terminal_durations': durations,
            'recorded_cumulative_request_bytes': sum(row['request']['bytes'] for row in starts),
            'recorded_provider_path_census': dict(Counter(str(row.get('path')) for row in starts)),
            'minimum_recorded_allocation_timestamp_gap_seconds': min(gaps) if gaps else None,
            'actual_network_send_timestamps_captured': False,
            'consistency_questions': questions, 'unknown_usage_is_zero': False}


def runtime_analysis(read, plan, result):
    raw = read.raw('execution/portable-runtime.json', optional=True)
    expected = result.get('portable_runtime_sha256')
    questions = []
    if expected is not None and (raw is None or digest(raw)['sha256'] != expected):
        questions.append('result_and_retained_portable_runtime_digest_differ')
    value = json.loads(raw) if raw is not None else None
    if value is not None:
        if value.get('required_original_versions') != plan['versions']:
            questions.append('runtime_required_versions_differ_from_frozen_plan')
        if any((value.get('distributions') or {}).get(name) != version for name, version in plan['versions'].items()):
            questions.append('runtime_installed_versions_differ_from_frozen_plan')
        for key in ('source_stage_sha256', 'original_windows_environment_sha256'):
            if value.get(key) != plan.get(key):
                questions.append('runtime_' + key + '_differs_from_frozen_plan')
    return {'record_present': value is not None, 'sha256': digest(raw)['sha256'] if raw is not None else None,
            'python_version': value.get('python_version') if value else None,
            'required_original_versions': value.get('required_original_versions') if value else None,
            'manifested_runtime_files': len(value.get('files', {})) if value else None,
            'runtime_package_bytes_independently_retained': False, 'consistency_questions': questions}


def analyze(read):
    plan = read.json('plan/plan.json')
    result = read.json('execution/result.json')
    if plan.get('schema_version') != 'ap2-native-shopper-provider-plan/1' or plan.get('allocated_task_count') != 1 or len(result.get('cases', [])) != 1:
        raise ValueError('single_declared_development_case_required')
    for name, expected in plan['owned_sources'].items():
        if digest(read.raw('plan/owned-source/' + name)) != expected:
            raise ValueError('frozen_owned_source_snapshot_differs')
    case = result['cases'][0]
    if case['case_id'] != CASE_ID or plan['public_human_facts']['case_id'] != CASE_ID:
        raise ValueError('declared_case_identity_differs')
    root = 'execution/cases/' + CASE_ID + '/'
    shopper = root + 'shopper/'
    snapshots = [(name, read.json(name)) for name in sorted(read.manifest) if re.fullmatch(re.escape(shopper) + r'turn-\d+-session\.json', name)]
    public = public_analysis(read.rows(shopper + 'ADK-events.jsonl'), read.rows(shopper + 'public-conversation.jsonl'),
                             read.rows(shopper + 'public-actor-decisions.jsonl'), snapshots, plan['public_human_facts'])
    provider = provider_analysis(read, result)
    runtime = runtime_analysis(read, plan, result)
    launch = read.json(root + 'native-launch.json', optional=True)
    binding = read.json(shopper + 'original-root-binding.json', optional=True)
    worker = read.json(shopper + 'worker-result.json', optional=True)
    questions = [*public['consistency_questions'], *provider['consistency_questions'], *runtime['consistency_questions']]
    if worker is not None and worker.get('ADK_event_count') != public['raw_ADK_events']:
        questions.append('worker_and_raw_ADK_event_count_differs')
    if binding is not None:
        expected = plan['sources']['code/samples/python/src/roles/shopping_agent/agent.py']['sha256']
        if binding.get('original_root_source_sha256') != expected or binding.get('root_model') != MODEL or binding.get('deterministic_BaseLlm_replacement') is not False:
            questions.append('actual_original_root_binding_differs')
        if public['session_snapshot_ids'] and public['session_snapshot_ids'] != [binding.get('session_id')]:
            questions.append('root_binding_and_recorded_session_identity_differ')
        if (binding.get('genai_Client_replaced') is not False or binding.get('official_ADK_runner') is not True
                or binding.get('root_name') != 'root_agent'
                or binding.get('original_root_tool_names') != list(BUSINESS_TOOLS['root_agent'])
                or [row.get('name') for row in binding.get('subagents', [])] != list(STAGES[1:])
                or any(row.get('model') != MODEL for row in binding.get('subagents', []))):
            questions.append('actual_original_root_tool_model_or_subagent_surface_record_differs')
    if provider['recorded_cumulative_request_bytes'] != (result.get('provider') or {}).get('cumulative_request_bytes', 0):
        questions.append('retained_request_bytes_and_parent_summary_differ')
    if provider['upstream_allocations'] > plan['limits']['upstream_calls_including_smoke'] or provider['recorded_cumulative_request_bytes'] > plan['limits']['maximum_total_request_bytes']:
        questions.append('recorded_provider_allocations_or_request_bytes_exceed_frozen_bounds')
    if provider['minimum_recorded_allocation_timestamp_gap_seconds'] is not None and provider['minimum_recorded_allocation_timestamp_gap_seconds'] < plan['limits']['minimum_interval_seconds']:
        questions.append('recorded_provider_allocation_timestamp_gap_below_frozen_minimum')
    if any(path != plan['provider_path'] for path in provider['recorded_provider_path_census']):
        questions.append('recorded_provider_path_differs_from_frozen_plan')
    if launch is not None:
        for role, expected in launch.get('public_cards', {}).items():
            if digest(read.raw(root + role + '.agent-card.json')) != expected:
                questions.append('recorded_native_agent_card_digest_differs')
    read.raw(root + 'shopper.stdout.log', optional=True)
    cleanups = case.get('process_cleanup', [])
    native_pids = {}
    for role in ('merchant', 'credentials', 'processor'):
        raw = read.raw(root + role + '.stdout.log', optional=True)
        matches = re.findall(rb'Started server process \[(\d+)\]', raw or b'')
        native_pids[role] = [int(value) for value in matches]
    cleanup_ids = {row['pid'] for row in cleanups if row.get('reaped')}
    if any(pid not in cleanup_ids for values in native_pids.values() for pid in values):
        questions.append('recorded_native_PID_lacks_reaped_cleanup')
    questions = list(dict.fromkeys(questions))
    return {'schema_version': 'ap2-native-shopper-provider-offline-analysis/1',
            'run_id': read.receipt['run_id'], 'head_sha': read.receipt['head_sha'], 'archive_sha256': read.receipt['archive_sha256'],
            'case_denominator': 1, 'case_id': CASE_ID, 'adaptive_development_followup': True, 'held_out_study': False,
            'status': 'retained_native_shopper_observations_consistent' if not questions else 'retained_native_shopper_incomplete_or_inconsistent',
            'observed_case_outcome': ('original_ADK_error_before_any_business_tool_or_visible_reply'
                 if public['raw_ADK_error_events'] and not public['business_call_count'] and not public['visible_model_messages']
                 else 'retained_development_observations_require_per_branch_reading'),
            'consistency_questions': questions, 'parent_case_status': case.get('status'),
            'parent_failure': result.get('failure'), 'worker_result': worker,
            'public_and_ADK': public, 'provider': provider,
            'native_launch': launch, 'original_root_binding': binding,
            'native_stdout_process_IDs': native_pids, 'parent_process_cleanup': cleanups,
            'all_recorded_children_reaped': all(row.get('reaped') for row in cleanups) if cleanups else None,
            'source_tree_unchanged_parent_record': result.get('source_tree_unchanged_after_original_run'),
            'copied_source_unchanged_parent_record': case.get('private_original_source_bytes_unchanged'),
            'runtime_manifest': runtime,
            'native_listener_ownership_parent_record': launch.get('exact_native_PID_listener_ownership_verified_before_card_requests') if launch else None,
            'native_listener_inode_records_independently_captured': False,
            'validated_read_members': read.reads, 'whole_task_grade': None, 'human_gold': False,
            'original_run_sh_provisioning_qualified': False, 'original_A2A_wire_capture_claimed': False,
            'hidden_effects_or_real_settlement_proven': False,
            'limits': ['Consistency is a reconstruction of retained development observations, not human task grading.',
                       'An owned public actor stop, original tool failure, provider failure and unreached branch are separate outcomes.',
                       'PID cleanup and listener ownership are recorded parent observations; listener inode snapshots and original full A2A wire are absent.',
                       'Runtime manifest identity and recorded versions are joined; installed package bytes are not independently archived here.',
                       'A retained sample receipt or assistant payment claim does not prove settlement, duplicate safety or hidden effects.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--retained', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise ValueError('fresh_additive_analysis_output_required')
    result = analyze(Retained(args.retained.resolve()))
    output.mkdir(parents=True)
    result['analyzer_source_sha256'] = file_hash(Path(__file__).resolve())
    with (output / 'analysis.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'status': result['status'], 'case_denominator': 1, 'consistency_questions': len(result['consistency_questions']),
                      'observed_ADK_events': result['public_and_ADK']['raw_ADK_events'],
                      'sample_success_receipts': result['public_and_ADK']['unique_success_receipt_records']}))


if __name__ == '__main__':
    main()
