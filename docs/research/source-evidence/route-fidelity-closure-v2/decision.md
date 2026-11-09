# Direct-origin push callback closure v2

25 October 2026. **One callback-family obligation is discharged at source level
under the frozen origin profile. No full-interface certificate or C1 advantage
is established.** This is separately authored AI source analysis, not human
review. No new application, network or performance trial ran.

## Scope and result

The earlier [coverage ledger](../origin-surface-closure-v1/coverage-ledger.json)
left callback/SDK dispatch open. This package follows mgcrea's permitted push
configuration tools through its actual built bridge, installed A2A SDK 1.3.0
client, and the **actual installed SDK 1.1.0 used by the strict origin** in the
retained B4 control. It establishes this conditional source predicate:

> While the original origin retains its frozen pushNotifications=false card,
> SDK 1.1.0 DefaultRequestHandler and unchanged configuration, push configuration
> actions cannot create a callback sender/configuration or cause a callback
> completion of that origin task. This remains true for arbitrary legal config
> IDs, callback URLs, tokens, task IDs and JSON parameters reaching these paths.

There is also a concrete projection distinction: typed **create** fails at the
SDK client capability guard before its configuration RPC; typed **delete** has
no such client guard and can send its RPC before the server refuses it. A model
that collapses both to the same zero-remote-call failure loses observable
request cost. Either tool call still consumes its declared caller action; this
does not change the original finite-model horizon into a network-call bound.

## Source argument

1. `scripts/capture-official-handler-bridge-v2.mjs:110-124` constructs the
   singleton 1.0-only card with pushNotifications=false and creates
   DefaultRequestHandler(card, new InMemoryTaskStore(), executor), with no
   supplied push store/sender. It mounts the official Express JSONRPC handler
   without legacy compatibility. The retained B4 report records that exact card.
2. `external/mcp-a2a/src/tools/writes.ts:197-276` exposes typed create/delete
   configuration tools, then calls PeerClient. `src/client/peer.ts:218-249`
   supplies their explicit typed parameters. The maintained source and built
   `dist/server-Dd272e4l.js:528-547,1051-1097` agree on this dispatch. Exact source
   contents are embedded in the inspected source map; that check is provenance,
   not a general verified-compiler theorem.
3. SDK 1.3.0 `dist/client/index.js:5514-5553` checks capability before create,
   get and list, but delete goes directly to executeWithInterceptors.
   Factory `6511-6536` returns this Client for the selected interface.
   Header normalization `5657-5661`, JSONRPC delete `5908-5914`, and request
   serialization `5970-5978,6012-6025` carry typed delete through the normal
   version-bearing transport. These are internal SDK options; the MCP caller
   does not gain arbitrary header control.
4. In the **origin's SDK 1.1.0** `dist/server/index.js:2513-2524`, a false card
   leaves both pushNotificationStore and pushNotificationSender unset. Each of
   create/get/list/delete at `3037-3093` throws PushNotificationNotSupportedError
   on the false capability before task-store loading or a configuration write.
   Therefore even a request reaching this dispatcher cannot manufacture a
   push config using its task/config/URL/token inputs.
5. Raw config methods do not evade those guards. The public raw enum includes
   their names (`src/tools/request.ts:11-23`), but rawRpc (`src/client/peer.ts:261-280`)
   supplies content type without a version header. The bridge fetch wrapper
   only adds configured bearer/User-Agent headers (`src/client/fetch.ts:40-57`).
   The fixed official Express path validates version before method dispatch
   (`dist/server/express/index.js:3359-3371`), so the direct raw config family is
   rejected earlier under this frozen profile. Even a hypothetical correctly
   versioned config request still encounters the server capability guard above.
6. Inline SendMessage configuration is a separate route and must be included:
   SDK 1.1.0 `dist/server/index.js:2856-2862,2924-2930` saves inline configs only
   when pushNotifications is true. `_sendPushNotificationIfNeeded:3174-3181`
   likewise requires both the true capability and a sender. Thus enabling a
   callback is unavailable even if execution publishes further task events.
   This says nothing new about whether a reference-bearing SendMessage can
   directly complete the executor; the earlier application/version guards and
   native control remain unchanged.

Under these premises, induction over any finite sequence of the scoped direct
configuration actions preserves the absence of an origin push store/sender.
The notification-dispatch condition stays false. These actions neither call
the executor's completion branch nor install later origin callback work.
This is standard guarded source reasoning, not a new theorem, mechanically
checked complete-negative proof, or measured result.

## Provenance and limits

[source-index.json](source-index.json) preserves exact selected source, built
bridge and installed SDK files, including MIT/Apache-2.0 licenses. The capture
script compares the selected current bytes with the retained B4 source/runtime
receipts and the available corresponding archive files. The original report
itself must match the group record's SHA-256. This closes a **selected slice**
of the current-to-archived-byte obligation; it does not certify every runtime
dependency, the whole compiler, or an arbitrary future process environment.

The first SDK read used Amir's installed 1.1.0 copy. Before relying on it, an
explicit byte comparison checked that its server module, Express module,
package and license equal the actual `external/sdk-http-control-v1` installation
used by the origin. The sealed package uses that actual origin path.

Initial exploratory output was truncated, and one guessed path
`scripts/official-handler-bridge-probe-v2.mjs` did not exist. The actual retained
driver was located as `scripts/capture-official-handler-bridge-v2.mjs`. No
absence or semantic claim uses the missing filename. The original broad-read
tool outputs were not saved as binary process receipts; this paragraph records
their visible limitations. Three later targeted tool responses are retained as
JSON serializations, including their tool metadata. Exact copied files support
the argument independently of console truncation.

The proof does **not** close all callbacks in an open environment. Another
permitted peer, a forwarding proxy, changed card/cache, process reconfiguration,
intervening code/environment mutation, or another callback source could have
different behavior. Those alternatives remain in C1/C2/C4 of the prior ledger.
The receiving peer's local mirror and daemon are also distinct from the
authoritative original origin. No current full-interface unsupported decision
or complete-negative certificate is justified. No novelty, qualified second
domain, human review, or additional checkpoint credit follows; credit stays 5%.

## Discriminating verification still available

[prospective-check.json](prospective-check.json) specifies a narrowly justified
future source-to-wire control: after one public pending prefix and warm peer
discovery, typed create should emit zero config RPCs; typed delete should emit
one version-bearing RPC; raw create/delete should encounter version rejection.
Private original-task/event counters and passive callback-receiver logs must
show no completion or callback. The check must preserve all failures and use a
new attempt path without changing the original card, handler, bridge or traces.
It has not been implemented or executed here. Its purpose is the new dispatch/
cost distinction; repeating the favorable native completion controls is not
needed to establish this source argument.
