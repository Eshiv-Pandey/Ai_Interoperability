# Independent analysis review: 10 November 2026

**Passed** for the final immutable analysis allocation
`runs/research-analysis/v1-20261110-3`.

Independent standard-library logic reconstructed the tables directly from the
four original budget bundles and profile bytes. It did not import or rerun the
analysis generator. All **11,640 table cells** matched: 1,056 case/method rows,
16 budget/method rows, 80 family/method rows and four paired rows. Canonical
UTF-8 JSON proof sizes were recomputed; all **373 unknown rows** correctly retain
blank proof size and zero certification.

The audit rehashed **10,383 manifest-listed files** and checked exact model and
certificate profile bindings. The final allocation's **17 input SHA bindings**,
**seven output SHA/size bindings**, current analysis-script digest, Python3.13.1
version and interpreter path are consistent. The former missing outer-terminal
dependency is now explicitly bound in v3.

The independently computed paired differences and family ranges match within
`1e-12`. The audit used seed1729, 2,000 replicates and five complete-family draws
with replacement. It calculated weighted family totals and used the independent
standard-library inclusive quantile implementation. These ranges describe
exploratory sensitivity to the composition of five existing development
families; they are not population confidence intervals.

| Budget | Both certified | Direct only | Shared only | Neither |
|---:|---:|---:|---:|---:|
| 32 | 2 | 18 | 0 | 46 |
| 256 | 39 | 15 | 0 | 12 |
| 4,096 | 53 | 1 | 0 | 12 |
| 100,000 | 54 | 0 | 0 | 12 |

All four final CSVs are byte-identical to the independently checked v2 CSVs, and
all 16 original raw-input bindings are unchanged. Numerical checks were reused
only after those identities were established. The previous v2 review remains
preserved separately.

Visual inspection of the PNG confirmed readable method labels, correct values,
units and denominators. Work/proof/family bar axes are linear and start at zero;
the coverage line uses a logarithmic work-allowance axis. The final PNG is
byte-identical to the inspected PNG, and the SVG differs only in its date
metadata. Final SVG labels/numeric bar values also match. PDF/SVG file hashes are
bound; the PDF was not separately rendered in this audit.

No numerical, proof-size, resampling or figure-label discrepancy remains. The
analysis correctly reports adverse shared-lifting coverage/work results and
does not establish novelty, speed superiority or held-out generalization.

The [machine-readable review](../../runs/research-analysis/independent-review-v1.json)
contains identities, exact checks, family parameters and final output bindings.
