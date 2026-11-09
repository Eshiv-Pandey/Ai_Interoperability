# CP2 next action: acquire a qualified response contract

30 October 2026. Source assessment only. **No new method implementation is
justified by the inspected AP2 human-present dependencies.** They provide a
concrete second-domain qualification target and the missing inputs for a later
method decision. This note changes the next action from another speculative
cache or symbolic-copy implementation to acquiring the original task/response
contract at a precise decision boundary. No imports, tests, installations,
native workflows or provider requests were performed for this note.

The current method requirement remains active. Ordinary correlated state,
source summaries, guarded symbolic composition and runtime revalidation are
already granted to the strong comparator. The existing local-summary and
response-binding assessments are not superseded.

## Contract needed before a method trial

Use the original human-present scenario and its merchant/processor child
tasks. The outer shopper is an ADK agent; it does not acquire an original A2A
task merely because it invokes A2A tools. The prospective decision cutoff is
after the original merchant reports `input_required`, before its original OTP
continuation. Keep earlier public observations separate from later evaluation
evidence. At that boundary the independently reviewed contract needs:

| Input | Source-supported obligation and missing evidence |
| --- | --- |
| Public task association | Shopper `tools.py:277,296` saves and reuses the merchant task ID. Merchant `tools.py:452-469` chooses the first history message whose task ID differs from its own; it does not verify the message sender in that helper. Capture the original yielded messages, task/context IDs, history and endpoints to determine whether this heuristic identifies the actual processor task in the unchanged scenario. |
| Public challenge representation | Processor `tools.py:135-150` emits a challenge DataPart and requires input. Shopper `tools.py:278-280,309-311` checks a different `challenge` state/status field and otherwise returns generic status. Capture both the upstream public reply and the exact shopper-visible tool result. A hidden challenge must not become a candidate input. |
| Credential association | CP `account_manager.py:181-187,206-230` creates a token, binds an unbound token to a transaction and subsequently finds credentials through that transaction. CP `tools.py:139-154` verifies the currently supplied signed mandate, then performs that lookup. Record the original mandate/token preparation and its reset boundary; private state may support grading but must not silently become practical admission evidence. |
| Required mandate identity | Processor `tools.py:112-118,180-184` resumes the pending task using the currently supplied mandate. Its examined branch has no comparison with the mandate that originally produced the challenge. Distinguish signature validity and previously associated transaction from a scenario requirement to complete the original intended mandate. A changed valid mandate is a near-miss proposal, not a source-proven rejection. |
| Completion predicate | Processor `tools.py:203-222,254-272` creates a success receipt referencing the closed JWT of the supplied mandate; merchant `tools.py:302-318` forwards that artifact and state. Grade this actual synthetic payment contract and exact reference binding. Do not infer a real debit, require an absent real-money ledger, or weaken the scenario goal into an arbitrary signature/echo. Native artifact/state and independent task-validity evidence remain absent. |

The original provider/model selection remains part of native feasibility.
Source enumeration does not determine the model's chosen handler, execution
success, readiness or quota. The original credential-return handler exists;
its availability does not prove that the router selects it for a particular
request. Unobserved or ambiguous behavior remains unknown.

## Scientific decision after qualification

The positive source relationships are standard predicates over a correlated
frame: the two task/context associations, supplied mandate, bound transaction,
credential artifact and receipt reference. Copying them into an online residual
record adds no capability beyond the existing episode/controller. A symbolic
template before the initial call is standard guarded dataflow until it also
has a source-supported response relation, explicit existential/conditional
quantifiers and independently checked completion semantics.

Before implementing another candidate, name one operation that the strongest
same-evidence forward/backward symbolic composition cannot perform with its
ordinary goal pruning, parameterized summaries and cached/incremental checks.
Alternatively, propose a practical cost advantage and freeze its threshold
before measurement. Charge extraction, public acquisition, model/profile
construction, invalidation, solving, certificate generation and checking to
every arm. Grant the comparator the same legal routes, response relations,
assumptions, horizon and actual decision cutoff. An advantage over enumerating
concrete UUID literals is not a credible comparison.

Qualified native evidence can close domain/fidelity gaps and may expose a
discriminating requirement; it cannot by itself pass C1 novelty. The next CP2
contribution decision still needs an actual human review against the strong
comparator. No contribution-route change, human acceptance, scientific
advantage or checkpoint credit is recorded here.

## Inspected source bytes

Files below are retained under
`source-evidence/ap2-procurement-screen-v1/source/code/samples/python/src/roles/`.
These SHA256 values identify locally inspected bytes, not loaded runtime or
authenticated deployment identity. Original source pin is
`e1ea56db72a6385bce3e5c1112b3a56ce60acb43`.

| Relative file | SHA256 |
| --- | --- |
| `merchant_payment_processor_agent/tools.py` | `41a11923ae38798099c39a25d95d358ab1845320f64f8833b4955fa09b04e12d` |
| `merchant_agent/tools.py` | `513b7a6dd5d92ef2a0b355e77003706ffcec77ac662d42161fb638ef98f816d3` |
| `credentials_provider_agent/account_manager.py` | `39f80ac02cf60a69eb223ce54c2a66842ab869c1ce6fedf11aedeb7243f2fef8` |
| `credentials_provider_agent/tools.py` | `b369fa1c0990abc71866915d30a7b2843d6881cf23094abb7e031679e0d979bf` |
| `shopping_agent/tools.py` | `612525025661b608a662a8a09bc50ea527543b26c3bdbc78911bd95f6c3926a6` |
