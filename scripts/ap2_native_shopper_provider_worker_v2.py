"""Original ADK shopper with a declared public user actor and native peers.

Importing this module loads no application, SDK or provider. Only ``execute``
imports the pinned original root and official ADK runtime. Public user replies
are derived from visible final-response text, never state or tool payloads.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
MAX_TURNS = 12
MAX_EVENTS = 160
MAX_EVENT_BYTES = 262144
WORKER_SECONDS = 600
SYNTHETIC_KEY = 'AP2_OWNED_ACCOUNTED_DOWNSTREAM_KEY_NOT_A_PROVIDER_CREDENTIAL'


def now():
    return datetime.now(timezone.utc).isoformat()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def append(path, value):
    raw = (json.dumps(value, sort_keys=True, allow_nan=False) + '\n').encode()
    if len(raw) > MAX_EVENT_BYTES:
        raise ValueError('owned_ADK_event_size_bound')
    with path.open('ab') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def public_facts():
    return {'case_id': 'ap2-native-shopper-provider-v4-correct-human',
            'initial_request': 'I want to buy comfortable unbranded walking shoes. My maximum budget is USD 100, with no brand or color preference and no other requirements. Please show the available options.',
            'maximum_budget_USD': 100, 'preferences': 'comfortable; no brand or color preference',
            'cart_index': 0, 'digital_wallet': 'Google Wallet',
            'user_email': 'bugsbunny@gmail.com', 'wallet_consent': True,
            'payment_method_index': 0, 'confirm_cart': True, 'otp_response': '123'}


def public_price_check(text, budget, *, first_option=False):
    """USD-only visible price gate; never guess an exchange rate or a total."""
    candidate = text
    if first_option:
        if re.search(r'(?m)^\s*(?:[-*]\s+|\(\d+\)\s+)', text):
            return None
        numbered = list(re.finditer(r'(?m)^\s*(?:\*\*)?(\d+)[.)]\s+', text))
        if not numbered or text[:numbered[0].start()].strip() or [int(row.group(1)) for row in numbered] != list(range(1, len(numbered) + 1)):
            return None
        first = numbered[0]
        candidate = text[first.start():]
        if len(numbered) > 1:
            candidate = text[first.start():numbered[1].start()]
    if re.search(r'\d(?:\s*[-\u2013\u2014]\s*|\s+(?:to|through|up to)\s*)(?:USD\s*|US\$\s*|\$\s*)?\d', candidate, re.I):
        return None
    # A dollar mark accompanied by a named foreign currency is not USD.
    if re.search(r'\b(?:EUR|GBP|CAD|AUD|NZD|INR|JPY|CNY|CHF|HKD|SGD|MXN)\b|[\u20ac\u00a3\u00a5\u20b9]', candidate, re.I):
        return None
    if any(match.group(1).upper() not in {'US', 'USD'} for match in re.finditer(r'(?<![A-Za-z])([A-Za-z]{1,4})\$', candidate)):
        return None
    if re.search(r'\b(?:C|A|CA|AU|NZ|HK|SG|NT|CN)\s+\$', candidate):
        return None
    if any(match.group(1).casefold() not in {'us', 'american', 'states'} for match in re.finditer(r'\b([A-Za-z]+)\s+dollars?\b', candidate, re.I)):
        return None
    # Capture the complete numeric token first. Validation then rejects bad
    # comma grouping, exponent notation or excessive decimals as a whole.
    raw_number = r'[-+]?\d+(?:,\d+)*(?:\.\d+)?(?:[eE][-+]?\d+)?'
    pattern = re.compile(r'(?<![A-Za-z])(?:USD\s*|US\s*\$\s*|\$\s*)(' + raw_number + r')(?![A-Za-z0-9]|[.,]\d)|(?<![A-Za-z0-9.,])(' + raw_number + r')\s+USD\b', re.I)
    matches = list(pattern.finditer(candidate))
    valid_number = r'(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?'
    if any(not re.fullmatch(valid_number, match.group(1) or match.group(2)) for match in matches):
        return None
    amounts = [Decimal((match.group(1) or match.group(2)).replace(',', '')) for match in matches]
    if not amounts or any(amount > Decimal(str(budget)) for amount in amounts):
        return None
    # More than one distinct visible amount can be item/shipping/subtotal. Do
    # not manufacture the checkout total from a collection of price mentions.
    selected = None
    if not first_option:
        label = r'(?:grand total|order total|total amount|total due|amount due)'
        total_lines = [line for line in candidate.splitlines() if re.search(r'\b' + label + r'\b', line, re.I)]
        if len(total_lines) != 1:
            return None
        total_pattern = re.compile(r'^\s*(?:[-*]\s*)?(?:\*\*)?' + label +
            r'(?:\*\*)?\s*[:=]?\s*(?:\*\*)?(?:USD\s*(' + raw_number +
            r')|US\$\s*(' + raw_number + r')|(' + raw_number + r')\s+USD)(?:\*\*)?\s*[.!]?\s*$', re.I)
        total = total_pattern.fullmatch(total_lines[0])
        if total is None:
            return None
        total_token = next(value for value in total.groups() if value is not None)
        if not re.fullmatch(valid_number, total_token):
            return None
        selected = Decimal(total_token.replace(',', ''))
        if selected > Decimal(str(budget)):
            return None
    if selected is None:
        if len(set(amounts)) != 1:
            return None
        selected = amounts[0]
    return {'currency': 'USD', 'visible_amount': str(selected), 'maximum_budget_USD': budget,
            'exchange_rate_or_hidden_state_used': False}


def public_reply(text, facts, previous_categories):
    """Conservative public actor: ambiguous or unseen questions stop the run.

    Exact categories and facts are frozen before allocation. This function
    receives no tool output, session state, private answer, or model object.
    """
    if type(text) is not str or not text.strip():
        return None
    normalized = ' '.join(text.casefold().split())
    asks = ('?' in text or any(word in normalized for word in
            ('please choose', 'please select', 'please provide', 'please enter',
             'please confirm', 'provide the', 'enter the', 'which would', 'let me know')))
    if not asks:
        return None
    categories = []
    if re.search(r'\b(?:otp|one[- ]time (?:password|code)|verification code)\b', normalized) and any(
            word in normalized for word in ('provide', 'enter', 'send', 'what', 'code?')):
        categories.append(('otp', facts['otp_response']))
    if 'wallet' in normalized and any(word in normalized for word in ('manual', 'prefer', 'which wallet', 'google wallet', 'paypal')):
        categories.append(('wallet-choice', 'Please use ' + facts['digital_wallet'] + '.'))
    if ('bugsbunny@gmail.com' in normalized or 'your account' in normalized or 'share your' in normalized) and any(
            word in normalized for word in ('access', 'allow', 'agree', 'is that ok', 'consent')):
        categories.append(('wallet-consent', 'Yes, I agree to access my demo account ' + facts['user_email'] + ' for this purchase.'))
    if ('email' in normalized or 'e-mail' in normalized) and not any(category == 'wallet-consent' for category, _ in categories):
        categories.append(('email', facts['user_email']))
    if any(word in normalized for word in ('payment method', 'forms of payment', 'payment option', 'eligible card')) and any(
            word in normalized for word in ('choose', 'select', 'which', 'prefer')) and re.search(r'(?m)^\s*1[.)]|\b(?:card|visa|mastercard|amex)\b', text.casefold()):
        categories.append(('payment-selection', 'I choose the first eligible payment method you displayed.'))
    cart_price, invalid_price = None, False
    if any(word in normalized for word in ('cart id', 'cart_id')) and any(
            word in normalized for word in ('choose', 'select', 'which', 'purchase')):
        cart_price = public_price_check(text, facts['maximum_budget_USD'], first_option=True)
        invalid_price = cart_price is None
        if cart_price is not None:
            categories.append(('cart-selection', 'I choose the first product option you displayed.'))
    if ('cart summary' in normalized or 'checkout' in normalized or 'confirm this purchase' in normalized) and any(
            word in normalized for word in ('confirm', 'proceed with', 'approve')):
        checkout_price = public_price_check(text, facts['maximum_budget_USD'])
        invalid_price = invalid_price or checkout_price is None
        if checkout_price is not None:
            categories.append(('checkout-confirmation', 'Yes, I confirm the displayed cart summary and authorize this demo purchase.'))
    # OTP, checkout and wallet consent are separate authorizations. Multiple
    # categories are retained as ambiguity rather than arbitrarily prioritized.
    if invalid_price or len(categories) != 1 or categories[0][0] in previous_categories:
        return None
    reply = {'category': categories[0][0], 'text': categories[0][1]}
    if reply['category'] == 'cart-selection':
        reply['visible_price_check'] = cart_price
    if reply['category'] == 'checkout-confirmation':
        reply['visible_price_check'] = checkout_price
    return reply


def visible_final_text(event):
    """Match ADK final user-facing text; omit thought and function parts."""
    if not event.is_final_response() or getattr(event, 'author', None) == 'user':
        return ''
    content = getattr(event, 'content', None)
    if content is None or getattr(content, 'role', None) != 'model':
        return ''
    if any(getattr(part, 'function_call', None) or getattr(part, 'function_response', None)
           for part in content.parts or []):
        return ''
    return '\n'.join(part.text for part in content.parts or []
                     if getattr(part, 'text', None) and not getattr(part, 'thought', False))


def actor_guard(proxy_url):
    parsed = urlparse(proxy_url)
    if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or not parsed.port:
        raise ValueError('owned_loopback_provider_required')
    ports = {8001, 8002, 8003, parsed.port}
    denied = {'private_reads': 0, 'external_network': 0, 'descendants': 0}

    def guard(event, values):
        if event == 'open' and values and isinstance(values[0], (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(values[0])).absolute()
            name = path.name.casefold()
            if name == '.env' or name.startswith('gemini-api-key') or ('evaluator' in name and path.is_relative_to(ROOT)):
                denied['private_reads'] += 1
                raise PermissionError('owned_user_actor_private_read_denied')
        if event in {'socket.connect', 'socket.connect_ex', 'socket.getaddrinfo', 'socket.sendto'}:
            address = values[1] if event in {'socket.connect', 'socket.connect_ex'} else (
                (values[0], values[1]) if event == 'socket.getaddrinfo' else values[-1])
            if not isinstance(address, tuple) or len(address) < 2 or address[0] not in {'127.0.0.1', 'localhost', '::1'} or address[1] not in ports:
                denied['external_network'] += 1
                raise PermissionError('owned_user_actor_external_network_denied')
        if event == 'subprocess.Popen' or event == 'os.system' or event.startswith('os.spawn'):
            denied['descendants'] += 1
            raise PermissionError('owned_user_actor_descendant_process_denied')
    sys.addaudithook(guard)
    return denied


async def application(output, facts, source_root):
    # The original model, instructions, root/subagents and tools stay intact.
    from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
    from google.adk.runners import Runner
    from google.adk.agents.run_config import RunConfig, StreamingMode
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    from roles.shopping_agent.agent import root_agent
    from roles.shopping_agent import remote_agents

    import roles.shopping_agent.agent as original_root_module
    original_root_file = Path(original_root_module.__file__).resolve()
    if original_root_file != source_root / 'code/samples/python/src/roles/shopping_agent/agent.py':
        raise ValueError('original_root_import_origin_differs_from_private_copy')
    if root_agent.model != 'gemini-3.1-flash-lite-preview' or [agent.name for agent in root_agent.sub_agents] != [
            'shopper', 'shipping_address_collector', 'payment_method_collector']:
        raise ValueError('original_root_model_or_subagents_changed')

    sessions, artifacts = InMemorySessionService(), InMemoryArtifactService()
    session = await sessions.create_session(app_name='ap2_original_native_shopper', user_id='prospective_demo_user')
    runner = Runner(agent=root_agent, app_name='ap2_original_native_shopper',
                    session_service=sessions, artifact_service=artifacts)
    run_config = RunConfig(streaming_mode=StreamingMode.NONE)
    write(output / 'original-root-binding.json', {
        'root_class': type(root_agent).__module__ + '.' + type(root_agent).__qualname__,
        'root_name': root_agent.name, 'root_model': root_agent.model,
        'subagents': [{'name': agent.name, 'model': agent.model,
                      'class': type(agent).__module__ + '.' + type(agent).__qualname__}
                     for agent in root_agent.sub_agents],
        'original_tools_instructions_models_unchanged': True,
        'original_root_tool_names': [tool.__name__ for tool in root_agent.tools],
        'official_ADK_runner': True, 'streaming_mode': 'NONE',
        'owned_public_user_actor': True, 'deterministic_BaseLlm_replacement': False,
        'genai_Client_replaced': False, 'session_id': session.id,
        'original_root_import_file': str(original_root_file),
        'original_root_source_sha256': hashlib.sha256(original_root_file.read_bytes()).hexdigest(),
        'original_native_remote_clients': [remote_agents.merchant_agent_client._base_url,
                                            remote_agents.credentials_provider_client._base_url]})
    user_message, previous_categories, event_count = facts['initial_request'], [], 0
    status, failure = 'maximum_public_turns_reached', None
    try:
        for turn in range(MAX_TURNS):
            append(output / 'public-conversation.jsonl', {'time': now(), 'turn': turn, 'role': 'user', 'text': user_message})
            visible = []
            async for event in runner.run_async(user_id=session.user_id, session_id=session.id,
                    new_message=types.Content(role='user', parts=[types.Part(text=user_message)]), run_config=run_config):
                event_count += 1
                if event_count > MAX_EVENTS:
                    raise ValueError('owned_ADK_event_count_bound')
                append(output / 'ADK-events.jsonl', {'time': now(), 'turn': turn,
                       'event': event.model_dump(mode='json', by_alias=True, exclude_none=True)})
                text = visible_final_text(event)
                if text:
                    visible.append(text)
                    append(output / 'public-conversation.jsonl', {'time': now(), 'turn': turn, 'role': 'model',
                           'author': event.author, 'text': text, 'official_final_response': True, 'thought_parts_excluded': True})
            snapshot = await sessions.get_session(app_name=session.app_name, user_id=session.user_id, session_id=session.id)
            write(output / f'turn-{turn:02d}-session.json', snapshot.model_dump(mode='json', by_alias=True, exclude_none=True))
            prompt = visible[-1] if visible else ''
            reply = public_reply(prompt, facts, previous_categories)
            append(output / 'public-actor-decisions.jsonl', {'time': now(), 'turn': turn,
                   'visible_prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
                   'reply': reply, 'session_or_tool_state_used': False})
            if reply is None:
                status = 'public_actor_stopped_without_unambiguous_unseen_question'
                break
            previous_categories.append(reply['category'])
            user_message = reply['text']
    except BaseException as error:
        failure = {'type': type(error).__name__, 'message': ' '.join(str(error).split())[:500]}
        status = 'original_ADK_failure_or_owned_limit_retained'
    finally:
        clients = [remote_agents.merchant_agent_client._httpx_client, remote_agents.credentials_provider_client._httpx_client]
        await asyncio.gather(*(client.aclose() for client in clients), return_exceptions=True)
        write(output / 'worker-result.json', {'schema_version': 'ap2-native-shopper-provider-worker/2',
              'time': now(), 'case_id': facts['case_id'], 'status': status, 'failure': failure,
              'ADK_event_count': event_count, 'public_reply_categories': previous_categories,
              'original_remote_http_clients_closed': [client.is_closed for client in clients],
              'whole_task_grade': None, 'human_gold_qualified': False,
              'native_source_and_model_observation_requires_separate_analysis': True})


def execute(facts_path, output, source_root):
    facts = json.loads(facts_path.read_bytes())
    if facts != public_facts():
        raise ValueError('only_frozen_public_human_facts_allowed')
    if os.environ.get('GOOGLE_API_KEY') != SYNTHETIC_KEY or os.environ.get('GOOGLE_GENAI_USE_VERTEXAI') != 'false' or any(
            os.environ.get(name) for name in ('GOOGLE_APPLICATION_CREDENTIALS', 'GOOGLE_VERTEX_BASE_URL')):
        raise ValueError('original_worker_requires_synthetic_proxy_credential_and_no_Vertex_or_ADC')
    output.mkdir(parents=True, exist_ok=False)
    denied = actor_guard(os.environ.get('GOOGLE_GEMINI_BASE_URL', ''))
    try:
        asyncio.run(asyncio.wait_for(application(output, facts, source_root), timeout=WORKER_SECONDS))
    finally:
        write(output / 'actor-input-separation.json', {'denials': denied,
              'public_user_replies_use_visible_final_text_only': True,
              'provider_credential_is_synthetic_downstream_only': True,
              'scope': 'Python audit controls, not an OS hostile-code sandbox'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public-human-facts', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, required=True)
    args = parser.parse_args()
    execute(args.public_human_facts.resolve(), args.output.resolve(), args.source_root.resolve())


if __name__ == '__main__':
    main()
