# Final bounded native shopper source counterreview

11 November 2026. All reported actor-price findings are resolved in the reviewed
source. **Nineteen constructed controls pass**, and an independent compiled-source
check passes 16 reported refusal cases plus six supported acceptance cases.
The [earlier review](native-provider-appendix-v2-and-shopper-source-review-v1.md)
and its JSON remain unchanged. This is AI source/software review, not actual
native/model execution or human-gold qualification.

## Fixed actor boundary

The prospective product rendering must start with an actual `1.` or `1)` row
and use consecutive unique decimal ordinals. The actor checks only the first
supported product's visible amount against the USD 100 maximum. The known
zero-based, bullet, parenthesized and mixed-list cases stop rather than borrowing
a later product's price. A supported first USD 55.99 option is still selected
when a later numbered option costs USD 120.

Known foreign qualifiers including `C$`, Canadian dollars and spaced `MXN $`
are refused. Complete amount-token validation refuses the reported malformed
comma groupings and price ranges instead of accepting a smaller numeric part.
The USD 100 boundary is inclusive; USD 100.01 is refused.

Checkout requires exactly one separate line labeled `Grand total`, `Order
total`, `Total amount`, `Total due` or `Amount due`, followed by one unambiguous
USD/US$ amount within the maximum. Bare item prices, unqualified totals and the
reported unfinished tax/shipping cases stop the actor. An explicit USD 65.99
total with displayed USD 55.99 item and USD 10 shipping passes without inventing
a total from hidden state or arithmetic.

These are deliberately bounded public actor rules. Unsupported legitimate
renderings may stop the run and must be reported as owned actor limitations,
not original-application non-support. The original root, models, instructions,
tools and SDK remain unchanged; no app instruction was rewritten to force this
format. Public replies still exclude thought/function parts and session/tool
state. The all-response usage census retains unknown failed-response usage.

## Scope and source binding

The numeric appendix review remains unchanged: three raw ZIP/ledger censuses,
separate 5/5/1 denominators, V2's two observed public receipt cases and zero
repeat calls across all three runs. V3's HTTP 503 usage remains unknown.

Reviewed worker SHA256:
`f7c0e3d79582e9bfbc49123fe7fd16791c3651f9c58dab7b70a69658a548b765`.
The [final review JSON](native-provider-appendix-v2-and-shopper-source-review-v2.json)
binds the runner, worker, tests, protocol, workflow, original source references,
appendix and preserved prior review. No open findings remain in the reported
cases. Root owns the exact fresh freeze, bounded dispatch and subsequent raw
runtime/application validation.

```powershell
python -I -S -B -m unittest discover -s tests -p test_ap2_native_shopper_provider_v1.py -v
```

Source and constructed checks supply no full-study, unchanged `run.sh`, human
review, held-out, settlement, hidden-effect or scientific checkpoint credit.
