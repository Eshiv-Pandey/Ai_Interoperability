# Retained physical costs and phase boundaries

11 November 2026. Supplement to manuscript V14, using the completed common-cost
allocation only. This analysis executes no solver, checker, application or
provider and preserves every original measurement.

The [phase description](../runs/common-cost-development/v1/phase-description-v1/result.json)
and [independent raw reconstruction](../runs/common-cost-development/v1/phase-description-v1/independent-phase-review-v1.json)
retain all 1,650 allocations. The descriptive comparison uses the same 54
certified profiles and five dependent repeats per profile as the completed
physical-cost analysis. The 300 unknown cells remain in the original denominator
and outside certified cost ratios.

| Recorded CPU measure, milliseconds | Goal-pruned direct | Original refinement | Shared lifting |
| --- | ---: | ---: | ---: |
| Full worker lifetime | 72.310500 | 66.880500 | 81.653500 |
| Profile loading and guard | 1.000387 | 1.000582 | 1.000587 |
| Solver import and evaluation | 17.997869 | 11.998145 | 25.999833 |
| Checker import and checking | 11.999503 | 12.998977 | 12.998116 |
| Lifetime CPU minus recorded phases | 40.786180 | 40.601544 | 41.743192 |

Each entry is a median across 54 profile-level medians, each formed from five
repeats. The last row is calculated within each repeat before taking medians.
These separately summarized medians are not additive. Recorded serialization
and result-output phase CPU medians are zero at this measurement resolution;
their wall measurements are nonzero. Zero recorded CPU does not mean zero work.

The solver timer includes its import. The checker timer includes a fresh checker
namespace import as well as checking. The remaining lifetime CPU includes
interpreter startup, worker imports, unmetered glue and output, and differences
between clocks. It cannot be assigned entirely to interpreter overhead. These
records do not isolate pure algorithm CPU or predict a warmed persistent-process
result.

Original refinement has the following physical-cost observations relative to
goal-pruned direct. Ratios are calculated per profile from paired repeat medians
and then summarized across profiles.

| Measure | Median original/direct ratio | Observed minimum to maximum | Original lower / equal / higher |
| --- | ---: | --- | ---: |
| Full worker CPU | 0.926615 | 0.912693 to 1.456409 | 53 / 0 / 1 |
| Launch-to-reap wall | 0.919235 | 0.915320 to 1.464615 | 53 / 0 / 1 |
| Peak worker RSS | 0.987673 | 0.975557 to 1.002375 | 51 / 1 / 2 |

This is a descriptive advantage in the recorded cold-worker treatment. It does
not establish a general algorithm speed ranking, independent held-out utility,
new mathematical contribution or application benefit. The profile ranges are
observed extrema, not confidence intervals. Shared lifting remains more costly
than goal-pruned direct on all 54 eligible profiles for each full-worker metric,
as reported in V14.

The independent review reconstructs the phase result from all 1,650 raw after
records and captured solver replies, verifies 162 method/profile phase records
and all 54 original/direct pairs, and checks three deliberately adverse changes.
The actual request/response and allocation bytes are unchanged. A future warmed
measurement would need a new prospective protocol, allowance and allocation.
