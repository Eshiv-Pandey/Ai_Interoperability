"""Independent retained-receipt audit; never imports or reruns captured code."""
from __future__ import annotations
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
CAPTURE = ROOT / "runs/ap2-hp-public-software/validation-v1"
OUTPUT = ROOT / "runs/ap2-hp-public-software/validation-v1-independent-review.json"
if OUTPUT.exists() or OUTPUT.with_suffix(".json.pending").exists():
    raise FileExistsError("Independent review namespace is consumed")

def descriptor(body):
    return {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}

def inventory():
    return {file.relative_to(CAPTURE).as_posix(): descriptor(file.read_bytes())
            for file in sorted(CAPTURE.rglob("*")) if file.is_file()}

checks = []
def check(name, value):
    checks.append({"name": name, "passed": bool(value)})

before = inventory()
plan = json.loads((CAPTURE / "plan.json").read_bytes())
result = json.loads((CAPTURE / "result.json").read_bytes())
check("result_schema", result.get("schema_version") == "ap2-hp-public-validation-result/1")
check("plan_schema", plan.get("schema_version") == "ap2-hp-public-validation-plan/1")
check("recorded_terminal_return_zero", type(result.get("returncode")) is int and result["returncode"] == 0)
check("recorded_passed_no_error", result.get("status") == "passed" and result.get("error") is None)
check("recorded_scope_only_constructed_observer", result.get("scope") == plan.get("scope") == "constructed_public_observer_tests_only")
check("application_imports_not_authorized", plan.get("application_imports_authorized") is False)
check("native_launches_not_authorized", plan.get("native_application_launches_authorized") is False)
check("recorded_native_qualification_false", result.get("native_qualification_established") is False)
check("recorded_original_application_launches_zero", type(result.get("original_application_processes_launched")) is int and result["original_application_processes_launched"] == 0)
check("recorded_provider_calls_zero", type(result.get("provider_calls")) is int and result["provider_calls"] == 0)
check("capture_complete_file_membership", set(before) == set(result["files"]) | {"result.json"})
for name, expected in result["files"].items():
    check("result_manifest:" + name, before.get(name) == expected)

driver_rel = "scripts/capture_ap2_hp_public_validation_v1.py"
driver = ast.parse((CAPTURE / "workspace" / driver_rel).read_bytes())
declared = None
for node in driver.body:
    if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "FILES" for target in node.targets):
        declared = ast.literal_eval(node.value)
check("driver_has_exact_unique_ten_source_files", type(declared) is tuple and len(declared) == len(set(declared)) == 10)
check("plan_matches_driver_source_set", set(plan["source_files"]) == set(declared))
workspace_before = {}
for name, expected in plan["source_files"].items():
    current = descriptor((ROOT / name).read_bytes())
    captured = descriptor((CAPTURE / "workspace" / name).read_bytes())
    workspace_before[name] = current
    check("current_source_hash:" + name, current == expected)
    check("captured_source_hash:" + name, captured == expected)
    check("plan_result_source_binding:" + name, result["files"].get("workspace/" + name) == expected)

test_rel = "tests/test_ap2_hp_public_assessment_v1.py"
syntax = ast.parse((CAPTURE / "workspace" / test_rel).read_bytes())
classes = [node for node in syntax.body if isinstance(node, ast.ClassDef)]
owners = [node for node in classes if node.name == "PublicPaymentAssessmentTests"]
check("one_primary_test_class", len(owners) == 1)
primary = sorted(node.name for owner in owners for node in owner.body
                 if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"))
check("exact_primary_ast_count_33", len(primary) == len(set(primary)) == 33)
check("plan_primary_exact_ast_membership", plan.get("primary_tests") == primary)
check("no_extra_test_classes", len(classes) == 1)
stderr = (CAPTURE / "stderr.txt").read_bytes().decode("utf-8", errors="strict")
lines = stderr.splitlines()
observed = []
unmatched_test_lines = []
for line in lines:
    if line.startswith("test_"):
        match = re.fullmatch(r"(test_\w+) \(test_ap2_hp_public_assessment_v1\.PublicPaymentAssessmentTests\.(test_\w+)\) \.\.\. ok", line)
        if match and match[1] == match[2]:
            observed.append(match[1])
        else:
            unmatched_test_lines.append(line)
check("logged_exact_primary_identity_membership", sorted(observed) == primary)
check("logged_33_unique_ok_tests", len(observed) == len(set(observed)) == 33)
check("no_unmatched_test_status_lines", not unmatched_test_lines)
summaries = [re.fullmatch(r"Ran (\d+) tests in ([0-9]+(?:\.[0-9]+)?)s", line) for line in lines if line.startswith("Ran ")]
check("one_terminal_ran_33_summary", len(summaries) == 1 and summaries[0] is not None and int(summaries[0][1]) == 33)
check("exact_terminal_ok", lines[-1:] == ["OK"] and lines.count("OK") == 1)
check("zero_failure_error_skip_log", not any(token in stderr for token in ("... FAIL", "... ERROR", "... skipped", "FAILED (", "Traceback (most recent call last)")))
check("stdout_empty", (CAPTURE / "stdout.txt").read_bytes() == b"")
check("recorded_counts_exact_33", type(result.get("tests_passed")) is int and type(result.get("tests_reported")) is int and result["tests_passed"] == result["tests_reported"] == 33)
check("recorded_exact_membership_true", result.get("exact_primary_membership_verified") is True)
check("recorded_preservation_true", result.get("inputs_unchanged") is True)
check("plan_exact_isolated_unittest_argv", plan.get("argv") == ["C:\\Python313\\python.exe", "-I", "-S", "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_ap2_hp_public_assessment_v1.py", "-v"])
check("recorded_clock_order", datetime.fromisoformat(result["started_at_utc"]) <= datetime.fromisoformat(result["ended_at_utc"]))

module_rel = "src/interoperability/ap2_hp_public_assessment_v1.py"
module = ast.parse((CAPTURE / "workspace" / module_rel).read_bytes())
module_imports = []
for node in ast.walk(module):
    if isinstance(node, ast.Import):
        module_imports.extend(item.name for item in node.names)
    elif isinstance(node, ast.ImportFrom):
        module_imports.append(node.module)
check("observer_imports_only_reviewed_stdlib", set(module_imports) == {"__future__", "base64", "copy", "hashlib", "json", "math"})
test_imports = []
for node in ast.walk(syntax):
    if isinstance(node, ast.Import):
        test_imports.extend(item.name for item in node.names)
    elif isinstance(node, ast.ImportFrom):
        test_imports.append(node.module)
check("tests_import_only_stdlib_and_explicit_observer_loader", set(test_imports) == {"copy", "importlib.util", "pathlib", "unittest"})
review_rel = "docs/research/ap2-human-present-public-assessor-source-review-v1.md"
review_before = descriptor((ROOT / review_rel).read_bytes())
check("bounded_source_review_exact_identity", review_before["sha256"] == "4083d03d8d14688ff4473015f4991913f61c24a8c0b4b57db6cda2cef409c5f9")

after = inventory()
check("entire_capture_preserved_during_audit", before == after)
for name, expected in workspace_before.items():
    check("current_source_preserved_during_audit:" + name, descriptor((ROOT / name).read_bytes()) == expected)
check("source_review_note_preserved_during_audit", descriptor((ROOT / review_rel).read_bytes()) == review_before)

report = {
    "schema_version": "ap2-hp-public-validation-independent-review/1",
    "status": "verified" if all(item["passed"] for item in checks) else "failed",
    "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
    "reviewer": "separate_AI_agent_method_next_step",
    "capture": str(CAPTURE), "capture_result_digest": before["result.json"],
    "capture_files": before, "current_source_files": workspace_before,
    "source_review_note": {"path": review_rel, **review_before},
    "reviewer_script_digest": descriptor(Path(__file__).read_bytes()),
    "primary_ast_tests": primary, "logged_primary_tests": observed,
    "checks_passed": sum(item["passed"] for item in checks), "checks": checks,
    "discrepancies": [item["name"] for item in checks if not item["passed"]],
    "test_reruns_by_reviewer": 0, "captured_modules_imported_by_reviewer": 0,
    "application_processes_launched_by_reviewer": 0, "provider_calls_by_reviewer": 0,
    "native_qualification_established": False, "scientific_novelty_established": False,
    "scope": "Independent retained-byte/result/plan/source/log membership and preservation audit of 33 constructed observer tests only. No test rerun or captured-code import. Return code and execution times are recorder evidence, not an independent live process observation. Source/capture authentication, causal order/completeness, original native HP workflow, signatures, credential/effect state, independent human task validity and scientific novelty remain unproved."
}
pending = OUTPUT.with_suffix(".json.pending")
with pending.open("xb") as stream:
    stream.write((json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n").encode())
    stream.flush()
    os.fsync(stream.fileno())
os.link(pending, OUTPUT)
pending.unlink()
print(json.dumps({"status": report["status"], "checks_passed": report["checks_passed"], "discrepancies": report["discrepancies"], "sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest()}))
