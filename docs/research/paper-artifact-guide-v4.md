# Paper version 4: artifact and reproduction guide

The manuscript is [working-draft-v4.md](../../paper/working-draft-v4.md).
Its [claim ledger](../../paper/claim-ledger-v4.json) binds empirical statements
and conditional design arguments to current evidence. Its
[draft status](../../paper/draft-status-v4.json) distinguishes a full drafted
manuscript from the research validity and publication gates that remain open.
The title and registered task-relative scope are preserved.

## Read the results without rerunning experiments

| Paper item | Numerical source | Independent evidence |
| --- | --- | --- |
| Table 1: coverage at four allowances | [budget-methods.csv](../../runs/research-analysis/v1-20261110-3/budget-methods.csv) | [analysis review](research-analysis-independent-review-v1.md), [four-method result](shared-lifting-scaling-results-v3.md) |
| Table 2: paired certification and restricted family sensitivity | [paired-certification.csv](../../runs/research-analysis/v1-20261110-3/paired-certification.csv), [family-methods.csv](../../runs/research-analysis/v1-20261110-3/family-methods.csv) | [independent analysis receipt](../../runs/research-analysis/independent-review-v1.json) |
| Table 3: largest-allowance work and proof bytes | [budget-methods.csv](../../runs/research-analysis/v1-20261110-3/budget-methods.csv), [case-methods.csv](../../runs/research-analysis/v1-20261110-3/case-methods.csv) | Canonical proof rehashing and all 11,640 analysis-cell checks in the independent analysis review |
| Figure 1 | [PNG](../../runs/research-analysis/v1-20261110-3/development-comparison.png), [SVG](../../runs/research-analysis/v1-20261110-3/development-comparison.svg), [PDF](../../runs/research-analysis/v1-20261110-3/development-comparison.pdf) | Seven bound output hashes in [analysis result](../../runs/research-analysis/v1-20261110-3/result.json); prior PNG visual inspection |
| Table 4: separately labelled inner-graph control | [postcapture audit result](../../runs/abstraction-control/postcapture-20261110-v1/result.json) | [control result note](abstraction-control-results-v1.md); failed outer allocations remain preserved |
| Table 5: original AgentOps task/effect integration | [native integration review](../../runs/ci-agentops-native/download-42808110286-independent-review.json) | [application result note](ci-agentops-native-results-v1.md), downloaded raw export |
| Section 8.3: structurally complete 68-candidate bank | [complete bank receipt](../../runs/task-bank-review/complete-68-v1.json) | 34 AgentOps and 34 AP2; prospective splits, mixed AP2 workflow/boundary scope; no human-approved gold claim |
| Section 8.4: six original AP2 source boundaries in two fixed-actor passes | [source-boundary result](../../runs/ap2-task-qualification/v1-20261110-2/result.json) | [execution note](ap2-task-runtime-qualification-v1.md); zero provider requests, explicit immediate-coroutine intervention, not full shopper qualification |
| Linux deterministic reproduction | [core reproduction review](../../runs/ci-research-core/download-42819352517-independent-review.json) | [core result note](ci-research-core-results-v1.md), retained raw worker/checker bundles |

The 66 finite authored development variants are not held-out application gold.
The family-resampling ranges are exploratory composition sensitivity, not
population confidence intervals. The supplementary inner-graph control has a
weaker input specification and cannot replace the same-input direct comparator.
AgentOps uses original refinement and a deterministic confirmation fixture,
not shared lifting or a live provider model.

## Source-to-result mapping

| Component | Source |
| --- | --- |
| Original witness-lift/refine candidate | [refinement.py](../../src/interoperability/refinement.py) |
| Shared exact-prefix/relation cache adaptation | [refinement_shared_lift_v2.py](../../src/interoperability/refinement_shared_lift_v2.py), [design](shared-lifting-design-v2.md) |
| Legacy relational direct/reference and refinement certificate checking | [refinement_oracle.py](../../src/interoperability/refinement_oracle.py) |
| Strong same-input direct comparator and explicit goal-pruned negative checker | [direct_goal_pruned_v2.py](../../src/interoperability/direct_goal_pruned_v2.py), [fairness correction](direct-goal-pruning-fairness-v2.md) |
| Checked single-attempt admission adapter | [shared_admission_v1.py](../../src/interoperability/shared_admission_v1.py) |
| Four-arm run/verify implementation | [shared_lifting_comparison_v3.py](../../src/interoperability/shared_lifting_comparison_v3.py) |
| Prospective complete scaling allocation | [run_shared_lifting_scaling_v3.py](../../scripts/run_shared_lifting_scaling_v3.py), [frozen plan](../../runs/shared-lifting-scaling/v3-20261110-1/plan.json), [terminal result](../../runs/shared-lifting-scaling/v3-20261110-1/result.json) |
| Numeric analysis and standard scientific plots | [analyze_research_results_v1.py](../../scripts/analyze_research_results_v1.py) |
| Conditional original-application pending adapter | [pending_admission.py](../../src/interoperability/pending_admission.py), [agentops_admission_control_v3.py](../../scripts/agentops_admission_control_v3.py) |
| Preserved successful Linux core coordinator | [ci_research_core_v1.py](../../scripts/ci_research_core_v1.py) |
| Versioned timeout cleanup successor | [ci_research_core_v2.py](../../scripts/ci_research_core_v2.py), [actual focused results](ci-research-core-timeout-results-v2.md) |

The executed Linux core source belongs to commit
`9ef339fa349cf73b6c3558d2c3f51dc967f89444` and run
[42819352517](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/42819352517).
The original AgentOps integration belongs to commit
`76d133f3ba251ffe37e7f932cb986af8e7830f28` and run
[42808110286](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/42808110286).
The focused timeout successor belongs to commit
`bee78c1214333de70e63eaa3f1e4ac2635ef3391` and run
[42823294717](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/42823294717).
That successor has passed actual group/child cleanup tests; it has not rerun the
full matrix. These execution identities must not be conflated.

## Read-only checks

Run from the repository root with Python 3.13. The bundle verifier below uses
the trusted checkout and reads retained results; it launches no application,
model or solver worker. Repeat it for budgets 32, 256, 4096 and 100000.

```powershell
python -I -S -B -c "import sys;sys.path.insert(0,'src');from interoperability.shared_lifting_comparison_v3 import main;raise SystemExit(main(sys.argv[1:]))" verify runs/shared-lifting-scaling/v3-20261110-1/budget-100000
```

The same trusted command can verify
`runs/ci-research-core/download-42819352517/budget-100000`.
The retained independent Linux audit program reconstructs every budget result,
checks deterministic projections and invokes trusted pure certificate checkers:
[download-42819352517-audit.py](../../runs/ci-research-core/download-42819352517-audit.py).
Inspect its fixed evidence and exclusive review-output paths before any new
execution; do not overwrite its prior audit output.

Check current source/profile availability without allocating an experiment:

```powershell
python -I -S -B scripts/ci_research_core_v2.py --check-inputs
```

The paper's own reproducible standard-library audit checks all local manuscript
and guide links, citation numbering/metadata provenance, recorded evidence
hashes, table cells and numeric source mappings:

```powershell
python -I -S -B paper/audit_draft_v4.py --output paper/draft-audit-v4-reproduction-1.json
```

That command requires a new output path. A later audit needs another suffix;
it does not overwrite the retained audit or rerun application/solver experiments.

## Fresh reproduction

A new full Linux reproduction requires a distinct exclusive allocation.
The successor uses an owned POSIX session/group, subreaper adoption and confirmed
cleanup before verification or final sealing. The original successful v1 run
remains preserved independently.

```bash
python -I -S -B scripts/ci_research_core_v2.py --execute --output runs/ci-research-core/fresh-reproduction-1
```

For the prospectively prepared local four-arm driver, preparation and execution
must use the same interpreter. Preparation captures its source/profile/runtime
and resource requirements; execution refuses changed or consumed allocations.
These commands describe a new experiment and are not needed to inspect the paper.

```powershell
python -I -S -B scripts/run_shared_lifting_scaling_v3.py prepare --output runs/shared-lifting-scaling/fresh-reproduction-1
python -I -S -B scripts/run_shared_lifting_scaling_v3.py execute --output runs/shared-lifting-scaling/fresh-reproduction-1
```

Recompute numerical tables from retained results without launching any solver:

```powershell
python -I -S -B scripts/analyze_research_results_v1.py --source runs/shared-lifting-scaling/v3-20261110-1 --output runs/research-analysis/fresh-numeric-analysis-1
```

Rendering the figure additionally requires matplotlib, NumPy and Pillow. The
verified figure allocation records versions 3.10.7, 2.5.4 and 13.0.0 respectively.
Use the dedicated verified analysis environment or explicitly reproduce those
dependencies, omit `-S` so installed packages are available, add `--plot`, and
choose another fresh output allocation. Figure metadata can change across
renderings; compare underlying numeric tables and labelled values separately.

## Bibliography and claim limits

The paper reuses all 18 entries from
[references-v2.json](../../paper/references-v2.json),
[references-v2.md](../../paper/references-v2.md) and
[references-v2.bib](../../paper/references-v2.bib), preserving versions and
author order. The current audit checks all numbered citations against those
entries, validates required fields and local provenance links, and records
every entry's existing metadata limits. It does not retrieve primary sources
online or reproduce prior systems.

Important retained limits include unresolved DEEPSEC pagination, omitted
unverified quotient pagination/DOI, an arXiv-versus-related-publication
distinction for IR-MIA/Pacti, and the repeated BRIDGE author spelling/order.
No invented venue, DOI or resolved page range is inserted. A final literature
and author review remains necessary before submission.

No independent human task/gold review or supervisor novelty approval is claimed.
No AP2 provider/native/TCP run, qualified two-domain corpus, held-out application
accuracy, universal completion guarantee or shared-lifting superiority is
established. The ledger and status retain these open claims rather than granting
scientific completion merely because the manuscript is fully drafted.
