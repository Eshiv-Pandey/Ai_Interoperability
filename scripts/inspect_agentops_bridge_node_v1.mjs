// Import-only runtime preflight; no servers, bridge calls, or application imports.
import { readFileSync, realpathSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const output = process.argv[2];
if (!output) throw new Error('Supply a fresh output JSON path');
const hash = file => createHash('sha256').update(readFileSync(file)).digest('hex');
const result = { schema_version: 'agentops-bridge-node-preflight/1',
  node: process.version, executable: realpathSync(process.execPath),
  executable_sha256: hash(process.execPath), platform: process.platform,
  application_requests: 0, live_model_calls: 0, installations: 0, bridges: [], status: 'failed' };
try {
  for (const name of ['a2a-to-mcp', 'mcp-a2a']) {
    const entry = path.join(root, 'external', name, 'dist/index.js');
    const module = await import(pathToFileURL(entry));
    const require = createRequire(entry);
    const sdk = require.resolve('@a2a-js/sdk/client');
    result.bridges.push({ name, entry, entry_sha256: hash(entry),
      exports: Object.keys(module), sdk, sdk_sha256: hash(sdk) });
  }
  result.status = 'imports_passed';
} catch (error) { result.error = error.stack ?? String(error); }
writeFileSync(output, JSON.stringify(result, null, 2) + '\n', { flag: 'wx' });
process.stdout.write(JSON.stringify(result, null, 2) + '\n');
process.exitCode = result.status === 'imports_passed' ? 0 : 1;
