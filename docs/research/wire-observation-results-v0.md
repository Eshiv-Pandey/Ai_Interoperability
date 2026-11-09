# Development wire-observation and projection results v0

24 October 2026. These are measured local **development** executions and software checks. They are not held-out application tasks, natural bridge defects, LLM experiments, novelty evidence or independent human validation. The registered title and full approved research scope remain unchanged.

## Retained executions and validation

Five capture attempts are retained under `runs/wire-observation/`: two AmirK-S startup-driver failures, one successful AmirK-S continuation and two successful mgcrea continuations. The latter two are repetitions of the same task family, not independent scenarios. Both failures happened before task behavior: Node preload needed a Windows file URL; configuration rejected port zero while the supported CLI override accepted it. These are recorded setup corrections, not adapter faults. No record was overwritten.

The preferred positive captures are:

- [AmirK-S modern task route](../../runs/wire-observation/amirk_a2a_to_mcp-2026-10-23T20-02-10-750Z-3828/runtime.json): real local HTTP, declared modern Tasks extension, one pending task, exact input-request key, same-task answer, extension result and ordinary authoritative reread.
- [mgcrea ordinary-tool route](../../runs/wire-observation/mgcrea_mcp_a2a-2026-10-23T20-06-37-342Z-9536/runtime.json): real child-process stdio and A2A loopback HTTP, negotiated MCP 2025-11-25, local/refresh task reads, same public task/context answer and completed text artifact.

Every successful directory includes exact driver snapshots, diagnostics and a separate `private-native-http.jsonl`. MCP-visible handles/IDs stay ordinary input; IDs learned solely through private HTTP are evaluator-private. AmirK-S's public status-message `_meta` also contains native task/context IDs in this capture, so **not every native ID is hidden**. The projector uses the ordinary bridge handles and does not read a private sidecar.

An independent checker validates the public event claims and serial finite graph; a separate explicit checker correlates native dispatches, response bodies and IDs. Streaming response headers/body can arrive after the MCP acknowledgement, so correlation uses unique initiation plus identity/text and never claims a poll caused the state change. All files are decoded explicitly as UTF-8; a discarded ad hoc cp1252 reader error was not a capture defect.

The corrected [v0.1 verification record](../../runs/wire-projection/verification-v0.1.json) retained all five attempts, checked three successful projections and their private correlations, and recorded **115 passing software tests**. It copied the exact code, tests, scripts, development examples and wire inputs into [its source/data archive](../../runs/wire-projection/verification-v0.1.sources) before verification. All 18 recorded Python implementation hashes and five runtime-input hashes matched both current and archived files when inspected. The [v0 record](../../runs/wire-projection/verification-v0.json) remains historical and was not overwritten.

Separate code review found controlled mutations that the initial private checker accepted incorrectly: omitted/empty native artifacts, an error or empty native task snapshot, and conflicting task state. A public ordinary `a2aState`/mapped-status inconsistency also needed rejection. Those are **our validation-code gaps found by labelled tests**, not observed adapter bugs. The corrected verification supersedes v0 for validation confidence and archives exact code/data before checking.

The [fresh-interpreter replay](../../runs/wire-projection/clean-replay-v0.1.json) imported only archived implementation source, independently rechecked both public projections and private correlations, reproduced the exact saved projections/baseline/oracle results and certificates, and passed **all 115 archived tests, with zero errors, failures or skips**. All three historical models remain incomplete and abstain at the next clock value. The replay hashed all **59 archive files** before and after execution and confirmed that none changed. It retained the two failed capture attempts; it did not rerun either bridge or make a model/network call. This is a clean-environment software/data replay, not a second human scientific validation or a new wire experiment.

Read-only cleanup checks found the recorded successful bridge PIDs absent and no children of the recorded driver PIDs. The fixture PIDs were not captured, so exact fixture-process termination cannot be asserted; neither captured fixture listening port remained open. No broad process kill was performed.

## Source-backed observations

| Observation | What it establishes | Limit |
| --- | --- | --- |
| Waiting task, exact task/context-bound answer and matching completed artifact were observed on both routes. | A functioning development continuation and literal wire-to-model mapping on the captured cases. | Shared upstream deterministic fixture; no independent application gold or broad interoperability estimate. |
| mgcrea local `refresh:false` reads made no native HTTP call; the post-answer local snapshot still reported input-required until a refresh. | Its documented local-mirror boundary is visible in real execution. | Expected design behavior, not a new failure. A mirror timestamp is not a remote-state lease. |
| Each decisive refreshed task read bundled status, identity and artifact text. | A strongest source-aware lazy checker can obtain that fragment's evidence in one request. | This does not promise one poll through arbitrary asynchronous completion. Cold setup, native requests and bytes are charged separately. |
| Modern Tasks update returned an acknowledgement; logical completion required the later disclosed ordinary task result. | Acknowledgement/result-delivery state must be distinguished from A2A task success. | The pinned source explicitly maps unsuccessful A2A outcomes into completed modern result delivery with an error result. That is a documented semantic distinction. |

All trace-derived finite manifests have `complete=False` and a zero-width **archival analysis clock**, not an invented service TTL. Baseline/oracle agreement and checked certificates concern recorded historical paths only. They do not show that an admission gate predicted completion before the answer was sent. Missing fields, unobserved paths and unmet goals remain unknown; a shortened probe trace cannot certify unsupported.

## Consequence for candidate selection

The [query feasibility audit](candidate-query-feasibility.md) derives a source-backed one-query lower bound for the known-task text fragment and a correctly cached/lazy policy attaining it. The candidate cannot save 20% requests on that fragment; artificial separate status/artifact probes or invented delays would create a misleading win. The 192-admission comparative pilot is **not ready to run under an efficiency claim** until genuinely richer source-backed obligations and a defensible distinction are identified. This is a candidate-feasibility result, not a measured candidate performance comparison.

The project continues toward a novel, independently defensible method. Prospective profile/model fidelity, richer actual operation dependencies, a substantive advantage over strong comparators and human novelty review remain open. The first-week scientific gate is not passed; progress remains **5%** because CP2 earns credit only after all of its required evidence exists.

The [next prospective source-backed probe](reference-continuation-probe-v0.md) checks an external application's reference-dependent continuation. It concerns typed/raw action expressiveness, not an observation saving. The original application uses A2A 0.3, so it supplies no unchanged native-compatible 1.0 witness yet. Native verification and any separately disclosed port are distinct from the five existing captures reported above.

## Reproduction

The capture commands and immutable driver snapshots are recorded in each run. Captures use pinned sources listed in `external/source-lock.json`. Read the [projection contract](wire-projection-v0.md) and [separate review](projection-independent-review.md) before interpreting output.

```powershell
.\.venv\Scripts\python.exe scripts/project_observations.py --output runs/wire-projection/new-verification.json
.\.venv\Scripts\python.exe scripts/replay_historical_verification.py --verification runs/wire-projection/verification-v0.1.json --python tmp/foundation-replay-env/Scripts/python.exe --output runs/wire-projection/new-replay.json
```

Each output must be a new path. The projection runner reads only existing captures, records failed attempts, checks public projections and explicitly loaded private correlations, and saves actual full software-test output. The replay runner uses the archived source/data and an explicitly chosen clean interpreter; create that interpreter with `python -m venv <new-path>` if it is absent. Python 3.11 or newer and the standard library suffice for the archive replay. Neither runner makes network/model calls. Projection mutations are labelled software tests, not naturally occurring bridge bugs.

The [exact replay driver copy](../../runs/wire-projection/clean-replay-v0.1.driver.py) matches the driver SHA-256 recorded in the replay report. Keep this copy with the report if the working replay script later changes.
