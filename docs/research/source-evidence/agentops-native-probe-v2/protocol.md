# AgentOps unchanged upstream native-control protocol v2

Prepared 25 October 2026. Prospective, **not executed**. This is development
eligibility for the original method study; it supplies no new C1 method,
domain qualification, human approval or checkpoint credit by preparation.

## Source and application contract

The original commit-labeled archive is `external/agentops-c806b7f1`, verified
against all 421 original regular-file hashes in the v1 ingestion record.
Unexpected added source files/directories or symlinks fail the source gate too.
Archive label coherence is not independently authenticated Git provenance.
Root AGENTS.md was read. Neither original source nor immutable seed is edited.
The application owns runtime initialization/migration. No direct state copy,
restore, reset, deletion or migration is performed by the observer.

The exact original pytest node is
`tests/test_server.py::test_a2a_confirmation_response_resumes_the_guarded_action_with_audit_identity`
(source lines 372-513). Its unchanged assertions require the emitted pause,
original task/context continuation, complete state, original request function,
synthetic caller attribution, rationale/session/invocation/action/target and
two calls of its upstream deterministic `_ConfirmationLlm`. That model is an
explicit offline double. No remote model, credentials, cloud or cluster runs.
This injected original test agent exercises the maintained application factory
and policy; it does not validate the full conversational agent on a live model.

The exact source lock selects CPython 3.13, ADK 2.10.0, A2A SDK 1.1.5 and the
remaining runtime/dev packages. The prepared dependency setup must finish
successfully before `run`. The coordinator compares critical installed versions
to the actual lock, rejects duplicate/out-of-runtime distributions and versions
absent from the lock, and retains full installed-version metadata. This version
check does not authenticate every installed file or independently rerun the uv
resolver. Installed-package byte fidelity remains a later runtime audit.

## Once-only stages

1. `prepare` reads original source hashes and SQLite seed through read-only
   transactions, then creates a new output directory and `plan.json`. It runs
   no pytest collection, application import, application request or setup.
2. After review, `run` requires matching frozen source/observer/protocol/checker hashes,
   matching prepared seed snapshot, an installed Python under the isolated v2
   runtime and the successful unchanged-lock dependencies-v2 receipt. The
   exclusive `execution.json` reserves the attempt. Every failure is retained;
   the attempt cannot be rerun or overwritten.
3. A metadata-only child checks installed versions. One pytest child then runs
   exactly the original node with original strict pyproject warning/config
   rules. Only output/cache/temp paths are redirected into fresh run storage.
   Ambient provider and pytest/Python customization variables are removed;
   plugin autoload is disabled and this single observer plugin is explicit.
   Existing configured runtime network restrictions are not relaxed. A Python
   audit hook rejects application socket connect/bind inside this in-process
   child. The one explicit exception is loopback self-wakeup socketpair creation
   on the exact standard-library socketpair call stack (needed by Windows
   asyncio), separately recorded. Any other attempted socket operation is an
   error even if caught by a dependency. This guard is not an OS sandbox claim.
4. Upstream autouse `isolated_data_dir` makes its normal throwaway dataset and
   runtime-directory selections. The observer only reads those selections and
   verifies both resolve inside this attempt's fresh pytest temp directory.
   No model/application/SDK function is wrapped, monkeypatched or replaced.
5. A main-thread `sys.setprofile` hook observes only the exact original test and
   `_stream_rpc_results` code objects. It captures full helper argument/result
   Python values and consistent read-only SQLite snapshots at helper call and
   return. The test's complete original assertions still execute unchanged.
6. Child stdout/stderr are retained as binary files, with actual command/PID,
   exit code, timeout and hashes. Pytest setup/call/teardown outcomes and JUnit
   output are preserved. A 300-second timeout kills only this owned child and
   retains failure. No time measurement supports a performance claim.
7. The independent checker is separately authored by the integrating agent.
   A zero pytest exit is only `upstream_test_passed_independent_check_pending`.
   Domain acceptance additionally needs that checker and human validity review.

## Passive snapshot contract for the independent checker

`seed-before.json` is a direct pre-run seed snapshot. The plugin additionally
writes `isolated-seed-before.json` after upstream fixtures, before application
startup. Both share the same `database` structure below (as top-level objects).

`passive-profile.json` has schema
`agentops-passive-upstream-observation/2`, exact `nodeid`, `observations`,
`final_test_locals`, `errors`, `network_attempts`, `function_replacements: 0`
and a scope label. The four expected observation records are:

| sequence | rpc_id | event | Boundary |
| ---: | --- | --- | --- |
| 0 | approval-start | helper_call | Startup completed; initial request not sent |
| 1 | approval-start | helper_return | Original initial SSE parser returned; paused |
| 2 | approval-resume | helper_call | Before original confirmation request |
| 3 | approval-resume | helper_return | Original resumed SSE parser returned |

Each record has `sequence`, `rpc_id`, `event`, `observed_at_utc` (UTC ISO8601),
`monotonic_ns`, a deep JSON copy of `payload`,
`results` on return, and `database`. Results are parsed upstream Python values,
**not byte-exact HTTP/SSE transport capture**. The profile neither consumes nor
changes a response. Missing/partial evidence or errors must not pass the checker.

The database object has `path` plus `path_base` (`workspace` for original seed,
`run` for isolated state), sorted `user_tables`, complete sorted SQLite `schema`
rows (`type,name,tbl_name,sql`), `user_version`, `columns` with complete
`PRAGMA table_info` rows, and `tables` with complete rows ordered by primary key.
Read access uses SQLite URI `mode=ro`, `query_only=ON` and one read transaction.
The observer refuses unexpected domain tables. The tables/row columns are:

| Table | Order | Complete row keys |
| --- | --- | --- |
| services | name | name, description, status, owner |
| incidents | id | id, service, title, severity, status, runbook, opened_at, resolved_at, summary |
| audit_log | id | id, schema_version, ts, actor, approved_by, rationale, context_summary, session_id, invocation_id, action, target, detail |
| sqlite_sequence | name | name, seq |

The actual original seed has eight services, ten incidents, inventory `down`,
zero audit rows and empty `sqlite_sequence`; the seed already has current audit
schema/index/triggers. These are direct read-only seed observations, not results
of an application run. The independent checker should require unchanged domain
rows across startup and pending snapshots, exactly one final inventory status
change to operational, one added original-task-attributed audit, only its
expected sequence increment, and no unrelated domain/schema changes. Runtime
session/task DB changes are expected but are outside these domain-table checks.

`final_test_locals` is captured at original test return before fixture teardown:
`task_id`, `context_id`, `rationale`, `seen_contexts`, `confirmation_call`,
`model_calls`. Missing locals on failure stay missing; none is synthesized.
`model_calls` counts the test double, not remote inference.

## Command after preparation/review and dependency setup

From the research workspace, create a new versioned path:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/agentops_native_probe_v2.py prepare --output runs/agentops-native-eligibility/native-probe-v2
```

Only after the unchanged locked dependencies and reviewed preparation exist:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/agentops_native_probe_v2.py run --output runs/agentops-native-eligibility/native-probe-v2
```

No command above was executed as an application control when this protocol was
written. A preparation run is distinguishable by absence of `execution.json`.
Do not rerun the old failed v1 bootstrap or reuse an executed output directory.

## Separate native wire and bridge gates

After this stage, freeze a separately versioned real loopback Uvicorn/control
protocol. Capture actual serialized card and binding/version/extension behavior,
raw native start/pause/get/confirmation/completion bytes, original identity,
source-owned compatibility policy and private domain state. Prefer the exact
upstream factory and original deterministic test double, with its deviation from
the full conversational agent disclosed. No handwritten SDK/handler substitute
qualifies. The source card advertises JSONRPC through supported interfaces and
text modes; installed serialization/accepted wire profile must be observed.

Only then select unchanged pinned bridge controls including permitted structured
and raw alternatives, initial invocation versus continuation failure, independent
task validity and whole-interface coverage limits. This stage alone does not
establish Windows release support, authenticated human identity, idempotent
duplicate confirmation, second-domain benchmark validity, novelty or CP2/CP3.
