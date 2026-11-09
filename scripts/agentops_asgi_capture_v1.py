"""Passive ASGI entity capture and read-only database boundary observations.

These are ASGI request/response entity bytes, not TCP or HTTP framing. Capturing
adds synchronous local I/O overhead; this observer is not a latency benchmark.
"""
import base64
import hashlib
from pathlib import Path
import time

import agentops_native_probe_v2 as evidence


class Capture:
    def __init__(self, app, output: Path, *, max_requests=256, max_bytes=32 * 1024 * 1024):
        self.app, self.output = app, output
        self.max_requests, self.max_bytes = max_requests, max_bytes
        self.sequence = 0
        self.errors = []
        (output / 'wire').mkdir(exist_ok=False)

    def snapshot(self, directory, name):
        value = {'observed_at_utc': evidence.now(), 'monotonic_ns': time.monotonic_ns(),
                 'database': evidence.database_snapshot(self.output / 'state/incidents.db', self.output, 'run')}
        evidence.write_json(directory / (name + '.snapshot.json'), value)

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        self.sequence += 1
        if self.sequence > self.max_requests:
            self.errors.append('HTTP request capture count exceeded')
            raise ValueError(self.errors[-1])
        directory = self.output / 'wire' / f'{self.sequence:06d}'
        directory.mkdir(exist_ok=False)
        headers = [(a.decode('latin-1'), b.decode('latin-1')) for a, b in scope.get('headers', [])]
        row = {
            'schema_version': 'agentops-asgi-exchange/1', 'sequence': self.sequence,
            'method': scope['method'], 'path': scope['path'], 'http_version': scope['http_version'],
            'query_string': base64.b64encode(scope.get('query_string', b'')).decode('ascii'),
            'request_headers': headers, 'response_status': None, 'response_headers': [],
            'request_body_complete': scope['method'] == 'GET' and
                all(value == '0' for key, value in headers if key.lower() == 'content-length'),
            'response_body_complete': False, 'response_chunks': [],
        }
        request_size = response_size = 0
        with (directory / 'request.body.bin').open('xb') as request_file, \
                (directory / 'response.body.bin').open('xb') as response_file:
            async def observed_receive():
                nonlocal request_size
                message = await receive()
                if message['type'] == 'http.request':
                    chunk = message.get('body', b'')
                    request_file.write(chunk)
                    request_size += len(chunk)
                    if request_size > self.max_bytes:
                        raise ValueError('ASGI request entity byte limit')
                    if not message.get('more_body', False):
                        row['request_body_complete'] = True
                return message

            async def observed_send(message):
                nonlocal response_size
                if message['type'] == 'http.response.start':
                    if row['response_status'] is not None:
                        raise ValueError('Duplicate ASGI response start')
                    row['response_status'] = message['status']
                    row['response_headers'] = [(a.decode('latin-1'), b.decode('latin-1'))
                                                for a, b in message.get('headers', [])]
                elif message['type'] == 'http.response.body':
                    chunk = message.get('body', b'')
                    response_file.write(chunk)
                    response_size += len(chunk)
                    row['response_chunks'].append({'bytes': len(chunk),
                        'sha256': hashlib.sha256(chunk).hexdigest(),
                        'more_body': message.get('more_body', False)})
                    if response_size > self.max_bytes:
                        raise ValueError('ASGI response entity byte limit')
                    if not message.get('more_body', False):
                        row['response_body_complete'] = True
                await send(message)

            try:
                self.snapshot(directory, 'before')
                row['started_at_utc'] = evidence.now()
                await self.app(scope, observed_receive, observed_send)
            except BaseException as error:
                row['error'] = f'{type(error).__name__}: {error}'
                self.errors.append({'sequence': row['sequence'], 'error': row['error']})
                raise
            finally:
                row['finished_at_utc'] = evidence.now()
                try:
                    self.snapshot(directory, 'after')
                except Exception as error:
                    row['snapshot_error'] = f'{type(error).__name__}: {error}'
                    self.errors.append({'sequence': row['sequence'], 'error': row['snapshot_error']})
                row['request_bytes'] = request_size
                row['response_bytes'] = response_size
                evidence.write_json(directory / 'exchange.json', row)
