# V5 resource decision: staging withheld

29 October 2026. A Windows observation at 02:18:51 UTC reported 1,440,140 KiB
free physical memory and no running WSL distribution. That improvement over the
previous turn justified checking eligibility for one fresh native/admitted
attempt. It did not establish a repair or the cause of the earlier timeout.

Before measuring eligibility, the [prospective plan](../../runs/agentops-admission-execution/v5-invocation/plan.json)
reserved a new outer invocation and set two Windows `GlobalMemoryStatusEx`
samples ten seconds apart, each requiring at least 1 GiB available physical
memory and 2 GiB available commit. These are conservative stop rules selected
after independent AI review, not validated safe-memory thresholds or human
approval. The same checks were planned after preflight, together with Linux
`MemAvailable >= 1 GiB`, immediately before application launch.

The recorded pre-stage checks did not pass:

| UTC | Available physical bytes | Available commit bytes | Eligible |
| --- | ---: | ---: | --- |
| [02:22:14.699035](../../runs/agentops-admission-execution/v5-invocation/prestage-memory-1.json) | 589,029,376 | 1,941,536,768 | No |
| [02:22:24.709490](../../runs/agentops-admission-execution/v5-invocation/prestage-memory-2.json) | 305,655,808 | 1,745,747,968 | No |

These use the same API/counters as the earlier v4 invocation; the initial CIM
`FreeVirtualMemory` observation is not substituted for available commit. The
improved headroom was not sustained. The [decision](../../runs/agentops-admission-execution/v5-invocation/prestage-resource-decision.json)
and [terminal receipt](../../runs/agentops-admission-execution/v5-invocation/result.json)
therefore record **withheld before staging**: zero staging attempts, phase
invocations, WSL-runtime launches and application launches. Configuration and
all eleven reviewed pipeline sources remained unchanged. No unrelated editor,
application or service was stopped.

`v5-invocation` is consumed; do not reuse it. The proposed stage directory `v5`
was never created. Both `v6` and `v6-invocation` were absent at this update and
are only possible future allocations, requiring a fresh check before use.

The next live dependency is sustained external resource improvement. Do not
repeat staging or relax the rule to obtain a favorable observation. The existing
recorder automatically advances through the chain, so it cannot enforce the
new pre-launch checkpoint. A future attempt can use the unchanged stage and
individual software/prepare/preflight/launch/after phase drivers, recording the
resource decision before launch. The unchanged exporter accepts terminal
preparation evidence even when live execution is withheld; absent task/effect
records must remain absent.

The original 65-second readiness limit, native N11-before-admitted-B7 gate,
fixture, source/runtime checks, admission budget and task/effect/cleanup
requirements remain mandatory. This decision adds no live admission success,
method contribution, domain qualification or project-percentage credit. The
[completed local demonstration](shared-admission-command-v1.md) remains ready
for the supervisor review; paper work remains deferred.
