# Export archived AgentOps runtime events

The [read-only exporter](../../src/interoperability/agentops_raw_events_v1.py)
captures the six tables and three indexes of the retained ADK/A2A SQLite schema.
It preserves raw JSON column strings, decoded rows, event and session identity,
function-part indices and repeated responses to the same guarded action call.
It imports no AgentOps or SDK code and makes no application or model calls.

This is **evaluator-private archived database evidence**. The active pinned SDK
can separately expose ordinary events in public A2A artifacts. A database
export is not a client observation, an admission input, a complete event stream
or a task grade. The [grading contract](upstream-agentops-grading-contract-v1.md)
defines the remaining public/private and state-checking boundaries.

The database must be an archived, stopped input. This is an external prerequisite;
the exporter does not determine whether its original process has stopped. It
refuses WAL, SHM and journal sidecars, links/reparse points, unsupported schemas,
malformed or duplicate-key JSON, identity mismatches and an existing output.
It opens an unchanged captured copy with SQLite `mode=ro&immutable=1`, runs
read-only integrity/foreign-key checks, and explicitly closes the connection.

The completed first allocation used:

```powershell
python -B src/interoperability/agentops_raw_events_v1.py --database runs/agentops-native-eligibility/linux-bridge-diagnostic-v12/workspace/runs/agentops-http-control/bridge-diagnostic-v1-N11/service/state/runtime.db --output runs/agentops-event-evidence/native-v12-v1
```

The [native-v12-v1 receipt](../../runs/agentops-event-evidence/native-v12-v1/result.json)
passed with seven events, two function calls and three responses. Both responses
to the original guarded action are retained. This allocation is consumed.
`status: passed` proves the export and its preservation checks; it does not
upgrade the historical run. New inputs require a new output allocation.

The [independent AI audit](../../runs/agentops-event-evidence/native-v12-v1-independent-review.json)
passed with zero discrepancies. It reconstructed the raw/decoded table rows and
every function projection, checked eight manifest files, all nine export files
and seven software files, and confirmed the thirteen passing tests. All twenty
monitored files remained unchanged during review. It made no application or
model calls and provides no human acceptance or complete-stream proof.
Failed allocations retain their plan, copied exporter, receipt and any captures.
The source database is checked before and after export, along with copied files.

| Output | Meaning |
| --- | --- |
| `input/runtime.db` | Exact captured database bytes. |
| `schema.json` | Original table and index SQL definitions. |
| `raw-tables.json` | All six selected tables, including unchanged JSON strings and SQLite rowids. |
| `decoded-tables.json` | The same rows with JSON columns decoded. |
| `function-observations.json` | Event/session/invocation identity, author, part index and original function payload. Missing function IDs remain explicitly incomplete. |
| `ordering.json` | Physical row order, timestamp ties/reversals and same-event call batches. No causal order is inferred. |
| `plan.json`, `exporter.py`, `result.json` | Prospective selection, exact exporter source, counts, hashes and preservation outcome. |

The guarded action can have an initial confirmation-required response and a later
executed response under the **same original call ID**. Both remain in the export.
Event IDs and part indices distinguish those observations. Sorting UUIDs or
deduplicating by call ID would corrupt this evidence.

The [final captured validation](../../runs/agentops-event-evidence/software-v2/result.json)
passed thirteen focused tests with zero skips and unchanged original/captured
source. [The preliminary capture](../../runs/agentops-event-evidence/software-v1/result.json)
is preserved: it failed Windows temporary-file cleanup because SQLite connection
context managers do not close connections. Explicit connection closure fixed
the leak, including fixture setup/updates. These suites overlap; do not add counts.
The [tests](../../tests/test_agentops_raw_events_v1.py) use temporary format fixtures
and cover repeated phase replies, identity/schema/JSON drift, ties/batches,
source mutation, sidecar refusal/appearance and output exclusivity.

The proposed N11 input is the original **“Restart inventory.”** fixture. It is
extractor development evidence, not an execution of any of the 21 upstream
cases. The [public observation normalizer](agentops-public-events-v1.md) now
has a separately audited historical export. The [cross-view binder](agentops-event-binding-v1.md)
and [bounded restart effect checker](agentops-restart-effects-v1.md) are also
implemented. The source-case native runner, full trajectory/effect grader,
memory-store checks and independent human review remain open.
