# AP2 durable observation software v1

30 October 2026. This adds a new standard-library-only
[recorder and raw ASGI wrapper](../../src/interoperability/ap2_hp_durable_observer_v1.py)
and [synthetic tests](../../tests/test_ap2_hp_durable_observer_v1.py).
The single reviewed capture passed all **22 tests** at 17:56:56 UTC.
No original AP2 module, SDK, credential, provider or service was imported. Every
previously consumed observer, binding, test driver and capture is preserved.
The independent review closed after four corrections: live raw IO is included
in final activity witnesses, row validation uses the persisted detached
snapshot, byte digests reject opaque types, and malformed scope classification
preserves original calls without opaque comparisons. The new recorder, tests
and dedicated driver are now consumed sources and must be preserved.

At root's request, a new
[once-only driver](../../scripts/capture_ap2_hp_durable_observer_tests_v1.py)
captured `runs/ap2-hp-reference-software/durable-observer-v1`.
It pins exactly the new module/test plus unchanged reference-execution and
passive-capture dependencies, with a separately pinned driver copy. Its
isolated child uses `-I -S -B`, finite explicit coroutine driving, complete
declared test IDs, raw binary streams and per-ID outcomes. Socket/provider
operations and unowned processes are denied; only the exact bound Python
child is permitted. The driver SHA256 is
`b21a73a3c9c83468c5f56556ce4009cf5b2d01d1c674b0f3a149de464c6673b0`.
Final driver review closed before root authorized exactly this one capture.
No earlier suite was rerun and no capture was relaunched.

## Owned artifacts and encoding

`DurableRecorder.allocate(absolute_path, streams)` requires a fresh artifact
directory with an existing regular parent and explicit named stream kinds:
`raw_asgi`, `frozen_asgi` or `public`. Paths reject links/reparse points.
Directory and file identity are checked before journal writes. Files use
exclusive creation; the recorder never replaces an existing artifact.
Failures after directory allocation return the same authority object with
`ready=False`. Its report retains errors and any open owned descriptors.
`close()` closes only retained descriptors whose recorded identity still
matches; close failures retain authority. It does not stop or close a supplied
application, server, client or transport.

Every accepted event is a JSONL envelope with a global attempt index, named
stream, source index and tagged payload. Supported values are exact built-in
None, bool, bounded int, finite float, str, bytes, tuple, list and dict.
Integers use canonical decimal text, floats use hexadecimal text including
negative zero, and bytes retain base64, length and SHA256. Dictionaries are
ordered key/value entry lists with independently tagged keys. A dictionary
that resembles a byte/tuple tag remains ordinary dictionary data. No object
conversion or `__dict__` inspection is used for payloads. Opaque objects,
mutable byte buffers, sets, nonfinite numbers, cycles and exceeded limits
are incomplete observations. The strict bounded inverse rejects malformed
tags, noncanonical or nonstring byte digests, and colliding decoded keys.
Validation, source index and persisted payload all use the same detached
decoded snapshot of the one encoded value; the original mutable row is not
reread after snapshot creation.

The journal has one owning process. A lock serializes complete bounded
full-write loops and `fsync`; an event is acknowledged only after successful
`fsync`. Global indices count all sink attempts, including rejected attempts,
so retained gaps and missing-index receipts stay explicit. A partial write or
failed `fsync` poisons the journal and prevents further appends. Existing
bytes remain retained. Source-local index gaps/reuse, unknown callbacks and
unbound terminal events mark observation incomplete.

The order is recorder lock acquisition and durable callback append order.
It does not establish socket chronology, causal order across services, or
cross-process coordination. Reentrant appends are refused. External mutable
data changing during serialization can make a snapshot incomplete. Synchronous
disk writes affect timing; preservation concerns objects, values passed to
original operations, returns and exceptions rather than latency.

## Raw ASGI and frozen sink compatibility

`RawAsgiCapture(app, recorder.sink(name))` accepts an owned `raw_asgi` sink.
It records selected public HTTP scope fields and raw receive/send events.
Tagging occurs once in the recorder. The original scope is passed to the app;
received event objects, sent event objects, original return objects and raised
exceptions are preserved. No copied object is passed to an original operation.
Recording/serialization/write failures are caught and make the wrapper's
observation incomplete while the original operation continues unchanged.

Each exchange and send/receive operation has an explicit ID. This permits
interleaved exchanges and out-of-order IO completions to remain bound to their
attempts. Raw IO remains active until its original return, error or
cancellation, including IO retained independently after the application
returns. Final active-operation witnesses include both application and IO
activity, so even partial sealing refuses while either remains alive.
A normal HTTP application return requires an observed completed
response body or disconnect; pending IO prevents interval closure. An observed
application exception may close a failure interval. This is boundary
completeness, not proof of task success or full ASGI/protocol qualification.
Lifespan and non-HTTP calls are forwarded identically and counted for final
quiescence, but are outside durable HTTP event coverage.
Malformed or unsupported scope/type values are marked incomplete before
comparison and the original app still receives its unchanged scope and IO
functions; opaque equality hooks are not invoked by scope classification.

For frozen `PassiveAsgiCapture` and `PublicClientObserver`, `StreamSink` is a
synchronous callback. Recorder failure raises `ObservationError`, which those
frozen wrappers already catch: their capture-completeness flags become false
and their original calls/results remain intact. These sinks retain the
already detached records they receive. They do **not** upgrade earlier
serialization semantics or resolve earlier encoding-marker ambiguity.
Frozen ASGI records lack per-IO IDs; their compatibility tracker uses pending
counts and callback order, not independent IO identity. Public model dumping
and JSON restrictions remain owned by the frozen public observer.

## Final completeness and publication

Every stream must explicitly finish with a final typed witness:
`source_complete`, `active_operations` and `attempted_records`.
An active source cannot finish. A false completeness witness, source-count
mismatch or unmatched interval marks the capture incomplete. This witness is
required even for an empty stream because a frozen serializer can fail before
calling its sink. `RawAsgiCapture.finish()` supplies its current witness;
frozen observers require the caller's explicit final witness after settlement.
No wrapper report or witness authenticates an original import.

`publish()` refuses an incomplete journal, source gap or unmatched interval.
Only an explicit `allow_incomplete=True` permits a partial terminal seal,
and every source must still have finished with zero active operations. The
partial manifest retains unmatched intervals with their key types and never
claims completeness. All publication compares the retained journal identity
with the acknowledged prefix.

Publication writes and `fsync`s an exclusively created
`terminal.pending.json`, then creates `terminal.json` using an exclusive
same-directory hard link. Existing terminal data is never overwritten.
If linking or publication fails, the pending artifact and remaining authority
are retained. Content durability is acknowledged file `fsync` plus successful
link publication; directory-entry survival across a crash remains explicitly
unverified, including on Windows. A visible file alone is not authenticated
proof of a successful publication acknowledgement.

The terminal is immutable and concerns only the declared closed local source
intervals. Later callbacks are refused and make the current recorder report
incomplete without rewriting that terminal. The native owner must settle all
original work before finishing streams and retain later error reports; a
terminal cannot prove that no future request will occur. Hostile concurrent
filesystem replacement is not authenticated or atomically excluded.

The constructed tests cover type/key/byte roundtrip,
malformed values, exclusive/partial allocation, short writes and write/fsync
failure, original object/error preservation, finite interleaving, final witness
and active-source refusal, gap/partial publication, frozen sink compatibility,
reentrancy, retained-journal interference, terminal no-overwrite, close authority
and post-seal attempts. They also exercise retained IO after application return,
original cancellation identity, post-encode row mutation, opaque digest types
and opaque scope types. These are synthetic application/IO objects, not
original SDK compatibility or native service evidence.

## Retained constructed validation

The [result](../../runs/ap2-hp-reference-software/durable-observer-v1/result.json)
has SHA256 `d0c327b08d74935c7708374179ea35adf28839580dccfaf019cf11a98705c511`.
It records return code 0, all 22 declared IDs passed, zero failures, errors,
skips, expected failures or unexpected successes, no timeout, and no cleanup
or execution error. Four source/test inputs, the separate driver copy and the
interpreter remained unchanged. The child created no event loop or process.
Socket/provider and unowned-process permissions were denied by policy;
both policy receipts contain zero rejected attempts. These Python audit
receipts concern the reviewed constructed code and do not authenticate a
native runtime.

The [capture plan](../../runs/ap2-hp-reference-software/durable-observer-v1/capture-plan.json),
[per-ID outcomes](../../runs/ap2-hp-reference-software/durable-observer-v1/test-outcomes.json),
[binary stdout](../../runs/ap2-hp-reference-software/durable-observer-v1/tests.stdout.bin)
and [binary stderr](../../runs/ap2-hp-reference-software/durable-observer-v1/tests.stderr.bin)
are retained with all five source/driver copies. Stdout is retained empty;
stderr contains the complete test runner output. Temporary per-case test
artifacts were cleaned up by their test owners; no retrospective per-case
provenance is manufactured.

| Consumed input | SHA256 |
| --- | --- |
| durable observer | `3ba610b079af528cca7301c8357de5cbd609dbf5cedd9460bdf843ce05e8f6bc` |
| constructed tests | `411f9824dd51def860e027c5c285826dcbbf394396c0422a6e5c12f24a689941` |
| reference execution dependency | `821b463c1e8d8500b32774b7c04ace2b865c7089c7a8e0ca1f5e7f20ab5df340` |
| passive capture dependency | `e3abb063246ee0688b098bba933a74c3c2e6c5789b7c9b39bc59cc12b135a5a8` |
| dedicated driver | `b21a73a3c9c83468c5f56556ce4009cf5b2d01d1c674b0f3a149de464c6673b0` |

No original SDK, native service, provider request or grade attempt executed.
This result grants no native qualification, provider entitlement or
full-research gate credit. Root status, handoff and ZIP updates remain a
separate responsibility.
