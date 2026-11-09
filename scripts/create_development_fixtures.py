"""Construct labelled semantic test inputs, NOT measured bridge task data."""

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    directory = ROOT / "examples/development"
    directory.mkdir(parents=True, exist_ok=True)
    base = {
        "schema_version": "finite-continuation/1", "id": "development-positive",
        "route": "authored task binding model; no external bridge observation",
        "provenance": {"kind": "authored-development",
                       "source": "scripts/create_development_fixtures.py",
                       "review_status": "AI-authored semantic tests; human validation pending"},
        "horizon": 3,
        "evidence": {"complete": True, "observed_at": 0, "valid_until": 4102444800},
        "initial": "pending", "states": {}, "transitions": [],
        "runtime_contract": {
            "goal": [{"field": "status", "op": "eq", "value": "completed"},
                     {"field": "task_handle", "op": "eq_field", "other_field": "required_handle"},
                     {"field": "artifact_accessible", "op": "eq", "value": True},
                     {"field": "principal", "op": "eq_field", "other_field": "authorized_principal"}],
            "invariants": [{"field": "unauthorized_effect", "op": "eq", "value": False}],
        },
    }
    for name, accessible in [("pending", False), ("approved", False), ("retrieved", True), ("completed", True)]:
        base["states"][name] = {
            "status": name, "task_handle": "scope-a:task-17", "required_handle": "scope-a:task-17",
            "artifact_accessible": accessible, "principal": "receiver", "authorized_principal": "receiver",
            "unauthorized_effect": False,
        }
    for source, target, operation in [("pending", "approved", "resume_with_authorized_input"),
                                     ("approved", "retrieved", "retrieve_artifact"),
                                     ("retrieved", "completed", "finish_task")]:
        base["transitions"].append({"id": operation, "source": source, "target": target, "operation": operation})
    cases = {"positive": base}
    mismatch = copy.deepcopy(base)
    mismatch["id"] = "development-unsupported-binding"
    mismatch["states"]["completed"]["task_handle"] = "scope-b:task-17"
    cases["unsupported-binding"] = mismatch
    unknown = copy.deepcopy(base)
    unknown["id"] = "development-unknown-observable"
    unknown["evidence"]["complete"] = False
    del unknown["states"]["completed"]["task_handle"]
    cases["unknown-observable"] = unknown
    unsafe = copy.deepcopy(base)
    unsafe["id"] = "development-unsupported-safety"
    unsafe["states"]["approved"]["unauthorized_effect"] = True
    cases["unsupported-safety"] = unsafe
    for name, model in cases.items():
        path = directory / f"{name}.json"
        payload = json.dumps(model, indent=2, sort_keys=True) + "\n"
        if path.exists() and path.read_text(encoding="utf-8") != payload:
            raise SystemExit(f"Refusing to replace changed fixture: {path}")
        path.write_text(payload, encoding="utf-8")
    print(f"Wrote {len(cases)} labelled authored DEVELOPMENT fixtures; zero observed bridge results.")


if __name__ == "__main__":
    main()
