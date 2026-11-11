# V1 implementation and development-paper package

This release packages the finite admission algorithm, fair benchmark, reproduced
development results, source-derived candidate bank, original-application
development observations and complete development manuscript. The fixed
[release plan](v1-release-plan-20261112.md) defines eight acceptance criteria.
The [independent acceptance review](overnight-v1-acceptance-review-20261111.md)
records the accepted evidence and its limits; final current-release qualification
is recorded separately when the hosted run has been retained and checked.

The original whole research project remains approximately 80% by its existing
work estimate. V1 acceptance does not complete the full registered study, human
gold, untouched holdout, distinctive-contribution assessment or final scientific
review. The manuscript reports the adverse comparison: shared lifting adds no
certified case beyond goal-pruned direct in the finite development suite.

## Read and review

- [Manuscript V15](../../paper/working-draft-v15.md): abstract, Sections 7 and
  8.12-8.15, limitations and conclusion.
- [Current claim ledger](../../paper/claim-ledger-v15.json): exact manuscript
  identity, substantive claims, evidence and explicit open scientific claims.
- [Paper artifact guide](paper-artifact-guide-v15.md): source/results/audit map.
- [Original-application profile appendix](../../paper/original-autonomous-workflow-shopper-appendix-v1.md):
  separate Workflow and shopper failures with no pooled success rate.

AI code and retained-evidence reviews are identified as AI reviews. They do not
supply human-approved gold or scientific approval. Scripted callers, finite
fixtures, native transports and provider observations retain separate labels.

## Run the algorithm and benchmark

From the repository root, Python 3.11 or newer is sufficient for this standard
library demonstration. Choose an unused output directory; an existing failed
or successful allocation is preserved.

```powershell
$demoOutput = Join-Path 'runs/admission-demo' ('v1-release-' + [guid]::NewGuid().ToString('N'))
python -I -S -B scripts/run_shared_admission_demo_v1.py --output $demoOutput --replay
```

The command checks standalone supported, unsupported, opaque-unknown and
budget-exhausted-unknown cases, runs the eleven-profile four-method benchmark,
verifies the complete bundle and executes its captured replay. Read
`result.json`, `inspection.json` and `replay-comparison.json` in the new output
directory. Unknown has no conclusive certificate; a failed run stays failed.
This demonstration makes no application or provider calls.

## Run the full release software qualification

Use Linux and Python 3.13.1 for the historical deterministic comparison. The
existing Linux coordinator owns and reaps complete process groups. The release
driver records current sources and fixtures, timeout controls, all four budgets
of the 66-profile comparison, independent bundle verification, the demo and its
replay, additional current controls and all 68 candidate-bank records.

```bash
python -I -S -B scripts/verify_research_v1_release.py --check-inputs
python -I -S -B scripts/verify_research_v1_release.py --execute --output runs/v1-release-software/my-unused-allocation
```

The manual [GitHub workflow](../../.github/workflows/research-v1-release-verification.yml)
uses a fresh Ubuntu 24.04 checkout with no provider secret or project runtime
dependencies. `result.json`, `plan.json`, all command streams and the complete
`retained-manifest.json` are retained, including failed allocations. Passing
software checks qualifies this bounded software package; original-application
and scientific claims rely on their separately scoped evidence.

## Verify the paper

Restore the exact retained evidence using the paper artifact guide and the
additive V15 offline restoration guide. Run the guide's fresh-output V15 read
audit. This rechecks manuscript/ledger identities and retained numerical/profile
claims without overwriting the published paper or executing original applications.

The next research phase must qualify the source-to-model and crossing routes,
resolve human judgments and near misses, freeze the full study prospectively,
run its declared comparisons and reproduce that study independently. Those
requirements remain recorded in the [whole-project register](project-completion-status-v1.json).
