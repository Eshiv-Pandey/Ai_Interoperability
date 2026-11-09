"""One read-only assessment of the consumed AP2 install and five docs collisions.

Never installs, repairs RECORD/files, imports original roles, processes installed
.pth files, opens credentials or makes model calls. Pip check is Job-owned.
"""
from __future__ import annotations
import base64
import csv
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
from pathlib import Path, PurePosixPath
import sys
import time
import types
import zipfile

ROOT = Path(__file__).absolute().parents[1]
INSTALL = ROOT / "runs/ap2-environment-preparation/installed-environment-v1"
OUTPUT = ROOT / "runs/ap2-environment-preparation/installed-assessment-v1"
PINS = {
    "result.json": "a0da20bed66d81c372affa54c40703d382d09bdbff911fd3419e7ea21a315608",
    "plan.json": "90595ab31a3198d7cb7e811aa2ee35fe83fd2497f12a5cf6fdfd48312f4bfb0b",
    "installer-report.json": "6b692f4235601e6c54e29962399df57f5b5d14afad2419964ee11305fc3c137b",
    "installed-record-diagnostic-v1.json": "28a7e534a7d153367dd03eb07ee8c3ecd03f90587e274488850dc80c13f64f22",
    "record-collision-wheel-comparison-v1.json": "b8521aa449121fc5fb47e406b3aa38371f8e054a999f70bcbc0d8e66553df46f",
    "installer-driver.py": "3d747d9c3a0f45dca2822cb4fc3e6896ba44bdc020e622f54decef4f24149bbe",
    "owned-job-helper.py": "67b5dc8190aee3a75b3c1954a530d0bba3edeb3bc64dc2770dd815173ecbd53a",
    "initial-environment-files.json": "66c3fbbb8f59b38effd8d530c40acfc23360aab027b53531de40164689b360b1",
    "pip-tooling-files.json": "248b57083bc7c03fdcad469b9e01a172acb2b375652217e715eaf5d36c1eaad4",
}
DOCS = {"docs/Makefile", "docs/conf.py", "docs/contributing.rst", "docs/index.rst", "docs/release_notes.rst"}
OWNERS = {"eth-abi", "eth-rlp", "hexbytes"}
PACKAGES = {"google-adk": "1.28.0", "a2a-sdk": "0.3.24", "google-genai": "1.66.0", "pydantic": "2.12.5"}


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def notice(value):
    try:
        print(json.dumps(value), flush=True)
    except BaseException:
        pass


def load(raw, path, name):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def run():
    need(not OUTPUT.exists(), "Read-only assessment allocation is consumed")
    bodies = {name: (INSTALL / name).read_bytes() for name in PINS}
    need(all(sha(bodies[name]) == expected for name, expected in PINS.items()), "Pinned consumed install/forensic input changed")
    helper = load(bodies["installer-driver.py"], INSTALL / "installer-driver.py", "_ap2_assessment_installer")
    helper.regular(OUTPUT.parent, True)
    result, plan = json.loads(bodies["result.json"]), json.loads(bodies["plan.json"])
    need(result["status"] == "offline_environment_not_established" and result["failure"] == {"error_type": "ValueError", "message": "Installed RECORD file hash/size differs"}
        and result["owned_job_authority_remaining"] is False and len(result["commands"]) == 2
        and all(row["passed"] is True and row["cleanup"]["job_empty_observed"] is True and row["cleanup"]["handles_closed"] is True and row["cleanup"]["errors"] == [] for row in result["commands"]), "Consumed install is not the exact settled RECORD-only failure")
    need(len(plan["wheels"]) == 187 and len({row["name"] for row in plan["wheels"]}) == 187, "Exact187 selected wheels required")
    ENV, SITE = INSTALL / "environment", INSTALL / "environment/Lib/site-packages"
    argv = [sys.executable, "-I", "-S", "-B", str(INSTALL / "installer-driver.py"), "--phase", "pip", "--pip-root", str(INSTALL / "tooling/pip-sources"), "--site-packages", str(SITE), "--",
            "--isolated", "--disable-pip-version-check", "--no-cache-dir", "--no-input", "check"]
    OUTPUT.mkdir()
    (OUTPUT / "input-snapshots").mkdir()
    (OUTPUT / "temporary").mkdir()
    for name, raw in bodies.items():
        (OUTPUT / "input-snapshots" / name).write_bytes(raw)
    (OUTPUT / "assessment-driver.py").write_bytes(Path(__file__).read_bytes())
    write(OUTPUT / "plan.json", {"schema_version": "ap2-readonly-installed-assessment-plan/1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
          "inputs": PINS, "environment_root": str(ENV), "output_root": str(OUTPUT), "driver_sha256": sha(Path(__file__).read_bytes()), "pip_check_argv": argv,
          "allowed_collision_paths": sorted(DOCS), "collision_owners": sorted(OWNERS), "winner": "eth-abi", "record_mismatches_expected": 10,
          "scope": "Read-only source payload/metadata/tree and dependency assessment; no installation/repair/original import/native compatibility claim."})
    held, failure, command = [], None, None
    try:
        before = helper.tree(ENV)
        initial = json.loads(bodies["initial-environment-files.json"])
        need(all(before[name] == value for name, value in initial.items()), "Initial venv files changed")
        expected = {row["name"]: row for row in plan["wheels"]}
        diagnostic = json.loads(bodies["installed-record-diagnostic-v1.json"])
        comparison = json.loads(bodies["record-collision-wheel-comparison-v1.json"])
        need(diagnostic["record_rows"] == 15281 and diagnostic["algorithms"] == {"sha256": 15094} and diagnostic["mismatch_count"] == 10
            and {row["file"] for row in diagnostic["mismatches"]} == DOCS and set(comparison["paths"]) == DOCS, "Only the exact observed10 rows/5docs may differ")
        for name, owners in comparison["paths"].items():
            need(len(owners) == 3 and {row["distribution"] for row in owners} == OWNERS
                and all(row["wheel_record_matches_payload"] is True for row in owners)
                and {row["distribution"] for row in owners if row["installed_payload_matches_this_wheel"]} == {"eth-abi"}, "Exact frozen three-owner docs ledger required")
        distributions, recorded, mismatches, rows = {}, set(), [], 0
        for distribution in metadata.distributions(path=[str(SITE)]):
            name, version = helper.normalized(distribution.metadata["Name"]), distribution.version
            need(name in expected and name not in distributions and version == expected[name]["version"], "Installed187 distribution identity differs")
            meta_path = Path(distribution._path) / "METADATA"
            need(sha(meta_path.read_bytes()) == expected[name]["metadata"]["metadata_sha256"], "Selected wheel METADATA differs")
            record_path = Path(distribution._path) / "RECORD"
            for filename, encoded_hash, size in csv.reader(record_path.read_text(encoding="utf-8").splitlines()):
                rows += 1
                path = (SITE / filename).resolve()
                need(path.is_relative_to(ENV), "RECORD escapes environment")
                relative = path.relative_to(ENV).as_posix()
                need(relative in before, "RECORD refers to absent/unverified file")
                actual = before[relative]
                if encoded_hash:
                    algorithm, declared = encoded_hash.split("=", 1)
                    need(algorithm == "sha256" and size.isdecimal(), "Unexpected RECORD hash/size encoding")
                    value = base64.urlsafe_b64encode(bytes.fromhex(actual["sha256"])).rstrip(b"=").decode()
                    if declared != value or int(size) != actual["bytes"]:
                        mismatches.append({"record": record_path.relative_to(INSTALL).as_posix(), "file": filename, "algorithm": algorithm,
                            "hash_matches": declared == value, "size_matches": int(size) == actual["bytes"], "declared_hash": declared,
                            "actual_hash": value, "declared_bytes": size, "actual_bytes": actual["bytes"]})
                else:
                    need(path == record_path.resolve() and not size, "Unhashed file other than own RECORD")
                recorded.add(relative)
            distributions[name] = {"version": version, "metadata_sha256": sha(meta_path.read_bytes()), "record_sha256": sha(record_path.read_bytes()),
                "requires_python": distribution.metadata.get("Requires-Python"), "requires_dist": distribution.metadata.get_all("Requires-Dist", []),
                "wheel_filename": expected[name]["filename"], "wheel_sha256": expected[name]["sha256"], "origin": expected[name]["origin"]}
        order = lambda row: (row["record"], row["file"])
        need(set(distributions) == set(expected) and rows == 15281 and sorted(mismatches, key=order) == sorted(diagnostic["mismatches"], key=order), "Current RECORD assessment differs from the exact10 pinned collision rows")
        need(set(before) - set(initial) <= recorded, "Installed file not covered by selected distribution RECORD")
        counts, exemptions, scripts = {}, [], []
        for wheel in plan["wheels"]:
            path = INSTALL / "wheels" / wheel["filename"]
            need(sha(path.read_bytes()) == wheel["sha256"], "Frozen selected wheel bytes changed")
            count = {"payload_files_exact": 0, "module_files_exact": 0, "docs_collision_loser_files": 0, "relocated_scripts_verified": 0, "regenerated_top_level_records_excluded": 0}
            with zipfile.ZipFile(path) as archive:
                for member in archive.namelist():
                    if member.endswith("/"):
                        continue
                    parts = PurePosixPath(member).parts
                    if member.endswith(".dist-info/RECORD") and len(parts) == 2:
                        count["regenerated_top_level_records_excluded"] += 1
                        continue
                    payload = archive.read(member)
                    target, scheme = SITE / member, None
                    if parts[0].endswith(".data"):
                        scheme = parts[1]
                        need(scheme in {"data", "scripts", "purelib", "platlib"}, "Unreviewed wheel relocation scheme")
                        target = {"data": ENV, "scripts": ENV / "Scripts", "purelib": SITE, "platlib": SITE}[scheme].joinpath(*parts[2:])
                    relative = target.relative_to(ENV).as_posix()
                    need(relative in before, "Selected wheel payload missing in environment")
                    actual = before[relative]
                    identical = actual == {"bytes": len(payload), "sha256": sha(payload)}
                    if not identical and member in DOCS and wheel["name"] in {"eth-rlp", "hexbytes"}:
                        winner = next(row for row in comparison["paths"][member] if row["distribution"] == "eth-abi")
                        need(actual == {"bytes": winner["wheel_payload_bytes"], "sha256": winner["wheel_payload_sha256"]}, "Docs winner bytes changed")
                        count["docs_collision_loser_files"] += 1
                        exemptions.append({"distribution": wheel["name"], "member": member, "source_sha256": sha(payload), "installed_winner": "eth-abi", **actual})
                    elif not identical and scheme == "scripts":
                        original_first, original_body = payload.split(b"\n", 1)
                        actual_first, actual_body = target.read_bytes().split(b"\n", 1)
                        need(original_first in {b"#!python", b"#!pythonw"}, "Unsupported source script shebang")
                        target_interpreter = "pythonw.exe" if original_first == b"#!pythonw" else "python.exe"
                        need(actual_first == b"#!" + str(ENV / ("Scripts/" + target_interpreter)).encode()
                            and original_body == actual_body, "Relocated script changed beyond exact supported interpreter shebang")
                        count["relocated_scripts_verified"] += 1
                        scripts.append({"distribution": wheel["name"], "member": member, "installed": relative, "body_exact": True, "target_interpreter_verified": True})
                    else:
                        need(identical, "Installed wheel payload differs outside exactdocs/shebang cases: " + wheel["name"] + ":" + member)
                        count["payload_files_exact"] += 1
                        if target.is_relative_to(SITE) and target.suffix in {".py", ".pyd", ".so"}:
                            count["module_files_exact"] += 1
            counts[wheel["name"]] = count
        need(len(exemptions) == 10, "Exact10 docs loser payloads required")
        for name in set(before) - set(initial):
            if name.startswith("Scripts/") and name.endswith(".exe"):
                need(any(str(ENV / ("Scripts/" + interpreter)).encode() in (ENV / name).read_bytes() for interpreter in ("python.exe", "pythonw.exe")), "Generated script interpreter differs")
        write(OUTPUT / "source-payload-provenance.json", {"distributions": counts, "docs_collision_exemptions": exemptions, "relocated_scripts": scripts,
            "all_other_selected_wheel_payloads_exact": True, "all_record_entries_match": False, "record_mismatch_count": 10,
            "payload_match_scope": "Archive payloads excluding regenerated top-level RECORD, exact interpreter-only script shebang rewrites, and the ten explicit overwritten documentation claims. Nested vendored RECORD payloads remain checked.",
            "classification": {"docs/Makefile": "Sphinx documentation build recipe", "docs/conf.py": "Sphinx documentation Python configuration",
                "docs/contributing.rst": "contributor documentation", "docs/index.rst": "documentation landing source", "docs/release_notes.rst": "release documentation"}})
        write(OUTPUT / "installed-distributions.json", distributions)
        base = plan["base_interpreter"]
        need(Path(sys.executable) == Path(base["path"]) and sha(helper.regular(Path(sys.executable)).read_bytes()) == base["sha256"], "Actual assessment interpreter differs from bound base")
        tooling_files = json.loads(bodies["pip-tooling-files.json"])
        piproot = INSTALL / "tooling/pip-sources"
        need(helper.tree(piproot) == tooling_files and sha((INSTALL / "tooling" / plan["pip_tool"]["filename"]).read_bytes()) == plan["pip_tool"]["sha256"], "Live extracted/copied pip tooling differs")
        jobs = load(bodies["owned-job-helper.py"], INSTALL / "owned-job-helper.py", "_ap2_assessment_jobs")
        command = helper.command(OUTPUT, "pip-consistency", argv, helper.clean_environment(OUTPUT), 120, jobs.WindowsJob, held)
        need(command["passed"], "Dependency consistency failed")
        need(helper.tree(ENV) == before and helper.tree(piproot) == tooling_files
            and all(sha((INSTALL / name).read_bytes()) == expected for name, expected in PINS.items()), "Read-only assessment changed or observed changed environment/consumed inputs/tooling")
        manifest = {"schema_version": "ap2-hp-native-environment/1", "status": "installed_hash_verified", "platform": "win32", "root": str(ENV), "site_packages": str(SITE),
            "interpreter": {"path": str(ENV / "Scripts/python.exe"), "sha256": before["Scripts/python.exe"]["sha256"]},
            "packages": {name: distributions[name]["version"] for name in PACKAGES}, "files": before, "all_distributions": distributions,
            "source_receipts": plan["inputs"], "installer_plan_sha256": PINS["plan.json"], "installer_report_sha256": PINS["installer-report.json"],
            "consumed_install_result_sha256": PINS["result.json"], "installer_tool": plan["pip_tool"], "base_interpreter": plan["base_interpreter"],
            "initial_environment_files_sha256": PINS["initial-environment-files.json"], "pip_tooling_files_sha256": PINS["pip-tooling-files.json"],
            "external_base_runtime_fully_inventoried": False, "total_distribution_count": 187, "indexed_distribution_count": 184, "local_distribution_count": 3,
            "all_record_entries_match": False, "record_mismatch_count": 10, "documentation_collision_paths": sorted(DOCS),
            "all_other_hashed_record_entries_match": True, "all_other_selected_wheel_payloads_exact": True, "docs_winner": "eth-abi",
            "source_payload_provenance_sha256": sha((OUTPUT / "source-payload-provenance.json").read_bytes()),
            "pip_consistency_passed": True, "environment_unchanged_during_assessment": True, "installed_pth_executed": False,
            "original_application_imported": False, "original_runtime_compatibility_established": False, "native_application_executed": False, "model_requests": 0,
            "claim_limit": "Installed metadata and complete file tree with exact frozen source payloads and five explicit documentation collisions; no full RECORD-consistency or original runtime claim."}
        need(manifest["packages"] == PACKAGES, "Native four-pin metadata differs")
        write(OUTPUT / "environment-manifest.json", manifest)
    except BaseException as error:
        failure = {"error_type": type(error).__name__, "message": str(error)}
    cleanup = []
    while held:
        notice({"status": "owned_cleanup_pending_assessment_retains_authority", "jobs": len(held)})
        try:
            for job in list(held):
                try:
                    cleanup.append(helper.settle(job, held))
                except BaseException:
                    pass
            if held:
                time.sleep(5)
        except BaseException:
            pass
    final = {"schema_version": "ap2-readonly-installed-assessment-result/1", "status": "installed_identity_with_documented_docs_collisions_verified" if failure is None else "readonly_assessment_incomplete",
        "finished_at_utc": datetime.now(timezone.utc).isoformat(), "failure": failure, "pip_command": command, "cleanup_retries": cleanup, "owned_job_authority_remaining": False,
        "record_mismatch_count": 10, "documentation_collision_path_count": 5, "all_record_entries_match": False,
        "environment_manifest_present": (OUTPUT / "environment-manifest.json").exists(), "original_application_imported": False,
        "original_runtime_compatibility_established": False, "native_application_executed": False, "model_requests": 0}
    write(OUTPUT / "result.json", final)
    notice({key: final[key] for key in ("status", "failure", "record_mismatch_count", "environment_manifest_present")})
    return 0 if failure is None else 1


if __name__ == "__main__":
    raise SystemExit(run())
