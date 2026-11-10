# Shared-Lifting Pilot: Final Verification Review

2026-11-09

## Verdict

The shared-lifting pilot write-up is numerically sound: every figure I recomputed from the raw run files matches the documents, and its claims stay within what the data supports. Shared lifting reached the same 8 of 12 certified decisions as the other three methods at the 100,000 budget, but it did so at higher charged work and with lower coverage at small budgets, so "experimental, not an efficiency gain" is the right framing. Before this goes to a supervisor, make the seven wording and coverage fixes listed under Open issues; none changes a number.

## Scope and method

I checked the three documents (shared-lifting comparison, pilot results of 29 October 2026, and admission refinement prototype v1) against each other and against the retained run files in the repository at commit `d543135`.

- **Done:** recomputed counts, coverage, timing and memory totals from `summary.json`, `results.jsonl`, manifests and `result.json`; hashed two evidence files; counted files on disk.
- **Not done:** I did not re-run any solver, checker, replay or test suite, and I did not check the 23, 3 and 5 test counts or the 66-case v2 results.
- **Environment note:** the pilot ran on Windows, so memory figures are `PeakWorkingSetSize` observations from that host.

## Verified claims

All claims below matched the raw files exactly.

| Claim in the pilot doc | Observed in repo | Status |
| --- | --- | --- |
| 349 worker jobs | 192 solver + 109 certificate + 48 reference | Match |
| 109 accepted certificate checks, 0 rejected | 18 + 29 + 30 + 32 across budgets; 0 invalid, 0 check errors | Match |
| 1,897 manifest-listed files | 428 + 483 + 488 + 498 | Match |
| 1,989 allocation files | 1,989 files under `runs/shared-lifting-pilot/v1` | Match |
| Plan SHA-256 `8c66caa0…` | Identical | Match |
| Result audit SHA-256 `fbf07438…` | Identical | Match |
| Coverage table, all 16 cells | Shared lifting 0, 6, 7, 8 of 12; others 6, 8, 8, 8 (refinement 6, 7, 7, 8) | Match |
| 4 supported, 4 unsupported, 4 unknown at 100,000 | Same for all four methods | Match |
| Time and memory table | All four rows reproduce; peaks 21.68 to 21.80 MiB; 20 memory observations per method | Match |
| `scale-0031` work units 134, 134, 5,566, 14,773 | Identical | Match |
| `scale-0031` cache figures | 16 relation entries, 324 hits; 341 prefix entries, 255 hits; 4,901 key and 4,447 payload nodes | Match |
| Memory observed for all 349 workers | Audit file records 0 missing | Match |
| Checker allowance not a factor | No rejected certificates, so no proof hit the 2,000,000-unit limit | Consistent |

## Consistency across the three documents

The three documents agree with one another on every point I compared.

- **Arms:** `baseline`, `direct_pruned`, `candidate` and `shared_lift` map one-to-one onto Legacy direct, Goal-pruned direct, Original refinement and Shared lifting.
- **Budgets:** the prototype's 100,000 default equals the largest pilot budget.
- **Unknown results:** the persistent unknowns (incomplete coverage, opaque relations, contracted observables, stale evidence) match the prototype's rules for withholding a negative certificate.
- **Learned refutations:** the prototype binds them to a profile digest and an exact prefix, which is compatible with the invocation-local cache in shared lifting.
- **Non-claims:** novelty, 70% completion, held-out evidence, a speed ranking and supervisor extension are disclaimed the same way in all three.
- **Prefix cache:** 341 entries is exactly the full tree for 256 depth-4 paths (1 + 4 + 16 + 64 + 256).

## Open issues and recommended edits

Seven edits remain, ordered by how much a reviewer could object. None changes a reported number.

1. **Name the fair comparator.** The prototype spec requires a memoized, goal-cone-pruned direct search. That is the `direct_pruned` arm. Say so explicitly, and describe `baseline` as a historical control only.
2. **Abstraction-only control.** The spec asks for a separately labelled abstraction-only BFS. None of the four pilot arms is one, so either add it or state that it was not run.
3. **Demonstration coverage map.** The spec lists seven demonstrations, and the twelve cases appear to cover most of them, but the docs never say which case covers which. Add a short case-to-demonstration table. The typed/raw distinction and the "failing edge becomes legal" context are only inferable from case names such as `explicit-header-configuration` and `working-state-blocks-second-answer`.
4. **Schema wording.** The prototype spec says "exactly these top-level fields" but its table lists five. `schema_version` is the sixth and appears only in the sentence above the table. Add it to the table.
5. **"Four bundles."** In the pilot doc this means four budgets. Write "four budget bundles" so it does not read as the four-method benchmark.
6. **Speed caveat placement.** Shared lifting has the lowest solver-plus-checker worker wall time (4.962 s). Keep the one-observation, fixed-order, constrained-host caveat directly beside that table.
7. **Absolute paths in committed results.** Worker records contain Windows paths such as `P:\JUNKK\Also Junk\sem_7\...`. This is harmless for verification but clutter in a public repo. Consider normalizing them in future runs.

## Limits that must stay attached

The results support only an engineering-pilot reading.

- **Data:** eleven authored development cases plus `scale-0031`, a stress case chosen because it motivated caching. This is not a held-out or representative sample.
- **Meters:** work units are method-specific operations, not equal hardware costs, so the table is not a CPU-speed ranking.
- **Timing and memory:** single observations in fixed method order on a constrained host; differences are not speed or memory evidence.
- **Audit:** the independent review reconciled recorded checker acceptance but did not re-execute it, and it does not replace a fresh replay or human review. The full twelve-case pilot has not been replayed.
- **Not established:** algorithmic novelty, application success, 70% completion, supervisor extension. Shared lifting remains experimental.
