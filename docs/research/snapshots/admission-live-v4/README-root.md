# Agent interoperability research

**Supervisor review: 31 October 2026.** This week's priority is the implemented admission algorithm and benchmark; no draft paper is required. Start with the [eight-minute supervisor guide](docs/research/supervisor-package-v1.md), [three-day checklist](docs/research/three-day-implementation-plan-v2.md) and [component status](docs/research/implementation-status-v1.json). The target is 70%; reaching it remains unverified, and no extension has been granted.

**Algorithm and benchmark (29 October):** the refinement candidate constructs concrete request witnesses and checked negative certificates, with unknowns retained. Its [ten-command demonstration](docs/research/implementation-demo-v1.md) passed. The stronger [versioned comparison](src/interoperability/direct_comparison_v2.py) adds goal-pruned direct search on the same recipe input; [21 focused tests passed](runs/direct-comparison-software/windows-v1/result.json), including captured-code replay. The [fairness review](docs/research/direct-goal-pruning-fairness-v2.md) records unnecessary off-goal work in the original comparator. The [66-case, four-budget comparison](docs/research/refinement-scaling-results-v2.md) completed with 1,591 worker invocations and 535 accepted certificate checks. The candidate does not consistently outperform corrected direct; all three methods agree at the largest budget.

**Latest live integration (29 October):** the public-state adapter, guarded controller and admitted client are implemented. Frozen validation passed **146 Python and 26 Node tests**. The [latest native prerequisite](docs/research/pending-admission-live-results-v2.md) timed out before service readiness and client launch; B7 was skipped. Reaping and empty-group cleanup were verified, and the original host configuration was restored. Fresh live admission remains unverified. The next startup diagnostic pipeline is reviewed and ready, but a [WSL no-op probe](runs/agentops-admission-execution/v4-resource-probe/result.json) failed for insufficient host resources before any new application launch.

**Diagnostic follow-up (28 October):** [v12 results](docs/research/agentops-bridge-diagnostic-results-v12.md) verify N11 and explicitly header-configured B7 strict success with clean exits. B6 remains semantically partial; all three shutdown diagnostic captures are complete. The parent checker verified 2,617 exported files. The earlier B7 failure did not reproduce; no cause or repair is established. V10 outcomes stay unchanged. Do not rerun the consumed v12 allocation.

The [supervisor package](docs/research/supervisor-package-v1.md) leads with the implemented algorithm and current comparison. Older visual replays and protocol controls remain supporting historical evidence; they do not establish a fresh admitted application run.

**Current evidence (28 October 2026):** the [checked v10 bridge/native results](docs/research/agentops-bridge-results-v10.md)
account for all 18 planned controls: **18 executed,
0 skipped and 0 unexecuted**. Executed cases
contain 4 strict successes,
11 complete recorded non-successes and
3 unknown or partial outcomes. The parent
check verifies 2,371 exported files. All **128 preparation
tests pass**. Skips, partial records and fixed-policy non-successes do not prove
whole-interface non-support; configured header behavior remains separately labelled.
**Do not rerun or silently resume the v8/v9/v10 groups.** Historical attempts
and seals are retained.

The [callsite-factoring method screen](docs/research/c1-callsite-factoring-screen-v1.md)
finds no construction beyond the strong shared-summary comparator. CP1 passed;
**CP2 remains open and verified progress stays 5%**. The distinct method,
substantive second domain, reviewed corpus, frozen evaluations, independent
reproduction, actual human review and complete paper remain required.

**Supervisor implementation review: 31 October 2026.** Paper work is deferred this week; no time extension is yet granted. The [implementation plan](docs/research/implementation-plan-v4.md)
preserves the full approved scope. Next work must resolve substantive method and
qualification gaps; another source audit or integrity pass cannot pass CP2.



Registered project: **Benchmarking Framework for LLM-Based Agent Interoperability: Measuring Interoperability Loss Across Heterogeneous Agent Boundaries**.

Approved workflow v1 studies task-relative continuation admission across pinned MCP/A2A bridge routes. The current code includes a **recipe-refinement admission candidate, direct comparator, independent checker and executed development benchmark**. A novel candidate advantage, faithful live admission, qualified domains and reviewed held-out results remain to be demonstrated. Paper work is deferred this week. No fabricated experimental results are included. All model access and token quotas remain unconfirmed.

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
