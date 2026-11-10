# AP2 original application development v4

This version adds shared-lifting admission immediately before the original
merchant OTP continuation. It preserves v3, every earlier hosted allocation,
the frozen AP2 source tree and the owned v1 binding/planning/observation helpers.
All v3 offline model, ASGI transport, portable source/runtime validation,
structural callable comparison, model projection and task-state comparison
interventions remain explicit. Provider generation requests are zero.

The owned coordinator subclass calls the unchanged original message builder
once. It retains that exact returned object and continues to send through the
original merchant observer. It reads the actual public pending Task, uses the
merchant Task's ID and shopping context, and preserves the nested processor task
reference separately. Existing caller-held signed mandates and risk data remain
unchanged. No task, mandate, status or receipt is manufactured for execution.
The only OTP recipe is 123, extracted from the actual public demo hint; a missing,
changed or ambiguous hint refuses continuation.

The pending profile has one finite continuation edge and horizon one. Its goal
projects completion of that original task under stated source-fidelity and
deterministic offline demo assumptions. It contains no invented future Task or
receipt. Model evidence and recipe coverage are both incomplete, so this
allocation can admit only a positive supported recipe-path. A negative or unknown
solver result cannot dispatch and never establishes whole-route non-support.
The module is an authored adapter to supplied finite relations, not an automatic
compiler of the complete AP2 interface.

The runner invokes `refinement_shared_lift_v2.evaluate` with a 100,000-unit work
budget and the unchanged independent `refinement_oracle.check_certificate`.
The witness must equal the exact public dump of the original builder message.
The 15-second evidence interval is measured from extraction at the observed
pending boundary. The input, profile, solver result, certificate/check receipt
and fsynced raw/public journal prefix are retained before the original send.

Before forwarding the actual original merchant HTTPX request to the original
ASGI handler, the runner rechecks the certificate at the dispatch clock. It
requires identical task/context/message IDs, signed mandates, challenge response
and all meaningful message fields. Only documented optional model nulls are
removed for the wire comparison; explicit null data values are preserved.
Admission files and the earlier journal prefix must retain their hashes, and a
second admission or raw dispatch is refused. The raw request's actual JSON-RPC
ID and byte digest are retained before forwarding; no SDK identifier is invented.

After execution, the unchanged durable raw capture must contain that exact
request after the recorded admission prefix. Original caller/public/raw results
must agree, the original merchant and processor tasks must resume and complete,
and the original Success receipt must match the processor, merchant, caller and
credential-provider delivery. Receipt correspondence and completion are observed
application checks, separate from the model certificate.

The local controls use explicitly constructed tasks and ASGI applications. They
exercise positive witnesses, public-hint selection, original authority, mandate
preservation, checker rejection, unknown budget outcomes, expiry, tampering,
once-only guards and journal ordering. They perform no original application
import or provider generation and cannot establish original runtime success.

Preparation and execution are exclusively allocated, retaining failures:

    python -I -S -B scripts/ap2_reference_development_v4.py prepare --output runs/ap2-reference-development/v4/prepared-NEW
    python -B -m unittest discover -s tests -p test_ap2_reference_development_v4.py -v
    python -I -S -B scripts/ap2_reference_development_v4.py execute --output runs/ap2-reference-development/v4/application-NEW --site-packages PATH

The read-only analyzer replays the certificate with the retained checker,
reconstructs the profile from actual public pending/caller values, verifies the
pre-send artifact and journal hashes, and checks original task/receipt semantics:

    python -I -S -B scripts/analyze_ap2_application_development_v4.py --application APPLICATION --output ANALYSIS-NEW

This remains development integration with offline fixtures, ASGI transport and
owned helper adaptations. It does not establish native TCP, live-provider,
human-gold, whole-route or aggregate research-task qualification. Project/model
quota and billing bounds remain unverified. Private signing files and saved
provider credentials are outside the retained public artifacts.
