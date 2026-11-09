# AP2 human-present reference planning v1

30 October 2026. The [pure reference planner](../../src/interoperability/ap2_hp_reference_plan_v1.py)
and [planning CLI](../../scripts/ap2_hp_reference_client_v1.py) implement the
source-derived merchant-front-door prelude and public message planning in the
[native design](ap2-human-present-native-runner-design-v1.md). **This is
preparation software, not a full native runner or an executed AP2 purchase.**
All dispatch/native eligibility fields are false. The CLI's `--execute` mode
unconditionally refuses before loading its input or helper and before any
original AP2/SDK import, key access, client request or model call. A supplied
resource receipt alone cannot enable execution.

## Implemented planning path

The planner consumes separately supplied, finite plain JSON observations one
phase at a time. It validates into a copied state and commits the phase only
after all checks succeed. Malformed, ambiguous, out-of-order, cross-context or
contract-discrepant observations do not advance it. Supplied observations and
returned reports are copied; none is authenticated native evidence.

| Phase | Supplied result required before advancing |
| --- | --- |
| `catalog` | Completed public Task with returned context and canonical `ap2.cart` objects; duplicate cart IDs are ambiguous. |
| `cart_selection` | An actual returned cart ID satisfying the declared currency and reference spending cap. |
| `shipping` | Completed Task in the returned context and one canonical ContactAddress; known optional string/null and address-line types are checked. |
| `payment_methods` | Completed Task in context; the original first DataPart supplies eligible aliases. |
| `payment_selection` | An actually returned eligible alias. |
| `credential_token` | `{task, agent_card}`: completed token Task and the actually discovered provider card. The retained token URL comes from its `url`, not a fabricated card. |
| `checkout` | Completed Task in context with one checkout matching the selected offer; exact JWT/hash and source rounding are checked without signature trust. |
| `approval` | `{approved: true, summary: ...}` matching the complete actual checkout/address/payment summary with exact JSON types. |
| `checkout_mandate` | Supplied actual original signer output. No key or signed mandate is created by this planner. |
| `payment_mandate` | Supplied actual original signer output. Its signature, issuer and transaction semantics remain unverified. |
| `cp_association` | Completed public original association Task. Credential-to-transaction state association remains unknown. |
| `payment_start` | Public merchant Task in `input_required` with an unambiguous public DataPart OTP challenge. The hidden shopper `status.challenge` field cannot substitute. |
| `otp_response` | Explicit caller string response to that public challenge; it is not forced to the demo value. |
| `payment_resume` | The later public Task has the same merchant task ID/context. Completed, still-pending and original failure states are retained separately. |

The declared contract has exactly `catalog_search`, `user_email`, `currency`
and nonnegative integer `max_amount_cents`. Selections and actual-summary
approval are subsequent supplied observations, not invented discovery results.
The spending cap is a stricter reference-caller decision rule; it does not prove
that upstream enforces a budget constraint. Prelude raw task IDs must be
distinct in this plan. This is a reference consistency condition, not a claim
that upstream guarantees global ID uniqueness across services.

Message planning preserves the original text, DataPart ordering and falsey
omission, including omission of `debug_mode=False` and an empty OTP response.
Each message requires an explicitly supplied lowercase 32-hex planning nonce.
That is a coarse shape placeholder, not evidence of original UUID4 generation,
freshness or caller control over an original builder nonce.

The public payment resume targets only the original merchant endpoint using
its observed pending task/context. No processor endpoint or hidden child ID
can be supplied as a rescue route. Plans require the original pinned client
and the `X-A2A-Extensions` AP2 header; Message metadata cannot substitute for
that transport precondition. Actual SDK envelopes, headers, routing and
child-task linkage have not been executed or authenticated.

## Pure CLI input

An initial planning file has this shape:

```json
{
  "contract": {
    "catalog_search": "coffee maker",
    "user_email": "declared-demo@example.test",
    "currency": "USD",
    "max_amount_cents": 10000
  },
  "observations": []
}
```

Subsequent observations are objects with exactly `phase` and `value` fields,
in the table's order. The file is a pure planning input; it is not a native
source-case result or held-out corpus. A prepared invocation is:

```powershell
C:\Python313\python.exe -I -S -B scripts/ap2_hp_reference_client_v1.py --input path/to/planning-input.json --message-id aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
```

The CLI returns the next action and current planning report as JSON on stdout.
It rejects duplicate object keys and nonfinite numbers before constructing a
phase. A phase rejection records its reason and accepted phase count. No
application, client, signing function or credential helper is executed by
this command. Do not treat a printed public-message plan as a dispatched
request. Any eventual execution wrapper needs its own prospectively retained
allocation and original outcome recording.

## Captured validation and exact limits

The two completed captures are separate scopes and must not be rerun:

| Suite | Captured result | Scope |
| --- | --- | --- |
| Reference plan v1 | [24 passed tests](../../runs/ap2-hp-reference-software/reference-plan-v1/result.json), zero failures/errors/skips | Constructed phase/message/approval/identity/failure controls; four original caller files parsed and hash-checked without importing them; actual `--execute` refusal path. |
| Reference CLI v1 | [3 passed tests](../../runs/ap2-hp-reference-software/reference-cli-v1/result.json), zero failures/errors/skips | Previously unexecuted actual initial pure CLI success, duplicate-key rejection and nonfinite-input rejection. The 24-test suite was not rerun. |

The reference-plan allocation retains **three own code/test copies**, exact
stdout/stderr bytes and its result. Four original caller files have recorded
before/after digests and matching current source bytes; they were not copied
into that allocation. The separate CLI allocation retains three own code/test
copies, logs and its result. The capture orchestration was inline in the tool
turn rather than a retained driver/plan file. These receipts support bounded
software/captured-membership consistency, **not seven captured code copies,
an isolated snapshot replay, capture authenticity or native qualification**.
The [separate source review](ap2-human-present-reference-plan-source-review-v1.md)
found no remaining blocker at pure planning/refusal scope. Independent retained
receipt audits verified [44 planner checks](../../runs/ap2-hp-reference-software/reference-plan-v1-independent-review.json)
and [36 CLI checks](../../runs/ap2-hp-reference-software/reference-cli-v1-independent-review.json)
without rerunning or importing tests/application code. They verify bounded
current/captured bytes, AST/log membership, hash bindings and preservation.
Execution and zero original/model/key counters remain recorder assertions
corroborated by inspected pure source; the audits add no capture authenticity,
isolated execution, human validity or native/scientific claim.

The [bounded source review](ap2-human-present-reference-plan-source-review-v1.md)
found no remaining pure-planning/refusal blocker. Independent retained-receipt
audits verified [44 planner checks](../../runs/ap2-hp-reference-software/reference-plan-v1-independent-review.json)
and [36 CLI checks](../../runs/ap2-hp-reference-software/reference-cli-v1-independent-review.json),
with zero discrepancies and no test reruns. Those audits retain the limitations
above; they establish no isolated replay or native qualification.

The static footprint checks exact retained bytes of
`shopping_agent/tools.py` and the shopper, shipping-address and payment-method
tool modules. Each inspected `tool_context` attribute access is through
`.state`. Parsing these four files closes that static access footprint only;
it does not construct an ADK ToolContext or establish runtime equivalence of
an emulated caller context.

| Current implementation input | SHA256 |
| --- | --- |
| `src/interoperability/ap2_hp_reference_plan_v1.py` | `4699f8aba9c8adfdc6c07ee8558b9ea356d64f1a80eb5d07f64e586f5aa0a8e0` |
| `scripts/ap2_hp_reference_client_v1.py` | `7258d93c0f8951f28178e2ee74d1c7ea16a052e7894bfcb003b0c12ae2904d96` |
| `tests/test_ap2_hp_reference_plan_v1.py` | `95f00096ec9e988bd1e856981b28d6ed006180ffd8654124bf794e894fd02afe` |
| `tests/test_ap2_hp_reference_cli_v1.py` | `6fe1ff26dcc5bbc94a316d991add8087ab61d0b5009652368d53ec95165e4ded` |

## Remaining native requirements

The complete AP2-specific dependency/build/runtime manifest, multi-service
owned bootstrap, prospective usage ledger and verified model allowance,
exact fixed resource-receipt binding and immediate bootstrap headroom check,
original-client delegation, listener/connected-peer ownership checks,
passive public/private observation recorder and closed capture validator are
not implemented by these files. The original server/client/signature/business
bytes remain unchanged. Keep the fixed 1 GiB physical/2 GiB commit gates and
task-owned shutdown rules from the native design.

Original router/credential failures and shopper challenge projection remain
native questions. No full task grade, CP2 contribution, qualified second
domain, held-out result, scientific novelty, 70% completion or supervisor
acceptance follows from either software suite. The recorded full-project
percentage remains 5% until its actual checkpoint gates pass.
