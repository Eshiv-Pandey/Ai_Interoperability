# Original-native reference continuation results v0

**24 October 2026.** The unchanged official Carol application exhibits the reference-dependent follow-up behavior found in its source: a same-task answer with a task reference completes; the same answer with empty references remains waiting. Context alone creates a different task. These are three deliberately selected development controls on **A2A 0.3**, not MCP-bridge results, naturally observed faults, a held-out study or a novel-method result.

## Actual execution and verification

The [prepare attempt](../../runs/native-reference-continuation/carol-prepare-20261023T204454418495Z-29896/report.json) and [native run](../../runs/native-reference-continuation/carol-run-20261023T204701107557Z-24356/report.json) are both preserved. Preparation installed the original exact `a2a-sdk==0.3.0` and `uvicorn==0.35.0` requirements in a separate **Python 3.12.7** environment. The full resolved dependency/file-hash ledger was recorded before execution. The official sample pin is `6603ba3f2c31a7ef33e70b9d8b5b5f8be42ac9a3`; original application bytes and license remain in the [source archive](source-evidence/reference-continuation/runtime/original-source-manifest.json). No original file or research bridge was edited.

The run followed the unchanged [prospective specification](reference-continuation-probe-v0.md), whose recorded SHA-256 still matches. It used separate original tasks and identical one-entry shuffle requests and `Well done!` answers. There was one attempt per control, with no failed control or substituted repeat.

| Control | Observed native answer and original-task read |
| --- | --- |
| N1: original task/context, own-task reference | Both return the original IDs and completed state. |
| N2: original task/context, empty references | Both return the original IDs and input-required state. |
| N3: original context only, empty references | Answer creates a new task in that context; the original remains input-required. A separate get confirms the new task's ID/context and input-required state. |

N2/N3 are explicit authored near-miss interventions. The source dispatch tests only whether references are nonempty; these controls do not prove that Carol enforces reference-ID equality, cross-task dependency validity or authorization. A completed acknowledgement needs no new terminal artifact for this status/association goal. Do not substitute this goal for the earlier artifact-delivery contract.

The record contains **14 local HTTP exchanges: one card discovery and 13 native RPCs**, with **2,555 request-body bytes and 11,200 response-body bytes**. Counts exclude headers/framing and preparation/diagnostics, which remain recorded separately. Native methods are old-version `message/send` and `tasks/get`; task states are `input-required` and `completed`. No model call, bridge execution or A2A 1.0 application execution is in this record.

The recorded original server PID **10852** was terminated specifically after observations and its exit was awaited; the terminal flag and a separate exact-PID check confirmed cleanup. Child exit code 1 is the Windows termination outcome, while the capture driver exited 0. It is not a hidden startup or task failure. No unrelated process was killed.

## Independent software/data evidence

The [separately authored checker](reference-independent-review.md) imports no capture/application/solver logic. It reconstructs all three controls from actual raw exchanges, checks native schemas/IDs/context, UTF-8/base64/hash/JSON agreement, duplicate-key rejection, chronology, phase completeness, summaries and body-byte/request accounting. Its **31 test methods** include labelled in-memory mutations; no captured record was overwritten. The parent separately verified the stored original source and dependency/spec ledgers.

The [immutable verification](../../runs/native-reference-continuation/verification-v1.json) preserves both preparation/run attempts, checks one native execution with three controls, and passes the full **146-test** software suite. It archives exact code, tests, input runs, original source and source/dependency ledgers before checking. All 24 recorded Python implementation hashes match the archive and current source.

The [clean-interpreter replay](../../runs/native-reference-continuation/clean-replay-v1.json) imports the archived checker, rechecks the archived native input and passes all **146 tests with zero failures, errors or skips**. Its **108-file** archive matches the verification inventory and stays unchanged during replay. This is software/data reproduction in the clean Python environment; it does not rerun the native application or impersonate an independent human review.

```powershell
.\.venv\Scripts\python.exe scripts/verify_reference_continuation.py --output runs/native-reference-continuation/new-verification.json
.\.venv\Scripts\python.exe scripts/replay_reference_verification.py --verification runs/native-reference-continuation/verification-v1.json --python tmp/foundation-replay-env/Scripts/python.exe --output runs/native-reference-continuation/new-replay.json
```

Use new output paths. The verification/replay commands make no network/model call. Replaying the actual original application requires its separate pinned environment and the recorded native driver; the clean software replay alone establishes no application re-execution.

## Research consequence and next boundary

This establishes an independently existing application's task-relative reference requirement. It motivates checking the complete action interface of a bridge: typed sends may omit a field while a permitted raw send restores it. That is a source/action-space question, distinct from the rejected one-bundle observation-saving hypothesis. Exact reachability given the same guards/actions already expresses this example, so no C1 novelty or superiority follows.

The [separate port change map](source-evidence/reference-continuation/port/change-map.json) documents an authored A2A 1.0 adaptation. The [new native port specification](reference-port-native-probe-v1.md) freezes its preservation controls before execution. Its results belong to a separate record. Original A2A 0.3 success is not an unchanged native-compatible witness for either frozen 1.0 bridge, and the application is not a third bridge.

Only after a version-matched native contrast and separately specified projection/check boundary may the actual bridge paths be tested. Permit mgcrea's raw SendMessage/GetTask alternative equally to every practical comparator; a typed-only restriction cannot establish loss of the full route. Keep limitations, errors and near-miss positives. Neither one raw recovery action nor a renamed guarded-reachability analyzer establishes a new method.

**Progress remains 5%.** C1's substantive technical distinction, prospective source/model validity, a strong-comparator advantage and actual human novelty/feasibility review remain open. The original title, six-week deliverable scope, metrics plan and confirmation gates are unchanged.
