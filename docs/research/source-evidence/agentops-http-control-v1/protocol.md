# AgentOps native HTTP control v1

Prepared 26 October 2026. Prospective development control, not an observed
application result. The original v3 in-process test and effect checker must
pass before this control can reserve execution or start its service. No bridge
qualification, method novelty, scientific review or checkpoint credit follows
from preparation or authored checker tests.

The source is the unchanged 421-file AgentOps c806b7f1 archive. The runtime is
the installed recovery environment inspected in v3. Preparation and execution
compare its installed metadata and selected boundary-source hashes. This does
not reconstruct the failed dependency installation, authenticate every installed
file, independently resolve the lock or establish upstream Windows support.

The service imports `_ConfirmationLlm` from the original `tests/test_server.py`
and explicitly reproduces that test's injected Agent configuration: one guarded
restart tool, `validate_actions`, and the callback that records synthetic caller,
session and invocation. It calls the unchanged `agent.server.create_app(agent)`
and runs its real Uvicorn server on 127.0.0.1, default port 18761. This is a
disclosed HTTP fixture, not execution of the unchanged pytest node and not the
full conversational agent. The original model double performs no inference.

Configuration points directly at the immutable source dataset and a fresh
run-specific state directory. Only application startup creates/migrates runtime
state. No direct database copy, repair, reset or restore is performed by this
harness. An application-process audit hook rejects socket connects/binds except
the declared loopback listener and standard-library loopback socketpair setup.
The hook is a Python-level guard, not a claim about OS isolation. Unexpected
attempts fail the control even if a dependency catches the exception.

After the owned service reports startup, the controller captures, once each:

1. GET `/.well-known/agent-card.json`.
2. The original `message/stream` request, `Restart inventory.`.
3. `tasks/get` for the returned original pending task.
4. The original DataPart confirmation, using the returned task, context and
   confirmation identifier and the original fixed rationale.
5. `tasks/get` for the same completed task.

All requests omit `A2A-Version`, matching the original upstream test. This
control records that default behavior only. It does not substitute a legacy
pass for the advertised profile or qualify the bridges' explicit-version
behavior. The actual serialized card interfaces/version are retained; their
relationship to the tested default and the future bridge profile remains a
separate obligation. No alternate version, input or route is tried after failure.

The controller saves exact HTTP/1.1 request/response socket bytes, including
headers and chunk framing, before decoding. It requests connection close and
reads to EOF, bounded to 45 seconds and 32 MiB per exchange. Partial bytes,
failed receipts and process stdout/stderr remain. It does not capture TCP
packets, unrelated connections or network timing suitable for performance claims.
No transport retry occurs. Read-only, transaction-consistent complete domain
snapshots surround every exchange. The original seed remains independently hashed.

The checker does not import the controller, service, app or SDK. It reuses the
small transport decoder and existing seed/row utilities, then separately checks
the request envelopes, original event sequences, task/context/confirmation
bindings, both native query results, six database boundaries and callback
attribution. Before confirmation, all domain contents equal the seed. Afterward,
only inventory's status, one complete attributed audit row and its sequence may
change. Discovery and native queries must have no domain effect. The original
synthetic A2A identity is not authenticated human identity. Two model-double
calls are required. This checker was authored by the same integrating agent;
independent software/scientific review remains required.

These snapshots cannot exclude transient changes restored between boundaries,
prove all session/task database invariants, transaction durability, concurrency,
duplicate-confirmation idempotency or universal behavior. The control is not a
performance trial, held-out task, real infrastructure restart or admission proof.

Preparation imports no application or SDK:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 scripts\agentops_http_control_v1.py prepare
```

After the original v3 control passes, execution uses the frozen plan:

```powershell
powershell -NoProfile -File .\scripts\run_agentops_http_v1.ps1
```

The output is `runs/agentops-http-control/native-http-v1/`. Execution verifies
the native receipt, retained hashes and original effect evidence before reserving
`execution.json`. A reserved attempt is never rerun or overwritten. Service
startup is bounded; shutdown requests are local files, not new application
endpoints. Only the owned child may be force-stopped after its shutdown deadline;
that fails the control. No original source, old receipt or global setting changes.

After real native evidence exists, inspect its advertised binding/version before
preparing unchanged bridge controls and their public alternatives. Whole-route
fidelity, a substantive C1 advantage, independent task validity, frozen evaluation
and actual human review remain open.
