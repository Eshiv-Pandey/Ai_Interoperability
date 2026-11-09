# AgentOps v10 partial cases and shutdown diagnostic

28 October 2026. This is a post-capture analysis of retained v10 evidence.
It adds no application run, live model call, strict success, domain qualification
or checkpoint credit. The [v10 results](agentops-bridge-results-v10.md) remain
unchanged: four native strict successes, eleven complete recorded non-successes
and three partial cases. The [new inspection](source-evidence/agentops-bridge-gaps-v1/result.json)
binds 211 unchanged input files. The separate
[resume audit](../../runs/agentops-native-eligibility/bridge-resume-audit-v1/result.json)
recomputes the complete parent report exactly, including its schema and gaps.
Its initial ad-hoc comparison error is retained in that audit directory.

## B5 and B6 stopped at the permitted public-binding limit

Both cases received task/context IDs from the typed prefix. Their one raw
`GetTask` request omitted `A2A-Version`; the origin returned **HTTP 200 with
JSON-RPC error -32009**. This differs from the older JS-handler HTTP-500 result
and must not be conflated with it. The typed projection did not expose the
confirmation-call ID to these callers. Each captured exactly one `SendMessage`,
the initial request, and attempted no structured confirmation.

This follows the [prospective rule](source-evidence/agentops-bridge-control-v1/protocol.md):
do not import private evaluator IDs when the permitted read fails. These are
partial continuation observations, not demonstrations that every permitted raw
continuation fails. No bug fix should insert a private ID or silently refill
these rows. Header configuration, other authorized public paths, legal guesses
and broader interface coverage remain distinct questions.

## B7 reached the effect but failed process teardown

The configured library fetch supplied `A2A-Version: 1.0`. A raw public read
exposed the confirmation binding; the subsequent raw `SendMessage` carried the
DataPart. The final origin read reported completion, and the captured domain
state contained the expected single attributed effect.

The service routine then wrote `status: stopped` at
`2026-10-27T13:10:05.011362+00:00`. Its stderr records application shutdown
completion and `Finished server process [2926]`. Nevertheless, the controller's
20-second process wait expired. It observed the same owned Python process and
sent SIGTERM; the recorded return code is **-15**. A following `/proc` read saw
an empty argv and retained an identity error. The later outer supervisor
observed the service group empty. These records do not establish a current
live process or justify resuming v10.

The controller did not take its required `terminal.snapshot.json` because its
immediate group cleanup was unconfirmed. A read-only inspection of a copied
archived database now matches the last live `final.snapshot.json` exactly,
including all recorded tables, schema and sequence state. That establishes
consistency of the archived state; it cannot supply the missing historical
terminal boundary or turn a forced exit into a clean exit. **B7 remains partial.**

The retained records locate the failure after the server routine's shutdown
report. They do not contain pending-task or thread stacks, so the cause of the
surviving Python process remains unknown. The application source already closes
its runner/session resources in its lifespan; merely adding another close call
or increasing the wait would be an unsupported repair.

## Diagnostic implementation and validation

[The new observer](../../scripts/agentops_shutdown_diagnostics_v1.py) records
task and thread stack locations when the service coroutine finishes. It arms
a one-shot five-second traceback dump during ordinary `asyncio.run` teardown
and records whether that call exits. It neither cancels extra tasks nor sends
signals, extends the service deadline, or records frame-local values.
Its limitation is explicit: a stall before the service coroutine finishes
requires different instrumentation.

[The diagnostic launcher](../../scripts/serve_agentops_bridge_diagnostic_v1.py)
wraps the unchanged v10 service routine. It is a new, **unexecuted application
deployment**, not a change to the frozen source, v10 seal or existing outcome.
Global faulthandler ownership is restricted to this dedicated process.

All **seven new offline tests pass**, with source snapshots and process streams
in the [validation receipt](../../runs/agentops-native-eligibility/bridge-shutdown-diagnostic-validation-v1/result.json).
They check ordinary task cancellation and return values, exception preservation,
diagnostic-write failure, exclusive output creation, invalid delays, exclusion
of local values/task names, and a real inert child with cancellation-resistant
teardown. The child emits a traceback and stays alive until the test terminates
that owned child. This authored stall tests the observer; it does not reproduce
or explain the AgentOps failure. No application was imported or requested.

## Next execution obligation

The next useful runtime question is which task or thread survives after the
service coroutine returns, and whether it is specific to the configured bridge
profile. Before launching, freeze a separately versioned diagnostic allocation,
matched native/library controls, exact launcher/runtime bytes, original
request/cleanup bounds and expected diagnostic files. Retain every attempt and
all original v10 outcomes. An eventual repair must follow the observed stack
and pass a new matched control; a favorable replacement run cannot rewrite v10.

The [updated CP2 packet](cp2-review-packet-v2.md) keeps the distinct method,
fair comparator, full source-to-model fidelity, second domain and actual human
review open. Resolving process teardown supplies none of those by itself.
