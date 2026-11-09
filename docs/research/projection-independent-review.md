# Separate AI review of historical wire projection v0

Prepared 2026-10-24. Human review remains pending. This is a software and source
inspection record, not a bridge benchmark, natural-defect estimate, independent
application gold, prospective admission result or novelty claim.

`src/interoperability/projection_checker.py` was authored by a separate AI agent
from `docs/research/wire-projection-v0.md`, the finite interchange specification
and pinned upstream sources. The checker does not import the projector,
baseline, oracle, extraction functions, predicate functions or transitions.
It checks the source bytes, scalar observable claims and exact finite graph
itself. Its tests state expected projections directly; they do not call the
projector to construct expectations. A shared specification and AI authorship
are limitations of this development review, not independent human validation.

The source inspection used AmirK-S `src/envelope.ts`, `src/parts.ts` and
`src/tasks/handlers.ts` and `src/lifecycle.ts`, and mgcrea `src/tools/tasks.ts`, `src/tools/writes.ts`
and `src/client/shape.ts`, at the commits in `external/source-lock.json`.
These sources establish the supported literal field paths: ordinary bridge
handles, modern task records and empty update acknowledgements, mgcrea JSON
tool text, bounded history, artifact descriptors and labelled artifact blocks.
History or unlabelled acknowledgement text never establishes artifact delivery.
Modern Tasks `status=completed` means that its request result is available; an
A2A failure can legitimately produce that outer status and a failed ordinary
result inside it. The checker uses the disclosed ordinary status for the
logical goal, rejects nested `isError` in v0, and leaves logical completion
missing when only the modern completed record is available.
Known ordinary `status` and `a2aState` must agree with the pinned source's
explicit mapping; contradicting them cannot turn A2A failure into logical
completion. The separate native check also compares state and complete
artifact identity/text sets on actual full GetTask snapshots, including empty
sets. An A2A error cannot back an ordinary successful task view; a disclosed
modern failed record remains a different, faithfully represented error layer.

The checker rejects duplicate JSON keys, inconsistent parsed/raw data or UTF-8
raw hashes, repeated exchange/request IDs, changed correlation or run markers,
overlapping serialized MCP intervals, changed pins, unsupported observable
claims and any graph, goal, namespace, clock or completeness substitution.
Missing returned fields and artifact bodies remain missing. A faithful partial
projection may pass checking while its finite decision is unknown. An explicit
wrong request target is false; an actual changed returned reference remains
the changed reference and cannot be replaced with an alias.

The separate `check_native_sidecar(trace, records)` accepts explicitly loaded
private records; neither checker reads sidecar paths or makes network calls.
Native raw bodies have their own hashes and JSON-RPC IDs. SSE data is parsed
with exact event framing. A native request is correlated by its unique MCP
request initiation and exact dispatched text/task identity. Stream headers and
full bodies may arrive after the acknowledgement and are not attributed as
actions caused by a subsequent get. Public/native IDs are compared directly
where public, and opaque bridge handles are checked for consistent association
without putting private native IDs into the public model.

The development check used the successful AmirK-S `20-02-10-750Z-3828` and
mgcrea `20-06-37-342Z-9536` captures under `runs/wire-observation`; their native
sidecars passed the separate checker. These are shared deterministic upstream
fixture executions with zero model calls. All JSON files must be read with
explicit UTF-8 decoding on Windows; the stdio hashes include the final newline.

`python -m unittest discover -s tests -p test_projection_checker.py -v` passed
33 methods covering normal and continuation paths, ordinary/modern differences,
local stale mirrors, missing observations, artifact/history substitution,
controlled byte/ID/hash/run mutations, graph/goal/clock mutations and private
native correlation. These are labelled synthetic software fixtures, not 33
external executions. Trace-derived finite evidence always has `complete=False`
and `observed_at=valid_until=analysis_clock`; a later evaluation is unknown.
