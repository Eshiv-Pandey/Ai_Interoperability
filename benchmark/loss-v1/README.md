# Agent handoff benchmark development release

This release implements six measurement areas: task completion, context
retention, required capability usability, constraint/tool fidelity, recovery
success and a separate overhead vector. It includes a runnable finite Python
diagnostic and a byte-preserving retained-input corpus. It does not claim a new
algorithm, a qualified full study, or general model/protocol performance.

## Results available today

- 80 fresh constructed episodes: ten authored tasks, eight conditions each.
  These execute a deterministic Python receiver and injected faults, not native
  MCP/A2A services or an LLM.
- 13 separately labelled historical observations: original/reference Carol,
  its disclosed A2A 1.0 port, pinned Amir/mgcrea bridges, and original AgentOps
  confirmation-double diagnostics. Some native rows are deliberate negatives.
- 68 passing software tests; one symlink-creation test is skipped on this host.
- Independent finite trace regrading, exact result regeneration and 106 pinned
  retained inputs. The portable inputs total 2,866,511 bytes.

The main [supervisor report](../../docs/research/loss-benchmark-supervisor-report-v1.md)
explains results and limitations. The [Word report](../../reports/loss-benchmark-supervisor-v1.docx)
contains the same summary and result tables. The [definitions](../../docs/research/loss-benchmark-metrics-v1.md)
state denominators, unknowns and observation scopes. The final retained rows and
fresh traces remain separate in the [final allocation](../../runs/loss-benchmark-v1/fresh-development-003/).

## Setup and run

Python 3.12 or later is required for this benchmark release, including the
exporter's Windows junction checks. From a new checkout on Windows:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e .
.venv/Scripts/python.exe -B scripts/run_loss_benchmark_v1.py --output runs/loss-benchmark-v1/my-unused-output --retained runs/loss-benchmark-retained-v1/20261112T112741770806Z-3326eed1/episodes.json
```

The project has no runtime dependencies for this benchmark. Linux uses
`.venv/bin/python` instead. Choose a new output directory; old allocations are
preserved. `fresh-results.json` summarizes the fresh conditions, while
`combined-episodes.json`, `metrics-summary.json` and `cells/` retain all scores
and traces. Different evidence kinds and unrelated retained families have no
pooled performance score.

To verify the final allocation and rebuild historical rows from the portable
raw-input mirror:

```powershell
.venv/Scripts/python.exe -B scripts/verify_loss_benchmark_v1.py --bundle runs/loss-benchmark-v1/fresh-development-003 --retained runs/loss-benchmark-retained-v1/20261112T112741770806Z-3326eed1/episodes.json --output runs/loss-benchmark-v1/my-unused-verification --run-tests
```

No service or provider call occurs. This checks retained data; it is not a
fresh reproduction of the original upstream applications.

The five software suites also passed in a temporary checkout containing only
the portable raw-input mirror: 68 passes and one symlink-creation skip. The
[receipt](../../runs/loss-benchmark-v1/mirror-only-tests-001/result.json) records
the tested file hashes and confirms that original raw paths were absent.

## Research work remaining

Human task/gold review, fresh qualified real routes, untouched evaluation
cases, closest-work comparison and a final scientific review remain open.
Fresh diagnostic outcomes establish software behavior under declared finite
rules. They do not establish population prevalence, causal loss attribution,
generalization or publication readiness.
