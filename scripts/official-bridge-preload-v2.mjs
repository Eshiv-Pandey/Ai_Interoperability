// Adds a local shutdown-control observer; original CLI and fetch remain unchanged.
import './log-reference-http.mjs';
import assert from 'node:assert/strict';
import { appendFileSync, readFileSync, watchFile, unwatchFile } from 'node:fs';
import path from 'node:path';
import { workspace, stamp } from './log-reference-http.mjs';
const control = path.resolve(process.env.REFERENCE_CLOSE_CONTROL);
assert(control.startsWith(path.join(workspace, 'runs/reference-bridge-observation') + path.sep));
let closing = false;
watchFile(control, { interval: 25, persistent: false }, () => {
  if (closing) return;
  let value;
  try { value = JSON.parse(readFileSync(control, 'utf8')); } catch { return; }
  assert.equal(value.pid, process.pid); assert.equal(value.run_id, process.env.REFERENCE_RUN_ID);
  assert.equal(value.action, 'close');
  closing = true; unwatchFile(control);
  appendFileSync(process.env.REFERENCE_HTTP_LOG, JSON.stringify({ type: 'shutdown-request', pid: process.pid,
    observed: stamp(), original_sigterm_listeners: process.listenerCount('SIGTERM'),
    mechanism: 'Python supervisor exclusive control file; original CLI SIGTERM handler' }) + '\n');
  assert(process.listenerCount('SIGTERM') > 0);
  process.emit('SIGTERM');
});

