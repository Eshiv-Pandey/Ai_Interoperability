# Original native AP2 shopper V4: tool attempts and retained failures

Run [43074319113](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/43074319113)
at head `117daf284fe2758746369f0abe06e03870077c31` captures one adaptive
development case. Its 1,255,530-byte ZIP has SHA256
`b051d089a19b489fc758b96b714bd56f6718bf662e09ab6a17c846494511d908`,
matching the retained GitHub API digest. Both independent read reviews verify all
48 ZIP/extracted members. Workflow success and shopper exit code zero do not
qualify a successful purchase.

| Retained observation | Count |
| --- | ---: |
| Allocated cases | 1 |
| Raw ADK events / session events including initial user | 10 / 11 |
| Original business function-call attempts / terminal responses | 2 / 0 |
| Visible model replies / actual actor replies | 0 / 0 |
| Canonical public receipt records | 0 |
| Upstream allocations, including access smoke | 5 |
| Shopper generation allocations | 4 |
| HTTP 200 / upstream HTTP 503 | 4 / 1 |
| Cumulative request bytes | 23,802 |
| Known reported tokens / responses lacking usage | 4,081 / 1 |
| Owned proxy refusals after upstream failure | 2 |

The original root emits `transfer_to_agent` to `shopper`; its matching ADK
function response completes that control-flow transfer. The actual shopper
then emits two `find_products` calls with the same public catalog query and
different call IDs. Captured provider responses match all three ADK call IDs,
names, exact arguments, model versions and reported token totals. Neither
business call has a terminal `functionResponse` or a returned catalog Task.

Both attempts produce `A2AClientHTTPError` at original merchant agent-card
acquisition, with `owned_user_actor_external_network_denied`. Stack traces
reach the pinned original shopper `tools.py:55`, where `find_products` awaits
the original merchant client. The native watcher and each native service log
contain one preparation card GET and no business POST. This is an owned actor
guard failure during actual original tool execution, not an observed merchant
business refusal or an absence of a model function call.

The bound worker guard allows only string loopback host names and configured
native/proxy ports. The rejected socket/getaddrinfo arguments were not retained;
the exact host/port representation mismatch is unproven. Source diagnosis must
not present a guessed bytes-host or IPv6 cause as a measured fact.

A later upstream response is HTTP 503 `UNAVAILABLE`, reporting high demand and
no usage metadata. Two subsequent owned local refusals carry the prior-failure
message, followed by the original retry-layer exhaustion event. Proxy source
and remaining call/byte/token allowance support the prior-failure branch;
these refusals are not measured quota exhaustion. The 4,081 known-token sum
includes 45 smoke tokens; the failed response's usage remains unknown rather
than zero. There are six raw error events: two owned card-network denials,
one upstream 503, two owned prior-failure refusals and one final retry exhaustion.

The public conversation contains only the initial user request. The actor's
sole decision has a null reply and the SHA256 of empty visible text. The worker
stops as `public_actor_stopped_without_unambiguous_unseen_question`; the session
state is empty and no receipt is retained. Predetermined OTP/confirmation facts
were not submitted during this case. No complete payment, human semantic grade,
real settlement or hidden-effect claim is granted.

The exact V4 worker/public facts and all six owned-source snapshots bind to the
plan. Required 182 versions match 185 recorded distributions, while hosted venv
physical files are unavailable for independent post-run rehashing. Four recorded
children are reaped, with native start/finish PIDs matching cleanup records and
both recorded remote HTTP clients closed. No explicit official Runner-close
receipt or raw `/proc` socket-inode ownership snapshot is retained.

This is direct original ADK with native peers, an owned public-only user actor
and an owned provider accounting proxy. Original root/subagent tool and model
declarations are separately source-bound; complete capture/runtime authentication
and unchanged `run.sh` provisioning remain unqualified. The earlier V1 timeout,
V2 interpreter-preflight failure and V3 public-facts mismatch remain unchanged
in their separate one-case denominators. V4 is not merged into the scripted V2
two-receipt cohort or the registered held-out study.

The [independent raw review](../../runs/ap2-native-shopper-provider-development/v4/independent-raw-review-v2/review.json)
and [provider/runtime/lifecycle review](../../runs/ap2-native-shopper-provider-development/v4/provider-lifecycle-independent-review-v1.json)
contain identities and witnesses. Their standard-library sources execute no
original application, SDK or provider. Recheck retained shopper evidence into an
unused output directory:

```powershell
python -I -S -B scripts/review_ap2_native_shopper_provider_v4.py --retained runs/ap2-native-shopper-provider-development/v4/retained-43074319113-1 --provider-review runs/ap2-native-shopper-provider-development/v4/provider-lifecycle-independent-review-v1.json --output runs/ap2-native-shopper-provider-development/v4/your-unused-raw-review
```

The [additive paper note](../../paper/ap2-native-shopper-v4-development-addendum-v1.md)
binds the unchanged V15 manuscript and this result; it does not replace any
sealed manuscript or historical result.
