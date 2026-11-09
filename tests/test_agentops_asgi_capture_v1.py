"""Constructed transport checks for the observer; no application execution."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from agentops_asgi_capture_v1 import Capture


class ASGICaptureTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='agentops-asgi-')
        self.addCleanup(temporary.cleanup)
        self.output = Path(temporary.name)
        self.enterContext(patch('agentops_asgi_capture_v1.evidence.database_snapshot',
                                return_value={'path': 'state/incidents.db', 'path_base': 'run'}))
        self.scope = {'type': 'http', 'method': 'POST', 'path': '/', 'http_version': '1.1',
                      'headers': [(b'content-length', b'4')], 'query_string': b''}

    async def test_request_and_stream_pass_through_without_normalization(self):
        incoming = [{'type': 'http.request', 'body': b'ab', 'more_body': True},
                    {'type': 'http.request', 'body': b'cd', 'more_body': False}]
        outgoing = [{'type': 'http.response.start', 'status': 200,
                     'headers': [(b'content-type', b'text/event-stream')]},
                    {'type': 'http.response.body', 'body': b'data: 1\n\n', 'more_body': True},
                    {'type': 'http.response.body', 'body': b'', 'more_body': False}]
        consumed, sent = [], []
        async def receive():
            return incoming[len(consumed)]
        async def send(message):
            sent.append(message)
        async def app(scope, recv, emit):
            self.assertIs(scope, self.scope)
            consumed.append(await recv())
            consumed.append(await recv())
            for message in outgoing:
                await emit(message)
        capture = Capture(app, self.output)
        await capture(self.scope, receive, send)
        folder = self.output / 'wire/000001'
        row = json.loads((folder / 'exchange.json').read_bytes())
        self.assertEqual(consumed, incoming)
        self.assertEqual(sent, outgoing)
        self.assertEqual((folder / 'request.body.bin').read_bytes(), b'abcd')
        self.assertEqual((folder / 'response.body.bin').read_bytes(), b'data: 1\n\n')
        self.assertTrue(row['request_body_complete'] and row['response_body_complete'])
        self.assertEqual(row['response_chunks'][0]['sha256'], hashlib.sha256(b'data: 1\n\n').hexdigest())
        before = json.loads((folder / 'before.snapshot.json').read_bytes())
        after = json.loads((folder / 'after.snapshot.json').read_bytes())
        self.assertLessEqual(before['observed_at_utc'], row['started_at_utc'])
        self.assertLessEqual(row['finished_at_utc'], after['observed_at_utc'])

    async def test_exception_preserves_partial_response_and_error(self):
        async def receive():
            return {'type': 'http.request', 'body': b'abcd'}
        async def send(message):
            pass
        async def app(scope, recv, emit):
            await recv()
            await emit({'type': 'http.response.start', 'status': 200})
            await emit({'type': 'http.response.body', 'body': b'partial', 'more_body': True})
            raise RuntimeError('constructed interruption')
        capture = Capture(app, self.output)
        with self.assertRaisesRegex(RuntimeError, 'constructed interruption'):
            await capture(self.scope, receive, send)
        folder = self.output / 'wire/000001'
        row = json.loads((folder / 'exchange.json').read_bytes())
        self.assertEqual((folder / 'response.body.bin').read_bytes(), b'partial')
        self.assertFalse(row['response_body_complete'])
        self.assertIn('constructed interruption', row['error'])
        self.assertEqual(len(capture.errors), 1)

    async def test_unconsumed_post_is_not_complete_but_bodyless_get_is(self):
        async def receive():
            raise AssertionError('Application does not consume a body')
        async def send(message):
            pass
        async def app(scope, recv, emit):
            await emit({'type': 'http.response.start', 'status': 400})
            await emit({'type': 'http.response.body', 'body': b'error'})
        capture = Capture(app, self.output)
        await capture(self.scope, receive, send)
        await capture(dict(self.scope, method='GET', headers=[]), receive, send)
        rows = [json.loads((self.output / f'wire/{seq:06d}/exchange.json').read_bytes()) for seq in (1, 2)]
        self.assertFalse(rows[0]['request_body_complete'])
        self.assertTrue(rows[1]['request_body_complete'])
        self.assertEqual([r['response_status'] for r in rows], [400, 400])


if __name__ == '__main__':
    unittest.main()
