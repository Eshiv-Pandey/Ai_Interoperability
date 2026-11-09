# Check the archived restart effect

29 October 2026. The [pure effect checker](../../src/interoperability/agentops_restart_effects_v1.py)
checks a supplied before/after business snapshot pair for the historical
`Restart inventory.` fixture. The [capture driver](../../scripts/capture_restart_effect_example_v1.py)
selects its data from a passed [public/private binding](agentops-event-binding-v1.md),
verifies the input manifest and copies all evidence before executing the copied
pure checker. No application, SDK, live database or model is run.

This is a bounded evaluator consistency check. It is not an execution or grade
of any of the 21 upstream cases, live admission success, complete phase/causal
proof, authenticated human approval or continuous proof that no mutation
occurred between snapshots. It does not check `memory.db` or terminal cleanup.
The [broader grading contract](upstream-agentops-grading-contract-v1.md) remains
open; approval cases in that suite end at the pause.

## What is checked

- Complete logical business metadata, schema and columns remain unchanged.
  Service rows change only at inventory status, from down to operational;
  all incident rows remain equal. Duplicate keys and unsupported formats never
  become a conclusive positive result.
- Exactly one fresh audit is appended, preserving previous rows, with only
  its `sqlite_sequence` increment. Reusing an earlier invocation/action/target
  idempotency key contradicts a fresh effect.
- Original call ID/name/arguments, executed reply and supplied runtime identity
  agree. The capture driver also requires the actual confirmation ID and its
  `originalFunctionCall` to bind that original action, then selects the actual
  approval request and its paired snapshots.
- Stored audit actor, approver, session, invocation, action, target and rationale
  agree with the supplied evidence. Context is derived from the starting
  inventory status and actual nonresolved inventory incidents, ordered by the
  pinned source's descending `opened_at` text; ambiguous ties remain unknown.
- The executed audit uses the exact declared spotlight wrapping for rationale,
  context and detail. Only the known audit integer fields admit equal integral
  protobuf floats; booleans and other coercions fail.
- Every capture endpoint's declared precision participates in ordering and
  bracketing. The audit's seconds-precision interval must fit entirely inside
  the conservative capture bracket. Overlap that cannot establish this stays
  unknown; an authoritative clock and causal order remain unproved.

The rationale scope is explicitly limited to the independent synthetic fixture
text and the original N11 prose, `Inventory is down and INC-002 matches the
service-down runbook.` Other text, unsupported transformations and noncanonical
identities remain unknown. This checker does not implement general PII or
injection sanitization. Raw input representations are retained unchanged.

For another compatible archived binding, choose a new output:

```powershell
python -B scripts/capture_restart_effect_example_v1.py --binding PASSED_BINDING --output NEW_OUTPUT
```

The driver refuses an existing output. It records the selected original call,
confirmation, approval and execution identities; copies the entire binding and
implementation sources; saves `assessment.json`; and checks input,
implementation and captured-file preservation before `result.json`.
Manifest consistency does not authenticate a self-resealed input receipt.

## Completed validation

The [final captured suite](../../runs/agentops-restart-effects/software-v2/result.json)
passed **66 tests with zero skips**: 60 pure-API methods and six driver
regressions. Six original and captured source files stayed unchanged. Tests
cover unrelated writes, duplicate keys, attribution, unsupported inputs,
source-derived context, idempotency, exact representations, precision
uncertainty, confirmation/action substitution and typed manifest fields.

The [preliminary software-v1](../../runs/agentops-restart-effects/software-v1/result.json)
passed 43 tests, then source review identified four missing semantic guards.
It remains preserved with its original source. The final suite includes those
regressions; the two counts overlap and must not be added.

The once-only [archived N11 assessment](../../runs/agentops-restart-effects/native-v12-N11-v1/result.json)
returned **consistent on all 13 dimensions**. It derived approval exchange 7
from the recorded confirmation request, checked the eight service rows and ten
incident rows, and matched the single appended audit and sequence value.
The [assessment](../../runs/agentops-restart-effects/native-v12-N11-v1/assessment.json)
retains every raw supplied value. All input, implementation and captured-file
preservation checks passed. This allocation is consumed. It adds zero native
runs, model calls or upstream-case grades.

The [independent AI audit](../../runs/agentops-restart-effects/native-v12-N11-v1-independent-review.json)
passed **251 checks**. It verified all 69 effect files, the original/copied
63-file binding, ten software-v2 files and six original/captured sources;
reconstructed the selected payload links, state/audit delta and all 13
dimensions without invoking the checker. Monitored bytes and membership stayed
unchanged. It executed no API, comparator, exporter, SDK, database or model.
This is historical consistency review, not human acceptance or native qualification.
