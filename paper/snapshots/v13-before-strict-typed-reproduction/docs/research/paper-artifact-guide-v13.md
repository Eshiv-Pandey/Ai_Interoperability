# Manuscript V13 evidence and build guide

The [V13 builder](../../paper/build_draft_v13.py) and [independent auditor](../../paper/audit_draft_v13.py) read the completed [V13 allocation](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/42918421487), attempt 1, and its [source-bound analysis](ap2-native-bridge-development-analysis-v13.md). Actual retention is `runs/ap2-native-bridge-development/v13/retained-42918421487-4`; the local transfer suffix is distinct from the GitHub attempt. All 104 captures verified, retaining 36 native purchase observations, 31 error-free owned-cell purchases and 39 unrealized bridge continuations. Completed failed or mixed allocations remain eligible when actual allocation/execution/evaluation records exist; workflow success is not a scientific inclusion filter. All output paths must be fresh. No application, actor, evaluator, solver or provider is executed by these manuscript tools.

The frozen [V11 manuscript](../../paper/working-draft-v11.md), its [audit](../../paper/working-draft-v11.audit.json) and all evidence inputs remain bound. A V13 successor explicitly says in its abstract that the V11 TCP matrix remained unexecuted after failed smoke verification, preserving all 104 missing matrix observations and 65 non-evaluable pairs. The [actual V12 preparation diagnostic](ap2-native-bridge-development-analysis-v12.md) remains separate: V12 stopped before real allocation, so its 104 public planned slots create no actual cell or transport-pair census.

The [actual V13 manuscript](../../paper/working-draft-v13.md), [provenance](../../paper/working-draft-v13.provenance.json) and [independent audit](../../paper/working-draft-v13.audit.json) reconstruct all 104 cells across 65 native and 39 repeated bridge initiation slots on 13 authored cases. Eight arm tables preserve closed process outcomes, verified captures, purchase observations, error-free owned-cell purchases and the stricter error-free, zero-exit/no-violation indicator. Every missing, failed, refused, unclosed or non-evaluable observation stays in its denominator. Receipt completion before a source/actor error or refusal does not become full original-task success. Bridge initiation does not become an independent task or an exercised OTP/fault continuation.

The builder verifies the completed run, retention, API artifact digest, actual archive bytes, selected archive/extraction bytes and every source-bound analysis input. Verified cells require exact captured runner and all declared helper copies, including the V13 guard helper and both V2 diagnostic helpers. Invalid source copies in already refused cells remain explicit and are not counted as verified source components. The independent auditor imports no builder or evaluator; it reconstructs the tables, all 65 purchase/error-free ASGI/TCP pairs and source-copy checks directly from the raw retained files.

The inherited V2 codec remains 26 retained proofs: 15,128 original-wrapper bytes, 11,918 DAG bytes and 7,760 direct bytes; two shrink and 24 grow. Its 31 constructed controls and separate [fresh hosted reproduction](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/42910442359) do not establish a faster checker, new method, native performance or business utility. No result is revised by the manuscript transformation.

The actual retained archive is 265,648,891 bytes, SHA-256 `07579b8221502f433adaf8aba3f96aee07501ba7914dfc443d417843efe0e988`. The analyzer's archive-size bound was aligned with the verified 300,000,000-byte retention limit; all digest and source gates were unchanged. The [read-only successor verifier](../../scripts/verify_ap2_native_bridge_development_v13.py) works with the already tracked result and compares every reconstructed field except its new `created_at_utc`. Seven constructed comparison controls and actual retained-result verification passed. The source-bound analyzer and analysis result remain byte-identical.

Read-only verification after checkout:

```powershell
python -I -S -B scripts/verify_ap2_native_bridge_development_v13.py --verify-existing --base runs/ap2-native-bridge-development/v13/retained-42918421487-4 --analysis runs/ap2-native-bridge-development/v13/analysis-42918421487-1/result.json
```

The [initial V13 build snapshot](../../paper/snapshots/v13-before-readonly-reproduction/manifest.json) preserves its manuscript, provenance, audit, documentation and build-source bytes before this reproducibility supplement and table-label clarification. To rebuild the current manuscript with fresh output paths:

```powershell
$v13Base = 'runs/ap2-native-bridge-development/v13/retained-42918421487-4'
$v13Analysis = 'runs/ap2-native-bridge-development/v13/analysis-42918421487-1/result.json'
python -I -S -B paper/build_draft_v13.py --native-analysis $v13Analysis --native-base $v13Base --output paper/working-draft-v13.md --provenance paper/working-draft-v13.provenance.json
python -I -S -B paper/audit_draft_v13.py --draft paper/working-draft-v13.md --provenance paper/working-draft-v13.provenance.json --native-analysis $v13Analysis --native-base $v13Base --output paper/working-draft-v13.audit.json
```

The registered title and 96-task, 288-path-cell and 96-crossing study remain preserved. Distinct-method novelty, candidate-specific gold and near misses, full source-to-model and unchanged bridge qualification, common-cost utility evidence, live-provider quality and accountable human novelty/feasibility/scientific review remain unresolved. A drafted manuscript and passing file/census audit do not establish publication readiness or project completion. V11, V12 diagnostics, historical captures and project-status records remain unchanged by these tools.
