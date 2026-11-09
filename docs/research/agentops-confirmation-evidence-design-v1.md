# Historical restart confirmation evidence check v1

29 October 2026. The immediate implementation is a small, evaluator-private
consistency check for the original `confirmation_test_agent` fixture whose
user text is `Restart inventory.`. It checks linked confirmation phases and
an attributed business-state delta. It does not grade any of the 21 unexecuted
upstream cases, establish a new admission-method contribution, or replace the
existing native task/process qualification checks. The broader
[upstream grading obligations](upstream-agentops-grading-contract-v1.md) remain
open.

## Inputs and byte binding

Use a passed [raw-event export](../../runs/agentops-event-evidence/native-v12-v1/result.json),
its `decoded-tables.json`, `function-observations.json`, `ordering.json`, and
captured `input/runtime.db`. Use a separately passed or explicitly partial
[public wire export](../../src/interoperability/agentops_public_events_v1.py),
its `observations.json`, and copied `wire/NNNNNN/` files. Recompute each selected
receipt hash and byte count before use; preserve inputs and membership after
checking. A receipt's `status` alone is insufficient. Reconstruct used function
observations from the decoded raw event parts, or independently check each
projection against those parts. Do not accept altered derived JSON just because
its contents look plausible.

The original N11 source wire root is:

```text
runs/agentops-native-eligibility/linux-bridge-diagnostic-v12/workspace/runs/agentops-http-control/bridge-diagnostic-v1-N11/service/wire
```

Its pending snapshot is sequence `000006`; its approval request and business
delta are sequence `000007`. B7 uses pending `000005` and approval `000006`.
These sequence numbers describe the inspected archives. A future checker must
select the approval exchange from its actual linked request, rather than assume
every input has the same fixed sequence numbers.

ASGI captures are server-observed protocol bytes. They do not prove that a
particular client received every response. The copied before/after snapshots
and raw SQLite evidence are evaluator-private and must not become admission
inputs. Keep actual request content and source/run identities; do not assign
an upstream case ID to this fixture.

## Task and runtime association

`decoded-tables.json` maps table names to row lists. For this limited fixture,
require one selected Task, one associated session, one invocation, the original
user event, and no unrelated function records within that selected scope.

- `tasks[i].id` is the original A2A task ID; `tasks[i].context_id` is its context.
- `tasks[i].metadata.adk_session_id`, `adk_user_id`, and `adk_app_name` must match
  `sessions[j].id`, `user_id`, and `app_name`.
- Every used function observation must have the same `app_name`, `user_id`,
  `session_id`, and `invocation_id`, matching its raw event envelope.
- The raw original user event has `event_data.author == "user"` and the actual
  `content.parts[].text == "Restart inventory."`. Retain that event ID.
- Public `task_context_associations` and the actual returned Task bodies must
  agree with that original Task/context. The approval SendMessage carries the
  same `message.taskId` and `message.contextId`; a replacement task fails this
  association check.
- The final stored Task and observed final Task reply must both be completed.
  Completion text alone cannot satisfy the state or effect checks below.

The inspected native identity is synthetic `A2A_USER_<context-id>`, not proof
of an authenticated human approver. Report the actual identity without
upgrading its assurance.

## Preserve and pair five function phases

Select phases by function name, ID and runtime scope, not list position or
SQLite rowid. Require exactly one of each phase for this fixture. Additional,
ambiguous or missing phase evidence must remain inconsistent or unknown.

| Phase | Exact evidence fields and relation |
| --- | --- |
| Original action call | `kind == "function_call"`; `function.name == "restart_service"`; nonempty `function.id`; `function.args == {"name": "inventory"}`; author is the selected fixture agent. |
| Preliminary action reply | `kind == "function_response"`; same original function ID/name; response is the observed confirmation-required error, without success/audit. Preserve it instead of treating it as the executed result. |
| Confirmation call | `function.name == "adk_request_confirmation"`; distinct nonempty ID; `function.args.originalFunctionCall` exactly matches the original action call; `toolConfirmation.confirmed is False`. |
| User approval response | Same confirmation ID/name; author is `user`; `function.response.confirmed is True`; payload contains a nonempty text `rationale`. Match it to the actual approval request's data part, not an evaluator-synthesized answer. |
| Executed action reply | Same original action ID/name; response contains the expected restart outcome and an `audit` object, without an error. The audit must match the state delta below. |

The normalizer's function observation fields are `event_id`, `part_index`,
`function_id`, `kind`, `function`, and the runtime identity fields above.
Use `(event_id, part_index)` to bind a phase to its raw ADK event. Public
artifact observations expose the same event identity through
`container.metadata.adk_event_id`; their payload is `part.data`. Confirmation
request/response parts can instead occur in public Task status/history or
the outgoing approval request. Preserve the actual representation and its
wire sequence.

The original action ID legitimately has two response events: preliminary
confirmation-required and later executed. A one-response-per-call rule, or
keeping only the last response, is incorrect. Repeated task polls are repeated
observations, not additional calls or effects.

## Pairing is distinct from order proof

The inspected raw export records a physical-row timestamp reversal: the
confirmation call occupies rowid 3 and the preliminary reply rowid 4, although
their event timestamps put the preliminary reply first. Do not reject this
valid archive merely because rowid order reverses, and do not redefine rowid
as causal order.

The selected phase timestamps can be checked for strict increasing relations
between original call, preliminary reply, confirmation, user approval and
executed reply. Report that as a timestamp consistency check only. Equal or
contradictory timestamps are unresolved for this check. Regardless of whether
the relation holds, retain `causal_order_proven: false` and
`complete_event_stream_proven: false`. The linked contents and observed
approval exchange establish a narrower consistency result; they do not prove
the full internal scheduling history or the upstream sequential-read obligations.

## Business effect and audit fields

Each copied snapshot has `observed_at_utc`, `monotonic_ns`, and `database`.
The database object has `path`, `path_base`, `user_tables`, `schema`,
`user_version`, `columns`, and `tables`. Compare its logical contents, not the
outer observation timestamps. Schema, columns and unrelated database metadata
must stay unchanged.

For N11, the following actual paths contain the paired transition:

```text
wire/000007/request.body.bin
wire/000007/exchange.json
wire/000007/before.snapshot.json
wire/000007/after.snapshot.json
```

Require these exact logical differences:

- `database.tables.services`: only the row with `name == "inventory"` changes,
  from `status == "down"` to `status == "operational"`. Its other columns and
  all other service rows are equal.
- `database.tables.incidents`: every row is unchanged.
- `database.tables.audit_log`: all prior rows are unchanged and exactly one
  new row is present. Require `action == "restart_service"`,
  `target == "inventory"`, `actor == "agentops-agent"`, `schema_version == 1`,
  actual `approved_by == user_id`, actual `session_id` and `invocation_id`,
  a fresh audit ID, the nonempty approval rationale, and the expected context
  and detail. The current fixture context is
  `service inventory was down; open incidents: INC-002`; its detail is
  `service restarted and marked operational (mock)`.
- `database.tables.sqlite_sequence`: only the audit-log sequence advances to
  the new audit ID; no unrelated sequence changes.
- All preapproval exchange snapshots preserve the baseline business state.
  Later captured wire snapshots preserve the postapproval state. A missing
  snapshot or unexplained intervening mutation is not a passing observation.

Match the executed reply's audit to this appended row. The pinned guardrail
wraps `rationale`, `context_summary`, and `detail` in the exact spotlight prefix
and suffix; persisted audit text is plain. For this clean-text fixture, compare
the response fields with that declared wrapping of the stored fields. Do not
strip arbitrary delimiters or assume that all future PII/injection transforms
are identity operations. Public protobuf JSON can represent audit integer
fields as integral floats; permit that declared numerical representation only
for the known integer audit fields, reject booleans, and retain the raw values.

The original audit clock truncates its UTC timestamp to whole seconds
(`data.py:461-463`), while captures retain finer ISO timestamps. Treat its declared
precision as an interval: a wholly bracketed audit interval is consistent,
a disjoint interval is inconsistent, and an interval that only overlaps the
captured approval exchange and before/after bracket remains unknown. These
are capture consistency checks, not proof of timestamp precision or an
authoritative service clock.
A last wire snapshot is not a terminal process observation. Terminal state
preservation, process exit and cleanup require their own retained evidence.

## Output and next-step boundary

Return separate results for raw-byte binding, fixture association, phase
linkage, timestamp consistency, public/private payload agreement and the
business/audit delta. Use `consistent`, `inconsistent`, or `unknown`; keep
missing evidence explicit. Set `graded_upstream_cases: 0`,
`new_native_runs: 0`, `causal_order_proven: false`, and
`qualification_established: false` for this historical checker.

This gives the future source-case runner a tested pairing/effect boundary.
It does not create observed read results, a source-grounded model for those
reads, live admission success, a substantive second domain or human acceptance.
No code, tests, application imports or live calls were performed for this note.
