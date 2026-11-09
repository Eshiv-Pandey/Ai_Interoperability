# apcore approval continuation and output projection: screen v2

25 October 2026. **Source-level projection lead; no qualified second domain or
new C1 method.** This continuation adds underlying approval implementation to
the [earlier framework screen](../apcore-screen-v1/decision.md). It changes no
frozen source, bridge, trace, action space, experiment or contribution route.

## Pinned source chain

The Python core release `python/v0.32.2` resolves through its release commit
link to `234813b283913c58532cd5292d9058730b42dc67`. Its commit-pinned LICENSE
is Apache-2.0. The already screened A2A adapter remains
`c8b5ae5c15ae7e848cdfb45c2f063293d172061d` (`python/v0.8.4`). These are
web-resolved revisions and formatted source excerpts, without a local Git
checkout, original downloaded source bytes or a resolved installation.

The core's [BuiltinApprovalGate](https://github.com/aiperceivable/apcore-python/blob/234813b283913c58532cd5292d9058730b42dc67/src/apcore/builtin_steps.py)
extracts `_approval_token` from invocation inputs (source lines596-620), rejects
a present non-string value, and removes the reserved key before subsequent
steps. On a gated call with a handler, lines711-747 call
`handler.check_approval(token)` when a token was supplied, otherwise
`handler.request_approval(request)`. An approved result continues; rejected,
timeout and pending results raise their corresponding typed errors. This is a
real Phase B API, so a fresh apcore Context in the A2A wrapper does not by itself
prove that external approval state is lost.

The [core error classes](https://github.com/aiperceivable/apcore-python/blob/234813b283913c58532cd5292d9058730b42dc67/src/apcore/errors.py)
establish the narrower output dependency. `ApprovalPendingError` stores the
handler result's `approval_id` in `details` and exposes it through a property
(lines364-381); its message names the module, without an approval-ID field.
`ModuleError.__str__` (lines135-136) returns only code and message. For equal
module and code, changing only the pending result's approval ID therefore
does not change that string. This source observation is about the projection
function, not a runtime pair or a claim that a token can never coincidentally
occur as text elsewhere.

The pinned [A2A executor](https://github.com/aiperceivable/apcore-a2a-python/blob/c8b5ae5c15ae7e848cdfb45c2f063293d172061d/src/apcore_a2a/server/executor.py)
passes `str(exc)` to `_input_required` on APPROVAL_PENDING (lines214-220).
That helper emits a text-only status message at lines424-435; it adds no
structured approval ID. A source comment saying the message carries the ID
is not evidence that it does. The branch handles pending before the ErrorMapper;
the mapper's separate formatting API does not automatically repair that
selected status path. No actual request was made, and this chain is not a
complete audit of every callable module, store, event or external approval API.

## Input, handler and application limits

The pinned PartConverter accepts an object-schema JSON TextPart or a DataPart
without doing module input validation. It can preserve `_approval_token` in
the resulting object, which the core later strips. Thus no blanket JSON-text
or extra-property resume obstruction follows from the inspected converter.
The caller still needs the required message `metadata.skillId`, permitted
task/context references, principal and actual binding. All typed/raw alternatives
must receive equal consideration. Factory.py explicitly enables SDK v0.3
compatibility; the strict JS-handler B4 header outcome cannot be transferred.

The core's built-in AutoApproveHandler always approves and is marked for
development; AlwaysDenyHandler always rejects; CallbackApprovalHandler rejects
all Phase B checks. None supplies a substantive asynchronous approval backend.
The pinned `examples/approval.py` approves based on an input flag and returns
a `deleted: true` dictionary without deleting a CRM record. Its call scenarios
are approval/denial controls, not a persisted CRM effect or pending/resume task.
The pinned email reference module explicitly simulates sending and returns a
computed message ID. Neither example qualifies as a second application domain.

The inspected [official approval cookbook](https://apcore.aiperceivable.com/guides/cookbook-approval-flow/)
supplies a custom ReviewQueueHandler: fresh UUID IDs index pending decisions;
the caller reads `e.approval_id` and resubmits it as `_approval_token`; a decided
check consumes the record. This establishes that ID/token relation for the
example handler. The recipe's refund module returns a dictionary, with no
refund ledger or transfer, and `queue.record` supplies the later decision.
It is documentation, not a commit-pinned native A2A application or independently
validated authorization model. Do not generalize its token lifecycle to all
handlers. The adjacent django-apcore README exposes endpoint scanning but no
qualified Phase B application; a nonmatching text find is not proof of absence.

The adapter test for APPROVAL_PENDING raises a coded custom exception through
AsyncMock and checks INPUT_REQUIRED. It does not exercise the real pending
exception, its ID, a handler, an effect, native consumption or same-task
completion. It was inspected, not run.

## C1 consequence and next discriminating work

The separate [AI technical assessment](independent-ai-assessment.md) found no
extra step beyond established partial-observation planning and relational
information-flow analysis. It is separately authored AI reasoning, not a
human novelty decision or independent experimental reproduction. The existing
[acquisition review](../../evidence-acquisition-review-v1.md) already requires
those comparators; this is not a newly discovered algorithmic gap.

With hidden initial possibilities B, may completion is `exists s in B,
exists safe completing trace`. Statewise winning is `forall s in B,
exists policy_s, forall allowed outcomes`. Caller-guaranteed completion instead
requires `exists one observation-history policy, forall s in B, forall allowed
outcomes`, preserving safety and the original goal within the same horizon.
These are different properties. A secret-specific path or policy cannot
certify the last one, but changing quantifiers does not supply a new method.

A matching exact comparator expands beliefs and finite action/observation
histories, retaining known arguments, principal, correlations, elapsed time,
token checks and every permitted result. Symbolic, backward and cached variants
receive the same source inputs and costs. Generic belief expansion, guarded
symbolic execution, paired outputs or a digest-bound certificate cannot be
renamed C1. No candidate pseudocode or advantage threshold is proposed here
because no concrete additional technical step has survived that reduction.

In particular, equal pending strings with different IDs do not prove
multistep impossibility. Safe guesses may distinguish states; an inventory,
authenticated review API, callback, task read, history or another module may
reveal the ID; some handlers may approve without it. A legitimate alternative
that completes within the task budget falsifies the obstruction. Universal
completion cannot assume an external approver always responds unless that
assumption belongs to the independently justified contract.

The finite next screen is one unchanged licensed handler plus a substantive
module and source-faithful public-surface closure, followed by native
pause/confirmation/completion of the original task and an isolated reset.
Only then freeze the task-derived safety/horizon and compare may reachability
with observation-based winning on the same smallest justified state table.
Unknown is required while handler, effect, profile or coverage is incomplete.
A new compiler/representation claim must specify an extra procedure and fair
advantage threshold before any candidate experiment. The AgentOps lead found
in query10 is screened separately; it is not credited here.

## Retention and execution statement

Twelve new query/result pairs preserve discovery, tag and commit-pinned
excerpts, examples and failures. Guessed unprefixed release/raw URLs returned
404 before the observed `python/` release naming was used. GitHub directory
fetches were restricted; an incorrect pipeline subdirectory and executor-test
path returned404; later exact observed paths were inspected. Nonmatching
finds for `_approval_token` in executor.py and `Phase`/`resume` in a test are
retained without absence conclusions. Initial display truncation of query8
was followed by reading its retained remainder; complete serialized responses
are saved. The cookbook and main-branch discovery sources remain unpinned.

No checkout, dependency install, application/service request, model inference,
candidate implementation/performance trial, external message or human review
occurred. The method objective remains active, CP2 open and verified credit5%.
