# Original AP2 native/provider public observations V2

Prepared 2026-11-11. All five fixed V2 development cases remain in the
denominator. The retained public responses contain two completed Tasks with
one Success receipt each, one wrong-reply refusal, one waiting Task without an
OTP submission, and one partial payment attempt stopped by the owned accounting
boundary before the repeat prerequisite completed. **No repeated OTP response
was captured in V2.** These are observed sample behaviors, not human gold or
whole-task semantic grades.

## Retained allocation and analysis binding

| Item | Binding |
| --- | --- |
| Hosted run | `42995902326` |
| Frozen head | `5f8ef7c8948c0a4a89b665810968cc4d5a734cda` |
| Root retention | `runs/ap2-original-native-provider-development/v2/retained-42995902326-1` |
| API/archive SHA256 | `5aa54a06193b25416e6d952fdee9be2af1760fd60fed596107906c5864bb2bf3` |
| Archive bytes / extracted files | 1,945,795 / 217 |
| Semantic output | `runs/ap2-original-native-provider-development/v2/independent-semantic-analysis-v1/analysis.json` |
| Semantic output SHA256 | `a1889821ce11848ca5e0e4cc9c2def1048a5bd050c21e5cbdb3903e648c8169a` |
| Analyzer source SHA256 | `8901795494755665cd46ad278e15cd83e0da26cd7c1937b22894bbb06aaa61f9` |
| Analyzer control source SHA256 | `8df1c4ddefb4e482c2466089a7db68896b86fbfc9950cca12b4d35d3d23cd608` |

The semantic analyzer checks the root-retained run/head/archive binding and the
manifest digest of each inspected capture. It reconciles all five caller result
objects with raw original-call terminal rows, actor event rows and public-read
terminal rows. Its retained status is `retained_public_observations_consistent`,
with **zero consistency questions**. It imports only the Python standard library
and makes no application, SDK, model or provider call. Root's separate raw review
owns archive, native-process, runtime and provider-ledger reconciliation.

Seven new constructed semantic controls passed. They cover all five case
shapes, a forbidden OTP call without a reply, altered recovery authority,
different repeated receipt observations, retention of a prior receipt after a
later failure, mismatch between result and raw read, and a zero-response branch.
The five case shapes are subcases of one control. The controls use constructed
actor events and retained earlier public Task fixtures, and are not additional
V2 scientific observations. One older wrong-reply fixture uses a different
wrong string; the control explicitly preserves the difference between an exact
actor reply event and corroboration in retained Task messages.

## All five fixed cases

All five parent rows say `executed_returned` and have caller exit code zero.
The caller retains failed/partial semantic outcomes in its result rather than
expressing every such outcome as a process failure.

| Fixed case | Exact prospective OTP fact | Original call terminals / returns | Final public state | Observation |
| --- | --- | --- | --- | --- |
| `correct-reply` | `123` | 11 / 11 | `completed` | One Success receipt |
| `wrong-reply` | `wrong-human-reply` | 11 / 11 | `input-required` | `Challenge response incorrect.`; no receipt |
| `no-reply` | `null` | 10 / 10 | `input-required` | Same public OTP challenge; no OTP continuation call or receipt |
| `foreign-context-recovery` | `123` | 13 / 12 | `completed` | One adverse original RPC error, owned read refusal, recovery, then one Success receipt |
| `repeat-completed` | `123` | 11 / 11 | `failed` | Owned budget stop during prerequisite payment; no repeat call/read or receipt |

This is **2/5 cases with an observed completed public receipt**, a descriptive
capture count. It is not a project completion percentage, pass rate for human
gold, or qualification of the held-out study. There are five actor results,
56 original-call terminal captures, 55 original-call public returns and 11
public-read observations, including the refused foreign-context read.

## Offers, display fields and exact replies

Every cart selection matches index zero of the original catalog tool's actual
returned offers. Every payment selection matches index zero of the original
payment-method tool's returned aliases: `American Express ending in 4444`.
Wallet consent, cart confirmation, selected offer, shipping display and payment
alias match the prospectively fixed facts and returned public objects. The
selected cart ID is `cart_1` within each fresh case; this is not a cross-case
authority identifier.

| Case | Actual selected item label | Selected amount / checkout amount cents |
| --- | --- | --- |
| Correct reply | Lightweight mesh walking shoes | USD 45.99 / 4599 |
| Wrong reply | Lightweight mesh breathable walking sneakers | USD 55.99 / 5599 |
| No reply | Lightweight breathable mesh walking shoes | USD 55.99 / 5599 |
| Foreign-context recovery | Lightweight breathable mesh walking shoes | USD 59.99 / 5999 |
| Repeat case | Lightweight mesh walking sneakers | USD 55.99 / 5599 |

Each returned checkout matches its selected offer's ID, label, amount and
currency. Its `checkout_hash` matches the SHA256 base64url digest of the returned
checkout JWT. This establishes consistency of captured fields; it does not
grade product relevance or independently verify cryptographic signatures.

All initial Tasks contain one public `input-required` OTP challenge with its
actual display text. The caller's OTP-request event uses that challenge and the
outer merchant Task ID/context. The exact `123` or `wrong-human-reply` fact is
present both in the corresponding actor event and in the retained final Task
messages. The no-reply event contains `null`, and there is no original
`payment-otp`, adverse OTP or repeated OTP call in that case. Its final public
challenge remains the same and no receipt is present. These observations do
not establish exact A2A wire attribution.

## Task authority, recovery and receipts

Successful public reads use the returned outer Task ID with
`historyLength=100`, and their Task contexts match the caller-held contexts
captured at read start. Final Tasks retain the initial Task ID/context. A
forwarded status message's processor `taskId` can differ from the outer
merchant Task ID; the analyzer preserves that distinction.

The recovery case records another original catalog call and the distinct
context `27246a09-8a8b-4db0-8800-9625e24912e7`. Its adverse original OTP call
returns the actual JSON-RPC error `-32602`, `bad context id`. The subsequent
public read returns the original merchant Task but the owned read tool refuses
it because the caller holds the foreign context. This is an **owned context
check on an actual returned public Task**, separately from the original
server's RPC error. It does not establish an original merchant task-not-found
result.

Only after that refused read does the caller recover merchant Task
`6c3e3acd-84ab-43d2-9852-f086d6e86453` and context
`29ff03b2-7f51-47f0-ae32-2bdb1dedf79a`, exactly the pair from its earlier public
Task. The subsequent original OTP call and public read produce one Success
receipt.

Both completed Tasks have exactly one artifact `ap2.PaymentReceipt`. Each
receipt preserves its original `status`, `iss`, `iat`, `reference`, `payment_id`,
`psp_confirmation_id` and `network_confirmation_id` fields. Both statuses are
`Success`, both issuers are the sample's empty string, both timestamps are
integers, and each receipt's three confirmation identifiers agree. Each
reference matches the SHA256 base64url hash of the closed payment JWT extracted
from that case's prior original payment-mandate return. No private journal or
evaluator answer is used. The receipts are sample public artifacts, not proof
of real-world settlement.

## Repeat-case accounting stop

The retained closing provider summary reports 60 upstream allocations, all
HTTP 200, 197,564 cumulative request bytes and 44,940 reported usage tokens.
These are global counts, including the parent smoke; they are not assigned to
individual semantic cases by this analyzer. The fixed limits remain 80 calls,
200,000 cumulative request bytes and a 100,000 observed-token stopping
threshold. The token threshold is checked after responses, and is not a hard
token or cost ceiling.

One owned local refusal occurs at `2026-11-11T09:38:55.010184+00:00` within the
repeat case's recorded window. Its public final Task is `failed` and contains
the propagated `owned_provider_budget_or_prior_failure` 429 message. The
closing proxy has `failed=false`; the call and token limits still have room.
The cumulative byte branch is therefore inferred from the bound proxy
implementation and exclusion of the other stopping branches. The refused
request payload and its byte count were not retained, so this is not a measured
claim about the size of that request. The captured evidence establishes an
**owned accounting-boundary stop propagated through an original failed public
Task**, rather than a live upstream provider/model failure.

The prerequisite `payment-otp` call returns `Status: TaskState.failed`; there is
no receipt. The caller then retains the local error `Duplicate continuation
requires an actual completed public receipt first.` No `repeat-original-otp`
call, repeated public read or repeat event exists. V2 consequently supplies no
observation of repeated continuation, idempotency, durability or duplicate
hidden effects. A later separately allocated repeat control cannot change this
V2 outcome or denominator.

## Treatment and limits

V2 uses the owned structural source binder, scripted caller and public SDK
read surface with original business functions and the prepared original native
services. The parent accounting proxy and explicit prospective human-choice
facts remain interventions. Source/control details are in
`ap2-public-original-binding-v2.md`; allocation rules are in
`ap2-original-native-provider-protocol-v2.md`. V1 sources and its failed retained
allocation remain unchanged.

No unchanged original `run.sh` provisioning, autonomous ADK shopper/root tool
surface, independent bridge, human gold, untouched holdout, whole-task grade,
full-study result or scientific checkpoint qualification is granted here.
Consistency of retained public captures also does not independently authenticate
provider or service provenance. Raw/native/provider review and semantic public
observations remain distinct evidence.
