# Exact offline restoration for the V15 paper package

This additive guide closes the command gaps in the sealed [V15 paper guide](paper-artifact-guide-v15.md). It leaves all V14/V15 manuscript, provenance, ledger and audit bytes unchanged. Run from the repository root in an isolated fresh checkout with Python 3.10 or later. No application, SDK, provider, evaluator, solver or certificate checker is executed by these restoration and paper-read commands.

The [portability census](../../paper/working-draft-v15.portability-audit.json) distinguishes directly indexed inputs from exact archived members and archives reconstructed from tracked binary parts. It is a read-only current-index check. A passed isolated-checkout paper read audit is the additional packaging test; the census alone does not claim that test was executed.

Before creating the release checkout, include every exact prerequisite in the census. In particular, `runs/ci-refutation-prefix-dag-v2/retained-42910442359-1/extracted-manifest.json` is a separately generated inventory, not a ZIP member: include its existing exact bytes in the release. Include the seven current V15 package files, this guide, the portability auditor and its receipt. The repository's `.gitattributes` uses `* -text` to preserve evidence bytes.

The standard restorer binds saved run/plan/API metadata, part/index/whole-archive hashes and the complete extracted inventory. `--restore-missing` verifies every existing extracted member before exclusively creating absent members. It never overwrites a present file. A changed, unexpected, unsafe or misbound member is an error. Do not delete retained evidence to make a check pass.

First reconstruct both V8 archives needed by the inherited wrapper. The first V8 archive is an inherited wrapper prerequisite even though it supplies no new V15 result:

```powershell
python -I -S -B scripts/restore_retained_evidence_v1.py --base runs/ap2-native-bridge-development/v8/retained-42897177156-1 --index runs/ap2-native-bridge-development/v8/retained-42897177156-1/archive-parts-v1/index.json --restore-missing
python -I -S -B scripts/restore_retained_evidence_v1.py --base runs/ap2-native-bridge-development/v8/retained-42897325489-1 --index runs/ap2-native-bridge-development/v8/retained-42897325489-1/archive-parts-v1/index.json --restore-missing
python -I -S -B scripts/restore_retained_paper_evidence_v3.py --restore
```

The inherited wrapper covers the directly tracked core Linux, fifth-comparator, original AP2 V3/V4, AgentOps pilot, cache-ablation, original payment-tool V5, earlier offline original shopper V7 and governed-App V4 archives. It verifies exact archived members and adds only missing extraction files. The two V8 archives are ready before that wrapper reads them.

Restore the remaining earlier profiles and paper reproduction inventories:

```powershell
python -I -S -B scripts/restore_retained_evidence_v1.py --base runs/ap2-native-bridge-development/v9/retained-42902256098-1 --index runs/ap2-native-bridge-development/v9/retained-42902256098-1/archive-parts-v1/index.json --restore-missing
python -I -S -B scripts/restore_retained_evidence_v1.py --base runs/ap2-native-bridge-development/v10/retained-42905259371-1 --index runs/ap2-native-bridge-development/v10/retained-42905259371-1/archive-parts-v1/index.json --restore-missing
python -I -S -B scripts/restore_retained_evidence_v1.py --base runs/ap2-native-bridge-development/v11/retained-42911850107-1 --index runs/ap2-native-bridge-development/v11/retained-42911850107-1/archive-parts-v2/index.json --restore-missing
python -I -S -B scripts/restore_retained_evidence_v1.py --base runs/ap2-native-bridge-development/v12/retained-42915964952-1 --index runs/ap2-native-bridge-development/v12/retained-42915964952-1/archive-parts-v2/index.json --restore-missing
python -I -S -B scripts/restore_retained_evidence_v1.py --base runs/ap2-native-bridge-development/v13/retained-42918421487-4 --index runs/ap2-native-bridge-development/v13/retained-42918421487-4/archive-parts-v3/index.json --restore-missing
python -I -S -B scripts/restore_retained_evidence_v1.py --base runs/common-cost-development/v1/retained-42927208534-1 --index runs/common-cost-development/v1/retained-42927208534-1/archive-parts-v3/index.json --restore-missing
python -I -S -B scripts/restore_retained_evidence_v1.py --base runs/ci-manuscript-v7/retained-42891705471-1 --restore-missing
python -I -S -B scripts/restore_retained_evidence_v1.py --base runs/ci-refutation-prefix-dag-v2/retained-42910442359-1 --restore-missing
```

Use V11's complete `archive-parts-v2` index; its earlier incomplete parts remain preserved. The direct codec/manuscript ZIPs are already included in Git; their complete inventories and saved metadata must also be included.

Restore every separately reported original native/provider, Workflow and autonomous native shopper profile:

```powershell
python -I -S -B scripts/restore_retained_evidence_v1.py --base runs/ap2-original-native-provider-development/v1/retained-42982595287-1 --index runs/ap2-original-native-provider-development/v1/retained-42982595287-1/archive-parts-v3/index.json --restore-missing
python -I -S -B scripts/restore_retained_evidence_v1.py --base runs/ap2-original-native-provider-development/v2/retained-42995902326-1 --index runs/ap2-original-native-provider-development/v2/retained-42995902326-1/archive-parts-v3/index.json --restore-missing
python -I -S -B scripts/restore_retained_evidence_v1.py --base runs/ap2-original-native-provider-development/v3/retained-43014447502-1 --index runs/ap2-original-native-provider-development/v3/retained-43014447502-1/archive-parts-v3/index.json --restore-missing
python -I -S -B scripts/restore_retained_evidence_v1.py --base runs/agentops-workflow-reference-development/v1/retained-43036777469-1 --index runs/agentops-workflow-reference-development/v1/retained-43036777469-1/archive-parts-v3/index.json --restore-missing
python -I -S -B scripts/restore_retained_evidence_v1.py --base runs/agentops-workflow-reference-development/v2/retained-43055395848-1 --index runs/agentops-workflow-reference-development/v2/retained-43055395848-1/archive-parts-v3/index.json --restore-missing
python -I -S -B scripts/restore_retained_evidence_v1.py --base runs/ap2-native-shopper-provider-development/v1/retained-43038234376-1 --index runs/ap2-native-shopper-provider-development/v1/retained-43038234376-1/archive-parts-v3/index.json --restore-missing
python -I -S -B scripts/restore_retained_evidence_v1.py --base runs/ap2-native-shopper-provider-development/v2/retained-43045731741-1 --index runs/ap2-native-shopper-provider-development/v2/retained-43045731741-1/archive-parts-v3/index.json --restore-missing
python -I -S -B scripts/restore_retained_evidence_v1.py --base runs/ap2-native-shopper-provider-development/v3/retained-43055390208-1 --index runs/ap2-native-shopper-provider-development/v3/retained-43055390208-1/archive-parts-v3/index.json --restore-missing
```

Finally run a fresh read audit. This verifies all 3,468 provenance inputs, the current manuscript-bound claim ledger, byte-identical inherited V14 technical/results text and actual archive-derived native/provider/Workflow summaries:

```powershell
$paperCheck = Join-Path 'paper' ('working-draft-v15.fresh-checkout-' + [guid]::NewGuid().ToString('N') + '.json')
python -I -S -B paper/audit_draft_v15.py --draft paper/working-draft-v15.md --provenance paper/working-draft-v15.provenance.json --ledger paper/claim-ledger-v15.json --output $paperCheck
```

An optional current-index portability recheck also uses a fresh output:

```powershell
$portableCheck = Join-Path 'paper' ('working-draft-v15.portability-recheck-' + [guid]::NewGuid().ToString('N') + '.json')
python -I -S -B paper/audit_draft_v15_portability.py --output $portableCheck
```

The restore command list is prospective until the isolated-checkout receipt is retained. No successful restoration or read audit supplies independent human gold, algorithmic novelty, untouched holdout, real settlement, autonomous live-task utility or completion of the original 96/288/96 study.
