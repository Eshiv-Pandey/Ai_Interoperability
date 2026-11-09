# AP2 human-present source reassessment, 30 October 2026

The original human-present card scenario is a substantive source lead for a
second application domain. Its merchant and processor have an original A2A
input-required continuation, and the processor can retrieve credentials
associated with a signed transaction before returning a payment receipt. It is
not an inevitable empty-artifact failure. Native execution, reset validation,
original-task completion and benchmark qualification remain unproved.

This note supersedes a debit-ledger-based rejection of that source lead. CP3 in
[the checkpoint rubric](checkpoints.md) does not require a real-money debit
ledger. The approved procurement scope does require reviewed application tasks,
reference trajectories, pending-input/identity checks and independently observed
outcomes. A generated receipt alone does not prove all of those requirements.
The original human-not-present MCP shopping variant remains a separate
implementation; none of its file-backed order effects are assigned to this one.

## Exact original path

All application paths below are relative to the retained
[Python sample](source-evidence/ap2-procurement-screen-v1/source/code/samples/python/)
at official Git pin `e1ea56db72a6385bce3e5c1112b3a56ce60acb43`.

The original launcher is
[`scenarios/a2a/human-present/cards/run.sh`](source-evidence/ap2-procurement-screen-v1/source/code/samples/python/scenarios/a2a/human-present/cards/run.sh).
It starts `roles.merchant_agent`, `roles.credentials_provider_agent` and
`roles.merchant_payment_processor_agent` on ports 8001, 8002 and 8003, then
`adk web --host 0.0.0.0 code/samples/python/src/roles` (128-144). The outer
human-facing shopper is an ADK application, not the shopping_agent_v2 A2A
frontend or the unrelated retained TypeScript A2A client. The
[`shopping_agent/agent.py`](source-evidence/ap2-procurement-screen-v1/source/code/samples/python/src/roles/shopping_agent/agent.py)
instructions (48-78) prescribe product selection, shipping address, user payment
method selection, checkout, human confirmation, signed checkout/payment mandates,
credentials-provider association, payment initiation, OTP and receipt display.

The next unchanged application path to exercise is that sequence through ADK
web, retaining its child A2A traffic. The same-original-A2A-task requirement
applies to each suspended merchant/processor payment task. It must not be
misapplied to the outer ADK conversation or satisfied by merely sharing a session.
A direct externally constructed merchant/processor request can be a separately
labelled endpoint control, but cannot stand in for completion of the original
shopper sequence.

## Task and context hierarchy

The
[`A2aMessageBuilder`](source-evidence/ap2-procurement-screen-v1/source/code/samples/python/src/common/a2a_message_builder.py)
sets the actual message `context_id` and `task_id` (71-79), not the JSON-RPC
request ID. The original
[`PaymentRemoteA2aClient`](source-evidence/ap2-procurement-screen-v1/source/code/samples/python/src/common/payment_remote_a2a_client.py)
passes that message to the SDK, collects task events and returns the resulting
Task (77-101); it activates required extension headers when creating the client
(103-109). The
[`BaseServerExecutor`](source-evidence/ap2-procurement-screen-v1/source/code/samples/python/src/common/base_server_executor.py)
requires the payment extension, uses supplied task/context identity for
TaskUpdater and passes `context.current_task` into the selected tool (90-114).

| Original step | Task binding in inspected source | Required retained observation |
| --- | --- | --- |
| Shopper starts payment | `shopping_agent/tools.py` 263-277 sends the shopping context and stores returned merchant `task.id` as `initiate_payment_task_id` | Initial merchant task/context and public challenge response |
| Merchant starts processor payment | `merchant_agent/tools.py` 277-300 forwards context, mandate and risk data; initial child task is distinct from merchant task | Initial processor task/context; parent-child message association |
| Processor requests OTP | `merchant_payment_processor_agent/tools.py` 108-151 uses input_required and a challenge DataPart | Original processor input-required state and challenge-bearing message |
| Merchant propagates suspension | `merchant_agent/tools.py` 315-318 forwards the processor status and status message | Merchant input-required state; forwarded message still carrying processor identity |
| Shopper submits OTP | `shopping_agent/tools.py` 293-307 sends the saved merchant task ID, shopping context, mandate, risk and challenge_response | Follow-up actual message.taskId/contextId equal to public pending merchant identity |
| Merchant resumes processor | `merchant_agent/tools.py` 296-300 sets a child task ID recovered from current merchant history | Follow-up actual child task/context equal to public pending processor identity |

The child-ID recovery is a heuristic, not a verified robust mapping:
`merchant_agent/tools.py` 464-469 iterates `task.history` **forwards** and returns
the first message whose `message.task_id != task.id`. There is no role check,
reverse scan, nonempty-ID check or explicit processor-origin check. An earlier
message with a missing or unrelated task ID may defeat the intended mapping.
Qualification must retain the full original history and prove which message the
unchanged helper actually selects; a caller-provided path label is insufficient.

The pinned A2A SDK 0.3.24
[`TaskUpdater`](source-evidence/ap2-procurement-screen-v1/adk-task-mapping-v1/a2a-sdk/source/a2a/server/tasks/task_updater.py)
constructs task events using updater identity (65-108), forwards the supplied
status Message without rewriting it and maps `requires_input` to
TaskState.input_required (192-201). Its `new_agent_message` attaches updater
task/context identity (210-238). The
[`TaskManager`](source-evidence/ap2-procurement-screen-v1/adk-task-mapping-v1/a2a-sdk/source/a2a/server/tasks/task_manager.py)
retains status messages in history (143-147, 260-269). These source paths explain
why a processor message can appear in merchant history; no observed successful
continuation is inferred from them.

## Credential effects and receipt obligations

The original HP account store is
[`credentials_provider_agent/account_manager.py`](source-evidence/ap2-procurement-screen-v1/source/code/samples/python/src/roles/credentials_provider_agent/account_manager.py).
It has process-local `_token = {}` (130). Card token creation writes the user's
email, selected method alias and an initially unbound mandate ID (181-189).
`update_token_by_transaction_id` binds the most recently created unbound token
to the supplied transaction ID (206-218). This is an actual in-memory mutation,
with no explicit user/task parameter on that binding operation. Cross-account
interleaving and two unbound-token ordering are relevant adverse cases; they are
not observed defects from this source inspection.

The
[`credentials-provider tools`](source-evidence/ap2-procurement-screen-v1/source/code/samples/python/src/roles/credentials_provider_agent/tools.py)
provide both the binding-only handler (`handle_signed_payment_mandate`,
192-215) and the raw-credential handler
(`handle_get_payment_method_raw_credentials`, 116-154). The latter verifies the
supplied mandate, obtains its transaction ID, looks up previously associated
credentials and returns a DataPart artifact; an unassociated transaction raises
an error. Both are registered in
[`agent_executor.py`](source-evidence/ap2-procurement-screen-v1/source/code/samples/python/src/roles/credentials_provider_agent/agent_executor.py)
61-68. The processor's natural-language credential request can therefore route
to a handler that returns data. A model selection of the binding-only handler
can still produce empty artifacts, but that outcome is contingent, not forced by
the tool registration.

The
[`processor tools`](source-evidence/ap2-procurement-screen-v1/source/code/samples/python/src/roles/merchant_payment_processor_agent/tools.py)
validate the literal demonstration OTP `123` (225-227). Completion verifies the
currently supplied PaymentMandate, requests credentials (174-196), checks the
credential task state and nonempty artifacts (230-251), constructs a PaymentReceipt,
delivers it to the credentials provider and publishes it before completing
(203-222). Receipt construction (254-273) sets status Success and references the
SHA256 base64url hash of the **closed mandate JWT**. The payment/network/PSP
confirmation IDs all use the same fresh UUID. Merchant tools propagate the
receipt artifact (302-313); shopper tools store it in ADK state (325-332).

These are simulated credentials and payment receipt semantics. The
credentials-provider receipt handler explicitly does nothing and completes
(298-312). No inspected post-OTP debit, reservation, durable order ledger or
deduplication mutation is claimed. That limits task/effect claims; it is not an
extra bank-ledger eligibility gate. A future domain task must retain original
credential association, mandate verification, authentic public task history,
receipt reference and actual declared simulated outcome. Signature success or
success text without the rest of the trajectory cannot be scored as purchase
completion.

There is also no inspected guard binding a pending processor task to the exact
PaymentMandate presented on its first message. `_handle_payment_mandate`
(108-120) uses task state to decide whether to challenge or complete, then
completion verifies and uses the **follow-up supplied** mandate (181-184).
The credentials provider checks that supplied transaction against its prior
token association, which is different from checking the original pending
transaction. A distinct valid, already associated signed mandate submitted on
the pending task must remain a reviewed near miss. Neither its rejection nor
its successful payment is established. Duplicate-side-effect scoring likewise
requires an explicit application contract; A2A protocol idempotency alone does
not supply one.

## Original shopper mismatch

The processor publishes `input_required` with a challenge object inside a
DataPart in `task.status.message` (135-151). Merchant tools forward that state
and message. The shopper's `initiate_payment` and OTP tool instead check
`task.status.state == "challenge"` and `task.status.challenge`
(`shopping_agent/tools.py` 278-280 and 309-311), returning only a generic
`Status: input_required` on the inspected path. That hides the original
challenge details from the root agent's tool result. Its instruction to relay
an OTP request does not prove the model will infer or obey it from that string.

This is an unchanged-source compatibility gap that a live control must retain.
Do not patch the shopper, inject a long-running tool, provide evaluator-private
mandates/IDs to the model or silently submit an OTP to turn a failed original
workflow into a favorable result. A diagnostic user follow-up or direct child
endpoint control must be labelled as such and must not upgrade the original
front-end result.

## Reset, dependencies and qualification boundary

The original scenario launcher deletes logs/temp-db and terminates port
listeners (the original full script is retained). It must not run directly in
the current workspace. An owned, fresh isolated allocation can launch original
modules while retaining all attempts and verifying that ports belong to that
allocation. A fresh credentials-provider process resets the inspected `_token`
dictionary; fresh server task stores, shopper session state, cart state and
generated keys still need exact lifecycle/reset validation. Resettable source
structure is not a tested reset.

The acquired AP2 source subset has no dependency lockfile. A2A SDK 0.3.24 and
ADK 1.28.0 are declared, but the x402 VCS dependency lacks a commit pin. The
original model routing remains Gemini-dependent, even for server tool
selection. Private configured key access and the earlier synthetic provider
smoke result do not qualify this workflow. No source import, installation,
native server/client launch, model call or application trial was performed for
this note. Resource minima remain 1 GiB available physical and 2 GiB available
commit with prospective timed observations and bootstrap validation.

The next artifact is the separately authored
[native-runner design](ap2-human-present-native-runner-design-v1.md). Native
qualification requires exact original entry and request paths, resolved pinned
dependencies, owned processes, raw public child task/history/HTTP observations,
original human-selection/confirmation order, reset evidence, independent gold
and source-consistent mandate/credential/receipt assessment. CP3 additionally
needs its reviewed development/calibration/held-out corpus, crossing placements,
baselines and ablations. This source note supplies no checkpoint percentage,
method novelty, bridge eligibility or completed second domain.

## Byte binding checked for this note

On 30 October, all 13 following current AP2 file SHA256 values matched their
entries in the retained
[acquisition result](source-evidence/ap2-procurement-screen-v1/source-result.json).
Paths are relative to `code/samples/python/` within the retained source above.
SDK helper hashes identify the separately retained pinned wheel source, not
AP2 Git blobs. This was a read-only source comparison, not runtime authentication.

| Path | SHA256 |
| --- | --- |
| `scenarios/a2a/human-present/cards/run.sh` | `4056da39baf86897b0e7bcd4e21243f8ab93cc7ec286034256719203bc488305` |
| `src/common/base_server_executor.py` | `a1e1f85ba4481aa1712d01bef83778c9ab970ed2e3856fdafc4fb821d48f27a9` |
| `src/common/a2a_message_builder.py` | `d92cccc6cb9478b160f95cee0c060f9c0dc41f25266d8220cf48a5bbeba95061` |
| `src/common/payment_remote_a2a_client.py` | `88bd46d93eb7408912c254b4dc6a392a821d07eabc049c5a04a42b8627042efb` |
| `src/common/server.py` | `1c97a4ba39a191a829d36effe24344616075b1dd03437126bfa31f58d7d04a4b` |
| `src/common/function_call_resolver.py` | `0504bda987763db99b0faf847a839d2d8ab5cbac6a16b00c609d98f4f395a747` |
| `src/roles/shopping_agent/agent.py` | `a1ad77fc4d17cfa2fcef5904cab00a9833395e4a4e8b60948d767d52640ec6a3` |
| `src/roles/shopping_agent/tools.py` | `612525025661b608a662a8a09bc50ea527543b26c3bdbc78911bd95f6c3926a6` |
| `src/roles/merchant_agent/tools.py` | `513b7a6dd5d92ef2a0b355e77003706ffcec77ac662d42161fb638ef98f816d3` |
| `src/roles/merchant_payment_processor_agent/tools.py` | `41a11923ae38798099c39a25d95d358ab1845320f64f8833b4955fa09b04e12d` |
| `src/roles/credentials_provider_agent/tools.py` | `b369fa1c0990abc71866915d30a7b2843d6881cf23094abb7e031679e0d979bf` |
| `src/roles/credentials_provider_agent/agent_executor.py` | `0932eb790bbc2c173cd79cb33730e4c3d6af5bee4bc5587b0c24412c44b75fd0` |
| `src/roles/credentials_provider_agent/account_manager.py` | `39f80ac02cf60a69eb223ce54c2a66842ab869c1ce6fedf11aedeb7243f2fef8` |
| A2A SDK `server/tasks/task_updater.py` | `5a75c1f24ac2f8a49e975c4fb254239642d31fecae6850ef322e8eba97d94d91` |
| A2A SDK `server/tasks/task_manager.py` | `640eef411fa6611e2c588a5cd2ed1ff710bcd4145dfcffda1bb48b1f069932a2` |
