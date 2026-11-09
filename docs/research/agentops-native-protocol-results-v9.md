# AgentOps native protocol controls: checked v9 results

Recorded 27 October 2026. These are development controls on the original
application factory and upstream deterministic model double, not bridge runs,
live-model results, a novel method or a qualified second benchmark domain.

The [frozen protocol](source-evidence/agentops-protocol-control-v1/protocol.md)
ran once as two fresh isolated cases, sync then stream. The
[terminal result](../../runs/agentops-native-eligibility/linux-protocol-v9/result.json) reports both controls passed.
The [parent check](../../runs/agentops-native-eligibility/protocol-parent-check-v9.json) recomputes wire/effect checks and verifies
all **1,247 exported files**, historical evidence and the unchanged parent inputs.
Do not rerun `scripts/run_agentops_protocol_wsl_v9.ps1` or completed v8.

| Fixed case | Observed result |
| --- | --- |
| Canonical synchronous `SendMessage` with `A2A-Version: 1.0` | Original task/context completes after the public bound DataPart confirmation; one expected inventory status change and one attributed audit row |
| Canonical `SendStreamingMessage` with that header | Same requirements pass from the complete captured stream and final `GetTask` |
| Identical canonical `GetTask` and confirmation requests with the header omitted | JSON-RPC `-32009` in both cases; no domain effect before the accepted confirmation |
| Agent card with and without the header | Equal card contents; both contain top-level `protocolVersion: "0.3"` while canonical handlers accept the explicit 1.0 profile |
| Cleanup and resources | Both services exit cleanly; expected initialization socket probe remains blocked; no unexpected network attempts, installations or live model calls |

The observed execution interval was `2026-10-27T11:42:05.399185+00:00` through
`2026-10-27T11:48:02.591740+00:00`. This includes capture and export; it is not a
method-performance measurement. The inventory restart changes simulated SQLite
service state, not infrastructure. Synthetic A2A approver identity is not
authenticated human approval. Terminal status or model prose alone is not the
success criterion: the checker also requires the original task/context, bound
confirmation, exactly one complete audit row and no unrelated domain changes.

## Preparation and retained failures

The previous Windows temporary-directory failure remains in
[preparation v1-5](../../runs/agentops-native-eligibility/protocol-preparation-v1-5/result.json).
The unchanged 18 tests passed under the current environment in v1-6. A separate
preparation defect was corrected before any v9 application execution: the
verifier had retained older launch/prerequisite lists. Both preparation and
export checkers now use the same exact seal contract and reject stale or narrowed
software receipts. Ten added regression tests bring the final
[software preparation](../../runs/agentops-native-eligibility/protocol-preparation-v1-7/result.json)
to **28 passing tests**. Original checker/contract bytes are retained in
`runs/agentops-native-eligibility/protocol-preparation-correction-v2/`.

A read-only installed-source inspection pins **150 A2A/ADK Python modules**.
The [new manifest](source-evidence/agentops-protocol-control-v1/manifest-v2.json)
and [pre-execution check](../../runs/agentops-native-eligibility/protocol-preparation-check-v2.json)
bind those modules, tests, scripts, and v8 evidence; the check also compares
module hashes with installed distribution RECORD entries. Earlier preparation
seals and failed attempts are retained. This is evidence consistency checking,
not full runtime/capture authentication, independent semantic validation or
human scientific review.

## Consequence for the next experiment

A no-header card's `protocolVersion` cannot alone determine which canonical
requests the server accepts. Preserve each bridge's actual discovery headers,
request defaults and permitted configuration. The
[bridge profile plan](agentops-bridge-profile-plan-v1.md) separates unchanged
default behavior from explicit header/fetch configuration and keeps every legal
confirmation route in scope. It is an unexecuted proposal; its harness/checker
and prospective seal still need completion before application execution.

Native v9 does not match every typed bridge's nonblocking, polling, Tasks or
callback behavior. Add those matched native controls before interpreting such
bridge results. Do not infer full-interface failure from a text-only send or
count a header intervention as default behavior.

The [C1 effect assessment](c1-agentops-effect-screen-v1.md) finds that these
bindings still fit the established source-recipe comparator; no new algorithm
or performance trial follows from the native result.

CP1 remains passed, CP2 in progress, verified gate credit **5%**. C1 advantage,
whole-route source/model fidelity, unchanged bridge/second-domain qualification,
actual human review, reviewed corpus, frozen evaluations, independent scientific
reproduction and the complete paper remain open. The original distinct-method
objective is unchanged. The user's revised delivery date is **10 November 2026**;
see the [deadline plan](deadline-plan-v2.md).
