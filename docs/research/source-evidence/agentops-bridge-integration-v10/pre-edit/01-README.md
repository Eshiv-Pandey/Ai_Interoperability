# Agent interoperability research

**Current evidence (27 October 2026):** the [native protocol v9 results](docs/research/agentops-native-protocol-results-v9.md)
verify synchronous and streaming canonical A2A 1.0 confirmation with one original-task
effect per case. The parent check verifies 1,247 exported files. Matched omitted-header
requests return -32009 without effects; both card variants still advertise 0.3.
All 28 preparation tests pass; 150 protocol modules are pinned. No installation
or live model call occurred. WSL execution succeeded in the current environment.
**Do not rerun completed v8 or v9.** Historical failures/seals are preserved.

Next, implement and freeze the [matched unchanged-bridge controls](docs/research/agentops-bridge-profile-plan-v1.md),
including default versus configured headers and all permitted confirmation alternatives.
Native success is not bridge qualification or C1 novelty. CP1 passed; CP2 in progress;
verified credit remains **5%**. The distinct method, reviewed corpus, frozen evaluations,
independent reproduction, human review and complete paper remain open.

**Current deadline: 10 November 2026**, following the user's 27 October two-week
instruction. The [deadline plan](docs/research/deadline-plan-v2.md) supersedes the
old 45-day calendar without reducing the approved requirements.


Registered project: **Benchmarking Framework for LLM-Based Agent Interoperability: Measuring Interoperability Loss Across Heterogeneous Agent Boundaries**.

Approved workflow v1 studies task-relative continuation admission across pinned MCP/A2A bridge routes. The current code is an **established finite reachability baseline and development foundation**. A novel candidate advantage, real-route study, reviewed held-out tasks and paper results remain to be demonstrated. No fabricated experimental results are included. All model access and token quotas remain unconfirmed.

See [approved workflow](RESEARCH_WORKFLOW.md), [checkpoint register](docs/research/checkpoints.md), [finite semantics](docs/research/finite-model-v1.md) and [research evidence](docs/research/README.md).

## Local setup and development replay

Python 3.11 or newer; core code has no third-party runtime dependency. On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m interoperability development --output runs/development/new-run.jsonl
```

On Linux/macOS use `.venv/bin/python` for the same commands. Evidence output must be a new path: existing run records are never overwritten by the CLI. Each trace contains the exact runtime manifest, provenance, source hashes, environment, actual decisions, certificate check and measured timings. Timing these tiny graphs does not establish a method speed advantage.

The fixture graphs under `examples/development/` are explicitly authored semantic tests. Their results validate finite-model handling only; they are not observed external bridge failures, held-out tasks or LLM experiments. The independently authored oracle does not import the baseline's predicates or transition logic. Agreement does not validate the graph's relationship to a real protocol or replace human review.

External bridges are pinned in `external/source-lock.json` when audited. Their original tests, licenses and wire evidence are separate from our planned application-style benchmark. Missing-license source is not approved for redistribution. No paid inference or remote publication is performed by local setup.

The [bridge eligibility audit](docs/research/bridge-eligibility.md) now records two licensed, separately implemented development routes. After its pinned Node dependencies are installed, the native reference can be replayed with `node scripts/native-wire-reference.mjs --output runs/wire-native/new-reference.json`. Its [initial raw HTTP record](runs/wire-native/reference-v1.json) verifies send/get, same-task input continuation and cancellation against the upstream deterministic fixture. This is development eligibility evidence, not an application benchmark or a new interoperability finding.

The [candidate v0](docs/research/candidate-admission-v0.md) and [hard novelty gate](docs/research/implementation-novelty-gate.md) define the next discriminating work. Novelty, wire-to-model fidelity, human review and the confirmatory study remain open. [Checkpoint status](docs/research/checkpoint-status.json) currently records CP1 only, at 5%.

[New wire-observation results](docs/research/wire-observation-results-v0.md) now include independently checked **historical** projections. Public MCP evidence and separate native correlation records remain distinct; no service TTL or prospective admission guarantee is inferred. The [query feasibility audit](docs/research/candidate-query-feasibility.md) rejects a 20% saving claim on the known-task one-query fragment, so the substantive candidate distinction remains under research.

The [original-native reference probe](docs/research/reference-continuation-results-v0.md) verifies an official A2A 0.3 application's reference-dependent follow-up with three source-valid controls and a clean 146-test software/data replay. The [separate disclosed A2A 1.0 port results](docs/research/reference-port-native-results-v1.md) reproduce those controls with raw native checks. The [four whole-interface bridge observations](docs/research/reference-bridge-results-v1.md) now verify typed/Tasks waiting and mgcrea raw completion, with exact archived replay and 205 passing software tests. These are development observations on the disclosed port; method novelty and prospective admission remain unproved. The [next bounded novelty screen](docs/research/reference-novelty-screen-v1.md) preserves those gates and the approved scope.
