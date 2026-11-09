# AP2 human-present public benchmark observer v1

30 October 2026. The second-domain benchmark now has an implemented
[public consistency assessor](../../src/interoperability/ap2_hp_public_assessment_v1.py).
Its first [captured validation](../../runs/ap2-hp-public-software/validation-v1/result.json)
passed all **33 authored software tests**, with exact primary membership,
unchanged inputs and no skipped primary tests. No original AP2 application,
SDK, model or native purchase ran. This is implementation evidence, not a
qualified second domain or a full-task grade.

The [separate AI source review](ap2-human-present-public-assessor-source-review-v1.md)
found no remaining blocker at this bounded scope. The
[independent receipt audit](../../runs/ap2-hp-public-software/validation-v1-independent-review.json)
verified 87 checks with zero discrepancies, without rerunning tests. The
[design](ap2-human-present-public-assessor-design-v1.md) and
[source reassessment](ap2-human-present-source-reassessment-v1.md) preserve the
original merchant/processor hierarchy and synthetic purchase requirements.
The original AgentOps metric and its fifteen audited terminal software suites
remain separate.

## Inputs and implemented lanes

`assess_public_payment(initial_message, merchant_pending, resume_message,
merchant_after, *, processor_pending=None, processor_resume_message=None,
processor_after=None)` accepts caller-supplied A2A 0.3 JSON observations.
The optional processor objects must be its actual public exchanges; labels
alone do not establish original child ownership or stage order.

- Merchant and processor task/context continuity, initial merchant binding,
  public OTP challenge and complete child challenge-message propagation.
- Exact typed OTP and mandate forwarding, with ambiguous/missing values left
  unknown. Initial/resumed mandate changes are observed separately; the source
  is not assumed to reject a different valid mandate on a pending task.
- Requested completion after literal `123`, retry after another string, and
  explicit absence-of-Success-receipt checks before a valid OTP. A downstream
  failure is an unmet target, not an invented successful purchase or proof of
  source nonconformance.
- Unique receipt extraction, strict JSON Success/Error field projection,
  separate source success/UUID4-constructor fields, typed full receipt
  propagation and the exact source closed-JWT-leaf SHA256/base64url reference.

Results use `consistent`, `discrepant` or `unknown` per lane. These describe
only the stated observation predicate or requested target. The report always
keeps aggregate task grade unset and native/scientific qualification false.
Capture completeness/order, source authentication, signature/authority/expiry,
credential association, consent, reset/effects and semantic purchase success
remain unknown. Strict JSON projection does not claim SDK coercion equivalence.

The observer rejects nonfinite/non-JSON values, preserves extra fields and
nulls, distinguishes booleans/integers/floats and does not mutate its inputs.
Malformed parts or duplicate candidate values cannot be hidden to obtain
conclusive absence, identity or receipt checks. Matching Error receipts may
satisfy propagation without satisfying the source payment-success projection.

## Captured implementation verification

The [33-test suite](../../tests/test_ap2_hp_public_assessment_v1.py) covers
wrong and missing task/context IDs, rewritten child challenge identity,
forwarding changes, wrong OTP with an inappropriate success artifact, missing
and duplicate receipts/mandates, changed mandates, stable leaf references,
bool timestamps, UUID4 bits, extra/null fields, Error schema, typed propagation,
malformed parts, finite JSON and input preservation.

The [capture driver](../../scripts/capture_ap2_hp_public_validation_v1.py)
ran frozen workspace copies with `-I -S -B`, retained stdout/stderr and exact
primary test identities, and published an exclusive result after checking
captured/current input agreement. The terminal capture is consumed; do not
rerun it to replace the record. Receipt audit status is tracked separately in
[implementation-status-v1.json](implementation-status-v1.json).

| Frozen file | SHA256 |
| --- | --- |
| Assessor | `2d675b1043671dc3319ce55df43b7b1bd3a967c650a35aff1a50e6fc47d5345e` |
| Tests | `d5ec2ec51bcd00987e0b7217f7a87ff37868396e4ef105a6ee94e9b45a3ad78e` |
| Capture driver | `518c60cb94bf337560b5b7c0177b46d9e70edcf1b2a07c289378fffef1cfd9a9` |
| Capture result | `a92a1c01455492c63b75f38b03a0a412c7c611fc33ea8e4ea12744e60295492e` |
| Independent receipt audit | `eb892d9e6e97090bab6ed1e9b6429ea6bdab17c66b10f912afd559d04ff75ea7` |

## Next native work

The [native runner design](ap2-human-present-native-runner-design-v1.md)
specifies a disclosed scripted reference at the unchanged merchant public
front door, using the complete original shopper prelude and merchant-mediated
processor continuation. The original ADK-web shopper remains a separate client
control with its challenge-display mismatch intact. No direct processor rescue
or merged MCP-shopping variant is substituted for those paths.

The [dependency plan](ap2-human-present-dependency-plan-v1.md) pins the original
floating x402 source to an explicit preparation-time commit. Complete combined
dependency resolution, source-faithful staging/imports, native runner and passive
capture implementation, reviewed task contracts/reset/gold and original
same-task qualification remain open. The physical-resource gate still fails;
no new native allocation was made. No checkpoint credit or 70% claim follows
from this software validation.
