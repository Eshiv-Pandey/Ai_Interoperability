# Fresh admission integration attempt: 29 October 2026

The fresh native control completed its original task and the last live database
observation showed the expected single inventory restart/audit effect. **It did
not pass the full acceptance check:** the service process survived after
`asyncio.run` returned and required SIGTERM. The admitted B7 case was therefore
**skipped**, as required by the prospective plan. There are **zero fresh
candidate application runs** and no newly verified live admission result.

The implemented algorithm and comparison benchmark remain available for the
31 October supervisor meeting. The separate
[supervisor rehearsal](../../runs/admission-demo/supervisor-1/result.json)
passed all ten commands, including the eleven-case benchmark and captured-code
replay. No paper draft is required this week.

## Fresh allocation and software results

The first staging attempt omitted the authored recipe fixtures. The checker,
coordinator, exporter and adapter suites passed; the solver suite had one
missing-file error. No application launched in that allocation. Its
[failed validation receipt](../../runs/agentops-admission-execution/v1/failed-stage-evidence/phase-software/result.json)
is preserved. The staging list and prepared inventory were corrected to include
the tests and fixtures, and a new workspace was allocated.

The corrected [v2 stage](../../runs/agentops-admission-execution/v2/result.json)
contains 687 pinned inputs, including the exact 421 original application files.
The bridge runtime verified 2,938 files and 22 links. Existing Python and bridge
runtime locations were reused explicitly; the staged application source was
confirmed at readiness. No old v8/v9/v10/v12 allocation was rerun.

The [focused runtime validation](../../runs/agentops-admission-execution/v2/export/workspace/runs/agentops-admission-live-v1/phase-software/result.json)
passed all five Python suites and the Node suite:

| Suite | Passed |
| --- | ---: |
| Independent admitted-client checker | 17 |
| Live plan/coordinator | 8 |
| Evidence exporter | 15 |
| Public pending-state adapter | 25 |
| Recipe-refinement solver/checker | 32 |
| Node controller/client | 26 |

This is **97 Python tests plus 26 Node tests**. These suites overlap earlier
software receipts; their totals must not be added to the earlier 69 or 83 as if
they were disjoint tests. All captured staged inputs remained unchanged.

## Executed outcome

The [group result](../../runs/agentops-admission-execution/v2/export/workspace/runs/agentops-admission-live-v1/attempt/result.json)
records `attempts_recorded`, not `strict_success`.

| Case | What actually happened | Acceptance |
| --- | --- | --- |
| New native N11 | Caller exited 0; original task completed; last live database showed one expected effect and inventory operational | Failed/incomplete: forced service stop, cleanup error and missing terminal snapshot |
| Admitted B7 | Withheld because the new native prerequisite failed | Skipped; no candidate request or application effect claimed |

The [native case check](../../runs/agentops-admission-execution/v2/export/workspace/runs/agentops-http-control/admission-live-v1-N11/case-check.json)
is structurally valid but incomplete. The separate
[shutdown check](../../runs/agentops-admission-execution/v2/export/workspace/runs/agentops-http-control/admission-live-v1-N11/diagnostic-check.json)
is valid and complete, with classification `post_asyncio_process_survival`.
The service coroutine and `asyncio.run` returned. Nearly twenty seconds later,
the same process identity was still present with its original command line;
the coordinator sent SIGTERM and recorded return code -15.

A subsequent cleanup observation saw that known process as a zombie with an
empty command line. The preserved cleanup helper treated it as an unknown
command, recorded an error and did not establish an empty group. That explains
the missing terminal database snapshot; it does **not** explain the preceding
process survival or turn this attempt into a success. The existing watchdog
stopped when `asyncio.run` returned, so it captured no interpreter-exit stack.
No specific SDK, provider, telemetry or resource-close cause is established.

## Retained evidence and next work

The [after-inspection](../../runs/agentops-admission-execution/v2/export/workspace/runs/agentops-admission-live-v1/phase-after/result.json)
matches the Python before-inspection exactly. The prepared application/code
inputs and bridge inventory also remained unchanged. The
[export receipt](../../runs/agentops-admission-execution/v2/export/result.json)
preserves the failed native case, explicit B7 skip, validation logs and captured
source. Export success is a copying/integrity outcome and does
not imply application success.

The [independent exported-evidence audit](../../runs/agentops-admission-execution/v2/independent-review/result.json)
verified all 812 workspace files and 687 staged inputs, reproduced the native
case/service/diagnostic checks from the captured code, confirmed B7's absence,
and reconciled the 97 Python plus 26 Node test logs. It found zero discrepancies
and no changes to the 814 export files including manifest and receipt. Its
status is `verified_expected_partial`, not successful live admission. It checked
the retained runtime-inspection evidence without rerunning that runtime.

For the supervisor meeting, run the
[implemented algorithm and benchmark walkthrough](implementation-demo-v1.md)
and disclose this remaining live-integration issue. The controller's public
snapshot, certificate and exact-request behavior also have the separate
[software and historical-request checks](pending-admission-results-v1.md).

The next live investigation needs separate interpreter-exit diagnostics and
correct handling of a receipt-owned exited child. Any new application attempt
requires a new allocation; this attempt and its acceptance rules remain intact.
Scientific novelty/advantage, qualified second-domain evaluation, independent
inputs and supervisor acceptance remain open. Neither these software results
nor a passing rehearsal establishes 70% project completion or a time extension.
