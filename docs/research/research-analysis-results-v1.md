# Reproducible development analysis

All 1,056 case-method records from 66 profiles, four budgets and four methods
were read without rerunning solvers or applications. The analysis checked the
bytes of all 10,383 manifest-listed bundle files before generating tables.

The [latest result manifest](../../runs/research-analysis/v1-20261110-3/result.json)
binds every input, output and the analysis script. The
[independent review](research-analysis-independent-review-v1.md) checks derived
values separately against the raw records.

| Allowance | Legacy direct certified | Goal-pruned direct | Original refinement | Shared lifting |
| ---: | ---: | ---: | ---: | ---: |
| 32 | 12/66 | 20/66 | 24/66 | 2/66 |
| 256 | 52/66 | 54/66 | 50/66 | 39/66 |
| 4,096 | 54/66 | 54/66 | 53/66 | 53/66 |
| 100,000 | 54/66 | 54/66 | 54/66 | 54/66 |

Shared lifting adds no certified case over goal-pruned direct in this matrix.
At the largest allowance its solver charges 46,840 operations versus 3,382
for goal-pruned direct, and its accepted proofs occupy 27,248 canonical JSON
bytes versus 19,880. Work units are method-specific operations; this is not a
hardware speed comparison. Unknowns stay in coverage denominators and have
missing proof size rather than zero bytes.

The complete exports are
[case-methods.csv](../../runs/research-analysis/v1-20261110-3/case-methods.csv),
[budget-methods.csv](../../runs/research-analysis/v1-20261110-3/budget-methods.csv),
[family-methods.csv](../../runs/research-analysis/v1-20261110-3/family-methods.csv)
and [paired-certification.csv](../../runs/research-analysis/v1-20261110-3/paired-certification.csv).
The paired table includes exploratory resampling of whole existing families.
Those ranges describe sensitivity to this development-family mixture; they
are not population confidence intervals or independent held-out evidence.

Exportable figures: [PDF](../../runs/research-analysis/v1-20261110-3/development-comparison.pdf),
[SVG](../../runs/research-analysis/v1-20261110-3/development-comparison.svg),
[PNG](../../runs/research-analysis/v1-20261110-3/development-comparison.png).
Visual inspection prompted zero-based linear axes for both bar panels; the
earlier local figure allocations remain retained. The final allocation also binds the consumed outer terminal result and records its interpreter. All data totals are unchanged.

To regenerate the tables with the standard-library interpreter:

```powershell
python -B scripts/analyze_research_results_v1.py --output runs/research-analysis/your-unused-allocation
```

To regenerate figures, install the pinned plotting dependencies in a task-local
virtual environment, then use its Python with `--plot`:

```powershell
python -m venv tmp/research-analysis-env
tmp/research-analysis-env/Scripts/python.exe -m pip --isolated install --index-url https://pypi.org/simple --only-binary=:all: -r scripts/research-analysis-requirements-v1.txt
tmp/research-analysis-env/Scripts/python.exe -B scripts/analyze_research_results_v1.py --output runs/research-analysis/your-unused-plot-allocation --plot
```

These are exploratory authored-development results, not a completed application
benchmark or an algorithmic novelty claim. The native application result uses
the original refinement candidate, not the shared-lifting successor.
