# Independent AP2 development review v2

The final retained-output analysis passed independent review on 10 November
2026. **This is partial AP2 development evidence; the original AP2 application
did not complete.** The actual original-function trial remains `subset_failed`
with exit code 2. Its five durable events reached original checkout creation,
both shopper signer outputs, original verifier outputs and original receipt
construction. A later harness property read failed because the SDK
`PaymentReceipt` is a RootModel and exposes `receipt.root.reference`.

The separate `postcapture-20261110T1310Z` allocation completed with exit code 0
and 11 passing checks. It reused those five outputs and performed **zero new
checkout/signing trials, zero signing-key operations and zero provider
requests**. It checked exact checkout/closed-leaf hashes, transaction and amount
bindings, receipt structure, the actual unsent message builder, canonical
receipt extraction, missing DataParts and duplicate receipt rejection. The
RootModel property correction was used in this separate analysis; the failed
original allocation was preserved.

| Allocation | Verified disposition |
| --- | --- |
| `offline-subset-20261110T1255Z` | Venv ancestry preflight failed; original status remains failed |
| `offline-subset-base-20261110T1258Z` | One original-function task trial reached five events, then harness failure |
| `postcapture-20261110T1310Z` | Retained-output analysis succeeded; no task/signing rerun |

The review hashed **28 retained files, 189,197 bytes**, without changing them.
All **136 original AP2 source files** matched the frozen inventory exactly,
including absence of extra source files. All **177 imported frozen-environment
files** reported by the successful analysis matched their installed manifest
hashes. The analysis worker result matched its outer receipt and all 11 checks
were true. The corrected successor's 14 constructed software tests passed
independently, including changed-binding and changed-copy rejection.

The failed trial's runner hash is
`0cc23270a868f5ff4533cb57a587c5450c01cf0260678a73f0a26e7fa33f1431`.
Its exact bytes were retained after the trial and before correction; this is
explicitly post-run retention, without capture authentication. The analysis
runner was retained before its own execution and matches its plan hash
`6b33c7ea5004e274ffd6a6ba372599b3bd6a6ecccefb5216134948e8f9bd6417`.
The independent review matched the original source plan/result/events/runner,
all four copied inputs, the analysis plan's `source_binding` and the worker's
`source_capture` exactly.

The captured analysis runner omitted an automatic comparison between its
reloaded external source binding and the planned binding/copies. No mismatch
was found in this actual run: the independent review performed those missing
comparisons. The author corrected that gate prospectively. The corrected
successor remains distinct from the already captured analysis runner, and no
analysis or original task was rerun for this source fix.

The extractor uses complete code objects compiled from the original modules
and creates functions with `types.FunctionType`. The review reconstructed code
hashes for all 12 selected original functions and checked the extraction
recipe. Their bodies are preserved, while globals/defaults and module setup
are supplied by the declared extraction intervention. The failed original
trial has no terminal function-code inventory, denial counters or imported
module inventory; those unavailable observations are not inferred from the
successful later analysis.

Both original generated-key profiles and the analysis profile are absent,
consistent with their complete cleanup receipts. The runner uses the
hash-pinned base Python executable with `-I -S -B`, explicit frozen
site-packages and a parent-PID gate, avoiding the venv launcher's secondary
process. Its direct child is waited before cleanup. The child environment
allowlist excludes provider credentials; capture payloads contained no private
PEM material or Gemini API-key format. The successful analysis recorded zero
network/process/secret-file denial events. This establishes source-bound
ownership and cleanup consistency, not a full OS sandbox or external capture
authentication.

**Signature verification is reused observation evidence.** The original trial
recorded outputs returned by the original mandate verifier functions. Generated
public/private key profiles were subsequently removed, and the retained
mandates provide no embedded public verification keys. The analysis therefore
did not freshly reverify their signatures. Altered-signature and wrong-key
negative controls in the original harness were not reached and are not claimed
as observed successes.

The constructed receipt's `Success` field follows the original receipt
constructor and binds the exact retained closed-mandate leaf. It is not
evidence that a payment, OTP continuation or provider acknowledgment completed.
The constructed cart, direct tool invocation, extracted function namespaces,
state carrier and unsent wrappers bypass the original resolver/catalog,
ADK shopper, credential selection, merchant/processor continuation and network
peers. Full original module-import compatibility is also unverified.

The compact review and per-file hashes are
[independent-review.json](../../runs/ap2-reference-development/v2/independent-review.json).
The original and later terminal results are
[original subset result](../../runs/ap2-reference-development/v2/offline-subset-base-20261110T1258Z/result.json)
and
[retained-output analysis result](../../runs/ap2-reference-development/v2/postcapture-20261110T1310Z/result.json).
These findings support implementation development and concrete partial
observations. They supply no full AP2 application success or held-out benchmark
qualification.
