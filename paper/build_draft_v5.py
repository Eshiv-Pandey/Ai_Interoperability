"""Build the next manuscript from preserved v4 and verified supplemental results."""
from pathlib import Path
import hashlib
import json
import re
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]


def record(name):
    data = (ROOT / name).read_bytes()
    return {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def build():
    text = (ROOT / "paper/working-draft-v4.md").read_text(encoding="utf-8")

    def replace(old, new):
        nonlocal text
        if text.count(old) != 1:
            raise ValueError("Expected one preserved fragment: " + old[:90])
        text = text.replace(old, new, 1)

    def section(start, end, new):
        nonlocal text
        a, b = text.index(start), text.index(end)
        text = text[:a] + new.strip() + "\n\n" + text[b:]

    section("Research manuscript, version 4", "## Abstract", """
Research manuscript, version 5, 10 November 2026. This version adds the
separately executed constraint-pruned comparator, refreshed primary-source
references and original AP2 application development execution. The registered
task-relative research scope and title are preserved. All empirical claims
refer to the retained finite models or explicitly intervened application
fixtures; independent held-out application gold and live-model utility remain
unestablished.
""")
    section("## Abstract", "## 1. Introduction", """
## Abstract

An accepted protocol message need not preserve the operations required to finish
an agent's original task. We implement bounded task-relative continuation
admission with three-valued decisions and independently checked positive and
complete-model negative certificates. A shared-lifting adaptation caches exact
prefixes and complete relation expansions while preserving correlated binding
frames, uncertainty and witness history. The original four-method development
matrix contains 66 authored profiles at four declared work allowances. A
separate conventional constraint-pruning experiment adds a fifth method on
identical profiles, producing 1,320 analyzed cells. At allowance 256, shared
lifting certifies 39/66 profiles; both goal-pruned and constraint-pruned direct
search certify 54/66. At allowance 100,000, all five methods certify the same
54 profiles. On a reconvergence stress case, relation checks fall from 1,024
to 16, but charged work rises from 5,566 to 14,773 and the 8,895-byte proof is
unchanged. A separately audited Linux reproduction matches the original
deterministic matrix. Original AgentOps confirmation tasks complete through
native and admitted bridge routes with one attributed effect each. A separate
original AP2 development sequence resumes its merchant and processor tasks to
a corresponding demo Success receipt under offline-model and ASGI interventions.
These results establish reproducible adverse evidence for the implemented cache
and proof representation, and separate model-relative admission from actual
task effects and observation completeness. They do not establish algorithmic
superiority, native AP2 qualification or held-out live-model generalization.
""")
    replace("a same-input four-method comparison with raw evidence and cross-platform", "a same-input four-method comparison and separately executed fifth comparator\nwith raw evidence and cross-platform")
    replace("The references retain previously inspected versions and metadata. This draft\nchecks citation coverage and local provenance structurally; it does not claim\na fresh exhaustive literature search, an independent reproduction of prior\nsystems or human approval of the contribution.", """The refreshed primary-source assessment adds the original CEGAR [19], relation
consistency [20], memo-functions [21] and bounded-model-checking [22] references.
The candidate follows the established abstract-path/concrete-check/refinement
pattern; the shared cache instantiates ordinary memoization. Constraint pruning
rejects partial assignments only after required guard dependencies are known
and a guard is definitely false. It does not implement AC-3 propagation or a
general CSP solver. The horizon bounds modeled steps; the work allowance can
instead cause unknown. None of these adaptations establishes a new general
verification principle. The bounded source assessment refreshed 22 identities
and retained failed retrievals and metadata gaps. It is an AI assessment, not an
exhaustive systematic review, prior-system reproduction or human contribution
approval.""")
    replace("All four experimental arms receive the refined recipe profile.", "All five experimental methods receive the same refined recipe profile.")
    replace("outside this\nfour-method matrix", "outside both\nfull-recipe experiments")
    section("### 4.2. Original witness", "### 4.3. Shared lifting", text[text.index("### 4.2. Original witness"):text.index("### 4.3. Shared lifting")].strip() + """

The separately executed constraint-pruned direct successor uses the same product
search and proof checker as its disclosed direct baseline, but enumerates
argument domains with conservative dependency-aware guard pruning. Only a
definitely false guard whose argument dependencies have already been assigned
can suppress a partial branch. Complete surviving tuples pass through the
unchanged relation interpreter. Unknown guards do not justify suppression.
Its additional indexing and guard work are charged explicitly. The experiment
tests a conventional optimization, not a new relation-consistency algorithm.
""")
    replace("The comparison captures selected solver and checker modules and profile bytes\nprospectively; executed evidence is preserved in exclusive versioned allocations.", """The comparison captures selected solver and checker modules and profile bytes
prospectively; executed evidence is preserved in exclusive versioned allocations.
The separate fifth-method experiment uses those exact profiles, clock and
horizon, with the original legal recipe interpreter and negative checker.
Its fresh legacy baseline matches all 264 preserved baseline outputs. This
supplement was declared after the original study and is reported as such;
it is not a fifth arm retroactively inserted into the original allocation.""")
    replace("There are 373 unknown algorithm rows. No worker error, timeout, rejected\ncertificate or input/source mutation was recorded in that matrix.", """There are 373 unknown algorithm rows. No worker error, timeout, rejected
certificate or input/source mutation was recorded in that matrix. The separate
Linux supplement contributes 264 comparator cells and 88 unknowns. The combined
analysis therefore retains 1,320 cells and 461 unknowns. Its 1,140 worker
dispatches include a fresh baseline and references, not 1,140 comparator tasks.
A prior Windows supplemental attempt timed out in a reference worker; that
failed allocation remains retained and is not included as a successful matrix.""")
    replace("## 7. Four-method results", "## 7. Five-method development results")
    replace("Table 1 reports the complete matrix.", "Table 1 reports the original matrix and separately executed fifth comparator.")
    replace("| Work allowance | Legacy direct | Goal-pruned direct | Original refinement | Shared lifting |\n| ---: | ---: | ---: | ---: | ---: |\n| 32 | 12/66 | 20/66 | 24/66 | 2/66 |\n| 256 | 52/66 | 54/66 | 50/66 | 39/66 |\n| 4,096 | 54/66 | 54/66 | 53/66 | 53/66 |\n| 100,000 | 54/66 | 54/66 | 54/66 | 54/66 |", """| Work allowance | Legacy direct | Goal-pruned direct | Original refinement | Shared lifting | Constraint-pruned direct |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 32 | 12/66 | 20/66 | 24/66 | 2/66 | 14/66 |
| 256 | 52/66 | 54/66 | 50/66 | 39/66 | 54/66 |
| 4,096 | 54/66 | 54/66 | 53/66 | 53/66 | 54/66 |
| 100,000 | 54/66 | 54/66 | 54/66 | 54/66 | 54/66 |""")
    replace("| Shared lifting | 46,840 | 27,248 | 8,895 |", "| Shared lifting | 46,840 | 27,248 | 8,895 |\n| Constraint-pruned direct | 4,186 | 19,880 | 893 |")
    replace("All 54 high-allowance shared certificates", """Constraint pruning adds no certified case beyond goal-pruned direct at any
tested allowance. At 100,000 it charges 4,186 units versus 3,382, with the
same aggregate proof size of 19,880 bytes. This suite supplies no aggregate
efficiency advantage for either shared lifting or constraint pruning.

All 54 high-allowance shared certificates""")
    section("![Four-method development", "### 7.3. Timing", """
![Five-method development comparison](../runs/research-analysis/v2-20261110-3/development-comparison-five-arm.png)

**Figure 1.** A: certified coverage at four categorical work allowances. B:
charged solver work across all 66 attempts at allowance 100,000. C: canonical
JSON proof bytes for the 54 certified profiles per method. D: coverage within
the five authored families at allowance 256 for goal-pruned direct, shared
lifting and constraint-pruned direct. Every quantitative y axis starts at zero.
The first four methods retain Windows observations; the fifth is a separate
Linux supplement. Timing and OS memory are not compared. SVG and PDF exports
and an exact profile/clock join ledger accompany the figure.
""")
    replace("### 7.4. Supplementary abstraction-only control", """The separate constraint-pruning capture at commit
`d341909ff1ccb1ce641e4eab63699bd4ff2cc671` passed 13 adversarial/differential
tests. Its retained-evidence audit checked 6,228 manifest-listed files,
1,140 dispatches and independently rechecked all 348 baseline/comparator
certificates. A separate AI challenge review examined 200 additional relations
with 4,688 complete domain tuples; every one of the 3,281 omitted tuples was definitely
false under the original interpreter. These are bounded implementation checks,
not additional application tasks or human scientific approval.

### 7.4. Supplementary abstraction-only control""")
    section("### 8.3. AP2 and corpus", "### 8.4. Executed AP2", """
### 8.3. Original AP2 development sequence and corpus boundary

Hosted run [42845852651](https://github.com/Eshiv-Pandey/Ai_Interoperability/actions/runs/42845852651)
imports all three original AP2 peer applications and the original shopper tools.
Original SDK request handlers, task stores, checkout construction, signing and
credential association execute as reached, with 136 original source files
unchanged. Bounded offline model responses replace provider generation; HTTPX
uses an owned ASGI transport to the local original apps. A portable owned-helper
validator, recursive structural callable comparison, explicit model projection
and a plain coordinator state carrier are further disclosed adaptations.
The SDK's mandate log is redirected to a private temporary location.

The coordinator chooses only publicly returned carts and payment aliases,
approves the actual checkout summary and responds to the original public demo
OTP challenge. It resumes the same original merchant task, retaining the nested
processor task separately. Original checkout, mandates and receipt values are
generated by the application. The observed Success receipt agrees across the
processor, merchant, caller and credential-provider delivery; its transaction
reference is independently recomputed. This is a demo receipt, not evidence of
a real financial settlement or purchase outside the sample.

The read audit checks 168 durable events, 17 raw exchanges and 12 RPC requests.
It verifies resumed task/context continuity, receipt correspondence and cleanup.
A separate audit checks 167 retained files, 1,617 imported runtime bindings and
64 structural callable checks. Captured buyer-root ES256 signatures and
disclosure hashes pass fresh checks; altered signatures and an unrelated public
key are rejected. The merchant checkout signature is not independently checked
because its public key was not captured. No legal-identity or complete mandate
policy qualification follows from those signature checks.

Earlier hosted allocations failed at callable fingerprinting, model projection
and pending-state comparison. Their exact sources and partial raw records remain
preserved. Successor changes affect the owned runner/adapters; no failed result is erased.
The successful v3 sequence has zero provider requests and no admission gate.
The v4 successor adds shared-lifting admission before the original OTP send;
constructed controls exist, but no original v4 execution is claimed here.
This development sequence does not qualify native TCP, the unchanged provider
router, a benchmark gold task or two-domain held-out utility.

The structurally complete banks contain 68 candidates: 34 AgentOps and 34 AP2,
each allocated as six development, four calibration and 24 prospective held-out
records. AP2 combines 28 workflow candidates and six source-boundary candidates.
These records are distinct from the 66 finite development profiles. Structural
validation and AI crossreviews do not supply independent human-approved gold or
untouched holdout, and the bank does not enlarge Tables 1 to 5. The six AgentOps
development receipts currently validate original read components only: none
completes its governed App task, and all six whole-task outcomes remain unknown.
""")
    replace("The complete Windows matrix and Linux reproduction made no application or live\nmodel calls. The separate AgentOps integration made no live model calls.", "The finite matrices and Linux reproduction made no application or live\nmodel calls. AgentOps and AP2 development integrations made no live model calls.")
    replace("a [versioned artifact guide](../docs/research/paper-artifact-guide-v4.md)", "a [versioned artifact guide](../docs/research/paper-artifact-guide-v5.md)") if "a [versioned artifact guide](../docs/research/paper-artifact-guide-v4.md)" in text else None
    text = text.replace("paper-artifact-guide-v4.md", "paper-artifact-guide-v5.md")
    replace("structurally checked. The literature was not refreshed online for this draft.",
            "structurally checked. Twenty-two identities were refreshed against primary\nsources for this version, with retrieval failures and metadata gaps retained.")
    replace("expected effect with clean lifecycle evidence. These are concrete, verified", "expected effect with clean lifecycle evidence. An explicitly intervened original\nAP2 sequence resumes both tasks to a corresponding demo Success receipt.\nThe separate fifth comparator reinforces the adverse aggregate result.\nThese are concrete, verified")
    bibliography = (ROOT / "paper/references-v3.md").read_text(encoding="utf-8")
    entries = [line for line in bibliography.splitlines() if re.match(r"^\d+\. ", line)]
    text = text[:text.index("## References")] + "## References\n\nThe numbered references preserve inspected identities and unresolved metadata\nin [references-v3.json](references-v3.json). The primary-source assessment is\nbounded and AI-authored; prior-system reproduction and human review are open.\n\n" + "\n\n".join(entries) + "\n"
    return text


if __name__ == "__main__":
    output = ROOT / "paper/working-draft-v5.md"
    if output.exists():
        raise SystemExit("Choose a new version rather than overwrite a built draft")
    output.write_text(build(), encoding="utf-8", newline="\n")
    print(json.dumps({"draft": record("paper/working-draft-v5.md"), "built_utc": datetime.now(timezone.utc).isoformat()}))
