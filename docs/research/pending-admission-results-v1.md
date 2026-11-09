# Public pending-task admission controller: implementation results v1

29 October 2026. The admission candidate is now connected to a public pending-task controller and a standalone MCP stdio client. **83 focused software tests passed**: 57 Python tests (25 adapter plus 32 solver checks) and 26 controller/client tests. Both JavaScript syntax checks passed. A retrospective check on actual retained B7 public bytes produced a valid certificate and exactly matched the historical continuation request.

Update: the [fresh native/admitted integration attempt](pending-admission-live-results-v1.md) executed its native prerequisite, which failed shutdown acceptance; B7 was therefore skipped. No fresh admitted task has completed. The evidence below remains software behavior and historical request equivalence.

## Implemented flow

| Component | Implemented behavior | Evidence |
| --- | --- | --- |
| [Public-state adapter](../../src/interoperability/pending_admission.py) | Binds tools, advertised endpoint, task/context, pending confirmation, original inventory operation and explicit deployment to a recipe profile | [Python tests](../../tests/test_pending_admission.py) |
| [Admission controller](../../scripts/agentops_admission_controller_v1.mjs) | Calls the candidate/checker, accepts only the exact certified request, rechecks public state/configuration before sending, permits at most one continuation | [Controller tests](../../tests/test_agentops_admission_controller_v1.mjs) |
| [Standalone client](../../scripts/agentops_admission_client_v1.mjs) | Runs the new controller over MCP stdio, records received/sent bytes and write completions, closes its child with bounded cleanup | Constructed MCP subprocess test in the same suite |
| [Retrospective projection](../../scripts/replay_pending_admission_v1.py) | Reads retained public bytes, derives a proposal from pre-dispatch observations, evaluates admission, then compares against the historical dispatch | [v2 result](../../runs/pending-admission-development/v2/result.json) |

The controller's exact RPC allowlist prevents other write methods from bypassing admission. Its single initial request is separately bounded. Unknown/unsupported decisions, failed certificates, stale observations, changed task/context/call bindings, changed route configuration, unmodeled serializers and denied raw methods cause zero continuation dispatches. A task observed as working is not answered again under this controller policy; this is not a general SDK refusal theorem.

The profile's goal remains original-task completion with the expected inventory effect under the named fixture contract. It is not weakened to merely emitting an HTTP request. That completion relation is conditional: the receipt explicitly lists unverified server-history, identity/session/invocation, write-policy, domain-state, redaction and successful-effect assumptions. The public pre-redaction rationale guard is checked; actual server redaction remains outside the adapter. No serialized request or source-contract name alone establishes a live effect.

## Retained verification

The [source-stable software receipt](../../runs/pending-admission-software/v1/result.json) records all four verification stages passing, with both original and captured inputs unchanged. It includes the actual transcripts and captured source/test files. The tests use authored observations and a constructed JSON-lines MCP subprocess; no real bridge, AgentOps service, model or network request was used.

The [retrospective plan](../../runs/pending-admission-development/v2/plan.json) records inspected public input/source hashes before evaluation. The [admission result](../../runs/pending-admission-development/v2/admission.json) has a supported decision, independent valid certificate and a witness matching retained public dispatch event 54. The [snapshot](../../runs/pending-admission-development/v2/snapshot.json) contains only the selected pre-dispatch public observations, configured deployment and caller proposal. The historical dispatch was compared only after evaluation; no old task was contacted.

Retrospective v1 remains preserved. V2 additionally includes the independent oracle dependency in source records and uses the final necessary rationale guard. Both produce the same matching request. This is a software re-evaluation of stored observations, not a rerun of v12.

The [source map](pending-admission-source-map-v1.md) and [30-source hash manifest](pending-admission-source-map-v1.json) distinguish inspected source facts from runtime assumptions. The source audit corrected an earlier interpretation: the deployed SDK can queue messages while working. The new controller's one-continuation rule is explicitly its own policy.

## Live verification status

The independent admitted-client checker and fresh coordinator are now implemented and tested. The coordinator ran its new N11 prerequisite, but correctly withheld B7 after the native service required a forced stop. The [new results report](pending-admission-live-results-v1.md) retains that outcome and the 97 Python plus 26 Node focused checks. The client still receives no evaluator-only identifiers or database state.

Any subsequent native/admitted attempt needs a new prospective allocation. Existing v8/v9/v10/v12 outputs and source seals remain unchanged. The client itself always leaves application effect verification to the external checker. Successful stdin writing, a transport reply and actual application completion remain separate observations.

The [eleven-case algorithm benchmark](admission-benchmark-results-v1.md) remains the executed development comparison. The controller work does not establish scientific novelty, a qualified second domain, held-out performance, supervisor acceptance or 70% project completion. Paper work remains deferred this week.
