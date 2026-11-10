# AP2 V9 retained native/bridge analysis

The [V9 analyzer](../../scripts/analyze_ap2_native_bridge_development_v9.py) is
prepared for a real retained allocation. Preparation and constructed checks
create no V9 application result, native qualification or completion credit.

The command accepts a completed run retained by the existing Actions evidence
tool. Its base must be the actual `retained-<run-id>-<attempt>` directory under
the workspace's `runs` directory. Supply its real paths after retention:

```powershell
python -I -S -B scripts/analyze_ap2_native_bridge_development_v9.py --base <actual-retained-v9-base> --output <fresh-workspace-runs-analysis.json>
```

The analyzer verifies saved GitHub run identity, run attempt, repository,
revision and conclusion against the retention receipt and saved artifact API
metadata. It recomputes the archive's size and SHA-256 and requires the exact
GitHub API digest. Selected extracted records must equal their archived bytes.
Before output creation, it checks the actual 104-cell allocation, execution and
evaluation order, all cell indices and identifiers, the public manifest and
current frozen actor/helper/orchestrator/evaluator source fingerprints. A run
conclusion of failure is retained; workflow success alone establishes no result.

All eight arms retain 13 authored cases. The analyzer independently reconstructs
native capture, legal bridge initiation, refusal, missing, partial, purchase,
safety and closed-process totals from the cell records and rejects disagreement
with published evaluator totals. It reports purchases, purchases with no
recorded actor/source error, and purchases also having a zero process return
code and no recorded safety violation separately. None of these indicators is
a full original task grade. A purchase followed by a suffix error remains
visible in the first count.

The 39 bridge slots repeat the initiation prefix across three legal bridge
routes. Verified bridge initiation requires the retained explicit statement
that later OTP and case-specific faults remain unrealized. It never becomes
purchase success, completed bridge continuation or a whole-interface failure
claim. The analyzer rechecks evaluation counts and source/run identities; it
does not replace the independent evaluator's raw semantic checks.

Exactly 65 native case/arm pairs are retained against the fixed, API-bound
[V5 ASGI allocation](../../runs/ap2-reference-development/v5/retained-42881390576-2/retention.json).
The original cases, source pin and five policy-control fields must match.
Comparison is evaluable only when both source-bound captures were independently
verified. Otherwise equality is null and the pair remains unresolved. No timing,
equivalence, causal utility or superiority conclusion follows from matching
purchase indicators in separately executed development allocations.

If smoke fails before matrix execution, analysis retains all 104 missing cells,
zero verified native observations and all 65 non-evaluable pairs. Those missing
cells are not measured zero-percent task-success trials. Actual smoke worker
results are reported separately from the matrix denominator. No V9 run ID is
invented by this guide or analyzer.

The following once-only constructed check reads the retained V8 missing-cell
records and adapts schema labels only in memory to exercise validation:

```powershell
python -I -S -B scripts/analyze_ap2_native_bridge_development_v9.py --self-check
```

It passes one intact denominator control and rejects seven mutations: reordered
or duplicated cell identity, an invented purchase on a missing cell, an invented
closing return code, changed denominator or native/bridge partition, and an
invented aggregate capture. These eight controls are software checks. They
execute no actor, evaluator, solver, provider or application and create no
actual V9 analysis file. The self-check needs the earlier V8 records locally
restored; actual V9 analysis does not depend on those V8 records.

The original 96-task/three-path and 96-crossing study, independently reviewed
gold, full ADK/provider route, canonical original server launcher and final
scientific review remain outside this bounded development analysis.
