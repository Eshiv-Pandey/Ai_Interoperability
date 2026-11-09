# AP2 human-present native runner design v1

Prepared 30 October 2026 from retained source. **Design only: no new runner,
dependency installation, source import, model call or native AP2 execution has
occurred.** This prepares the procurement domain; it does not qualify CP2/CP3
or earn checkpoint credit. The [source reassessment](ap2-human-present-source-reassessment-v1.md)
records the original task/effect findings separately.
The separate [public assessor design](ap2-human-present-public-assessor-design-v1.md)
is confined to caller-supplied public consistency lanes; it is not a full
source-case or native purchase grade.

## Domain boundary and two distinct clients

The approved [workflow](../../RESEARCH_WORKFLOW.md) permits a scripted reference
agent and real pinned SDK/wire paths (lines 285-296). The primary prospective
case here is **the original merchant A2A front door**, with the original
merchant, payment processor and credentials provider unchanged. Its caller is
a disclosed source-derived scripted reference, using the original shopper's
public request forms and mandate preparation. The merchant's original child
processor task must continue through the merchant. It is not permissible to
resume the processor directly to rescue a failed merchant route.

This is distinct from the original ADK-web shopping frontend. The latter is an
additional original-client control, with its original prompts and output
projection intact. A merchant-front-door success cannot establish successful
ADK-web shopping. Conversely, a shopper projection defect does not establish
that every original merchant public path is unusable.

The prospective contract is a local simulated card purchase: select an offer,
explicitly authorize its amount and payment choice, associate the original
signed mandate with a credential token, receive a public OTP pause, resume the
same merchant and processor tasks, and receive a mandate-referenced receipt.
Do not add real bank settlement or a debit ledger to this contract. Authority,
offer/mandate freshness, task identity, transaction binding and duplicate
effects still need separate reviewed requirements and near misses.

## Retained source and original startup

All AP2 paths below are relative to
`docs/research/source-evidence/ap2-procurement-screen-v1/source/`, at official
Git pin `e1ea56db72a6385bce3e5c1112b3a56ce60acb43`. The
[acquisition](source-evidence/ap2-procurement-screen-v1/source-result.json)
retains 134 files with Git blob and SHA256 closure.

The [human-present scenario](source-evidence/ap2-procurement-screen-v1/source/code/samples/python/scenarios/a2a/human-present/cards/run.sh)
sets `PAYMENT_METHOD=CARD`, uses a shared fresh `TEMP_DB_DIR`, points
`AGENT_PROVIDER_PUBLIC_KEY_PATH` to its signing public key and starts:

| Original entry | Listener and public route |
| --- | --- |
| `python -m roles.merchant_agent` | `127.0.0.1:8001/a2a/merchant_agent` |
| `python -m roles.credentials_provider_agent` | `127.0.0.1:8002/a2a/credentials_provider` |
| `python -m roles.merchant_payment_processor_agent` | `127.0.0.1:8003/a2a/merchant_payment_processor_agent` |
| Separate original-client control: `adk web code/samples/python/src/roles` | ADK web on 8000; select `shopping_agent` at `/dev-ui` |

Run these entries only from an exclusive staged source/environment. Do not run
the convenience script in the evidence/workspace root: it clears `.logs` and
recursively removes `TEMP_DB_DIR`, creates/syncs an environment and owns several
children. Reproduce the supported module/configuration entries with a runner
that creates fresh directories rather than deleting old evidence. Preserve the
hard-coded URLs/cards/ports; an occupied original port makes the native
allocation ineligible, not grounds to kill another listener or rewrite cards.

`common.server` constructs the original `DefaultRequestHandler`,
`InMemoryTaskStore`, `SimpleRequestContextBuilder` and
`A2AStarletteApplication`. Discovery is at each RPC prefix plus
`/.well-known/agent-card.json`. The original `PaymentRemoteA2aClient` requests
the AP2 extension `https://github.com/google-agentic-commerce/ap2/v1` through
the pinned SDK extension header, sends the original `Message`, consolidates
events with the original `ClientTaskManager` and returns its `Task`. Record
actual native discovery and requests; card application version is not a new
protocol qualification. Merchant card bytes declare `protocolVersion=0.3.0`.
Original `A2aMessageBuilder.add_data` omits every falsey value, including
`False`, an empty risk string and an empty challenge response. Preserve this
omission rather than emitting a fixed dictionary containing those fields.

## Scripted source-case caller and preparation

The first implementation should preserve the complete prelude below in every
fresh case. It must not preseed merchant carts, credential tokens, task stores,
successful replies or a fixed receipt. Model-selected catalog and router
outputs are original application behavior; they can fail and must be retained.

Use the exact hashed original caller tool functions in a separate reference
process, with an explicitly disclosed caller state carrier. Every inspected
caller read/write is through `tool_context.state`; a minimal state carrier is
a harness context, **not an ADK `ToolContext` or the original LLM shopper**.
Before executing this design, source review must close the state access
footprint and retained business byte identity. Do not patch annotations,
business functions, remote clients, mandate classes, issuers or signature checks.

| Step | Original caller operation and required public/state binding |
| --- | --- |
| 1 | `subagents.shopper.tools.find_products(catalog_search, context)` calls merchant with original search/risk/shopping-agent fields. Capture returned carts and adopt only the returned `task.context_id` as `shopping_context_id`. |
| 2 | Select a returned `cart_id` using original `select_cart`; selection must satisfy the task's offer/budget choice and remain tied to the captured cart. Do not assume `cart_1` before discovery. |
| 3 | `shipping_address_collector.tools.get_shipping_address` obtains the declared demo account's public address. The source account `bugsbunny@gmail.com` is fixture data, not a supplied real account. |
| 4 | `payment_method_collector.tools.get_payment_methods` then `get_payment_credential_token` uses an actually returned eligible alias after recorded scripted/user selection. Source CARD eligibility is amex/mastercard, not all methods. |
| 5 | `shopping_agent.tools.create_checkout` uses the selected cart and captured context; retain the merchant-signed checkout JWT, hash, amount/currency and returned task/artifacts. |
| 6 | Record explicit approval of the actual checkout summary. Only then execute original `create_checkout_mandate` and `create_payment_mandate`. The original latter sets `transaction_id=checkout_hash`; the original key helper creates the shared demo signing key/public file if absent. |
| 7 | `send_signed_mandates_to_credentials_provider` makes the original public signed-mandate call. Grade its real task status separately; the tool returns a success string without itself checking the returned status. Require the original CP token association evidence before claiming preparation succeeded. |
| 8 | Send the exact merchant initiation `Message` from `initiate_payment`: context, signed PaymentMandate, optional signed CheckoutMandate, risk data, `shopping_agent_id=trusted_shopping_agent`, unchanged debug setting and text `Initiate a payment`. The scripted caller keeps the actual public merchant `Task`, not just the shopper tool's string. |
| 9 | After the actual merchant task is publicly `input_required` with the forwarded OTP request, obtain the contract's OTP response. Use the original public message form from `initiate_payment_with_otp`: **same merchant task ID and context**, original mandates/risk/shopping-agent fields, `challenge_response` and text `Initiate a payment. Include the challenge response.` |
| 10 | Require the same merchant task's terminal status and original receipt artifact. Confirm processor original-task continuation and credential/receipt dependencies using separate retained peer evidence. |

Steps 8-9 can be implemented by invoking the original message builder/client
with the exact source-derived request forms while keeping their returned Task.
They must not call the original status-only shopper wrappers and then invent
missing Task fields. The implementation is a scripted public client at the
merchant boundary and must be labelled that way. The optional full ADK-web
control instead invokes the original shopper tools through ADK and retains
their original output loss.

## Same-task hierarchy and original challenge mismatch

The catalog, address, payment-method, token, checkout and CP association tasks
are distinct original tasks sharing a shopping context. Do not call the entire
shopping session one A2A task. Merchant initiation creates merchant task `M`;
the original merchant creates processor task `P` with the same context. The
processor emits `input_required` with a text request and DataPart `challenge`.
The merchant forwards its state and status message to `M`.

The merchant executor also retains the original instruction that a
`checkout_mandate` request must select `dpc_finish`. Its resolver receives only
the first text part, system instructions and tool docstrings, not the actual
DataParts. The original initiation text is `Initiate a payment` while the
optional CheckoutMandate is a DataPart. This is a source-supported possible
router mismatch, not proof that a mandate forces a misroute. Record the
original Gemini tool choice; do not force `initiate_payment` or repair the
system prompt to obtain a favorable native path.

For OTP resume, the public caller addresses `M`. Original merchant
`tools.py:452-469` scans `current_task.history` in forward order and returns the
first `message.task_id != merchant task.id`. It does not verify message role,
sender, uniqueness or even that the candidate ID is non-null. The runtime
must show that the selected ID actually equals the original pending `P`.
Do not replace this heuristic with a corrected binding or fill in `P` from
private observations. Ambiguous/absent association stays a failed or unknown
binding result, not qualified continuation.

The original shopper `tools.py:277-280` saves `M`, then tests state
`"challenge"` and `task.status.challenge`. Original processor
`tools.py:135-151` emits `input_required` with DataPart challenge instead.
Consequently the shopper's inspected public tool result is the generic
`Status: input_required`; the exact native enum representation still needs
observation. The original OTP wrapper does retain `M`/context and can send the
expected response if called. This mismatch is an original-client control
question, not an inevitable processor failure. Do not inject the hidden
challenge into the original LLM shopper, alter its schema, force an unrequested
OTP tool call, or mark this source screen complete-negative.

## Evidence, reset and grade boundaries

A new passive recorder should wrap the original ASGI app/SDK observation
boundaries in the bootstrap without changing requests, response entities,
event objects, application selection or emitted order. Its own overhead and
placement are disclosed. Retain every original HTTP receive/send event,
method/path/status/header/entity byte sequence, per-service request identity,
original public Task/status/artifact/history and every attempted caller turn.
No hidden expected trajectory, gold answer or grade enters the caller/model.
The existing human-oriented `watch.log` truncates mandates and is not a
byte-exact receipt or sole evidence source.

Distinct service clocks/recorder sequence are not causal ordering by
themselves. Bind sender/recipient, actual request and returned task/context,
original parent/child message IDs and observed terminal boundaries. Preserve
model-router choices and actual call/reply ordering; same-context coincidence
does not establish unique child-task or credential support.

Evaluator-only snapshots should capture original merchant `storage._store`,
CP `account_manager._token`, original task-store state and caller state at
defined before/after boundaries. Retain exact loaded-module origins/hashes
and snapshots before clean owned shutdown because these stores are in-memory.
Do not make snapshots a new public API or feed them into admission decisions.
The original CP associates its latest unbound token with a transaction ID;
credential lookup uses that ID. Wrong-token association, multiple unbound
tokens and valid different signed mandates are necessary near-miss designs.

Grade these lanes separately: offer/approval/amount authority; signed-mandate
validation and freshness; token-to-transaction association; public merchant
pause and same-task resume; original processor association/resume; successful
raw-credential response; PaymentReceipt schema/reference; propagation to the
same merchant task; duplicate/repeated delivery behavior; final task answer
grounding. A successful reply string or a valid signature cannot substitute
for the original purchase outcome. Original CP receipt handler completes
without business mutation; no post-payment ledger, atomic debit, durable
exactly-once or settlement claim follows.

The receipt reference must match the hash of the closed original PaymentMandate
JWT using the actual original SDK semantics, not the entire presentation's
string hash. Require its `Success` status and observed common payment/network/
PSP identifiers to agree with the original processor artifact and merchant
propagation. This does not prove same-pending-transaction enforcement: validate
that separately against the task contract and near misses.

Reset by allocating fresh source-stage/config/temp/log/caller/evidence roots
and new owned merchant/processor/CP processes for every case/variant. Verify
empty original stores before the first business operation, distinct context
and task IDs, and absence of retained keys/state contamination. Never reset by
deleting consumed allocations or rewriting the source archive. A first native
source case is diagnostic; it is not held-out data or two-domain completion.

## Dependency, model and ownership gates

ADK **1.28.0** and A2A SDK **0.3.24** wheel bytes/source metadata are already
retained. The sample/root pyprojects pin many direct dependencies but have no
Python lockfile; its `x402-a2a` declaration is an unpinned VCS URL, and root
dependency `py` also lacks a version. The new
[dependency plan](ap2-human-present-dependency-plan-v1.md) selects the public-origin
x402 source `125db5526a965d2325459d1a9df2e274a7e42396` with verified Git object
identities. This is a preparation-time selection, not an original AP2 lock.
Resolve a complete platform/interpreter-specific graph,
retain wheels/metadata/hashes and pin the exact VCS object in a new environment
record before a reproducible native launch. This is environment resolution,
not permission to edit upstream pyprojects or silently drop x402 imports.
Record any missing source subset/build input and resolve it at the original
Git pin. Existing AgentOps dependencies are a different environment.

The original Gemini model is `gemini-3.1-flash-lite-preview` in shopper,
catalog and router sources. The resolver calls Gemini even for one-tool
dispatch. Existing private DPAPI storage and `scripts/with_gemini_key.ps1`
remain the only key injection path; no credentials belong in plans, command
arguments, logs or source. The earlier synthetic provider check is not a
workflow run or a future allowance. Before a model-bearing allocation, record
verified remaining-use/counting/reset constraints and the task-owned atomic
usage ledger required by the workflow. Preserve original model retries and
count every attempted request, including failures; freeze caps and stopping
rules prospectively rather than stopping on a favorable payment result.

Use the existing native ownership design as a contract, not the AgentOps
application-specific runner unchanged: exclusive new allocation, Windows
Job ownership, process creation identity and listener/connected-peer PID
verification before accepting readiness or each request. All three hard-coded
service ports must be free initially. Do not trust arbitrary HTTP 200 responses.
Source-bound discovery and distinct successful original readiness establish
startup; no business/model request is a readiness probe. Only task-owned
children may be stopped, with exit/cleanup/empty-job receipts for each.

The fixed resource minima stay **1,073,741,824 bytes available physical memory**
and **2,147,483,648 bytes available commit**. Use fresh prospective prestage and
prelaunch receipts with two passing observations separated by 10-30 seconds,
both UTC and monotonic intervals consistent within one second. Bind exact
source/environment/command/allocation/service identities. At every bootstrap
main entry, validate the exact prelaunch receipt with a nonnegative age at most
60 seconds and check immediate current headroom before original SDK/business
imports. Starting one service can exhaust memory needed by the next, so a
prior passing group sample is not enough. Retain refusals before staging/
launch without relaxing minima or stopping unrelated apps/services.

## Implementation sequence and exit criteria

1. Freeze a reviewed merchant-front-door diagnostic task and faithful original
   caller state/message plan, keeping the optional full shopper control separate.
2. Close dependency/VCS/source inputs and prepare the isolated environment
   manifest without overwriting retained upstream evidence.
3. Implement a multi-service owned bootstrap, passive ASGI/private-state
   recorder, source-derived scripted caller and closed-evidence validator.
   Use meaningful synthetic adversarial checks for ownership, task binding,
   refusal, partial recording and byte-identical pass-through before native use.
4. Review exact source/client/observer hashes and resource/usage/stop policy.
5. Only after fresh fixed gates pass, allocate a new once-only native diagnostic,
   retain every prelude/router/request/outcome/cleanup result and independently
   assess its original-task and purchase obligations. No native command exists
   merely because this design is written.
6. Qualification needs successful reset/reference and reviewed near misses,
   actual pinned bridge routes/crossing placement, independently reviewed gold
   and the development/calibration/held-out corpus. A diagnostic native success
   alone cannot pass CP3, establish a contribution or raise the current 5%.

## Source identities checked for this design

| Relative AP2 source path | SHA256 |
| --- | --- |
| `code/samples/python/scenarios/a2a/human-present/cards/run.sh` | `4056da39baf86897b0e7bcd4e21243f8ab93cc7ec286034256719203bc488305` |
| `code/samples/python/scenarios/a2a/human-present/cards/README.md` | `6aa7d6fcec24a82c9ed25529cd0da5914ff85a47e77b317bd96a1dbaa082f415` |
| `code/samples/python/src/common/server.py` | `1c97a4ba39a191a829d36effe24344616075b1dd03437126bfa31f58d7d04a4b` |
| `code/samples/python/src/common/base_server_executor.py` | `a1e1f85ba4481aa1712d01bef83778c9ab970ed2e3856fdafc4fb821d48f27a9` |
| `code/samples/python/src/common/payment_remote_a2a_client.py` | `88bd46d93eb7408912c254b4dc6a392a821d07eabc049c5a04a42b8627042efb` |
| `code/samples/python/src/common/a2a_message_builder.py` | `d92cccc6cb9478b160f95cee0c060f9c0dc41f25266d8220cf48a5bbeba95061` |
| `code/samples/python/src/roles/shopping_agent/tools.py` | `612525025661b608a662a8a09bc50ea527543b26c3bdbc78911bd95f6c3926a6` |
| `code/samples/python/src/roles/shopping_agent/subagents/shopper/tools.py` | `7a577d4088dc9decb3bbe72d3162e356176a4f6b1b0c3cb87d496be4e6245bc4` |
| `code/samples/python/src/roles/shopping_agent/subagents/payment_method_collector/tools.py` | `be4b5fea7a4c0eef965694cde93205ce1b1652a36c0f121fa7ec6d820fbed8dd` |
| `code/samples/python/src/roles/shopping_agent/subagents/shipping_address_collector/tools.py` | `6c11b152344289c075fc66595c7ed344a37c2762c549532c8a9c275ecf8d542d` |
| `code/samples/python/src/roles/merchant_agent/tools.py` | `513b7a6dd5d92ef2a0b355e77003706ffcec77ac662d42161fb638ef98f816d3` |
| `code/samples/python/src/roles/merchant_agent/agent_executor.py` | `523e1dbe5cb21eb821b861f2bd283e96af464bf0651964b65e9f0ffca8a2df68` |
| `code/samples/python/src/roles/merchant_agent/storage.py` | `425838c273be4c316b7bef5c83584b4541ef1520d7304073741794132631abdf` |
| `code/samples/python/src/roles/merchant_agent/agent.json` | `f5d67bace1fc46401d1e87d79660fc950028acb959485754a4d004792d3ef388` |
| `code/samples/python/src/roles/merchant_payment_processor_agent/tools.py` | `41a11923ae38798099c39a25d95d358ab1845320f64f8833b4955fa09b04e12d` |
| `code/samples/python/src/roles/credentials_provider_agent/tools.py` | `b369fa1c0990abc71866915d30a7b2843d6881cf23094abb7e031679e0d979bf` |
| `code/samples/python/src/roles/credentials_provider_agent/account_manager.py` | `39f80ac02cf60a69eb223ce54c2a66842ab869c1ce6fedf11aedeb7243f2fef8` |
| `code/samples/python/pyproject.toml` | `0121f705c05aa3836cff7a7fb4d967b9e3af7a3983a4e78f3cb0f19747b7fbf1` |
| `pyproject.toml` | `78656cfd88b01d10c693a7fdffdf9d789dc4ddfbb57c208b583e13986fd44b63` |

Resource reference contracts: `src/interoperability/upstream_agentops_native_runner_v2.py:264-277`
and `scripts/serve_upstream_agentops_cases_v2.py:121-158`. Existing owned-job
and TCP ownership helpers remain separately scoped; no AP2 compatibility test
was performed by writing this note.
