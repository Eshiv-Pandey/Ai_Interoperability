"""Read-only archive, raw-cell and deterministic cache-ablation census."""
from collections import Counter
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from interoperability import shared_cache_comparison_v3 as bundle

METHODS = ("baseline", "direct_pruned", "cache_neither", "cache_prefix", "cache_relation", "cache_both")
BUDGETS = (32, 256, 4096, 100000)


def load(path):
    return json.loads(path.read_bytes())


def digest(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def require(value, message):
    if not value:
        raise ValueError(message)


def deterministic(result):
    return {key: ({k: v for k, v in value.items() if k != "elapsed_ns"} if key == "stats" else value)
            for key, value in result.items() if key != "method"}


def audit(base, source, output):
    base, source, output = base.resolve(), source.resolve(), output.resolve()
    require(not output.exists(), "New read-audit allocation required")
    retention = load(base / "retention.json")
    require(retention["run_id"] == 42879031721, "Declared run changed")
    require(digest(base / "artifact.zip") == {"bytes": retention["archive_bytes"], "sha256": retention["archive_sha256"]}, "Archive changed")
    artifacts = load(base / "github-artifacts.json")["artifacts"]
    api = next(row for row in artifacts if row["id"] == retention["artifact_id"])
    require(api["digest"] == "sha256:" + retention["archive_sha256"], "API digest differs")
    raw = base / "extracted"
    inventory = load(base / "extracted-manifest.json")["files"]
    for row in inventory:
        require(digest(raw / row["path"]) == {"bytes": row["bytes"], "sha256": row["sha256"]}, "Archive member changed")
    all_cells, totals, pairs, verifications = [], [], {}, {}
    for budget in BUDGETS:
        folder = raw / f"budget-{budget}"
        verifications[budget] = bundle.verify(folder)
        rows = [json.loads(line) for line in (folder / "results.jsonl").read_bytes().splitlines()]
        old = [json.loads(line) for line in (source / f"budget-{budget}/results.jsonl").read_bytes().splitlines()]
        require(len(rows) == len(old) == 66, "66 cases required at each budget")
        for row, prior in zip(rows, old):
            require((row["case_id"], row["family"], row["model_sha256"], row["evaluation_clock"]) ==
                    (prior["case_id"], prior["family"], prior["model_sha256"], prior["evaluation_clock"]), "Changed profile/family/clock join")
            for method, previous in (("baseline", "baseline"), ("direct_pruned", "direct_pruned"), ("cache_both", "shared_lift")):
                require(deterministic(row["algorithms"][method]["execution"]["result"]) ==
                        deterministic(prior["algorithms"][previous]["execution"]["result"]), "Preserved arm deterministic mismatch")
            direct = row["algorithms"]["direct_pruned"]["execution"]["result"]["decision"]
            for method in METHODS:
                arm = row["algorithms"][method]
                require(arm["execution"]["status"] == "returned" and arm["valid_result"], "Missing/invalid cell cannot be omitted")
                result = arm["execution"]["result"]
                decision = result["decision"]
                require(decision == "unknown" or arm["certificate_valid"] is True, "Required proof invalid")
                if decision != "unknown" and direct != "unknown":
                    require(decision == direct, "Conclusive contradiction")
                proof = result["certificate"]
                encoded = None if proof is None else len(json.dumps(proof, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())
                resource = arm["execution"]["resources"]
                checker_ns = arm.get("certificate_check", {}).get("evaluation_ns", 0)
                stats = result.get("stats", {})
                cell = {"budget": budget, "case_id": row["case_id"], "family": row["family"], "method": method,
                        "decision": decision, "certified": decision != "unknown", "proof_bytes": encoded,
                        "work_units": stats.get("work_units"), "evaluation_ns": arm["execution"]["evaluation_ns"],
                        "check_ns": checker_ns, "prefix_cache_hits": stats.get("prefix_cache_hits", 0),
                        "relation_cache_hits": stats.get("relation_cache_hits", 0),
                        "prefix_cache_entries": stats.get("prefix_cache_entries", 0),
                        "relation_cache_entries": stats.get("relation_cache_entries", 0),
                        "direct_decision": direct, "model_sha256": row["model_sha256"]}
                if method in ("cache_neither", "cache_relation"):
                    require(cell["prefix_cache_hits"] == cell["prefix_cache_entries"] == 0, "Disabled prefix cache used")
                if method in ("cache_neither", "cache_prefix"):
                    require(cell["relation_cache_hits"] == cell["relation_cache_entries"] == 0, "Disabled relation cache used")
                all_cells.append(cell)
        for method in METHODS:
            cells = [row for row in all_cells if row["budget"] == budget and row["method"] == method]
            counts = Counter(row["decision"] for row in cells)
            totals.append({"budget": budget, "method": method, "cases": len(cells), "certified": sum(row["certified"] for row in cells),
                           "supported": counts["supported"], "unsupported": counts["unsupported"], "unknown": counts["unknown"],
                           **{field + "_sum": sum(row[field] or 0 for row in cells) for field in
                              ("work_units", "proof_bytes", "evaluation_ns", "check_ns", "prefix_cache_hits", "relation_cache_hits")}})
            pairs[f"{budget}/{method}"] = dict(Counter(row["direct_decision"] + "/" + row["decision"] for row in cells))
    require(len(all_cells) == 1584, "All six-arm cells retained")
    output.mkdir(parents=True)
    for name, rows in (("case-methods.csv", all_cells), ("budget-methods.csv", totals)):
        with (output / name).open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)
    result = {"schema_version": "shared-cache-ablation-read-review/3", "status": "passed_read_only_raw_cell_and_source_audit",
              "created_at_utc": datetime.now(timezone.utc).isoformat(), "run_id": retention["run_id"], "head_sha": retention["head_sha"],
              "raw_zip": digest(base / "artifact.zip"), "extracted_files_verified": len(inventory),
              "algorithm_cells": len(all_cells), "cache_policy_cells": 1056, "profiles": 66, "budgets": list(BUDGETS),
              "paired_decisions_against_goal_pruned_direct": pairs, "totals": totals, "bundle_verifications": verifications,
              "new_solver_checker_application_or_provider_calls": 0, "human_scientific_review": False,
              "limits": "Authored related development profiles; work is method-specific; timings sequential and noisy; no held-out or novelty claim",
              "audit_source": {"path": Path(__file__).relative_to(ROOT).as_posix(), **digest(Path(__file__))},
              "exports": [{"path": name, **digest(output / name)} for name in ("case-methods.csv", "budget-methods.csv")]}
    with (output / "result.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    return {"status": result["status"], "totals": totals}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.base, args.source, args.output), indent=2))
