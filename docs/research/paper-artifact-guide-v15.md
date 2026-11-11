# Manuscript V15: V1 development release paper and claim guide

The [V15 manuscript](../../paper/working-draft-v15.md) reports the implemented finite admission/certificate benchmark, its adverse shared-lifting results, physical development costs and separately allocated original-application observations. It preserves the numerical and technical sections of the frozen [V14 manuscript](../../paper/working-draft-v14.md). This is the paper package for the V1 development release due 12 November 2026 at 06:00 IST. It does not establish completion of the registered full research study or publication readiness.

Read the abstract, Sections 7 and 8.12-8.15, limitations and conclusion first. The current [claim ledger](../../paper/claim-ledger-v15.json) binds the exact V15 manuscript bytes and maps its substantive claims, section locations, quantitative values, source/artifact identities, existing validation and limitations. The old V7 ledger remains historical; it does not bind this manuscript. [V15 provenance](../../paper/working-draft-v15.provenance.json) binds every inherited V14 input and the new actual-result inputs. The [read audit](../../paper/working-draft-v15.audit.json) verifies these bytes, preserved sections, separate run denominators, current claims and local links without running an application, SDK, model, solver, evaluator or certificate checker.

| Result family | Primary guide and exact validation |
| --- | --- |
| Finite semantics, four-method matrix, fifth comparator, stress case and Linux reproduction | [Inherited V14 guide](paper-artifact-guide-v14.md), [V7 evidence guide](paper-artifact-guide-v7.md), inherited manuscript/audit identities in the V15 ledger |
| Cache ablation and earlier original AP2/AgentOps development fixtures | [V7 evidence guide](paper-artifact-guide-v7.md), raw result and independent review paths in the current ledger |
| Lossless V2 proof packaging | [Comparison](refutation-prefix-dag-comparison-v2.json), [V2 paper audit](../../paper/refutation-prefix-dag-appendix-v2.audit.json), hosted reproduction receipt in the ledger |
| Historical owned-TCP/native-bridge V8-V13 observations, including failures | [V14 guide](paper-artifact-guide-v14.md), exact V11/V12/V13 analysis/review records in the ledger |
| All 1,650 physical-cost attempts and ten paired 54-profile cohorts | [Common-cost results](common-cost-results-v1.md), [final independent audit3](../../runs/common-cost-development/v1/read-audit-42927208534-3/result.json), [V14 audit](../../paper/working-draft-v14.audit.json) |
| Scripted original native AP2/Gemini V1-V3 | [Three-run appendix](../../paper/original-native-provider-v2-appendix.md), its [provenance](../../paper/original-native-provider-v2-appendix.provenance.json), V2 semantic reconstruction and V3 raw review in the ledger |
| Original AgentOps Workflow V1-V2 | [Additive appendix](../../paper/original-autonomous-workflow-shopper-appendix-v1.md), [actual V2 results and source diagnosis](agentops-workflow-reference-results-v2.md), frozen analysis and raw-review identities in the ledger |
| Original autonomous native shopper V1-V3 | [V3 actual results](ap2-native-shopper-provider-development-results-v3.md), [V3 source diagnosis](../../runs/ap2-native-shopper-provider-development/v3/offline-analysis-43055390208-1/source-diagnosis.json), earlier V1/V2 results and separate archive identities in the ledger |

Every allocated profile keeps its own denominator and intervention. Upstream provider requests, known usage, unmeasured usage, access smoke, whole-task completion and evidence retention are different observations. The two scripted V2 completed public Tasks and demo Success receipts do not imply autonomous shopper success, settlement, hidden-effect idempotence, human gold or untouched holdout. Workflow V2 reaches all four original stages but both recommendations remain insufficient with null targets. Native shopper V1-V3 retain timeout, preflight and metadata-wiring failures.

To check a restored checkout, first use the V14 guide's exact offline restoration commands for inherited artifacts. The new appendices and actual-result guides name the saved archive parts and raw analyses for their separately retained profiles. Do not delete or overwrite a saved extraction or audit to reproduce it. Then run:

```powershell
$paperAudit = Join-Path 'paper' ('working-draft-v15.recheck-' + [guid]::NewGuid().ToString('N') + '.json')
python -I -S -B paper/audit_draft_v15.py --draft paper/working-draft-v15.md --provenance paper/working-draft-v15.provenance.json --ledger paper/claim-ledger-v15.json --output $paperAudit
```

This is a read-only artifact/claim check. It inherits the saved, byte-bound V14 numerical audit and verifies that its entire technical/result text is preserved. It rechecks the new profile summaries against their bound analyses and appendices. It does not reexecute earlier certificate semantics or establish capture authenticity, independent human scientific review or new application utility.

The first build used the following command, with all three canonical output files absent. Once released, use the fresh audit command above rather than replacing them:

```powershell
python -I -S -B paper/build_draft_v15.py --output paper/working-draft-v15.md --provenance paper/working-draft-v15.provenance.json --ledger paper/claim-ledger-v15.json
python -I -S -B paper/audit_draft_v15.py --draft paper/working-draft-v15.md --provenance paper/working-draft-v15.provenance.json --ledger paper/claim-ledger-v15.json --output paper/working-draft-v15.audit.json
```

Original study scope remains 96 tasks, 288 path cells and 96 additional crossings. Distinctive contribution, independently reviewed task/gold bank, untouched holdout, complete two-domain/source-to-model/native-route qualification and accountable final scientific review remain open. A release acceptance result must be labeled for the V1 development release and cannot be substituted for those scientific gates.
