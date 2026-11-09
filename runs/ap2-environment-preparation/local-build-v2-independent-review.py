"""Review only the named retained three-wheel capture; never load its code."""
from collections import Counter
from datetime import datetime, timezone
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path
import tomllib
from zipfile import ZipFile

BASE = Path(__file__).resolve().parent
CAPTURE = BASE / "local-build-v2"
STAGE = BASE / "source-stage-v1"
OUTPUT = Path(__file__).with_suffix(".json")
PIN = "554f4cea03f8153daac9b65117c445581bb725e1d3eea9ce8f93d96f7116c7d0"
checks, wheels = [], []

def sha(body):
    return hashlib.sha256(body).hexdigest()

def check(name, passed):
    checks.append({"check": name, "passed": bool(passed)})

body = (CAPTURE / "result.json").read_bytes()
receipt = json.loads(body)
plan = json.loads((CAPTURE / "plan.json").read_bytes())
check("exact_terminal_pass_receipt", sha(body) == PIN and receipt["schema_version"] == "ap2-isolated-local-wheel-build-result/2" and receipt["status"] == "three_original_source_wheels_built_and_inspected" and receipt["error"] is None)
check("12_successful_settled_owned_commands", len(receipt["commands"]) == 12 and all(row["passed"] is True and row["cleanup"]["handles_closed"] is True and row["cleanup"]["job_empty_observed"] is True and row["cleanup"]["errors"] == [] for row in receipt["commands"]) and receipt["owned_job_authority_remaining"] is False)
check("177_pristine_inputs_and_296_original_copy_files_preserved", len(receipt["input_preservation"]) == 177 and len(receipt["working_source_copy_preservation"]) == 296 and all(row["unchanged"] is True and sha(Path(row["file"]).read_bytes()) == row["sha256"] for row in receipt["input_preservation"] + receipt["working_source_copy_preservation"]))
check("no_ver_fallback_observed_and_v1_cause_unconfirmed", receipt["allowed_windows_ver_popen_probes"] == 0 and all(not rows for rows in receipt["audit_decisions_by_operation"].values()) and receipt["prior_v1_cause_confirmed"] is False)
check("original_application_and_model_execution_absent_in_declared_capture", receipt["original_application_imported"] is False and receipt["native_application_executed"] is False and receipt["model_requests"] == 0)
for project in plan["projects"]:
    name = project["name"]
    built, inspected = receipt["builds"][name], receipt["inspections"][name]
    path = CAPTURE / "wheels" / built["wheel_filename"]
    raw = path.read_bytes()
    original_path = STAGE / project["build_root"] / "pyproject.toml"
    original_raw = original_path.read_bytes()
    original = tomllib.loads(original_raw.decode())["project"]
    with ZipFile(path) as archive:
        members = archive.namelist()
        metadata_names = [member for member in members if member.endswith(".dist-info/METADATA")]
        metadata_raw = archive.read(metadata_names[0])
        metadata = BytesParser().parsebytes(metadata_raw)
        expected_modules = inspected["module_checks"]
        module_bindings = all(row["present"] is True and row["matches"] is True and sha((STAGE / row["source"]).read_bytes()) == row["expected_sha256"] == row["wheel_sha256"] == sha(archive.read(row["wheel_path"])) for row in expected_modules)
        metadata_matches = metadata["Name"] == original["name"] and metadata["Version"] == original["version"] and metadata["Requires-Python"] == original["requires-python"] and Counter(metadata.get_all("Requires-Dist", [])) == Counter(original["dependencies"])
        cards_match = all(row["included"] == (row["wheel_path"] in members) and sha((STAGE / row["source"]).read_bytes()) == row["sha256"] and row["wheel_sha256"] is None and row["included_bytes_match_source"] is None for row in inspected["agent_json_inclusion"])
        typed = inspected["py_typed"]["expected"]
        typed_match = typed is None or sha((STAGE / typed["source"]).read_bytes()) == typed["sha256"] == sha(archive.read(typed["wheel_path"]))
        check(name + "_wheel_metadata_original_module_and_asset_bindings", sha(raw) == built["wheel_sha256"] == inspected["wheel_sha256"] and len(raw) == built["wheel_bytes"] and sha(metadata_raw) == inspected["metadata_sha256"] and sha(original_raw) == project["original_pyproject_sha256"] and metadata_matches and module_bindings and cards_match and typed_match and len(members) == len(set(members)) and {member for member in members if member.endswith(".py")} == {row["wheel_path"] for row in expected_modules})
        wheels.append({"name": name, "wheel_filename": path.name, "sha256": sha(raw), "metadata_sha256": sha(metadata_raw), "requires_python": metadata["Requires-Python"], "requires_dist": metadata.get_all("Requires-Dist", []), "original_python_modules_verified": len(expected_modules), "agent_json_inclusion": inspected["agent_json_inclusion"], "py_typed_source_bytes_verified": typed_match})
check("exact_three_wheels_and_129_original_python_modules", len(wheels) == 3 and sum(row["original_python_modules_verified"] for row in wheels) == 129 and receipt["source_wheel_builds_attempted"] == 3)
result = {"schema_version": "ap2-three-local-wheels-independent-review/1", "reviewed_at_utc": datetime.now(timezone.utc).isoformat(), "status": "passed_bounded_retained_wheel_source_review" if all(row["passed"] for row in checks) else "discrepancy", "receipt_sha256": PIN, "review_script_sha256": sha(Path(__file__).read_bytes()), "checks": checks, "wheels": wheels, "replayed": False, "captured_or_application_code_imported": False, "wheel_build_or_install_performed": False, "model_requests": 0, "scope": "Recorded receipt and actual wheel/source byte consistency only; missing sample agent JSON remains disclosed, ver fallback was not observed, and original runtime/native/domain qualification is not established."}
with OUTPUT.open("x", encoding="utf-8") as stream:
    json.dump(result, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({"status": result["status"], "checks": len(checks), "discrepancies": sum(not row["passed"] for row in checks), "wheels": len(wheels), "original_python_modules": 129}))
