# Verified hosted core reproduction

On 10 November 2026, [GitHub Actions run 42819352517](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/42819352517)
at commit `9ef339fa349cf73b6c3558d2c3f51dc967f89444` reproduced the complete
66-profile, four-budget, four-arm development comparison on a fresh Linux
runner. **All 1,056 algorithm outputs, 264 reference outputs and 683 independent
checker outputs matched the retained Windows results**, after excluding the
declared machine-dependent timing/process/resource observations. Complete
solver results, certificates, deterministic statistics and input integrity
matched. This is an observed successful run, not a prospective workflow.

The workflow used Ubuntu 24.04 and Python 3.13.1 with only the standard library.
Its core execution ran from 12:52:00.437875 to 12:54:25.964068 UTC, about 146
seconds. It executed the current tracked code through a captured checkout,
then captured a separate package for each budget's fresh workers. It made
zero live model calls and zero application calls.

## Reproduced certified coverage

Every table cell uses all 66 profiles as its denominator. Certification requires
a valid returned decision and an accepted certificate. An `unknown` result
remains a coverage loss and is never treated as a semantic refutation.

| Work budget | Direct baseline | Goal-pruned direct | Refinement | Shared lifting |
| ---: | ---: | ---: | ---: | ---: |
| 32 | 12 / 66 | 20 / 66 | 24 / 66 | 2 / 66 |
| 256 | 52 / 66 | 54 / 66 | 50 / 66 | 39 / 66 |
| 4096 | 54 / 66 | 54 / 66 | 53 / 66 | 53 / 66 |
| 100000 | 54 / 66 | 54 / 66 | 54 / 66 | 54 / 66 |

At budget 100000, every arm returned 28 supported, 26 unsupported and 12 unknown
results. The fair goal-pruned direct comparator still removes the proposed
shared-lifting coverage advantage. Independently recomputing paired
certification from the downloaded case records gives:

| Budget | Both certified | Direct only | Shared only | Neither |
| ---: | ---: | ---: | ---: | ---: |
| 32 | 2 | 18 | 0 | 46 |
| 256 | 39 | 15 | 0 | 12 |
| 4096 | 53 | 1 | 0 | 12 |
| 100000 | 54 | 0 | 0 | 12 |

Shared lifting adds **zero certified cases beyond goal-pruned direct** at every
tested budget. This reproducible negative comparison is the research result;
the run supplies no evidence of shared-lifting superiority or established
algorithm novelty. Work units remain implementation-defined counters, so
equal budgets do not establish equal CPU effort.

## Independent verification

The local audit checked the exact inventory and SHA256 hashes of **10,821
retained files, totaling 33,707,262 bytes**, both before and after inspection.
The sealed plan matched its recorded hash. Its current-code, test, fixture and
input hashes matched the local checkout bytes. Each of the four trusted local
bundle verifiers exactly reproduced the hosted verifier's output, including
recomputed summaries and dispatch/reply/resource bindings. The audit executed
no downloaded Python code and launched no services or models.

The audit separately compared complete deterministic solver, reference and
checker replies against the SHA256-pinned Windows outputs. It also reran the
trusted pure certificate checker for **all 683 algorithm certificates and 172
reference certificates**. Every check returned exactly `True`, without
mutating its input profile or result.

The captured checkout ran **167 existing tests**, with zero errors, failures or
skips. Their raw unittest summary and process receipt match the driver result.
All nine actual outer commands returned zero. All **2,003 actual matrix
workers** returned zero, with no timeouts. The run was attempt 1; it used no
favorable automatic retry. Historical local fixture-validation failures are
separate from this hosted experiment and are not relabelled as hosted results.

All 2,003 workers retained positive Linux peak-resident observations from
`getrusage(RUSAGE_SELF).ru_maxrss`, converted from KiB to bytes. The Windows
references use `GetProcessMemoryInfo.PeakWorkingSetSize`. These are distinct OS
meters; this result claims no cross-OS equality of timings or memory.
Overlapping timing fields must not be added. Raw observations remain available.

## Retained evidence and reproduction

The compact result is
[download-42819352517-independent-review.json](../../runs/ci-research-core/download-42819352517-independent-review.json).
Its reproducible read-only audit source is
[download-42819352517-audit.py](../../runs/ci-research-core/download-42819352517-audit.py).
The extracted artifact is retained locally at
`runs/ci-research-core/download-42819352517/`, including every worker dispatch,
reply, certificate, binary stdout/stderr stream, process receipt, verifier
output, sealed plan and final hashed manifest. The hosted artifact is named
`research-core-42819352517-1`, GitHub artifact ID `13765264923`, with seven-day
retention. Its reported transport ZIP digest is
`sha256:b6735569ddc6fdcc2806c43e64c1e439cf6342b43bf0d2d2fbe5b5769ab19e4a`;
this audit verifies extracted file bytes directly and does not claim to have
rechecked that transport digest.

The prospective specification is
[ci-research-core-plan-v1.md](ci-research-core-plan-v1.md). A new workflow dispatch
consumes a fresh exclusive output allocation; existing evidence is never
overwritten. Read-only bundle checks use the trusted checkout CLI:

```text
python -I -S -B -c "import sys;sys.path.insert(0,'src');from interoperability.shared_lifting_comparison_v3 import main;raise SystemExit(main(sys.argv[1:]))" verify runs/ci-research-core/download-42819352517/budget-100000
```

This completes a clean cross-OS software reproduction of authored development
results. It does not establish held-out application performance, independent
human task/gold review, task-bank qualification, AP2 execution or publication
readiness. Those claims require their own evidence.
