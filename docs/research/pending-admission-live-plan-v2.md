# Prospective admitted control with interpreter-exit observation

29 October 2026. This is a separate implementation revision and fresh allocation
following the retained [failed native prerequisite](pending-admission-live-results-v1.md).
It is not a retry or reclassification of that consumed case.

The same original fixture, N11 native client, B7 admitted client, request
contents, budgets, native-first gate, independent effect checks and 20-second
graceful service-exit deadline from [v1](pending-admission-live-plan-v1.md) apply.
Each case still receives fresh state. Zero live model API calls are permitted.
The original application, runtime and v1 helper sources are unchanged.

Two harness changes address concrete gaps observed in the failed attempt:

1. `agentops_owned_child_v1.py` uses the actual Popen child handle to wait for
   exit. After the graceful deadline it requests termination, waits at most two
   seconds, then requests kill and waits at most three seconds if necessary.
   It reaps that child **before** invoking the preserved remaining-group helper.
   An unconfirmed child exit withholds group inspection and terminal snapshot.
   Timeouts and signal requests remain explicit failures of clean acceptance.
   A successful reap cannot make a forced service stop pass.
2. `serve_agentops_bridge_diagnostic_v3.py` retains the unchanged service routine
   and v2 asyncio observations. It adds process-bound interpreter-exit markers
   and a separate watchdog that remains available after asyncio returns.
   It does not install an exit shortcut or a speculative SDK/resource fix.
   Tracebacks locate observed execution; they do not establish a causal repair.

Use `stage_agentops_admission_v2.py` to create a new Linux workspace, then
`agentops_admission_live_plan_v2.py` and `agentops_admission_control_v2.py` for
preparation, preflight and one launch. The preparation schema is
`agentops-admission-live-preparation/2`. Case-relative paths remain N11/B7 under
`runs/agentops-http-control/admission-live-v1-*`, but the enclosing workspace is
new and its exact absolute path is pinned. Existing case paths are refused.
The exporter can retain the same bounded relative trees without rewriting any
recorded paths.

All scripts, tests, package code, recipe fixtures, seven pinned documents and the
exact 421 original application files are captured before execution. Software
validation must include the new owned-child Linux tests, exit-observer and
independent exit-checker tests, coordinator regressions and existing admitted
client/adapter/controller checks. After-inspection and export retain every
failure, skip or partial. No source is edited after that allocation is frozen.

The new exit checker must bind the diagnostic PID/order, process argv,
`service_child_cleanup` receipt, return code, graceful timeout, signal requests,
group receipt and actual service flags. Strict success requires clean return
code zero, no forced stop or cleanup errors, coherent complete exit diagnostics,
and all previous independent protocol/task/effect checks. Only a freshly
qualified N11 allows B7 to run. A repeated exit stall is an informative failed
attempt, not grounds to waive the native gate.

Any success is one conditional local integration observation. The earlier
failure stays in the report; no reliability rate, repaired root cause,
algorithmic novelty, second-domain qualification or 70% completion follows.
The implemented benchmark and algorithm remain the supervisor deliverables;
paper work remains deferred.
