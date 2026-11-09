# Native A2A 1.0 port results v1

**24 October 2026.** The separately disclosed Carol port reproduces the three original application's tested continuation controls on native A2A 1.0. This is an authored adaptation with actual native wire evidence, not an unchanged external-application result, MCP-bridge execution, natural defect or novel method. The [prospective port specification](reference-port-native-probe-v1.md) and [change map](source-evidence/reference-continuation/port/change-map.json) were hashed and copied before execution.

The single [native run](../../runs/reference-port-native/carol-port-native-v1-2026-10-23T21-10-38-290Z-14572/report.json), SHA-256 `fbd4dbedf77c925894089fdc1279c74ba71028e1c53b66046e129ae406642574`, preserves all setup/control attempts and raw HTTP. It uses the actual pinned official SDK client/server over loopback; no model or bridge ran.

| Control | Observed native outcome |
| --- | --- |
| P1: original task/context plus own-task reference | The original task/context completes; answer and subsequent GetTask agree. |
| P2: same task/context with empty references | The original task remains input-required; answer and GetTask agree. |
| P3: original context only with empty references | A different task is created in that context. Both new and original tasks remain input-required, confirmed by separate gets. |

Each control had one initial request, one fixed `Well done!` answer and the necessary recorded task observations. There were **14 HTTP requests: one card discovery, six SendMessage calls and seven GetTask calls**, with **2,721 request-body bytes and 11,436 response-body bytes** and no failed request. These are entity-byte counts, excluding framing/implicit headers. Logging overhead is disclosed; no latency or efficiency comparison is made. P2/P3 are deliberately authored near-miss interventions.

The official protobuf serializer omits empty repeated fields: P2/P3 SDK inputs contain `referenceTaskIds=[]`, while their actual wire requests omit that field. P3's empty SDK `taskId` likewise disappears on the wire. Treat absent repeated references as the native default empty list, while keeping exact raw bytes and SDK representations separately. Native wire task states use `TASK_STATE_*` strings; SDK task objects use numeric enum values. Neither representation may be substituted without a declared conversion.

The port and driver were unchanged after execution. Server PID **18756** closed its specific listener through IPC, reported `server_listening=false` and exited normally with code 0 and no signal. Separate exact-PID checks found both server/capture processes absent. No broad process kill occurred.

The capture owner recorded [263 integrity checks](../../runs/reference-port-native/carol-port-native-v1-2026-10-23T21-10-38-290Z-14572/capture-integrity.json) against stored source/SDK copies, raw body encodings, correlation and cleanup. The parent independently reconstructed the controls from native raw bodies without importing the driver, SDK or application. Its [corrected check](../../runs/reference-port-native/parent-check-v1.1.json) passes **148 checks** for the declared profile, serial observations, body/hash/parsed agreement, RPC IDs, original association, task state, references, actual costs and pre-execution source snapshots.

The [initial parent check](../../runs/reference-port-native/parent-check-v1.json) rejected the record because the checker assumed the older capture's `observed` outcome label; the new record uses `recorded-with-prospective-checks-passed`. This was a parent-checker schema assumption, not an application failure. Both reports and exact driver copies are retained; raw captures were not changed. The corrected checker still determines the P1/P2/P3 facts from raw requests/replies rather than trusting that outcome label.

These parent checks concern this fixed captured fragment. They are not a complete mutation-tested A2A conformance checker, authentication/complete-logging proof, source-to-world theorem, prospective admission decision or independent human review. The earlier **146-test** clean archive replay covers the foundation and original A2A 0.3 checker; it must not be portrayed as new test coverage for this 1.0 checker or future bridge projection.

The [original 0.3 results](reference-continuation-results-v0.md) and this separate port agree on the tested source branch and association behavior. The port's SDK/event/card, language/RNG/formatting changes remain explicit; no arbitrary-input or byte-equivalence claim is made. A passing port is a version-matched **native** control, not a third converter or evidence that either MCP route loses this requirement.

The next required work is a frozen whole-interface bridge probe and independently checked **status/association** projection. Include AmirK-S ordinary send and exposed modern Tasks update, plus both mgcrea typed and permitted raw SendMessage/GetTask paths. mgcrea's documented raw alternative may restore references in one task action; every strong comparator must be allowed to choose it directly. Do not run the rejected 192-admission observation-efficiency pilot or claim superiority from an obvious raw action.

**CP2 remains open; overall progress remains 5%.** A substantive new C1 step, strong-comparator advantage, prospective profile/model validity and recorded human novelty/feasibility review are still required.
