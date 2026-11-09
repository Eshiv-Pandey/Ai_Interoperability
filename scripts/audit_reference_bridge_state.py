"""Read-only live source/dependency/process audit, retaining a new report.

This complements archived replay; process absence is an observation at audit
time and cannot be reproduced by replaying old files. No process is signalled.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    driver = output.with_suffix(".driver.py")
    if not output.is_relative_to(ROOT) or output.exists() or driver.exists():
        raise SystemExit("Audit report and driver must be new workspace files")
    paths = sorted((ROOT / "runs/reference-bridge-observation").glob("R*-*/runtime.json"))
    if len(paths) != 4:
        raise SystemExit("Expected four retained v1 observations")
    records = [json.loads(path.read_bytes().decode("utf-8")) for path in paths]
    roots, conflicts, pids = {}, [], []
    for record in records:
        pre = record["pre_execution"]
        manifests = [pre[k] for k in ("bridge_source_manifest", "bridge_dist_manifest")]
        manifests += [dependency["manifest"] for group in ("installed_runtime_dependencies", "port_runtime_dependencies")
                      for dependency in pre[group]]
        for manifest in manifests:
            expected = {entry["path"]: entry["sha256"] for entry in manifest["entries"]}
            name = manifest["root"]
            if name in roots and roots[name] != expected:
                conflicts.append(name)
            roots[name] = expected
        pids += [record["parent_pid"]] + [entry["pid"] for entry in record["cleanup"]]
    trees = []
    for name, expected in sorted(roots.items()):
        directory = (ROOT / name).resolve()
        if not directory.is_relative_to(ROOT):
            raise SystemExit("Manifest root escapes workspace")
        actual = {path.relative_to(directory).as_posix(): sha256(path)
                  for path in sorted(directory.rglob("*")) if path.is_file()}
        trees.append({"root": name, "file_count": len(actual), "matches_pre_execution": actual == expected})
    source_checks = []
    for name, commit, lock in (("a2a-to-mcp", records[0]["source_commit"], "package-lock.json"),
                               ("mcp-a2a", next(r["source_commit"] for r in records if r["variant_id"] == "R3"), "pnpm-lock.yaml")):
        directory = ROOT / "external" / name
        head = subprocess.run(["git", "-C", str(directory), "rev-parse", "HEAD"], capture_output=True, text=True, encoding="utf-8")
        diff = subprocess.run(["git", "-C", str(directory), "diff", "--exit-code", "HEAD", "--", "src", "package.json", lock],
                              capture_output=True, text=True, encoding="utf-8")
        source_checks.append({"source": name, "head": head.stdout.strip(), "expected_head": commit,
                              "head_matches": head.returncode == 0 and head.stdout.strip() == commit,
                              "tracked_source_package_lock_unchanged": diff.returncode == 0,
                              "diff_stdout": diff.stdout, "diff_stderr": diff.stderr})
    if any(type(pid) is not int or pid <= 0 for pid in pids):
        raise SystemExit("Invalid observed process ID")
    ps = ("$observedProcessIds=@(" + ",".join(str(pid) for pid in pids) + "); "
          "$activeCapturedProcesses=@(Get-Process -Id $observedProcessIds -ErrorAction SilentlyContinue | Select-Object Id,ProcessName); "
          "ConvertTo-Json -InputObject $activeCapturedProcesses -Compress")
    processes = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, encoding="utf-8")
    try:
        active = json.loads(processes.stdout)
    except json.JSONDecodeError:
        active = None
    process_valid = processes.returncode == 0 and active == []
    node_checks = [{"path": r["pre_execution"]["node"]["path"],
                    "matches_pre_execution": sha256(Path(r["pre_execution"]["node"]["path"])) == r["pre_execution"]["node"]["sha256"]}
                   for r in records]
    valid = (not conflicts and all(row["matches_pre_execution"] for row in trees + node_checks)
             and all(row["head_matches"] and row["tracked_source_package_lock_unchanged"] for row in source_checks)
             and process_valid)
    output.parent.mkdir(parents=True, exist_ok=True)
    with driver.open("xb") as handle:
        handle.write(Path(__file__).read_bytes())
    report = {"schema_version": "reference-bridge-live-state-audit/1", "recorded_at": datetime.now(timezone.utc).isoformat(),
              "claim_limit": "Current source/dependency hash and process-absence observation only; no conformance, future availability, method advantage or native service rerun",
              "inputs": {p.relative_to(ROOT).as_posix(): sha256(p) for p in paths}, "manifest_conflicts": conflicts,
              "tree_checks": trees, "source_checks": source_checks, "node_checks": node_checks,
              "recorded_pids": pids, "active_captured_processes": active, "process_query_exit": processes.returncode,
              "process_query_stdout": processes.stdout, "process_query_stderr": processes.stderr,
              "process_query_command": ps, "driver": str(driver), "driver_sha256": sha256(driver), "valid": valid}
    with output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"valid": valid, "manifest_trees": len(trees), "processes_absent": process_valid, "output": str(output)}))
    return int(not valid)


if __name__ == "__main__":
    raise SystemExit(main())
