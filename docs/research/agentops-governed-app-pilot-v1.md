# Original AgentOps governed-App development pilot

This prospective pilot executes d01 health/active incidents and d03 unconfirmed
restart through the original AgentOps conversational App, policy plugin, A2A
executor, SDK task store and persistent ADK session service. The pinned original
commit is `c806b7f1cd0042c9817c0a4c46d80a9a95a24293`. No original function body,
policy callback, PII mechanism, database seed or bank-v1 record is edited.

The declared intervention replaces only the original selected root's model
object with a deterministic public-task recipe. The original root gains an
observational before-tool callback that returns `None`. Original tool responses
and dependent arguments pass through the original policy/PII callbacks. The
actor sees its public task and actual model input; the private evaluator runs
after the actor processes finish. A Python audit hook denies evaluator-file
opens and socket operations. This hook is instrumentation, not an OS sandbox.

The request transport is Starlette TestClient ASGI. The pilot does not establish
native-network execution, provider-model performance, a new admission gate
application integration or independently qualified held-out task performance.
Its scope is actual original-App reference execution and actual SDK task
completion/pause with retained raw state and identity evidence. A structural
pass leaves human gold judgment and full bank qualification pending.

Each case uses a fresh exclusive copy of original data and a separate absent
state directory. d01 submits the exact public prompt including `" INVENTORY "`;
the actor derives the final health/incident response from the observed tool
response. d03 awaits the original incident, returned-service health, unfiltered
logs and returned-slug runbook reads in separate model steps. Its finite recipe
requests restart only when those responses agree, the incident is unresolved,
the service is nonoperational and the returned runbook includes restart
guidance. The SDK must generate the actual confirmation request. No approval
is sent, and the evaluator checks business state remains unchanged.

The hosted workflow uses Ubuntu 24.04 x86_64 with at least 2 GiB MemAvailable,
the preserved source archive checksum, original UV 0.12.0 checksum and original
`uv sync --locked` dependency selection with Python 3.13.1. This is a separate
host profile; it does not reinterpret the unsuccessful local Windows resource
gate. All 421 original source files must remain byte-identical after sync and
execution. Provisioning and task subprocesses have fixed deadlines.

Evidence includes exact public request/SSE bytes, decoded RPC events, actual
model inputs/outputs, actual user/session/invocation tool contexts, original
before/after database tables, closed SQLite copies, SDK `tasks/get` bytes,
subprocess streams/receipts, runtime versions and source/input manifests.
Allocated failures remain retained. The uploader preserves the artifact even
when the workflow fails.

Run the no-SDK preparation controls:

```powershell
python -B scripts/check_agentops_governed_app_pilot_v1.py
python -B scripts/ci_agentops_governed_app_pilot_v1.py --check-inputs
```

Execute `.github/workflows/agentops-governed-app-pilot.yml` on the selected pushed
research revision. A result is established only by the resulting retained raw
capture and a separate evaluator/reviewer. This document itself claims no
completed application task.
