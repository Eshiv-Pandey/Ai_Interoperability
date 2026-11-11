# Workflow V2 analyzer peer review V1

This additive constructed review imports no original application or SDK and makes no provider calls. It tests analyzer acceptance, not human gold, held-out qualification or actual Workflow execution. Temporary positive-fixture files are discarded; mutations replace analyzer readers in memory.

The positive two-case fixture returned zero questions. Each of the 14 independently mutated invalid captures also returned zero questions and `retained_development_workflow_consistent`.

## Reproducible source boundary

| Analyzer | SHA-256 |
| --- | --- |
| `analyze_agentops_workflow_reference_v1.py` | `7da513d2583bb2af4b5152a11b7c9c8592fbeac1737cd2539a1d54498797b490` |
| `analyze_agentops_workflow_reference_v2.py` | `9d81fe9bad9d544b55536d4f7c21f04c36edc09ccaf62c2cc0961724631fff20` |

Replay command (choose a fresh output path):

```powershell
python -B scripts/check_agentops_workflow_reference_v2_analyzer_peer_v1.py --output docs/research/agentops-workflow-reference-v2-analyzer-peer-review-v2.json --expect-rejected
```

## Observed acceptance gaps

| Mutation | Analyzer questions | Accepted invalid capture |
| --- | ---: | --- |
| All four stage entries precede all four stage exits | 0 | true |
| First callback invocation differs from stage/tool invocation | 0 | true |
| First stage entry invocation differs from all other observations | 0 | true |
| All raw events use a different invocation than callback/stage/tool rows | 0 | true |
| First raw function-response event is moved before its matching function-call event | 0 | true |
| Receipt retains denied socket.connect_ex backend operation | 0 | true |
| Receipt retains denied socket.getaddrinfo backend operation | 0 | true |
| Receipt retains denied socket.sendto backend operation | 0 | true |
| Receipt retains denied socket.sendmsg backend operation | 0 | true |
| Receipt has status failed, error_type ValueError and copied_data_unchanged_during_task false | 0 | true |
| First recorded governed-request model differs from preserved compiled model | 0 | true |
| Exported original model identifier contradicts preserved compiled model claim | 0 | true |
| First raw event retains an error_message without error_code | 0 | true |
| First raw event actions request a confirmed tool confirmation | 0 | true |

Fix implications: require completed interleaved stage lifecycles; bind callback, stage, tool and raw events to one actual invocation; verify raw function calls precede their unique matching responses; retain all denied backend operations as failures while keeping any reviewed bootstrap exception explicit; reject failed worker receipts, contradictory model preservation records, raw SDK error messages and requested tool confirmations.

The `requested_tool_confirmations` mutation uses the expected official EventActions field; pinned schema verification is separate from this analyzer-level proof. This file preserves the pre-fix analyzer result. Later correction verification must be additive.
