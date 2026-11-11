"""Add accurate enclosing-section navigation to the sealed V15 claim ledger.

Standard-library read-only check. No sealed artifact is changed; no application,
SDK, provider, evaluator, solver or certificate checker is executed.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def record(path):
    path = path.resolve()
    if not path.is_relative_to(ROOT) or not path.is_file() or path.is_symlink():
        raise ValueError("regular_workspace_input_required")
    raw = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def build(draft, ledger):
    text = draft.read_text(encoding="utf-8")
    value = json.loads(ledger.read_text(encoding="utf-8"))
    if value["draft"] != record(draft):
        raise ValueError("sealed_ledger_and_draft_must_match")
    lines = text.splitlines()
    headings = [(index + 1, len(match.group(1)), line)
                for index, line in enumerate(lines)
                if (match := re.match(r"^(#{2,3}) ", line))]
    locations = []
    for claim in value["claims"]:
        original = claim["manuscript_location"]
        matching = [(line, level) for line, level, heading in headings if heading == original["heading"]]
        if len(matching) != 1 or matching[0][0] != original["line_start"]:
            raise ValueError("claim_heading_or_start_no_longer_matches:" + claim["id"])
        start, level = matching[0]
        next_heading = next((line for line, other_level, _ in headings
                             if line > start and other_level <= level), len(lines) + 1)
        corrected = {"heading": original["heading"], "line_start": start, "line_end": next_heading - 1}
        if original["line_end"] > corrected["line_end"]:
            raise ValueError("original_claim_range_exceeds_its_enclosing_section")
        locations.append({"claim_id": claim["id"], "original_location": original,
                          "navigation_location": corrected,
                          "includes_child_subsections": level == 2 and any(
                              start < line < next_heading and child_level > level
                              for line, child_level, _ in headings),
                          "range_expanded": original["line_end"] < corrected["line_end"],
                          "claim_statement_source_scope_or_validation_changed": False})
    expanded = [row["claim_id"] for row in locations if row["range_expanded"]]
    if expanded != ["SEMANTICS", "ALGORITHMS", "DESIGN"]:
        raise ValueError("unexpected_claim_range_changes:" + ",".join(expanded))
    return {"schema_version": "paper-v15-sealed-claim-navigation-supplement/1",
            "audited_utc": datetime.now(timezone.utc).isoformat(),
            "status": "passed_exact_draft_and_ledger_section_navigation_audit",
            "draft_identity": record(draft), "sealed_ledger_identity": record(ledger),
            "auditor_source_identity": record(Path(__file__)), "claim_count": len(locations),
            "expanded_parent_claims": expanded, "claim_locations": locations,
            "interpretation": "Use navigation_location for section reading. Parent ## ranges include every child ### subsection; all sealed statements, evidence, status and limitations remain unchanged.",
            "sealed_V15_files_modified": False,
            "new_application_SDK_provider_solver_checker_or_evaluator_executions": 0,
            "human_scientific_review_claimed": False, "full_original_study_complete": False,
            "publication_ready": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("draft", "ledger", "output"):
        parser.add_argument("--" + flag, type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "paper") or output.exists():
        raise ValueError("fresh_paper_supplement_output_required")
    value = build(args.draft.resolve(), args.ledger.resolve())
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": value["status"], "claim_count": value["claim_count"],
                      "expanded_parent_claims": value["expanded_parent_claims"], "output": record(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
