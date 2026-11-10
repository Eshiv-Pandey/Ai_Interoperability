# Verified results note: conditional admission and shared lifting

This note records implemented and verified results available on 10 November
2026. It supplies results and claim boundaries for a later paper draft.

## Implemented methods and comparison

The prototype searches finite public continuation recipes under explicit
freshness, horizon, coverage, state and binding assumptions. It returns a
supported witness, a checked complete-model unsupported certificate, or unknown
when those assumptions or the work allowance do not support a conclusive answer.
Shared lifting adds call-local prefix and relation memoization to the preserved
witness/refine traversal. It preserves correlated binding frames and exact
histories. All conclusive benchmark outputs are submitted to an independent
certificate worker; the solver and checker are timed separately.

The fixed development study contains 66 related authored profiles spanning
argument products, layered reconvergence, correlated frames, horizon boundaries
and off-goal load. Four methods receive identical inputs at budgets 32, 256,
4,096 and 100,000: legacy relational direct, goal-pruned memoized direct,
original refinement and shared lifting. Legacy direct is disclosed as both the
historical control and reference implementation. The goal-pruned direct method
is the strongest same-input comparator in this experiment.

## Certified coverage

The complete matrix retains 2,003 worker invocations and 683 accepted
certificate checks. Fresh read-only verification binds the dispatched modules,
source/input hashes, replies, decisions, checker flags and resource observations.
No planned profile is removed from the denominator. Unknown is uncertified.

| Work allowance | Legacy direct | Goal-pruned direct | Original refinement | Shared lifting |
|---:|---:|---:|---:|---:|
| 32 | 12/66 | 20/66 | 24/66 | 2/66 |
| 256 | 52/66 | 54/66 | 50/66 | 39/66 |
| 4,096 | 54/66 | 54/66 | 53/66 | 53/66 |
| 100,000 | 54/66 | 54/66 | 54/66 | 54/66 |

All methods return 28 supported, 26 unsupported and 12 unknown profiles at the
largest allowance. Shared lifting adds zero certified profiles beyond the fair
direct comparator at every tested budget. At budget 256, it loses certification
on 15 profiles certified by goal-pruned direct. These are adverse comparison
results, not evidence of superiority.

## Cache and proof costs

At allowance 100,000, total solver work across all 66 attempts is
4,292 / 3,382 / 14,518 / 46,840 units in the same method order. Total canonical
certificate size is 20,064 / 19,880 / 27,248 / 27,248 bytes. Work units count
method-specific operations; they are not hardware-equivalent costs and exclude
the checker's unavailable internal work counter.

For `scale-0031`, four stages with four parallel edges have 256 abstract paths.
Shared lifting reduces relation evaluations from 1,024 to 16 compared with
original refinement, but charged solver work rises from 5,566 to 14,773. Both
retain an 8,895-byte path-list certificate. Goal-pruned direct uses 134 solver
units and a 338-byte product certificate. Repeated relation evaluation was
removed while prefix bookkeeping and the uncompressed proof representation
remained costly. This explains this implementation's measured tradeoff; it is
not a general claim about symbolic refinement methods.

Largest-budget solver-plus-checker worker-wall sums were
16.689 / 16.861 / 16.538 / 16.896 seconds. They are single fixed-order observations
on one host. Startup/import/output are included, overlapping timings are not
added, and sequential process memory peaks are not summed. These measurements
do not establish a speed ranking.

## Actual application result

The separately provisioned standard Ubuntu native run
[42808110286](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/42808110286)
executed an original AgentOps confirmation fixture through native N11 and then
admitted configured B7. Both original tasks completed; each changed inventory
to `operational` with exactly one audit row. B7's supported certificate bound to
its original task/context and exactly one actual `SendMessage` continuation.
It used 33 of 100,000 solver work units. Independent effect, wire, startup,
asyncio, interpreter-exit and process-cleanup checks passed. Both service/client
exit codes were zero, with no forced cleanup. All 1,138 exported files and 864
staged inputs matched their recorded hashes.

This application run uses the original `refinement.evaluate` candidate through
the pending adapter. It is **not an application execution of shared-lifting v2**.
The named deterministic fixture uses the original `_ConfirmationLlm`; there
were no live model calls. Its continuation certificate remains conditional on
the declared one-step fixture relation. Original task completion and domain
effect were established separately from certificate acceptance.

## Source-to-result claim mapping

| Claim | Implementation | Evidence |
|---|---|---|
| Three-valued shared admission and checked conclusive proofs | `refinement_shared_lift_v2.py`, `shared_admission_v1.py`, `direct_goal_pruned_v2.check_certificate` | 79 focused tests; `runs/admission-demo/shared-rehearsal-1/inspection.json` |
| Same-input four-method execution and certified-coverage matrix | `shared_lifting_comparison_v3.py`, `benchmark.py`, `benchmark_resources_v1.py` | `runs/shared-lifting-scaling/v3-20261110-1/{plan,result}.json` and four verified budget bundles |
| Reduced relation checks without reduced proof size on `scale-0031` | Shared cache plus preserved path-list certificate | Largest-budget retained per-case replies and canonical certificate sizes |
| Conditional admission followed by an actual original application effect | `pending_admission.py`, `agentops_admission_control_v3.py` and independent retained-evidence validators | `runs/ci-agentops-native/download-42808110286-independent-review.json` and downloaded raw export |

The scaling plan/result SHA-256 values are
`8908356aa597363359084b641bf9ea3f79003c91337431c6671b404e811b5d8e` and
`f0ec201cf13ed4cacfd1eadc80c2700a9c562f2f5e6f3c4fb2efa02a7ec53401`.
The implementation audit is [recorded separately](../docs/research/implementation-acceptance-audit-v1.md).

## Limits of the available results

The 66 profiles are related development variants, not independent held-out
templates or application gold answers. The certificate language and boundary
assumptions restrict applicability. A single deterministic application fixture
does not demonstrate conversational performance or a second qualified domain.
The selected installed-runtime inspection does not authenticate every runtime
byte, and local record consistency does not independently authenticate captures.
No algorithmic novelty, general performance advantage or completed paper is
claimed by these results.
