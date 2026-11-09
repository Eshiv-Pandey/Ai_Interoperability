# Benchmarking Framework for LLM-Based Agent Interoperability: Measuring Interoperability Loss Across Heterogeneous Agent Boundaries

**Internal working draft v3, 28 October 2026.** Prepared for supervisor review
on 31 October. The working completion target is 1 November, interpreting the
user's instruction to finish this week; this is a schedule target, not a
claim that scientific gates can be met on a date. The original method objective
and full deliverable scope remain in force. This is an incomplete paper draft,
not a submission, a novel-algorithm claim or a selected applied-only route.
[Status](draft-status-v3.json), [claim ledger](claim-ledger-v3.json) and
[eight-minute supervisor brief](supervisor-brief-v2.md) state the remaining work.
V1, v2 and the existing bibliography are preserved.

## Abstract

Agent interoperability requires more than accepted messages: a receiving caller
must be able to continue the original task and produce its required effects
through the actual protocol route. We present a development benchmark artifact
for bounded, task-relative continuation across two pinned MCP-to-A2A bridge
implementations. Its established finite reachability baseline produces separately
checked path and bounded no-path certificates. Its protocol harness records
native and bridged requests, public recovery evidence, original task/context,
SQLite effect snapshots and process completion. An eighteen-case AgentOps matrix
contains four strict native successes, eleven complete recorded non-successes
and three partial cases. Two raw bridge cases never obtained a public confirmation
binding; a configured-header case reached task completion and the expected effect
but lacked clean process exit and a terminal snapshot. A separate prospective
three-case shutdown diagnostic now records strict success for native N11 and
the configured B7 route, including clean exits and terminal snapshots; B6
remains partial because its public binding was unavailable. All three diagnostic
runs returned normally from asyncio. The earlier hang did not reproduce and
its cause remains unknown. Earlier reference controls separately expose
task-reference and transport-version dependencies. These are
bounded deterministic observations, not natural failure prevalence, live-model
utility or a new admission algorithm. A distinct method, fair-comparator advantage,
validated two-domain corpus and independent human review remain unresolved.

## 1. Introduction

Interoperable communication is useful when it preserves the operations needed
to complete a task. For example, a receiver that can send a message and read a
task may still lack a way to submit the reference-bearing answer expected by
the original application. A task-status field can also describe an adapter's
local record while the authoritative source task remains unfinished. Assessing
only message validity or advertised capability flags misses the relation
between the required operation, the affected task and the route that carries it.

This project investigates that relation through task-relative continuation
admission. A runtime contract names observable goals and invariants; an accepted
route model names permitted transitions and their evidence boundary. Admission
asks whether at least one permitted bounded continuation satisfies that
contract. It separates a modeled completion path from actual agent compliance
and separates lack of evidence from a proven obstruction. The intended method
must provide a useful advance over established whole-route analysis rather
than merely outperform an incomplete feature checklist.

Prior work already measures handoff preservation and downstream outcomes,
checks protocol composition, and admits actions under contracts. Consequently,
the project makes no first-handoff-measurement, first-composition-check or
first-runtime-admission claim. Its open contribution is a concrete, tested
procedure for this task-relative problem with a demonstrated advantage under
fair evidence and resource accounting. The implementation and experiments
reported below are foundations for that contribution, not evidence that it has
already been achieved.

The research has three intended deliverables: a distinct admission method,
replayable cases on independent real bridge paths, and conditional live utility
validation using resources verified before confirmation. The current artifact
contains an established finite baseline, a separately authored oracle and
bounded local wire controls. This working draft reports those completed
components and identifies the unresolved requirements explicitly.

### 1.1. Implemented artifact and proposed contribution

The concrete output available for review is an auditable development benchmark
for original-task continuation through two pinned MCP-to-A2A mappings. It
combines a finite decision/certificate baseline with public wire capture,
matched native profiles, an effect-based application grader and explicit
incomplete-evidence outcomes. The baseline algorithm is established reachability.
The wire study is a bounded deterministic fixture evaluation.

The proposed contribution for supervisor judgment is a task-relative evaluation
artifact that distinguishes **request acceptance, caller-visible recovery,
original-task completion, attributed domain effects and observation completeness**.
The data below demonstrate that these measurements can disagree in real pinned
implementations. Whether this constitutes a sufficiently distinct empirical or
artifact contribution relative to the closest work has not been established.
Accepting that statement would not by itself satisfy the original distinct-method
objective. Any change of contribution route requires an explicit reviewed
decision; this draft makes no such change.

## 2. Related work and comparator obligations

[AgentThread](https://arxiv.org/html/2606.28690v1) [1] already links source-derived
protocol requirements, typed intermediate representations, bounded composition
checks and executable replay. [CONTINUITY](https://arxiv.org/html/2609.05269v1) [2]
uses contracts for runtime action admission, including bindings and freshness.
[PC2](https://arxiv.org/html/2610.28484v1) [3] reasons about operation obligations,
visible-state uncertainty and composable guarantees. These mechanisms require
property-by-property comparison; changing universal admissibility to
existential completion does not itself establish a new algorithm.

[BRIDGE](https://arxiv.org/html/2610.17805v1) [4] checks prerequisites and executing
capabilities when selecting repairs. [AgentAsk](https://aclanthology.org/2026.acl-long.1294/) [5]
includes clarification and capable-peer rerouting for unavailable tools or
APIs. Equal-budget adaptations of these mechanisms are relevant when recovery
utility is claimed. An adaptation must be distinguished from the authors'
released implementation, and both arms must receive the same permitted
alternatives.

Handoff preservation is also an established empirical subject.
[Facts Without Rules](https://arxiv.org/html/2608.29028v1) [6] studies boundary and
operational information preservation, handoff formats and task outcomes. The
project's earlier [identity and claim audit](../docs/research/claim-audit.md)
therefore rejects novelty based solely on another structured packet or vendor
score matrix. A native/reference comparison is needed to attribute a bounded
route effect; a full-context single-agent comparison also changes decomposition
and information availability.

Classical predicate-transformer, interface-compatibility and contract methods
remain central comparators. [Dijkstra's predicate transformers](https://www.cs.utexas.edu/~EWD/transcriptions/EWD04xx/EWD472.html) [7],
[contract quotient](https://eskang.github.io/assets/papers/memocode18.pdf) [8],
[IR-MIA](https://arxiv.org/abs/1606.09035v7) [9] and
[Pacti](https://arxiv.org/abs/2303.17751v1) [10] cover established relational or contract
reasoning. Backward existential preimage on a deterministic serialization
fragment is a baseline technique. Task IDs, principals and expiry are state
variables, not by themselves new mathematical machinery.

Evidence acquisition has close comparators as well. Finite contingent planning,
[equivalence-class determination](https://papers.nips.cc/paper_files/paper/2010/file/1e6e0a04d20f50967c64dac2d639a577-Paper.pdf) [11]
and [overlapping decision regions](https://proceedings.mlr.press/v33/javdani14.pdf) [12]
already address selecting costly observations for decisions. These sources
have specific quantifiers, priors and test assumptions; their guarantees cannot
be transferred without checking those assumptions. The local
[acquisition review](../docs/research/evidence-acquisition-review-v1.md)
also requires correctly cached, shared-bundle and alternative-support baselines.

Finally, identifier canonicalization faces established data-independence and
nominal-automata methods. The primary
[fresh-transition-system study](https://drops.dagstuhl.de/storage/00lipics/lipics-vol363-csl2026/html/LIPIcs.CSL.2026.23/LIPIcs.CSL.2026.23.html) [13]
includes bounded-history reduction under explicit assumptions. The new
[identity screen](../docs/research/source-evidence/identity-method-screen-v1/decision.md)
therefore rejects a generic identifier quotient or fresh-name cutoff as a
distinct C1 step. Source-specific freshness and input predicates still require
fidelity checks.

Symbolic protocol analysis supplies additional strong comparators.
[YAPA](https://arxiv.org/html/1005.0737v1) [16] represents public recipes,
deduction and visible equations; its saturation result has explicit
termination/nonfailure conditions. [DEEPSEC](https://members.loria.fr/IRakotonirina/files/public_html/publications/18-sp.pdf) [17]
retains observation frames, recipe-labelled inputs and equality tests for
bounded-session equivalence under its rewrite-system restrictions.
These idealized term models do not automatically cover every concrete JSON
string operation or establish task-completion guarantees.

[Symbolic partial-order reduction](https://arxiv.org/pdf/1804.03650v2) [18]
already analyzes enabled and disabled action dependencies, constructs
persistent/sleep sets and conservatively collapses conditionals. Its preserved
non-equivalence witnesses are not automatically bounded safe original-task
completion witnesses. Transferring the reduction requires preserving the task
monitor, caller observations, legal inputs and horizon. A read that reveals
an identifier can enable new input recipes even when method names look
independent. Generic symbolic/POR composition is consequently an established
baseline direction; the distinct implementation step remains missing.

These summaries reuse inspected primary-source ledgers and the stated new
screen. They are not independent reproductions of prior systems' empirical
results. The [versioned bibliography metadata](references-v2.json) records the inspected
versions and their primary-source provenance. A final literature refresh and
human claim audit remain required before a novelty claim.

## 3. Task-relative semantics and evidence boundary

Let a supplied finite model contain states S, initial state s0, permitted
transitions R, a goal G, invariants I and a nonnegative horizon H. The primary
question is whether there exists a trace of at most H transitions from s0 whose
visited states satisfy I and whose final state satisfies G. H counts transitions;
it does not count arbitrary primitive instructions or promise an elapsed-time
bound. Nondeterministic edges denote possible outcomes. Existence of one safe
trace does not imply a winning policy against all environment outcomes.

The [finite-continuation/1 specification](../docs/research/finite-model-v1.md)
accepts scalar observables and explicit transitions. Runtime predicates include
type-sensitive equality, field equality, finite membership and integer order.
Missing values are indeterminate; explicit null is a known value. Malformed
input is rejected rather than classified as interoperability failure. Source,
route, evidence and review metadata record provenance, but a provenance string
does not prove projection fidelity or completeness.

| Decision | Required justification |
| --- | --- |
| Supported | A path within H has definitely satisfied invariants and goal, under the accepted model and evidence assumptions. |
| Unsupported | Fresh, declared complete relevant evidence excludes every safe path within H and no relevant predicate indeterminacy prevents refutation. |
| Unknown | Stale evidence, an incomplete model or relevant indeterminacy prevents either justified binary decision. |

The baseline can support a known witness in a partial model. It cannot refute
the existence of an unmodeled alternative using that same partial evidence.
Its unknown rule is conservative and does not claim maximal decision coverage.
An explicit completeness declaration remains an assumption needing source or
application justification; several failed attempts cannot establish it.

The runtime contract is distinct from evaluator-private task requirements.
Gate correctness is assessed against the exact supplied contract. A separate
pipeline analysis must assess whether requirement extraction omitted private
gold constraints. Gold information cannot be inserted into a practical gate or
used to construct its recovery action. In the local controls, final evaluator
reads are used to grade the outcome and are not available to the caller.

Evidence validity also has a restricted meaning. The finite interface checks
its supplied observation interval. A service-side lease, atomic cross-peer
snapshot or future stability guarantee is not inferred from an adapter cache
timestamp. Prospective execution requires revalidating relevant assumptions
and disclosing any no-intervening-change condition that the actual service
does not enforce.

### 3.1. From source and wire evidence to a finite model

A concrete continuation state includes application and adapter control,
task/context and resource bindings, caller observation history, principal,
approval availability and time. A caller action consists of a permitted
operation and arguments constructible under the declared caller rules. Its
effect includes request serialization, transport defaults, handler guards,
response projection and any subsequent state change. Caller-visible arguments
must be distinguished from internal client options and generated identifiers.
In particular, a raw body parameter does not grant control of an HTTP header.

Mapping that semantics to a finite graph has two separate proof obligations.
A supported abstract path needs a continuous concrete lift from the accepted
initial state: the same bindings, observations, legal actions and safe goal
must be maintained along the whole path. Individually realizable edges are
insufficient if their shared intermediate values disagree. A negative result
needs coverage in the other direction: every legal safe completing concrete
trace within the bound must be represented without losing its goal or
extending its cost beyond the bound. These are standard abstraction
soundness/completeness obligations, not a new compiler theorem.

The model must retain all relevant public alternatives, failed outcomes,
consumption, expiry and allowed intervening changes. Source excerpts and a
successful native test do not establish this closure. If a reduced state
forgets caller history, deleted internal handles can incorrectly erase still
available public values. Pooling observations from incompatible histories can
also create a completion that no concrete trace permits. The finite software
checks in Section4 assume an accepted graph; they do not discharge these
source-to-graph obligations.

When a concrete API accepts arbitrary strings, its legal input set includes
guesses. A finite dictionary or a private-atom convention cannot silently
remove them. UUID syntax alone does not prove that a legal guess is impossible,
and static nondeduction does not rule out a revealing read or later interaction.
The [action/observation coverage record](../docs/research/source-evidence/action-observation-closure-screen-v1/closure-obligations.json)
keeps these source-fidelity obligations open. No fully covering compiler or
complete-negative certificate for such an application is claimed here.

### 3.2. Existence, public evidence and caller guarantee

For a fixed concrete initial state s, may completion means that some legal
safe trace completes within H. For public evidence E describing several
compatible initial states, evidence-relative may means that such a trace
exists from at least one state in E. A uniform caller guarantee instead
requires one policy based on public observation history to complete safely
from every state in E and under every declared environmental outcome.
These quantifiers answer different questions. The first remains the approved
primary target; the other two must be labelled separately. A private gold value
cannot be inserted into the receiving caller's practical recovery action.

An illustrative equality-test interface makes the distinction explicit.
Assume N distinct possible stable strings, harmless failures that reveal only
non-equality, no other revealing operation, and completion immediately on a
match. Each guess consumes one operation. With H at least1, every fixed state
has a may-completing trace: a literal guess can happen to equal its string.
A worst-case guarantee exists exactly when H is at least N. When H is smaller,
the all-failure history tests at most H distinct strings, leaving a compatible
untested string; when H is at least N, enumeration completes.

This is a standard counting argument under the stated toy assumptions.
It is not a probability or entropy estimate, an application experiment or
a new method. Approval effects, informative failures, extra public actions or
a later completion step can invalidate that simplified bound. The observation
model and horizon must therefore be verified before transferring it to a
source-backed task. No distribution or unguessability premise is established
for the current application leads.

## 4. Established baseline and independent software checks

The current baseline explores bounded layers, retaining definitely safe paths
for acceptance and possibly safe reachability for uncertainty. Goal checks
include the initial state, so a zero-transition witness is valid. Recurrent
states remain represented at later depths because the horizon is a bound on
transitions. The implementation records state visits and edge checks; those
counters are not a claim of practical checking-cost advantage.

Supported certificates contain the ordered transition IDs. An independent
checker replays the path, checks endpoints, invariants, the final goal and the
horizon. Unsupported certificates contain the complete bounded layers and
require fresh complete evidence with no blocking indeterminacy. The checker
validates closure, including every permitted safe successor, rather than
trusting an empty list of goals.

Each certificate binds the entire supplied manifest by SHA-256, as well as
checking time, horizon and validity limit. A changed contract, identity, graph
or evidence changes that digest. Selective evidence reuse must create and check
a new projected manifest; it cannot make an old certificate valid for a changed
manifest. The independent oracle and certificate checker do not import the
baseline's decision or predicate implementation.

The retained [foundation verification](../runs/foundation/verification-v1.json)
records 65 passing software tests, including exhaustive two-state finite
cross-checks, three-valued predicate cases and forged-certificate rejection.
The [fresh-environment replay](../runs/foundation/clean-replay-v1.json)
records the same test suite without third-party runtime packages. The retained v1 drafting audit records matching baseline, oracle and manifest
source hashes for that drafting version. These checks validate the finite implementation;
they do not prove a graph is a faithful model of a real application, establish
method novelty or supply independent human scientific review.

The core development CLI preserves new records and refuses to replace existing
evidence files. Actual source, runtime manifest, outcome and certificate check
remain available for replay. Tiny authored graphs are implementation controls,
not held-out application tasks or external failure measurements.

### 4.1. Benchmark execution and evidence architecture

| Implemented layer | Input and output | What it does not establish |
| --- | --- | --- |
| Finite semantics and baseline | Supplied contract, explicit transition model and bound; supported/unsupported/unknown plus certificate | Automatic or complete compilation of application source |
| Separate oracle/certificate checker | The same accepted manifest and proposed path or bounded closure | Independent human task validity |
| Native/bridge controller | Frozen profile, fresh fixture state and public client inputs; complete or partial MCP/A2A capture | Population-level failure rate or model utility |
| Effect grader | Original task/context, confirmation binding and database boundaries; strict effect and task assessment | Success from prose or terminal task state alone |
| Evidence package | Source/runtime hashes, process receipts, exact case accounting and preserved failures | Remote-source authentication or independent scientific reproduction |

The [controller](../scripts/agentops_bridge_control_v1.py) keeps the public
client separate from the final grader-only origin read. The
[case checker](../scripts/check_agentops_bridge_v1.py) reports validity,
completeness, task state, effect classification and strict success separately.
The [group checker](../scripts/check_agentops_bridge_group_v1.py) verifies
case accounting, declared prerequisites, runtime/export bindings and process
cleanup. These are implemented software components, not merely a proposed
measurement framework. Their scientific scope depends on the source, task and
profile assumptions described below.

## 5. Pinned bridge profiles and fidelity controls

The outgoing routes use independently implemented licensed bridge mappings:
[AmirK-S/a2a-to-mcp](https://github.com/AmirK-S/a2a-to-mcp/tree/58eff9da469bccdc432bf164662727947de646b4) [14] at
`58eff9da469bccdc432bf164662727947de646b4` (Apache-2.0) and [mgcrea/mcp-a2a](https://github.com/mgcrea/mcp-a2a/tree/c4d9d3c57c1746abbf9f6aadd3a9912d464eb1f5) [15] at
`c4d9d3c57c1746abbf9f6aadd3a9912d464eb1f5` (MIT). Their
[eligibility audit](../docs/research/bridge-eligibility.md) distinguishes common
SDK dependencies from mapping-code independence. Both measured directions are
MCP caller to A2A agent. No untested inverse route is counted as a crossing.

Amir exposes ordinary tools and a tested modern MCP Tasks surface, using opaque
task/context handles. The tested mgcrea stdio route negotiates MCP2025-11-25,
offers typed tools and a permitted raw request alternative, and keeps a local
task mirror. Those profile differences remain explicit. Documented optional
non-support is a replication/control case rather than a newly found protocol
defect.

### 5.1. Historical reference and official-handler controls

The official-handler v2 controls use the genuine SDK1.1.0 Express handler,
unchanged bridge CLIs, an authored 1.0-only card and a disclosed Carol executor.
The executor's completion branch requires a nonempty reference list and the
fixed answer prefix. Native controls complete the original task/context. The
executor does not validate equality of the supplied reference with the original
task ID; the study must not infer a stronger association or authorization
contract from its nonempty-list guard.

| Case | Tested bridge action | Fixed-goal outcome |
| --- | --- | --- |
| B1 | Amir ordinary typed answer | HTTP200; empty references; original task remains input-required. |
| B2 | Amir Tasks form acceptance | HTTP200; empty references; original task remains input-required. |
| B3 | mgcrea write-enabled typed answer | HTTP200; empty references; original task remains input-required. |
| B4 | mgcrea permitted raw SendMessage | HTTP500/-32009 for absent version header; raw final GetTask also rejects. Private E1 confirms the original task remains input-required. |

Each case ran once in sequence. Across the four isolated services, N1-N3
executed 12 native-control requests, and four private E1 reads graded the
original task/context after the bridge sequence. B2-B4 initially returned
SUBMITTED under nonblocking submission; the existing public pre-answer read
established the actual pending artifact. These states are preserved rather
than replaced with a favorable initial snapshot.

Transport acceptance does not imply task completion. Conversely, B4's public
read error is not an authoritative observation of task disappearance. The
private E1 read confirms the pending original association, without becoming
recovery evidence for the caller. The older raw-positive result remains
qualified by an authored wrapper that supplied version1.0 when the header was
absent. It cannot be substituted for the strict official-handler result.

The original checker/replay failures are preserved. A disclosed post-capture
v2.1 correction fixes the initial-state expectation, nullable-notification cost
handling and mutation selectors while checking the same captured bytes within
the unchanged bound. Four corrected isolated archive replays pass; together
they contain 8,834 files and reject 109 completed evidence mutations. Counts
include repeated dependencies across archives and are not independent research
samples. Mutation setup errors from the original replay were not credited as
rejections. [Exact results and limitations](../docs/research/official-handler-bridge-results-v2.md).

The observed obstruction is explained by standard source/guard reasoning:
the typed actions accept transport but cannot populate the required reference
field; the raw action can express the body field but lacks the accepted
transport header. The inspected read actions do not execute completion. This
bounded consequence is neither a full-interface complete-negative certificate
nor an advantage over an exact comparator with the same actions and evidence.
[Method implication](../docs/research/official-handler-method-implication-v2.md).

### 5.2. AgentOps application and native profile controls

The second application lead is the original commit-labeled AgentOps archive
`c806b7f1cd0042c9817c0a4c46d80a9a95a24293`. Archive bytes were supplied locally;
they are not independently authenticated Git objects. The retained runtime
records Python 3.13.1, Google ADK 2.10.0 and Python A2A SDK 1.1.5. The HTTP
fixture uses the original application factory and imported upstream deterministic
confirmation model double. A restart changes simulated inventory service state
in SQLite, not infrastructure. Synthetic A2A approver identity is not authenticated
human approval. The fixture is not the complete conversational application.

Strict task success requires the same original task/context to complete, a
legally supplied confirmation, exactly one fully attributed expected audit row,
the intended inventory state change, no early or unrelated domain changes, and
complete capture and clean process exit. A terminal status or positive model
prose is insufficient. Read-only snapshots cover the full declared domain state
before and after boundaries; evaluator-private IDs are never supplied to the
caller to manufacture a continuation.

| Version and control | Verified result | Scope |
| --- | --- | --- |
| [v8 native/HTTP](../docs/research/agentops-native-http-results-v8.md) | Original offline upstream confirmation and HTTP fixture complete with one attributed effect; parent check verifies 1,046 exported files | Captured HTTP uses legacy method/part forms without a version header; canonical 1.0 is not inferred |
| [v9 canonical sync/stream](../docs/research/agentops-native-protocol-results-v9.md) | Both explicit `A2A-Version: 1.0` confirmation cases complete with one effect; paired omitted-header canonical probes reject with -32009 and no effect before accepted confirmation; 1,247 exported files verified | Native profiles only; not bridge polling, Tasks or callback qualification |
| v9 discovery | Cards obtained with and without the header match and both expose top-level `protocolVersion: "0.3"` | Card text alone does not identify accepted canonical request behavior |

These separately versioned controls establish that the task is natively
achievable under recorded profiles. They supersede v1's statement that AgentOps
had no local runtime or executed native control. They do not establish a
qualified second benchmark domain, all public continuation alternatives or
independent task validity. Historical preparation failures and source seals
remain retained; no favorable case was rerun for this draft.

### 5.3. AgentOps matched native/bridge matrix v10

The [prospective v10 protocol](../docs/research/source-evidence/agentops-bridge-control-v1/protocol.md)
fixed eleven native and seven bridge/deployment cases before execution. Each
cell used fresh application/model-double/bridge state. Native controls matched
blocking, streaming and polling configurations; bridge cases included ordinary,
Tasks, MRTR, typed polling, raw CLI and configured library paths. B6 forwards
fetch arguments; B7 adds the version header only for the frozen local origin.
B7 is an explicit deployment intervention, not stock raw behavior.

The terminal group records `failed` because B7 required forced service cleanup.
The [parent check](../runs/agentops-native-eligibility/bridge-parent-check-v10.json)
accounts for all eighteen attempted cells and verifies 2,371 exported files.
It does not equate artifact integrity with complete observations.

| Cases | Frozen continuation/profile | Origin/effect observation | Whole-case classification |
| --- | --- | --- | --- |
| N1, N2, N4, N5, N7, N8 | Literal or JSON-text native confirmation in blocking, streaming or polling profiles | Input-required; unchanged domain state | Six complete recorded non-successes |
| N3, N6, N9 | Native DataPart confirmation in those three profiles | Original task completed; one expected attributed effect each | Three strict successes |
| N10 | Typed/polling prefix; raw DataPart without version header | Version rejection; original task pending; no effect | One complete recorded non-success |
| N11 | Matched prefix; raw DataPart with version header | Original task completed; one expected attributed effect | One strict success |
| B1, B2 | Amir ordinary/Tasks; public confirmation binding serialized as JSON text | Original task input-required; no effect | Two complete recorded non-successes |
| B3, B4 | Amir MRTR/mgcrea typed polling; permitted literal fallback when confirmation binding was absent | Original task input-required; no effect | Two complete recorded non-successes |
| B5, B6 | mgcrea stock raw/passthrough library; raw public read before structured continuation | Raw read returns HTTP 200/-32009; confirmation binding not observed; no confirmation send attempted | Two partial cases |
| B7 | mgcrea library with explicit version-header fetch; public raw read and DataPart send | Original task completed and one expected effect observed; service process later required SIGTERM | One partial case |

The totals are **four strict successes, all native; eleven complete recorded
non-successes, seven native and four bridged; and three partial bridged cases**.
These counts describe fixed development cells. They are not an estimated bridge
success rate, eighteen independent task templates or a statistical comparison.
The recorded 128 passing preparation tests are software checks, not additional
application episodes. No installation or live model call occurred in v10.

B5/B6 followed the prospective public-information policy: the caller did not
import an evaluator-only confirmation ID after the raw read failed. Their
partial classification must not be turned into proof that all permitted raw
continuations fail. AgentOps's HTTP-200 JSON-RPC error is also distinct from
the older official JS-handler HTTP-500 result in Section 5.1.

In v10, B7's final origin and effect observations are positive, but strict
success is unverified. Uvicorn reported shutdown; Python remained alive beyond the
20-second process wait and exited after SIGTERM with return code -15. A
subsequent process-identity error prevented the required terminal snapshot.
The outer supervisor later observed the service group empty. A copied archived
database now matches the last live final snapshot exactly; that consistency
cannot recreate the missing historical observation or a clean exit. The
[gap analysis](../docs/research/agentops-bridge-gap-analysis-v1.md) preserves
this partial result and leaves the surviving task/thread cause unknown.

### 5.4. Prospective shutdown diagnostic v12

A separately frozen diagnostic asked which task or thread survived the shutdown
boundary and whether the same phenomenon occurred in matched native and
passthrough controls. The [v12 protocol](../docs/research/source-evidence/agentops-bridge-diagnostic-v2/protocol.md)
fixed fresh N11, B6 and B7 cases in that order, once each, preserving the public
binding policy, application/model double, bridge implementations and client
profiles. A versioned observer wrapped the existing service routine and recorded
asyncio boundaries, task/thread stack locations and a one-shot teardown
traceback. It added no cancellation, signal or timeout extension. Observation
work may nevertheless change scheduling.

The earlier v11 preparation was sealed but never launched. An export-path
reference bug was corrected prospectively in v12; the old seal and bytes remain
preserved in the [supersession record](../docs/research/source-evidence/agentops-bridge-diagnostic-v2/supersession.json).
The [terminal group](../runs/agentops-native-eligibility/linux-bridge-diagnostic-v12/result.json)
records all three cases and no installation or live model call. The
[parent check](../runs/agentops-native-eligibility/bridge-diagnostic-parent-check-v12.json)
passes artifact and semantic verification for 2,617 exported files: three
executed, zero skipped and zero unexecuted. Runtime checks agree before and
after execution. Export counts include retained dependencies and prior evidence;
they are not independent observations.

| Diagnostic case | Public continuation and domain result | Whole-case result | Shutdown evidence |
| --- | --- | --- | --- |
| N11: matched native profile | Public bound DataPart; original task completed; one expected attributed effect | Strict success | Complete; normal asyncio return, clean exit and terminal snapshot |
| B6: passthrough public factory | Raw read yields no confirmation binding; no confirmation send; original task input-required and state unchanged | Unknown/partial | Complete; normal asyncio return, clean exit and terminal snapshot |
| B7: header-configured public factory | Public raw read recovers binding; DataPart completes original task; one expected attributed effect | Strict success | Complete; normal asyncio return, clean exit and terminal snapshot |

B7 therefore supplies one fully observed positive for the configured bridge
route under this diagnostic wrapper. Its fetch configuration adds
`A2A-Version: 1.0` only at the selected local origin; this is not stock raw
behavior. B6 again receives HTTP 200 with JSON-RPC `-32009` on its raw read;
no private confirmation ID is supplied to repair the caller's evidence.
All service/client exit codes are zero, with no forced cleanup or cleanup error.
Terminal snapshots follow observed empty service process groups. B6's missing
public binding keeps the parent `all_evidence_complete` flag false even though
all three shutdown diagnostic captures are complete.

Every lifecycle records `asyncio_run_entered`, `teardown_watchdog_armed`,
`coroutine_finished` and `asyncio_run_exited` with outcome `returned`. There
are no diagnostic errors or timeout traces; all three traceback files are
empty. At the coroutine-finished snapshot, N11 and B7 show only the current
observer task. B6 additionally shows four pending tasks: two telemetry wrappers,
an active-task producer and an active-task consumer. Those tasks did not prevent
normal return in this run. These snapshots are suspension locations, not full
await chains or cancellation histories. The enumerated main Python thread does
not establish absence of all native/runtime threads.

Seventeen captured-frame source snapshots were retained, five each for N11/B7
and seven for B6. Their recorded hashes/bytes verify, with no recorded-frame
source-closure gaps. The files were copied after capture; this does not prove
pre-execution loaded-module fidelity or coverage of unobserved frames.
The [diagnostic results and direct lifecycle links](../docs/research/agentops-bridge-diagnostic-results-v12.md)
retain these observations and their limits.

The earlier unlocalized post-server process-survival problem did not reproduce.
V10 did not capture these new asyncio boundaries, so the diagnostic cannot place
the earlier hang inside asyncio teardown rather than a later interpreter phase.
No causal explanation, successful repair, latency improvement or reliability
estimate follows. V10 remains four strict native successes, eleven complete
recorded non-successes and three partial cases; the new controls are neither
pooled into that matrix nor substituted for its B7 observation.

### 5.5. Interpretation and open causal claims

The observations distinguish representation, transport, public recovery and
effect evidence. They do not show that ordinary reachability fails on an
accepted complete model. The [source-recipe baseline](../docs/research/source-recipe-baseline-v0.md)
expresses the serializer and guard conditions, while the
[shared-callsite screen](../docs/research/c1-callsite-factoring-screen-v1.md)
reduces the proposed factoring step to established interprocedural summaries.
No additional method or fair-comparator advantage is demonstrated by either
the positive native effects or the configured-header observation.

The early shutdown observer's seven passing offline tests, including an inert
stalled-teardown child, remain software validation. The v12 application
diagnostic is reported separately in Section 5.4. Neither an authored stalled
child nor three normally returning controls identify the cause of historical
v10 B7. Any further diagnostic requires a new substantive question and
prospective design; the consumed allocations are not repeated for a favorable
explanation.

## 6. Remaining method and evaluation requirements

**Distinct method: unresolved.** The current finite baseline, source/preimage
recipe, observation planner, identifier representation and shared-callsite
factoring do not demonstrate C1. Exact bounded reachability is already correct
on a complete accepted finite model. A defensible method contribution needs an
additional procedure, useful exact representation, sound approximation or
material cost improvement under a stated evidence boundary, compared fairly
with the strongest applicable existing mechanism. Candidate pseudocode,
quantifiers, correctness obligations, meaningful advantage threshold and
measurement cases must be fixed before candidate performance is collected.

**Two-domain benchmark and human validity: incomplete.** AgentOps now has local
source, installed runtime, native controls and bounded bridge observations.
It remains an unqualified benchmark-domain lead because complete relevant
route/task validity and independent human review are open, including after the
configured-route positive in v12. The approved domains are procurement/approval
and service operations. AgentOps is an operations candidate; Carol and its
disclosed port are reference development controls, not procurement. No acquired
qualified procurement application is established. The
[task-validity packet](../docs/research/task-validity-supervisor-packet-v1.md)
provides proposed operations contracts and blank human review forms without
claiming qualification. Neither source screens nor repetitions of one fixture
create an independently authored two-domain corpus.

The approved corpus still requires 12 development templates, 8 calibration
templates and 48 independently authored held-out templates, 24 per domain,
with two held-out instances each. Two actual humans must review task validity
and resolve disagreements. Runtime contracts and evaluator-private gold must
remain separate, with reviewed reference trajectories, near misses, objective
effect graders and frozen crossing placements. These requirements are not
satisfied by the eighteen-case profile matrix or separate three-case diagnostic.

The planned deterministic evaluation retains schema/per-edge controls, exact
bounded whole-route analysis, symbolic/backward computation and correctly
cached/incremental alternatives. Relevant identity-cost claims require
symmetry-aware comparators. Every arm receives the same runtime contract,
source terms, public evidence, allowed actions, horizon and updates. Charge
profile construction, initialization, extraction, compilation, proof generation
and checking, updates/invalidation, failed probes and execution attempts.
A bundled task read is one returned bundle for every arm.

Correctness, unknowns, supported coverage and certificate validity are separate
outcomes. Refusal is not completion; a waiting reply is not a complete-negative
certificate. Omitted private requirements are extraction/pipeline errors rather
than failures of the gate against its supplied contract. The original measurement
areas remain planned: task success, context and capability preservation,
constraint/tool fidelity, recovery, latency, messages/bytes and tokens/calls.
Their definitions, denominators and missing/not-applicable treatment require
validated graders and a prospective freeze, not merely trace fields.

**Live validation: conditional and pending.** No task-model inference is reported
here. Access, quota and spending limits are unverified. If reliable access is
confirmed, paired continuations must share the public prefix, receiver model,
tools, reset state and repair/compute budget. The approved access policy permits
omission only under its recorded condition and then restricts claims. There is
no live superiority estimate, confidence interval, vendor ranking or transfer
result in this draft. Deterministic repeats provide reproducibility checks,
not new independent task samples.

**Independent reproduction and scientific review: pending.** Separate code,
archive checks and AI critique are useful verification but do not supply the
required human task review, supervisor novelty/feasibility judgment or independent
scientific reproduction. The [CP2 packet](../docs/research/cp2-review-packet-v2.md)
provides the current evidence and unresolved gates. A supervisor may assess the
proposed artifact claim, request a concrete new-method discriminator, or review
an explicit change of route. No decision is presumed by this draft.

The 31 October meeting and working 1 November completion target tighten the
schedule, not these requirements. The complete distinct-method study cannot
truthfully be declared achieved while they remain unresolved. The immediate
reviewable deliverable is this substantive working manuscript, executable
development artifact and [decision brief](supervisor-brief-v2.md).

## 7. Reproduction, limitations and responsible reporting

The Python finite core has no third-party runtime dependency. The
[README](../README.md) documents setup, unit tests and a development replay to a
new output path. Native/bridge experiments have separately pinned application,
SDK and runtime dependencies; fresh replay of their archived evidence is
distinct from rerunning an application. Existing run directories must not be
overwritten or silently resumed. Source, exact requests/responses, process
receipts, effect snapshots, prospective inputs and contrary outcomes remain
available through the linked results.

The claim ledger distinguishes specified semantics, implemented software,
observed development controls, retained-data recomputation and proposed future
claims. File counts measure export coverage, not statistical sample size or
capture authenticity. Multiple archives contain repeated dependencies. A local
hash binds retained bytes but does not independently authenticate remote Git
history, establish human review, or prove source-to-model completeness.

External validity is limited to the pinned outgoing MCP-to-A2A profiles and
recorded deterministic tasks. The study has not measured the inverse direction,
a representative deployment population, live agent behavior, arbitrary legal
strings or endpoints, concurrent/multi-approval workflows, long-lived state,
expiry beyond the chosen bounds or authenticated human approval. Header
configuration is a deployment intervention; its outcome cannot be credited to
the stock raw CLI. Model-double prose is not an effect grader.

Internal validity depends on correct capture, public/private separation,
profile matching and a complete definition of the effect. Historical v10 B7
demonstrates why process completeness is part of evidence validity. Its positive
pre-exit state and negative cleanup result are retained alongside the separately
observed strict v12 B7 positive. The new observer may perturb scheduling, and
non-reproduction does not identify a repair or the earlier hang's location.
The unknown cause is not attributed to AgentOps, ADK, SQLite or a bridge.
No-continuation cases do not establish universal failure. Earlier checker
corrections and v12 frame-source collection are disclosed as post-capture work.

No natural failure prevalence, novel algorithm, practical speed advantage,
confirmed live utility or acceptance probability is claimed. Final publication
requires the remaining experiments and claim review, accountable authorship,
AI-use disclosure, license/redistribution review and an explicit release decision.
This local supervisor draft is not that release.

## 8. Current conclusion and proposed review claim

The implemented artifact makes original-task continuation, public recovery,
transport acceptance, attributed effects and observation completeness separately
checkable. The retained native and bridged controls show that those outcomes
need not agree. In v10, four native cells meet the strict contract, eleven cells
record non-success and three remain partial. The separately frozen v12 diagnostic
adds strict native N11 and configured-bridge B7 positives, while B6 remains
partial for missing public confirmation evidence. All three diagnostic processes
returned cleanly; the prior hang did not reproduce and remains unexplained.
The new positive does not erase the historical unclean exit. These are concrete
bounded findings with replayable evidence, not a repair or performance claim.

The proposed supervisor claim is therefore an auditable task-relative
interoperability evaluation artifact with explicit result qualification.
Its novelty and sufficiency as a contribution require review. The original
research objective additionally requires a distinct admission method and fair
advantage, two validated domains, frozen evaluations and independent reproduction.
Those requirements remain open, so this manuscript is a working draft rather
than a completed method paper or a unilateral change of research direction.

## References

The bibliography covers sixteen literature references and two pinned software sources.
[BibTeX](references-v2.bib), [metadata/provenance](references-v2.json) and the
[claim ledger](claim-ledger-v3.json) retain inspected versions, author order
and claim limits. The unresolved DEEPSEC page range is omitted. Final literature
coverage and human metadata/claim review remain pending.

1. Shenghan Zheng, Qifan Zhang, Zheng Zhang, Haonan Li, Christophe Hauser. [Formal Security Analysis of Agent Protocol Composition](https://arxiv.org/abs/2606.28690v1). 2026; arXiv:2606.28690v1; Preprint, version 1, submitted 27 June 2026.

2. Chris Zheng, Geng Yang. [CONTINUITY: Security-Context Contracts for Composable LLM Agent Controls](https://arxiv.org/abs/2609.05269v1). 2026; arXiv:2609.05269v1; Preprint, version 1, submitted 4 September 2026.

3. Carlo Ciliberto, Alessandro Rudi, Enrico Tassi. [Proof-Carrying Contracts: Commitments AI Agents Cannot Break](https://arxiv.org/abs/2610.28484v1). 2026; arXiv:2610.28484v1; Preprint, version 1, submitted 20 October 2026.

4. Encheng Su, Pengze Li, Ziheng Hua, Qiucheng Yu, Jianyu Wu, Chen Tang, Yizhou Wang, Lintao Wang, Junjia Xiang, Xinzhu Ma, Xi Chen, Shixiang Tang, Houqiang Li, Xi Chen, Aoran Wang. [BRIDGE: Selective Boundary Repair with Dependency Graph Evidence in Multi-Agent Systems](https://arxiv.org/abs/2610.17805v1). 2026; arXiv:2610.17805v1; Preprint, version 1, submitted 13 October 2026; reported author order retained.

5. Bohan Lin, Kuo Yang, Zelin Tan, Yingchuan Lai, Chen Zhang, Guibin Zhang, Xinlei Yu, Miao Yu, Xu Wang, Yudong Zhang, Yang Wang. [AgentAsk: Multi-Agent Systems Need to Ask](https://aclanthology.org/2026.acl-long.1294/). Proceedings of the 64th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers); pp. 28055–28077; 2026; DOI 10.18653/v1/2026.acl-long.1294.

6. Yian Wang, Agam Goyal, Eshwar Chandrasekharan, Hari Sundaram. [Facts Without Rules: Boundary Metadata Collapse in Multi-Agent LLM Handoffs](https://arxiv.org/abs/2608.29028v1). 2026; arXiv:2608.29028v1; Preprint, version 1, submitted 29 August 2026.

7. Edsger W. Dijkstra. [Guarded commands, non-determinacy and formal derivation of programs](https://www.cs.utexas.edu/~EWD/transcriptions/EWD04xx/EWD472.html). Communications of the ACM; vol. 18; no. 8; pp. 453–457; 1975; EWD472 archival transcription; publication identity stated by the archive.

8. Íñigo Íncer Romeo, Alberto Sangiovanni-Vincentelli, Chung-Wei Lin, Eunsuk Kang. [Quotient for Assume-Guarantee Contracts](https://eskang.github.io/assets/papers/memocode18.pdf). MEMOCODE 2018; 2018; Author-hosted proceedings paper; printed author spelling retained.

9. Lars Luthmann, Stephan Mennicke, Malte Lochau. [Compositionality, Decompositionality and Refinement in Input/Output Conformance Testing - Technical Report](https://arxiv.org/abs/1606.09035v7). 2019; arXiv:1606.09035v7; Technical report, version 7, revised 14 February 2019; first submitted 29 June 2016.

10. Inigo Incer, Apurva Badithela, Josefine Graebener, Piergiuseppe Mallozzi, Ayush Pandey, Sheng-Jung Yu, Albert Benveniste, Benoit Caillaud, Richard M. Murray, Alberto Sangiovanni-Vincentelli, Sanjit A. Seshia. [Pacti: Scaling Assume-Guarantee Reasoning for System Analysis and Design](https://arxiv.org/abs/2303.17751v1). 2023; arXiv:2303.17751v1; Inspected preprint, version 1, submitted 31 March 2023; related ACM publication not substituted.

11. Daniel Golovin, Andreas Krause, Debajyoti Ray. [Near-Optimal Bayesian Active Learning with Noisy Observations](https://papers.nips.cc/paper_files/paper/2010/hash/1e6e0a04d20f50967c64dac2d639a577-Abstract.html). Advances in Neural Information Processing Systems; vol. 23; 2010.

12. Shervin Javdani, Yuxin Chen, Amin Karbasi, Andreas Krause, Drew Bagnell, Siddhartha Srinivasa. [Near Optimal Bayesian Active Learning for Decision Making](https://proceedings.mlr.press/v33/javdani14.html). Proceedings of the Seventeenth International Conference on Artificial Intelligence and Statistics; Proceedings of Machine Learning Research; vol. 33; pp. 430–438; 2014.

13. Mohamed H. Bandukara, Nikos Tzevelekos. [A Logic for Fresh Labelled Transition Systems](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.CSL.2026.23). 34th EACSL Annual Conference on Computer Science Logic (CSL 2026); Leibniz International Proceedings in Informatics (LIPIcs); vol. 363; pp. 23:1–23:24; 2026; DOI 10.4230/LIPIcs.CSL.2026.23.

14. AmirK-S. [a2a-to-mcp](https://github.com/AmirK-S/a2a-to-mcp/tree/58eff9da469bccdc432bf164662727947de646b4). Software source, commit 58eff9da469bccdc432bf164662727947de646b4; 2026; Apache-2.0; commit dated 6 September 2026 in retained source lock.

15. mgcrea. [mcp-a2a](https://github.com/mgcrea/mcp-a2a/tree/c4d9d3c57c1746abbf9f6aadd3a9912d464eb1f5). Software source, commit c4d9d3c57c1746abbf9f6aadd3a9912d464eb1f5; 2026; MIT; commit dated 9 October 2026 in retained source lock.

16. Mathieu Baudet, Véronique Cortier, Stéphanie Delaune. [YAPA: A generic tool for computing intruder knowledge](https://arxiv.org/abs/1005.0737v1). 2010; arXiv:1005.0737v1; Inspected preprint, version 1, submitted 5 May 2010.

17. Vincent Cheval, Steve Kremer, Itsaka Rakotonirina. [DEEPSEC: Deciding Equivalence Properties in Security Protocols - Theory and Practice](https://members.loria.fr/IRakotonirina/files/public_html/publications/18-sp.pdf). Proceedings of the 39th IEEE Symposium on Security and Privacy; 2018; DOI 10.1109/SP.2018.00033; Inspected 2018 author-hosted conference paper; page range unresolved.

18. David Baelde, Stéphanie Delaune, Lucca Hirschi. [POR for Security Protocol Equivalences: Beyond Action-Determinism](https://arxiv.org/abs/1804.03650v2). 2018; arXiv:1804.03650v2; Inspected preprint, version 2, revised 24 April 2018; first submitted 10 April 2018.
