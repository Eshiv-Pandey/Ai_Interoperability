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

The [single-profile admission command and new launcher](shared-admission-command-v1.md)
now support a supplied model and the shared-lifting demonstration from one command.
The [completed shared-rehearsal-1](../../runs/admission-demo/shared-rehearsal-1/result.json)
passed all eight commands with unchanged original and frozen inputs. Its
[inspection](../../runs/admission-demo/shared-rehearsal-1/inspection.json) shows the
four standalone examples and eleven-case four-arm benchmark; its
[captured replay comparison](../../runs/admission-demo/shared-rehearsal-1/replay-comparison.json)
matched all 44 algorithm and 11 reference results except `stats.elapsed_ns`.
The command passed [eleven final focused tests](../../runs/shared-admission-software/windows-v2/result.json)
and an [independent AI source review](../../runs/shared-admission-software/source-review-v1.json).
The earlier ten-test capture overlaps these tests and is not an additional count.

The [shared-lifting implementation and four-arm harness](shared-lifting-comparison-v3.md)
are now implemented, with [23 solver tests](../../runs/refinement-shared-lift-software/v2/validation-1/result.json)
and [3 resource plus 5 comparison tests](../../runs/shared-lifting-comparison-software/validation-1/result.json)
passing, including a two-profile temporary captured replay. Independent source
reviews of the [solver](../../runs/refinement-shared-lift-software/v2/source-review-v1.json)
and [comparison/resource code](../../runs/shared-lifting-comparison-software/source-review-v1.json)
found no blocker. The [12-case engineering pilot](shared-lifting-pilot-results-v1.md) is now
complete: all eleven original examples plus motivating scale-0031, four budgets
and four arms. Its eight commands returned zero, all four bundles verified and
guards stayed unchanged. It records 349 worker jobs and 109 accepted certificate
checks without recorded errors. The [independent result audit](../../runs/shared-lifting-pilot/independent-result-review-v1.json) passed. Shared
lifting provides no certified-coverage advantage and remains experimental;
defaults are unchanged.

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

The [upstream AgentOps case loader](upstream-agentops-cases-v1.md) now preserves
21 original cases and 22 user turns in separate application/evaluator projections.
Its export, eleven focused tests and independent AI audit passed. These public
development cases overlap and have not been executed or graded as native tasks.
The [raw ADK exporter](agentops-raw-events-v1.md) and
[public-event normalizer](agentops-public-events-v1.md) now have passing focused
tests and independently audited historical exports. The
[cross-view binder](agentops-event-binding-v1.md) is independently audited, and the
[bounded restart effect checker](agentops-restart-effects-v1.md) passed 66 final
tests and an independent archived-result audit. General source-grounded
trajectory/effect grading and a faithful native case runner remain the next
benchmark implementation steps. [Gemini access](gemini-local-setup.md)
is verified for metadata and one bounded synthetic forced-tool request to the
exact AP2 model; native AP2 qualification remains open.

## Priorities for the three days

| Date | Required work | Evidence to bring to the review |
| --- | --- | --- |
| **29 October** | Completed the 12-case engineering pilot, its independent result audit and the shared-lifting supervisor rehearsal. Preserve all terminal allocations and the earlier 66-case v2 comparison. | Four verified pilot bundles and their audit; separately, the eight-command shared-rehearsal-1 receipt, checked standalone examples and matched captured replay. |
| **30 October** | Rehearse the eight-minute review using the completed software rehearsal and retained adverse pilot results. Keep further live work dependent on a prospective resource decision and fresh plan. | Actual shared-rehearsal-1 inspection/results; shared-rehearsal-2 is the next unused one-command allocation, while shared-supervisor-1 remains an optional unused direct-benchmark allocation. |
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
  Keep the completed three-method v2 results and the completed four-arm, 12-case engineering pilot separate.
- [ ] Present the actual [v2 results](refinement-scaling-results-v2.md)
  **using the completed verified bundles**. Report certificate-validated conclusive
  coverage, retained unknowns and failed checks. Distinguish authored
  sufficient-budget expectations, budgeted reference abstentions and accepted
  certificates; raw decision agreement alone is insufficient. Present the completed
  pilot's 12 authored cases, adverse results and completed independent audit explicitly.
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
It covers shared lifting, the verified earlier comparison, retained completed
pilot evidence, the controller/live status and the supervisor's assessment.

Pre-open retained evidence and rehearse before the meeting. The primary command is:

```powershell
python -B scripts/run_shared_admission_demo_v1.py --output runs/admission-demo/shared-rehearsal-2 --replay
```

Any new execution must use an unused output directory. Shared-rehearsal-1 is
consumed; shared-rehearsal-2 and the optional shared-supervisor-1 direct benchmark
were unused at this update.
The completed engineering pilot and remaining live dependency do not change the scope statement above.
