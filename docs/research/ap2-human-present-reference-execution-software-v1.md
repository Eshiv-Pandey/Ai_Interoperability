# AP2 injected reference execution and passive public capture v1

30 October 2026. This adds executable reference coordination and passive ASGI
observation around supplied bindings. It is implementation for the supervisor
demonstration, not a paper draft or a completed native AP2 purchase.

## Implemented software

- [Reference execution](../../src/interoperability/ap2_hp_reference_execution_v1.py)
  runs the full public prelude through injected tool functions and validates each
  observed phase with the unchanged [pure planner](../../src/interoperability/ap2_hp_reference_plan_v1.py).
- [Passive capture](../../src/interoperability/ap2_hp_passive_capture_v1.py)
  wraps an injected final ASGI application without importing an application,
  SDK, model provider, credential helper or evaluator store.
- [New constructed tests](../../tests/test_ap2_hp_reference_execution_v1.py) and
  [once-only capture driver](../../scripts/capture_ap2_hp_reference_execution_tests_v1.py)
  are separate from every consumed planner, CLI, assessor and native-gate suite.

`ReferenceBindings` supplies original tool function objects, the original
builder factory, observed original merchant/credentials clients and the original
public-artifact receipt extraction helper. The binding adapter must arrange
that caller tool globals use these observers; the coordinator verifies each
tool's captured public call count/role. This file does not implement or
authenticate that adapter. The disclosed context has only `.state` and is not
an ADK ToolContext or the original ADK-web shopper.

The coordinator selects only returned carts and aliases, checks public-return
and caller-state consistency, and obtains explicit approval of the actual typed
checkout/address/payment summary before invoking either signer. Shipping state
remains reference approval state because the original shipping tool returns an
address without storing it. Actual signer outputs are retained unchanged.

The credentials association helper's actual returned Task is retained even
though the original helper returns a success string and discards that Task.
A noncompleted public association stops this reference before payment. This is
a stricter reference-caller decision, not a repair to the original helper.

Payment start/resume call the injected original builder/client directly. They
preserve original text, DataPart order, falsey omission, optional checkout
mandate placement and builder-owned UUID generation. Continuation uses only
the public merchant `input_required` Task's OTP DataPart and the same observed
merchant task/context. An empty response stays empty and is omitted by the
builder; other responses are not corrected to the demo value. The original
shopper's separate `status.challenge` defect is not silently repaired.

`PublicClientObserver` returns the identical original Task/Card object and
keeps that object separately from detached finite plain-JSON observations.
Opaque values and nonstring object keys cannot become observations. A shared
coordinator stream records global callback sequence plus original endpoint-local
sequence. This is observer-boundary ordering, not socket timing or complete
causal order. Observation failure leaves delegated behavior intact and stops
the coordinator before a dependent phase. Original exceptions remain retained.

The original client owns its HTTP extension behavior. `X-A2A-Extensions` must
carry `https://github.com/google-agentic-commerce/ap2/v1`; message metadata is
not a replacement. Original initial card discovery may precede setting that
header. These high-level callbacks do not prove actual headers or peer ownership.

## Passive capture and ownership

The ASGI wrapper forwards the identical original scope and receive/send events,
preserving chunks, byte order, header order/repetition, return values and raised
exception identity. Bytes use base64, byte length and SHA256; tuples are tagged.
Only public HTTP scope fields are selected. Application/router objects and
merchant/credentials/task-store inner state are not consulted. Attempted and
completed send boundaries remain distinct. Recording failure is fail-open for
the application and makes the wrapper's observation-completeness flag false.
In-memory records alone are not a durable or authenticated native capture.

`run_owned_reference` keeps the injected returned group through readiness,
coordinator construction, reference execution, publication and cleanup. It
always attempts only that group's `stop()`. If cleanup is incomplete or throws,
the returned outcome retains the same authority object and reports
`cleanup_incomplete_authority_retained`. No owner is inferred from a port or
unrelated process. No native group or binding factory is implemented here.

## Retained constructed validation

Root's bounded source review closed before the single new capture, including
recursive typed equality, strict public JSON keys and a shared ordered callback
stream. The [retained result](../../runs/ap2-hp-reference-software/reference-execution-v1/result.json)
completed at 2026-10-30 16:30:04 UTC with **15 distinct tests passed**, return
code 0 and zero failures, errors, skips or timeout. All 11 original/copied
inputs remained unchanged. No existing suite was rerun.

The [capture plan](../../runs/ap2-hp-reference-software/reference-execution-v1/capture-plan.json)
binds four own files, the fixed planner dependency and six original
caller/builder/client files. The driver refused consumed output and checked
the seven frozen identities before allocation. Only the new suite executed
with `-I -S -B`. Six original files were copied for identity retention and never
imported; the frozen planner dependency was imported without running its suite.
Binary stdout/stderr, [per-ID outcomes](../../runs/ap2-hp-reference-software/reference-execution-v1/test-outcomes.json)
and 15 per-test constructed artifact files remain retained.

The tests cover exact payment forms/order and same-task merchant continuation,
empty/wrong OTP, invalid/ambiguous cart and typed approval, hidden challenge,
cross-task reply, failed discarded association Task, returned/error object
identity, detached observation, global callback order, recording-failure
neutrality, ASGI scope/event/byte order and original error propagation,
once-only refusal, nested JSON-key/type refusal and owned cleanup after
factory/publication failures. Injected builders/tools/clients do not prove
original compatibility. Zero native/model/key fields describe this inspected
driver/test path, not a system-wide observer or native qualification.

| Bound artifact | SHA256 |
| --- | --- |
| Reference execution | `821b463c1e8d8500b32774b7c04ace2b865c7089c7a8e0ca1f5e7f20ab5df340` |
| Passive capture | `e3abb063246ee0688b098bba933a74c3c2e6c5789b7c9b39bc59cc12b135a5a8` |
| New tests | `11b37c63031130dc31e21440dd7072fc8c7d924afecb395a277733e88e4815dd` |
| Capture driver | `1b1b7ec09eb4e457e34f574394551cf7756cf9520204b4ff11196a7552490766` |
| Capture result | `9e7c30d92abf2cd448d8131410bdc896ffdd707101d549586c2b57599c053719` |
| Capture plan | `0773ca34522bc5ebca138ebedabfc2985d0ef3585203a00ea6f949e3c34939d5` |

## Remaining native integration

The existing startup plan/bootstrap are frozen and have no passive-capture
hook field. This independent contract does not extend them silently. A reviewed
final-application placement, authenticated original binding adapter, exact
client-connection ownership before each HTTP request, durable public capture,
fresh fixed resource gates and verified provider allowance/enforcement remain
required before native execution. The provider ledger is a separate workstream.
The unchanged 1 GiB physical/2 GiB commit thresholds still apply.

Injected success does not establish original import/runtime compatibility,
mandate authenticity, credential transaction association, effect/reset validity,
native task grades, a qualified second domain, scientific novelty or supervisor
acceptance. Research checkpoint credit remains governed by the full rubric.
