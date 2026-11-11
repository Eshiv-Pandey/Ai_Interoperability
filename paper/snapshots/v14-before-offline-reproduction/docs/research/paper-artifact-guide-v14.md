# Manuscript V14 evidence and build guide

V14 is a separate successor to the frozen [V13 manuscript](../../paper/working-draft-v13.md), [provenance](../../paper/working-draft-v13.provenance.json) and [audit](../../paper/working-draft-v13.audit.json). It integrates the actual [common-cost results](common-cost-results-v1.md) from run [42927208534](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/42927208534), attempt 1. The [V14 builder](../../paper/build_draft_v14.py) reads existing artifacts; it does not execute an actor, application, evaluator, solver, checker or provider.

The retained archive is `runs/common-cost-development/v1/retained-42927208534-1/artifact.zip`, 9,438,211 bytes, SHA-256 `bc84692b270eadb32ee80c0e1c4ac594606329542d6db0852c874287c894be23`. V14 consumes only [final independent audit3](../../runs/common-cost-development/v1/read-audit-42927208534-3/result.json), SHA-256 `737ce96dfbe415898c5d7e31eb38f2f25e4fedaabaf2c622b7563a2c9b61338e`, its [1,650-cell export](../../runs/common-cost-development/v1/read-audit-42927208534-3/cells.jsonl), [complete evidence inventory](../../runs/common-cost-development/v1/read-audit-42927208534-3/evidence-files.json) and [exact auditor source](../../runs/common-cost-development/v1/read-audit-42927208534-3/auditor-source.py). Audit1/audit2 remain preserved. Audit3 binds reply/profile identities and strict certificate clock/horizon/expiry headers without reexecuting certificate semantics.

Each method retains 330 attempts: 270 certified results and 60 unknown results. Every status remains in the census. All ten same-decision certified paired cohorts contain the same 54 profiles and all five dependent timing repeats. The manuscript reports medians of per-profile median cost ratios, with explicit ratio direction; observed profile ranges are not confidence intervals. Unknown and adverse attempts retain their measurements and are excluded from cost ratios. Reason-aware logical headroom is reconstructed independently of the frozen worker's counter-only labels.

The separate [V14 auditor](../../paper/audit_draft_v14.py) reconstructs the status table and ten cost cohorts from retained closing replies/results and resource receipts, importing no builder or benchmark/runtime code. Final manuscript and provenance are `paper/working-draft-v14.md` and `paper/working-draft-v14.provenance.json`; its independent numerical/source/claim audit is `paper/working-draft-v14.audit.json`.

Current saved V13 analysis can be checked without deleting or overwriting any artifact:

```powershell
python -I -S -B scripts/verify_ap2_native_bridge_development_v13.py --verify-existing --base runs/ap2-native-bridge-development/v13/retained-42918421487-4 --analysis runs/ap2-native-bridge-development/v13/analysis-42918421487-1/result.json
```

To build V14, the output paths must be fresh. Historical V13 files and all raw captures remain unchanged:

```powershell
$costBase = 'runs/common-cost-development/v1/retained-42927208534-1'
$costAudit = 'runs/common-cost-development/v1/read-audit-42927208534-3/result.json'
python -I -S -B paper/build_draft_v14.py --cost-base $costBase --cost-audit $costAudit --output paper/working-draft-v14.md --provenance paper/working-draft-v14.provenance.json
python -I -S -B paper/audit_draft_v14.py --draft paper/working-draft-v14.md --provenance paper/working-draft-v14.provenance.json --cost-base $costBase --cost-audit $costAudit --output paper/working-draft-v14.audit.json
```

The standalone common-cost auditor supports a fresh analysis directory, so its saved audit3 need not be removed to reproduce it. The full retained source, raw outputs and exclusions remain available through the results guide.

The registered title, 96-task, 288-path-cell and 96-crossing study are unchanged. The V13 native results, V11 smoke failure, V12 preallocation diagnostic and all historical studies remain preserved. Human gold, untouched holdout/near misses, full route/source-to-model and original native-launcher qualification, provider utility, distinctive contribution and accountable final scientific review remain unresolved. A drafted successor and passing artifact audit do not establish publication readiness or whole-project completion.
