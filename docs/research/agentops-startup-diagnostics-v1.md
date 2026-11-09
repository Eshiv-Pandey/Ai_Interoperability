# Passive startup diagnostics for the next live allocation

The new [startup observer](../../scripts/agentops_startup_diagnostics_v1.py)
and [v4 service entrypoint](../../scripts/serve_agentops_bridge_diagnostic_v4.py)
cover the interval before service readiness. **Eleven focused inert tests
passed** against the finalized sources. No AgentOps application or WSL process
was launched by this validation, and no live failure cause has been established.

## Evidence for the coverage gap

The retained [v3 native attempt](pending-admission-live-results-v2.md) timed out
before fixture readiness and client launch. PID 785 recorded only
`interpreter_exit_observer_installed` with `watchdog_armed: false`, followed by
`asyncio_run_entered`. The interpreter-exit and asyncio-teardown stack files
are empty; `service-ready.json` and `service-result.json` are absent. The
[independent export review](../../runs/agentops-admission-execution/v3/independent-review/result.json)
retains this incomplete outcome and the skipped B7 case.

The preserved [asyncio observer](../../scripts/agentops_shutdown_diagnostics_v2.py)
arms its timer in the service coroutine's `finally`. The preserved
[v3 entrypoint](../../scripts/serve_agentops_bridge_diagnostic_v3.py) arms the
interpreter-exit observer only after `run_observed` returns or raises. Neither
timer covers a service that remains active before readiness. This explains the
diagnostic coverage gap; it does not explain the startup delay. The earlier
v2 post-asyncio process-survival issue is a separate, still unresolved boundary.

## New observation and ownership rules

V4 starts `StartupObserver` before service/application imports and retains the
existing asyncio and interpreter-exit observers. Its dedicated daemon calls
`faulthandler.dump_traceback` into a separate raw, non-inheritable descriptor
while readiness is absent. It never installs or cancels the global
`dump_traceback_later` timer used by the existing observers.

The default sampling interval is five seconds, controlled by
`--startup-stack-seconds`. The observer records
`startup-diagnostics/lifecycle.jsonl` and `startup-stacks.txt`. Lifecycle schema
`agentops-startup-event/1` binds event sequence, PID, monotonic and epoch clocks,
phase and diagnostic error types. Events distinguish arming, monitor start,
sample start/completion/failure, observed readiness and observer stopping.
Tracebacks contain Python stack locations rather than frame locals or task and
thread names.

Readiness stops the daemon. Coroutine exit also requests stopping before the
preserved asyncio-teardown observer begins; wrapper exit provides a final stop
request before interpreter-exit observation is armed. The stop wait is bounded
(one second by default). A delayed dump retains ownership of its descriptors
until the daemon finishes or the OS reclaims the process; a timed-out join does
not close a descriptor still in use. A thread-construction failure can close
directly because no start occurred. If `Thread.start()` raises after it may have
launched the daemon, construction requests stopping and retains daemon/OS
ownership instead of recycling those descriptors.

The observer changes no application request, cancellation, signal, service
deadline, cleanup acceptance or exit status. It adds a daemon, diagnostic I/O
and a bounded join, so it can affect scheduling and measured timings. The daemon
needs Python/GIL scheduling; delayed or absent samples do not prove that startup
was unstalled. A stack location identifies observed execution, not its cause.

## Verification and deployment boundary

The [fresh software receipt](../../runs/agentops-startup-software/windows-v1/result.json),
[pre-execution plan](../../runs/agentops-startup-software/windows-v1/plan.json)
and [raw unittest output](../../runs/agentops-startup-software/windows-v1/stderr.bin)
record **11 tests passing in 2.126 seconds**, with unchanged source/test bytes.
The suite checks readiness stop, a constructed pre-readiness stall, original
exception propagation, timer noninterference, non-inheritable descriptors,
allocation failures, delayed writers, thread construction failure and interrupted
start after a writer has begun. Its subprocesses contain inert test code or a
stubbed service; they are not real application trials. This finalized-source
receipt supersedes the earlier nine-test tool observation for this new helper.

Seven preserved observer, wrapper, coordinator, plan and interpreter-checker
scripts were byte-equal before/after validation and matched the retained v3
export. No previous wrapper, coordinator, checker or consumed allocation was
changed during startup-observer finalization.

A fresh deployment needs separately versioned plan, coordinator and checker
support. The existing
[interpreter-exit checker](../../scripts/check_agentops_interpreter_exit_v1.py)
correctly pins the v3 launch argv and must not silently accept or relabel v4.
The next application attempt must receive a new allocation, retain the same
readiness and acceptance rules, and qualify N11 before any admitted B7 request.
The new diagnostic helper itself does not authorize replacing a failed result,
relaxing acceptance, or claiming live admission success.
