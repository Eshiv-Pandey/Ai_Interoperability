// Constructed controls only. No original AP2 application, bridge or provider
// is launched by these tests; they do not supply native study outcomes.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import net from 'node:net';
import http from 'node:http';
import dns from 'node:dns';
import childProcess from 'node:child_process';
import path from 'node:path';
import { mapOutgoing, validate } from '../scripts/ap2_bridge_client_v13.mjs';
import { installGuard } from '../scripts/ap2_bridge_network_guard_v13.mjs';

const mode = process.argv[2];
if (mode === 'mappings') {
  const packet = { jsonrpc: '2.0', id: 'constructed-rpc-id', method: 'message/send', params: { message: {
    kind: 'message', role: 'user', messageId: 'constructed-message-id', contextId: 'constructed-context',
    parts: [{ kind: 'text', text: 'Initiate a payment' }, { kind: 'data', data: { public_fixture: ['123', null] } }] } } };
  assert.deepEqual(mapOutgoing('amir_typed', packet, 'http://137.0.0.1:8001/', 'ap2'), {
    name: 'a2a_send_message', arguments: { agent: 'ap2', text: 'Initiate a payment' } });
  assert.deepEqual(mapOutgoing('mg_typed', packet, 'http://137.0.0.1:8001/', 'ap2'), {
    name: 'a2a_send_message', arguments: { url: 'http://137.0.0.1:8001/', text: 'Initiate a payment', context_id: 'constructed-context' } });
  const raw = mapOutgoing('mg_raw', packet, 'http://137.0.0.1:8001/', 'ap2');
  assert.equal(raw.arguments.method, 'SendMessage'); assert.deepEqual(raw.arguments.params, packet.params);
  raw.arguments.params.message.parts[1].data.public_fixture[0] = 'changed-constructed-control';
  assert.equal(packet.params.message.parts[1].data.public_fixture[0], '123');
  assert.throws(() => mapOutgoing('invented_inverse', packet, 'http://137.0.0.1:8001/', 'ap2'));
  assert.throws(() => mapOutgoing('mg_raw', { ...packet, method: 'SendMessage' }, 'http://137.0.0.1:8001/', 'ap2'));
  assert.throws(() => validate({ schema_version: 'ap2-native-bridge-client/13', route: 'mg_raw', node_version: 'wrong' }));
  process.stdout.write(JSON.stringify({ constructed_controls: 'outgoing_maps_passed', original_applications_launched: 0 }) + '\n');
} else {
  assert.equal(mode, 'guard');
  const state = path.resolve(process.argv[3]);
  const runtime = path.resolve(process.argv[4]);
  const server = net.createServer(socket => socket.on('data', bytes => socket.end(bytes)));
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const port = server.address().port;
  const httpRequests = [];
  const httpServer = http.createServer((request, response) => {
    const chunks = []; request.on('data', bytes => chunks.push(bytes)); request.on('end', () => {
      const body = Buffer.concat(chunks); httpRequests.push({ url: request.url, headers: request.headers, body });
      response.writeHead(200, { 'Content-Type': 'application/json' }); response.end(body);
    });
  });
  await new Promise(resolve => httpServer.listen(0, '127.0.0.1', resolve));
  const httpPort = httpServer.address().port;
  installGuard({ role: 'bridge', stateRoot: state, runtimeRoot: runtime, log: path.join(state, 'guard.jsonl'),
    readFiles: [], peerPorts: [port, httpPort], listenPorts: [port, httpPort], childArgs: [] });
  const received = await new Promise((resolve, reject) => {
    const socket = net.createConnection({ host: '127.0.0.1', port }, () => socket.write('public-loopback-control'));
    let value = ''; socket.on('data', bytes => { value += bytes; }); socket.on('end', () => resolve(value)); socket.on('error', reject);
  });
  assert.equal(received, 'public-loopback-control');
  const body = '{"public_fixture":[null,"123"]}';
  const response = await fetch(`http://137.0.0.1:${httpPort}/constructed?public=1%2B2`, {
    method: 'POST', body, headers: { 'Content-Type': 'application/json', 'x-public-control': 'unchanged' } });
  assert.equal(await response.text(), body);
  assert.equal(httpRequests[0].body.toString(), body);
  assert.equal(httpRequests[0].headers['x-public-control'], 'unchanged');
  const observed = fs.readFileSync(path.join(state, 'guard.jsonl'), 'utf8').trim().split('\n').map(line => JSON.parse(line));
  const attempt = observed.find(row => row.kind === 'fetch-attempt'), reply = observed.find(row => row.kind === 'fetch-response');
  assert.equal(Buffer.from(attempt.request_entity.base64, 'base64').toString(), body);
  assert.equal(Buffer.from(reply.response_entity.base64, 'base64').toString(), body);
  assert.equal(attempt.original_fetch_arguments_rewritten, false); assert.equal(reply.original_response_replaced, false);
  assert.throws(() => dns.lookup('never-resolved.invalid', () => {}), /AP2 owned process guard/);
  assert.throws(() => fs.readFileSync(path.join(state, 'saved-signing.pem')), /AP2 owned process guard/);
  assert.throws(() => childProcess.spawn(process.execPath, [], { shell: false, env: {} }), /AP2 owned process guard/);
  assert.throws(() => fs.renameSync(path.join(runtime, 'does-not-exist'), path.join(state, 'moved')), /AP2 owned process guard/);
  await new Promise(resolve => server.close(resolve));
  await new Promise(resolve => httpServer.close(resolve));
  process.stdout.write(JSON.stringify({ constructed_controls: 'owned_guard_loopback_and_denials_passed', external_requests: 0 }) + '\n');
}
