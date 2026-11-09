# Three-day implementation target: admission algorithm and benchmark

Updated 28 October 2026 from the user's latest instruction. **The 31 October
review must demonstrate a new admission algorithm and the benchmark implemented.**
A draft paper is not required this week. The proposed artifact-only direction
was not selected. Paper and offline packaging work are deferred while the
algorithm and benchmark take priority.

The user will seek additional time if at least 70% of the project is complete.
No extension has been granted, and no 70% completion claim is currently supported.
The older research-gate tracker measures the full research/paper plan; it cannot
be used as an implementation estimate. We will report runnable components,
passed acceptance checks and remaining critical work with any estimate, rather
than changing that tracker's denominator to obtain the target number.

## Required demonstration

The supervisor should be able to supply a runtime task contract, select an
eligible route/model, run the candidate admission procedure, inspect its
supported/unsupported/unknown decision and independently checked explanation,
and compare it with the baseline on the same benchmark inputs. The benchmark
must retain inputs, method/source versions, failures, costs and results.

1. **Concrete candidate mechanism.** Specify inputs, state, steps, assumptions,
   quantifiers, abstention and certificate behavior. Identify the actual
   procedure beyond the existing baseline and its strongest fair comparator.
   A new module name is insufficient. Novelty remains unestablished until the
   distinction and evidence survive review.
2. **Running algorithm.** Implement that candidate and expose a stable callable
   interface and command. A specification or source screen alone is incomplete.
3. **Correctness evidence.** Cross-check small development instances against an
   independent solver/checker; retain negative, indeterminate, stale, changed
   binding and forged-certificate cases. Match the tested property's scope.
4. **Running comparison benchmark.** Execute the candidate and applicable
   baselines with identical public inputs, contracts, horizon, clock and resource
   accounting. Report decision correctness, coverage, certificate validity,
   failures and measured costs. Charge preprocessing and checking as appropriate.
5. **Meaningful input coverage.** Keep authored finite development fixtures,
   historical protocol observations and any source-faithful route models clearly
   distinguished. A captured successful trace is not a complete action-space
   model. The two-domain and independent evaluation requirements stay open until
   actually met; no calibration or held-out tasks are consumed for this demo.
6. **End-to-end demonstration.** Show admission and benchmark execution from one
   documented launch, with inspectable outputs and clear limits. The existing
   archived browser replay can provide supporting protocol evidence; it does
   not itself run the new admission algorithm.

## Work order

| Window | Concrete output |
| --- | --- |
| Now / 28 October | Select the strongest implementable candidate mechanism; implement the comparison benchmark in parallel; update CLI and implementation tracker |
| 29 October | Complete candidate code and independent small-instance checks; connect candidate to the benchmark; retain all development failures |
| 30 October | Run the integrated demonstration, compare behavior and costs, fix substantive defects and verify the actual supervisor workflow |
| 31 October | Demonstrate the implemented algorithm and benchmark; show completed and missing requirements; obtain the supervisor's assessment and any explicit time extension |

Stop expanding paper drafts, generic provenance infrastructure or additional
shutdown trials during this window. The v12 diagnostic is complete; its positive
configured-route result is supporting evidence. Preserve all consumed v8/v9/v10/
v12 allocations. Any new application experiment needs a separate prospective
design and new output paths.

## Current starting point

As verified on 29 October, the repository has a running recipe-refinement
candidate, independent direct solver/certificate checker and comparison runner.
The [executed demonstration](admission-benchmark-results-v1.md) records 69 passing
software tests, all eleven recipe cases and a successful captured-code replay.
The [single-command walkthrough](implementation-demo-v1.md) is ready to run.
The native/bridge harness retains the separate configured-B7 success from v12.
Scientific novelty, faithful live-route admission, the qualified two-domain
benchmark and supervisor acceptance remain unresolved. Paper work stays deferred.

[Implementation status](implementation-status-v1.json) records acceptance evidence
without awarding paper/research gates or treating planned work as complete.
This plan supersedes the immediate delivery priorities in
[deadline plan v3](deadline-plan-v3.md); historical artifacts remain unchanged.
