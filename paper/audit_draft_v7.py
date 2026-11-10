"""Read-only manuscript audit against retained raw-audit outcomes and bindings."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "paper" / (name + ".py"))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def require(value, message):
    if not value:
        raise ValueError(message)


def load(name):
    return json.loads((ROOT / name).read_bytes())


def record(name):
    raw = (ROOT / name).read_bytes()
    return {"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def audit():
    inherited = module("audit_draft_v6").audit()
    builder = module("build_draft_v7")
    draft = (ROOT / "paper/working-draft-v7.md").read_text(encoding="utf-8")
    ledger = load("paper/claim-ledger-v7.json")
    require(draft == builder.build(publish=False), "Manuscript transformation differs")
    require(ledger["draft"] == record("paper/working-draft-v7.md") and ledger["builder"] == record("paper/build_draft_v7.py"), "Manuscript/builder binding changed")
    for evidence in ledger["evidence"]:
        require(record(evidence["path"]) == evidence, "Evidence changed: " + evidence["path"])
    ap2, numeric = load(builder.AP2), load(builder.AP2_NUMERIC)
    totals = {arm: sum(cell["purchase_completed"] for cell in ap2["cells"] if cell["arm_id"] == arm)
              for arm in ("reference", "conventional", "recovery", "shared", "recovery_shared")}
    require(list(totals.values()) == [11, 3, 10, 3, 9] and sum(totals.values()) == 36, "AP2 retained purchase totals differ")
    require(numeric["total_strict_error_free_owned_cell_purchases"] == 31 and numeric["reviewed_cells"] == 65, "Strict AP2 distinction lost")
    require(ledger["AP2_purchase_totals"] == totals, "AP2 ledger census differs")
    cache = load(builder.CACHE)
    require(cache["algorithm_cells"] == 1584 and cache["cache_policy_cells"] == 1056, "Cache denominator differs")
    agentops = load(builder.AGENTOPS)
    census = dict(Counter(row["status"] for row in agentops["cases"]))
    require(census == {"observed_reference_recipe": 20, "observed_partial_reference_recipe": 10, "unsupported_public_recipe": 2, "checks_failed": 2}
            and census == ledger["AgentOps_statuses"], "AgentOps complete/partial/failed census differs")
    adk = load(builder.ADK)
    require(adk["candidate_denominator"] == 34 and adk["new_original_adk_process_denominator"] == 29
            and adk["totals"] == {"actual_purchase_processes": 0, "generic_status_adverse_processes": 28,
                 "independent_evaluation_refusals": 0, "missing_processes": 0, "verified_original_adk_prefix_processes": 29}, "ADK denominator/adverse outcome differs")
    for marker in ("1,584", "3/13", "10/13", "36 purchase", "29/29", "31/65", "AdmissionRefused", "20 complete", "10 partial"):
        require(marker in draft, "Reported evidence marker missing: " + marker)
    for name in ("paper/working-draft-v7.md", "docs/research/paper-artifact-guide-v7.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
            parsed = urlparse(target)
            if parsed.scheme:
                require(parsed.scheme in ("http", "https") and parsed.netloc, "Invalid external URL")
            else:
                path = ((ROOT / name).parent / unquote(parsed.path)).resolve()
                require(path.is_relative_to(ROOT) and path.exists(), "Broken retained evidence link: " + target)
    status = load("paper/draft-status-v7.json")
    require(status["full_manuscript_drafted"] and not status["publication_ready"] and not status["human_scientific_review_claimed"]
            and not status["original_full_study_scope_complete"], "Completion/qualification conflated")
    return {"schema_version": "manuscript-evidence-audit/7", "status": "passed", "as_of_utc": datetime.now(timezone.utc).isoformat(),
        "draft": record("paper/working-draft-v7.md"), "ledger": record("paper/claim-ledger-v7.json"),
        "guide": record("docs/research/paper-artifact-guide-v7.md"), "audit_source": record("paper/audit_draft_v7.py"),
        "inherited_v6_status": inherited["status"], "AP2_purchases": totals, "AP2_error_free_owned_cell_purchases": 31,
        "AgentOps_status_census": census, "ADK_totals": adk["totals"], "cache_cells": 1584,
        "new_application_solver_checker_or_provider_calls": 0, "full_original_study_complete": False, "human_review": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit()
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(result))
