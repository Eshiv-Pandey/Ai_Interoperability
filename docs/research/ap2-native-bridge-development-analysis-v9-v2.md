# Actual native V9 allocation analysis, version 2

The [retained V9 attempt](../../runs/ap2-native-bridge-development/v9/retained-42902256098-1/retention.json)
failed its separate conventional smoke before public certificate admission:
the retained worker error is `NameError: name 'append' is not defined` at
`worker` line 707. All 104 matrix cells remain unexecuted and missing, with
zero verified native or bridge captures and 65 non-evaluable ASGI/TCP pairs.
These are missing observations, not measured failed business tasks.

[Analyzer version 2](../../scripts/analyze_ap2_native_bridge_development_v9_v2.py)
corrects a metadata assumption in the preserved version 1. The historical V5
directory ends in `-2` because it was the second download allocation after a
failed transfer. The actual GitHub `run_attempt` is 1. Version 2 binds the local
transfer allocation through its plan, run ID and repository, and checks the
actual GitHub attempt separately. The historical run ID and exact archive digest,
all source hashes, case/arm/order checks and private evaluator separation are
preserved.

The [actual analysis](../../runs/ap2-native-bridge-development/v9/analysis-42902256098-2/result.json)
was generated from the retained archives without actor, evaluator, provider or
solver execution. The source-confirmed missing UTC helper is an additional
defect; the observed first error names only `append`. V9 reached no guarded
network operation, so it cannot identify the unlocated V8 network denial.

```powershell
python -I -S -B scripts/analyze_ap2_native_bridge_development_v9_v2.py --base runs/ap2-native-bridge-development/v9/retained-42902256098-1 --output runs/ap2-native-bridge-development/v9/fresh-analysis-v2/result.json
```

Use a fresh output. The original analyzer is preserved, including its rejected
historical attempt assumption. Any prospective V10 runtime uses a new allocation;
V9 evidence does not acquire native performance or full-study qualification.
