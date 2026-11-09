"""One read-only review of the retained v2 export; no applications or tests run."""
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys

sys.dont_write_bytecode = True
REVIEW = Path(__file__).resolve().parent
EXPORT = REVIEW.parent / "export"
WORKSPACE = EXPORT / "workspace"
GROUP = "runs/agentops-admission-live-v1"
CASE = "runs/agentops-http-control/admission-live-v1-N11"
B7 = "runs/agentops-http-control/admission-live-v1-B7"
EXPECTED_MANIFEST = "a7cdc1281b28737fc2fb263ca8674c03bc83f28330303f1f6ed19fc574b9d389"


def now():
    return datetime.now(timezone.utc).isoformat()


def load(path):
    return json.loads(path.read_bytes())


def record(path, root):
    raw = path.read_bytes()
    return {"path": path.relative_to(root).as_posix(), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def inventory(root):
    files, pending = [], [root]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as stream:
            entries = sorted(stream, key=lambda entry: entry.name)
        for entry in entries:
            path = Path(entry.path)
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
                raise ValueError("Link in exported artifact: " + str(path))
            if stat.S_ISDIR(info.st_mode):
                pending.append(path)
            elif stat.S_ISREG(info.st_mode):
                files.append(record(path, root))
            else:
                raise ValueError("Nonregular exported artifact: " + str(path))
    return sorted(files, key=lambda row: row["path"])


def write_new(name, value):
    with (REVIEW / name).open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")


def workspace_record(name):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name or name != path.as_posix():
        raise ValueError("Unsafe retained relative path")
    return record(WORKSPACE / name, WORKSPACE)


def main():
    report = {"schema_version": "agentops-admission-independent-export-review/1",
              "started_at_utc": now(), "reviewer": "independent AI evidence review; not human review",
              "status": "started", "export": str(EXPORT), "application_launches": 0,
              "benchmark_or_test_reruns": 0, "failures": [],
              "source": record(Path(__file__), REVIEW)}
    write_new("execution.json", report)
    before = inventory(EXPORT)
    write_new("export-before.json", before)

    def check(condition, message):
        if not condition:
            report["failures"].append(message)

    try:
        exported = load(EXPORT / "result.json")
        manifest = load(EXPORT / "manifest.json")
        manifest_record = record(EXPORT / "manifest.json", EXPORT)
        check(manifest_record == exported["manifest"], "Export result does not bind manifest bytes")
        check(manifest_record["sha256"] == EXPECTED_MANIFEST, "Manifest differs from supplied export digest")
        check(exported["status"] == manifest["status"] == "exported", "Export did not complete")
        check(exported["sources_unchanged"] is True and exported["copies_match_source_before"] is True,
              "Export did not establish source/copy equality")
        check(not exported["failures"] and not manifest["failures"], "Export records contain integrity failures")
        copied = [{**row, "path": row["path"].removeprefix("workspace/")}
                  for row in before if row["path"].startswith("workspace/")]
        check(copied == manifest["copied"]["files"] == manifest["source_before"]["files"] == manifest["source_after"]["files"],
              "Actual exported files differ from copied/before/after inventories")
        check(all(manifest[key]["complete"] is True for key in ("source_before", "source_after", "copied")),
              "Export inventory was incomplete")
        check(len(copied) == exported["copied_files"] == 812, "Unexpected copied file count")
        check(sum(row["bytes"] for row in copied) == exported["copied_bytes"] == 11188632,
              "Unexpected copied byte count")
        check(exported["external_runtime_closure_copied"] is False, "Runtime scope claim changed")
        check(not any(row["path"].startswith("external/runtime") for row in copied), "Runtime tree was unexpectedly exported")
        plan = load(WORKSPACE / GROUP / "preparation/plan.json")
        for row in plan["inputs"]:
            check(workspace_record(row["path"]) == row, "Staged input mismatch: " + row["path"])
        check(len(plan["inputs"]) == 687, "Unexpected staged-input count")
        permitted = {row["path"] for row in plan["inputs"]}
        permitted.update(row["path"] for row in copied if any(row["path"].startswith(tree + "/") for tree in (GROUP, CASE, B7)))
        check(permitted == {row["path"] for row in copied}, "Export contains out-of-scope files")
        report["integrity"] = {"manifest": manifest_record, "workspace_files": len(copied),
                               "workspace_bytes": sum(row["bytes"] for row in copied), "staged_inputs": len(plan["inputs"]),
                               "export_files_including_manifest_and_result": len(before),
                               "reuse_root": exported["reuse_root"], "external_runtime_closure_copied": False}

        group = load(WORKSPACE / GROUP / "attempt/result.json")
        skipped = load(WORKSPACE / GROUP / "attempt/B7.skipped.json")
        native_result = load(WORKSPACE / CASE / "result.json")
        check(group["status"] == exported["group_execution"]["status"] == "attempts_recorded", "Group outcome mismatch")
        check(group["plan"] == workspace_record(GROUP + "/preparation/plan.json"), "Group plan digest mismatch")
        check(group["cases"]["N11"]["result"] == workspace_record(CASE + "/result.json"), "Native case digest mismatch")
        check(group["cases"]["N11"]["status"] == native_result["status"] == "failed", "Native failure was changed")
        check(group["cases"]["B7"] == skipped and skipped["status"] == "skipped", "Skipped case records differ")
        check(not (WORKSPACE / B7).exists(), "Skipped B7 has an allocated case directory")
        check(not (WORKSPACE / CASE / "client/admission").exists(), "Native control unexpectedly has an admission allocation")
        invocations = sorted(path.name for path in (WORKSPACE / GROUP / "attempt").glob("*.invocation.json"))
        check(invocations == ["N11.invocation.json"], "Unexpected live invocation inventory")
        check(group["live_model_calls"] == group["research_gate_credit_added"] == 0,
              "Unexpected model calls or research gate credit")

        # Import only after all copied source-byte identities have been checked.
        if report["failures"]:
            raise ValueError("Export integrity failed; retained code was not imported")
        sys.path[:0] = [str(WORKSPACE / "scripts"), str(WORKSPACE / "src")]
        bridge = importlib.import_module("check_agentops_bridge_v1")
        effects = importlib.import_module("check_agentops_effect_v2")
        diagnostics = importlib.import_module("check_agentops_bridge_diagnostic_v1")
        seed = effects.seed_snapshot(WORKSPACE / "external/agentops-c806b7f1/agents/data/incidents.db")
        service_check = bridge.check_service(WORKSPACE / CASE / "service", seed)
        native_check = bridge.check_case(WORKSPACE / CASE, seed)
        diagnostic_check = diagnostics.validate_diagnostics(WORKSPACE / CASE, native_check)
        write_new("N11-service-recheck.json", service_check)
        write_new("N11-case-recheck.json", native_check)
        write_new("N11-diagnostic-recheck.json", diagnostic_check)
        check(service_check == load(WORKSPACE / CASE / "check.json"), "Recomputed service classification differs")
        check(native_check == load(WORKSPACE / CASE / "case-check.json"), "Recomputed native classification differs")
        check(diagnostic_check == load(WORKSPACE / CASE / "diagnostic-check.json"), "Recomputed diagnostic classification differs")
        check(native_check["valid"] is True and native_check["complete"] is False
              and native_check["strict_success"] is False and native_check["outcome"] == "unknown_or_partial",
              "Native check is not the retained incomplete classification")
        check("service:terminal.snapshot_missing" in native_check["observation_gaps"], "Missing terminal snapshot gap disappeared")
        check(not (WORKSPACE / CASE / "service/terminal.snapshot.json").exists(), "Unexpected terminal snapshot")
        check(native_check["task_completed"] is True and native_check["effect_classification"] == "expected_single_effect",
              "Native task/effect evidence differs")
        check(diagnostic_check["valid"] is True and diagnostic_check["complete"] is True
              and diagnostic_check["classification"] == "post_asyncio_process_survival", "Diagnostic outcome differs")
        check(native_result["forced_service_stop"] is True and native_result["service_returncode"] == -15,
              "Forced SIGTERM outcome differs")
        cleanup = native_result["service_group_cleanup"]
        check(cleanup["forced_cleanup"] is True and cleanup["final_empty"] is False
              and any(row["state"] == "Z" for row in cleanup["final_members"]), "Cleanup bookkeeping differs")
        report["live_outcome"] = {"group_status": group["status"], "N11_status": native_result["status"],
                                  "N11_outcome": native_check["outcome"], "N11_strict_success": False,
                                  "N11_task_completed": native_check["task_completed"],
                                  "N11_effect_classification": native_check["effect_classification"],
                                  "N11_observation_gaps": native_check["observation_gaps"],
                                  "N11_diagnostic_classification": diagnostic_check["classification"],
                                  "N11_service_returncode": native_result["service_returncode"],
                                  "B7_status": skipped["status"], "B7_reason": skipped["reason"],
                                  "B7_directory_absent": not (WORKSPACE / B7).exists(), "candidate_live_calls": 0,
                                  "candidate_certificate_to_ASGI_check": "not_applicable_B7_was_not_executed",
                                  "live_model_calls": group["live_model_calls"], "research_gate_credit_added": 0,
                                  "diagnostic_root_cause_established": False}

        software = load(WORKSPACE / GROUP / "phase-software/result.json")
        check(software["status"] == "passed" and software["staged_sources_unchanged"] is True,
              "Retained software phase was not clean")
        python_count, node_count, cases = 0, 0, []
        for command in software["commands"]:
            directory = WORKSPACE / GROUP / "phase-software"
            check(command == load(directory / (command["name"] + ".receipt.json")), "Test command receipt mismatch")
            check(command["returncode"] == 0, "Retained test command failed: " + command["name"])
            for stream in command["streams"]:
                check(hashlib.sha256((directory / stream["path"]).read_bytes()).hexdigest() == stream["sha256"],
                      "Test stream digest mismatch: " + stream["path"])
            if command["name"].startswith("test_"):
                text = (directory / (command["name"] + ".stderr.bin")).read_text(encoding="utf-8")
                match = re.search(r"^Ran (\d+) tests? in .+\n\s*\nOK\s*$", text, re.MULTILINE)
                check(match is not None, "Missing clean unittest summary: " + command["name"])
                count = int(match[1]) if match else 0
                python_count += count
                cases.append({"suite": command["name"], "passed": count})
            else:
                text = (directory / "node-controller.stdout.bin").read_text(encoding="utf-8")
                metrics = {key: int(value) for key, value in re.findall(r"^# (tests|pass|fail|cancelled|skipped|todo) (\d+)$", text, re.MULTILINE)}
                check(metrics == {"tests": 26, "pass": 26, "fail": 0, "cancelled": 0, "skipped": 0, "todo": 0},
                      "Node test totals differ")
                node_count = metrics.get("pass", 0)
                cases.append({"suite": command["name"], "passed": node_count})
        check(python_count == 97 and node_count == 26, "Unexpected retained test totals")
        report["software_tests"] = {"evidence_only_not_rerun": True, "python_passed": python_count,
                                    "node_passed": node_count, "suites": cases}

        runtime_before = WORKSPACE / GROUP / "python-runtime-before.json"
        runtime_after = WORKSPACE / GROUP / "phase-after/python-runtime-after.stdout.bin"
        check(runtime_before.read_bytes() == runtime_after.read_bytes(), "Python runtime metadata changed")
        runtime = load(runtime_before)
        check(runtime["status"] == "installed_versions_match_lock" and runtime["application_imports"] == 0,
              "Runtime inspector status/scope differs")
        preparation = load(WORKSPACE / GROUP / "preparation/verification.json")
        after = load(WORKSPACE / GROUP / "phase-after/verify-prepared-inputs.stdout.bin")
        check(preparation["bridge"] == after["bridge"] == group["prepared_inputs_after"]["bridge"],
              "Before/after bridge verification differs")
        check(after["staged_files"] == 687 and after["bridge"]["files"] == 2938
              and after["bridge"]["links"] == 22, "Runtime/preparation counts differ")
        after_phase = load(WORKSPACE / GROUP / "phase-after/result.json")
        check(after_phase["status"] == "passed" and after_phase["python_runtime_equal"] is True
              and not after_phase["python_runtime_differing_keys"], "After-phase equality receipt differs")
        for command in after_phase["commands"]:
            directory = WORKSPACE / GROUP / "phase-after"
            check(command == load(directory / (command["name"] + ".receipt.json")) and command["returncode"] == 0,
                  "After-phase command receipt mismatch/failure")
            for stream in command["streams"]:
                check(hashlib.sha256((directory / stream["path"]).read_bytes()).hexdigest() == stream["sha256"],
                      "After-phase stream digest mismatch")
        report["runtime_evidence"] = {"python_inspection_before": record(runtime_before, WORKSPACE),
                                      "python_inspection_after": record(runtime_after, WORKSPACE),
                                      "python_inspection_bytes_equal": runtime_before.read_bytes() == runtime_after.read_bytes(),
                                      "bridge_verification_before_after_equal": preparation["bridge"] == after["bridge"],
                                      "bridge": after["bridge"], "external_runtime_reinspected_during_review": False,
                                      "scope": after["python_runtime_scope"]}
        imported = []
        for name, module in sorted(sys.modules.items()):
            if name.startswith(("check_agentops", "agentops_", "interoperability")) and getattr(module, "__file__", None):
                path = Path(module.__file__).resolve()
                check(path.is_relative_to(WORKSPACE), "Imported local module outside export: " + name)
                imported.append({"module": name, "source": record(path, WORKSPACE)})
        report["exported_modules_imported"] = imported
    except Exception as error:
        report["failures"].append(type(error).__name__ + ": " + str(error))
    finally:
        after = inventory(EXPORT)
        write_new("export-after.json", after)
        report["export_unchanged_during_review"] = before == after
        check(before == after, "Export bytes changed during review")
        report["finished_at_utc"] = now()
        report["status"] = "verified_expected_partial" if not report["failures"] else "review_discrepancies"
        report["review_files"] = [record(path, REVIEW) for path in sorted(REVIEW.iterdir()) if path.is_file()]
        write_new("result.json", report)
    print(json.dumps({key: report.get(key) for key in ("status", "integrity", "live_outcome", "software_tests", "export_unchanged_during_review", "failures")}, indent=2))
    return 0 if not report["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
