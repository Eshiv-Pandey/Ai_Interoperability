// Explicit source-unchanged library deployment for B6/B7; no top-level startup on import.
import assert from 'node:assert/strict';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

export function createVersionFetch(origin, mode, implementation = globalThis.fetch) {
  assert(['passthrough', 'version-header'].includes(mode));
  const permittedOrigin = new URL(origin).origin;
  return (input, init) => {
    if (mode === 'passthrough') return implementation(input, init);
    const target = new URL(input instanceof Request ? input.url : String(input));
    if (target.origin !== permittedOrigin) return implementation(input, init);
    const headers = new Headers(init?.headers ?? (input instanceof Request ? input.headers : undefined));
    headers.set('A2A-Version', '1.0');
    return implementation(input, { ...init, headers });
  };
}

export async function main(argv = process.argv.slice(2)) {
  const args = {};
  for (let index = 0; index < argv.length; index += 2) {
    assert(['--workspace', '--mode', '--origin'].includes(argv[index]), 'Unexpected embed option');
    assert(argv[index + 1] && args[argv[index]] === undefined, 'Missing/duplicate embed option');
    args[argv[index]] = argv[index + 1];
  }
  assert(args['--workspace'] && args['--mode'] && args['--origin']);
  const origin = new URL(args['--origin']);
  assert(origin.protocol === 'http:' && origin.hostname === '127.0.0.1' && !origin.username && !origin.password);
  const directory = path.resolve(args['--workspace'], 'external/mcp-a2a');
  const { createServer, loadConfig } = await import(pathToFileURL(path.join(directory, 'dist/index.js')).href);
  const { StdioServerTransport } = await import(pathToFileURL(path.join(directory,
    'node_modules/@modelcontextprotocol/server/dist/stdio.mjs')).href);
  const config = loadConfig();
  assert(config.allowWrites === true && config.channel === false && config.maxRetries === 0,
    'Expected frozen write-enabled, no-channel, zero-retry profile');
  const created = createServer({ config, fetch: createVersionFetch(origin.origin, args['--mode']), watchChannel: false });
  const transport = new StdioServerTransport();
  await created.server.connect(transport);
  process.stderr.write(JSON.stringify({ type: 'agentops-embed-ready', mode: args['--mode'], origin: origin.origin }) + '\n');
  let closing = false;
  const close = async () => {
    if (closing) return;
    closing = true;
    try { created.channel?.stop(); await created.server.close(); process.exit(0); }
    catch (error) { process.stderr.write(String(error?.stack ?? error) + '\n'); process.exit(1); }
  };
  process.on('SIGTERM', close);
  process.on('SIGINT', close);
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  main().catch(error => { process.stderr.write(String(error?.stack ?? error) + '\n'); process.exitCode = 1; });
}
