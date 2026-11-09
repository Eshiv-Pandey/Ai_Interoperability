# AgentOps native protocol-profile control v1

Prospective development control, 26 October 2026. Actual execution is pending.
Prerequisite: passed v8 native/HTTP capture and its retained-evidence parent check.
This package adds two fresh cases in the already installed Linux v7 workspace.
No installation, model inference, bridge modification, or new domain qualification.
The initial preflight seal is retained as `manifest.json`; coordinator cleanup
and complete version-dispatch source pinning are corrected in `manifest-v2.json`.

## Fixed cases and sequence

Run `sync` then `stream`, each once, in isolated fresh state. The same unchanged
`serve_agentops_http_v2.py` fixture starts the original factory and upstream
deterministic model double, with one local listener (18762/18763 respectively).
The source seed remains immutable. The source, installed protocol-module bytes,
controller, checker and original prerequisite are verified before execution.

1. GET original card without a version header.
2. GET original card with `A2A-Version: 1.0`.
3. Send `Restart inventory.` through `SendMessage` (sync) or
   `SendStreamingMessage` (stream), canonical parts and `ROLE_USER`, with header.
4. `GetTask` with header, using the public original task identifier.
5. Identical `GetTask` payload without header.
6. Send the original task/context and public `adk_request_confirmation` call ID
   as a canonical data part, `adk_type: function_response`, `confirmed: true`,
   and the original rationale, without header.
7. Send the **identical** RPC/message payload with header.
8. `GetTask` with header, checking original-task completion.

The synchronous configuration is the SDK default blocking behavior. The
streaming case waits for the complete response. These do not yet match every
bridge's polling/Tasks/callback configuration; those require separate controls.
Raw HTTP requests are authored native controls, not bridge executions. The
omitted-header probes use the same method as their positive case; mgcrea raw
exposes only `SendMessage`, not `SendStreamingMessage`.

Snapshots bracket every request. Expected behavior: no domain effect until
step 7; exactly one inventory status change and one completely attributed audit
row; original task/context completes; no unrelated domain changes; two offline
double calls; socket initialization probe blocked and service shut down cleanly.
Both no-header canonical RPCs are expected to return JSON-RPC -32009. Record
their actual HTTP status and complete error. A contrary result fails this fixed
control and is retained; it must not be patched, retried or excluded. If step 6
changes the domain, stop before step 7 to avoid duplicating an effect. Malformed
or absent captures fail checking. Incomplete observations never imply unsupported.

All wire bytes, framing, partial responses, stdout/stderr, runtime inventory,
source hashes, snapshot times, subprocess argv and cleanup receipts are retained.
Network requests are bounded at 45 seconds/32 MiB, the service retains its
240-second watchdog, and supervision retains failed or timed-out cases. A second
independent case may run after a failed first case only after confirmed cleanup.
Export the new and historical evidence without rewriting any older run.

## Scope and interpretation

The card helper merges protobuf and backward-compatibility fields independent
of the request header. Thus top-level `protocolVersion: "0.3"` is not sufficient
to infer absence of canonical handlers. The card comparison is reported, not
silently normalized or replaced. Canonical 1.0 success, if observed, establishes
only these native fixture profiles. It does not establish whole-bridge support,
non-support, model behavior, a distinct method, or human task validity.

The public confirmation structure is an ADK convention. Text-only paths cannot
be judged by assuming text is parsed into a FunctionResponse: inspect converter,
runner and every permitted bridge alternative. The full conversational agent is
outside this offline fixture. Any later bridge experiment must preserve source
pins, actual discovery headers, legal peer/URL/metadata options, task handles,
polling/Tasks/streaming behavior and default-versus-explicit version behavior.

Verified project credit stays 5%. C1 and scientific gates remain open.
