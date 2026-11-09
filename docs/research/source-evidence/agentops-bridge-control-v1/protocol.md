# AgentOps matched native/bridge control v1

Prospective development protocol, 27 October 2026. No case has been executed
when this file is prepared. The final manifest binds this file, exact software,
test receipts, retained v9 prerequisite and relocated runtime before launch.
This is eligibility/fidelity work, not a C1 performance study or held-out corpus.

The original AgentOps factory and imported upstream deterministic confirmation
model double are unchanged. A separately versioned wrapper records ASGI entity
bytes and read-only SQLite snapshots. This observes parsed HTTP fields and body
chunks; it does not capture TCP framing and adds local I/O overhead. No timing
or speed advantage is claimed. Original source and pinned dependency bytes are
preserved. The effect is simulated service state in SQLite, not infrastructure.

## Fixed allocation and prerequisite rules

Run N1-N11, then B1-B7 in this order, once each, with fresh fixture/model, domain
state and bridge state. All eighteen cells remain in the attempt ledger,
including skipped, partial and failed cases. Native positive controls are
required before dependent bridge cells; a missed prerequisite is recorded as a
skip, not replaced by a more favorable trial. A process timeout or unconfirmed
cleanup stops subsequent launches. A completed contrary result is retained.

| Cases | Native profile | Fixed continuation |
| --- | --- | --- |
| N1, N2, N3 | Amir SDK 1.1.0 default blocking `SendMessage` | Literal, JSON text, DataPart respectively |
| N4, N5, N6 | Amir SDK 1.1.0 `SendStreamingMessage` | Literal, JSON text, DataPart respectively |
| N7, N8, N9 | mgcrea SDK 1.3.0 polling, accepted output modes text/plain and application/json | Literal, JSON text, DataPart respectively |
| N10 | mgcrea typed/polling prefix, raw canonical `SendMessage` continuation without version header | DataPart |
| N11 | Same prefix, raw canonical `SendMessage` with `A2A-Version: 1.0` | DataPart |

Native callers acquire task/context and the confirmation call from actual public
SDK responses. The three representations share the start `Restart inventory.`
and rationale `Inventory is down and INC-002 matches the service-down runbook.`
The literal answer is exactly:

`Yes, confirm the inventory restart. Rationale: Inventory is down and INC-002 matches the service-down runbook.`

JSON text is the serialization of
`{id: <public confirmation ID>, name: "adk_request_confirmation", response: {confirmed: true, payload: {rationale: <fixed rationale>}}}`.
The DataPart carries the same object and part metadata
`{"adk_type":"function_response"}`. Numeric SDK user role and actual installed
codec/configuration behavior are checked without application requests before
freezing. Raw controls carry canonical JSON, no SDK-added configuration, and
use the same request shape with the stated header difference. Fresh task,
context and message identifiers differ between these isolated cases; they are
not claimed to be identical request bytes across resets.

| Case | Bridge path | Native positive prerequisites |
| --- | --- | --- |
| B1 | Amir ordinary tools, no Tasks or elicitation capability | N3 |
| B2 | Amir negotiated Tasks path, including its advertised streaming behavior | N6 |
| B3 | Amir MRTR/form continuation with echoed opaque request state | N3 |
| B4 | mgcrea stock CLI typed send and authoritative refresh | N9 |
| B5 | mgcrea stock CLI typed prefix, permitted raw request alternative | N9 |
| B6 | mgcrea public library factory over stdio, passthrough fetch | N9 |
| B7 | Same embedding as B6; fetch adds the version header only for this local origin | N9, N11 |

The detailed public-interface inventory is the
[bridge profile plan](../../agentops-bridge-profile-plan-v1.md). B6/B7 are
explicit library deployments; B7 is a configuration intervention and cannot be
reported as default CLI behavior. No source bridge code is modified.

## Public information and prospective correction

Source inspection during preparation found that some bridge projections omit
the structured confirmation ID. This corrects the earlier plan's assumption
that every typed pending response would supply it, before observing any case.
Every caller binding must point to an actual MCP response sequence and field,
including explicit decoding of JSON-in-text when applicable. Opaque handles and
MRTR state are echoed through their documented inputs, not decrypted or replaced
with the private origin IDs recorded by the observer.

B1-B4 use the fixed JSON text only if the required confirmation ID is publicly
available. Otherwise they make at most one permitted literal-answer attempt,
labelled as a literal fallback. B5/B6 first try permitted raw `GetTask` after the
typed pending prefix. If that does not reveal the binding, record
`public_binding_not_observed` and do not fabricate or import an ID for a raw
confirmation. B7 may obtain its binding through its header-configured raw read.
Absence in these bounded observations is not universal non-support. Legal
string guesses, other URLs/deployments and other permitted alternatives remain
explicit broader-coverage obligations, not silently excluded facts.

## Capture, grading and bounds

All cases use loopback AgentOps port 18764, with Amir MCP at 18765. Sequential
reuse requires the preceding owned services to have exited. Each case gets
fresh state/config directories and no inherited credentials, token or channel.
The existing Python environment is reused; the Node dependency closure is
copied from pinned installed bytes, with no package installation or build.
Node executable/version and all package resolution edges/files are pinned.

Freeze limits: 15-second client request timeout, 100-ms poll interval, at most
30 polls per wait, 180-second client episode deadline, 32-MiB response cap.
The server observer caps each body at 32 MiB and the case at 256 HTTP requests.
The fixture watchdog is 300 seconds; the controller bounds startup at 65
seconds and client lifetime at 220 seconds, retaining partial streams on error.
An outer 480-second supervision deadline handles unexpected controller failure.
These are development bounds, not service expiry assumptions.

The server records complete/partial request and response bodies, supplied
headers, streaming chunks and boundaries around every actual A2A request.
The client records exact MCP bytes and public binding provenance. After that
client exits, a grader-only `GetTask` targets the origin task identified from
the private initial wire response. Its ID is `evaluator-final`; its response is
never fed to the caller. Snapshot again before stopping the service and after
its confirmed exit, so late background effects remain visible.

Report evidence validity, capture completeness, task state, prose, approval
representation and actual domain effect separately. Strict success requires
original task/context completion, lawful bound approval, the intended inventory
change, exactly one fully attributed audit row, no earlier/unrelated changes,
and clean capture/cleanup. Success prose or a terminal task alone is insufficient.
Valid contrary effects and API errors remain observations; malformed or partial
evidence produces unknown, never an impossibility claim. The independent
checker implementation does not make this an independent human/oracle review.

Preserve every attempt, original source, v8/v9 results, failed preparation,
pre-execution seal, runtime graph/archive, raw captures and analysis/checker
outputs. No selective reruns, favorable replacement controls or inference.
CP2, method novelty, second-domain qualification and human review remain open;
this control alone adds no scientific checkpoint credit.
