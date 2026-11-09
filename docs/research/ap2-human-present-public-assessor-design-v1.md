# AP2 human-present public assessor design, 30 October 2026

Implement a standard-library, observer-only public consistency assessor for the
original HP merchant/processor OTP path. This advances the second-domain grader
without importing the application, calling Gemini or claiming that a native
purchase, qualified domain or full task has passed. The
[source reassessment](ap2-human-present-source-reassessment-v1.md) supplies the
original hierarchy and source limitations.

## Inputs and outputs

The proposed API is
`assess_public_payment(initial_message, merchant_pending, resume_message,
merchant_after, *, processor_pending=None, processor_resume_message=None,
processor_after=None)`. Inputs are separately supplied public JSON objects:
initial merchant payment Message, pending merchant Task, merchant follow-up
Message and subsequent merchant Task; the processor observations are optional.
The initial Message is used only for observed mandate-change reporting and
initial absence-of-task binding; it is not proof of a completed shopper prefix.
Use original A2A 0.3 field names (`id`, `contextId`, `taskId`, `kind`, `status`,
`message`, `artifacts`, `parts`, `data`). Do not translate a JSON-RPC request ID,
session metadata or caller path label into task/context identity. Missing
observations make the relevant lane unknown. Invalid supplied shapes may be
rejected or reported failed with a precise reason; never silently discard them.

Return a report with named checks carrying `passed`, `failed` or `unknown`,
precise evidence locations/reasons and observed branch information. No aggregate
full-task, native, domain or scientific success field may become true. Always
state that source authentication, capture ordering/completeness, original stage
mapping, credential association, signature/authority/expiry/amount checks,
reset, effect commitment, user consent and semantic adequacy remain unassessed.
Supplied object labels are candidate stages, not proof of original stage order.

## Separate public obligations

| Lane | Concrete observation/obligation | Source support |
| --- | --- | --- |
| Pending suspension | Each supplied pending Task has input_required state, nonempty task/context identity and a challenge-bearing processor status Message | Processor tools 108-151; merchant tools 315-318 |
| Merchant continuity | Merchant follow-up actual message.taskId/contextId equal the pending merchant id/contextId; subsequent Task preserves both | Shopper tools 293-307; BaseServerExecutor 98-114 |
| Processor continuity | Processor follow-up actual message.taskId/contextId equal pending processor id/contextId; subsequent Task preserves both | Merchant tools 277-300; processor tools 108-120 |
| Child challenge propagation | Merchant pending status Message preserves processor pending challenge message identity and data; do not require its message.taskId to equal the merchant task ID | Merchant tools 315-318; SDK TaskUpdater 65-108 |
| OTP forwarding | Uniquely extract challenge_response from each follow-up's DataParts and compare exact typed values; missing/ambiguous/different values are explicit | Merchant tools 290-294; shopper tools 298-301 |
| Supplied mandate forwarding | Uniquely extract `ap2.mandates.PaymentMandateSdJwt` from both follow-up Messages and compare exact strings | Processor tools 59-82; merchant tools 277-288 |
| Incorrect OTP target | If processor follow-up response is a string other than `123`, observed subsequent input_required state with no Success receipt satisfies the documented retry target; missing subsequent observation is unknown | Processor tools 154-171, 225-227 |
| Correct OTP target | Literal `123` selects the completion branch; completed is the requested continuation target. Failed or still-pending outcomes leave that target unmet, while correct OTP alone cannot establish completion because signature, credential routing and delivery can fail | Processor tools 162-222, 230-251 |
| Receipt extraction/shape | Extract the canonical `ap2.PaymentReceipt` object only from actual DataParts. Keep malformed parts explicit. Exactly one supplied final receipt is required for an unambiguous receipt lane | Processor tools 212-218; merchant tools 302-313; SDK generated receipt |
| Final receipt propagation | Schema-valid processor and merchant receipts have the same complete JSON value; preserve empty issuer and explicit null fields | Merchant tools 302-313 |
| Supplied receipt reference | Receipt.reference equals source-compatible hash of the exact processor follow-up supplied closed JWT leaf, not decoded/re-serialized payload JSON | Processor tools 254-273; SDK mandate 402-417 and utils 21-36 |
| Original constructor shape | A Success receipt has its source constructor's three confirmation identifiers equal to one nonempty UUID hex string. Keep this separate from schema admissibility | Processor tools 258-273 |

A wrong-OTP retry that remains pending is not successful purchase completion.
A correct-OTP task that fails is a retained unmet completion target, not a reason
to invent credentials or a favorable receipt. A success receipt visible while
the processor remains input_required conflicts with the documented retry target.
Missing receipt or outcome evidence cannot produce a receipt pass.

## Exact reference and schema semantics

The source algorithm is:

```python
leaf = presentation_token.rsplit('~~', 1)[-1].split('~', 1)[0]
reference = base64.urlsafe_b64encode(
    hashlib.sha256(leaf.encode('utf-8')).digest()
).rstrip(b'=').decode('ascii')
```

This matches extraction/hash semantics only. It does not authenticate the
presentation, decide whether a chain is valid or prove the leaf belongs to the
pending transaction. Malformed or empty presentations cannot be promoted to
validated mandates because a hash can be computed for them. Record whether the
optional initiating merchant mandate differs from the follow-up; changes to
delegation/disclosures can leave the closed-leaf reference unchanged. Distinguish
whole-presentation equality from closed-leaf equality.

The generated PaymentReceipt is a RootModel of Success/Error models. Success
requires string fields status=`Success`, iss, reference, payment_id,
psp_confirmation_id and network_confirmation_id, plus integer iat. Error requires
status=`Error`, iss, reference, payment_id, error, error_description and integer
iat; its confirmation fields may be omitted or null. Success error fields may be
omitted or null, and the generated type also permits strings there despite the
descriptive text. The source can create `iss=""` when pisp is absent. Extra fields
are not forbidden by the generated default BaseModel. Do not advertise exact SDK
validation equivalence from a stricter JSON observer: preserve extra fields and
compare full supplied JSON for propagation, document strict JSON type checks and
separate source-constructor obligations. Boolean iat is not an integer JSON
obligation for the observer. No signature trust follows from schema validity.

## Near misses required for useful implementation checks

These are authored software fixtures, not upstream outcomes or held-out tasks:

- Wrong merchant/processor task or context; RPC ID changes while actual task ID
  stays wrong; child status Message task ID preserved versus rewritten as parent.
- Wrong or absent OTP, conflicting duplicate OTP DataParts and correct OTP with
  a failed credential task outcome. Preserve input_required retry and failed
  completion as distinct observations.
- Missing/malformed canonical receipt, conflicting receipts, swapped propagated
  receipt, bool iat, wrong reference, null optional fields, empty issuer and
  supported extra fields. A repeated observation in a different supplied snapshot
  does not add another independent receipt.
- A distinct valid-looking supplied mandate on the pending task. Report observed
  mandate change and receipt reference to that supplied leaf; leave original-task
  transaction association unknown. **Do not assume upstream rejects the changed
  mandate.** This cannot earn a native or credential-association pass.
- Same closed JWT with different presentation disclosures/delegation prefix: leaf
  reference agrees while full presentation differs. A payload-JSON hash or padded
  base64 reference must not satisfy the exact source-reference lane.
- Incomplete pending/follow-up/final observations: only supported lanes can pass,
  all missing causal/history/source-authentication evidence stays unknown.

## Source byte identity

The sample tool hashes are recorded in the source reassessment and matched the
retained acquisition. Additional retained SDK source SHA256 values read on
30 October:

| Source relative to retained `code/sdk/python/ap2/sdk/` | SHA256 |
| --- | --- |
| `mandate.py` | `6251ec83622192805cd3cd8a4830f9ab922260c3089d4ff9323b9eb2ec27b1f5` |
| `utils.py` | `92920007d190f68cad6b9899f0133ae511332196f59e3255d68be08dbc1e2a2f` |
| `generated/payment_receipt.py` | `78db7cd258eedd66a1f4e891e1b704df7cff78183249de94e4e77b2df3bb8aae` |

This design authorizes no original application mutation or relaxed resource
gate. Its implementation should remain separate from original-metric AgentOps
grading and from any full native HP scenario grade.
