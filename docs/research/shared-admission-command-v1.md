# Run one supplied profile with shared lifting

The [single-profile command](../../src/interoperability/shared_admission_v1.py)
accepts either `shared_lift` or the corrected `direct_pruned` comparator. It
requires an explicit evaluation clock and positive work budget. The existing
admission command and solver defaults are unchanged.

From the project root:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location).Path 'src'
python -B -m interoperability.shared_admission_v1 --input examples/refinement-development/04-correlated-prefix-refinement.json --method shared_lift --work-budget 100000 --now 100 --output runs/admission-demo/single-shared-1.json
```

Use an unused output filename. `--input` accepts a supplied
`recipe-continuation/1` profile; use `--method direct_pruned` with a different
output filename for the corrected comparator. Clock 100 is the declared clock
for these development examples, not a live freshness assertion.

The result file retains the supplied model, raw input hash, canonical model hash,
source hashes, full solver result and independent certificate-check outcome.
`recorded` means the command produced a well-formed result and any conclusive
certificate was accepted. It does not mean the route is supported: inspect
`result.decision` for `supported`, `unsupported` or `unknown`. A rejected
certificate or execution error gives a nonzero command exit and remains in its
reserved output. Invalid command options or JSON are rejected before evaluation.

The independent checker is
[`direct_goal_pruned_v2.check_certificate`](../../src/interoperability/direct_goal_pruned_v2.py),
which handles the existing witness and both negative certificate kinds. Unknown
results carry no conclusive certificate and do not invoke the checker. The work
budget applies to the selected solver; the checker retains its existing separate
check budget. The receipt measures evaluation and checking separately, without
claiming a hardware-equivalent cost across algorithms.

## One command for the supervisor rehearsal

The [new launcher](../../scripts/run_shared_admission_demo_v1.py) runs four
individual shared-lifting examples: a supported witness, an unsupported
certificate, an opaque unknown and a one-unit budget-exhausted unknown. It then
runs and verifies all eleven original development cases with all four methods.
The optional replay runs captured source into a separate new directory and
compares every full result and certificate, excluding only `stats.elapsed_ns`.

```powershell
python -B scripts/run_shared_admission_demo_v1.py --output runs/admission-demo/shared-rehearsal-2 --replay
```

The launcher freezes its source and inputs before execution, retains command
stdout/stderr and checks that original and frozen inputs remain unchanged. Open
`result.json` for overall command status and `inspection.json` for the three
checked examples, budget abstention and four-method comparison. An existing
allocation, including a failed one, is refused.

The [first completed rehearsal](../../runs/admission-demo/shared-rehearsal-1/result.json)
passed all eight commands with unchanged original and captured inputs. Its
[inspection output](../../runs/admission-demo/shared-rehearsal-1/inspection.json)
contains the four standalone examples. Each benchmark method returned 4
supported, 3 unsupported and 4 unknown cases; all 7 conclusive certificates per
method were accepted. Both the original and replay bundles verified, with 83
workers and 28 accepted certificate checks each. The
[replay comparison](../../runs/admission-demo/shared-rehearsal-1/replay-comparison.json)
matched all 44 algorithm results and 11 reference results, excluding only
`stats.elapsed_ns`. The used `shared-rehearsal-1` allocation must not be rerun;
`shared-rehearsal-2` was unused when these instructions were updated.

The [independent AI result audit](../../runs/admission-demo/shared-rehearsal-1-independent-review.json)
passed with zero discrepancies. It checked 906 manifest-listed files, all
command/worker records and semantic replay, and confirmed that all 975 files in
the completed allocation were unchanged. This reconciles retained checker
replies; it does not claim a fresh checker execution or human approval.

The [final focused validation](../../runs/shared-admission-software/windows-v2/result.json)
passed all eleven tests from captured source with no skips or changed inputs.
They include actual witnesses and both negative certificate kinds, unknowns,
forged-certificate rejection, exact Boolean checker acceptance, JSON type-changing
mutation, malformed input/results and preservation of failed output files. The
earlier ten-test capture remains preserved under `windows-v1`; the two counts
overlap and must not be added together.
The [independent AI source review](../../runs/shared-admission-software/source-review-v1.json)
confirmed the final result-format fix and found no unresolved source issue.

This is a local implementation demonstration over authored finite models. It
does not send a request to an application, qualify a second domain, establish
scientific novelty or verify a project completion percentage. The
[completed pilot](shared-lifting-pilot-results-v1.md) remains the evidence for
the cache tradeoffs; the [live integration gap](pending-admission-live-results-v3.md)
remains open.
