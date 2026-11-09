# Shared-lifting engineering pilot: 29 October 2026

The shared-lifting implementation and four-method benchmark ran successfully.
All four bundles passed verification, with **349 worker jobs and 109 accepted
certificate checks**. The [independent result audit](../../runs/shared-lifting-pilot/independent-result-review-v1.json)
reconciled all 1,897 manifest-listed files and all 1,989 allocation files stayed
unchanged during review. No discrepancy, worker error or rejected certificate
was recorded, and the frozen source/input guards stayed unchanged. Shared lifting remains an
experimental option: it reduced repeated relation evaluation, but its added
cache work reduced conclusive coverage at smaller declared budgets.

This pilot uses all eleven original recipe examples plus `scale-0031`, the
previously observed stress case that motivated caching. That extra case was
deliberately selected; the twelve cases are authored development inputs, not a
held-out or representative application study. The existing
[66-case three-method results](refinement-scaling-results-v2.md) are unchanged.

## Certificate-validated coverage

Every count includes all twelve planned cases in the denominator. Unknown is a
valid abstention, not a negative decision or an accepted certificate.

| Work budget | Legacy direct | Goal-pruned direct | Original refinement | Shared lifting |
| ---: | ---: | ---: | ---: | ---: |
| 32 | 6/12 | 6/12 | 6/12 | 0/12 |
| 256 | 8/12 | 8/12 | 7/12 | 6/12 |
| 4,096 | 8/12 | 8/12 | 7/12 | 7/12 |
| 100,000 | 8/12 | 8/12 | 8/12 | 8/12 |

At 100,000, all four methods return **4 supported, 4 unsupported and 4 unknown**.
The shared solver's persistent unknowns retain incomplete coverage, opaque
relations, uncertain contracted observables and stale evidence. At lower budgets,
additional cases exhaust their work allowance. Every outcome and reason remains
in the [complete result](../../runs/shared-lifting-pilot/v1/result.json).

Work units are method-specific operations, not equal hardware costs. Shared
lifting explicitly charges cache keys, lookups, payload traversal and histories
in addition to the preserved search charges. This table compares the declared
meters; it does not establish a CPU-speed ranking.

## What happened in the motivating case

All methods certify `scale-0031` as unsupported at the largest allowance.

| Method | Relation work | Search size | Solver work units |
| --- | ---: | ---: | ---: |
| Legacy direct | 16 assignments | 4 product states | 134 |
| Goal-pruned direct | 16 assignments | 4 product states | 134 |
| Original refinement | 1,024 checks | 256 abstract paths | 5,566 |
| Shared lifting | 16 checks | 256 abstract paths | 14,773 |

The new solver records 16 complete relation-cache entries and 324 hits, plus
341 prefix-cache entries and 255 hits. Its key and payload work contributes
4,901 and 4,447 units respectively. Reuse removes duplicate relation evaluation,
but all 256 paths and refutations remain. The unchanged negative checker still
reconstructs the proof without the solver cache. These observations support
retaining shared lifting for inspection and further engineering, without
promoting it as an efficiency improvement.

## Retained time and memory observations

The following are totals over all twelve cases at budget 100,000. Each method
has twelve solver workers and eight certificate workers. The reference and
outer coordinator are recorded separately. These are single observations in
fixed method order on a resource-constrained host; differences are not speed
or memory-superiority evidence.

| Method | Solver function, ms | Checker function, ms | Solver + checker worker wall, s | Maximum process peak, MiB |
| --- | ---: | ---: | ---: | ---: |
| Legacy direct | 17.099 | 6.216 | 5.889 | 21.68 |
| Goal-pruned direct | 5.641 | 4.116 | 5.904 | 21.76 |
| Original refinement | 11.418 | 37.619 | 5.262 | 21.80 |
| Shared lifting | 16.420 | 27.163 | 4.962 | 21.79 |

Function timings are contained within worker wall time; do not add those columns.
Worker wall includes process startup, imports and output. Process memory is the
OS high-water observation before final reply output, including interpreter and
input overhead; the table reports a maximum across workers, not their sum or
solver-only allocation. All eighty method/checker workers in this high-budget
slice have a memory observation. The independent audit confirmed observations
for all 349 pilot workers, with none missing. Other budgets, reference workers, preparation,
serialization, missing counts and per-case observations remain in the raw result.
See the [measurement contract](shared-lifting-comparison-v3.md).

## Evidence and demonstration

- [Prospective plan](../../runs/shared-lifting-pilot/v1/plan.json), SHA256
  `8c66caa0467f09588a533019526df2401f1ac526cd53b7aa364961bffe612265`.
- [Complete result and eight command receipts](../../runs/shared-lifting-pilot/v1/result.json).
- Bundle summaries at [32](../../runs/shared-lifting-pilot/v1/budget-32/summary.json),
  [256](../../runs/shared-lifting-pilot/v1/budget-256/summary.json),
  [4,096](../../runs/shared-lifting-pilot/v1/budget-4096/summary.json) and
  [100,000](../../runs/shared-lifting-pilot/v1/budget-100000/summary.json).
- [Prospective independent review](../../runs/shared-lifting-pilot/source-review-v1.json)
  verified exact membership and all 51 originals and 51 snapshots before execution.
- [Independent result reconciliation](../../runs/shared-lifting-pilot/independent-result-review-v1.json),
  SHA256 `fbf07438a0f58aa921a309f7a27705e45c76dc73b6f3d97c8608b71e634e69b7`.
  This read-only audit invoked no project code, tests, solvers, checkers or replay.
- [Algorithm, software tests and comparison source reviews](shared-lifting-comparison-v3.md).

The twelve-case allocation is consumed. Do not rerun its driver. Read-only
verification of the retained high-budget bundle uses its captured source:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location).Path 'runs/shared-lifting-pilot/v1/source'
python -B -m interoperability.shared_lifting_comparison_v3 verify runs/shared-lifting-pilot/v1/budget-100000
```

Captured-code replay was exercised by the focused two-case harness; the entire
twelve-case pilot has not been replayed. The independent audit reconciles its
recorded execution; it does not substitute for a fresh replay or human review.
Use the [supervisor guide](supervisor-package-v1.md) to present this implementation
and the preserved larger comparison. The live-startup gap remains in the
[v4 report](pending-admission-live-results-v3.md). No application success,
algorithmic novelty, 70% completion or supervisor extension follows from this pilot.
