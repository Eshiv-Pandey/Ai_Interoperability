"""Bind manuscript v5 to the actual retained result files, without running experiments."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]


def record(name):
    data = (ROOT / name).read_bytes()
    return {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


CLAIMS = [
    ("V5-01", "3-5", "Conditional finite semantics, checked certificates and the preserved four-arm findings.",
     ["paper/claim-ledger-v4.json", "paper/draft-audit-v4-6.json", "paper/working-draft-v4.md"],
     "Conditional on supplied finite relations; no real-route closure theorem."),
    ("V5-02", "6-7; Tables1,3", "1320 cells,461 unknowns; separate constraint-pruned comparator adds no certified case over goal-pruned direct.",
     ["runs/research-analysis/v2-20261110-3/case-methods.csv", "runs/research-analysis/v2-20261110-3/budget-methods.csv",
      "runs/research-analysis/v2-20261110-3/join-ledger.csv", "runs/research-analysis/v2-20261110-3-independent-review.json",
      "runs/guard-pruned-comparison/independent-capture-audit-42836579527.json", "docs/research/guard-pruned-comparison-results-v3.md"],
     "Fifth method is separately executed; authored dependent development profiles; charges are method-specific."),
    ("V5-03", "Figure1", "Five-method scientific figure derives from the full retained matrix with zero-origin quantitative y axes.",
     ["runs/research-analysis/v2-20261110-3/result.json", "runs/research-analysis/v2-20261110-3/development-comparison-five-arm.png",
      "runs/research-analysis/v2-20261110-3/development-comparison-five-arm.svg", "runs/research-analysis/v2-20261110-3/development-comparison-five-arm.pdf"],
     "No CPU or OS memory ranking; family ranges remain exploratory."),
    ("V5-04", "7.3", "Supplemental13 controls,1140 dispatches,348 rechecked certificates; challenge review4688 tuples/3281 definitely-false omissions.",
     ["runs/guard-pruned-comparison/independent-capture-audit-42836579527.json", "runs/guard-pruned-review/v3-20261110-2/result.json"],
     "Bounded software and AI review; not human method approval."),
    ("V5-05", "8.3", "Original AP2 v3 resumes merchant/processor tasks and returns corresponding demo Success receipt;168 events/17 exchanges/12 requests.",
     ["runs/ap2-reference-development/v3/semantic-analysis-42845852651/result.json",
      "runs/ap2-reference-development/v3/hosted-42845852651-independent-review.json", "docs/research/ap2-reference-development-v3.md"],
     "Offline model/ASGI/owned-helper interventions; zero providers; no native qualification or admission gate in v3."),
    ("V5-06", "8.3", "AP2 captured buyer-root signatures checked; merchant signature not checked; six AgentOps whole-App tasks remain unknown.",
     ["runs/ap2-reference-development/v3/hosted-42845852651-independent-review.json", "docs/research/agentops-reference-development-results-v1.md"],
     "Not legal identity, financial settlement, full mandate policy or application gold qualification."),
    ("V5-07", "2;References", "22 inspected bibliography identities and classical mechanism attribution.",
     ["paper/references-v3.json", "paper/references-v3.md", "paper/references-v3.bib", "paper/bibliography-audit-v3-2.json", "docs/research/final-literature-review-v1.md"],
     "Bounded primary-source/AI assessment; not exhaustive search, prior-system reproduction or new algorithm proof."),
]


if __name__ == "__main__":
    now = datetime.now(timezone.utc).isoformat()
    ledger = {"schema_version": "working-paper-claim-ledger/5", "created_utc": now,
              "draft": record("paper/working-draft-v5.md"), "artifact_guide": record("docs/research/paper-artifact-guide-v5.md"),
              "builder": record("paper/build_draft_v5.py"), "paths_relative_to": "repository_root",
              "title_preserved": True, "human_scientific_review_claimed": False,
              "claims": [{"id": cid, "section": section, "statement": statement,
                          "evidence": [record(name) for name in files], "limits": [limit]}
                         for cid, section, statement, files, limit in CLAIMS]}
    status = {"schema_version": "working-paper-draft-status/5", "created_utc": now,
              "document": "paper/working-draft-v5.md", "prior_version": "paper/working-draft-v4.md",
              "full_manuscript_drafted": True, "publication_ready": False,
              "original_research_validity_gates_complete": False, "title_preserved": True,
              "human_scientific_review_claimed": False, "claim_ledger": "paper/claim-ledger-v5.json",
              "artifact_guide": "docs/research/paper-artifact-guide-v5.md", "references": 22,
              "finite_algorithm_cells": 1320, "unknown_cells": 461,
              "original_AP2_v3_offline_sequence_observed": True, "AP2_v4_original_admitted_execution_claimed": False,
              "new_application_or_provider_calls_for_drafting": 0, "verification": "pending",
              "remaining": ["Accountable scientific/claim review", "Full route/model qualification",
                            "Independent whole-task gold and held-out validity", "Prescribed full application experiments and analysis"]}
    for name, value in (("paper/claim-ledger-v5.json", ledger), ("paper/draft-status-v5.json", status)):
        with (ROOT / name).open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    print(json.dumps({"status": "registered", "claims": len(CLAIMS), "references": 22}))
