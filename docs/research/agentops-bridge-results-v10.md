# AgentOps bridge and matched native controls: checked v10 results

Integrated 28 October 2026. This is one bounded development matrix using a reproduced
original AgentOps confirmation fixture and the upstream deterministic model
double. It is not a live-model study, a C1 performance experiment or a qualified
second benchmark domain. The simulated inventory effect is a SQLite state
change; synthetic A2A approver identity is not authenticated human approval.

The [prospective protocol](source-evidence/agentops-bridge-control-v1/protocol.md)
and [seal](source-evidence/agentops-bridge-control-v1/manifest.json) specify
**18 cases: 11 native profile/representation controls and 7 bridge deployment
controls**. The [terminal group](../../runs/agentops-native-eligibility/linux-bridge-v10/result.json) records
`failed`. The [final parent check](../../runs/agentops-native-eligibility/bridge-parent-check-v10.json) verifies
**2,371 exported files** and accounts for every planned case:
**18 executed, 0 skipped, 0 unexecuted**.
The executed cases contain **4 strict successes,
11 complete recorded non-successes, and
3 unknown or partial outcomes**. Skips and
unexecuted cases remain unknown; they are not negative bridge observations.
No outcome is inferred from a case name or from the source screen.

| Case and receipt | Frozen profile | Recorded status | Independent outcome | Final origin state | Effect classification | New audit rows |
| --- | --- | --- | --- | --- | --- | --- |
| [N1](../../runs/agentops-native-eligibility/linux-bridge-v10/N1.json) | amir-sync / literal | recorded | observed_non_success | input_required | unchanged | 0 |
| [N2](../../runs/agentops-native-eligibility/linux-bridge-v10/N2.json) | amir-sync / json-text | recorded | observed_non_success | input_required | unchanged | 0 |
| [N3](../../runs/agentops-native-eligibility/linux-bridge-v10/N3.json) | amir-sync / data | recorded | strict_success | completed | expected_single_effect | 1 |
| [N4](../../runs/agentops-native-eligibility/linux-bridge-v10/N4.json) | amir-stream / literal | recorded | observed_non_success | input_required | unchanged | 0 |
| [N5](../../runs/agentops-native-eligibility/linux-bridge-v10/N5.json) | amir-stream / json-text | recorded | observed_non_success | input_required | unchanged | 0 |
| [N6](../../runs/agentops-native-eligibility/linux-bridge-v10/N6.json) | amir-stream / data | recorded | strict_success | completed | expected_single_effect | 1 |
| [N7](../../runs/agentops-native-eligibility/linux-bridge-v10/N7.json) | mg-poll / literal | recorded | observed_non_success | input_required | unchanged | 0 |
| [N8](../../runs/agentops-native-eligibility/linux-bridge-v10/N8.json) | mg-poll / json-text | recorded | observed_non_success | input_required | unchanged | 0 |
| [N9](../../runs/agentops-native-eligibility/linux-bridge-v10/N9.json) | mg-poll / data | recorded | strict_success | completed | expected_single_effect | 1 |
| [N10](../../runs/agentops-native-eligibility/linux-bridge-v10/N10.json) | mg-raw-no-header / data | recorded | observed_non_success | input_required | unchanged | 0 |
| [N11](../../runs/agentops-native-eligibility/linux-bridge-v10/N11.json) | mg-raw-header / data | recorded | strict_success | completed | expected_single_effect | 1 |
| [B1](../../runs/agentops-native-eligibility/linux-bridge-v10/B1.json) | Amir ordinary typed text | recorded | observed_non_success | input_required | unchanged | 0 |
| [B2](../../runs/agentops-native-eligibility/linux-bridge-v10/B2.json) | Amir Tasks form | recorded | observed_non_success | input_required | unchanged | 0 |
| [B3](../../runs/agentops-native-eligibility/linux-bridge-v10/B3.json) | Amir MRTR opaque-state continuation | recorded | observed_non_success | input_required | unchanged | 0 |
| [B4](../../runs/agentops-native-eligibility/linux-bridge-v10/B4.json) | mgcrea typed polling text | recorded | observed_non_success | input_required | unchanged | 0 |
| [B5](../../runs/agentops-native-eligibility/linux-bridge-v10/B5.json) | mgcrea stock raw request | recorded | unknown_or_partial | input_required | unchanged | 0 |
| [B6](../../runs/agentops-native-eligibility/linux-bridge-v10/B6.json) | mgcrea public factory, passthrough fetch | recorded | unknown_or_partial | input_required | unchanged | 0 |
| [B7](../../runs/agentops-native-eligibility/linux-bridge-v10/B7.json) | mgcrea public factory, explicit version-header fetch | failed | unknown_or_partial | completed | expected_single_effect | 1 |

The outcome column comes from the recomputed whole-case checks. Strict success
requires the original task/context, a legal publicly supplied continuation,
the required completed origin state, exactly one attributed guarded effect,
no early or unrelated domain changes, the declared profile, and complete clean
process evidence. Terminal status or success prose alone is insufficient.
`not observed` records missing evidence and never means zero effects.

## Gaps, deviations and non-execution reasons

- **B5:** client:continuation_not_attempted:public_binding_not_observed.
- **B6:** client:continuation_not_attempted:public_binding_not_observed.
- **B7:** service:terminal.snapshot_missing; service_shutdown_not_clean; service_owned_group_not_initially_clean; coordinator_cleanup_errors.

The full [parent report](../../runs/agentops-native-eligibility/bridge-parent-check-v10.json) retains every nested client, origin,
effect and process diagnostic. Artifact integrity verification is distinct
from complete observations: `all_evidence_complete` is
`false`. Unknown or partial cases must
not be promoted to observed non-support. A complete recorded non-success is
limited to its fixed attempt and policy; it is not a whole-interface negative
certificate and does not eliminate other legal values, guesses or routes.

## Preparation, deployment and interpretation

The sealed [software preparation](../../runs/agentops-native-eligibility/bridge-software-preparation-v1/result.json) contains **128 passing
tests**: 87 Python bridge/checker/supervision tests,
3 observer tests and 38 Node policy/SDK
serialization tests. These are software checks, not 128 application trials.
The [prospective parent check](../../runs/agentops-native-eligibility/bridge-preparation-parent-check-v1.json) predates this execution.
The [runtime seal](source-evidence/agentops-bridge-control-v1/runtime/preparation-seal.json),
[dependency graph](source-evidence/agentops-bridge-control-v1/runtime/graph.json)
and [runtime verification](source-evidence/agentops-bridge-control-v1/runtime/runtime-verification.json)
retain the deployed package bytes and resolution checks. The frozen Node pin
is `v22.23.2` on Linux.

B1-B3 use Amir's ordinary, Tasks and MRTR public routes. B4-B5 use mgcrea's
stock typed and raw tools. B6-B7 use its unchanged public factory with explicit
fetch configuration; B6 forwards the fetch arguments and B7 inserts the scoped
`A2A-Version: 1.0` header. B7 is a configured deployment intervention, not the
stock raw default. Each bridge case depends on the prospectively declared
positive native profile checks. No native effect is itself bridge qualification.

The recorded execution interval is `2026-10-27T13:03:37.472188+00:00` through
`2026-10-27T13:18:52.231651+00:00`. It includes capture and export and is not a method
performance measurement. The group records zero installations and zero live
model calls. Earlier failures, source audits, preparation receipts, and
[v8](agentops-native-http-results-v8.md)/[v9](agentops-native-protocol-results-v9.md)
evidence remain retained. **Do not rerun the completed/attempted v8, v9 or v10
groups, or fill skipped/unexecuted rows by silently resuming this sealed matrix.**
Any additional execution requires a separately specified and versioned study.

## Method and checkpoint consequence

The [callsite-factoring screen](c1-callsite-factoring-screen-v1.md) assesses a
concrete shared serializer/continuation-summary construction and reduces it to
the equally informed interprocedural/shared-DAG comparator. No additional C1
step or advantage is demonstrated. Its separate AI critique is not independent
human scientific review. These controls strengthen bounded evidence only;
they do not repair the method distinction by themselves.

CP1 remains passed; CP2 remains in progress; verified progress stays **5%**.
A distinct method with a fair-comparator advantage, full source-to-model
fidelity, substantive second-domain qualification, actual human review,
reviewed corpus, frozen evaluations, independent scientific reproduction and
the complete paper remain open. The approved objective and scope are unchanged.
The delivery deadline remains **10 November 2026**; see the
[deadline plan](deadline-plan-v2.md).
