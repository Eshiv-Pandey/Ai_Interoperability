# Five-method development analysis

The final analysis preserves all **1,056 original four-method cells** and appends
the **264 separately executed constraint-pruning cells**. All 264 joins match
the exact case, family, model hash, input schema and logical clock 100, with equal
captured profile contents and horizon. The resulting matrix contains **1,320
cells**, including 461 unknowns. Unknown proof sizes remain blank.

| Allowance | Legacy direct | Goal-pruned direct | Original refinement | Shared lifting | Constraint-pruned direct |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 32 | 12/66 | 20/66 | 24/66 | 2/66 | 14/66 |
| 256 | 52/66 | 54/66 | 50/66 | 39/66 | 54/66 |
| 4,096 | 54/66 | 54/66 | 53/66 | 53/66 | 54/66 |
| 100,000 | 54/66 | 54/66 | 54/66 | 54/66 | 54/66 |

Constraint pruning adds no certified case beyond the retained goal-pruned
direct method in this suite. At allowance 100,000 the five methods charge
4,292, 3,382, 14,518, 46,840 and 4,186 method-specific operations respectively.
Their 54 accepted certificates occupy 20,064, 19,880, 27,248, 27,248 and 19,880
canonical JSON bytes respectively. These findings do not support an aggregate
shared-lifting or constraint-pruning efficiency advantage over goal pruning.
The units are method-specific charges, not equal primitive costs or CPU speed.

## Final exports

- [Scientific figure PDF](../../runs/research-analysis/v2-20261110-3/development-comparison-five-arm.pdf)
- [Scientific figure SVG](../../runs/research-analysis/v2-20261110-3/development-comparison-five-arm.svg)
- [Scientific figure PNG](../../runs/research-analysis/v2-20261110-3/development-comparison-five-arm.png)
- [All 1,320 cells](../../runs/research-analysis/v2-20261110-3/case-methods.csv)
- [Budget totals](../../runs/research-analysis/v2-20261110-3/budget-methods.csv)
- [Family totals](../../runs/research-analysis/v2-20261110-3/family-methods.csv)
- [Exact join ledger](../../runs/research-analysis/v2-20261110-3/join-ledger.csv)
- [Paired comparisons and exploratory family ranges](../../runs/research-analysis/v2-20261110-3/paired-comparisons.csv)
- [Unchanged original shared/direct paired table](../../runs/research-analysis/v2-20261110-3/paired-certification-original.csv)
- [Analysis manifest](../../runs/research-analysis/v2-20261110-3/result.json)
- [Fresh read audit](../../runs/research-analysis/v2-20261110-3-independent-review.json)

Figure caption: Five-method comparison on 66 related authored development
profiles. A shows certified coverage at the four categorical method-specific
work allowances. B shows charged solver work across all 66 profiles at allowance
100,000. C shows canonical JSON proof bytes for the 54 certified profiles per
method at allowance 100,000. D shows coverage within the five existing families
at allowance 256 for goal-pruned direct, shared lifting and constraint-pruned
direct. Every quantitative y axis starts at zero. The first four methods retain
the original Windows observations; the fifth is the separately executed Linux
supplement. Timing and OS memory measurements are not compared in this figure.

## Verification and limits

The analysis verified 10,383 original manifest-listed files and 6,228
supplemental files. The fresh read audit independently reconstructs all 264
supplemental cell decisions, work charges and certificate sizes from the retained
raw records, verifies every exact profile/clock join, reconciles all budget
totals, and compares the first 1,056 CSV dictionaries directly with the saved
v1 CSV. The original shared/direct family-resampling table is identical to v1.
No solver, checker, application or model was invoked.

The final PNG was visually inspected after reducing long vertical labels and
separating the legend from category labels. PNG/SVG/PDF format headers and
artifact hashes are checked. Earlier table and figure allocations remain in
`v2-20261110-1` and `v2-20261110-2`; numerical data did not change during layout
revision.

The four-arm evidence comes from
`runs/shared-lifting-scaling/v3-20261110-1`; the separate fifth arm comes from
`runs/guard-pruned-comparison/download-42836579527`. The original algorithm,
checker and Windows/Linux execution audits remain the authorities for execution
and certificate acceptance. This analysis is a read-only join and presentation.

All profiles are related, AI-authored development cases. Complete-family
resampling measures sensitivity to their mixture; its ranges are exploratory,
not population confidence intervals or independently held-out evidence. Human
scientific review, task-gold independence and general novelty remain unproved.

## Reproduction

The new [v2 script](../../scripts/analyze_research_results_v2.py) imports the
unchanged v1 collection, canonical encoding, aggregation and resampling helpers.
Tables need only Python's standard library:

```powershell
C:/Python313/python.exe -B scripts/analyze_research_results_v2.py --output runs/research-analysis/your-unused-table-allocation
```

Use a separate plotting environment with
[pinned requirements](../../scripts/research-analysis-requirements-v2.txt) and add
`--plot`. The actual final run reused the existing environment with Matplotlib
3.10.7, NumPy 2.5.4 and Pillow 13.0.0, without installing new dependencies:

```powershell
tmp/research-analysis-v1/Scripts/python.exe -B scripts/analyze_research_results_v2.py --output runs/research-analysis/your-unused-figure-allocation --plot
```

The [read-audit source](../../runs/research-analysis/audit-five-arm-v2.py) verifies
the named final allocation and writes a fresh unused audit receipt. Existing
allocations and receipts must not be overwritten.
