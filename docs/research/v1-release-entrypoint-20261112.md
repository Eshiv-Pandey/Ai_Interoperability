# V1 implementation and development-paper package

This release packages the finite admission algorithm, fair benchmark, reproduced
development results, source-derived candidate bank, original-application
development observations and complete development manuscript. The fixed
[release plan](v1-release-plan-20261112.md) defines eight acceptance criteria.
All eight criteria are accepted in the [completed release record](v1-release-status-20261112.md).
The [independent acceptance review](v1-release-independent-acceptance-v2-20261112.md)
binds the current Linux software checks, exact paper restoration and their limits.
The earlier seven-criterion review and all failed attempts remain preserved.

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
- [Native shopper V4 paper addendum](../../paper/ap2-native-shopper-v4-development-addendum-v1.md):
  two original business attempts, zero business returns and zero receipts.

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
python -I -S -B scripts/verify_research_v1_release_v2.py --check-inputs
python -I -S -B scripts/verify_research_v1_release_v2.py --execute --output runs/v1-release-software/my-unused-allocation
```

The manual [GitHub workflow](../../.github/workflows/research-v1-release-verification-v2.yml)
uses a fresh Ubuntu 24.04 checkout with no provider secret or project runtime
dependencies. `result.json`, `plan.json`, all command streams and the complete
`retained-manifest.json` are retained, including failed allocations. Passing
software checks qualifies this bounded software package; original-application
and scientific claims rely on their separately scoped evidence.

## Verify the paper

Use the [exact-input restoration guide](paper-v15-offline-restoration-guide-v2.md)
with Python 3.12 or newer. The tested command restores missing required inputs
and runs the unchanged V15 read auditor from one fresh output allocation:

```powershell
$paperOutput = Join-Path 'runs/v1-release-paper' ('v1-release-' + [guid]::NewGuid().ToString('N'))
python -I -S -B scripts/verify_v15_paper_package_v2.py --output $paperOutput
```

The [actual isolated-checkout receipt](../../runs/v1-release-paper/clean-47439ff5-v2-1/result.json)
restores 2,995 members and ten archives, verifies all 3,468 input hashes and
passes 19 read checks. Existing evidence is verified and preserved. This
qualifies the exact paper inputs; unrelated SDK payloads remain outside the check.
The [paper artifact guide](paper-artifact-guide-v15.md) maps result-specific
reproduction and the independently inherited numerical/certificate reviews.

The later V4 addendum has a separate 48-member capture. Restore and inspect it
with the bounded restorer and reader named in its result guide. Its
[fresh-checkout review](../../runs/ap2-native-shopper-provider-development/v4/fresh-checkout-review-1/review.json)
has zero consistency questions and preserves the failed business outcome.

The next research phase must qualify the source-to-model and crossing routes,
resolve human judgments and near misses, freeze the full study prospectively,
run its declared comparisons and reproduce that study independently. Those
requirements remain recorded in the [whole-project register](project-completion-status-v1.json).
