# Advertising-domain eligibility screen v2

Recorded 25 October 2026 (Asia/Calcutta). **Neither application is selected as
the required second continuation domain.** This is a primary-source screen,
not application execution, a bridge trial, a new C1 method, or human review.
The original method objective remains active; CP2 is open and credit remains 5%.

## Evidence preserved

Fifteen web query/result pairs preserve searches, successful excerpts, missing
paths and unsuccessful finds. They contain the exact JSON serialization of the
retained tool objects, **not original source bytes** or a complete checkout.
The nine records inherited at handoff were archived before further screening.
New retrievals include immutable Prebid commit URLs, application normalization,
the release lockfile and SDK route/helper sources. SDK tag-source retrievals are
version leads, not a separately verified Git or installed-package snapshot.

The separate [direct acquisition attempt](../advertising-screen-v2-20261024T192359210164Z-9868/screen.json)
retains both GitHub API requests that failed with WinError10061. Those failures
establish neither repository absence nor ineligibility. No unchanged download
was retried, source installed, proxy changed or runtime started. The local
prerequisite receipt shows Python3.13.1, no installed a2a-sdk/adcp/SQLAlchemy/
Flask distributions, a discoverable docker.exe and no discovered uv command.
The aggregate command exited1; Docker daemon/database readiness is untested.

Local receipts rechecked the unchanged bridge Git pins and clean tracked files.
Seven licensed local source snapshots preserve the inspected typed-input and
authentication boundaries. [manifest.json](manifest.json) binds these files,
all query/results, direct-failure receipts, this decision and the claim ledger.
Hashes establish local record integrity, not remote authenticity or runtime
conformance. A failed source find is never credited as proof of absence.

## Agentic Mobile: excluded from this modern binding screen

The primary [handlers](https://raw.githubusercontent.com/IABTechLab/agentic-mobile/main/server/src/a2a/handlers.ts)
and [card](https://raw.githubusercontent.com/IABTechLab/agentic-mobile/main/server/src/a2a/agent-card.ts)
implement a custom/legacy facade. The dispatcher accepts `message/send`,
`task/get`, `task/cancel` and `agent/card`; skill extraction requires a data
part's `type` tag. Task/context IDs occur in top-level parameters. The card's
application version does not certify an A2A1.0 binding. Pricing and inventory
operations are substantive, but the inspected facade does not establish the
unchanged modern profile required here. Main is unpinned. No runtime, universal
incompatibility claim or defect is asserted. An authored adapter to modernize
this facade would be a new intervention, not qualifying unchanged evidence.

## Prebid Sales Agent: substantive but presently unqualified

The former adcontextprotocol repository redirects to prebid/salesagent. Release
v2.0.0 resolves through its release commit link to
`17ebfb0841b0affc85f2796460503bda699e09b9`; its inspected pinned license is
Apache-2.0. These are web-source observations, not a verified local checkout.
[Release commit](https://github.com/prebid/salesagent/commit/17ebfb0841b0affc85f2796460503bda699e09b9).

| Requirement | Source observation and remaining gap |
| --- | --- |
| Modern binding | The pinned card constructor includes an interface URL and protocol version1.0 but omits explicit protocol binding. The app copies the card, changes the URL and calls the SDK's `agent_card_to_dict`. That helper merges compatibility fields. Actual serialized card and bridge selection remain unverified; omission alone is not a proven card defect. |
| Version handling | The pinned app uses the SDK route factory with `enable_v0_3_compat=True`. The SDK factory forwards this option to its dispatcher. Do not transplant strict JS-handler v2 missing-header rejection to this application. Specific raw requests remain unexecuted and their acceptance is unknown. |
| Substantive input | Explicit operations consume a protobuf data value containing a skill and input/legacy parameters. The natural-language create branch explicitly rejects that operation. Embedding JSON in a text part does not establish an equivalent structured transaction. Both inspected typed bridge surfaces accept text; mgcrea's permitted raw alternative remains a distinct action. |
| Authentication | Non-discovery skills require a Bearer token at the A2A boundary. Amir's reviewed configuration/client exposes no corresponding credential input; mgcrea's fetch wrapper supports a configured token. Native/bridge authorization must be identical. Bypassing the app's auth gate or adding a proxy would change the tested route. These are source/profile limits, not measured failures or a novel finding. |
| Same A2A task | Each inspected `on_message_send` allocates a fresh task ID and stores that new task. `on_get_task` reads the in-memory task dictionary. No native same-task continuation through this handler is established. Reusing a context or supplying an earlier task ID does not by itself establish continuation of the original task. |
| Business-object continuation | Update operations require media_buy_id, verify ownership and allowed actions, then call the adapter. This is a plausible substantive business workflow; it is not automatically the same-A2A-task contract. No replacement contract, native gold, reset procedure or horizon is selected. |
| Reproducible environment | Pinned pyproject fixes adcp5.7.0 and requires Python>=3.12. Its uv.lock resolves a2a-sdk1.0.1 and adcp5.7.0 but identifies the application as1.7.0 while pyproject says2.0.0. Frozen installation validity needs checking; no install was attempted and the lock was not repaired. Mock-adapter documentation is a setup lead, not verified credential-free application execution. |

These observations are supported by the pinned
[handler](https://raw.githubusercontent.com/prebid/salesagent/17ebfb0841b0affc85f2796460503bda699e09b9/src/a2a_server/adcp_a2a_server.py),
[app](https://raw.githubusercontent.com/prebid/salesagent/17ebfb0841b0affc85f2796460503bda699e09b9/src/app.py),
[update](https://raw.githubusercontent.com/prebid/salesagent/17ebfb0841b0affc85f2796460503bda699e09b9/src/core/tools/media_buy_update.py),
[pyproject](https://raw.githubusercontent.com/prebid/salesagent/17ebfb0841b0affc85f2796460503bda699e09b9/pyproject.toml)
and [lockfile](https://raw.githubusercontent.com/prebid/salesagent/17ebfb0841b0affc85f2796460503bda699e09b9/uv.lock).

## Method implication and next discriminating work

Create-media-buy has budget/product/creative checks and scoped idempotency,
including canonical wire-payload hashing, expiry and conflict handling. Its
source warns that an adapter-side orphan can remain after an idempotency race.
A database unique index therefore does not establish universal exactly-once
external effects. No race was executed, introduced or measured.
[Pinned create source](https://raw.githubusercontent.com/prebid/salesagent/17ebfb0841b0affc85f2796460503bda699e09b9/src/core/tools/media_buy_create.py).

Field/authorization guards reduce to the retained source/preimage baseline.
Adding business-object IDs or idempotency predicates does not supply an extra
C1 technical step. Any stronger recovery property must state its quantifiers,
observable evidence and effect boundary and face the corresponding exact,
symbolic and cached comparators on identical inputs/actions/horizon. No new
candidate advantage is asserted or performance trial justified by this screen.

A checkout-path question remains pending. If an exact local checkout becomes
available, first verify its commit, license, tracked state and original lock;
inspect actual SDK card normalization and the native continuation semantics.
Only a justified, unchanged, resettable contract with source-valid native
controls warrants a prospective trial. Do not run paid/production advertising
operations, silently weaken same-task requirements or count a business update
as a native continuation without independent validation. Lack of a checkout is
an acquisition gap; the source-level task/auth/input gaps remain even if it is
supplied. No human scientific review or contribution-route change is recorded.
