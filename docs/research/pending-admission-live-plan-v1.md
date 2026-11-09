# Fresh native and admitted AgentOps execution v1

This prospective implementation check allocates a **new Linux workspace** and
executes exactly two cases in order: a matched native control (`N11`), then one
configured B7 episode whose continuation is gated by the implemented admission
candidate and independent certificate checker. The B7 case runs only when the
new native control independently passes its public protocol, original-task,
domain-effect, shutdown-diagnostic and owned-process checks. An old success
cannot satisfy that prerequisite.

No application has been launched by preparing this document or importing the
new plan/coordinator. The root operator executes the final launch only after
fresh staging, source checks and software validation. No old resume script,
consumed case directory, seal or source file is overwritten or rerun.

## Fixed cases and admission policy

| Order | New case | Caller | Required observation |
| --- | --- | --- | --- |
| 1 | `admission-live-v1-N11` | Preserved native profile client, `mg-raw-header`, `data` | Original task completes and exactly the required inventory restart/audit effect is independently established |
| 2 | `admission-live-v1-B7` | New admitted client and controller, configured mgcrea raw JSON-RPC route | Current public observations yield a supported certificate; its exact request is dispatched once; actual task/effect evidence is independently checked |

Both cases use the same disclosed upstream confirmation-agent fixture and its
model double. Each receives its own copied/initialized database state, session
state, temporary files, client logs and service process. There are zero live
model API calls. This is a deterministic integration control, not a natural
application workload, held-out study or a newly qualified domain.

The fixed origin is `http://127.0.0.1:18764/`. Limits are 15 seconds per public
request, 30 polls separated by 100 ms, 180 seconds per caller, and 32 MiB of
client response capture. Admission receives 100,000 work units and a 30-second
subprocess timeout. The operational observation window is at most 15 seconds
from the raw pending observation. It is a local policy, not a service lease or
atomic lock. Public tool, discovered endpoint, pending task and raw task are
rechecked before dispatch. Unknown, unsupported, expired, altered or invalidly
certified observations cause zero forwarded continuations. No retry of a
consumed continuation or case is permitted.

The admitted configuration schema is `agentops-admitted-client-config/1`.
It retains the explicit bridge command/environment and adds:

```json
{
  "admission": {
    "python": "<explicit reused Python executable>",
    "budget": 100000,
    "timeout_ms": 30000,
    "deployment": {
      "origin": "http://127.0.0.1:18764/",
      "header_mode": "version-header",
      "serializer": "mgcrea-raw-jsonrpc/1",
      "service_contract": "agentops-inventory-confirmation-fixture/1"
    }
  }
}
```

The client itself allocates a new `client/admission` receipt directory. The
bridge environment enables writes, disables retries, and isolates bridge
configuration/state. The first advertised JSON-RPC interface must have the
configured origin so the origin-scoped `A2A-Version: 1.0` header applies. The
public request does not invent a `headers` tool argument.

## Fresh staging and immutable inputs

Allocate `/var/tmp/agentops-admission-live-v1-<unique suffix>` on the native Linux
filesystem. It must be disjoint from the read-only reused workspace
`/var/tmp/agentops-research-v7-gs9r5her`. Stage all authored top-level `.py` and
`.mjs` scripts and tests, the Python interoperability package, every regular
file in `examples/refinement-development` and `examples/benchmark-development`,
the six pinned documents listed in `PINNED_DOCS` of the new plan module, and
the exact 421 upstream application files selected by the ingestion manifest.
Reject extra/missing application files or source-tree symlinks.

Preparation hashes the staged tests and both fixture directories for export
and reproduction, including the recipe fixture manifest and both benchmark
suite files. Missing required fixture files stop preparation. These fixture
inputs retain their authored development labels and do not become live
application evidence by being packaged alongside the live run.

Reuse these explicit existing runtime locations without relocation, symlink
aliases, installations or metadata edits:

- Python: `<reused workspace>/external/runtime-agentops-linux-v7/venv/bin/python`.
- Bridge packages: `<reused workspace>/external/runtime-agentops-bridges-v1`.
- Node: `/usr/bin/node`, with its executable bytes pinned in preparation.

The old Python editable `.pth` points to old application source. Therefore the
new coordinator sets service `PYTHONPATH` to the staged `scripts`, staged `src`
and staged `external/agentops-c806b7f1/agents/python/src`, in that order. Before
starting either caller it requires the service-ready `source_factory` to point
to the staged `agent/server.py`. It does not call the old root-specific native
validation/resume helpers.

The root staging tool captures a fresh read-only installed-runtime inspection
using the old Python and old `inspect_agentops_runtime_v6.py` with `-I -B`,
writing its JSON into the new group as `python-runtime-before.json`. This
inspects metadata without importing the application. Preparation pins its
referenced executable/provider/selected-source/metadata bytes. Complete Python
runtime authenticity is not claimed. The full bridge runtime bytes and links
are checked against the separately pinned graph and materialization records.
The root also retains a corresponding after-inspection and checks reused input
and historical evidence inventories remain unchanged.

All staged source and code hashes, exact ordered cases, runtime locations,
executables, constants and the before-inspection record enter a new
`agentops-admission-live-preparation/1` plan. A loopback bind probe checks port
availability without a service or application request; it makes no reservation
claim. Any changed prepared input or existing planned case path stops execution.

## Commands after staging

Run from the new Linux workspace. Replace the paths with the allocated absolute
paths; the root operator supplies them, rather than reusing a historical alias.

```text
python3 -B scripts/agentops_admission_live_plan_v1.py --reuse-root /var/tmp/agentops-research-v7-gs9r5her --python-before <fresh>/runs/agentops-admission-live-v1/python-runtime-before.json --output <fresh>/runs/agentops-admission-live-v1/preparation
python3 -B scripts/agentops_admission_control_v1.py --plan <fresh>/runs/agentops-admission-live-v1/preparation/plan.json --preflight-only
```

The separately executed live command is:

```text
python3 -B scripts/agentops_admission_control_v1.py --plan <fresh>/runs/agentops-admission-live-v1/preparation/plan.json
```

The coordinator imports no application until the explicitly invoked service
subprocess begins. Case paths are new directories beneath the fresh root:
`runs/agentops-http-control/admission-live-v1-N11` and
`runs/agentops-http-control/admission-live-v1-B7`. This subtree allows reuse of
the unchanged diagnostic service entrypoint. Group records live under
`runs/agentops-admission-live-v1/attempt`. Existing outputs are refused; failures,
partial captures, skipped cases and unexecuted cases remain in their records.

## Evidence and acceptance

The coordinator retains source/configuration plans, ASGI request/response bytes,
MCP/native journals, initial/final/terminal database observations, application
audit rows, admission input/profile/result/certificate, process-group receipts
and shutdown diagnostics. Only after the caller's owned process group is
confirmed empty does a separate evaluator query the original task; its IDs and
results never become admission inputs.

The preserved service/effect checker must establish original-task completion
and the expected inventory restart/audit transition. The preserved native
checker additionally binds the matched control's configuration and actual wire
profile. The new admitted-client checker validates current public snapshots,
Python source/certificate receipts, exact request dispatch and actual completed
stdin writes. Its task/context must match the independently checked service
task. Positive admission alone earns no live task/effect success.

Strict success additionally requires clean service and caller exits, complete
shutdown diagnostics, initially/finally empty owned groups, no forced cleanup,
unchanged prepared inputs and unchanged original application bytes. If N11
fails any prerequisite, B7 is recorded as skipped. An incomplete or failed
attempt never becomes an inferred success because an earlier version passed.

The [source map](pending-admission-source-map-v1.md) remains controlling for
interpretation: the profile's completion/effect relation is conditional on the
named fixture contract, server history/policy/identity, rationale handling and
successful transactional execution. The one-continuation/working-state rule is
our controller policy, not a blanket SDK theorem. A successful new pair would
establish this bounded integration; it would not establish algorithmic novelty,
general performance advantage, procurement-domain qualification, 70% project
completion, human approval or an extension.
