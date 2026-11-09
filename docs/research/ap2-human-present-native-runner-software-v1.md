# AP2 human-present native runner software v1

This implementation prepares owned startup of the pinned original AP2 merchant,
credentials provider and payment processor. It does not execute the reference
case or assign a task grade. The supervisor deliverable is implementation and
software evidence; this guide is not a paper draft.

## Implementation and boundaries

`src/interoperability/ap2_hp_native_gate_v1.py` is a stdlib contract validator and
an injected startup engine. `src/interoperability/ap2_hp_windows_runtime_v1.py`
is its concrete Windows Job/TCP adapter. `scripts/boot_ap2_hp_service_v1.py` is
the two-stage child bootstrap. The concrete native startup path has not run.
The tests load adapter definitions and exercise its early helper-origin refusal;
they do not call Windows Job, TCP-ownership or resource-observation APIs or
establish native readiness. The exclusive hard-link publication operation is
exercised by the constructed filesystem tests on the capture drive.

The unchanged services are started sequentially in this order:

| Role | Original module | Port | RPC path |
| --- | --- | --- | --- |
| merchant | `roles.merchant_agent` | 8001 | `/a2a/merchant_agent` |
| credentials | `roles.credentials_provider_agent` | 8002 | `/a2a/credentials_provider` |
| processor | `roles.merchant_payment_processor_agent` | 8003 | `/a2a/merchant_payment_processor_agent` |

The 134-file source receipt stays unchanged. A separate pinned certificate
manifest supplies the two original public certificate assets. The source
validator requires exactly their union of 136 files, including SHA256, byte
length and the two certificate Git blob identities. The complete source stage
must contain no additional files, cached bytecode, links or reparse paths.
These byte bindings do not authenticate source provenance.

## Prospective native plan

The plan schema is `ap2-hp-native-plan/1`. Its exact fields are
`schema_version`, `run_id`, `model`, `output_root`, `source_root`, `services`,
`ownership_policy` and the following artifact references:

- `source_receipt`, `supplementary_assets` and `environment_manifest`;
- `usage_receipt`, `usage_hook`, `usage_hook_review`;
- `interpreter`, `powershell`, `credential_helper`;
- `owned_job_helper`, `tcp_helper`, `bootstrap_helper`, `bootstrap_script`,
  `windows_runtime`.

Each artifact reference has exactly `path` and `sha256`. Paths are absolute,
regular and free of links/reparse ancestors. Original helpers and source
receipts have fixed reviewed digests and origins. The bootstrap, runtime and
gate origins must match their expected project paths. The `run_id` is 32 lower
case hexadecimal characters. The fixed model is
`gemini-3.1-flash-lite-preview`. The fixed ownership policy is
`per_service_windows_job_no_breakaway`.

The configuration hash is SHA256 of canonical JSON for every plan field except
`usage_receipt`, avoiding a circular reservation reference. The launch binding
also contains the complete plan SHA256, run identity, role and ownership policy.
The output must be newly allocated and separate from the source/environment.

The environment receipt schema is `ap2-hp-native-environment/1`, with status
`installed_hash_verified`, platform `win32`, bound interpreter, environment root,
site-packages inside that root, complete `files` inventory and these package
pins: ADK 1.28.0, A2A SDK 0.3.24, GenAI 1.66.0 and Pydantic 2.12.5. Installed
bytes must match the manifest; a resolver result is insufficient.

The reservation schema is `ap2-hp-model-usage-reservation/1`, with status
`reserved_prospective_allowance`. It binds the configuration hash, run, model,
hook digest, hashed allowance evidence and ledger. Remaining/reserved model
calls must be positive integers, with reservation no greater than remaining
allowance. Counting/reset rules must be marked verified, and the reservation
must be currently valid. The hook review requires `source_review_closed`, its
bound hook digest, and `enforce_before_every_provider_request`. Receipt checks
do not authenticate provider entitlement or prove that an unexecuted hook
enforces its asserted contract.

## Resource gates and owned cleanup

`ap2-hp-native-resource-gate/1` has exact fields `schema_version`, `binding`,
`minimums` and two `samples`. Each sample contains an aware UTC timestamp,
nonnegative integer `monotonic_ns`, and integer available physical/commit bytes.
Both samples must meet 1 GiB available physical memory and 2 GiB available
commit. Samples are 10 to 30 seconds apart; UTC and monotonic intervals must
agree within one second. The second sample must be no more than 60 seconds old.
An immediate sample is no more than two seconds old and must remain consistent
with the prospective gate. These fixed thresholds are policy inputs, not a
measured guarantee of successful execution.

The engine obtains group and per-service gates, refuses occupied original ports,
and creates exclusive `.temp-db` and `.logs` directories. It retains each owner
before attempting launch. On startup success, the returned `GroupRun` retains
all owners; its caller must call `stop()` and settle them before disposing of
the object. On any startup or final-result publication failure, it attempts to
stop only its retained owners. Incomplete cleanup returns live authority and
status `cleanup_incomplete_authority_retained`. No unrelated listener is killed
or remapped. Final result publication is inside this cleanup boundary.

JSON publication writes an exclusive `.pending` sibling, flushes/fsyncs it, then
creates the final path with an exclusive hard link. Pending bytes remain
evidence. A consumed output cannot be restarted or overwritten.

## Bootstrap and readiness

Before credential access, the first bootstrap validates current artifacts,
headroom, the bound interpreter and exact inherited Windows Job membership. It
then invokes the existing DPAPI credential helper through controlled PowerShell
arguments. The credential-injected stage repeats the gates/membership checks,
requires CARD/shared-state configuration, installs the reviewed per-request
usage guard, rechecks headroom, and runs the unchanged original module.

PowerShell propagation of the inherited Job handle remains unverified. The
original stage fails closed if it cannot verify that exact handle. The existing
credential helper is invoked by pathname after validation, so executed helper
bytes are not held immutable against a concurrent replacement.

Readiness uses the original process PID from the guarded bootstrap marker,
verifies Job/TCP ownership of the connected peer, obtains a fresh client gate,
and performs the original discovery GET. It compares the returned card's
`name`, `url` and `protocolVersion` with pinned source fields. This is a
three-field identity comparison, not full card equivalence or authentication.
The native Windows Job, inheritance, TCP and original-card path has not run.

## Retained constructed software capture

The once-only capture driver is
`scripts/capture_ap2_hp_native_gate_tests_v1.py`. It copies its driver, the three
implementation files, the test suite, frozen helper/receipt files, original
134-file source tree and supplementary certificate copies into an isolated
checkout layout. The child uses `-I -S -B` and runs the captured test suite. It
retains the capture plan, input inventories, per-ID outcomes, binary test
streams, constructed source/environment/usage fixtures and case outputs.

The suite declares 28 checks covering exact source closure, tampered/missing
certificates, environment and usage binding refusal, resource sample timing,
original ports/order, occupied-port refusal, injected startup/readiness failures,
owned cleanup, final-publication cleanup authority, exclusive publication,
consumed-output refusal and arbitrary-helper early refusals. The one bootstrap
subprocess retains its binary refusal streams. Constructed environment, usage
and hook fixtures are explicitly nonexecuting and do not authorize a native run.

The single retained run completed at 2026-10-30 12:28:59 UTC under
`runs/ap2-hp-reference-software/native-gate-v1`. All 28 distinct declared tests
passed, with return code 0 and no timeout. The 147 copied input files matched
their pre-copy identities before launch; original and captured inputs were
unchanged afterward. `capture-plan.json`, `test-outcomes.json`,
`tests.stdout.bin`, `tests.stderr.bin`, `result.json` and all constructed case
artifacts remain retained. No suite replay was performed.

The retained result SHA256 is
`68d9601e8fb6ee589bd7445835385378ec06376cac6f337c01044cd237041d22`.
The plan SHA256 is
`10860e5e1b887c15e03b48de93b99f7564e013ce36df92d561b7fd4080b03aea`.
The per-ID outcome SHA256 is
`e547d03df1fc201e367ff8e7137e948cf7a2fa27dc3a8e0c3ae8a1fe0c7cd8f0`.

The native run still requires an installed byte-verified environment, genuine
prospective allowance evidence and a reviewed enforcing usage hook. No original
AP2 imports, key opening, model requests or original application execution have
occurred in this software preparation. No checkpoint percentage is inferred
from the constructed software tests.
