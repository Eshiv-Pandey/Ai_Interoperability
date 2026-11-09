# AgentOps diagnostic v12: clean completion without reproducing the prior hang

28 October 2026. The prospectively frozen three-case diagnostic completed once.
**N11 and the explicitly header-configured B7 deployment passed the strict
case contract. B6 remains partial because no public confirmation binding was
obtained and no continuation was attempted.** All three shutdown diagnostic
captures are complete and record normal `asyncio.run` return.

The earlier v10 B7 process-survival problem did not reproduce in this allocation.
No cause or repair was established. V10 remains four strict native successes,
eleven complete recorded non-successes and three partial cases. Do not pool the
diagnostic controls into that matrix or replace its historical B7 observation.

## Allocation and verification

The [prospective protocol](source-evidence/agentops-bridge-diagnostic-v2/protocol.md)
and [seal](source-evidence/agentops-bridge-diagnostic-v2/manifest.json) fixed
N11, B6 and B7 in that order, with fresh state and the original public-binding
policy, profiles and limits. N11 was the mandatory positive control. Every
case had to provide complete diagnostics and clean process cleanup before a
later case could launch. All three executed; none was skipped or unexecuted.

The version-1 diagnostic preparation was sealed but never launched. Its
case-relative export reference bug was corrected prospectively, preserving
the old seal and all source bytes; see the
[supersession record](source-evidence/agentops-bridge-diagnostic-v2/supersession.json).
The corrected [software receipt](../../runs/agentops-native-eligibility/bridge-diagnostic-software-v2/result.json)
records **100 passing tests across seven stages on the retained Linux Python
3.13 runtime, with no skips**. The
[preflight](../../runs/agentops-native-eligibility/bridge-diagnostic-preparation-check-v2.json)
passed before launch. No packages were installed and no live model was called.

The [terminal group result](../../runs/agentops-native-eligibility/linux-bridge-diagnostic-v12/result.json)
records `matrix_attempts_recorded`, unchanged parent inputs, no export-reference
failures and identical before/after bridge-runtime checks (2,938 files,
15 packages and 22 links). The separately executed
[parent checker](../../runs/agentops-native-eligibility/bridge-diagnostic-parent-check-v12.json)
verified **2,617 exported files**, all planned-case accounting, task/effect
semantics, diagnostic observations and cleanup evidence. These files include
retained prior evidence, not 2,617 independent observations.

## Results kept separate by measurement

| Case | Public continuation / task / effect | Strict whole-case result | Shutdown diagnostic |
| --- | --- | --- | --- |
| N11: native matched polling/raw profile | Public structured confirmation; original task completed; exactly one expected attributed effect | Pass; complete evidence | Complete; normal asyncio return; clean exit |
| B6: passthrough public factory | Raw read did not yield a public confirmation binding; no continuation attempted; original task unfinished and domain unchanged | Unknown / partial | Complete; normal asyncio return; clean exit |
| B7: header-configured public factory | Public binding recovered; DataPart continued the original task; exactly one expected attributed effect | Pass; complete evidence | Complete; normal asyncio return; clean exit |

B7's fetch configuration explicitly adds `A2A-Version: 1.0` at the selected
local origin. This is a configured deployment observation, not a stock-raw
claim or a new admission method. All task/effect observations use the original
deterministic confirmation double and simulated SQLite service state.

Every service/client exit code was zero. No forced cleanup or cleanup error
was recorded. Terminal database snapshots followed observed empty service
process groups. B6's continuation gap remains in the semantic checker, so the
parent report correctly sets `all_evidence_complete` to false despite complete
shutdown diagnostics in every case. A clean shutdown is not task completion.

## What the diagnostic captured

Each lifecycle contains the ordered phases `asyncio_run_entered`,
`teardown_watchdog_armed` (five seconds), `coroutine_finished`, and
`asyncio_run_exited` with outcome `returned`. No diagnostic errors were recorded;
all three traceback files are empty. The watchdog was cancelled on asyncio
return. These are boundary observations, not process-latency measurements.

At the coroutine-finished snapshot, N11 and B7 contain only the current observer
wrapper task. B6 also contains four pending tasks: two telemetry wrappers, an
active-task producer and an active-task consumer. They did not prevent normal
return in this B6 run. The producer frame awaits a request-queue item; the
consumer awaits `EventConsumer.run()`. The wrapper frames do not identify their
inner coroutines. These are suspension locations, not complete await chains or
cancellation histories. At both captured thread boundaries each case lists
one enumerated Python thread, the main thread; this does not enumerate every
native/runtime thread.

Direct evidence:

- [N11 lifecycle](../../runs/agentops-native-eligibility/linux-bridge-diagnostic-v12/workspace/runs/agentops-http-control/bridge-diagnostic-v1-N11/service/shutdown-diagnostics/lifecycle.jsonl)
- [B6 lifecycle](../../runs/agentops-native-eligibility/linux-bridge-diagnostic-v12/workspace/runs/agentops-http-control/bridge-diagnostic-v1-B6/service/shutdown-diagnostics/lifecycle.jsonl)
- [B7 lifecycle](../../runs/agentops-native-eligibility/linux-bridge-diagnostic-v12/workspace/runs/agentops-http-control/bridge-diagnostic-v1-B7/service/shutdown-diagnostics/lifecycle.jsonl)
- [B6 captured producer/consumer source](../../runs/agentops-native-eligibility/linux-bridge-diagnostic-v12/workspace/runs/agentops-http-control/bridge-diagnostic-v1-B6/diagnostic-sources/source-0004.py), lines 518 and 585
- [B6 captured telemetry source](../../runs/agentops-native-eligibility/linux-bridge-diagnostic-v12/workspace/runs/agentops-http-control/bridge-diagnostic-v1-B6/diagnostic-sources/source-0005.py), line 242

The source collector retained 17 snapshots: five each for N11/B7 and seven for
B6. Their recorded bytes/hashes check, with no recorded-frame source-closure
gaps. They were copied **after capture**; this is not proof of pre-execution
loaded-module fidelity or coverage of unobserved tasks/frames.

## Interpretation and remaining work

The [original v10 B7 result](../../runs/agentops-native-eligibility/linux-bridge-v10/workspace/runs/agentops-http-control/bridge-v1-B7/result.json)
still records service exit `-15`, forced termination and a missing terminal
snapshot after the server routine had reported shutdown. V10 did not contain
these new lifecycle boundaries. Its failure therefore remains unlocalized:
the new observations cannot determine whether the earlier surviving process
was inside asyncio teardown or a later interpreter phase.

The diagnostic wrapper adds observation work and may change scheduling. Three
fresh controls are not a causal isolation experiment or a reliability estimate.
No timing, repeatability, root-cause or successful-repair claim follows from
this non-reproduction. Do not repeat this consumed allocation to obtain a more
favorable explanation. A further experiment would need a new substantive
question and prospective design.

For the supervisor, the new concrete result is one completely observed strict
positive on the configured bridge route under this diagnostic wrapper. It
improves the bounded evidence available for review. It does not establish
novelty, a qualified second domain, independent human validation or a completed
study. CP2 remains open and verified checkpoint credit remains **5%**.

To recheck the retained export without running the application, use a new
output path:

```text
python -B scripts/check_agentops_bridge_diagnostic_group_v2.py --output runs/agentops-native-eligibility/bridge-diagnostic-parent-check-v12-new.json
```

The default run is the retained v12 group. Preserve every check output; this
command requires the original workspace prerequisites and is not a complete
standalone runtime installation. Never rerun v8/v9/v10 or this v12 allocation.
