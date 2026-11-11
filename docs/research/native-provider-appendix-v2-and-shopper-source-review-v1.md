# Native/provider appendix and original shopper source counterreview

11 November 2026. The canonical appendix matches the retained raw ZIPs and
provider ledgers. The new original-shopper runner has one remaining public
actor policy issue: its first-option selection can exceed its declared budget.
This AI source review grants no application, human-gold or full-study credit.

## Appendix checked against raw captures

All three complete archives and each retained provider request/response payload
were read directly, without executing the builder, apps, SDK or provider.
The canonical provenance numbers reproduce:

| Allocation | Parent attempts | Upstream calls | HTTP 200 / 503 | Request bytes | Known reported tokens | Missing usage | Owned refusals | ZIP members |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| V1 | 5 | 1 | 1 / 0 | 356 | 45 | 0 | 0 | 27 |
| V2 | 5 | 60 | 60 / 0 | 197,564 | 44,940 | 0 | 1 | 217 |
| V3 | 1 | 3 | 2 / 1 | 6,327 | 839 | 1 | 0 | 34 |

Raw actor captures establish two completed public receipt cases in V2 and none
in V1/V3. No allocation contains a repeat call. The three denominators remain
5, 5 and 1. The appendix correctly retains V3's missing 503 usage as unknown,
distinguishes V2's owned refusal from an upstream quota observation, and makes
no full-study, human-gold, idempotence or pooled-efficacy claim.

## Shopper source and controls

The pinned ADK source confirms that `StreamingMode.NONE` calls the original
asynchronous `generate_content`, compatible with the inherited proxy's ordinary
`generateContent` path. The new worker imports the original root, subagents,
tools and instructions; no GenAI Client or BaseLlm is replaced. Original sources
are copied byte for byte into fresh private roots so original SDK log paths
stay isolated. Parent provider accounting, deadlines and native process cleanup
remain explicit.

The public actor uses visible final-response text, excluding thought and
function parts. Session snapshots are retained for analysis and do not select
replies. Eleven constructed controls pass independently. They establish owned
software behavior, not an executed original ADK/provider application.

Two findings were fixed during review: the price regex now handles real Unicode
currency displays, and a separate hash-bound all-response census preserves
successful/failed missing usage plus unclosed allocations. The historical
provider helper remains unchanged; its original unknown counter is explicitly
restricted to HTTP 200 responses.

## Remaining revision

At `scripts/ap2_native_shopper_provider_worker_v1.py:86`, the actor always
selects the first displayed cart once it recognizes a choice question. Its new
`maximum_budget_USD=100` fact is never checked. This owned-only reproduction
returns a cart-selection approval for:

```text
1. **Walking shoes**, $120; Cart ID: cart_1. Which item would you like to purchase?
```

The reply is `I choose the first product option you displayed.` That contradicts
the frozen budget and can weaken the declared correct-human treatment. Check
the first displayed option's price/currency from public text, refuse an
overbudget or ambiguous/unsupported-currency option, and add constructed
allowed/overbudget/ambiguous controls. Do not obtain the price from hidden
tool/session state or invent exchange rates.

The accompanying [review JSON](native-provider-appendix-v2-and-shopper-source-review-v1.json)
binds the exact source/output hashes, reproduction and limits. Root owns the
correction, fresh freeze and any later dispatch. This review does not establish
actual native/model behavior or original `run.sh` provisioning.
