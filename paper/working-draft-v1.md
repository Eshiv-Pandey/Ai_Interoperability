# Benchmarking Framework for LLM-Based Agent Interoperability: Measuring Interoperability Loss Across Heterogeneous Agent Boundaries

**Internal working draft v1, 25 October 2026.** This document drafts the stable
foundation and evidence sections of the approved method study. The distinct
admission method, qualifying second domain, held-out evaluation, applicable
live study and accountable human review remain incomplete. It is not a completed
paper, submission or selection of an applied-only contribution. Authorship and
AI-use disclosures require researcher review before public release.

## Abstract

Agent interoperability depends on whether a receiving agent can perform the
operations required by a task through the actual handoff route. A message may
be accepted while a follow-up cannot address the original task, supply a
required reference, or retrieve authoritative completion evidence. This study
targets bounded, task-relative continuation admission across pinned MCP-to-A2A
bridges. Its current foundation defines supported, unsupported and unknown
decisions for a supplied finite continuation model, with separately checked
path and bounded no-path certificates. Local controls distinguish application
guards from transport-version requirements and retain native references,
public caller evidence and private evaluation reads separately. Four controls
against an official SDK handler fail the fixed original-task completion goal;
all source-valid native controls succeed. These observations establish bounded
software fidelity, not a novel algorithm or failure prevalence. The proposed
research contribution still requires a substantive advantage over exact,
symbolic and cached analysis, a qualifying second domain and human validation.

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
records the same test suite without third-party runtime packages. In the
current drafting audit, the baseline, oracle and manifest source hashes match
that retained verification. These checks validate the finite implementation;
they do not prove a graph is a faithful model of a real application, establish
method novelty or supply independent human scientific review.

The core development CLI preserves new records and refuses to replace existing
evidence files. Actual source, runtime manifest, outcome and certificate check
remain available for replay. Tiny authored graphs are implementation controls,
not held-out application tasks or external failure measurements.

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

## 6. Open method and evaluation requirements

**Distinct method: pending.** The current finite baseline, source/preimage
recipe, observation planner and identity representation do not demonstrate C1.
An exact solver already gives correct binary decisions on a complete accepted
finite model. A defensible distinction must therefore identify additional
useful coverage under a declared evidence boundary, a new exact representation,
a sound approximation, substantive diagnostics or reproducible savings against
the strongest applicable comparator. The candidate specification and meaningful
advantage threshold must precede its measurements.

**Benchmark confirmation: pending.** The local study still requires two
resettable application-style domains, independently reviewed task/reference
contracts, development/calibration/held-out separation and frozen actual
crossing placements. Source screens identify leads and exclusions; they are
not benchmark outcomes. The recent
[advertising screen](../docs/research/source-evidence/advertising-screen-v2/decision.md)
does not qualify either inspected application as the second continuation domain.
Reusing business-object identity cannot silently replace an original-task
continuation requirement.

The [AgentOps pinned-source lead](../docs/research/source-evidence/agentops-por-followup-v1/agentops-source-update.md)
has a web-resolved release and an inspected upstream same-task confirmation
test with local service/audit assertions. It has no local checkout, executed
native control, verified wire profile or human-validated task here. It remains
an eligibility lead and supplies no additional benchmark domain.

The planned deterministic evaluation must compare schema/per-edge controls,
exact bounded whole-route analysis, symbolic/backward computation and correctly
cached alternatives. Identity-cost claims additionally require symmetry-aware
baselines. All arms receive the same runtime contract, source terms, accepted
evidence, allowed actions, horizon and updates. A full task read is charged as
one returned bundle to every arm. Profile construction, initialization,
extraction, compilation, proof generation/checking, updates, unsuccessful probes
and execution attempts remain in total cost accounting.

Correctness, unknowns, useful supported coverage and independent certificate
validity are separate outcomes. A policy that refuses every task has no useful
completion coverage. A waiting reply is not a complete-negative witness, and
omitting a private gold requirement is evaluated as an extraction/pipeline
failure. Source/profile revisions, identity changes and expiry require tested
invalidation rather than uncontrolled warm-cache comparisons.

The original measurement areas also remain in scope: context and capability
preservation, constraint/tool fidelity, recovery, latency/message/byte overhead,
and token/call overhead are planned secondary or diagnostic outcomes alongside
task success. Their formulas and denominators require scorer/trace validation;
this draft does not replace them with admission accuracy alone. The
[approved experiment design](../docs/research/student-budget-experiment-design.md)
retains the scope and conditional resource policy.

**Live validation: conditional and pending.** No task-model inference has been
performed in the current study. Model/provider access, quota and spending limits
remain unverified. If reliable access is available, paired live continuations
must share the same public prefix, receiving model, tools, reset state and
action/compute budget. The approved policy permits omission only under its
recorded access condition and restricts resulting claims. Neither paid
inference nor a paper deadline can compensate for missing C1 validity.

No power calculation, confirmatory effect, uncertainty interval, transfer
estimate or model-ranking result is reported in this draft. Those analyses
require the frozen pilot/resource and experimental gates. Deterministic repeats
check reproducibility; they do not create independent task samples.

## 7. Reproduction and claim limits

The Python core has no third-party runtime dependency; its
[README](../README.md) provides environment setup, tests and development replay.
Evidence outputs must use new paths. Wire controls separately preserve source
pins, dependency packages, actual binary pipes, ingress records, process
receipts and shutdown evidence. Archive replay validates captured claims
without launching the service or rerunning an unfavorable attempt.

Authored development graphs, source-only screens, original upstream behavior,
the disclosed port and strict official-handler controls are separate evidence
classes. Tool-formatted web excerpts are not complete original source bytes.
Local hashes protect retained integrity but do not authenticate arbitrary remote
claims. Every headline must link to its exact source/result and to the scope of
its independent check.

The artifact currently supports bounded finite-software and local fidelity
claims. It does not establish natural failure prevalence, universal protocol
incompatibility, arbitrary future stability, live LLM usefulness, a novel method
or publication readiness. Human task validity, adversarial scientific review,
authorship and AI-use disclosure are required before final conclusions.

## 8. Current conclusion

The completed foundation makes task-relative continuation requirements and
evidence limits explicit and supplies replayable software controls. The strict
official-handler cases show why body expressibility and transport acceptance
must be checked together. Their outcome also defeats a generic raw-recovery
advantage for the inspected profile. The research remains a method study with
unresolved novelty and benchmark gates; those missing results determine what
the final paper can claim.

## References

The bibliography covers sixteen literature references and two pinned software sources.
[BibTeX](references-v2.bib), [metadata/provenance](references-v2.json) and the
[claim ledger](claim-ledger-v1.json) retain inspected versions, author order
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
