# Load the original AgentOps evaluation cases

The [versioned loader](../../src/interoperability/upstream_agentops_cases_v1.py)
exports the acquired upstream AgentOps case data with application inputs and
evaluator expectations in separate files. It uses the retained
[source-ingestion record](source-evidence/agentops-local-archive-v1/ingestion.json)
to verify seven selected files: the three evalsets, `agents/LICENSE`, the SQLite
seed, `schema.sql` and `seed.sql`. No original source is changed or imported,
and no SQL, application, model or grader is executed.

The source files contain 15 core cases, three structured-report cases and three
workflow cases. The core memory case has two turns. These are **public,
source-derived development inputs**, with overlapping incidents, tools and
decision structures. They are not 21 independent templates, hidden gold, a
held-out split, human-reviewed tasks or observed task outcomes. Archive labels
and matching local hashes do not independently authenticate Git objects.

From the project root, use Python 3.11 or later and a new output directory:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location).Path 'src'
python -B -m interoperability.upstream_agentops_cases_v1 --source-root external/agentops-c806b7f1 --capture-root docs/research/source-evidence/agentops-local-archive-v1 --output runs/upstream-agentops-cases/v2
```

The proposed `v2` allocation is unused at this update; check it before use.
Inspect `result.json`; `status: passed` means the data export and preservation
checks passed. It does not mean any task or admission decision passed.
Existing outputs, including failed exports, are refused. Output must be outside
the source and capture trees. Once an allocation exists, choose another path.

| Export path | Contents and intended consumer |
| --- | --- |
| `application/cases.json` | Original eval-set/case IDs, session inputs, creation timestamps and every original user turn in order. Supply only this input projection to a future application runner. |
| `evaluator/expectations.json` | The corresponding original reference responses and expected tool trajectories, with invocation IDs and timestamps. Keep this projection on the evaluator side. |
| `source/` | Unchanged bytes of the seven verified source files, including full evalsets and their expectations. This archive is not an application input. |
| `source-sets.json` | Original eval-set metadata and source names. |
| `capture/ingestion.json` | The unchanged retained ingestion record used for verification. |
| `plan.json`, `result.json` | Explicit roots, selected sources, implementation hash, per-file checks, counts, preservation checks and file hashes. A failed attempt retains its plan, error and any completed captures. |

Do not hand the full export directory to an admission procedure: the source
archive itself contains reference answers. Separation here is an explicit
runtime-input contract, not a confidentiality claim about publicly available
upstream data. No expected response or trajectory field is copied into the
application projection.

The loader accepts the current text-only source format. It rejects unknown
fields, duplicate JSON keys, duplicate case IDs across selected sets, repeated
invocation IDs within a case, malformed roles/parts/trajectories, nonfinite
numbers, selected-source hash drift, links/reparse points, missing selected
files and additional `*.evalset.json` files. Other upstream documentation and
implementation files remain outside this selected export. New source formats
or evalsets require an explicit loader change rather than silent omission.

The [focused tests](../../tests/test_upstream_agentops_cases_v1.py) use temporary
loader-format fixtures, including distinct expectation sentinels, a multi-turn
case, rehashed malformed inputs and mutations during export. They do not
constitute an export or evaluation of the real upstream cases. Run them with:

```powershell
python -I -S -B -m unittest discover -s tests -p test_upstream_agentops_cases_v1.py -v
```

## Completed export and validation: 29 October 2026

The consumed [v1 export](../../runs/upstream-agentops-cases/v1/result.json)
passed with **21 cases and 22 user turns**, all seven selected sources matching
the original ingestion record. Original and captured sources, projections and
the export plan stayed unchanged. It made zero application or model calls.

Captured-source software validation ran eleven tests, all OK with zero skips.
The [raw process record](../../runs/upstream-agentops-cases/software-v1/result.json)
has exit code 0 but its recorder incorrectly labelled the run failed while
matching an LF-only success string against Windows CRLF output. The original
record is preserved. The separate [assessment](../../runs/upstream-agentops-cases/software-v1-assessment.json)
reads the retained output without rerunning tests and records the passing result.
The [independent AI audit](../../runs/upstream-agentops-cases/v1-independent-review.json)
confirmed exact reconstruction of the application/evaluator projections and
metadata, all twelve manifest entries, thirteen export files and seven software
files. All 33 monitored files remained unchanged. It also confirmed the passing
software assessment and the CRLF/LF mismatch; this is not human acceptance.

The exported [application inputs](../../runs/upstream-agentops-cases/v1/application/cases.json)
are ready for a separately reviewed native runner. This data-export result is
not an executed external benchmark, a task-effect grade or domain qualification.

The original `restart-needs-approval` and `resolve-needs-approval` cases stop
at a confirmation request. The upstream evaluator's nonempty-response and
tool-order checks do not prove original A2A-task completion or an attributed
effect. A future application benchmark still needs a reviewed public-evidence
and state-grading contract, a fresh native prerequisite, original-task/effect
checks, a qualified procurement domain and actual independent human review.
The existing [authored four-arm benchmark](shared-lifting-comparison-v3.md)
retains its original input/provenance restrictions; this loader does not
relabel these external cases to enter that benchmark.
