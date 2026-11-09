# AP2 human-present public assessor: bounded source review v1

30 October 2026. **Closed at the caller-supplied public-consistency scope; no
remaining source blocker found in the final bytes below.** A separate AI review
read the core, all 33 authored test methods, the
[design](ap2-human-present-public-assessor-design-v1.md), retained generated
PaymentReceipt types and source leaf/hash/constructor paths. This reviewer did
not edit core/tests, import either module, rerun tests, call Gemini, launch AP2
or issue a native/domain grade. Root's later captured execution and its receipt
audit remain separate evidence.

This is an AI source review, not independent human scientific validation,
capture authentication or an executed original workflow. Consistent lanes
state only the properties explicitly checked in supplied JSON objects.

## Reviewed final identity

| File | SHA256 |
| --- | --- |
| `src/interoperability/ap2_hp_public_assessment_v1.py` | `2d675b1043671dc3319ce55df43b7b1bd3a967c650a35aff1a50e6fc47d5345e` |
| `tests/test_ap2_hp_public_assessment_v1.py` | `d5ec2ec51bcd00987e0b7217f7a87ff37868396e4ef105a6ee94e9b45a3ad78e` |
| `docs/research/ap2-human-present-public-assessor-design-v1.md` | `30752cf40579d0f63c2fbfe2771dffaf44619d1e0541e90f4e22a4dc2d7f181d` |

Any later change to these core/test bytes needs a new review or an explicitly
bounded amendment. The review does not bind an uninspected capture driver.

## Boundaries checked

| Boundary | Final source finding |
| --- | --- |
| JSON types | The entry point validates finite JSON values with string object keys before assessment. Nonfinite floats, arbitrary objects, tuples and nonstring keys cannot be normalized into eligible observations. Full receipt/challenge comparisons use canonical JSON serialization, preserving boolean/integer/float and absent/null differences. |
| Part extraction | The extractors require recognizable text/data/file part shapes, a dict for actual DataPart data and exactly one occurrence of the selected key. Missing or malformed parts and ambiguous receipt/mandate occurrences produce uncertainty rather than hidden values or a conclusive absence. This is a bounded shape observer, not a full SDK A2A-envelope validator. |
| Task and context continuity | Pending and later Task `id`/`contextId` must be nonempty strings. Missing associations or missing continuation fields are unknown; present continuation task/context values are compared with the actual pending/later identities. RPC IDs, caller stage labels and session metadata are not substituted for these fields. |
| Child challenge forwarding | The complete supplied status Message is compared with the processor Message, whose task/context is checked against the supplied processor Task. A preserved child Message need not be rewritten to merchant task identity. Distinct parent/child task IDs and shared context remain observations, not authenticated ownership. |
| OTP and mandate forwarding | Unique typed strings from actual continuation DataParts are compared separately. Missing, ambiguous or nontyped values remain unknown. Initiating/resumed mandate equality is an observed lane; changed supplied mandates do not trigger an aggregate failure or a claim that the original source rejects them. |
| Target versus conformance | Literal `123` has requested target `completed`; another string has retry target `input_required`. A correct-OTP downstream failure is an unmet completion target. The lane explicitly does not infer source nonconformance or payment from this target comparison. |
| Wrong-OTP receipt contradiction | Independent pending/incorrect-OTP absence lanes detect a supplied Success receipt even when state remains input_required. Missing/malformed artifact evidence cannot prove absence. A correct OTP does not automatically establish any receipt or signature/effect obligation. |
| Receipt schema versus constructor | `strict_json_receipt_schema_projection` separately handles generated Success/Error field types. Success optional error strings are permitted there; Error requires error strings and permits absent/null/string confirmations. Integer iat excludes boolean. Extra JSON fields are retained. The stricter success-field projection and constructor lane do not become SDK coercion-equivalence claims. |
| Complete receipt propagation | Both unique supplied receipts must satisfy the strict JSON schema projection before their full typed JSON is compared. Equal malformed receipts cannot pass; matching Error receipts can pass propagation without being payment success. Extra fields and explicit nulls participate in equality. |
| Exact reference | The implementation uses the last `~~` segment, the portion before its first `~`, UTF-8 SHA256 and unpadded base64url. This matches retained source extraction/hash operations. Empty/nonstring or unencodable leaf inputs yield no validated reference. Whole presentation equality remains separate from closed-leaf reference equality. |
| UUID4 constructor bits | The source-confirmation lane requires the success projection, one lowercase 32-hex payment ID, version nibble `4`, RFC4122 variant nibble in `89ab` and all three identifiers equal. This is source-constructor shape, not proof that randomness or the original constructor actually produced the value. |
| Claim ceiling and mutation | All input observations are read only; returned lanes are copied. Aggregate task grade is always null. Source authentication, completeness, original stage order, signatures, credential association, authority/expiry/amount, consent, reset/effects and semantic purchase success remain unknown. Native qualification and scientific novelty stay false. |

## Disclosed review corrections

The reviewer initially found two blockers and sent them to root before capture:

1. Equal lowercase 32-hex strings alone admitted IDs whose version/variant bits
   cannot be produced by `uuid.uuid4().hex`. Root added the UUID4/RFC4122 bit
   checks and corrected the positive fixture; an adversarial non-UUID4-hex
   fixture is present in final test source.
2. The initial stricter success projection could not represent the design's
   generated Success/Error schema lane. Root added a separate strict JSON union
   projection, permitted Success optional error strings, Error field/null
   handling and schema-gated full propagation. The final test source separately
   checks schema admissibility, source-constructor discrepancy and Error
   propagation without task success.

The final reread also confirms finite-JSON validation, malformed-receipt
propagation guards and malformed-part uncertainty added by root during this
implementation. The reviewer made no edits and executed none of those fixtures.
The 33 test methods are a source inventory, not a passing-test count. The source
review does not assert exhaustive coverage of every design near-miss combination.

## Source basis and remaining qualification

Original AP2 source is retained at pin
`e1ea56db72a6385bce3e5c1112b3a56ce60acb43` under
`source-evidence/ap2-procurement-screen-v1/source/`. Relevant original predicates
are processor `tools.py:108-171,180-222,254-273`, merchant
`tools.py:277-318`, shopper `tools.py:277-311`, generated PaymentReceipt
Success/Error fields, SDK `mandate.py:402-417` and `utils.py:21-36`.
Those source relationships establish the observer's comparison rules, not
loaded-runtime equivalence or future model routing.

The assessor intentionally cannot prove causal ordering/completeness, stage
authenticity, actual merchant-child origin, valid signed authority, credential
state association, reset, committed payment or a successful unchanged native
scenario. Those require source-bound capture, original runtime evidence and
independent task validity. A captured authored-software pass may validate this
implementation at its stated scope; it cannot upgrade any of those open lanes,
establish a second qualified domain, demonstrate novelty or award checkpoint
credit by itself.
