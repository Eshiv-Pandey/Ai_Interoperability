# Primary-source literature synthesis and AI assessment v1

This review positions the implemented admission benchmark and its refinement,
shared-lifting and guard-pruning arms against the retained literature. The
bounded source review is complete for this version: all 18 existing bibliography
identities were refreshed against primary pages or exact software metadata, and
four closest-method references were added. The defensible contribution is a
reproducible, source-bound empirical artifact with adverse algorithm results.
The evidence does not establish a new general verification algorithm or a
field-first interoperability benchmark.

The review date is 10 November 2026. [Bibliography v3](../../paper/references-v3.md)
has 22 entries: 20 literature references and two software revisions. Its
[structured records](../../paper/references-v3.json) retain inspected versions,
source locations and unresolved fields. The [fresh allocation](source-evidence/final-literature-review-v1-20261110/plan.json)
and [hash manifest](source-evidence/final-literature-review-v1-20261110/manifest.json)
bind the source receipts. Existing entries 1-18 retain their numbering; entries
19-22 are available for the next manuscript. Paper v4 was preserved.

This is a signed, subjective AI assessment by Codex AI, agent
`/root/hosted_native_execution`. It is not a human review or supervisor approval.
Metadata checks and method interpretation are separate from reproducing another
system's empirical results. No such result reproduction is claimed here.

## Scope and source checks

The search refreshed the 18 retained reference URLs, then sought original
primary evidence for counterexample-guided abstraction refinement, relation
consistency, memo functions and bounded model checking. Publisher and author
records establish bibliographic identity. Primary paper bodies and previously
retained mechanism screens support the comparisons below. This is a targeted
synthesis of the selected literature, not an exhaustive systematic review of
every interoperability paper.

| Reference group | Primary identity verification and scope |
| --- | --- |
| 1-6: AgentThread, CONTINUITY, proof-carrying contracts, BRIDGE, AgentAsk, Facts Without Rules | Exact arXiv versions and ordered authors refreshed; official ACL metadata and PDF first page independently agree on AgentAsk's authors, venue and pages. Their reported experiments were not reproduced. |
| 7-10: guarded commands, contract quotient, IR-MIA report, Pacti | Author archive/PDF and exact preprint versions refreshed. A related final-publication DOI is not silently substituted for an inspected report or preprint. |
| 11-13: EC2, HEC, fresh labelled transition systems | Official NeurIPS, PMLR and Dagstuhl records verify authors, proceedings identities and supported fields. Active learning and fresh-name semantics are context rather than executed comparator arms. |
| 14-15: the two protocol adapters | Exact commits, account attribution, UTC commit dates and pinned Apache-2.0/MIT license bytes independently agree with the retained source lock. Account identity is not legal personal identity. |
| 16-18: YAPA, DEEPSEC, protocol-equivalence POR | Explicit author lists, inspected versions and original conference identity refreshed. Previous primary-body screens remain retained; their stronger cryptographic/equivalence guarantees are not assigned to this implementation. |
| 19-22: CEGAR, constraint consistency, memo functions, original BMC | Original publisher/author metadata verified. CEGAR and BMC bodies were inspected; memo functions were inspected in original scanned page images. Mackworth's author metadata and BibTeX were verified, but new full-body retrieval failed. |

The newly displayed arXiv DOI for proof-carrying contracts is recorded as
`10.48550/arXiv.2610.28484`, with no journal-publication or independent resolution
claim. BRIDGE's primary author list repeats Xi Chen; the repetition is retained.
DEEPSEC's DOI and conference identity are supported, but its disputed page range
remains omitted. Contract-quotient pages and DOI, Dijkstra's DOI, and EC2's
unverified pages/editors/DOI remain omitted.

Search/open receipts contain formatted tool responses, not original HTTP bytes.
The raw-primary allocation separately retains three successful paper downloads
and the primary Nature HTML body. The gh allocation retains API output bodies
and independently decoded pinned license bytes. Blocked GitHub tree opens,
Nature tool redirects, constraint-PDF timeouts/503, institutional TLS failure and
publisher 403 remain recorded. The primary Nature HTML succeeded through a
separate bounded HTTP request. Failed sources were not relabelled as successes.

## Closest algorithmic mechanisms

| Established mechanism | What this implementation does | Assessment and boundary |
| --- | --- | --- |
| CEGAR [19] | Searches an abstract graph, checks a candidate goal path against concrete recipe/binding semantics, and records exact infeasible prefixes. | This follows the established abstract-candidate/concrete-check/refinement pattern. Its bounded may-reachability decision and exact-prefix trie are a particular adaptation; they do not establish a new CEGAR principle. |
| Constraint consistency and finite pruning [20] | Resolves finite legal argument domains and explores partial assignments. A guard can prune only after its dependencies are assigned and its value is definitely false. Remaining complete tuples use the unchanged interpreter. | This is conventional conservative constraint pruning. The code does not propagate arc supports to a fixpoint or implement AC-3. The refreshed primary metadata establishes the classical lineage; a fresh full-body AC-3 comparison is not claimed. |
| Memo functions [21] | Reuses only complete local relation outcomes keyed by edge and whole binding frame; exact-prefix caches preserve depth/history context within one invocation. | Reusing results for an identical input is ordinary memoization. Correct keying, uncertainty and history handling are important implementation obligations, not a demonstrated invention of caching. |
| Bounded model checking [22] | Searches a declared finite horizon and independently checks witness/refutation certificates. A work limit can yield unknown. | Finite-horizon checking has established precedent, but this implementation is an explicit recipe/binding search, not the original SAT/LTL encoding. A work allowance differs from a temporal horizon; exhausting resources does not prove unbounded absence. |

The original [CEGAR paper](https://link.springer.com/chapter/10.1007/10722167_15)
already analyzes spurious abstract counterexamples and refines the abstraction
using an infeasible prefix. Our failure-after-one-prefix rule must therefore be
presented as context-bound refinement: it cannot exclude an edge globally when
another correlated frame enables that edge. The implementation retains the
prefix sequence and whole frames to avoid that mistake. It does not inherit the
original paper's general temporal verification guarantees.

[Michie's memo-functions paper](https://www.nature.com/articles/218019a0)
describes computing an answer, storing it with its input, and using the stored
answer on a later match. The local relation cache is a direct instance of that
general principle. The project-specific obligations concern canonical whole
frames, complete expansions, preserved uncertainty and attaching a local step
to the current history. The benchmark measures whether those obligations and
proof checking erase the saved repeated relation work.

[Mackworth's author record](https://www.cs.ubc.ca/~mack/Publications/b2hd-AI77.html)
supports the classic relation-consistency reference. The
[guard-pruning implementation](../../src/interoperability/direct_guard_pruned_v3.py)
supports the narrower claim made here: dependency-aware partial enumeration and
definite-false rejection. It does not revise variable domains using an arc queue.
Calling this arm a complete CSP solver, an AC-3 implementation, or a new
constraint-consistency method would exceed the implemented behavior.

The original [BMC paper](https://link.springer.com/chapter/10.1007/3-540-49059-0_14)
separately defines bounded path semantics and discusses the conditions needed to
conclude absence beyond a selected bound. Our certificates concern the supplied
finite recipes, contract, coverage, evidence clock and horizon. Positive evidence
is one known-safe feasible path; a certified negative is checked exhaustion
within that declared model. Neither is a universal security proof, a protocol
equivalence result, or a winning strategy against every environment response.

## Relation to the remaining selected literature

AgentThread, CONTINUITY and proof-carrying contracts [1-3] motivate explicit
composition assumptions and checked boundary obligations. BRIDGE, AgentAsk and
Facts Without Rules [4-6] motivate observing failures at handoffs and preserving
needed context. The current experiments supply fixed recipe/contract inputs and
source-bound application fixtures; they do not reproduce these systems or
establish their model-dependent error rates. A supplied deterministic relation
is not a measurement of an LLM's full output distribution.

Guarded-command and assume-guarantee work [7-10] supplies the established language
for local guards, composition and contracts. The current evaluator preserves
correlated whole frames and atomic updates, but it does not implement general
contract quotient or all modal input/output conformance obligations. EC2 and HEC
[11-12] concern selecting information to support a decision; no active-learning
selection arm is executed in the four-method study. Fresh labelled transition
systems [13] concern names and observation semantics that the finite profile
encoding does not fully provide.

The pinned adapters [14-15] are software boundaries that can be inspected and
tested, not evidence of semantic preservation for every A2A/MCP feature. YAPA,
DEEPSEC and security-protocol POR [16-18] reason about intruder knowledge,
equivalence or independence under stronger formal assumptions. The present
certificates do not encode that full semantics. In particular, combining
values from different binding frames or declaring actions independent from
shared graph topology alone cannot import those soundness guarantees.

## What the empirical evidence supports

The [four-method development comparison](shared-lifting-scaling-results-v3.md)
uses 66 fixed authored profiles at four declared work allowances. Shared lifting
certifies no case beyond goal-pruned direct in this matrix. At allowance 256,
its certified coverage is 39/66 against direct's 54/66; at 100,000, all four
methods certify the same 54 profiles. Unknown remains in the denominator. These
profiles are related development variants, not independent held-out tasks.

For `scale-0031`, sharing reduces repeated relation checks from 1,024 to 16,
while charged solver work rises from 5,566 to 14,773. Both refinement proofs
remain 8,895 bytes. This isolates an adverse cache/proof-representation tradeoff
and supports reporting the implementation as an experimental arm. It is not a
general lower bound for symbolic methods, a proof of CPU superiority, or a
claim that every refinement implementation must retain the same path-list proof.

The guard-pruned arm is a stronger conventional-comparator supplement. Its
focused tests and independent relation challenges support the implemented
definite-false pruning boundary. Comparative claims must use its separately
captured completed experiment; the retained partial Windows attempt is not a
complete four-budget result. Original four-arm evidence remains unchanged.

## Signed AI assessment and paper recommendation

I judge the current artifact suitable for a research-paper draft about a
constrained interoperability-admission benchmark, conservative unknown outcomes,
and measured search/certificate tradeoffs. Its most concrete result is the
reproducible adverse comparison: removing duplicate relation evaluation does
not by itself improve coverage or compress the existing negative proof. The
code, unchanged certificate checks, source captures and explicit limitations
make that result reviewable.

I do not find evidence here for a new general refinement, memoization or
constraint-pruning principle, or for universal interoperability/security
guarantees. The contribution should be framed around the implemented benchmark,
its boundary-specific adaptation and verified findings. Application-domain
generalization, independently authored held-out workloads, full provider/model
execution, task/gold human qualification and human scientific judgment remain
separate evidence needs. This AI review cannot manufacture those outcomes or
replace an unavailable human review.

**Signed:** Codex AI, `/root/hosted_native_execution`, 10 November 2026.
**Assessment type:** subjective AI literature/method synthesis, with primary
metadata verification and preserved retrieval evidence. **Human review:** no.
