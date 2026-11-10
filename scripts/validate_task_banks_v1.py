"""Validate public/gold separation and source bindings without executing applications.

Structural validity is distinct from reviewed gold, native qualification and a
sealed held-out set. This command never changes checkpoint credit.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
SPLITS = {"development": 6, "calibration": 4, "held_out": 24}
META = ("id", "split", "template_family", "distinct_obligation")
GOLD_KEYS = {"expected_facts", "expected_order", "expected_state", "reset",
             "legitimate_alternatives", "near_misses", "source_refs", "review_status"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_regular(root, name):
    relative = PurePosixPath(name)
    require(not relative.is_absolute() and ".." not in relative.parts
            and str(relative) == name and "\\" not in name, "Unsafe input path: " + name)
    path = root / name
    require(path.resolve().is_relative_to(root.resolve()), "Input escaped source root: " + name)
    require(path.is_file() and not path.is_symlink(), "Missing or nonregular input: " + name)
    require(all(not ancestor.is_symlink() for ancestor in path.parents
                if ancestor.is_relative_to(root)), "Symlinked input ancestor: " + name)
    return path.read_bytes()


def reject_gold_public(value):
    if isinstance(value, dict):
        require(not GOLD_KEYS.intersection(value), "Evaluator-only field leaked into public inputs")
        for nested in value.values():
            reject_gold_public(nested)
    elif isinstance(value, list):
        for nested in value:
            reject_gold_public(nested)


def claim_objects(value):
    if isinstance(value, dict):
        if "claim" in value:
            yield value
        else:
            for nested in value.values():
                yield from claim_objects(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from claim_objects(nested)


def validate_pair(application, evaluator, source_reader):
    require(application["schema_version"] == evaluator["schema_version"] == "source-task-bank/1",
            "Task-bank schema mismatch")
    require(application["domain"] == evaluator["domain"], "Domain mismatch")
    require(application["source_pin"] == evaluator["source_pin"], "Public/gold source pins differ")
    public, gold = application["records"], evaluator["records"]
    require(len(public) == len(gold), "Public/gold counts differ")
    for records in (public, gold):
        for field in ("id", "template_family", "distinct_obligation"):
            values = [record[field] for record in records]
            require(all(isinstance(value, str) and value.strip() for value in values),
                    "Missing template metadata: " + field)
            require(len(set(values)) == len(values), "Duplicate template metadata: " + field)
    require([row["id"] for row in public] == [row["id"] for row in gold],
            "Public/gold ordered IDs differ")
    counts = Counter(row["split"] for row in public)
    require(set(counts) <= set(SPLITS), "Unknown split")
    require(all(counts[split] <= target for split, target in SPLITS.items()), "Split over allocation")
    files, references, claims, claim_statuses = {}, set(), 0, Counter()

    def source(name, expected):
        if name not in files:
            raw = source_reader(name)
            files[name] = {"sha256": digest(raw), "bytes": len(raw),
                           "line_count": len(raw.splitlines())}
        require(files[name]["sha256"] == expected, "Source hash mismatch: " + name)
        return files[name]

    pin = application["source_pin"]
    for entry in pin.get("data_files", []):
        source(entry["path"], entry["sha256"])
    if "seed_database" in pin:
        entry = pin["seed_database"]
        source(entry["path"], entry["sha256"])
    for a, e in zip(public, gold):
        require(all(a[field] == e[field] for field in META), "Joined template metadata mismatch")
        require(set(a) == set(META) | {"public"}, "Unexpected public record field")
        reject_gold_public(a["public"])
        require(isinstance(a["public"], dict) and a["public"], "Empty public task")
        for key in GOLD_KEYS:
            require(key in e and e[key], "Missing evaluator obligation: " + key)
        registry = e["source_refs"]
        require(isinstance(registry, dict), "Expected a citation registry")
        for label, ref in registry.items():
            info = source(ref["path"], ref["sha256"])
            bounds = ref["lines"]
            require(isinstance(bounds, list) and len(bounds) == 2
                    and all(type(value) is int for value in bounds)
                    and 1 <= bounds[0] <= bounds[1] <= info["line_count"],
                    "Invalid source range: " + a["id"] + ":" + label)
            references.add((ref["path"], ref["sha256"], *bounds))
        for key in GOLD_KEYS - {"source_refs", "review_status"}:
            for claim in claim_objects(e[key]):
                require(isinstance(claim["claim"], str) and claim["claim"].strip(), "Empty claim")
                refs, status = claim["source_refs"], claim["status"]
                require(isinstance(refs, list) and set(refs) <= set(registry), "Unbound claim citation")
                require(status in {"source_supported", "pending_human_judgment"}, "Unknown claim status")
                require(status != "source_supported" or bool(refs), "Uncited source-supported claim")
                claims += 1
                claim_statuses[status] += 1
    missing = {split: target - counts[split] for split, target in SPLITS.items()}
    return {"domain": application["domain"], "structural_status": "valid",
            "templates": len(public), "split_counts": dict(counts), "missing_slots": missing,
            "allocation_complete": not any(missing.values()), "source_files_checked": len(files),
            "source_ranges_checked": len(references), "claims_checked": claims,
            "claim_statuses": dict(claim_statuses), "source_files": files,
            "review_statuses": dict(Counter(row["review_status"] for row in gold)),
            "qualification": evaluator["qualification"],
            "runtime_execution_performed": False, "gold_semantics_validated": False,
            "independent_holdout_sealed": False, "research_checkpoint_credit_added": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    root, reports, inputs = args.root.resolve(), [], []
    for domain in ("agentops", "ap2"):
        values = []
        for projection in ("application", "evaluator"):
            name = f"benchmark/tasks-v1/{domain}/{projection}.json"
            raw = read_regular(root, name)
            inputs.append({"path": name, "sha256": digest(raw), "bytes": len(raw)})
            values.append(json.loads(raw))
        reports.append(validate_pair(*values, lambda name: read_regular(root, name)))
    report = {"schema_version": "source-task-bank-validation/1", "status": "structurally_valid",
              "checked_at_utc": datetime.now(timezone.utc).isoformat(), "inputs": inputs,
              "domains": reports, "total_templates": sum(row["templates"] for row in reports),
              "allocation_complete": all(row["allocation_complete"] for row in reports),
              "semantic_or_runtime_qualification_claimed": False}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(report, handle, indent=2, allow_nan=False)
            handle.write("\n")
    print(json.dumps({key: value for key, value in report.items() if key != "domains"}, indent=2))
    for domain in reports:
        print(json.dumps({key: value for key, value in domain.items() if key != "source_files"}, indent=2))
    return 2 if args.require_complete and not report["allocation_complete"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
