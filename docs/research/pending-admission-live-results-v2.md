# Live admission integration: v3 allocation, 29 October 2026

The latest native N11 attempt **timed out waiting for fixture readiness before
the client launched**. It produced no captured client or ASGI requests, no task
completion evidence and no application-effect evidence. The admitted B7 case
was **skipped** because its native prerequisite did not qualify. There are
**zero candidate live calls** in this allocation.

The [independent exported-evidence audit](../../runs/agentops-admission-execution/v3/independent-review/result.json)
reproduced the incomplete outcome from the captured checkers and found no
integrity discrepancies. The [group result](../../runs/agentops-admission-execution/v3/export/workspace/runs/agentops-admission-live-v1/attempt/result.json)
remains `attempts_recorded`; neither case achieved `strict_success`.

This report covers the new v3 allocation. The unchanged
[earlier live-results report](pending-admission-live-results-v1.md) preserves
the v2 attempt, which completed its task but failed after `asyncio.run` returned.
The latest attempt did not reach or reproduce that exit-stall boundary.

## Frozen allocation and software validation

The fresh workspace was
`/var/tmp/agentops-admission-live-v1-341ec982771b4691`. Its
[preparation/2 plan](../../runs/agentops-admission-execution/v3/export/workspace/runs/agentops-admission-live-v1/preparation/plan.json)
fixed 702 staged inputs, including the original application source, tests and
fixtures. Existing Python and bridge runtimes were reused at their recorded
absolute locations. All staged input bytes remained unchanged.

The retained [software-phase receipts and logs](../../runs/agentops-admission-execution/v3/export/workspace/runs/agentops-admission-live-v1/phase-software/result.json)
show **146 Python tests and 26 Node tests passed**:

| Python suite | Passed |
| --- | ---: |
| Independent admitted-client checker | 17 |
| Live plan/coordinator v2 | 9 |
| Evidence exporter v1 | 15 |
| Public pending-state adapter | 25 |
| Recipe-refinement solver/checker | 32 |
| Owned-child cleanup | 8 |
| Interpreter-exit observer | 12 |
| Interpreter-exit checker | 18 |
| Refinement scaling generator | 10 |
| **Python total** | **146** |

The Node controller/client suite passed 26 tests. The audit checked the actual
suite summaries, process return codes and stream hashes. These suites overlap
historical validation; their totals are not additional disjoint tests or live
application successes. The audit did not rerun them.

## Actual startup and cleanup outcome

The [N11 result](../../runs/agentops-admission-execution/v3/export/workspace/runs/agentops-http-control/admission-live-v1-N11/result.json)
records `TimeoutError: Fixture readiness deadline`. Its service process, PID
785, retained exactly two startup markers across the two diagnostic journals:

1. `interpreter_exit_observer_installed`
2. `asyncio_run_entered`

There was no readiness marker, service result, service state/wire capture,
client directory, client process receipt or evaluator directory. Neither
journal reached an entrypoint-return, watchdog-arm or exit boundary. Both
traceback files and both service console streams were empty. These observations
locate the incomplete attempt before readiness; they do not establish a
specific startup subsystem cause.

The service required SIGTERM and returned **-15**. The new owned-child receipt
records that the child was **reaped before group inspection**. The subsequent
group snapshot was already empty, required no group signal and contained no
cleanup errors. This is coherent cleanup evidence for the failed startup; the
service still did not exit normally without intervention.

| Retained check | Valid | Complete | Recorded limitation |
| --- | --- | --- | --- |
| [Native case](../../runs/agentops-admission-execution/v3/export/workspace/runs/agentops-http-control/admission-live-v1-N11/case-check.json) | Yes | No | Missing executed client `config.json` |
| [Service/effect](../../runs/agentops-admission-execution/v3/export/workspace/runs/agentops-http-control/admission-live-v1-N11/check.json) | Yes | No | Missing `service-result.json`; no task/effect established |
| [Asyncio shutdown](../../runs/agentops-admission-execution/v3/export/workspace/runs/agentops-http-control/admission-live-v1-N11/diagnostic-check.json) | Yes | No | `incomplete_before_supported_boundary` |
| [Interpreter exit](../../runs/agentops-admission-execution/v3/export/workspace/runs/agentops-http-control/admission-live-v1-N11/interpreter-exit-check.json) | No | No | Required `service-result.json` absent |

The exported interpreter-exit checker was rerun read-only. Its missing-file
error contains the relocated Windows path and platform wording; the original
Linux error remains unchanged. Both reports identify the same absent service
result and agree on every other field. No lifecycle or exit-stall trace was
invented to fill that gap.

The [B7 skip record](../../runs/agentops-admission-execution/v3/export/workspace/runs/agentops-admission-live-v1/attempt/B7.skipped.json)
remains explicit, and no B7 case directory exists. Certificate-to-ASGI linkage
for a live candidate request is therefore unexecuted.

## Runtime, host configuration and evidence integrity

The [after-inspection](../../runs/agentops-admission-execution/v3/export/workspace/runs/agentops-admission-live-v1/phase-after/result.json)
passed. The retained Python before/after inspection files are byte-identical.
Bridge verification also matched: **2,938 files, 15 packages and 22 links**.
This covers the recorded executable, selected sources/metadata and bridge
inventory; the external runtime closure was not copied into the export.

A [temporary host adjustment](../../runs/agentops-admission-execution/v3/host-resource-adjustment/plan.json)
reduced the WSL memory cap from 4 GB to 2 GB during resource-constrained startup.
The [restoration receipt](../../runs/agentops-admission-execution/v3/host-resource-adjustment/restoration.json)
records restoration at **2026-10-28 21:46:23 UTC**. At the audit, the actual
`.wslconfig` matched the retained original bytes exactly and stayed unchanged
through the review. The adjustment is environmental context; its causal role
in the fixture readiness failure has not been established.

The [export/2 receipt](../../runs/agentops-admission-execution/v3/export/result.json)
contains **800 workspace files totaling 10,923,138 bytes**. Exporter v2 ran as
separate tooling and preserved its exact source in `exporter-source.py` outside
the workspace replica. The frozen application inputs were not changed to add
that exporter.

The audit verified all 702 staged-input hashes, exact export scope, exporter
source hash and all **803 export files** including the manifest, receipt and
exporter source. Before/after file inventories matched. Its status is
`verified_expected_partial`: copying and audit integrity passed while the live
attempt remained incomplete. No WSL launch, application launch, test rerun or
source/configuration change occurred during the audit.

## Remaining live evidence

The next investigation needs to locate the startup delay between asyncio entry
and service readiness. A qualifying fresh N11 control is still required before
an admitted B7 request can establish certificate-to-wire linkage, completion
and application effect. The earlier post-asyncio process-survival issue also
remains unresolved because this attempt never reached that boundary. Existing
attempts and acceptance rules remain preserved; this report adds no project
percentage, supervisor acceptance, time extension or scientific gate credit.
