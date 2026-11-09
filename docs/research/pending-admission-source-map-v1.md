# Pending-state admission: configured AgentOps B7 source map v1

29 October 2026. This map covers one continuation of an **already observed,
input-required AgentOps task** through the configured mgcrea raw tool. It is
an AI source/output review, not human review, a complete source compiler, a
novelty finding or a new application experiment. Historical v12 observations
are never current authorization to send another request.

The companion [source manifest](pending-admission-source-map-v1.json) fixes
the inspected bytes, source correspondences and public observation references.
Existing v8/v9/v10/v12 records were read only. No application was imported or
launched. The implemented recipe solver still reasons under a supplied model;
this document identifies which parts of a pending-state model can be tied to
source and which assumptions remain outside that solver.

## Narrow starting state and public evidence

Use the selected deployment's current public tool list and pending task reply.
Retain their exact received bytes and paths before constructing a profile.
For retrospective v12 B7, the retained MCP journal contains:

| Event | Public observation | Profile use |
| --- | --- | --- |
| 17 | `tools/list` advertises `a2a_request` and permits `SendMessage` | Check the chosen operation is available in this deployment |
| 29 | Typed send returns the original task ID and context ID | Bind original task/context; never infer them from names |
| 49 | Raw `GetTask` returns the same task/context, `TASK_STATE_INPUT_REQUIRED` and one `adk_request_confirmation` call | Bind the pending confirmation and its original action/target |
| 54 | The historical caller sends one raw `SendMessage` continuation | Retrospective request-shape correspondence only; never an input to a prospective decision |

The source container is
`runs/agentops-native-eligibility/linux-bridge-diagnostic-v12/workspace/runs/agentops-http-control/bridge-diagnostic-v1-B7/client/mcp.jsonl`.
Resolve fields from received `mcp-message` entities after checking raw bytes,
length and SHA-256. `scripts/check_agentops_bridge_v1.py:507` implements the
existing public-source resolver; `scripts/agentops_bridge_client_v1.mjs:80`
checks raw task/context association and extracts confirmation candidates.

Event 49's decoded `result.status.message.parts[0].data` includes all of:

```json
{
  "id": "adk-3d91dfd7-2049-4510-8b8c-a17e7c2b6d20",
  "name": "adk_request_confirmation",
  "args": {
    "originalFunctionCall": {
      "id": "restart-inventory-call",
      "name": "restart_service",
      "args": {"name": "inventory"}
    },
    "toolConfirmation": {
      "hint": "Please approve or reject the tool call restart_service() by responding with a FunctionResponse with an expected ToolConfirmation payload.",
      "confirmed": false
    }
  }
}
```

Those values are historical examples. A new controller must bind its current
task ID, context ID, confirmation call ID/name, original function-call ID/name
and target from the current public reply. The current old caller extracts only
confirmation ID/name; the new adapter should also retain the public original
action and arguments when matching a target-specific contract. Do not read
server-only session or SQLite state to fill missing public values.

## Public tool and emitted request

`external/mcp-a2a/src/tools/request.ts:35` registers `a2a_request`. The tool
schema accepts `url` as a URI string, `method` from a fixed enumeration and
`params` as an arbitrary string-keyed JSON object (default `{}`). `url` and
`method` are required. `SendMessage` is in the enumeration only when writes
are enabled. The schema does not validate the ADK confirmation semantics inside
`params`; a schema-valid call can fail later.

For this selected pending state, the narrow public recipe is:

```json
{
  "name": "a2a_request",
  "arguments": {
    "url": "<selected public peer base URL>",
    "method": "SendMessage",
    "params": {
      "message": {
        "messageId": "<caller message ID>",
        "role": "ROLE_USER",
        "taskId": "<observed original task ID>",
        "contextId": "<observed original context ID>",
        "parts": [{
          "data": {
            "id": "<observed confirmation call ID>",
            "name": "adk_request_confirmation",
            "response": {
              "confirmed": true,
              "payload": {"rationale": "<caller-supplied bounded rationale>"}
            }
          },
          "metadata": {"adk_type": "function_response"}
        }]
      }
    }
  }
}
```

This is the `params` of an MCP `tools/call`. The old caller constructs it at
`scripts/agentops_bridge_client_v1.mjs:240`; its confirmation payload helper is
at line 109. Approval and rationale are caller inputs in the local controlled
fixture. `confirmed: true` does not authenticate human approval.

The inner HTTP request is a different layer:

- `external/mcp-a2a/src/client/peer.ts:261` selects the **first advertised
  JSONRPC interface** from the peer card and sends HTTP POST there. It serializes
  `{jsonrpc: "2.0", id: randomId("rpc"), method, params}`. The caller does not
  choose the bridge-generated RPC ID or directly supply the HTTP endpoint.
- That function supplies `content-type: application/json`.
  `src/client/fetch.ts:38` preserves those headers, adds optional bearer/user
  agent and applies the configured retry policy. It does not add the A2A
  version header. B7's retained configuration sets retries to zero.
- `scripts/agentops_mgcrea_embed_v1.mjs:6` inserts `A2A-Version: 1.0` only when
  the selected request URL's origin equals the explicitly configured origin.
  Matching the tool's base URL alone is insufficient if the advertised JSONRPC
  interface points at a different origin. The adapter must check the selected
  interface and deployment configuration together.
- In the retained A2A 1.1.5 sources, `jsonrpc_dispatcher.py:496` applies the
  1.0 version validator to non-streaming requests. `version_validator.py:70`
  interprets a missing/empty version as 0.3 and compares major/minor versions.
  A whole-interface negative does not follow: older method names and other
  public routes are outside this one-recipe scope.

The recipe should describe the public MCP arguments. Do not pretend that an
emitted `headers` object is an accepted argument to `a2a_request`. Header and
endpoint behavior belong in a separately checked deployment/serializer contract.
The generated RPC ID can be abstracted only with a stated transport assumption;
it must not be assigned an arbitrary supposedly observed value.

## Source-supported predicates and their limits

The Linux paths below are relative to the exported
`external/runtime-agentops-linux-v7/venv/lib/python3.13/site-packages` tree inside
v12's workspace. The manifest records complete paths and hashes.

| Predicate or transition | Exact source support | What remains outside the public observation |
| --- | --- | --- |
| Raw `SendMessage` is offered | mgcrea `src/tools/request.ts:35-81`, current public tool list | Tool list and configured deployment must still be current |
| The selected origin receives the 1.0 header | `agentops_mgcrea_embed_v1.mjs:6-16`; mgcrea `src/client/peer.ts:261-279` | Selected card/interface, configuration and loaded code must match the mapped deployment |
| A pending task needs an actual function-response DataPart | ADK `a2a/converters/long_running_functions.py:159-204`; maintained executor `a2a_agent_executor_impl.py:125-135` | This check only recognizes shape/metadata; it does not validate the confirmation target |
| Text containing JSON is still text | ADK `a2a/converters/part_converter.py:131-140`; function-response conversion at `197-203` | Other unmodeled public transformations could exist; no whole-interface text impossibility claim |
| The response names an outstanding confirmation | ADK `flows/llm_flows/tools/_confirmation.py:276-295` parses the last user event's named response and ID | Whether that ID is outstanding in the current server branch is internal state |
| Confirmation targets the original action and arguments | `_confirmation.py:126-218` matches confirmation ID, original call ID/name/args, agent ownership and registered tool; checks confirmation requirement | Public `originalFunctionCall` is evidence to retain, not an independent proof of the server's entire session history |
| Already processed confirmation is dropped within the described processing flow | `_confirmation.py:300-325` filters original call IDs already responded to since the latest user event | This is not a general at-most-once guarantee across arbitrary new user requests or invocation IDs |
| Unconfirmed guarded tool does not execute its function | `tools/function_tool.py:391-419` requests confirmation when missing and refuses when false | Other callbacks/policy may also block execution |
| A confirmed inventory restart still has application guards | AgentOps `actions.py:108-148`: writes enabled, valid existing service, confirmation, nonempty identity/session/invocation, bounded rationale; validation at `48-95` | These runtime facts cannot all be proved from an MCP confirmation string |
| Successful mutation and audit are transactional | AgentOps `data.py:620-662`: `BEGIN IMMEDIATE`, idempotency lookup, service update, audit append, commit | No DB/runtime failure, no competing state change, correct invocation key, and successful commit remain runtime obligations |
| The same `(invocation_id, action, target)` reuses its prior audit row | AgentOps `data.py:632-640` | A later A2A request may have a different invocation ID; do not infer cross-request idempotency |
| Synthetic A2A attribution is distinct from authenticated identity | ADK `a2a/converters/request_converter.py:67-77,113-120`; AgentOps `server.py:330-339` can override with a verified subject | The local fixture has synthetic attribution; no authenticated-human claim |

AgentOps permits a nonblank rationale of at most 500 characters after trimming,
and checks its length again after redaction (`actions.py:78-87`, `models.py:13`).
The recipe language has equality/presence guards, not these string operations.
The current adapter checks the known necessary predicate
`0 < len(rationale.strip()) <= 500` at `pending_admission.py:186`. Successful
server redaction and its output length remain explicit runtime assumptions;
this source review does not import the application redactor.

## Working-state correction

**A blanket SDK refusal of a second request while working is not established by
the inspected deployed sources.** The runtime imports `DefaultRequestHandler`
as an alias of `DefaultRequestHandlerV2` (`request_handlers/__init__.py:46`).
V2 enqueues a request through `ActiveTask.subscribe` / `enqueue_request`
(`default_request_handler_v2.py:276-287`, `active_task.py:422-428,641`).
The active task producer refreshes current task state and processes queued
requests under a request lock (`active_task.py:513-542`). Terminal tasks are
rejected at startup (`active_task.py:469-474`). The maintained ADK executor
publishes working before processing (`a2a_agent_executor_impl.py:137-148`).

For the new adapter, **send only on an observed input-required state, send at
most one continuation, and poll while working** is an explicit controller
policy. It is a reasonable narrow scope for the demo, not a discovered SDK
impossibility theorem. A changed or working observation should stop dispatch
and require re-evaluation; under an open action space it means unknown for
completion, not an unsupported certificate. The existing authored
`10-working-state-blocks-second-answer.json` must retain its development label.

## Honest pending-state contract

A narrow adapter can establish that its witness uses an available public tool,
the mapped request representation, current correlated public bindings, a
target-matching confirmation, and the explicitly selected deployment. It can
then conditionally reason about bounded completion under stated server-history,
policy, identity, effect and environment assumptions. It must keep those
assumptions inspectable alongside the profile and certificate.

Do not set `done=true`, `safe=true` or complete route coverage solely because
the request can be serialized or because the old B7 trial succeeded. If the
required effect/safety relation has not been supplied and justified, preserve
unknown. The implemented solver's positive result is conditional on its model;
it is never an observation that a new task actually completed.

The first source-adapted profile should therefore:

1. Start at a received pending snapshot, without inventing response-derived
   IDs or future binding updates.
2. Bind task/context/confirmation/original-action/target as one correlated
   frame, and bind the contract and selected deployment to its digest.
3. Use the actual public request recipe above. Record header/interface
   obligations as checked deployment facts, separate from MCP arguments.
4. Declare coverage incomplete for the entire bridge. Negative conclusions
   may concern only a genuinely closed, explicitly enumerated recipe policy.
5. Keep runtime effect and source-fidelity assumptions explicit; inspect actual
   task/effect observations after any separately planned new execution.

No retained past task should be continued again. Candidate-driven live
execution, a full source-to-model argument and domain qualification remain
separate acceptance work.

## Current adapter and next live allocation

`src/interoperability/pending_admission.py` now builds a one-edge projection
under the explicitly named `agentops-inventory-confirmation-fixture/1`
contract. Its completion/effect state and initial safety value are **conditional
model assumptions**. The public observations do not by themselves establish
hidden history, current domain state, the write kill-switch, attributable
runtime identity, invocation identity, rationale acceptance or successful
database commit. These must remain visible in receipts and supervisor claims.
The fifteen-second local revalidation policy is not a service-issued lease or
an atomic lock against concurrent changes.

The [retrospective development receipt](../../runs/pending-admission-development/v1/result.json)
records a supported result with a checked certificate and exact request
equality to retained dispatch event 54. It explicitly records zero application
requests and `live_admission_verified: false`. This establishes historical
public-input/request correspondence, not a fresh completion observation.

The next live integration can use the new
`scripts/agentops_admission_client_v1.mjs`, whose
`agentops-admitted-client-config/1` adds explicit admission Python executable,
deployment, work budget and timeout. Its controller wraps the existing
import-safe episode through `runAdmittedEpisode`.

Create a **new coordinator and case allocation** using the lifecycle structure
of `scripts/agentops_bridge_diagnostic_control_v2.py:124`, with its own case
prefix, plan, source list and preparation seal. The concrete substitution is
the client-selection site around line 182: launch the new admitted client
instead of the historical public client. Preserve the existing service,
public-capture, evaluator-only observation, SQLite boundary and owned-process
checks. Importing shared helper functions does not authorize invoking the old
coordinator's consumed `run` path.

The old `check_agentops_bridge_v1.check_client` accepts only its historical
config/event schemas. Add an admitted-client checker that binds received raw
bytes to the snapshot, certificate, public rechecks and actual sent witness
before combining that report with the existing effect/process checks. A
successful old checker or a controller-only test cannot stand in for this
new end-to-end check. No new application allocation was launched for this map.
