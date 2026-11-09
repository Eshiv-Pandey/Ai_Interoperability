# AgentOps matched bridge-profile plan v1

Prepared 27 October 2026 from read-only source inspection. **No experiment in
this plan has been executed.** This is a bounded next-experiment design, not a
sealed launch manifest, whole-interface impossibility proof, second-domain
qualification or C1 result. Freeze exact inputs, budgets and checker expectations
before execution; retain contrary outcomes rather than revising expectations
after observing them.

The [native protocol control](source-evidence/agentops-protocol-control-v1/protocol.md)
now has [checked v9 results](agentops-native-protocol-results-v9.md). Its sync/default-blocking and streaming cases cannot
automatically stand in for a bridge's polling, background stream consumption or
elicitation behavior. Earlier [v8](agentops-native-http-results-v8.md) establishes
only its recorded no-header A2A 0.3 native profile.

## Source findings and exact locations

The following prefixes identify exact local paths:

- **A** = [external/a2a-to-mcp](../../external/a2a-to-mcp), HEAD
  `58eff9da469bccdc432bf164662727947de646b4`.
- **M** = [external/mcp-a2a](../../external/mcp-a2a), HEAD
  `c4d9d3c57c1746abbf9f6aadd3a9912d464eb1f5`.
- **P** = `runs/agentops-native-eligibility/linux-socket-resume-v8/workspace/external/runtime-agentops-linux-v7/venv/lib/python3.13/site-packages/`.

Both Git HEADs were read and both `git status --short` outputs were empty during
this inspection. This verifies tracked checkout state, not every installed or
built runtime byte. The [source lock](../../external/source-lock.json) identifies
the bridges' separate mapping implementations and shared JS SDK family. Seal
the actual builds/dependencies used by the experiment separately.

| Finding | Exact source location and limit |
| --- | --- |
| AmirK-S discovery sends `A2A-Version: 1.0` and `Accept: application/json`. | A `src/agent-card.ts:160-165`; its resolved interface is selected at lines 148-156. Capture the real request and returned card. |
| mgcrea discovery also sends the version header through its installed SDK resolver. | M `src/client/peer.ts:70-98,103-109`; M `node_modules/@a2a-js/sdk/dist/client/index.js:5311-5320` explicitly adds `A2A-Version`. A no-header card from v8 is not a substitute. |
| AgentOps card response can contain modern and compatibility fields together. | P `a2a/server/routes/agent_card_routes.py:43-48` does not inspect the request header; P `a2a/server/request_handlers/response_helpers.py:87-113` merges protobuf JSON with compatibility fields. A top-level `protocolVersion: "0.3"` alone does not determine handler eligibility. |
| mgcrea's normal client prefers the modern interface when present, and supplies its version header. | M SDK `dist/client/index.js:6515-6536` selects interfaces; lines 5831-5839 prefer `1.0` within a binding; lines 5657-5660 add the negotiated version. Preserve the actual discovered interface list and selected URL. |
| AmirK-S ordinary send is text-only and uses SDK default blocking behavior. | A `src/tools.ts:184-201,275-306`; `src/a2a-client.ts:68-74,90-105,207-225`. It constructs one text part with no part metadata or reference IDs. JSON-looking text remains a text part at this boundary. |
| AmirK-S MRTR and Tasks use that same text builder. | A `src/mrtr.ts:155-183`; `src/tasks/handlers.ts:126-135,287-307`. Tasks chooses streaming when advertised; otherwise it sets `returnImmediately: true`. MRTR passes an elicited string into ordinary send. |
| The generic content-to-part helper is not an exposed structured send path in these handlers. | A `src/parts.ts:93-107` can rebuild a data part from tagged content. Searching `contentToPart` across A `src/` returned only its definition. The exposed tool, MRTR and Tasks handlers above accept text instead. This source fact does not establish all conceivable embedding behavior. |
| mgcrea typed sends poll and carry text parts. | M `src/client/peer.ts:89-96,166-191` sets `polling: true`, accepted output modes `text/plain` and `application/json`, and `parts: [textPart(text)]`. SDK `dist/client/index.js:5447,5623-5638` derives send configuration. M `src/tools/writes.ts:32-71` exposes URL/text/task/context; it does not expose the library method's optional message metadata. |
| Message metadata is not part metadata or HTTP headers. | M `src/client/peer.ts:168-191` puts library metadata on the Message. P `google/adk/a2a/converters/request_converter.py:101-120` handles request metadata separately and converts each actual part. No inference that a `metadata.headers` object changes transport headers is justified. |
| mgcrea raw requests accept structured params but omit the version header in the default path. | M `src/tools/request.ts:11-24,54-77` permits nine named RPCs when writes are enabled, including `SendMessage`, but not `SendStreamingMessage` or legacy `message/send`. M `src/client/peer.ts:261-278` picks a JSONRPC URL from the card and passes only content-type. M `src/client/fetch.ts:40-54` adds bearer authorization and User-Agent, not a version header. |
| A source-unchanged library deployment has a custom-fetch alternative. | M `src/client/peer.ts:32,70-78` and `src/server.ts:58-66` accept and forward `opts.fetch`. It reaches both raw requests and SDK traffic. A wrapper supplying `A2A-Version: 1.0` is an explicit deployment intervention, not stock CLI behavior, but cannot be excluded from a claim covering the entire library interface. |
| AgentOps distinguishes text from a typed confirmation. | P `google/adk/a2a/converters/part_converter.py:129-140` turns a text part into GenAI text. Lines 172-203 create a FunctionResponse only for a data part with the ADK function-response tag. The text branch does not parse JSON into a FunctionResponse. |
| Local mirror completion is not origin completion. | M `src/tools/writes.ts:137-165` makes `a2a_respond_to_task` update the local store and explicitly labels outbound updates as mirror annotations. M `src/tools/tasks.ts:74-81` performs an origin read only with `refresh: true`; lines 147-157 show wait watching local changes. |

P's retained snapshot did not contain `a2a/server/routes/common.py`,
`jsonrpc_routes.py`, `a2a/utils/version_validator.py` or the request-handler
interface module. Those failed path reads are an inspection limitation, not
evidence of absent installed handlers. P `jsonrpc_dispatcher.py:272-303`
shows legacy-method dispatch before canonical parsing, and its canonical
handlers are decorated at lines 345 and 496. Use the new complete runtime-source
inspection and actual native records to settle default-header dispatch.

## Proposed bounded arms

Freeze the start text as `Restart inventory.`. Obtain the original task/context
and `adk_request_confirmation` call ID from caller-visible output; do not supply
IDs from private snapshots. Freeze one canonical confirmation object with
`confirmed: true` and the native control's rationale. For text arms, send its
exact JSON serialization as text; do not silently transform that text into a
data part. Retain a literal acceptance response in each elicitation envelope.

Each row uses fresh application state, model-double instance and bridge
state/cache. This avoids a preceding failed text turn changing the next arm's
history. One row is one bounded attempted episode, not a population sample.

| Arm | Fixed route and continuation | Matched control needed |
| --- | --- | --- |
| B1: AmirK-S ordinary tool | Default `a2a_send_message`, then same task handle with confirmation JSON as text; explicit final origin read. No Tasks or elicitation negotiation. | Native SDK send with the same default configuration and text payload; separate typed DataPart positive. |
| B2: AmirK-S Tasks | Negotiate the actual Tasks profile, start through the tool, collect public input request, then submit the frozen string through the published Tasks response mechanism. Capture background stream to completion/closure and final origin state. | Native streaming configuration when the original card advertises streaming, plus the matched text continuation. Do not disable streaming to select the easier path. |
| B3: AmirK-S MRTR | Negotiate elicitation without Tasks; retain verified request state and replay the original call with the accepted answer in the public input-response slot. | Ordinary native send control matching B1; distinguish the MRTR envelope/continuation mechanism from direct tool arguments. |
| B4: mgcrea typed | Stock configured CLI, writes enabled. Start, poll with refresh until the bounded pending condition, send confirmation JSON as text with both task/context, then refresh origin again. | Native `SendMessage` with polling/`returnImmediately: true`, identical accepted output modes and bounded origin polling; both text and typed DataPart controls. Default-blocking v9 alone is insufficient. |
| B5: mgcrea stock raw | Fresh stock CLI episode; use typed start/poll to obtain the original pending task, then `a2a_request` / `SendMessage` with canonical DataPart params. Capture the raw result and use typed refresh for final origin truth, even if a raw `GetTask` also fails. | Canonical raw request with omitted header, paired with a separate same-profile header-present positive. A startup failure in a raw-only episode would not test continuation. |
| B6: mgcrea library/raw baseline | Same source and tool calls as B5, embedded through the public server factory with a fetch that forwards arguments unchanged. | Controls embedding and instrumentation differences before attributing a result to B7's header. |
| B7: mgcrea library/raw header intervention | Same embedding as B6; the sole request mutation adds `A2A-Version: 1.0` for the frozen local A2A origin. Keep canonical params, discovery and all other behavior unchanged. | Compare with B6 and native DataPart positive. Report as an explicit deployment intervention, never as unmodified default behavior or a novel admission algorithm. |

This is the minimum proposed matrix for the exposed paths identified above;
the exact polling schedule, input-response schemas, byte/time limits and
supervisor cleanup must be implemented and sealed before launching. Reuse v9
as evidence only for profiles it actually exercises. Where a control changes
downstream state or model history, run a fresh isolated control rather than
replaying an old suffix. Do not execute a second effect-producing confirmation
after an unexpected effect; retain that result and stop the episode.

## Success and evidence requirements

Strict success is the conjunction of original task/context completion, the
expected inventory state change, exactly one fully attributed audit row,
confirmation before the effect, and no unrelated domain change or forbidden
action. Compare database snapshots before/after every boundary. Report task
state, prose, data representation, RPC result and effect state separately.

This matters because the original
`external/agentops-c806b7f1/agents/python/tests/test_server.py:57-94`
model double requests the action on its first call, then merely checks that some
`restart_service` FunctionResponse exists in its input history before emitting
success prose. It is not an independent effect grader. A text arm might reach
terminal state or positive prose without the intended state transition; record
the actual result, not an assumed failure or success. The fixture remains the
disclosed local confirmation agent, not the full conversational application or
real infrastructure execution.

Capture exact discovery/MCP/A2A requests and responses, stream framing and
closure, public handle provenance, actual polling/configuration, snapshots,
model-double calls, source/build/dependency hashes, subprocess receipts and
clean exit. Preserve all attempts and failed setup/checker outcomes in new
paths. Check runtime/gold separation and reject mutations of task/context,
confirmation ID, attribution, effect timing, extra writes and incomplete wire
capture. No terminal-state-only grader is sufficient.

## Permitted alternatives still requiring closure

The bounded arms do not prove failure for every public input or deployment.
Before any broader statement, retain an explicit coverage ledger for:

1. All tool registrations and all raw-method choices under the actual write
   gate, not just the send names; cancellation/refusal remains distinct from
   original-task completion.
2. Tasks, MRTR/form responses, literal tool continuations, legal arbitrary text,
   tagged content helpers versus reachable tool inputs, metadata placement,
   and parser/serialization behavior. One failed JSON string does not quantify
   over all legal strings.
3. Dynamic discovery and peer URLs. M `src/tools/util.ts:55-61` validates a URL,
   not membership in configured peers; A `src/server.ts:47-60` configures card
   URLs. Raw destination selection comes from the discovered card. Freeze the
   allowed original origin and disclose any relay, alternate card or endpoint
   deployment intervention; do not silently exclude an authorized alternative.
4. Default CLI configuration versus public library options, including custom
   fetch. The ordinary CLI config fields in M `src/config.ts:209-221` expose no
   generic outgoing-header field. A header-injecting library wrapper is still
   a relevant separately labelled permitted deployment.
5. Origin reads versus mirrors, local response tools, waiting, daemon/inbound
   paths and whether a claimed route actually reaches this original task.
   A different peer completing a different task is not this task's completion.
6. Push-notification/callback alternatives and actual advertised support. M
   `src/tools/writes.ts:198-243` configures callbacks; a callback notification
   is not itself an application approval. Verify any additional delivery
   behavior before excluding or crediting it.
7. SDK version negotiation, card normalization, binding choice, caller
   identity, session association and required DataPart conventions. P
   `google/adk/a2a/converters/request_converter.py:67-77,113-120` derives user
   and session from request context; synthetic identity is not human auth.
8. Schedule, expiry, retained-handle lifetime, concurrency, refresh and retry
   policy. Freeze bounded choices, record unknown beyond them, and count retries
   rather than treating them as invisible transport details.
9. Independent task/source validity and a fair same-evidence/actions comparator.
   A default-header repair or direct structured send is an existing recovery
   mechanism; neither alone supplies the missing C1 technical distinction.

This plan adds no checkpoint credit and makes no full-interface non-completion
claim. The next launch decision requires concrete sealed controls and checkers,
not this source inventory alone.
