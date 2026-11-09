"""Create one new results note from the retained, verified matrix."""
import json
from pathlib import Path

RUN = Path(__file__).resolve().parents[1]
ROOT = RUN.parents[2]
review = json.loads((RUN / "post-review/result.json").read_bytes())
matrix = json.loads((RUN / "result.json").read_bytes())
assert review["status"] == "verified" and matrix["status"] == "passed"
budgets = (32, 256, 4096, 100000)


def decisions(value):
    return "/".join(str(value.get(key, 0)) for key in ("supported", "unsupported", "unknown"))


def coverage(value):
    return f"{value['certificates_valid']}/66 ({100 * value['certified_coverage']:.1f}%)"


lines = [
    "# Refinement development scaling results, v1", "",
    "The implemented generator and benchmark completed 66 authored profiles at four fixed work allowances, using identical profile bytes, logical clock 100 and one frozen package for both solvers and the reference. All four benchmark bundles passed the existing CLI verifier. A separate reconciliation checked all 1,145 worker jobs and all bundle hashes; measured artifacts remained unchanged.", "",
    "Every conclusive result below has an independently accepted certificate: 353 checks total, zero rejections, zero checker errors/exhaustions, and no failed/timed-out or input-mutating workers. These are development results; they add no held-out cases, application-domain qualification or novelty evidence.", "",
    "## Overall outcomes", "",
    "S/U/? means supported/unsupported/unknown. Certified coverage counts only checker-accepted conclusive results, with all 66 cases as the denominator.", "",
    "| Work allowance | Direct S/U/? | Candidate S/U/? | Direct certified coverage | Candidate certified coverage |",
    "| ---: | ---: | ---: | ---: | ---: |",
]
for budget in budgets:
    row = review["budgets"][str(budget)]["algorithms"]
    lines.append(f"| {budget:,} | {decisions(row['baseline'])} | {decisions(row['candidate'])} | {coverage(row['baseline'])} | {coverage(row['candidate'])} |")
lines += ["", "At 100,000 units, both implementations match all 66 authored sufficient-budget expectations: 28 supported, 26 unsupported and 12 unknown. The 12 unknown profiles retain opaque relations; expected labels are authored finite-semantic assertions, not application gold.", "",
          "At allowance 32, 12 candidate certificates were accepted while the budgeted reference/direct solver abstained; at 256 this occurred twice. Those reference abstentions remain unknown. Conversely, the candidate abstained on four reference-decided cases at 256 and one at 4,096. Expected labels, budgeted reference decisions and independent certificate acceptance remain separate in the retained case records.", "",
          "## Outcomes by family", "",
          "Each cell lists `direct S/U/?; candidate S/U/?`. All S and U counts in this table are certificate-validated.", "",
          "| Family (cases) | Allowance 32 | Allowance 256 | Allowance 4,096 | Allowance 100,000 |",
          "| --- | --- | --- | --- | --- |"]
names = {"argument_product": "Argument product", "layered_reconvergence": "Layered reconvergence",
         "correlated_frames": "Correlated frames", "horizon_boundary": "Horizon boundary", "off_goal_load": "Off-goal load"}
for family, label in names.items():
    cells = []
    count = None
    for budget in budgets:
        value = review["budgets"][str(budget)]["families"][family]
        count = value["baseline"]["cases"]
        cells.append(decisions(value["baseline"]["decisions"]) + "; " + decisions(value["candidate"]["decisions"]))
    lines.append(f"| {label} ({count}) | " + " | ".join(cells) + " |")
lines += ["", "## Two mechanism differences", "",
    "- **Reconvergent refutation, scale-0031:** width four and depth four create 256 abstract paths to a false final relation. At allowance 4,096, the direct solver certifies unsupported while the candidate exhausts its budget. At 100,000, both certify unsupported; the candidate records 256 lifted paths, 256 refinements and 1,024 relation checks, while the direct solver records four product states and 16 argument assignments.",
    "- **Off-goal work, scale-0064:** four dead branches each contain a 16-assignment product, followed by a separate goal edge. At allowance 256, the candidate certifies supported while the direct solver exhausts its budget. At 100,000, both certify supported; the candidate records one relation check while the direct solver records 65 argument assignments.", "",
    "These results expose different costs of lazy path lifting and shared relational search. Equal integer allowances charge different internal operations, so the counters are not interchangeable primitive costs. Both favorable and unfavorable candidate cases are retained. Other root live-work may have contended for CPU; no wall-clock speed superiority is claimed. All evaluation, startup and certificate-check timings remain in the raw summaries, including every abstention and all reference invocations. The reference and direct baseline are the same implementation.", "",
    "## Retained evidence", "",
    "- [Prospective matrix plan](../../runs/refinement-scaling/v1/plan-v2.json) and [frozen inputs/labels manifest](../../runs/refinement-scaling/v1/inputs/manifest.json). All four budget allocations and package hashes were fixed before evaluation.",
    "- [Complete matrix results](../../runs/refinement-scaling/v1/result.json), including per-family reasons, per-case counters, checking costs and raw evidence references.",
    "- [Reconciliation result](../../runs/refinement-scaling/v1/post-review/result.json), with exact before/after inventories beside it. This was an AI evidence review, not human review.",
    "- Raw verified summaries: [32](../../runs/refinement-scaling/v1/budget-32/summary.json), [256](../../runs/refinement-scaling/v1/budget-256/summary.json), [4,096](../../runs/refinement-scaling/v1/budget-4096/summary.json), [100,000](../../runs/refinement-scaling/v1/budget-100000/summary.json).", ""]
target = ROOT / "docs/research/refinement-scaling-results-v1.md"
with target.open("x", encoding="utf-8", newline="\n") as handle:
    handle.write("\n".join(lines))
print(target)
