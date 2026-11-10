# Governed AgentOps pilot: observed tasks and failed test profiles

This addendum to [manuscript v6](working-draft-v6.md) reports subsequent run
[42859288563](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/42859288563)
at `014c9d902c35629f27e68290f59872560b67ea17`. It preserves the original App,
policy plugin, tools, PII handling, SDK task store and ADK sessions. The selected
model is replaced by a deterministic public-evidence recipe; ASGI and an
observational before-tool callback are declared interventions.

| Public development case | Actual SDK state | Model calls / tool calls / ADK events | Original checks | Strict profile |
| --- | --- | ---: | ---: | --- |
| d01 health and active incidents | completed | 2 / 1 / 4 | 35/36 | failed |
| d03 unconfirmed restart | input-required | 5 / 5 / 12 | 39/40 | failed |

D01 returns the original inventory-down and active INC-002 information. D03
awaits four original evidence reads, requests the original SDK restart
confirmation and pauses without an approved action or inventory/audit/note
effect. Raw SSE, task-get responses, durable task/session/event records and
closed database snapshots agree. These are observed application behaviors,
separate from acceptance of the complete test profile.

The strict aggregate remains **0/2**. Both runs fail `no_network_attempts`
because each records one denied `socket.bind`. The target and stack were not
captured, so its origin cannot be attributed. The failure is neither removed
nor relabelled as harmless loopback activity. Workflow success and
`pilot_captured` describe collection, not a passed task/gold qualification.

The [independent semantic read audit](../runs/ci-agentops-governed-app-pilot/hosted-42859288563-2/semantic-read-review-1.json)
checks all 99 retained files and 421 original source ZIP members, task/context
and session identity, original outcomes and unchanged business state. The
[results note](../docs/research/agentops-governed-app-pilot-results-v1.md)
retains the scope and first transfer timeout. This audit launches no additional
application, solver, model or private evaluator. Full bank gold, held-out
validity, native/provider behavior and admission integration remain unqualified.
