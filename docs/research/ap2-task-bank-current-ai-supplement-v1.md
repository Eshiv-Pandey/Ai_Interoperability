# AP2 candidate-bank current source crossreview supplement V1

11 November 2026. This AI source review checks the six candidates added after
the earlier 28-record AP2 crossreview and verifies the two reported recipe
clarifications in the current bank. It grants no human review, gold validation,
untouched holdout status or scientific checkpoint. The current receipt is
[`ap2-current-ai-supplement-v1.json`](../../runs/task-bank-review/ap2-current-ai-supplement-v1.json).

| Current candidate | Source check |
| --- | --- |
| `ap2-ho-019` | `create_checkout` reports the unavailable cart and returns before obtaining the signing key or publishing checkout artifacts. |
| `ap2-ho-020` | `initiate_payment` reports the missing payment mandate before optional checkout verification, risk checks and processor construction. |
| `ap2-ho-021` | With a nonempty payment mandate and no optional checkout mandate, the missing-risk guard returns before processor construction. This does not authenticate the supplied token. |
| `ap2-ho-022` | The separate DPC finish tool reports the missing checkout mandate before verification or its simulated success artifact. It is separately scoped from CARD OTP payment. |
| `ap2-ho-023` | `find_data_part` returns the first containing dictionary's exact value, including null or false; `find_data_parts` preserves all occurrences in order. |
| `ap2-ho-024` | The processor extracts nonempty text-bearing parts in order; a noncompleted task raises a diagnostic `ValueError`. Empty text and ordinary DataParts contribute no text. |

These obligations use different input guards, a separate DPC route, typed lookup
behavior and ordered remote diagnostics. The six recipes explicitly identify
source-boundary controls and distinguish them from a full native shopper
trajectory. Their `held_out` labels remain prospective allocation labels, not
independence claims. No source-semantic blocker was found in this reviewed delta.

Current `ap2-dev-001`, `ap2-cal-003`, `ap2-ho-001`, `ap2-ho-004` and
`ap2-ho-018` recipes contain `PAYMENT_METHOD=CARD`, `debug_mode=False` and
ordinary nonverbose turns. The earlier review documents the competing original
debug instruction as a source limitation. The evaluator separates nonempty artifact-list checks
from actual credential contents and selected-transaction association.

The historical 28-record review does not bind the current edited files. This
supplement binds current bytes for its six-record semantic delta and targeted
fix checks; the fresh structural validator independently checks all 34 current
public/evaluator pairs, source hashes and citation ranges. Neither check replaces
a fresh exhaustive human semantic review. No original application or SDK was
imported or executed, and no provider call or bank mutation was performed.
