# Task validity and two-domain qualification: supervisor packet v1

Prepared 28 October 2026 for the 31 October supervisor review. **All human
judgments are pending.** This packet supplies development-only workload
sketches, acceptance contracts and a review form. It creates no runnable task
instances, private gold, calibration or held-out material, and reports no new
experiment. It supplements the [CP2 review packet](cp2-review-packet-v2.md) and
[supervisor package](supervisor-package-v1.md), whose general gate questions do
not supply these task-specific contracts or annotation fields.

The principal decision is concrete: **the acquired evidence does not yet
qualify the approved two domains.** AgentOps is a service-operations candidate;
Carol is a tutorial/reference control; procurement remains an acquisition and
qualification gap. Counting two applications, or counting AgentOps approval
as procurement, would not meet the domain requirement.

## 1. Requirement and current qualification

The approved [workflow, section 7](../../RESEARCH_WORKFLOW.md) requires
procurement/approval and service operations, locally resettable state, 12
development templates, 8 calibration templates and 48 independently authored
held-out templates, 24 per domain with two instances each. Repeated schedules,
new names and parameter substitutions do not create independent templates.
Shared decision structures must be reported at their shared family level.
The [measurement design](student-budget-experiment-design.md) and
[CP3 gate](checkpoints.md) require two actual human reviewers of task prose,
runtime contracts, private gold, reference trajectories and near misses.
Preparing this AI-assisted packet fulfills none of that human review.

| Candidate | Source and observed behavior | Defensible present role | Missing qualification |
| --- | --- | --- | --- |
| AgentOps | Acquired commit-labeled source `c806b7f1cd0042c9817c0a4c46d80a9a95a24293`; original factory plus upstream deterministic confirmation double; guarded mock restart and attributed SQLite change observed | Service-operations development candidate | Reviewed substantive task; source-valid public evidence/triage flow; full reset, grading and reference/near-miss qualification; independently reviewed corpus |
| Carol/reference | Official sample pin `6603ba3f2c31a7ef33e70b9d8b5b5f8be42ac9a3`; original A2A 0.3 same-task reference controls | Reference microcontrol of continuation fields and task association | It is a minimal number-game tutorial, not procurement; one-entry shuffle does not establish substantive artifact quality; the disclosed 1.0 port is an adaptation |
| Procurement/approval | No acquired and qualified procurement application established by the retained screens | Missing approved domain | Original licensed pinned bytes, reproducible environment, actual runtime contract, reset and native reference, then bridge/task validation |
| Prebid Sales Agent lead | [Advertising screen](source-evidence/advertising-screen-v2/decision.md) records pinned web excerpts and an unqualified substantive purchasing workflow | Acquisition lead only | No verified local checkout; authentication, serialized binding, reset and adapter effects unresolved; inspected handler creates a fresh A2A task per send |

The [additional-domain screen](source-evidence/additional-domains-screen-v1/decision.md)
also qualified no additional application. Web excerpts and source leads are
not original-source acquisition or runtime evidence. The procurement gap
cannot be closed by renaming Carol, substituting business-object identity for
original-task identity, or silently changing the approved study.

## 2. Evidence the reviewer can already inspect

| Record | What it establishes | What it does not establish |
| --- | --- | --- |
| [Original Carol v0](reference-continuation-results-v0.md) | N1 completes the original task with task/context and a nonempty own-task reference; N2 without references remains input-required; N3 with context only creates a different task | Reference-ID equality checks, authorization, cross-task dependency validity, substantive procurement or artifact correctness |
| [AgentOps v8](agentops-native-http-results-v8.md) and [v9](agentops-native-protocol-results-v9.md) | Native original-task completion and one attributed mock effect; v9 canonical synchronous/streaming DataPart confirmation works with the declared version header | Production restart, authenticated human approval, live-model usefulness, second-domain qualification |
| [AgentOps v10](agentops-bridge-results-v10.md) | 18 executed development cells: four strict native successes, eleven complete recorded non-successes and three partial cases; [parent check](../../runs/agentops-native-eligibility/bridge-parent-check-v10.json) verifies 2,371 exported files | A corpus result, whole-interface impossibility, prevalence, a new method advantage or complete bridge qualification |

In v10, strict native positives are N3/N6/N9/N11. B5/B6 raw `GetTask`
omitted the version header and returned HTTP 200 with JSON-RPC `-32009`;
no public confirmation ID was obtained and no confirmation send was attempted.
B7's explicitly header-configured library deployment recovered the public
binding, completed the original task and produced the expected single effect.
Its forced Python exit and missing terminal snapshot keep it partial. The
[gap analysis](agentops-bridge-gap-analysis-v1.md) explains these boundaries.
New diagnostic work cannot retroactively repair historical v10 evidence.

Do not rerun, rewrite or fill missing evidence in the consumed v8/v9/v10
groups. Any eventual workload validation needs its own prospective version,
allocation and evidence paths. No diagnostic outcome is assumed here.

## 3. Minimal substantive operations workload for review

**Proposed development family: diagnose a reported service incident, obtain
attributable permission for the selected mock restart, and verify its result.**
This is a review sketch, not an executable template or a qualified task.
No concrete incident, target, rationale, seed or gold instance is selected.

Proposed public task wording:

> Inspect the reported incident and its associated service. Present the
> supporting evidence and the exact proposed restart target for approval.
> After a confirmed approval with a rationale, complete the original action
> task and report the resulting service state with evidence available through
> the declared public interface. Preserve unrelated domain state.

This has a domain result beyond a terminal label: the correct selected service
changes state, approval is attributable, and the observation is connected to
the reported incident. A human must judge whether the simulated operational
decision has adequate substance. A fixed tool call, arbitrary rationale and
success prose alone do not validate triage or evidence quality.

### Source basis and intervention boundary

The acquired [read tools](../../external/agentops-c806b7f1/agents/python/src/agent/tools.py)
provide `get_incident`, `get_service_status` and deterministic service-log
search. `get_incident` returns the service and runbook reference for dependent
calls. The [guarded actions](../../external/agentops-c806b7f1/agents/python/src/agent/actions.py)
require confirmation, nonempty approver/session/invocation identities and a
nonempty bounded rationale; persisted rationale is redacted. They reject a
write freeze, malformed target or nonexistent target. The
[input callback](../../external/agentops-c806b7f1/agents/python/src/agent/guardrails.py)
also rejects malformed writes before a confirmation request is built.

The [data layer](../../external/agentops-c806b7f1/agents/python/src/agent/data.py)
reads restart context under the write lock, sets the selected service to
operational and appends its audit row in one `BEGIN IMMEDIATE` transaction.
Duplicate delivery is scoped to `(invocation_id, action, target)`: it returns
the prior row. A new invocation is not covered by that deduplication key.
This is an application-level mock-state contract, not a universal A2A or
exactly-once external-effect guarantee.

The [executed fixture](../../scripts/serve_agentops_bridge_v1.py) exposes only
`ACTION_TOOLS[0]` to its deterministic model and requests an inventory restart.
It does **not** establish the proposed incident-read, evidence-assessment and
post-action-read trajectory. Adding a scripted controller, exposing further
tools, or changing the deterministic policy must be versioned as an explicit
fixture intervention, with fresh native qualification. Keep the original
application source and historical fixture evidence separate from that work.

### Proposed four-stage workflow

| Fixed stage | Public input/output obligation | Qualification still needed |
| --- | --- | --- |
| 1. Triage | Read incident and associated service through declared tools; pass the exact returned target and supporting observations | Show the reads and their public accessibility; review evidence sufficiency without inventing a source-enforced runbook policy |
| 2. Propose | Initiate the guarded action; retain original task/context and the public pending confirmation binding | Native source-valid pending trajectory and exact field provenance |
| 3. Authorize and execute | Supply the bound confirmation and rationale through a legal declared route | Same-task native confirmation, synthetic identity disclosure, equal legal raw/configuration alternatives for comparators |
| 4. Verify | Obtain public original-task status and the declared service-state evidence; produce an inspectable result | Establish an actual public evidence path; private SQLite snapshots cannot supply caller knowledge |

These four stages define three prospective delivery edges. Before use in a
crossing experiment, identify the concrete caller/receiver at each edge and
prove the selected one/two/three-crossing placements are realizable with the
same roles and task. Both retained bridges operate from MCP caller to A2A
agent; this sketch supplies no inverse bridge direction. If an edge cannot
use the route, report the topology gap rather than inventing a crossing.

### Proposed acceptance contract

All rows below require human review. Source-derived invariants are separated
from proposed task obligations; task obligations do not become upstream guards
merely because they appear in this table.

| Obligation | Origin | Acceptance evidence and limit |
| --- | --- | --- |
| Correct incident/target | Proposed task, grounded in incident/service read tools | Runtime-visible returned service is the selected restart target; grader independently checks the relationship against reset state |
| Evidence before approval | Proposed task; action source instructs the client to retain decision evidence and original arguments | Trace shows the approver receives the exact proposal and supporting observations; source rationale nonemptiness alone does not prove evidence adequacy |
| No early write | Source confirmation/write guards | No domain change or new audit row before valid bound confirmation; denied or invalid approvals retain state |
| Original-task continuation | Proposed task plus existing native controls | Pending, confirmation and final public reads use the original task/context; a newly completed task cannot substitute |
| Intended domain effect | Source mutation plus task-selected target | Selected service is operational after acceptance; exactly one new `restart_service` audit row for that target; a non-operational seed is required for a measurable state transition |
| Attribution | Source approval validation and audit transaction | Audit actor, approver, session, invocation and redacted rationale match the accepted action; identities remain synthetic unless a separately qualified authentication boundary establishes more |
| No collateral changes | Proposed task and restart-only action boundary | Full before/after domain comparison preserves other services, incident records and prior audit rows; observation/accounting metadata is classified separately |
| Scoped replay behavior | Source transaction/deduplication key | If later selected for validation, replay the same invocation/action/target and observe the same audit result with no second mutation; do not infer equivalence for a new invocation or arbitrary retries |
| Public result evidence | Proposed task, not established by the current fixture | Declare the exact public state/receipt fields and how to retrieve them. Internal tool results and grader-only audit snapshots are not automatically accessible to the caller |
| Complete bounded observations | Measurement contract | Original-task, effect and evidence-validity outcomes remain separate; missing terminal state, incomplete capture or unclean process evidence yields a partial/unknown strict result |

The deployment-supplied `C_runtime` must include the actual permitted actions,
observable fields, pending-binding rule, target relationship, confirmation
requirements, effect boundary and finite horizon. Specify which evidence is
fresh enough; do not claim expiry or stale-evidence enforcement from a
watchdog timeout. Private `C_gold` and its evaluator are authored separately.
An omitted gold rule can reveal an extraction/task failure without proving
the gate unsound on the weaker supplied `C_runtime`.

### Optional operations extension, not a second domain

The source also offers guarded `resolve_incident`, which checks existence and
approval and atomically marks a non-resolved incident resolved with an audit
row. A prospective **incident-closure** family could require evidence,
attributable approval, original-task completion and one correctly attributed
resolution, leaving service state unchanged. Its native trajectory, reset,
public evidence path and grading remain unexecuted/unqualified.

Do not assume the source requires a restart before resolution: the resolution
transaction does not check that the service is operational. A combined
restart-then-resolve task would need an explicit reviewed deployment policy,
two separately bound approvals and independent validation of the longer
trajectory. Renaming an action or extending a chain does not establish an
independent template family or procurement coverage.

## 4. Preserve the reference control's limited contract

Carol's [executor](source-evidence/reference-continuation/runtime/original-number-game/agent_Carol.py)
branches on a nonempty reference list and completes a follow-up beginning
with `well done`. It does not validate reference-ID equality or approval.
Its [history helper](source-evidence/reference-continuation/runtime/original-number-game/utils/game_logic.py)
formats histories or randomly shuffles entries. The last history is stored
on the executor, not in a demonstrated per-task isolated store.

The existing acceptance contract is only original-task/context association
and final state, with the N1/N2/N3 contrasts in section 2. Preserve that
contract. An optional future artifact-control extension could independently
check preservation of a nontrivial history's entries, associated responses
and multiplicities; it would require its own prospective specification,
reset/concurrency assumptions and artifact grader. It would still be a
tutorial control, not procurement or evidence of generally substantive tasks.

## 5. Procurement qualification decision

The approved procurement requirements are offer validity, budget/authority,
pending approval, identity and duplicate effects. There is presently no
source-grounded accepted workload here. The supervisor should select and
record a next qualification action, leaving unavailable facts blank:

| Field to establish | Required evidence before a procurement task is accepted |
| --- | --- |
| Application/source | Exact acquired pin, original license/bytes, tracked changes and preserved dependency lock |
| Business action | A real offer/approval/reserve-or-commit operation in that source; explicit observable effect and application deduplication scope |
| Continuation identity | Native original-A2A-task behavior if the contract requires it; a business-object ID does not silently replace it |
| Authority and freshness | Actual credential/principal boundary, offer validity/expiry and budget rules; distinguish source guards from reviewer-supplied policy |
| Reset and isolation | Reproducible local state with no paid/production transaction or uncontrolled external effect |
| Public path | Actual serialized card, selected binding, version handling, legal tools and equal authorization on native/bridge routes |
| Task validity | Reviewed public goal, runtime contract, independently authored private gold, correct reference and discriminating near misses |

Decision choices for the recorded human review are: pursue an identified
procurement application's acquisition/qualification, or explicitly review
a domain-scope amendment with its scientific consequences. **Neither choice
is made by this packet.** For Prebid, successful acquisition alone would not
resolve the inspected fresh-task handler, authorization or adapter-effect
questions. Do not repeat unchanged failed acquisition attempts as progress.
The distinct bounded-method objective also remains unchanged.

## 6. Evidence needed before task/domain qualification

1. Freeze a development-only source/fixture/profile version and proposed
   contract before validation. Preserve upstream guards and label authored
   policies, scripted roles, instrumentation and interface changes.
2. Demonstrate reproducible reset, isolated task/session/domain state, native
   positive reference and complete capture. Check the intended domain effect,
   attribution and absence of unrelated writes; a success string is inadequate.
3. Have separate authors prepare reference reasoning, private gold/oracle and
   near misses. Review categories include wrong target/association, missing
   approval/rationale, new-task substitution, duplicate effect under the same
   application key and inaccessible evidence. These are prospective review
   categories, not new instantiated tests or claims that every case is legal
   on every public route.
4. Establish exact public legal actions and evidence for every comparator;
   retain permitted raw requests and explicit deployment configurations.
   Private observer IDs or snapshots never repair the caller's input.
5. Validate graders against reviewed correct and incorrect development traces.
   Report task outcome, supplied-contract gate correctness, extraction/gold
   agreement and evidence completeness separately. Incomplete closure of legal
   values, schedules or state is not a bounded impossibility certificate.
6. Obtain two actual human task reviews and resolve disagreements against
   versioned material. Qualification remains pending while material objections
   are unresolved. Supervisor method/feasibility review remains a separate CP2
   obligation; task acceptance alone proves no methodological novelty.
7. Only after the relevant gates, arrange independent held-out authorship,
   separation, sealing and prospective allocation. This packet consumes and
   supplies no held-out/evaluation tasks and cannot count toward their totals.

## 7. Human review form

Copy this form into a **new** dated review record; preserve this packet.
Reviewer A and Reviewer B complete initial judgments independently before
reconciliation. The same supervisor may review method feasibility, but the
two-person task-validity requirement is not met by duplicating one signature.

| Review identification | Reviewer A | Reviewer B |
| --- | --- | --- |
| Actual name and role | Pending | Pending |
| Date/time and relationship to task authors | Pending | Pending |
| Packet, source pin, fixture and task/contract versions inspected | Pending | Pending |
| Public prose, runtime contract and evidence inspected | Pending | Pending |
| Private gold/reference/near misses inspected through controlled access | Pending; no private material supplied here | Pending; no private material supplied here |
| AI assistance or other authorship involvement disclosed | Pending | Pending |

Use **accept / revise / reject / not assessable**, with a reason and exact
evidence reference for each row. Blank or pending is not acceptance.

| Independent judgment | Reviewer A: decision and reason | Reviewer B: decision and reason |
| --- | --- | --- |
| Domain membership and substantive user outcome | Pending | Pending |
| Source-faithful task, guards and stated authored policies | Pending | Pending |
| Original-task identity and legitimate public continuation | Pending | Pending |
| Runtime-visible evidence and permitted action space are sufficient | Pending | Pending |
| Effect, attribution, deduplication and no-collateral contract | Pending | Pending |
| Reset, horizon, isolation and actual crossing placements | Pending | Pending |
| Runtime/gold separation and independent reference/oracle | Pending | Pending |
| Near misses and grader can distinguish meaningful failures | Pending | Pending |
| Template/family independence and expected review burden | Pending | Pending |
| Allowed claim scope and explicit limitations | Pending | Pending |
| Overall task qualification | Pending | Pending |

Reconciliation record, completed only after both initial reviews:

- Disagreements and each reviewer's initial position: **Pending**.
- Required changes, responsible person and due date: **Pending**.
- Revised task/contract/evidence version and re-review outcome: **Pending**.
- Unresolved objections and their effect on qualification: **Pending**.
- Procurement acquisition or explicitly reviewed scope decision: **Pending**.
- Whether Carol remains a reference-only control: **Pending human judgment**;
  it is classified that way in the current evidence.
- Named reviewers' final decisions and date: **Pending**.
- Separate supervisor method/feasibility decision and allowed claims:
  **Pending**.

As of the [28 October tracker](checkpoint-status.json), CP1 alone is passed
and verified deliverable credit is 5%. This packet records neither qualified
domains nor human approval and advances no checkpoint by itself.
