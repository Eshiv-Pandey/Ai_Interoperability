# Reproducible development-result analysis v1

This is an exploratory analysis of already observed 66-profile development
results. It does not add held-out tasks or prospectively select a favorable
sample. Use all four original budgets and all four methods, retaining unknowns
and failures in their original denominators.

Regenerate case-level method tables, budget and family aggregates, paired
shared-lifting versus goal-pruned-direct certification counts, canonical proof
bytes and solver work totals. Work units remain method-specific operations;
proof size includes only certified decisions and records unknown proof size as
missing. Timing observations do not support speed rankings.

As exploratory dependency sensitivity, resample complete development families
2,000 times using seed 1729; preserve every profile and both method outcomes
inside each sampled family. Report a 2.5th-to-97.5th percentile sensitivity
range for paired certification difference. This is sensitivity to the existing
family mixture, not a population confidence interval or new independent data.

Verify the retained bundle manifests and derived totals before export. Retain
input/output hashes, script identity, dependency versions, all CSV tables and
Matplotlib PNG/PDF/SVG figures in a new unused allocation. Run no solver,
archived source, application or model during this analysis.
