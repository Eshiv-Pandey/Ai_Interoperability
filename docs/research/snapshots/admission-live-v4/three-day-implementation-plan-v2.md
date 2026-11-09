# Three-day implementation plan: supervisor review on 31 October 2026

The deliverable for **31 October 2026** is a demonstrable admission algorithm
and an implemented, checked benchmark. **No draft paper is required this
week.** Use 29–31 October to finish the evidence, rehearse the demonstration
and present the remaining integration work accurately.

**70% is a target, not a verified percentage.** There is no agreed completion
denominator, no extension has been granted, and no human acceptance has been
recorded. The checklist below is unweighted; counting its items does not
establish a project percentage. This plan does not replace the research scope
or establish algorithmic novelty, domain qualification or comparative advantage.

## Evidence available and work in progress

The [candidate algorithm](admission-refinement-v1.md) implements bounded
abstract-path search, concrete recipe lifting and context-specific failed-prefix
refinement. Its three outcomes are supported with a witness, unsupported with
a certificate, and unknown when the available model or budget cannot justify
a conclusion. The [rehearsed software demo](implementation-demo-v1.md) and its
[independent audit](../../runs/admission-demo/supervisor-1/independent-audit.json)
provide existing evidence for the three outcomes, benchmark checking and replay.

The corrected comparison is governed by the prospective
[v2 matrix plan](../../runs/refinement-scaling/v2/plan.json): 66 development
profiles, four budgets (32, 256, 4096 and 100000), the same v1 input bytes and
evaluation clock, and three arms: legacy direct, goal-pruned direct and
refinement. Its [v2 results report](refinement-scaling-results-v2.md) is
**completed after this plan was created**: all four bundles passed verification,
with 1,591 worker invocations and 535 accepted certificate checks. Use the
actual result report, including its adverse comparisons and unknowns. The
[comparator fairness review](direct-goal-pruning-fairness-v2.md) explains the
need for goal-pruned direct comparison.

The [latest audited live allocation](pending-admission-live-results-v2.md)
retains 146 passing Python tests and 26 passing Node tests, but N11 timed out
waiting for fixture readiness before client launch. B7 was skipped and there
were zero candidate live calls. Those software receipts overlap earlier suites;
they are not additional disjoint tests or live application successes.

## Priorities for the three days

| Date | Required work | Evidence to bring to the review |
| --- | --- | --- |
| **29 October** | Finish the corrected v2 matrix and check every recorded allocation. Reconcile results with certificates, inputs and source captures. | Actual v2 results report and run receipts, including unknowns, failures, budgets, hashes and costs. |
| **30 October** | Rehearse the software demo using a fresh output allocation. Investigate the native readiness failure with a bounded diagnostic task. | New rehearsal receipt if executed; otherwise the clearly dated existing rehearsal. A precise integration blocker and next action. |
| **31 October** | Freeze the review bundle, check its links and rehearse the eight-minute sequence. Record the supervisor's actual assessment and extension decision afterward. | Algorithm explanation, verified benchmark evidence, runnable instructions and explicit remaining work. |

Remaining integration priorities are to localize the N11 readiness failure,
verify normal startup and shutdown, and only then attempt the admitted B7 case.
Any new live attempt must use a fresh allocation and satisfy N11 before B7.
The older post-`asyncio.run` exit stall was not reproduced by the latest attempt;
its cause remains open. Preserve failed attempts and consumed outputs. Avoid
simultaneous matrix workers and live launches on the resource-constrained host.

## Proposed review acceptance checklist (unweighted)

These boxes record proposed criteria for supervisor review. They do not record
human acceptance, and they do not define a percentage denominator.

- [ ] Explain the implemented refinement mechanism, its finite supplied-model
  assumptions and its stopping conditions using the
  [algorithm specification](admission-refinement-v1.md) and
  [solver source](../../src/interoperability/refinement.py).
- [ ] Show supported, unsupported and unknown outcomes; inspect the witness
  and negative certificate with the separate checker, and show that budget
  exhaustion remains unknown. Use the
  [demo instructions and retained receipts](implementation-demo-v1.md).
- [ ] Show an executable benchmark with all three comparator arms, matching
  input bytes, clock and declared budgets from the
  [v2 plan](../../runs/refinement-scaling/v2/plan.json), with the
  [fairness limitations](direct-goal-pruning-fairness-v2.md) stated.
- [ ] Present the actual [v2 results](refinement-scaling-results-v2.md)
  **using the completed verified bundles**. Report certificate-validated conclusive
  coverage, retained unknowns and failed checks. Distinguish authored
  sufficient-budget expectations, budgeted reference abstentions and accepted
  certificates; raw decision agreement alone is insufficient.
- [ ] Show input/source hashes, recorded budgets and costs, verification and
  captured-code replay using the [benchmark demo instructions](implementation-demo-v1.md).
  Keep unequal work-unit definitions and host contention visible; make no
  speed superiority or novelty claim from this matrix.
- [ ] Trace public pending state through admission to the controller's selected
  request using the [retrospective controller results](pending-admission-results-v1.md).
  Identify this as a match to a historical request, not a new candidate live run.
- [ ] Present the [audited live outcome](pending-admission-live-results-v2.md)
  and its outstanding startup/exit work without claiming strict success or
  candidate live execution.
- [ ] Agree and record the supervisor's remaining acceptance criteria and
  extension decision after the review. Use this plan and the
  [supervisor package](supervisor-package-v1.md) as the evidence index; retain
  70% as an unverified target until a denominator and assessment are agreed.

## Demonstration: eight minutes maximum

| Time | Demonstration |
| --- | --- |
| **0:00–2:00** | Explain the refinement step and show the supported witness, unsupported certificate and unknown example. |
| **2:00–4:00** | Show the corrected v2 matrix only if verified. Otherwise show its pending status and the explicitly historical verified software benchmark. |
| **4:00–5:30** | Trace the retrospective pending-state → admission → selected-request controller chain and state its limit. |
| **5:30–7:00** | Show the audited latest live failure, the software checks and the next integration task. |
| **7:00–8:00** | Obtain the supervisor's assessment, remaining acceptance criteria and decision on more time. Do not presume acceptance or an extension. |

Pre-open the linked evidence and use a completed rehearsal receipt to keep the
demonstration within eight minutes. Any new execution must use an unused
output directory. Paper writing is outside this week's review deliverables;
the wider research contribution and validation requirements remain open.

## Latest readiness for the next live attempt

The [versioned startup pipeline](pending-admission-live-plan-v3.md) is implemented and independently reviewed. Its initial Windows run recorded 62 passes and three platform-specific skips; the final changed plan/phase/chain suites passed 20 tests. The next `v4` application allocation has not been staged or launched.

A [WSL resource probe](../../runs/agentops-admission-execution/v4-resource-probe/result.json) failed before any application import, with `HCS/0x800705aa` (insufficient system resources) while Windows reported 99% memory use. The original WSL configuration stayed unchanged. Freeing host resources is the next prerequisite; no new live outcome or project percentage follows from this probe. The algorithm/benchmark demonstration remains available independently of WSL.
