# Converter eligibility audit

Audited locally on **24 October 2026**. This record verifies source provenance and a small development wire path. It does not establish admission correctness, a natural bridge defect, algorithmic novelty, or a held-out experimental result. No model inference or credentials were used. The workflow's original scientific first-week gate still requires independent finite checking, frozen route profiles, comparisons and mentor/team review.

The two supplied repository URLs both resolved and were cloned at exact commits. The second supplied candidate has no explicit source license, so a recently updated MIT candidate was found independently through GitHub repository search and checked as a replacement development mapping. All three local checkouts are detached. Exact manifests, dependency lock hashes and status are in [source-lock.json](../../external/source-lock.json).

| Candidate | Source pin and license | Direction and actual implementation | Development status |
| --- | --- | --- | --- |
| [AmirK-S/a2a-to-mcp](https://github.com/AmirK-S/a2a-to-mcp/tree/58eff9da469bccdc432bf164662727947de646b4) | `58eff9da469bccdc432bf164662727947de646b4`, Apache-2.0 | MCP HTTP client calls four generic tools; converter invokes A2A agent JSON-RPC. Opaque in-memory task/context handles. | Build passed; 42 selected upstream tests passed through genuine loopback HTTP. |
| [aarushitandon0/a2a-mcp-bridge](https://github.com/aarushitandon0/a2a-mcp-bridge/tree/aee7c44a43eced15d6b3eb78b91b920cd743f6da) | `aee7c44a43eced15d6b3eb78b91b920cd743f6da`, **license unresolved** | MCP HTTP client calls projected per-skill tools; converter invokes official A2A Python SDK. Sealed AES-GCM/CBOR task handles. | Source inspected only. No dependency installation or runtime execution. Not counted as redistributable/wire-verified. |
| [mgcrea/mcp-a2a](https://github.com/mgcrea/mcp-a2a/tree/c4d9d3c57c1746abbf9f6aadd3a9912d464eb1f5) | `c4d9d3c57c1746abbf9f6aadd3a9912d464eb1f5`, MIT | MCP stdio client calls ordinary tools; converter invokes A2A peers and stores a file-backed native task mirror. Also includes an inbound A2A peer daemon. | Build and genuine child-process/loopback send, reread, same-task resume and cancellation passed. |

These are **two independently implemented outgoing mappings**, not two crossing directions. The existence of an inbound daemon in mgcrea is not evidence that arbitrary MCP servers are automatically converted into A2A agents. No inverse converter is invented for a crossing-count comparison.

## Provenance and independence

GitHub API metadata reported `fork=false`, no parent/source repository and `archived=false` for all three. Complete fetched histories had no pairwise shared commit hashes. Searches of source, tests, READMEs and available design notes found no cross-candidate attribution or reference. The converters differ substantively in tool projection, identity storage, runtime language and lifecycle handling. AmirK-S and mgcrea share the official A2A JS SDK family; their bridge mapping code and state stores are distinct.

This supports implementation independence. It cannot prove independent conceptual invention, rule out unattributed copying, or supply an independently authored oracle. The mgcrea eligibility smoke deliberately shares AmirK-S's deterministic A2A fixture for an ordinary reference behavior; it is not independent gold.

Repository activity observed at audit: AmirK-S last push `2026-09-06T05:28:17Z`; aarushitandon0 `2026-08-11T13:27:22Z`; mgcrea `2026-10-09T08:52:26Z`, including dependency/package-manager updates. These timestamps establish recent public source activity, not a guarantee of future maintenance. README maintenance promises were not treated as runtime evidence.

The Python candidate has no tracked `LICENSE` file, no `project.license` declaration, and GitHub's detected license is null. Public availability alone does not supply redistribution permission. Its local checkout is retained for private source inspection; do not bundle its source in a publication artifact. Its dependency ranges are unpinned and no dependency lock is present, which separately prevents an exact installed-runtime claim. The fallback MIT mapping removes the need to count this candidate at the original two-eligible-mapping development checkpoint.

## Pinned protocol profiles and source behavior

**AmirK-S route.** The manifest pins `@a2a-js/sdk 1.1.0`, `@modelcontextprotocol/server 2.0.0`, test client `2.0.0`, `zod 4.2.0`, `typescript 7.0.2`, `tsx 4.23.13` and `vitest 5.0.0`. The source targets A2A 1.0.1 and sends `A2A-Version: 1.0`. It serves MCP `2026-07-28` through discovery and supports legacy `2025-11-25` initialization. The modern route offers `io.modelcontextprotocol/tasks`; the selected wire tests actually exercise it.

The implementation is in [`src/server.ts`](../../external/a2a-to-mcp/src/server.ts), [`src/tools.ts`](../../external/a2a-to-mcp/src/tools.ts), [`src/handles.ts`](../../external/a2a-to-mcp/src/handles.ts), [`src/lifecycle.ts`](../../external/a2a-to-mcp/src/lifecycle.ts) and [`src/tasks/handlers.ts`](../../external/a2a-to-mcp/src/tasks/handlers.ts). Four tools are registered: discover, send, get and cancel. The send input is `text`. Task/context references are bridge-minted in-memory `tk_`/`cx_` handles, with a default 15-minute sliding TTL. Modern task operations are routed ahead of the SDK in [`src/tasks/intercept.ts`](../../external/a2a-to-mcp/src/tasks/intercept.ts). Without the extension, callers receive a plain result and can continue with the task handle; with it, they receive the extension task surface. URL parts become resource links in [`src/parts.ts`](../../external/a2a-to-mcp/src/parts.ts); the bridge does not thereby prove that any receiving principal can dereference an arbitrary link.

The project explicitly omits reverse conversion, push notifications, authentication and other optional surfaces. In-memory handle lifetime and those documented scope limits are profile facts, not newly discovered faults. Failed/rejected/auth-required state mappings and generated fault-command tests must retain their original context; a scripted `vanish` fixture is not a natural external-service failure.

**Python route, source inspection only.** [`src/bridge/server.py`](../../external/a2a-mcp-bridge/src/bridge/server.py) serves only modern `2026-07-28` HTTP JSON-RPC at `POST /`. There is no MCP SDK dependency; field names and response dictionaries are implemented locally. [`src/bridge/discover.py`](../../external/a2a-mcp-bridge/src/bridge/discover.py) projects skills into `{agent_id}__{skill_id}` tools with a required `message` string. [`src/bridge/a2a_client.py`](../../external/a2a-mcp-bridge/src/bridge/a2a_client.py) uses official protobuf A2A `JsonRpcTransport`, `SendMessage`/`GetTask`/`CancelTask`, and header `A2A-Version: 1.0`. [`src/bridge/tasks.py`](../../external/a2a-mcp-bridge/src/bridge/tasks.py) offers task get/update/cancel; handles in [`src/bridge/state.py`](../../external/a2a-mcp-bridge/src/bridge/state.py) bind the agent, A2A task/context IDs and 24-hour expiry under shared keys/configuration. No inference is needed, but exact SDK compatibility remains unverified: the manifest merely says `a2a-sdk>=0.3`, whereas the source imports A2A 1.0 protobuf types. Its checked-in fake agent manually constructs protocol JSON and should not be called an independent official-server conformance test.

**mgcrea route.** Its `pnpm@12.10.1` frozen lock resolves `@a2a-js/sdk 1.3.0`, MCP server/client `2.3.1`, MCP Hono `2.0.2`, `@hono/node-server 2.1.4`, `hono 4.13.13`, `zod 4.6.5`, `tsx 4.23.15`, `typescript 7.0.2`, `tsdown 0.23.0` and `vitest 5.0.3`. The measured **stdio handshake negotiated MCP `2025-11-25`**, with A2A 1.0 JSON-RPC over HTTP. An SDK's support for newer protocol revisions does not establish that a given runtime path negotiated one.

[`src/cli.ts`](../../external/mcp-a2a/src/cli.ts) attaches a genuine stdio server. [`src/tools/index.ts`](../../external/mcp-a2a/src/tools/index.ts) registers mutation tools only when `A2A_ALLOW_WRITES=1`. [`src/tools/writes.ts`](../../external/mcp-a2a/src/tools/writes.ts) maps `a2a_send_message(url,text,task_id?,context_id?)` to A2A and stores a task mirror; [`src/client/peer.ts`](../../external/mcp-a2a/src/client/peer.ts) resolves peer cards and invokes the official SDK. [`src/tools/tasks.ts`](../../external/mcp-a2a/src/tools/tasks.ts) uses `a2a_get_task(task_id,refresh:true)` to obtain remote truth; its default `refresh:false` intentionally reads the local mirror. [`src/client/shape.ts`](../../external/mcp-a2a/src/client/shape.ts) returns summarized states/history/artifacts. This outgoing route uses ordinary MCP tools, not the first candidate's tested modern MCP Tasks extension.

Read-only defaults, explicit refresh and omitted gRPC are documented configuration/design limits. They are not bridge defects. This smoke enabled writes and used a supported JSON-RPC binding. It did not establish arbitrary URI retrieval, credential negotiation, public accessibility, restart behavior or a sound whole-route profile.

## Reproduction and evidence

All commands are local; no global Node/Python packages or shared project `.venv` were modified by this audit. On this Windows environment Node is `C:\Program Files\nodejs\node.exe` (`v22.13.0`). Prepending its directory to the current process's `PATH` permits npm/pnpm child scripts to find it. Standard package-manager caches are local caches, not global installations.

From `external/a2a-to-mcp`:

```powershell
& 'C:\Program Files\nodejs\npm.cmd' ci --ignore-scripts --no-audit --no-fund
& 'C:\Program Files\nodejs\node.exe' node_modules/typescript/bin/tsc -p tsconfig.build.json
& 'C:\Program Files\nodejs\node.exe' node_modules/vitest/vitest.mjs run test/integration/send-message.test.ts test/integration/tasks-extension.test.ts
```

The original tool-return stdout and exit code are retained verbatim in [a2a-to-mcp-upstream-wire.json](bridge-evidence/a2a-to-mcp-upstream-wire.json): **2 files, 42 tests passed**. Both test files start the upstream fixture and bridge on ephemeral TCP ports; [`test/helpers/mcp-http.ts`](../../external/a2a-to-mcp/test/helpers/mcp-http.ts) posts actual HTTP JSON-RPC. These are upstream-authored development tests, not independently sealed cases or a rerun of the entire upstream/conformance suite.

For a standalone source fixture, run `node node_modules/tsx/dist/cli.mjs fixtures/agent/cli.ts --port 0`. Write a configuration such as `{"agents":{"fixture":{"url":"http://127.0.0.1:<fixture-port>"}},"port":<bridge-port>}` and launch `node dist/cli.js --config <config-path>`. The bridge endpoint is `/mcp`. A modern request must put `2026-07-28` in `MCP-Protocol-Version` and `params._meta["io.modelcontextprotocol/protocolVersion"]`, declare `clientCapabilities`, and mirror the method/tool or task ID with `Mcp-Method`/`Mcp-Name`. Do not send a legacy initialization packet and label the response modern.

From `external/mcp-a2a`:

```powershell
$env:PATH = 'C:\Program Files\nodejs;' + $env:PATH
& 'C:\Program Files\nodejs\npm.cmd' exec --yes --package=pnpm@12.10.1 -- pnpm install --frozen-lockfile --ignore-scripts
& 'C:\Program Files\nodejs\npm.cmd' run build -- --config-loader tsx
```

Plain `npm run build` failed because tsdown's automatic loader tried missing optional `unrun`; the existing `--config-loader tsx` option built successfully without modifying upstream source, manifest or lockfile. The first candidate's initial `npm run build` invocation also failed when child `node` was absent from `PATH`; the absolute Node compiler invocation succeeded. These were setup/tooling observations, not converter behavior or experimentally injected bridge faults.

From the workspace root, replay the independent **transport smoke driver**:

```powershell
& 'C:\Program Files\nodejs\node.exe' external/audit-mgcrea-wire.mjs
# Or choose a new filename; an existing file is refused before startup:
& 'C:\Program Files\nodejs\node.exe' external/audit-mgcrea-wire.mjs --output docs/research/bridge-evidence/mgcrea-replay-001.json
```

The driver launches a separate deterministic A2A fixture process, launches mgcrea's built MCP stdio process, and uses the real SDK client over its pipes. A2A requests cross actual loopback HTTP, with no mocked `fetch` or in-memory MCP transport. It avoids personal config/token paths, uses an isolated `external/audit-state` directory, enables writes, disables channel notifications and retries, and closes both child processes. It performs these checked operations:

1. Discover the real MCP tool list; send `task: bridge-eligibility`; refresh the returned task and check its original ID, completed state and expected reversed-text artifact.
2. Send `ask: destination`; observe `input_required` through real refresh calls; answer `Paris` using the same native task/context IDs; refresh to completed and check `destination = Paris`.
3. Create a pending `ask: cancel-me` task and cancel it through the supported tool; check the peer's canceled state.

The [complete version-3 smoke evidence](bridge-evidence/mgcrea-wire-smoke.json) contains the JSON-RPC requests/replies, actual initialization reply, process diagnostics and outcome: **passed, exit 0**. Its exact [driver source snapshot](bridge-evidence/mgcrea-wire-smoke-v3-driver.txt) is archived as text. The [earlier basic smoke](bridge-evidence/mgcrea-wire-smoke-basic.json) passed send/reread. An [initial expanded attempt](bridge-evidence/mgcrea-wire-smoke-v2-initial.json) failed its own premature assertion that nonblocking send would immediately return `input_required`; it correctly returned `submitted`. The current driver polls real task state before dependent operations. The failed development attempt is retained; it is not an adapter defect or a held-out exclusion. The version-4 runner keeps the same behavioral checks and writes a unique timestamped file by default, or a new `--output` path, with exclusive creation; replay cannot overwrite these archives.

mgcrea's upstream tool tests use in-memory MCP transports and a mocked network seam; this audit did not count them as real-wire proof. The passing subprocess driver resolves that specific startup/continuation uncertainty. The common fixture still limits independent behavioral validation.

## Gate implication

Two explicitly licensed converter implementations now have concrete functioning local wire evidence. This passes a **development source/startup eligibility check** for outgoing A2A delegation through ordinary MCP tools. Only the first candidate has selected modern MCP Tasks-extension wire verification, so profiles must retain that difference rather than claiming equal extension support.

The scientific first-week gate is **not passed by this record**. No natural cross-edge witness, independent finite oracle, admission certificate correctness result, or advantage over the same-evidence whole-route reachability comparator has been established here. Documented non-support can supply honest profile/replication cases; it cannot be renamed a newly found defect. Further tests must derive cases from the actual pinned mappings and record injected controls separately.
