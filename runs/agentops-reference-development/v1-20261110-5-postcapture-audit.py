"""Read-only recapture of manifests, raw streams, private grades and bindings."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from agentops_reference_evaluator_v1 import IDS, seed_gold, grade, adversarial_controls

BASE = Path(__file__).resolve().parent / "v1-20261110-5-postcapture"
prior = BASE.parent / "v1-20261110-4"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
manifest = json.loads((BASE / "manifest.json").read_bytes())
for row in manifest["files"]:
    path = BASE / row["path"]
    assert path.stat().st_size == row["bytes"] and sha(path) == row["sha256"]
assert {row["path"] for row in manifest["files"]} == {path.relative_to(BASE).as_posix() for path in BASE.rglob("*") if path.is_file() and path.name != "manifest.json"}
plan = json.loads((BASE / "plan.json").read_bytes())
for row in plan["owned_inputs"]:
    path = ROOT / row["path"]
    assert path.stat().st_size == row["bytes"] and sha(path) == row["sha256"]
source = ROOT / "external/agentops-c806b7f1"
for name, digest in plan["source_files"].items():
    assert sha(source / name) == digest
for row in plan["seed_files"]:
    assert sha(source / row["path"]) == row["sha256"]
observed, scored, imported_counts = {}, [], {}
gold = seed_gold(source / "agents/data")
for selected in IDS:
    case = BASE / selected
    payload = json.loads((case / "actor-output.json").read_bytes())
    events = [json.loads(line) for line in (case / "events.jsonl").read_bytes().splitlines()]
    assert payload["trace"] == events
    assert payload["before_state"] == json.loads((case / "before-state.json").read_bytes())
    assert payload["after_state"] == json.loads((case / "after-state.json").read_bytes())
    if selected in plan["reused_capture_provenance"]["cases"]:
        assert sha(case / "actor-output.json") == sha(prior / selected / "actor-output.json")
    process = json.loads((case / "process.json").read_bytes())
    assert process["returncode"] == 0 and not process["timed_out"]
    observed[selected] = payload
    scored.append(grade(payload, gold, "minimal_reads"))
    imported_counts[selected] = {"original_files": len(payload["original_imported_files_verified"]),
                                "dependency_files": len(payload["dependency_imported_files_verified"])}
assert all(row["checks_verified"] == row["checks_total"] for row in scored)
controls = adversarial_controls(observed, gold)
assert controls["all_rejected"]
result = {"schema_version": "agentops-component-reference-read-audit/1", "status": "retained-component-evidence-rechecked",
          "sealed_files": len(manifest["files"]), "sealed_bytes": sum(row["bytes"] for row in manifest["files"]),
          "checks_verified": sum(row["checks_verified"] for row in scored), "checks_total": sum(row["checks_total"] for row in scored),
          "fresh_original_recipe_invocations_in_this_audit": 0, "source_and_seed_bindings_match": True,
          "raw_streams_match_actor_observations": True, "imported_counts": imported_counts,
          "adversarial_controls": controls, "original_App_tasks_passed": 0, "original_App_tasks_unknown": 6,
          "human_review": "not_reviewed", "independent_evaluator_authorship": False}
with (BASE.parent / "v1-20261110-5-postcapture-audit.json").open("x", encoding="utf-8") as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(result, indent=2))
