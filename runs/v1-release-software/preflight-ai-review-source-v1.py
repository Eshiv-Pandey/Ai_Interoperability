"""Independent constructed preflight checks; no actual Linux/App/provider run."""
from copy import deepcopy
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_research_v1_release as release

BASE = ROOT / "runs/v1-release-software/preflight-controls-v1"
BASE.mkdir(parents=True, exist_ok=False)
ROWS = [release.core.record(ROOT / name, ROOT) for name in (
    "scripts/verify_research_v1_release.py",
    ".github/workflows/research-v1-release-verification.yml")]
results = []


def fixture(name, intervention=None):
    output = BASE / name
    calls = []

    def invoke(allocation, label, argv, timeout):
        if not (allocation / "checkout").is_dir():
            raise AssertionError("Outer empty working directory absent")
        if label != "current-extra-controls" and not Path(argv[4]).is_absolute():
            raise AssertionError("Expected absolute known script entry point")
        calls.append(label)
        folder = allocation / "commands" / label
        folder.mkdir(parents=True)
        (folder / "stderr.bin").write_bytes(b"constructed retained stream\n")
        observed = {"status": "passed"}
        suffix = {
            "owned-timeout-controls": "timeouts/result.json",
            "complete-core-reproduction": "core/result.json",
            "admission-demo-and-replay": "demo/result.json",
            "current-extra-controls": "commands/current-extra-controls/stdout.bin",
            "complete-bank-validation": "bank-validation.json",
        }[label]
        if label == "current-extra-controls":
            observed = {"successful": True, "tests_run": 1, "skipped": 0,
                        "failures": 0, "errors": 0}
            if intervention == "zero_controls":
                observed["tests_run"] = 0
        if label == "complete-bank-validation":
            observed = {"status": "structurally_valid", "allocation_complete": True,
                        "total_templates": 68, "semantic_or_runtime_qualification_claimed": False}
            if intervention == "semantic_overclaim":
                observed["semantic_or_runtime_qualification_claimed"] = True
        if intervention == "failed_outcome" and label == "complete-core-reproduction":
            observed["status"] = "failed"
        path = allocation / suffix
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(observed), encoding="utf-8")
        if not (folder / "stdout.bin").exists():
            (folder / "stdout.bin").write_bytes(b"constructed retained stdout\n")
        receipt = {"returncode": 0, "timed_out": False, "label": label}
        if intervention == "returncode_failure" and len(calls) == 1:
            receipt["returncode"] = 1
        if intervention == "timeout" and len(calls) == 1:
            receipt["timed_out"] = True
        release.core.write(folder / "process.json", receipt)
        return receipt

    after = deepcopy(ROWS)
    if intervention == "source_drift":
        after[0]["sha256"] = "constructed changed source identity"
    with mock.patch.object(release.owned, "require_linux"), \
            mock.patch.object(release, "inventory", side_effect=[deepcopy(ROWS), after]), \
            mock.patch.object(release.owned, "invoke", side_effect=invoke):
        value = release.execute(output)
    expected = "passed" if intervention is None else "failed"
    if value["status"] != expected:
        raise AssertionError((name, value["status"], expected))
    if not value["outer_owned_groups_confirmed_closed"]:
        raise AssertionError("Constructed review left a registered outer group")
    manifest = release.core.read(output / "retained-manifest.json")
    if manifest["status"] != expected:
        raise AssertionError("Failure manifest status was promoted")
    recorded = {row["path"] for row in manifest["files"]}
    if not any(path.endswith("stderr.bin") for path in recorded):
        raise AssertionError("Constructed failed stream was not retained")
    if intervention in ("returncode_failure", "timeout") and len(calls) != 1:
        raise AssertionError("Dependent commands continued after first failure")
    if intervention == "failed_outcome" and len(calls) != 2:
        raise AssertionError("Dependent commands continued after failed outcome")
    if intervention == "zero_controls" and len(calls) != 4:
        raise AssertionError("Zero-test controls were accepted")
    results.append({"id": name, "status": "passed_constructed_control", "observed_release_status": expected,
                    "mocked_commands": calls, "actual_original_application_or_sdk_executions": 0,
                    "actual_provider_requests": 0})


for label, intervention in (
    ("all_commands_pass", None), ("nonzero_exit_kept_failed", "returncode_failure"),
    ("timeout_kept_failed", "timeout"), ("failed_core_outcome_stops_dependencies", "failed_outcome"),
    ("zero_test_run_is_refused", "zero_controls"),
    ("candidate_bank_semantic_overclaim_is_refused", "semantic_overclaim"),
    ("source_drift_is_refused", "source_drift")):
    fixture(label, intervention)

original_read = release.core.regular_bytes
count = [0]


def corrupt_first_capture(path):
    count[0] += 1
    raw = original_read(path)
    return raw + b"constructed altered capture" if count[0] == 1 else raw


snapshot_output = BASE / "captured_bytes_must_match_preflight"
with mock.patch.object(release.owned, "require_linux"), \
        mock.patch.object(release, "inventory", return_value=deepcopy(ROWS)), \
        mock.patch.object(release.core, "regular_bytes", side_effect=corrupt_first_capture), \
        mock.patch.object(release.owned, "invoke", side_effect=AssertionError("unexpected command")) as invoke:
    try:
        release.execute(snapshot_output)
    except ValueError as error:
        if "Frozen release copy differs from preflight bytes" not in str(error):
            raise
    else:
        raise AssertionError("Different captured bytes were accepted")
    invoke.assert_not_called()
results.append({"id": "captured_bytes_must_match_preflight", "status": "passed_constructed_control",
                "no_command_started": True, "precommand_failure_capture_retained": True,
                "structured_result_not_written_before_command_phase": True})

inventory = release.inventory()
paths = {row["path"] for row in inventory}
plan_path = ROOT / "runs/ap2-native-shopper-provider-development/v3/preparation-1/plan.json"
plan = json.loads(plan_path.read_bytes())
required = [plan_path]
required += [plan_path.parent / "owned-source" / name for name in plan["owned_sources"]]
required += [ROOT / "tests/fixtures/ap2-public-continuation-v1" / ("v13-" + outcome + "-" + state + "-task.json")
             for outcome in ("correct", "wrong") for state in ("pending", "final")]
if any(path.relative_to(ROOT).as_posix() not in paths for path in required):
    raise AssertionError("Current extra-control dependency not captured")

empty = BASE / "empty-working-directory"
empty.mkdir()
argv = [sys.executable, "-I", "-S", "-B", "-c", release.core.TEST_BOOT,
        str(ROOT), *release.EXTRA_TESTS]
control_run = subprocess.run(argv, cwd=empty, capture_output=True, timeout=180, check=False)
(BASE / "current-extra-controls.stdout.bin").write_bytes(control_run.stdout)
(BASE / "current-extra-controls.stderr.bin").write_bytes(control_run.stderr)
if control_run.returncode != 0:
    raise AssertionError("Current extra controls failed from empty working directory")
actual_tests = json.loads(control_run.stdout)
if not actual_tests["successful"] or any(actual_tests[key] for key in ("skipped", "failures", "errors")):
    raise AssertionError("Current extra controls did not all execute")
report = {"schema_version": "v1-release-software-preflight-ai-review/1",
          "reviewed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "status": "no_material_blocker_found_after_fixes",
          "review_kind": "AI software source/wiring review and constructed status/retention controls",
          "reviewed_sources": [release.core.record(ROOT / path, ROOT) for path in (
              "scripts/verify_research_v1_release.py", ".github/workflows/research-v1-release-verification.yml",
              "scripts/ci_research_core_v1.py", "scripts/ci_research_core_v2.py",
              "scripts/run_shared_admission_demo_v1.py", "scripts/validate_task_banks_v1.py")],
          "inventory_inputs_checked": len(inventory), "required_extra_fixture_dependencies_bound": len(required),
          "fixed_findings": ["Extra-control test fixtures and exact V3 frozen plan/source snapshots now captured",
                             "Captured source inventory explicitly equals original preflight inventory before commands and afterward"],
          "constructed_controls": results, "actual_current_extra_controls": actual_tests,
          "actual_current_extra_controls_argv": argv, "actual_current_extra_controls_cwd": str(empty),
          "workflow_review": {"manual_dispatch_only": True, "Ubuntu_24_04_Python_3_13_1": True,
              "pinned_checkout_python_artifact_actions": True, "read_only_repository_permissions": True,
              "no_secrets_or_provider_setup": True, "always_uploads_failed_allocations": True},
          "observations": ["Input-validation failures happen before allocation; workflow step logs retain them, while artifact upload has no allocation to upload.",
                           "Capture-validation failures happen before the command-phase try/finally; partial captured bytes are retained but no structured result/manifest is sealed.",
                           "owned.invoke can raise after writing process.json; result commands list may omit that failed receipt, but complete retained file inventory includes it.",
                           "Unconfirmed owned groups block manifest sealing and final exit is nonzero; no successful release claim is made."],
          "actual_original_application_or_sdk_execution_by_reviewer": 0,
          "actual_provider_requests_by_reviewer": 0,
          "actual_Git_actions_by_reviewer": 0,
          "actual_Linux_core_or_demo_execution_by_reviewer": False,
          "scope_limit": "Preflight software qualification only; actual Linux owned groups/full core/demo replay remain required after hosted execution. Constructed controls do not award application task success, human gold, novelty or whole-study completion.",
          "review_source": release.core.record(Path(__file__).resolve(), ROOT)}
release.core.write(ROOT / "runs/v1-release-software/preflight-ai-review-v1.json", report)
print(json.dumps({"status": report["status"], "inputs": len(inventory),
                  "constructed_controls": len(results), "current_extra_tests": actual_tests["tests_run"]}))
