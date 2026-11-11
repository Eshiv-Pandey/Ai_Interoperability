# Verified results: minimum review guide

11 November 2026. The current whole-project work estimate is **80%**, rounded
from **77.5%**, with approximately **10 percentage points of uncertainty**.
The [estimate](whole-project-progress-estimate-v8.json) preserves the original
weights `[25, 20, 10, 20, 10, 15]` and scores `[85, 75, 60, 60, 90, 95]`:
`sum(weight * score) / 100 = 77.5`. The inherited nearest-five rule gives 80.
This is approximate work completion; the [project register](project-completion-status-v1.json)
still records `whole_project_complete: false` and preserves the original scope.

Read these three files, in order:

1. [Common physical-cost results](common-cost-results-v1.md): the complete
   1,650-cell census, all ten paired comparisons, adverse shared-lifting costs
   and measurement/certificate caveats.
2. [AP2 native V13 results](ap2-native-bridge-development-analysis-v13.md): the
   complete 104-capture matrix, original payment observations, failed legal
   bridge initiation and native/ASGI correspondence.
3. [Working manuscript V14](../../paper/working-draft-v14.md): the integrated
   research argument, verified results and explicit limits. It remains a
   development manuscript while the registered full study is incomplete.

The concrete completed evidence is:

- **AP2 V13: all 104 captures verified**, comprising 65 native policy cells and
  39 legal bridge initiation cells over 13 authored cases. The native cells
  contain 36 purchase observations, including 31 error-free owned-cell purchase
  observations. All 65 same-case native/ASGI pairs are evaluable and reproduce
  the earlier purchase indicators. All 39 bridge initiation replies are tool
  errors; subsequent OTP/fault continuations remain unrealized. There are no
  missing matrix cells or recorded raw safety violations. These observations
  do not establish financial settlement, full shopper-task completion, original
  native-launcher/provider qualification or human gold.
- **Common cost: all 1,650 allocations measured**, over 66 authored profiles,
  five methods and five timing repeats. Each method has 140 certified supported,
  130 certified unsupported and 60 unknown cells; all 300 unknown cells retain
  their actual resources. There are no failures, timeouts, stopped/unstarted
  cells, certified contradictions or headroom-label discrepancies. Every one
  of the ten paired cost cohorts contains 54 same-decision certified profiles
  with all five repeats and nonbinding declared logical/CPU/wall limits.

The shared-lifting result is unfavorable in this capture. Shared/direct ratios
of the paired five-repeat medians have descriptive medians **1.130 CPU**,
**1.115 outer wall** and **1.055 peak RSS** against goal-pruned direct. Shared
lifting costs more on all 54 eligible profiles for each metric, with no added
certified coverage. These are related authored profiles, not 330 independent
tasks or proof of general algorithmic superiority. Full-lifetime startup,
loading, solving, independent checking and output costs are included; Linux RSS
is observed, and `RLIMIT_AS` is the enforced address-space limit.

The linked results guides contain exact run/source/archive identities and raw
audits. A fresh checkout first needs the ZIPs and their extracted members.
Run these offline prerequisites from the repository root:

```powershell
python -I -S -B scripts/restore_retained_paper_evidence_v3.py --restore
python -I -S -B scripts/restore_retained_evidence_v1.py --base runs/ap2-reference-development/v5/retained-42881390576-2 --restore-missing
python -I -S -B scripts/restore_retained_evidence_v1.py --base runs/ap2-native-bridge-development/v11/retained-42911850107-1 --index runs/ap2-native-bridge-development/v11/retained-42911850107-1/archive-parts-v2/index.json
python -I -S -B scripts/restore_retained_evidence_v1.py --base runs/ap2-native-bridge-development/v12/retained-42915964952-1 --index runs/ap2-native-bridge-development/v12/retained-42915964952-1/archive-parts-v2/index.json
python -I -S -B scripts/restore_retained_evidence_v1.py --base runs/ap2-native-bridge-development/v13/retained-42918421487-4 --index runs/ap2-native-bridge-development/v13/retained-42918421487-4/archive-parts-v3/index.json
python -I -S -B scripts/restore_retained_evidence_v1.py --base runs/common-cost-development/v1/retained-42927208534-1 --index runs/common-cost-development/v1/retained-42927208534-1/archive-parts-v3/index.json
```

The first command restores inherited manuscript/V7/V8 evidence. V5 uses its
checked-in ZIP; V11/V12 supply inherited provenance through their legacy part
indices; V13 and common cost use the current part indices. The new
[bounded restorer](../../scripts/restore_retained_evidence_v1.py) verifies saved
retention/API digests, part identities, safe ZIP members and the exact extraction
manifest with 256 KiB streaming buffers, a 300 MB compressed bound and a 2 GB
expanded bound. By default, existing extraction must be complete and exact.
V5's explicit `--restore-missing` handles its checked-in partial extraction:
every present file must be an exact expected member before missing files are
added exclusively. Extra, changed or linked files are refused before any
retained writes. Present evidence is never overwritten.

With the retained archives and extracted members available, these commands
reconstruct or verify the analyses without rerunning an application, solver,
checker or provider:

```powershell
python -I -S -B scripts/verify_ap2_native_bridge_development_v13.py --verify-existing --base runs/ap2-native-bridge-development/v13/retained-42918421487-4 --analysis runs/ap2-native-bridge-development/v13/analysis-42918421487-1/result.json
python -I -S -B runs/common-cost-development/v1/read-audit-42927208534-3/auditor-source.py --base runs/common-cost-development/v1/retained-42927208534-1 --output runs/common-cost-development/v1/read-review-user-1
```

The second command requires a fresh output directory. The preserved
[common-cost audit](../../runs/common-cost-development/v1/read-audit-42927208534-3/result.json)
and [native analysis](../../runs/ap2-native-bridge-development/v13/analysis-42918421487-1/result.json)
remain unchanged. The independent audits verify captured acceptance receipts
and their source/result bindings; common-cost certificate semantics are not
reexecuted by the read auditor.

Reaching 100% still requires the original **96-task, 288-path-cell and 96
additional crossing study**, including its declared comparisons and ablations;
independent human gold, untouched holdout and near misses; complete route,
source-to-model, original native-launcher and applicable provider qualification;
full-study reproduction and analysis; and contribution assessment plus the
final manuscript, accountable authorship/AI disclosure and actual human
scientific review. The completed development lanes supply concrete evidence
for that work without replacing those requirements.
