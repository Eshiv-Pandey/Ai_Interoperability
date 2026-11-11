# Additive original native AP2 shopper V4 development observation

This note is additive to the frozen V15 manuscript and preserves its numerical
sections, original-study qualifications and earlier denominators. It reports one
separately allocated adaptive development case from run `43074319113` at head
`117daf284fe2758746369f0abe06e03870077c31`.

The actual original root/ADK emits ten events, including a completed transfer
to the shopper and two original `find_products` attempts. Neither business
attempt returns a terminal function response: both fail during merchant native
agent-card lookup at the owned actor socket guard. A later actual provider
response is HTTP 503 high demand, followed by two owned prior-failure refusals
and retry exhaustion. Exact rejected socket arguments were not captured.

All five upstream allocations remain counted, including one access smoke:
four HTTP 200, one HTTP 503, 23,802 request bytes, 4,081 known reported tokens
and one response lacking usage. Failed-response usage is unknown rather than
zero. Four recorded children are reaped and both recorded remote clients close;
full runtime authentication, Runner-close and socket-inode witnesses are absent.

The public conversation has only the initial user request; there is no visible
model reply, actor reply, returned catalog Task, payment completion or receipt.
Shopper exit zero reflects the owned actor's honest stop, not purchase success.
This profile adds actual original tool-attempt failure evidence, with no human
gold, untouched holdout, settlement or general method-advantage qualification.

The earlier V1 timeout, V2 interpreter-preflight failure and V3 public-facts
mismatch remain unchanged. The V4 result is separate from scripted native AP2
V2's two completed public receipt cases and the original registered full study.

See [the complete V4 result guide](../docs/research/ap2-native-shopper-provider-development-results-v4.md)
and [the independent raw review](../runs/ap2-native-shopper-provider-development/v4/independent-raw-review-v2/review.json).
The [provenance](ap2-native-shopper-v4-development-addendum-v1.provenance.json)
binds this note, frozen V15, raw archive, current read reviews and source.
