# AP2 route eligibility and prospective public recovery

Status: source-bound preparation with passing retained-public-Task and constructed
caller controls, 2026-11-11. The caller is prepared for the parent's separately
bounded live screen. No observed native/provider result or frozen V13/V14 edit
accompanies this document.

## All 39 V13 bridge initiation errors

The retained source is
`runs/ap2-native-bridge-development/v13/retained-42918421487-4/extracted/matrix/cells/*/bridge/result.json`.
Each route has 13 legal initiation replies with `isError: true`:

| Route | Observed first error | Source-bound disposition |
| --- | --- | --- |
| `amir_typed` | Nonempty `supportedInterfaces` required; original v0.3 card rejected. | Exact original bridge rejects this original AP2 card before any payment continuation. |
| `mg_typed` | Origin-root agent-card URL returns 404. | Nested peer configuration fixes discovery location; typed transport remains blocked by the unchanged v0.3 card. |
| `mg_raw` | Same 404. | Nested peer configuration fixes discovery location; raw route still dereferences missing `supportedInterfaces` and only exposes v1 method names. |

Original AP2 pin: `e1ea56db72a6385bce3e5c1112b3a56ce60acb43`.
Original Amir pin: `58eff9da469bccdc432bf164662727947de646b4`.
Original mgcrea pin: `c4d9d3c57c1746abbf9f6aadd3a9912d464eb1f5`.

The original merchant card (`roles/merchant_agent/agent.json:4-6`) advertises
`http://localhost:8001/a2a/merchant_agent`, JSONRPC, and `protocolVersion: 0.3.0`.
`common/server.py:203-207` mounts the card under
`/a2a/merchant_agent/.well-known/agent-card.json`; the original native launcher
selects that RPC base in `roles/merchant_agent/__main__.py:26-33`.

Amir validates the card itself, before its SDK can translate it:
`external/a2a-to-mcp/src/agent-card.ts:180-207`. It requires nonempty
`supportedInterfaces` and explicitly rejects v0.3 cards.

The sealed graph installs SDK 1.1.0 for Amir (`nodes/p002/package`) and SDK 1.3.0
for mgcrea (`nodes/p005/package`). The SDK 1.3.0 resolver contains a legacy card
translator, but **only when `legacyCompat.enabled` is true**:
`nodes/p005/package/dist/client/index.js:5335-5348`. Its JSONRPC legacy transport
is also opt-in at lines 6112-6124; default factory transports omit that option at
lines 6450-6454. The exact original mgcrea bridge constructs its resolver and
transports with `fetchImpl` only (`external/mcp-a2a/src/client/peer.ts:78-87`).
Its typed client uses `supportedInterfaces` at SDK lines 6515-6540; its raw
client directly calls `card.supportedInterfaces.find` at original peer lines
261-278. No original public config exposes `legacyCompat`.

Therefore a path-only successor is not a full-continuation remedy. This
conclusion about the next error is static source evidence, not a newly observed
runtime result. Changing cards, enabling compatibility by editing bridge code,
or inserting a version/transport shim would create a new treatment. None may be
reported as the unchanged pinned bridge against unchanged pinned AP2.

## Continuation requirements beyond discovery

Original `roles/shopping_agent/tools.py:255-311` sends signed payment and optional
checkout mandate DataParts, risk data, caller identity, and debug mode. It stores
the actual returned merchant task ID. OTP continuation adds the original
context, that stored task ID, and the user's exact `challenge_response` DataPart.
The merchant forwards these to a separate processor task and recovers its child
ID from its actual history (`roles/merchant_agent/tools.py:277-318,452-468`).

Both typed bridge tools expose text and task/context references, but do not
expose the required AP2 DataParts. Their send paths also provide no public
argument for the AP2 extension header. The AP2 executor requires activation of
`https://github.com/google-agentic-commerce/ap2/v1` before dispatching a tool
(`common/base_server_executor.py:90-96,171-180`). The raw mgcrea public enum permits
`SendMessage`/`GetTask`, excludes `message/send`/`tasks/get`, and has no headers
argument (`external/mcp-a2a/src/tools/request.ts:11-24,54-71`). Even an externally
rewritten card would not itself repair these independent requirements.

Do not allocate a purported unchanged-bridge full purchase successor under
these pins. Any newly selected bridge revision, exposed compatibility setting,
or owned shim must pass a fresh public-surface eligibility screen and receive a
separate route label before task allocation.

## Original ADK shopper boundary and public native recovery

The retained V7 bank has 19 later OTP/receipt/fault obligations unrealized after
the generic payment return (independent result at
`runs/ap2-original-shopper-development/v7/retained-42886479185-1/extracted/independent-bank-evaluation/result.json`).
Its original tool returns `Status: TaskState.input_required`; the owned V7 model
fixture stops unless it sees `Verification required:`
(`ap2_original_shopper_fixture_v7.py:164-178`). The original shopper checks an
unrealized `status.state == "challenge"` and `status.challenge`, while the
processor actually publishes `input-required` with a `challenge` DataPart under
`status.message` (`merchant_payment_processor_agent/tools.py:123-151`). Wrong OTP
continuation retains `input-required` with `Challenge response incorrect.` at
lines 154-171. The source demo validates exactly `123` at lines 225-227.

A supplied model policy can recognize the generic pending status and call the
unchanged original OTP tool with an explicit user reply. That requires no source
body change and uses the task/context already held by the original caller. It
does not expose the actual challenge or receipt to that model. The original
ADK root lists only six original tools and no Task read
(`roles/shopping_agent/agent.py:84-96`); its payment tools store receipts in state
but return a status string (`roles/shopping_agent/tools.py:275-311,325-332`).

The pinned Python SDK has public `ClientFactory.create(card)` and
`Client.get_task(TaskQueryParams)` APIs. `create` explicitly consumes original
v0.3 `preferred_transport`/`url` (`a2a/client/client_factory.py:183-231`), and
`get_task` returns the current public Task/history (`a2a/client/client.py:131-138`).
The original AP2 wrapper also exposes public `get_agent_card`
(`common/payment_remote_a2a_client.py:67-75`). These are sufficient without
calling `_get_a2a_client`, reading evaluator inputs, or recovering IDs from
private event/grading journals.

Prepared helper: `src/interoperability/ap2_public_task_read_v1.py`. It reads only
the caller-held payment ID/context, obtains the original public card, creates a
public SDK client, and queries that Task. It verifies the returned authority and
returns the public Task to the supplied model. It performs no continuation,
state repair, response selection, agent installation, or dispatch.

Prepared scripted caller:
`src/interoperability/ap2_public_scripted_continuation_v1.py`, with source-bound
process entry `scripts/ap2_public_scripted_continuation_v1.py`. It executes the
full original shopper/business-function prefix and continuation from public
human fact fields only. It verifies original source bytes and loaded function
bodies, rejects an already existing caller signing key, and lets the original
signing function generate the fresh key. It retains original returns, public Task
reads, wrong/no replies, mismatched authority reads, recovery using a previously
returned public Task, and repeated calls. No evaluator outcome is accepted.
Calls are bounded at 60 seconds and the caller at 240 seconds; timeout and
interruption observations are retained. The process admits only the three
original AP2 loopback service ports and blocks evaluator/journal reads,
descendants, and writes outside the task directory.

The parent must launch a fresh original merchant/processor/credential service
group first, using the native entrypoint/provider review below. Set task-local
`TEMP_DB_DIR` and `AGENT_PROVIDER_PUBLIC_KEY_PATH` before importing original
modules, launch the caller with its task directory as its working directory, and
leave caller provider-credential variables unset. Portable Linux execution uses
explicit `--environment-manifest-sha256`, `--site-packages`, and `--task-root`.
The new manifest binds the fresh interpreter, pip report, installed distribution
versions and Linux file inventory; Windows evidence remains a separately named
prior hash. Private runtime state and retained caller output may live in separate
explicit directories. Known standard-library platform metadata is warmed before
the strict actor audit, and blocked evaluator/journal reads are positively probed.
The caller creates no service
and invokes no model. It does not establish the service-launcher/provider
qualification merely by completing a purchase. Both new caller modules have
syntax and unit controls; original business-function/native/provider execution
remains unobserved in this preparation. Controls are in
`tests/test_ap2_public_task_read_v1.py` and
`tests/test_ap2_public_scripted_continuation_v1.py`, using exact retained Task/card
fixtures with source hashes. Constructed business/API doubles do not establish
original outcomes.

Adding this helper to `root_agent.tools` is an **owned public-tool-surface
intervention**, even though original agent and payment function bodies remain
unchanged. A successor must state that treatment explicitly. Keeping an
original-body fingerprint does not establish an unchanged tool surface.

## Smallest substantive successor proposal

Use a fresh name/allocation, after the parent freezes the new runner and public
manifest. Scope it as original AP2 ADK agents with disclosed supplied-model
policy, owned public Task read tool, and native TCP; retain a source-preserving
control without the added read tool. Do not reuse V7/V13/V14 attempt paths.

Five fresh human-present tasks are sufficient for the first meaningful screen:

1. Complete full shopper selection, shipping/payment choice, cart approval,
   original signing and credential association, payment initiation, public
   challenge read, explicit correct reply, original OTP continuation, and actual
   receipt observation. Compare receipt fields across merchant, processor and
   credential-provider public replies; require successful delivery before claiming
   completion.
2. Perform the same prefix and public challenge read, preserve an explicit wrong
   reply, retain the real OTP attempt and its pending/error text, then read that
   Task again. Do not replace the reply with the source demo hint.
3. Perform the same prefix and public challenge read with no user reply. Require
   a truthful waiting result, no continuation call, and no completion/receipt claim.
4. Read a task after a deliberately received foreign context or wrong task
   reference; retain the adverse query/result or SDK error. Require the actor to
   reject mismatched authority rather than inventing a handle or copying a child
   processor reference into merchant continuation. Any later recovery must use an
   authority already returned on the model-visible public surface and retain the
   adverse attempt separately.
5. After actual successful continuation, repeat the unchanged OTP call using the
   actual original task/context. Retain every public reply/receipt and distinguish
   actual idempotence, refusal, timeout, or repeated effects. Do not predeclare
   idempotence from a finite model.

At most five task instances per treatment for this screen. A passed owned-tool
screen qualifies only that public native treatment; it does not retroactively
qualify the 19 V7 bank obligations or any bridge. A broader task bank and real
provider qualification remain separate prospective work.

Before dispatch, the actor must be unable to read evaluator/gold files or
private journals. Its only challenge/receipt inputs must be actual model-visible
tool replies, caller-held source values, and prospectively supplied human choices.
Retain tool schemas, source hashes, all native requests/responses, every failure,
public model requests, tool additions, provider boundary, and unfulfilled branches.

## Sealed SDK evidence

Graph SHA256: `efafadaa673d78dd1e4ccf20d92db9941e00d6bd802d909fdae4c4b8a8278de6`.
Runtime ZIP SHA256: `c4567dc405e74d664921f038e6c5acb454c66fd85f42f21c04a10c8e75305864`.
SDK 1.3.0 client member SHA256:
`0814951d54a43a7cccaad69299f44a567d80cb1a417c0ebe9fb0b79601c9fb89`.
The cited SDK line numbers refer to the exact ZIP member, not an unpinned local
dependency installation. Native-launcher/provider constraints are documented in
`docs/research/ap2-native-launcher-provider-review-2026-11-11.md` before any
dispatch is considered. Its environment-only loopback provider boundary retains
original constructors and serialization but is a synthetic-provider treatment,
with no real-model qualification claim.
