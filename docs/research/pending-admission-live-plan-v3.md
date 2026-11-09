# Prospective admitted control with startup observation

29 October 2026. This version addresses the diagnostic coverage gap in the
retained [v3 allocation](pending-admission-live-results-v2.md), which reached
asyncio entry but not fixture readiness. It has not been staged or executed.
The root coordinator must choose an unused parent allocation and a fresh Linux
workspace before capturing this source. Existing attempts remain unchanged.

## Preserved acceptance rules

The original N11 native client, B7 admitted client, application source, fixture,
request contents, 100000-unit admission budget, 30-second admission timeout,
65-second fixture-readiness deadline and native-first gate remain unchanged.
Owned-child cleanup keeps its 20-second graceful exit wait followed by bounded
termination/kill waits and reaping before group inspection. Any forced stop,
cleanup error, incomplete required diagnostic, missing task/effect evidence or
failed native prerequisite prevents strict success. B7 runs only after a fresh
N11 result is recorded and all required checks establish strict success.

There are zero live model API calls. Diagnostic stack locations do not establish
a subsystem cause or repair. Neither a readiness marker nor an empty stack file
proves application completion, normal process exit or absence of a startup stall.
The independent effect, original-task, admitted-request, asyncio and process-exit
checks remain mandatory.

## New versioned components

| Component | Version and change |
| --- | --- |
| Service wrapper | `serve_agentops_bridge_diagnostic_v4.py` adds the reviewed passive startup observer before application imports and preserves the v2 asyncio/v3 interpreter-exit observers. |
| Startup checker | `check_agentops_startup_v1.py` binds v4 argv, PID, case window, sampling configuration, event order, sample headers and Python stack locations, matching readiness and monitor stop. Missing readiness can be valid partial evidence but is never complete startup observation. |
| Exit checker | `check_agentops_interpreter_exit_v2.py` retains all v1 exit/process requirements and explicitly accepts the v4 launch and its two diagnostic options. The preserved v1 checker still rejects v4. |
| Preparation | `agentops_admission_live_plan_v3.py` uses `agentops-admission-live-preparation/3`, pins wrapper v4, both 5-second diagnostic intervals and the unchanged 65-second deadline. |
| Coordinator | `agentops_admission_control_v3.py` records the new wrapper/observer/checker hashes in each case plan, saves `startup-check.json`, and adds valid, complete startup observation to all previous strict-success gates. |
| Stage/phase drivers | `stage_agentops_admission_v3.py` and `execute_agentops_admission_phase_v3.py` select the v3 preparation/control and new software suites. The phase driver is import-safe; after-inspection also fails if Python runtime equality is missing or false. |
| Chain driver | `run_agentops_admission_chain_v3.py` runs the captured preparation/preflight/launch/after sequence with explicit gates and a disjoint export destination. Its inert tests are included in the software phase. |
| Exporter | `export_agentops_admission_v3.py` accepts preparation/3 only, emits manifest/result schema /3, captures its own exact source, and preserves the same bounded input/group/N11/B7 trees, including every failure and startup diagnostic. |

The [startup observer specification and test receipt](agentops-startup-diagnostics-v1.md)
describe its daemon/GIL scheduling limit and descriptor ownership. It uses
`dump_traceback` into its own non-inheritable descriptor and does not replace or
cancel the global delayed-trace timer used by the preserved teardown observer.
The monitor normally stops at readiness; an early failure requests stopping at
the service-coroutine or wrapper boundary. A delayed monitor retains descriptor
ownership rather than recycling an FD that it may still write.

Startup checking is separate from exit checking. Valid startup evidence may
remain incomplete after a readiness timeout, interrupted capture or diagnostic
error. The exit checker can remain invalid/incomplete if no service result was
written. Both outcomes are retained, without manufacturing missing lifecycle
markers or weakening N11 qualification.

## Prospective execution and preservation

An unused Windows parent such as `runs/agentops-admission-execution/v4` is a
proposal, not an allocated run. Check its absence before selecting it. The
stager creates a fresh `/var/tmp/agentops-admission-live-v1-*` workspace; the
relative group and case names are retained under that new absolute root.
Do not reuse the consumed v2/v3 parents or their Linux workspaces.

Use the v3 stage, preparation, control and phase entrypoints together. All
scripts, relevant tests, package sources, reproduction fixtures, nine pinned
documents and the exact 421 original application files are captured before
software validation and preparation. No source may change after this capture.
The original editable runtime remains at its verified absolute path and is
inspected before and after; no runtime relocation is proposed.

Software validation includes the new startup observer/checker, versioned exit
checker, native gate/coordinator and exporter regressions, alongside the existing
admitted-client, adapter, refinement, owned-child, interpreter-observer and
scaling-generator suites. Windows symlink skips are not Linux passes. Native
software validation must execute the full selected suite under the captured
runtime before any application launch.

The [initial Windows pipeline receipt](../../runs/agentops-startup-pipeline-software/windows-v1/result.json)
records 65 tests run: 62 passed and three symlink checks skipped. After review
added the runtime-equality failure rule and the root chain, the
[final changed-source receipt](../../runs/agentops-startup-pipeline-software/windows-v2/result.json)
records 20 passing plan/phase/chain tests. It binds the unchanged startup/exit
checker and exporter sources to their earlier test receipt; these are scoped
receipts, not 85 different checks or a Linux validation result. Both retain raw
stdout/stderr. The [preserved-source record](../../runs/agentops-startup-pipeline-software/windows-v2/preserved-sources.json)
confirms the six older pipeline implementations stayed byte-identical.

Preflight must verify source/runtime identity and unused paths. The launch
then receives one attempt per N11/B7 case. After-inspection and export follow
the recorded outcome, including partial or failed attempts. The three exported
trees are the prepared group and its new N11/B7 case trees; external runtime
closures and unrelated historical allocations remain outside export scope.

This prospective plan adds no successful live candidate call, algorithm novelty,
qualified second domain, supervisor acceptance, 70% completion or extension.
The algorithm and implemented benchmark remain this week's supervisor
deliverables; paper writing remains deferred.
