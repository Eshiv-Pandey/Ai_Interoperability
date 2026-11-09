# SDK version-default function control v1

Prepared **24 October 2026 before execution**. This is a prospective **SOFTWARE/SDK CONTROL**, following the [version-default fidelity audit](port-version-default-audit-v1.md). It is neither a new application nor a native/bridge observation, and it supplies no natural-defect, conformance-on-the-wire, efficacy, efficiency or novelty claim. Existing port, bridges, specifications and captures remain unchanged. Integrating-assistant readiness review is complete: the source default, binding-filtered validator and actual semantic-to-JSONRPC mapping were read; driver syntax and checker compilation passed. Execute the four cases once with the checker snapshotted before SDK import.

Use the existing installed official `@a2a-js/sdk==1.1.0` under `external/a2a-to-mcp/node_modules/@a2a-js/sdk`. The actual server bundle `dist/server/index.js` has SHA-256 `57ab549afa0e2cb2bef0de37f88f1ea0192c918b360322232bbd6d30263cd643`. Its builder/context default appears at lines 3417-3447; binding-filtered exact version validation appears at 3673-3692. Call the real exported `defaultServerCallContextBuilder`, `getSupportedVersions` and `validateVersion`; do not replace or mock any validator. A separately labelled call to the actual `JsonRpcTransportHandler.mapToJSONRPCError` may serialize an observed semantic exception, but it is not a received HTTP/JSONRPC error.

The driver [capture-version-default-control-v1.mjs](../../scripts/capture-version-default-control-v1.mjs) constructs a clearly labelled, 1.0-only card. It has exactly one supported interface with `protocolBinding="JSONRPC"` and `protocolVersion="1.0"`; its `.invalid` URL is never contacted. No request handler, executor, transport server, socket, HTTP client, child process, model or credential is used. The code reads local artifacts, imports the official SDK and calls the listed functions. This is not a network sandbox or a test of HTTP header/query parsing.

## Prospective cases

Each case supplies a complete builder options object with the official unauthenticated user and a headers object. Only the `requestedVersion` property differs. For the absent case the property is omitted entirely, rather than assigned `null`; empty and explicit cases carry the matching header string as descriptive local input. The builder stores these headers but does not derive a version from them.

| Case | Builder `requestedVersion` | Source-based effective version | Source-based validation against JSONRPC 1.0-only card |
| --- | --- | --- | --- |
| D1 absent | Property omitted | `0.3` | Semantic `VersionNotSupportedError` |
| D2 empty | `""` | `0.3` | Semantic `VersionNotSupportedError` |
| D3 explicit modern | `"1.0"` | `1.0` | Accept; return value `undefined` |
| D4 explicit legacy | `"0.3"` | `0.3` | Semantic `VersionNotSupportedError` |

Run each listed case once, in this order, after successful setup. Save actual inputs/property-presence, effective requested version, returned value or semantic exception, timestamps and optional official JSONRPC mapping. Preserve all cases even if a source expectation is contradicted. The raw semantic exception has `name`/`reason`/message; do not invent native `code`, `envelopeCode` or `data`. The optional official mapping is expected to yield code `-32009` and an `ErrorInfo` reason `VERSION_NOT_SUPPORTED`; record its actual result separately. A software-expectation result may be checked, but is not a scientific evidence gate.

## Preservation and boundaries

Before any SDK import or case call, create one exclusive attempt directory under `runs/version-default-control/`. Preserve the exact driver/spec/audit/card/case-plan, installed SDK source and license, dependency lock/source ledger, installed SDK and `jose` file manifests, Node executable hash/version, and any root-selected checker snapshots. The ledger records exact file bytes/hashes and precedes execution. Use exclusive creation for all outputs; retain failed setup, unexpected exceptions, contradictions and post-run unreadable/changed-source outcomes. No favorable repeat replaces an unsuccessful attempt.

The run uses one process and starts no server or child. Record that process ID, completion and zero-network/zero-model call inventory; root can check its terminal outcome after command completion. Count the actual direct builder/validator/support-set/mapping calls, not hypothetical HTTP requests. Dependencies and source programs are not modified or installed. The integrating assistant separately implements [check_version_default_control.py](../../scripts/check_version_default_control.py); this is not independent human authorship. It checks actual inputs, returns/errors, call order/count, event records and preserved bytes rather than trusting the driver's pass flags. Preserve complete SDK and jose bytes for archival checks. No full application suite is required for this bounded control.

The official SDK's Express `jsonRpcHandler` adapter is present as source/export. It extracts `A2A-Version` before using the default builder and validates the card before dispatch (`dist/server/express/index.js:3359-3369`). Express is absent from both inspected bridge dependency environments, so unchanged adapter startup has not been established. Root owns any later isolated dependency environment and prospective official-handler fidelity work. This control neither installs Express nor implements another port or a substitute handler.

Successful function controls would verify the installed SDK defaults on these four local inputs. They would not amend R4's historical service-specific result or establish an unobserved failure on a standards-default service. HTTP version query alternatives and whole-interface recovery remain separate unexecuted questions. CP2 remains open and no scientific gate is passed.
