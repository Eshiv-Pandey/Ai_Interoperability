# Method and research contribution assessment v2

As of 11 November 2026, the verified evidence supports a concrete research
artifact and negative mechanistic findings. It does not establish a new general
admission, refinement, memoization or constraint-pruning principle, or practical
superiority of shared lifting. A paper can honestly present the benchmark and
these findings. Whether that contribution is sufficiently original and useful
for a particular venue remains a scientific review decision, not an outcome
proved by these audits.

This assessment preserves the original objective: a distinct, rigorously tested
task-relative method and an independently reproducible, qualified two-domain
interoperability study. It does not select an artifact-only alternative, revise
the approved workload, pass the novelty gate or declare the project complete.
The [structured assessment](method-contribution-assessment-v2.json) binds the
reviewed inputs and records supported and unresolved claims separately.

The starting points are the [retained literature synthesis](final-literature-review-v1.md),
[manuscript v7](../../paper/working-draft-v7.md), current source and independently
audited results. The targeted literature review contains 22 references and is
not an exhaustive search. Its primary-body limitation for Mackworth is retained.
No external system's reported experiment was reproduced in this assessment.

## Closest mechanisms and the actual comparator

| Implemented operation | Closest established mechanism | What is supported here |
| --- | --- | --- |
| Bounded abstract goal-path search, concrete recipe lifting and exact infeasible-prefix refinement | CEGAR/lazy symbolic checking; original CEGAR reference [19] | A particular executable bounded may-completion adaptation. Exact prefixes preserve binding context; failure of one context cannot disable an edge globally. This is not a demonstrated new refinement rule. |
| Edge-and-whole-frame relation caches and exact-path prefix summaries | Memo functions [21], ordinary stateful relational summaries | Complete expansions, typed canonical keys, sticky uncertainty and current-history reconstruction are important verified implementation obligations. Identical-input reuse is established memoization. |
| Remaining-horizon goal-cone pruning and finite state/frame products | Finite reachability, predicate/contract reasoning and bounded checking [7-10,22] | A credible same-input direct baseline. Explicit task IDs, principals, expiry and three decision labels do not alone distinguish an algorithm. |
| Dependency-aware partial argument enumeration, pruning only definitely false closed guards | Conservative finite constraint pruning [20] | A stronger conventional-comparator supplement. It is not AC-3, full constraint propagation or a new consistency method. |
| Independent path/refutation checks bound to profile, horizon and clock | Certificate checking under supplied finite semantics | A useful assurance and reproducibility interface. Checked finite witnesses do not establish universal progress, source-model completeness or real-world settlement. |

The strongest executed aggregate comparator is
[goal-pruned memoized direct search](../../src/interoperability/direct_goal_pruned_v2.py).
Its source retains the same recipe language, correlated frames, freshness and
coverage rules, a whole-frame relation cache, remaining-horizon goal pruning
before tuple expansion, and return on the first feasible goal tuple. Its
negative checker reconstructs the relevant product without trusting the solver.
It is therefore not an intentionally uncached or goal-unaware comparator.

The [constraint-pruned successor](../../src/interoperability/direct_guard_pruned_v3.py)
retains that product search and exhaustive checker, adding conservative
dependency checks before complete tuples. The
[completed supplement](guard-pruned-comparison-results-v3.md) gives it no extra
certified case over goal-pruned direct at any tested allowance. At 100,000 it
charges 4,186 units versus 3,382, with the same 19,880 accepted proof bytes.
Those charges are method-specific counters, not equal hardware costs.

The [earlier callsite-factoring screen](c1-callsite-factoring-screen-v1.md)
also showed why ordinary exact interprocedural summaries and shared symbolic
call DAGs already reproduce the proposed faithful factoring operation.
Coarser merging would omit actual state/observation obligations. That rejected
construction is not a missing novel step supplied by the current caches.

This review does not show that every possible new method is impossible.
Algorithmic distinctness and empirical advantage are separate questions: an
unfavorable result alone cannot disprove novelty. Here the absence of a
demonstrated distinct step comes from the source/mechanism comparison; the
absence of demonstrated shared-lifting advantage comes from the measurements.

## Concrete supported contributions

1. **An executable task-relative admission and measurement artifact.** The
   implementation makes legal recipes, correlated bindings, atomic updates,
   runtime contracts, finite horizons, evidence clocks and incomplete coverage
   explicit. Positive witnesses, justified finite negatives and unknowns are
   distinguished, with separately authored checking logic. These are concrete
   software and semantic-interface contributions; tests and propositions under
   stated assumptions are not a mechanized proof or an invention of reachability.

2. **A reproducible, same-evidence comparison that removes a weak-baseline
   explanation.** The four-method suite and separate fifth comparator yield
   1,320 method/profile/allowance cells on 66 authored development profiles.
   The separate cache allocation has 1,584 method cells, including 1,056 cache
   policy cells. These studies reuse the same related profiles; their cell
   counts must not be summed into independent tasks. At allowance 256, shared
   lifting certifies 39/66 versus goal-pruned direct's 54/66. Shared-only
   certification is zero at every tested allowance. At 100,000, all five
   original/supplemental methods agree on 28 supported, 26 unsupported and
   12 unknown, preserving incomplete decision coverage.

3. **A negative mechanism finding about cache savings and proof representation.**
   On `scale-0031`, shared lifting reduces relation checks from 1,024 to 16,
   while declared work rises from 5,566 to 14,773 and the proof stays 8,895
   bytes. Goal-pruned direct uses 134 units and a 338-byte proof on that case.
   Across all 66 profiles at 100,000, neither/prefix/relation/both cache policies
   charge 46,278/44,432/50,150/46,840 units. Prefix-only saves 1,846 relative to
   neither, relation-only adds 3,872 and both adds 562. Every cache policy
   retains 27,248 accepted proof bytes versus direct's 19,880. The result is
   narrower than saying caches never help: local reuse is real, but it does
   not add certified coverage or compress this implementation's path-list proof.
   No CPU-speed, memory ranking or general lower bound follows.

4. **Evidence that correct bounded admission and business utility differ.** The
   [AP2 raw peer review](../../runs/ap2-reference-development/v5/retained-42881390576-2/independent-peer-review-v1.json)
   verifies 65 original payment-tool cells. Purchase counts are 11/3/10/3/9 for
   reference/conventional/recovery/admission/recovery-plus-admission. The
   corresponding error-free owned-cell counts are 10/2/9/2/8: 36 observed
   payments include five later duplicate errors. Admission alone is -7/13
   purchases relative to informed recovery, and recovery plus admission is
   -1/13 relative to recovery. Refusing an invalid or expired request is not
   purchase completion. Canonical reference values and arm information differ;
   this is disclosed development evidence, not the primary equal-information
   held-out utility study.

5. **Source-bound diagnostic evidence that separates natural boundaries from
   owned interventions.** The original shopper tools test for `challenge` while
   actual SDK tasks report `input-required`, hiding the challenge in a generic
   return. The [original ADK review](../../runs/ap2-original-shopper-development/v7/retained-42886479185-1/independent-raw-peer-review-v1.json)
   verifies 29 prefixes, 28 generic-status adverse boundaries and zero purchases,
   while retaining 34 candidates. Wallet DataPart/tool/display and fresh reset
   identities are checked. Common prefixes do not qualify unrealized OTP,
   receipt or fault branches. This is an observed source boundary, not a claim
   of whole-interface non-support or the first report of the issue. The separate
   AgentOps 34-candidate mechanical census is feasibility evidence; its
   20/10/2/2 complete/partial/unsupported/failed labels remain subject to semantic
   review and are not human gold or full-study success rates.

There is one important qualification to the aggregate negative findings:
**original refinement**, distinct from shared lifting, certifies 24/66 versus
direct's 20/66 at allowance 32. That is a real result under the stated meters.
It does not show a prespecified practical advantage under common end-to-end
cost, and it does not justify claiming direct dominates every method in every
configuration. At the other three tested allowances, original refinement's
coverage is lower than or equal to goal-pruned direct.

## What is still unresolved

The existing memoization and exact-prefix implementation supplies no demonstrated
technical step absent from the closest reviewed mechanisms. A current method
claim must identify a new representation/property/procedure and its assumptions,
not merely a new task label, quantifier, cache name or collection of checks.
The reviewed literature constrains this claim; it does not certify that no
unreviewed work or future construction could support it.

An efficiency or reusable-analysis claim also remains unresolved. All current
shared caches are invocation-local. They do not demonstrate cross-call evidence
reuse or dependency-aware invalidation after task, principal, namespace, source,
contract or expiry changes. Current charged counters and fixed-order timing
observations cannot establish common-cost practical superiority. Source/profile
construction, probes, witness/proof production, checking and maintenance cannot
be omitted merely because relation evaluations decrease.

The original source-to-model and two-domain empirical obligations remain open.
The AP2 gate projects one incomplete relation using public observed values;
its certificate does not prove closure over all original legal actions and
recovery alternatives. Offline models and in-process ASGI do not qualify
native/provider routes or actual repeated MCP/A2A crossings. Exposed candidate
records cannot retrospectively become untouched held-out gold. Candidate-specific
branches and all permitted safe recovery options require independent validation.

The supplied [pilot review](../../src/shared-lifting-pilot-final-review.md)
checks numerical and wording consistency and explicitly disclaims novelty and
application success. It is evidence within that scope, not a recorded final
novelty/feasibility judgment or complete task/gold review. AI audits do not
replace those accountable scientific judgments.

## Exact work remaining for the original method claim

| Required work | Concrete completion evidence |
| --- | --- |
| State the distinctive technical step | Versioned pseudocode/property/quantifiers and a property-by-property comparison with exact product search, backward/symbolic or contract methods, CEGAR and credible shared/incremental summaries. Demonstrate why the same-evidence comparator does not already perform that step. |
| Establish the claimed property | Proof under explicit assumptions, independently authored checks and discriminating adversarial cases for typed frames, legal recipes, incomplete evidence, correlated histories, horizons, witness expansion and sound negative checking. If the idea is a compact proof representation, check its coverage and reconstruction rather than only counting compressed bytes. |
| Test a meaningful same-evidence advantage | Freeze the outcome, threshold, workload and resource accounting before new measurements. Compare optimized direct and applicable symbolic/backward/contract/incremental alternatives with the same observations, actions, contract and horizon. Charge full construction, querying, solving, proof/checking and invalidation costs; preserve adverse and unknown outcomes. |
| Qualify source and route fidelity | Independently review source-to-model assumptions, public alternatives, task/context/principal authority and actual crossing placements. Demonstrate both eligible independently implemented bridges and required native controls without invented inverse routes or injected losses labelled natural. |
| Complete the original application benchmark | Validate all 68 original candidate records, reference trajectories, near misses and gold obligations; resolve partial/unrealized branches. Prospectively seal genuinely independent evaluation material and settings. Preserve the original 96-task, three-path and crossing allocation requirements unless a recorded explicit scope decision changes them. |
| Confirm, reproduce and review | Execute the frozen qualified study, applicable live subset only with verified access, equal-information recovery/admission contrasts and all prescribed attempts. Reproduce headline evidence independently, report template/family dependence, and obtain recorded method/task/gold/scientific review within its actual scope. |

A compact refutation DAG, a proven exact quotient or sound dependency-based
evidence invalidation could be directions to investigate. They are hypotheses,
not implemented contributions or promised successful next steps. Ordinary DAG
sharing, quotients and invalidation also have prior art and need the same closest
method test. Choosing one without a concrete distinction would restart the
same unresolved claim under a different name.

## Paper positioning without changing the project objective

The defensible present narrative is: **an executable task-relative admission
benchmark exposing search, proof and application-utility tradeoffs**. The
central findings are the lack of shared-lifting coverage benefit against a
credible direct comparator, the measured gap between relation reuse and proof
compression, and valid-refusal versus task-completion differences on retained
original application evidence. The method should be described as a bounded
adaptation and experimental arm; the manuscript already avoids universal and
field-first claims.

This is a credible research-paper narrative, not a publication guarantee or a
substitute for independent benchmark validity. A negative study can be a result
without inventing superiority. Its significance, originality, reviewed task
validity and reproducibility still need accountable scientific judgment.
Reporting that narrative now leaves the original distinct-method and qualified
full-study work visible and unfinished. No objective or gate was changed by
this assessment.

**Assessment author:** Codex AI, `/root/agentops_task_bank`.
**Assessment type:** independent task within the same AI-assisted project,
using static source and retained evidence. **New application, solver, provider
or external-system experiment calls:** zero. **Human scientific review:** no.
