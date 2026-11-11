"""Independent read-only audit of retained release software components.

Executes only the trusted current pure bundle and certificate verifiers.
Never imports or executes captured application/provider/solver sources.
Writes new audit outputs exclusively and leaves all retained files unchanged.
"""
from __future__ import annotations

import copy
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE = ROOT / "runs/v1-release-software/v2-retained-43079771054-1"
EXTRACTED = BASE / "extracted"
RUN_ID = "43079771054"
HEAD = "577f34a82a32d3a891db2018a68823ba98f21e48"
ARCHIVE_SHA = "994131b2ce6f063c6a806c8cdf136b3412fe1b9a30fcf082be8a44c005aa3208"
METHODS = ("baseline", "direct_pruned", "candidate", "shared_lift")
LABELS = ("owned-timeout-controls", "complete-core-reproduction",
          "admission-demo-and-replay", "current-extra-controls", "complete-bank-validation")
EXTRA_MODULES = ("test_pending_admission", "test_task_bank_validation_v1",
                 "test_ap2_original_native_provider_semantics_v2",
                 "test_analyze_ap2_native_shopper_provider_v3", "test_ap2_native_shopper_provider_v4")
GOLD_KEYS = {"expected_facts", "expected_order", "expected_state", "reset",
             "legitimate_alternatives", "near_misses", "source_refs", "review_status"}
META = ("id", "split", "template_family", "distinct_obligation")
SPLITS = {"development": 6, "calibration": 4, "held_out": 24}
BOUND = {}


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON key: " + key)
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("Non-JSON numeric constant: " + value)


def decode(raw):
    return json.loads(raw, object_pairs_hook=unique, parse_constant=reject_constant)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def same(a, b, message):
    require(canonical(a) == canonical(b), message)


def stable(result):
    result = copy.deepcopy(result)
    if type(result.get("stats")) is dict:
        result["stats"].pop("elapsed_ns", None)
    return result


MANIFEST_RAW = (BASE / "extracted-manifest.json").read_bytes()
MANIFEST_LIST = decode(MANIFEST_RAW)["files"]
MANIFEST = {r["path"]: r for r in MANIFEST_LIST}
require(len(MANIFEST) == len(MANIFEST_LIST) == 12999, "Manifest count or duplicates")


def read(name):
    relative = PurePosixPath(name)
    require(not relative.is_absolute() and ".." not in relative.parts and "\\" not in name,
            "Unsafe retained path: " + name)
    path = EXTRACTED / name
    require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(EXTRACTED.resolve()),
            "Nonregular or escaped retained path: " + name)
    raw = path.read_bytes()
    expected = MANIFEST[name]
    actual = {"path": name, "bytes": len(raw), "sha256": digest(raw)}
    same(actual, expected, "Retained manifest mismatch: " + name)
    BOUND[name] = actual
    return raw


def load(name):
    return decode(read(name))


def check_record(prefix, record):
    raw = read(prefix + record["path"])
    require(len(raw) == record["bytes"] and digest(raw) == record["sha256"],
            "Embedded file identity mismatch: " + prefix + record["path"])
    return raw


def write_new(name, value):
    raw = (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    with (OUT / name).open("xb") as stream:
        stream.write(raw)
    return {"path": str((OUT / name).relative_to(ROOT)).replace("\\", "/"),
            "bytes": len(raw), "sha256": digest(raw)}


def check_group(receipt, *, normal):
    group = receipt["owned_group"]
    require(receipt["new_owned_session"] is True and group["pgid"] == receipt["pid"],
            "Owned command session/PID mismatch")
    require(group["parent_reaped"] is True and group["final_empty"] is True,
            "Unclosed owned group")
    require(group["unexpected_members_after_normal_exit"] is False, "Unexpected descendants")
    snapshots = group["snapshots"]
    require(snapshots[0]["phase"] == "initial" and snapshots[-1]["phase"] == "final"
            and snapshots[-1]["members"] == [], "Missing final empty snapshot")
    same(snapshots[0]["members"], group["initial_members"], "Initial members mismatch")
    ticks = [x["monotonic_ns"] for x in snapshots]
    require(ticks == sorted(ticks), "Process snapshots out of order")
    if normal:
        require(receipt["returncode"] == 0 and receipt["timed_out"] is False
                and group["timed_out"] is False and group["signals"] == []
                and group["initial_members"] == [], "Normal command lifecycle mismatch")
    else:
        require(receipt["timed_out"] is True and group["timed_out"] is True,
                "Timeout not retained")
    require(receipt["coordinator_source_unchanged"] is True, "Coordinator source drift")
    same(receipt["coordinator_source_before"], receipt["coordinator_source_after"], "Coordinator inventory drift")
    for record in receipt["coordinator_source_before"]:
        check_record("software/source/", record)
    return {"pid": receipt["pid"], "returncode": receipt["returncode"],
            "timed_out": receipt["timed_out"], "signals": group["signals"],
            "parent_reaped": True, "final_empty": True,
            "adopted_children_reaped": group["adopted_children_reaped"]}


def audit_commands(plan, result):
    require(result["scheduled_commands"] == 5 and len(result["commands"]) == 5, "Incomplete commands")
    same([c["label"] for c in result["commands"]], list(LABELS), "Command allocation differs")
    same(plan["extra_test_modules"], list(EXTRA_MODULES), "Extra modules differ")
    groups = []
    for embedded in result["commands"]:
        label = embedded["label"]
        process = load("software/commands/" + label + "/process.json")
        projected = {k: v for k, v in embedded.items() if k != "validated_outcome"}
        same(process, projected, "Embedded/process command mismatch: " + label)
        groups.append({"label": label, **check_group(process, normal=True)})
        for stream in ("stdout", "stderr"):
            check_record("software/", process[stream])
        if "validated_outcome" in embedded:
            check_record("software/", embedded["validated_outcome"])
    require(result["outer_owned_groups_confirmed_closed"] is True, "Outer closure absent")
    same(result["source_after"], plan["source"], "Software source inventory drift")
    require(len(plan["source"]) == 819, "Software input inventory count")
    require(result["sources_unchanged"] is True and result["captured_sources_unchanged"] is True
            and result["captured_source_matches_preflight"] is True, "Software capture failure")
    controls = decode(read("software/commands/current-extra-controls/stdout.bin"))
    expected_controls = {"tests_run": 57, "errors": 0, "failures": 0, "skipped": 0, "successful": True}
    same(controls, expected_controls, "Extra control failure")
    same(result["extra_controls"], controls, "Extra controls embedded mismatch")
    command = next(c for c in result["commands"] if c["label"] == "current-extra-controls")
    same(command["argv"][-5:], list(EXTRA_MODULES), "Executed extra modules differ")
    stderr = read("software/commands/current-extra-controls/stderr.bin").decode("utf-8")
    tests = re.findall(r"^test_.* \(([^)]+)\) \.\.\. ok$", stderr, re.M)
    require(len(tests) == 57 and len(set(tests)) == 57 and "Ran 57 tests" in stderr
            and stderr.rstrip().endswith("OK"), "Extra stderr test result mismatch")
    modules = Counter(name.split(".")[0] for name in tests)
    same(sorted(modules), sorted(EXTRA_MODULES), "Extra module coverage mismatch")
    return {"commands": groups, "source_inventory_count": 819,
            "extra_controls": controls, "extra_module_test_counts": dict(modules)}


def audit_timeouts():
    report = load("software/timeouts/result.json")
    require(report["status"] == "passed" and report["tests_run"] == 5
            and report["failures"] == report["errors"] == report["skips"] == 0,
            "Timeout controls failed")
    require(report["source_unchanged"] is True and report["captured_source_unchanged"] is True,
            "Timeout source changed")
    same(report["source_before"], report["source_after"], "Timeout source before/after")
    same(report["captured_source_before"], report["captured_source_after"], "Timeout captured inventory")
    for record in report["captured_source_before"]:
        check_record("software/timeouts/", record)
    stderr = read("software/timeouts/tests.stderr.bin").decode("utf-8")
    require(len(re.findall(r"^test_.* \.\.\. ok$", stderr, re.M)) == 5
            and "Ran 5 tests" in stderr and stderr.rstrip().endswith("OK"), "Timeout stderr mismatch")
    require(read("software/timeouts/tests.stdout.bin") == b"", "Unexpected timeout test stdout")
    output = []
    for name, signal in [("test_normal_output_and_return_code_are_preserved", None),
                         ("test_sigterm_ignoring_group_is_killed_and_reaped", "SIGKILL"),
                         ("test_timeout_reaps_coordinator_and_delayed_child_before_return", "SIGTERM")]:
        prefix = "software/timeouts/" + name + "/"
        label = "normal" if signal is None else "timeout"
        process = load(prefix + "commands/" + label + "/process.json")
        lifecycle = check_group(process, normal=signal is None)
        stdout = check_record(prefix, process["stdout"])
        stderr_raw = check_record(prefix, process["stderr"])
        if signal is None:
            require(stdout == b"normal-output\n" and stderr_raw == b"normal-error\n", "Normal streams lost")
        else:
            require(process["returncode"] == (-9 if signal == "SIGKILL" else -15), "Timeout return code differs")
            same(process["owned_group"]["signals"], ["SIGTERM", "SIGKILL"] if signal == "SIGKILL" else ["SIGTERM"],
                 "Timeout signal escalation differs")
            pids = decode(stdout)
            same(sorted(x["pid"] for x in process["owned_group"]["initial_members"]),
                 sorted(pids.values()), "Timeout child PIDs differ")
            require(pids["coordinator_pid"] == process["pid"], "Coordinator PID mismatch")
            adopted = process["owned_group"]["adopted_children_reaped"]
            require(len(adopted) == 1 and adopted[0]["pid"] == pids["child_pid"]
                    and adopted[0]["wait_status"] == (9 if signal == "SIGKILL" else 15), "Child reap mismatch")
            marker = load(prefix + "delayed-marker-check.json")
            require(marker["coordinator_pid"] == pids["coordinator_pid"] and marker["child_pid"] == pids["child_pid"]
                    and marker["marker_exists"] is False and marker["group_members_after_wait"] == []
                    and marker["open_groups"] == [] and marker["subreaper_state_restored"] is True
                    and marker["wait_after_return_seconds"] > marker["child_marker_delay_seconds"],
                    "Delayed child survived or restoration mismatch")
            require(prefix + "late-marker.txt" not in MANIFEST and not (EXTRACTED / prefix / "late-marker.txt").exists(),
                    "Late marker retained")
        output.append({"control": name, **lifecycle})
    return {"tests_run": 5, "retained_group_controls": output, "application_runs": 0, "model_calls": 0,
            "scope": "Retained Linux process-group controls; no native application qualification"}


def walk(value):
    if type(value) is dict:
        yield value
        for child in value.values():
            yield from walk(child)
    elif type(value) is list:
        for child in value:
            yield from walk(child)


def audit_bank():
    report = load("software/bank-validation.json")
    require(report["status"] == "structurally_valid" and report["total_templates"] == 68
            and report["allocation_complete"] is True and report["semantic_or_runtime_qualification_claimed"] is False,
            "Bank qualification mismatch")
    require(len(report["inputs"]) == 4, "Bank input count")
    for record in report["inputs"]:
        check_record("software/source/", record)
    output = []
    for domain in ("agentops", "ap2"):
        prefix = "software/source/benchmark/tasks-v1/" + domain + "/"
        application, evaluator = load(prefix + "application.json"), load(prefix + "evaluator.json")
        same(application["source_pin"], evaluator["source_pin"], "Task bank source pin mismatch")
        expected_qualification = {"human_review": "pending", "runtime_execution": "not_executed", "gold_validation": "pending"}
        same(application["qualification"], expected_qualification, "Public qualification differs")
        same(evaluator["qualification"], expected_qualification, "Gold qualification differs")
        public, gold = application["records"], evaluator["records"]
        require(len(public) == len(gold) == 34, "Bank template count: " + domain)
        same([r["id"] for r in public], [r["id"] for r in gold], "Public/gold ordered IDs differ")
        for records in (public, gold):
            for field in ("id", "template_family", "distinct_obligation"):
                values = [r[field] for r in records]
                require(all(type(v) is str and v.strip() for v in values) and len(set(values)) == 34,
                        "Non-distinct bank field: " + field)
        counts = dict(Counter(r["split"] for r in public))
        same(counts, SPLITS, "Bank split allocation mismatch")
        files, ranges, statuses = {}, set(), Counter()

        def source(name, expected):
            if name not in files:
                raw = read("software/source/" + name)
                files[name] = {"sha256": digest(raw), "bytes": len(raw), "line_count": len(raw.splitlines())}
            require(files[name]["sha256"] == expected, "Bank source hash differs: " + name)
            return files[name]

        for pin in application["source_pin"].get("data_files", []):
            source(pin["path"], pin["sha256"])
        if "seed_database" in application["source_pin"]:
            pin = application["source_pin"]["seed_database"]
            source(pin["path"], pin["sha256"])
        for a, g in zip(public, gold):
            same({k: a[k] for k in META}, {k: g[k] for k in META}, "Bank metadata differs")
            require(set(a) == set(META) | {"public"}, "Public top-level fields leak evaluator")
            require(type(a["public"]) is dict and a["public"], "Empty public task")
            require(all(not GOLD_KEYS.intersection(item) for item in walk(a["public"])), "Gold fields in public task")
            require(all(g.get(k) for k in GOLD_KEYS), "Missing gold obligation")
            registry = g["source_refs"]
            for label, ref in registry.items():
                info = source(ref["path"], ref["sha256"])
                bounds = ref["lines"]
                require(type(bounds) is list and len(bounds) == 2 and all(type(x) is int for x in bounds)
                        and 1 <= bounds[0] <= bounds[1] <= info["line_count"], "Bank source range invalid")
                ranges.add((ref["path"], ref["sha256"], *bounds))
            for field in GOLD_KEYS - {"source_refs", "review_status"}:
                for claim in (item for item in walk(g[field]) if "claim" in item):
                    require(type(claim["claim"]) is str and claim["claim"].strip(), "Empty gold claim")
                    refs, status = claim["source_refs"], claim["status"]
                    require(type(refs) is list and set(refs) <= set(registry), "Unbound gold claim")
                    require(status in {"source_supported", "pending_human_judgment"}
                            and (status != "source_supported" or refs), "Invalid gold claim status")
                    statuses[status] += 1
        derived = {"domain": domain, "structural_status": "valid", "templates": 34, "split_counts": counts,
                   "missing_slots": {k: 0 for k in SPLITS}, "allocation_complete": True,
                   "source_files_checked": len(files), "source_ranges_checked": len(ranges),
                   "claims_checked": sum(statuses.values()), "claim_statuses": dict(statuses), "source_files": files,
                   "review_statuses": dict(Counter(r["review_status"] for r in gold)),
                   "qualification": expected_qualification, "runtime_execution_performed": False,
                   "gold_semantics_validated": False, "independent_holdout_sealed": False,
                   "research_checkpoint_credit_added": 0}
        retained = next(d for d in report["domains"] if d["domain"] == domain)
        same(derived, retained, "Bank report differs from independent reconstruction: " + domain)
        output.append({k: v for k, v in derived.items() if k != "source_files"})
    return {"total_templates": 68, "inputs_bound": report["inputs"], "domains": output,
            "semantic_or_runtime_qualification_claimed": False}


def audit_demo():
    plan, result = load("software/demo/plan.json"), load("software/demo/result.json")
    inspection = load("software/demo/inspection.json")
    names = ("supported", "unsupported", "unknown", "budget-unknown", "benchmark", "verify", "replay", "verify-replay")
    same([s["name"] for s in plan["steps"]], list(names), "Demo steps differ")
    same([s["name"] for s in result["steps"]], list(names), "Demo receipt steps differ")
    require(result["status"] == "passed" and result["errors"] == [] and result["inputs_unchanged"] is True,
            "Demo result failed")
    require(len(plan["inputs"]) == 93, "Demo input inventory count")
    same(plan["inputs"], result["inputs_after"], "Demo original input drift")
    same(plan["inputs"], result["frozen_inputs_after"], "Demo frozen input drift")
    for record in plan["inputs"]:
        check_record("software/source/", record)
        check_record("software/demo/prepared/", record)
    sys.path.insert(0, str(ROOT / "src"))
    from interoperability import shared_lifting_comparison_v3 as verifier
    from interoperability import direct_goal_pruned_v2 as checker
    verifications = {}
    for name in ("benchmark", "replay"):
        # Only the current trusted read-only verifier is called. It does not
        # dispatch the retained sources or freshly execute the algorithms.
        bundle = EXTRACTED / "software/demo" / name
        verification = verifier.verify(bundle)
        require(verification["status"] == "passed" and verification["files_verified"] == 511
                and verification["case_records"] == 11 and verification["worker_jobs_bound"] == 83
                and verification["certificate_jobs_bound"] == 28 and verification["fresh_algorithm_execution"] is False,
                "Trusted demo bundle verification failed")
        for entry in load("software/demo/" + name + "/manifest.json")["files"]:
            check_record("software/demo/" + name + "/", entry)
        recorded = load("software/demo/" + ("verify" if name == "benchmark" else "verify-replay") + ".stdout.json")
        same(verification, recorded, "Fresh pure verification differs from recorded result")
        verifications[name] = write_new(name + "-pure-verification.json", verification)
    rows = {name: [decode(line) for line in read("software/demo/" + name + "/results.jsonl").splitlines()]
            for name in ("benchmark", "replay")}
    require(len(rows["benchmark"]) == len(rows["replay"]) == 11, "Demo row count")
    checks = 0
    for first, second in zip(rows["benchmark"], rows["replay"]):
        for key in ("case_id", "model_sha256", "input_schema", "family", "evaluation_clock", "provenance", "reference_valid"):
            same(first[key], second[key], "Replay row identity mismatch: " + key)
        same(load("software/demo/benchmark/" + first["input_snapshot"]),
             load("software/demo/replay/" + second["input_snapshot"]), "Replay input snapshot differs")
        same(stable(first["reference"]["result"]), stable(second["reference"]["result"]), "Replay reference result differs")
        same(sorted(first["algorithms"]), sorted(METHODS), "Demo method set differs")
        for method in METHODS:
            a, b = first["algorithms"][method], second["algorithms"][method]
            same(stable(a["execution"]["result"]), stable(b["execution"]["result"]), "Replay algorithm differs")
            for key in ("certificate_valid", "status", "valid_result", "decision_agreement"):
                same(a[key], b[key], "Replay outcome metadata differs")
            require(("certificate_check" in a) == ("certificate_check" in b), "Replay certificate presence differs")
            if "certificate_check" in a:
                same(a["certificate_check"]["result"], b["certificate_check"]["result"], "Replay checker differs")
                checks += 1
    replay = {"status": "passed", "cases": 11, "algorithm_results_compared": 44,
              "reference_results_compared": 11, "excluded_result_fields": ["stats.elapsed_ns"]}
    same(replay, load("software/demo/replay-comparison.json"), "Replay report differs")
    same(replay, result["replay_comparison"], "Embedded replay differs")
    by_id = {r["case_id"]: r for r in rows["benchmark"]}
    standalone = []
    for step, embedded in zip(plan["steps"], result["steps"]):
        name = step["name"]
        same(embedded, load("software/demo/" + name + "-command.json"), "Demo embedded receipt differs")
        same(step["argv"], embedded["argv"], "Demo planned/actual argv differs")
        require(embedded["status"] == "passed" and embedded["returncode"] == 0, "Demo step failed")
        require(read("software/demo/" + name + ".stderr.txt") == b"", "Demo unexpected stderr")
        stdout = load("software/demo/" + name + ".stdout.json")
        if step["kind"] == "admit":
            receipt = load("software/demo/" + name + ".json")
            input_relative = receipt["input_path"].split("/software/demo/prepared/", 1)[1]
            raw = read("software/demo/prepared/" + input_relative)
            model = decode(raw)
            same(model, receipt["runtime_manifest"], "Admission model differs")
            require(receipt["input_path"] == step["input"] and receipt["input_sha256"] == digest(raw)
                    and receipt["model_sha256"] == digest(canonical(model).encode("utf-8")), "Admission input identity mismatch")
            require(receipt["status"] == "recorded" and receipt["method"] == "shared_lift"
                    and receipt["solver_module"] == "interoperability.refinement_shared_lift_v2"
                    and receipt["checker_module"] == "interoperability.direct_goal_pruned_v2"
                    and receipt["checker_entrypoint"] == "check_certificate"
                    and receipt["evaluation_clock"] == 100 and receipt["work_budget"] == step["budget"]
                    and receipt["result"]["decision"] == step["decision"], "Admission scope/outcome mismatch")
            for filename, sha in receipt["source_sha256"].items():
                require(digest(read("software/demo/prepared/src/interoperability/" + filename)) == sha,
                        "Admission source identity differs")
            expected_stdout = {"status": receipt["status"], "method": receipt["method"],
                               "case": model.get("id"), "decision": receipt["result"]["decision"],
                               "reason": receipt["result"]["reason"], "work_budget": receipt["work_budget"],
                               "certificate_valid": receipt["certificate_valid"], "error": receipt.get("error"),
                               "output": step["output"]}
            same(stdout, expected_stdout, "Admission stdout projection differs")
            same(embedded["validated_outcome"], {"decision": step["decision"], "certificate_valid": receipt["certificate_valid"]},
                 "Admission validated outcome differs")
            if step["decision"] == "unknown":
                require(receipt["certificate_valid"] is None and receipt["result"]["certificate"] is None
                        and receipt["checker_invoked"] is False and receipt["unknown_has_no_certificate"] is True,
                        "Unknown admission carried a certificate")
            else:
                before_model, before_result = canonical(model), canonical(receipt["result"])
                accepted = checker.check_certificate(model, receipt["result"], 100)
                require(accepted is True and receipt["certificate_valid"] is True and receipt["checker_invoked"] is True,
                        "Admission certificate rejected")
                require(canonical(model) == before_model and canonical(receipt["result"]) == before_result,
                        "Pure checker mutated retained values")
            if name == "budget-unknown":
                require(receipt["result"]["reason"] == "work_budget_exhausted" and receipt["work_budget"] == 1,
                        "Budget exhaustion example missing")
                same(receipt["result"], inspection["budget_exhaustion_result"], "Inspection budget result differs")
            else:
                row = by_id[model["id"]]
                same(stable(receipt["result"]), stable(row["algorithms"]["shared_lift"]["execution"]["result"]),
                     "Standalone and benchmark disagree")
                example = next(e for e in inspection["examples"] if e["standalone_receipt"] == name + ".json")
                same(example["result"], row["algorithms"]["shared_lift"]["execution"]["result"], "Inspection result differs")
                same(example["certificate_valid"], receipt["certificate_valid"], "Inspection certificate differs")
                if example["certificate_reply"] is not None:
                    same(example["certificate_check"], load("software/demo/" + example["certificate_reply"]),
                         "Inspection retained checker differs")
            require(receipt["application_requests"] == receipt["live_model_calls"] == 0, "Admission executed application/provider")
            standalone.append({"name": name, "decision": step["decision"], "certificate_valid": receipt["certificate_valid"],
                               "input_sha256": receipt["input_sha256"], "model_sha256": receipt["model_sha256"],
                               "reason": receipt["result"]["reason"], "work_budget": receipt["work_budget"]})
        else:
            verified = stdout["verification"] if step["kind"] in ("run", "replay") else stdout
            projected = {k: verified[k] for k in ("benchmark_status", "case_records", "worker_jobs_bound", "certificate_jobs_bound")}
            same(projected, embedded["validated_outcome"], "Demo benchmark validated outcome differs")
            if step["kind"] in ("run", "replay"):
                same(stdout["summary"], load("software/demo/" + name + "/summary.json"), "Demo stdout summary differs")
                require(stdout["bundle"] == step["output"] and stdout["source_package"] == step["source_package"]
                        and stdout["status"] == "passed", "Demo bundle identity differs")
    summary = load("software/demo/benchmark/summary.json")
    for method in METHODS:
        same(inspection["algorithms"][method], {k: summary["algorithms"][method][k] for k in inspection["algorithms"][method]},
             "Inspection algorithm summary differs")
    require(result["application_requests"] == result["live_model_calls"] == 0, "Demo executed application/provider")
    trusted_sources = []
    for name, module in sorted(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if filename and name.startswith("interoperability"):
            path = Path(filename).resolve()
            if path.is_relative_to(ROOT / "src"):
                rel = path.relative_to(ROOT).as_posix()
                raw = path.read_bytes()
                require(raw == read("software/source/" + rel), "Trusted verifier import differs from captured input: " + rel)
                trusted_sources.append({"path": rel, "bytes": len(raw), "sha256": digest(raw)})
    return {"steps": 8, "input_inventory_count": 93, "standalone_admissions": standalone,
            "bundles": {n: {"case_records": 11, "worker_jobs_bound": 83, "certificate_jobs_bound": 28,
                             "files_verified": 511, "verification_artifact": a} for n, a in verifications.items()},
            "replay": {**replay, "checker_results_compared": checks}, "trusted_verifier_sources": trusted_sources,
            "fresh_algorithm_execution": False, "application_requests": 0, "live_model_calls": 0}


def main():
    require(not (OUT / "review.json").exists(), "Preserve previous review")
    archive = (BASE / "artifact.zip").read_bytes()
    require(len(archive) == 16754100 and digest(archive) == ARCHIVE_SHA, "Archive identity differs")
    plan, result = load("software/plan.json"), load("software/result.json")
    same(plan["github"], {"GITHUB_SHA": HEAD, "GITHUB_RUN_ID": RUN_ID, "GITHUB_RUN_ATTEMPT": "1",
                          "RUNNER_OS": "Linux", "RUNNER_ARCH": "X64"}, "Run/head/runtime identity differs")
    require(result["status"] == "passed" and result["application_calls"] == result["provider_calls"] == 0
            and result["human_review"] is False and result["whole_original_research_project_complete"] is False,
            "Software acceptance scope differs")
    commands = audit_commands(plan, result)
    timeouts = audit_timeouts()
    bank = audit_bank()
    demo = audit_demo()
    report = {"schema_version": "research-v1-release-independent-component-review/1", "status": "verified",
              "reviewed_at_utc": datetime.now(timezone.utc).isoformat(), "run_id": RUN_ID, "run_attempt": "1", "head_sha": HEAD,
              "retained_base": BASE.relative_to(ROOT).as_posix(), "archive_bytes": len(archive), "archive_sha256": ARCHIVE_SHA,
              "api_artifact_id": "13885085260", "extracted_manifest_sha256": digest(MANIFEST_RAW),
              "extracted_manifest_count": len(MANIFEST_LIST), "commands": commands, "timeout_controls": timeouts,
              "task_bank": bank, "demo": demo, "retained_files_bound_count": len(BOUND),
              "retained_files_bound": [BOUND[k] for k in sorted(BOUND)],
              "reviewer_source": {"path": Path(__file__).relative_to(ROOT).as_posix(), "sha256": digest(Path(__file__).read_bytes())},
              "review_original_application_executions": 0, "review_provider_calls": 0,
              "captured_source_execution": False, "fresh_algorithm_execution": False,
              "independent_human_review": False, "scientific_gate_credit": 0,
              "scope_limits": ["Independent AI retained software component review; no human gold review or human task scoring",
                               "No novelty, superiority, held-out scientific-study or whole-original-project completion credit",
                               "Timeout controls prove recorded Linux owned process groups only",
                               "Earlier failed release run 43076696650 remains retained and is not replaced"]}
    identity = write_new("review.json", report)
    print(json.dumps({"status": "verified", "report": identity, "bound_files": len(BOUND), "demo_steps": 8,
                      "extra_controls": 57, "bank_templates": 68, "fresh_algorithm_execution": False}, indent=2))


if __name__ == "__main__":
    main()
