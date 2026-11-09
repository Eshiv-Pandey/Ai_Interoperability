// Local environment capability probe only. No SDK/bridge/application imported.
import { createServer } from 'node:http';
import { createInterface } from 'node:readline';
const server = createServer((request, response) => response.end('capability-probe'));
server.on('error', error => {
  console.log(JSON.stringify({ type: 'listen-error', code: error.code, message: error.message }));
  process.exitCode = 1;
});
server.listen(0, '127.0.0.1', () => {
  console.log(JSON.stringify({ type: 'ready', pid: process.pid, address: server.address() }));
  const input = createInterface({ input: process.stdin, terminal: false });
  input.on('line', line => {
    console.log(JSON.stringify({ type: 'stdin-received', line }));
    if (line === 'close') {
      input.close();
      server.close(() => console.log(JSON.stringify({ type: 'closed', listening: server.listening })));
    }
  });
});
