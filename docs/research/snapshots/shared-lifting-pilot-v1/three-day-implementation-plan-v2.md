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

The [original refinement candidate](admission-refinement-v1.md) implements bounded
abstract-path search, concrete recipe lifting and context-specific failed-prefix
refinement. Its three outcomes are supported with a witness, unsupported with
a certificate, and unknown when the available model or budget cannot justify
a conclusion. The [rehearsed software demo](implementation-demo-v1.md) and its
[independent audit](../../runs/admission-demo/supervisor-1/independent-audit.json)
provide existing evidence for the three outcomes, benchmark checking and replay.

The [shared-lifting implementation and four-arm harness](shared-lifting-comparison-v3.md)
are now implemented, with [23 solver tests](../../runs/refinement-shared-lift-software/v2/validation-1/result.json)
and [3 resource plus 5 comparison tests](../../runs/shared-lifting-comparison-software/validation-1/result.json)
passing, including a two-profile temporary captured replay. Independent source
reviews of the [solver](../../runs/refinement-shared-lift-software/v2/source-review-v1.json)
and [comparison/resource code](../../runs/shared-lifting-comparison-software/source-review-v1.json)
found no blocker. The 12-case, four-budget, four-arm engineering pilot (all eleven
original examples plus motivating scale-0031) is being prepared and has not run.

The completed [66-case v2 comparison](refinement-scaling-results-v2.md)
used the [frozen plan](../../runs/refinement-scaling/v2/plan.json), four budgets
(32, 256, 4096 and 100000), identical inputs and three original methods.
All four bundles passed verification, with 1,591 worker invocations and 535
accepted certificate checks. Preserve its adverse comparisons and unknowns;
it contains no shared-lifting results.

The [latest audited v4 allocation](pending-admission-live-results-v3.md)
retains 188 passing Python and 26 passing Node tests, but N11 failed readiness
before client launch. Sixteen startup samples locate dependency imports/module
initialization without proving a cause. B7 was skipped; there were zero candidate
live calls. V4 changed no host configuration or unrelated service. These software
counts overlap earlier suites and do not represent additional live successes.

## Priorities for the three days

| Date | Required work | Evidence to bring to the review |
| --- | --- | --- |
| **29 October** | Freeze the bounded 12-case engineering pilot around the completed shared-lifting code and four-arm harness. Preserve the completed v2 comparison. | Frozen pilot source/inputs/budgets and the existing focused validation receipts; no pilot result claimed. |
| **30 October** | Execute and check the frozen pilot once, then rehearse the software demo. Keep further live work dependent on a prospective resource decision and fresh plan. | Actual checked pilot/rehearsal receipts if executed, including unknowns, failed checks and solver-plus-checker resource costs; otherwise explicit pending status. |
| **31 October** | Freeze the review bundle, check its links and rehearse the eight-minute sequence. Record the supervisor's actual assessment and extension decision afterward. | Algorithm explanation, verified benchmark evidence, runnable instructions and explicit remaining work. |

Further live work requires the pending resource decision and a fresh prospective
plan. Its priorities are to investigate N11 readiness, verify normal startup and
shutdown, and only then attempt the admitted B7 case.
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
  [original solver](../../src/interoperability/refinement.py), then the
  [shared-lifting design and source](shared-lifting-design-v2.md).
- [ ] Show supported, unsupported and unknown outcomes; inspect the witness
  and negative certificate with the separate checker, and show that budget
  exhaustion remains unknown. Use the
  [demo instructions and retained receipts](implementation-demo-v1.md).
- [ ] Show the implemented four-arm benchmark and its
  [commands, source and measurement definitions](shared-lifting-comparison-v3.md).
  Keep the completed three-method v2 results and the planned four-arm pilot separate.
- [ ] Present the actual [v2 results](refinement-scaling-results-v2.md)
  **using the completed verified bundles**. Report certificate-validated conclusive
  coverage, retained unknowns and failed checks. Distinguish authored
  sufficient-budget expectations, budgeted reference abstentions and accepted
  certificates; raw decision agreement alone is insufficient. Add pilot results
  only after execution and checking, keeping its 12 authored cases explicit.
- [ ] Show input/source hashes, recorded budgets and costs, verification and
  captured-code replay using the [benchmark demo instructions](implementation-demo-v1.md).
  Keep unequal work-unit definitions and host contention visible; make no
  speed superiority or novelty claim from this matrix.
- [ ] Trace public pending state through admission to the controller's selected
  request using the [retrospective controller results](pending-admission-results-v1.md).
  Identify this as a match to a historical request, not a new candidate live run.
- [ ] Present the [audited live outcome](pending-admission-live-results-v3.md)
  and its outstanding startup/exit work without claiming strict success or
  candidate live execution.
- [ ] Agree and record the supervisor's remaining acceptance criteria and
  extension decision after the review. Use this plan and the
  [supervisor package](supervisor-package-v1.md) as the evidence index; retain
  70% as an unverified target until a denominator and assessment are agreed.

## Demonstration: eight minutes maximum

Use the [single eight-minute supervisor schedule](supervisor-package-v1.md#what-to-show-in-eight-minutes).
It covers shared lifting, the verified earlier comparison, checked pilot evidence
if available, the controller/live status and the supervisor's assessment.

Pre-open retained evidence and rehearse before the meeting. Any new execution
must use an unused output directory; shared-supervisor-1 was unused at this update.
The pending pilot and remaining live dependency do not change the scope statement above.
