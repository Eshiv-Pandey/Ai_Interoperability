# Inner-graph abstraction control: 10 November 2026

The separately labelled graph-only control has executed on all **66 original
development profiles**, using each supplied inner graph unchanged. It answers
the weaker graph-reachability question. It is excluded from the four-method
recipe-feasibility accuracy and work comparisons.

| Abstract graph decision | Retained goal-pruned recipe decision | Cases |
| --- | --- | ---: |
| supported | supported | 28 |
| supported | unsupported | 24 |
| supported | unknown | 12 |
| unsupported | unsupported | 2 |

The graph alone therefore supports 64 cases. Of the 26 cases where the refined
same-input direct solver certifies non-support, 24 still have an abstract graph
path. This demonstrates the importance of checking the supplied request
relations in this development suite. It does not show real application failures
or quantify error on an independently authored population. Unknown recipe cases
remain unknown and are not counted as false positives.

## Execution and accounting

The [original finite baseline](../../src/interoperability/baseline.py) and
[separately implemented finite oracle/checker](../../src/interoperability/oracle.py)
ran through captured isolated workers. The benchmark automatically inserts its
reserved baseline; the explicitly named `abstraction_only` arm therefore
duplicated the same baseline. All actual jobs are included: **330 workers**, with
**132 accepted certificate checks** across the two labels. This is 66 unique
abstract decisions, not 132 independent cases. Every worker returned zero without
a timeout and retained a memory observation. The peak process observation was
22,147,072 bytes; it includes interpreter overhead and does not establish a memory
advantage over the differently scoped recipe methods.

Both failed driver allocations are retained:

- [v1-1](../../runs/abstraction-control/v1-20261110-1/runner-failure.json) stopped
  before workers because wrapper and inner-graph IDs were incorrectly required
  to match. The actual IDs are `scale-*` and `graph-*`; neither is renamed.
- [v1-2](../../runs/abstraction-control/v1-20261110-2/runner-failure.json) executed
  every control job, then failed its outer final check because it expected only
  one algorithm while the harness inserted the reserved baseline. Its old
  198-job/66-check accounting omitted the duplicate label. Its terminal status
  remains failed.

The separate [postcapture audit](../../runs/abstraction-control/postcapture-20261110-v1/result.json)
verified **1,917 original manifest-listed files**, the one additional terminal
failure file, all graph-to-recipe digest joins, all evaluation/checker dispatches,
all case decisions and the corrected accounting. Its result is passed. It also
reverified the original high-budget recipe bundle, which was not rerun or changed.
The audit made **zero new solver, checker, application or model requests**.
The recorded original certificate acceptance is verified as a retained observation;
the postcapture audit did not re-execute certificates.

## Reproduction

The [driver](../../scripts/run_abstraction_control_v1.py) now explicitly accounts
for both baseline labels. A new full execution requires an unused output directory:

```powershell
& 'C:\Python313\python.exe' -I -S -B scripts/run_abstraction_control_v1.py run --source-bundle runs/shared-lifting-scaling/v3-20261110-1/budget-100000 --output runs/abstraction-control/next-unused
```

The preserved v1-2 capture and its successful separate audit are evidence for
the table above. Current corrected driver bytes are a successor, not the source
that produced that capture. Each allocation retains its own exact driver source.
Source hashes establish file consistency, not signed execution provenance, human
review, source-to-model fidelity or study-wide qualification.
