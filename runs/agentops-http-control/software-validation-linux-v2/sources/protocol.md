# AgentOps Linux native HTTP control v2

26 October 2026. Prospective Linux adaptation; no application outcome follows
from implementation or authored validation. The failed Windows native v3 and
the unexecuted HTTP v1 plan remain unchanged. Both preparation and execution of
v2 require a passing original Linux native v4 test and its effect evidence.

## Scope and prerequisite

The application is the original 421-file AgentOps c806b7f1 archive. This
controller imports native v4 helpers and uses that run's isolated Linux runtime.
It verifies native result/plan schema, every retained receipt hash, source and
harness hashes, successful dependency-setup receipt, distinct setup/call/teardown
passes, matching prepared/executed runtime inventories, original seed snapshots,
and the effect-check report's profile/seed binding. It re-runs the separate
semantic effect check on the retained original profile before admitting HTTP.
Status strings alone do not permit execution.

The pinned HTTP modules are located from the verified native runtime's
distribution metadata. Each location must stay inside its venv. The coordinator
may use a different bootstrap Python; its `sysconfig` is not used to select the
runtime SDK. An executable symlink into managed Python does not change which
venv is checked. Preparation captures a new runtime inventory and requires it
to match the passed native inventory; execution repeats that comparison.

This records installed versions, metadata and selected source bytes. It does
not authenticate every installed file or independently resolve dependency
closure. A replica workspace has its own absolute runtime identity; it must run
native and HTTP controls together with matching identities. Exported evidence
does not imply that execution occurred in the destination workspace.

## Unchanged wire semantics

The existing `serve_agentops_http_v1.py` is reused without modifications. It
imports the original `_ConfirmationLlm` and reproduces the original injected
Agent configuration, then calls the original factory and runs Uvicorn on one
loopback port. This is a disclosed HTTP fixture, not the unchanged pytest node
or the full conversational agent. The model double makes no live model call.
Its network audit guard and immutable seed/fresh state behavior are unchanged.

The five once-only exchanges remain: card discovery, original start request,
pending `tasks/get`, bound DataPart confirmation, completed `tasks/get`. Six
read-only transaction-consistent domain snapshots surround them. Pending-task
verification must pass before confirmation. All requests omit `A2A-Version`, as
the original test does. There is no alternate header, route, input, port or retry
after failure. The advertised card/version is retained separately from default
request behavior; this alone cannot qualify an explicit-version bridge.

The original raw HTTP capture and separate wire/effect checker are reused. Their
plan/service payload schemas remain `/1` because the semantic contract has not
changed. The new plan additionally requires
`controller_version: agentops-http-control/2`, a native-v4 prerequisite digest,
and a separate output path. Execution and result records use `/2`. A v1 plan
cannot be executed by this controller.

The checker verifies complete envelopes and event sequences, original task,
context and confirmation identity, both queries, two deterministic model-double
calls, callback attribution and exact boundary effects. Only the approved
inventory status, one complete audit row and its sequence may change. The
synthetic identity is not authenticated human identity. Boundary snapshots
cannot exclude transient reverted changes or prove concurrency, durability,
all session/task state, or duplicate-confirmation idempotency.

## Linux execution

After actual native v4 success, from the same Linux workspace:

```bash
python3 -B scripts/agentops_http_control_v2.py prepare
python3 -B scripts/agentops_http_control_v2.py run
```

The default output is `runs/agentops-http-control/native-http-linux-v2`, port
18761. `--output` must remain inside the HTTP runs subtree. `--port` is selected
at preparation, then frozen. Preparation creates its directory exclusively and
retains a failure result if runtime inspection fails. Execution refuses any
existing reservation and revalidates its completed preparation and unchanged
native prerequisite before reserving `execution.json`.

The service runs in an owned Linux process group. Local stop-file requests
allow normal shutdown; deadline expiry force-stops that group and fails the
control. Cleanup errors are recorded so stream closure and result writing can
continue. Raw requests/responses, partial captures, process streams, snapshots,
checker receipts and failures remain. The capture is bounded HTTP byte evidence,
not TCP packet capture or a performance study. No source, seed, old attempt,
global setting, system package or cloud resource is modified.

## Validation boundary

The new authored tests exercise positive retained-native evidence, stale/missing
or resealed-invalid receipts, platform rejection, package locations, once-only
reservation, cleanup errors and compatibility with the unchanged wire checker.
They import no application or SDK and do not start WSL, a service or an HTTP
exchange. Actual Linux native and HTTP execution remain required before any
application claim. The separate AI code review is not independent human
scientific review. Bridge qualification, second-domain validity, C1 novelty,
frozen evaluation and human review remain open; no gate credit is added.
