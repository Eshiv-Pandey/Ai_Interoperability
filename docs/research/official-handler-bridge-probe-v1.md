# Official-handler bridge fidelity probe v1

Prepared 24 October 2026 before the new bridge/service cases. This is a bounded
SOFTWARE/BRIDGE FIDELITY CONTROL, not C1 novelty, a second application domain,
natural failure prevalence or human scientific review. The original method
objective and 5% checkpoint credit remain unchanged.

## Fixed service and unchanged mappings

Reuse the installed official @a2a-js/sdk 1.1.0 Express jsonRpcHandler,
DefaultRequestHandler, InMemoryTaskStore and default context builder; no
contextBuilder, version override or legacy compatibility. Reuse unchanged
CarolReferenceExecutor (b6b6492ee5c27cf5db0474054b0f18a8feafe0859d9faaa4fd67946c7768626d)
and an expressly authored 1.0-only JSONRPC card. Mount the official card handler
at /.well-known/agent-card.json and the official RPC handler at /a2a, on an
ephemeral 127.0.0.1 server. The earlier authored HTTP wrapper is never started.
The executor remains an authored 1.0 port of an upstream demonstration.

Bridge pins stay AmirK-S/a2a-to-mcp 58eff9da469bccdc432bf164662727947de646b4
(Apache-2.0) and mgcrea/mcp-a2a c4d9d3c57c1746abbf9f6aadd3a9912d464eb1f5
(MIT). These are two outgoing mappings, not inverse crossing directions.
No mapping, SDK, dependency, serializer, card URL or request header is repaired.

## Once-only variants and controls

| ID | Actual caller path | Fixed answer action | Source-based expectation |
| --- | --- | --- | --- |
| B1 | Amir modern MCP HTTP ordinary tools | typed same-task/context text | 1.0 transport accepted; empty references leave task input-required |
| B2 | Amir modern MCP HTTP Tasks extension | accept the actual string elicitation form via tasks/update | 1.0 transport accepted; same source reference obstruction |
| B3 | mgcrea MCP 2025-11-25 stdio, writes enabled, retries=0 | typed same-task/context text | SDK version header accepted; empty references leave task input-required |
| B4 | Same mgcrea profile | allowed raw SendMessage with public original IDs and nonempty references | raw fetch lacks version header; official handler rejects before executor |

Use a fresh isolated server and bridge child per variant. Native cases N1-N3
run once before bridge startup: header-1.0 initial SendMessage, source-valid
same-task/context answer with references, and header-1.0 authoritative GetTask.
All three must succeed for that variant's native eligibility. They use a
separate original task, never the bridge task. The initial text is
{"action":"shuffle","history":[{"guess":25,"response":"Go higher"}]};
the answer is Well done!. One history entry avoids meaningful shuffle variation.
Native N2/N3 bindings come only from N1's response.

The fixed bridge actions reuse the prepared historical R1-R4 client routines,
without a behavioral edit. Discovery lists the full tools before execution.
Initial typed SendMessage must yield public bindings; bounded reads establish
pending state and the original one-entry artifact. Make one selected answer
attempt and one final bridge read (plus the existing Tasks record read in B2).
B4's final read is the allowed raw GetTask, which is also expected to be rejected.
An MCP error return is retained as an outcome; it is never a completion receipt.

After bridge actions, evaluator-only E1 performs one header-1.0 GetTask for the
task created by that variant's initial bridge request. The identifier is
correlated from captured native response bytes and is NEVER given to the
bridge caller or used as a recovery action. E1 establishes authoritative
original task/context state even when B4 cannot read it via raw RPC. It does
not establish agent-visible reachability or a supported recovery policy.
If there is no identifiable initial bridge task, E1 is unexecuted with reason;
do not invent it or repeat the initial send.

All bridge/native requests use genuine HTTP or stdio. No network beyond loopback,
inference, solver comparison, repair, query-only alternative, token use, extra
bridge or benchmark episode is introduced. The three native controls and E1
are charged separately from actual MCP and bridge-to-A2A exchanges.

## Preservation, checking and stop rules

Use exclusive attempt/output paths. Freeze this specification, capture/helper
routines, separate checker, provenance/attribution, bridge source/dist and
installed direct-runtime package manifests plus the complete official HTTP
environment before service imports/bridge startup. Preserve those bytes for
replay; hash dependencies and sources again after execution. Record Node
identity, actual child process lifecycle, dynamic loopback configuration,
client/native entity bytes, explicit headers, server-ingress headers/body,
public MCP bindings and evaluator-only E1 separately.

The unchanged read-only preload retains its historical authored-port labels;
the new report must override the actual service classification and say these
labels are inherited logging terminology, not evidence of the old wrapper.
Server ingress is additional authoritative evidence of headers delivered to
the unchanged official handler. Instrumentation never adds headers or fields.

The checker must be authored before these new captures, use no SDK/driver
imports, derive conclusions from retained raw entities, distinguish HTTP-500
version exceptions from HTTP-200 positive responses, verify public binding
provenance and same-task/context E1 association, and reject altered artifacts,
references, version headers, HTTP status, order, costs, lifecycle and snapshots.
It may reject an unexpected result as a retained deviation, never justify rerun.
AI-authored separate logic does not count as human novelty/feasibility review.

Run every variant once, retaining every setup/observation/checker failure.
After a failed native control or absent public prefix, record dependent actions
unexecuted and keep their failure reason. Continue independent variants.
Close actual bridge children via their unchanged shutdown handler, await actual
exit, close all server connections and await listening=false. Archive replay
checks these same records without starting the SDK, server or bridge again.

## Interpretation boundary

B1-B3 waiting would reproduce the serializer restriction under a verified
official transport. B4 rejection would disqualify a generic raw-recovery claim
for this exact handler/profile, despite the historical permissive-wrapper
positive result. Neither outcome demonstrates a novel admission algorithm or
a previously undocumented general systems contribution. An actual second
domain and scientific review remain missing; the applied-only route is not selected.

