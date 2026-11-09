"""Read only the named retained capture; never load or replay its implementation."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAPTURE = Path(__file__).with_name("native-gate-v1")
OUTPUT = Path(__file__).with_suffix(".json")
checks = []

def identity(path):
    body = path.read_bytes()
    return {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}

def check(name, value):
    checks.append({"check": name, "passed": bool(value)})

receipt = json.loads((CAPTURE / "result.json").read_bytes())
plan = json.loads((CAPTURE / "capture-plan.json").read_bytes())
outcomes = json.loads((CAPTURE / "test-outcomes.json").read_bytes())
pins = {"result.json": "68d9601e8fb6ee589bd7445835385378ec06376cac6f337c01044cd237041d22", "capture-plan.json": "10860e5e1b887c15e03b48de93b99f7564e013ce36df92d561b7fd4080b03aea", "test-outcomes.json": "e547d03df1fc201e367ff8e7137e948cf7a2fa27dc3a8e0c3ae8a1fe0c7cd8f0"}
check("exact_terminal_receipt_plan_outcome_pins", all(identity(CAPTURE / name)["sha256"] == digest for name, digest in pins.items()))
check("terminal_constructed_success", receipt["status"] == "passed_constructed_software_tests_only" and receipt["returncode"] == 0 and receipt["timed_out"] is False)
check("reported_preservation_and_copy_binding", all(receipt[name] is True for name in ("copied_checkout_matches_precopy_inputs", "declared_test_membership_verified", "original_and_captured_inputs_unchanged")))
check("scope_remains_software_only", all(receipt[name] is False for name in ("credential_opened", "environment_installed", "native_adapter_startup_executed", "native_application_executed", "native_windows_operations_executed", "original_source_imported")) and receipt["model_requests"] == 0)
retained = receipt["retained_files_before_result"]
check("all_declared_retained_artifact_bytes", all(identity(CAPTURE / name) == expected for name, expected in retained.items()))
expected = dict(plan["inputs_before"])
for prefix, key in (("docs/research/source-evidence/ap2-procurement-screen-v1/source", "original_source_files"), ("docs/research/source-evidence/ap2-hp-cert-assets-v1/source", "supplementary_certificate_files")):
    expected.update({prefix + "/" + name: value for name, value in plan[key].items()})
check("exact_147_copied_inputs_equal_precopy_bindings", len(expected) == len(plan["captured_inputs"]) == receipt["captured_file_count"] == 147 and expected == plan["captured_inputs"])
check("captured_input_bytes_still_match", all(identity(CAPTURE / "captured-checkout" / name) == expected for name, expected in plan["captured_inputs"].items()))
check("current_authored_inputs_match_before_and_after", plan["inputs_before"] == receipt["inputs_after"] and all(identity(ROOT / name) == expected for name, expected in plan["inputs_before"].items()))
tree = ast.parse((CAPTURE / "captured-checkout/tests/test_ap2_hp_native_gate_v1.py").read_bytes())
names = sorted(node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"))
check("exact_declared_and_recorded_28_test_membership", len(names) == 28 and names == plan["declared_test_names"] == sorted(row["id"].rsplit(".", 1)[-1] for row in outcomes["outcomes"]) and len({row["id"] for row in outcomes["outcomes"]}) == 28)
check("28_recorded_successes_without_failures_errors_or_skips", outcomes["tests_run"] == receipt["tests_run"] == 28 and outcomes["successful"] is True and all(outcomes[name] == 0 for name in ("failure_count", "error_count", "skipped_count")) and all(row["status"] == "passed" for row in outcomes["outcomes"]))
result = {"schema_version": "ap2-hp-native-gate-retained-receipt-review/1", "reviewed_at_utc": datetime.now(timezone.utc).isoformat(), "status": "passed_bounded_retained_receipt_audit" if all(row["passed"] for row in checks) else "discrepancy", "checks": checks, "retained_artifacts_hashed": len(retained), "captured_inputs_hashed": len(expected), "review_script": identity(Path(__file__)), "receipt_pins": pins, "capture_replayed": False, "captured_code_imported": False, "native_operations_performed": False, "original_application_imported": False, "model_requests": 0, "scope": "Receipt and file-byte consistency only; recorded tests were not rerun and native/provider/scientific qualification is not established."}
with OUTPUT.open("x", encoding="utf-8") as stream:
    json.dump(result, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({"status": result["status"], "checks": len(checks), "discrepancies": sum(not row["passed"] for row in checks), "retained_artifacts_hashed": len(retained)}))
