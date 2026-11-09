"""Credential-free loopback capture with an explicit, bounded version choice."""
from datetime import datetime, timezone
import json
from pathlib import Path
import socket
import time

from agentops_http_bytes_v1 import decode_response, rpc_results, strict_json


def request_bytes(port, method, payload, version):
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError('Expected unprivileged loopback port')
    if version not in (None, '1.0') or method not in ('GET', 'POST'):
        raise ValueError('Outside the frozen protocol choices')
    if (method == 'GET') != (payload is None):
        raise ValueError('GET must be bodyless; POST must carry JSON')
    target = '/.well-known/agent-card.json' if method == 'GET' else '/'
    body = b'' if payload is None else json.dumps(payload, ensure_ascii=False,
        allow_nan=False, separators=(',', ':')).encode('utf-8')
    lines = [f'{method} {target} HTTP/1.1', f'Host: 127.0.0.1:{port}',
             'Connection: close', 'Accept-Encoding: identity',
             'Accept: application/json, text/event-stream', f'Content-Length: {len(body)}']
    if payload is not None:
        lines.append('Content-Type: application/json')
    if version is not None:
        lines.append('A2A-Version: ' + version)
    return ('\r\n'.join(lines) + '\r\n\r\n').encode('ascii') + body


def exchange(output: Path, label, port, method, payload=None, version='1.0', timeout=45):
    request = request_bytes(port, method, payload, version)
    with (output / f'{label}.request.bin').open('xb') as stream:
        stream.write(request)
    record = {'label': label, 'port': port, 'method': method, 'version': version,
              'started_at_utc': datetime.now(timezone.utc).isoformat(),
              'request_fully_sent': False, 'response_eof': False, 'status': 'failed'}
    deadline = time.monotonic() + timeout
    try:
        with (output / f'{label}.response.bin').open('xb') as stream:
            with socket.create_connection(('127.0.0.1', port), timeout=timeout) as connection:
                connection.sendall(request)
                record['request_fully_sent'] = True
                total = 0
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError('HTTP capture deadline')
                    connection.settimeout(remaining)
                    chunk = connection.recv(65536)
                    if not chunk:
                        record['response_eof'] = True
                        break
                    stream.write(chunk)
                    total += len(chunk)
                    if total > 32 * 1024 * 1024:
                        raise ValueError('HTTP capture byte limit')
        record['status'] = 'captured'
    except Exception as error:
        record['error'] = f'{type(error).__name__}: {error}'
    finally:
        record['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
        with (output / f'{label}.exchange.json').open('x', encoding='utf-8') as stream:
            json.dump(record, stream, indent=2)
    if record['status'] != 'captured':
        raise ValueError(f'{label} failed; preserve partial bytes')
    return decode_response((output / f'{label}.response.bin').read_bytes())


def rpc_response(response, rpc_id, streaming=False):
    status, headers, body = response
    if status != 200:
        raise ValueError(f'Expected successful RPC; got HTTP {status}')
    content_type = headers.get('content-type', '').split(';', 1)[0]
    if streaming:
        if content_type != 'text/event-stream':
            raise ValueError('Expected complete SSE response')
        return rpc_results(body, rpc_id)
    if content_type != 'application/json':
        raise ValueError('Expected JSON response')
    reply = strict_json(body)
    if reply.get('jsonrpc') != '2.0' or reply.get('id') != rpc_id or 'error' in reply:
        raise ValueError('RPC binding/error')
    return reply['result']


def pending_task(reply, streaming):
    if not streaming:
        task = reply['task']
        task_id, context_id, status = task['id'], task['contextId'], task['status']
    else:
        event = reply[-1]['statusUpdate']
        task_id, context_id, status = event['taskId'], event['contextId'], event['status']
    if status.get('state') != 'TASK_STATE_INPUT_REQUIRED':
        raise ValueError('Expected pending confirmation')
    calls = [p['data'] for p in status['message']['parts']
             if p.get('metadata', {}).get('adk_type') == 'function_call'
             and p.get('data', {}).get('name') == 'adk_request_confirmation']
    if len(calls) != 1 or not calls[0].get('id') or not task_id or not context_id:
        raise ValueError('Expected one public confirmation binding')
    return task_id, context_id, calls[0]
