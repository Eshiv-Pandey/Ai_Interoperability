# Admission algorithm and development benchmark: executed results v1

Updated 29 October 2026 (Asia/Calcutta). The candidate admission algorithm and comparison benchmark now run from one command. The retained demonstration passed all ten command steps, including the captured-code replay. These are authored development results; scientific novelty, source-to-model fidelity and live admission integration remain open.

## Executed evidence

- [Prospective execution plan](../../runs/admission-demo/review-1/plan.json): exact source/input hashes, all eleven recipe cases, both methods, clock 100, 100,000 work units per solver and 30-second worker timeout; written before execution.
- [Combined software check](../../runs/admission-benchmark-software/v3/result.json): **69 tests passed** in 48.470 seconds with original and captured inputs unchanged.
- [Demonstration receipt](../../runs/admission-demo/review-1/result.json): **10 steps passed**, source/input hashes unchanged, no application requests or model calls.
- [Candidate/direct benchmark](../../runs/admission-demo/review-1/benchmark/summary.json): all eleven cases included.
- [Captured-code replay](../../runs/admission-demo/review-1/replay/summary.json): the same decisions and certificate outcomes across all eleven cases.
- [Finite baseline smoke suite](../../runs/admission-demo/review-1/finite/summary.json): four cases, four oracle agreements, three valid conclusive certificates, one unknown. This separate schema does not evaluate the recipe candidate.

## Actual decisions

Candidate and direct relational solver agree on **11/11** profiles: **4 supported, 3 unsupported, 4 unknown**. Each method has **7/7 accepted conclusive certificates**. Unknown cases retain null certificates. There are no worker errors, timeouts, false-support/refusal disagreements or failed certificate checks in this run. This is reference agreement under supplied models, not measured application accuracy.

| Development profile | Candidate | Direct | Candidate certificate |
| --- | --- | --- | --- |
| direct-public-binding | supported | supported | valid |
| fixed-text-shape-obstruction | unsupported | unsupported | valid |
| missing-public-binding-partial-coverage | unknown | unknown | none (unknown) |
| correlated-prefix-refinement | supported | supported | valid |
| raw-parameters-without-version-header | unsupported | unsupported | valid |
| explicit-header-configuration | supported | supported | valid |
| opaque-serialization | unknown | unknown | none (unknown) |
| conservative-observable-uncertainty | unknown | unknown | none (unknown) |
| atomic-public-binding-updates | supported | supported | valid |
| working-state-blocks-second-answer | unsupported | unsupported | valid |
| stale-evidence | unknown | unknown | none (unknown) |

The four unknowns expose incomplete public-binding coverage, opaque serialization, uncertain observables and stale evidence. They are retained in the denominator. Seven conclusive decisions out of eleven are algorithm coverage; this is unrelated to percentage of project completion.

## Show the refinement mechanism

The [correlated-binding witness](../../runs/admission-demo/review-1/supported.json) inspects two abstract paths, refutes one prefix and accepts `b_good_binding -> finish`. Its final public arguments and emitted request are `{"call":"call-B","target":"B"}`. The witness retains the complete binding frame and passes the separate checker. The candidate uses 47 metered work units; the direct reference also uses 47 on this example. No work-saving claim follows.

The [negative example](../../runs/admission-demo/review-1/unsupported.json) has a checked `refinement-exhaustion` certificate for the declared finite recipes. The [incomplete-input example](../../runs/admission-demo/review-1/unknown.json) returns unknown without a certificate. Neither says that every public route of an actual bridge was searched.

## Measured cost and replay

The table reports totals across eleven evaluations and seven certificate checks per method. Function times include validation/evaluation but exclude imports and process startup. Worker times include startup, imports and capture. Reference invocations are accounted separately in each summary. Parent orchestration is excluded from worker totals.

| Run | Method | Evaluation total (ms) | Certificate total (ms) | Evaluation + certificate worker total (s) |
| --- | --- | ---: | ---: | ---: |
| First run | candidate | 4.800 | 5.185 | 7.777 |
| First run | direct reference baseline | 7.265 | 5.102 | 7.971 |
| Captured replay | candidate | 5.112 | 4.359 | 5.681 |
| Captured replay | direct reference baseline | 4.851 | 5.530 | 5.724 |

The small timings vary between executions; the direct evaluator is faster in aggregate on the replay. Neither run was a statistical performance study. No speedup or superiority threshold was specified or claimed. Work counters are method-specific operations and are not normalized CPU costs.

Bundle verification passed for [266 recipe files](../../runs/admission-demo/review-1/verify.stdout.txt), [266 replay files](../../runs/admission-demo/review-1/verify-replay.stdout.txt) and [79 finite-suite files](../../runs/admission-demo/review-1/verify-finite.stdout.txt). Verification recomputes case accounting and summaries; captured replay is the separate actual algorithm re-execution.

## Limits and next implementation work

The eleven fixtures cover ten descriptive families, including related variants. They are not a qualified two-domain or held-out corpus. The direct baseline and benchmark reference share the disclosed independent reference module. Successful certificate checking establishes model-relative validity, not the truth or completeness of supplied public-recipe declarations.

The next integration step is a new continuation controller starting from an already observed public pending task: validate public bindings and route configuration, invoke admission, check the witness, then dispatch its actual public arguments. The existing language cannot discover future response identifiers, so those values must not be invented in profile updates. Source mapping and a separately allocated live check are still required. Consumed v8/v9/v10/v12 application allocations remain unchanged.

The method is a CEGAR/lazy-symbolic adaptation. Scientific novelty and advantage against strong comparators remain open. Supervisor acceptance and any extension are pending; **70% project completion is not established**. Paper work remains deferred this week.

Run the [implementation walkthrough](implementation-demo-v1.md) to reproduce the demo into a new directory. Earlier software v1/v2 receipts are preserved, including the v2 failure caused by source changes during testing.
