"""Preserve Windows failure evidence and publish the Linux recovery handoff locally."""
from __future__ import annotations

import json
from pathlib import Path

import agentops_native_probe_v2 as evidence

ROOT = evidence.WORKSPACE


def main():
    output = ROOT / "runs/agentops-native-eligibility/platform-diagnosis-v1"
    docs = ROOT / "docs/research/source-evidence/agentops-native-probe-v4"
    previous = evidence.load_json(ROOT / "docs/research/source-evidence/agentops-http-control-v1/manifest.json")
    changed = [row["path"] for row in previous["files"] if evidence.digest(ROOT / row["path"]) != row]
    if changed:
        raise ValueError(f"Previous continuation inputs changed before integration: {changed}")
    native = ROOT / "runs/agentops-native-eligibility/native-probe-v3"
    result = evidence.load_json(native / "result.json")
    for row in result["files"]:
        if evidence.digest(ROOT / row["path"]) != row:
            raise ValueError("Windows failure receipt differs from retained result")
    plan = evidence.load_json(native / "plan.json")
    if plan["source_files"] != evidence.source_inventory():
        raise ValueError("Original application source changed")
    for row in plan["harness_files"]:
        if evidence.digest(ROOT / row["path"]) != row:
            raise ValueError("Windows harness changed")
    reports = evidence.load_json(native / "pytest-reports.json")
    profile = evidence.load_json(native / "passive-profile.json")
    stdout = (native / "upstream-confirmation.stdout.bin").read_text(encoding="utf-8")
    if (result["status"] != "failed" or reports != {
            "schema_version": "agentops-upstream-pytest-reports/2", "exitstatus": 4, "reports": []}
            or profile["observations"] != [] or "No module named 'fcntl'" not in stdout):
        raise ValueError("Retained failure does not match this diagnosis")
    validation = ROOT / "runs/agentops-native-eligibility/software-validation-linux-v4"
    validated = evidence.load_json(validation / "result.json")
    if validated["status"] != "passed":
        raise ValueError("Linux harness software validation failed")
    for row in validated["source_snapshots"]:
        if evidence.digest(ROOT / row["path"])["sha256"] != row["sha256"]:
            raise ValueError("Validated source changed")
    evidence.write_json(output / "diagnosis.json", {
        "schema_version": "agentops-platform-diagnosis/1", "reviewed_at_utc": evidence.now(),
        "native_result": evidence.digest(native / "result.json"),
        "failure_stage": "pytest_collection", "pytest_exitstatus": 4,
        "collected_tests": 0, "test_phases": 0, "observed_application_helper_calls": 0,
        "error": "ModuleNotFoundError: No module named 'fcntl'",
        "network_attempts_recorded_by_original_observer": profile["network_attempts"],
        "native_result_field_interpretation": "v3 application_test_started denotes pytest launch; no test phase ran",
        "source_files_verified": len(plan["source_files"]),
        "harness_files_verified": len(plan["harness_files"]),
        "native_receipt_files_verified": len(result["files"]),
        "source_evidence": [evidence.digest(evidence.SOURCE / name) for name in (
            "SUPPORT.md", "agents/python/src/agent/state.py", "mise.lock", "agents/python/uv.lock")],
        "capabilities": evidence.load_json(output / "capabilities.json"),
        "new_application_requests": 0, "model_calls": 0, "gate_credit_added": 0,
    })
    snapshot = ROOT / "docs/research/snapshots/continuation-v9"
    snapshot.mkdir(parents=True, exist_ok=False)
    context = [ROOT / "docs/research/execution-handoff.md", ROOT / "RESEARCH_WORKFLOW.md",
               ROOT / "docs/research/checkpoint-status.json"]
    preserved = []
    for path in context:
        destination = snapshot / path.name
        with destination.open("xb") as stream:
            stream.write(path.read_bytes())
        preserved.append({"before": evidence.digest(path), "snapshot": evidence.digest(destination)})
    evidence.write_json(snapshot / "manifest.json", preserved)
    note = """**Latest continuation (26 October 2026): Linux recovery prepared**

The [platform diagnosis and recovery](docs/research/source-evidence/agentops-native-probe-v4/decision.md)
supersede the old request to run Windows native v3. That once-only attempt has
now failed during pytest collection: `agent.state` imports Unix-only `fcntl`.
Zero tests/pytest phases and zero application helper calls were observed. Its
19 receipt hashes, eight harness hashes and 421 original source hashes verify.
The v3 `application_test_started` field denotes pytest launch, not a test-body
execution. All failure evidence and upstream source remain unchanged.

WSL enumeration is denied in this sandbox; Docker's Linux engine endpoint is
unavailable. Neither proves that WSL is absent from the user's normal terminal.
The separate Linux v4 setup/controller is implemented, with 21 passing authored
software checks. It verifies the upstream Linux uv checksum, installs the
unchanged lock into a separate workspace runtime, requires real native `fcntl`,
and prepares/runs the original offline test once. Linux setup and native v4 have
not run. On WSL Ubuntu with Python >=3.11, from this workspace in normal
PowerShell, the next command is `wsl --exec python3 scripts/run_agentops_linux_v4.py`.
The equivalent Linux-terminal command is `python3 scripts/run_agentops_linux_v4.py`.
Preserve any result; do not repeat existing attempts.

HTTP v1 remains bound to failed Windows native v3 and must not execute. A passing
Linux native/effect control requires a separately versioned Linux HTTP plan.
C1 novelty, bridge qualification, second-domain validity, full evaluation and
human review remain open. CP2 is open, CP7 pending, verified credit 5%.

"""
    handoff = context[0].read_text(encoding="utf-8")
    start = handoff.index("**Latest continuation (26 October 2026):**")
    end = handoff.index("Updated 25 October 2026", start)
    context[0].write_text(handoff[:start] + note.replace("docs/research/source-evidence/", "source-evidence/")
                          + handoff[end:], encoding="utf-8", newline="\n")
    workflow = context[1].read_text(encoding="utf-8")
    start = workflow.index("**Latest continuation (26 October 2026):**")
    end = workflow.index("**Original AgentOps archive (25 October):**", start)
    context[1].write_text(workflow[:start] + note + workflow[end:], encoding="utf-8", newline="\n")
    status = evidence.load_json(context[2])
    assert status["progress_percent"] == 5 and status["novelty_demonstrated"] is False
    cp2 = next(row for row in status["checkpoints"] if row["id"] == "CP2")
    assert cp2["status"] == "in_progress"
    cp2["evidence"].extend([
        "source-evidence/agentops-native-probe-v4/protocol.md",
        "source-evidence/agentops-native-probe-v4/decision.md",
        "source-evidence/agentops-native-probe-v4/verification.json",
        "../../runs/agentops-native-eligibility/native-probe-v3/result.json",
        "../../runs/agentops-native-eligibility/platform-diagnosis-v1/diagnosis.json",
        "../../runs/agentops-native-eligibility/software-validation-linux-v4/result.json"])
    cp2["source_leads"]["agentops_runtime_setup"] = (
        "Windows native v3 failed collection due to Unix fcntl; zero test phases; original source/receipts verified. "
        "Separate Linux v4 setup/controller software-tested; actual Linux environment/setup/execution pending.")
    cp2["source_leads"]["agentops_http_control"] = (
        "HTTP v1 remains prepared and unexecuted, permanently gated by failed Windows native v3; "
        "requires a separately versioned Linux HTTP plan after actual Linux native/effect success.")
    status["as_of"] = "2026-10-26"
    context[2].write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8", newline="\n")
    paths = set(context)
    for directory in (output, snapshot, validation, validation / "sources", docs):
        paths.update(path for path in directory.iterdir() if path.is_file())
    paths.update(ROOT / name for name in (
        "scripts/agentops_native_probe_v4.py", "scripts/inspect_agentops_runtime_v4.py",
        "scripts/run_agentops_linux_v4.py", "scripts/integrate_agentops_linux_v9.py",
        "tests/test_agentops_linux_control.py"))
    paths.add(native / "result.json")
    paths.update(ROOT / row["path"] for row in result["files"] + plan["harness_files"])
    rows = [evidence.digest(path) for path in sorted(paths)]
    evidence.write_json(docs / "manifest.json", {"schema_version": "agentops-linux-recovery-integrity/1", "files": rows})
    failures = [row["path"] for row in rows if evidence.digest(ROOT / row["path"]) != row]
    evidence.write_json(docs / "verification.json", {
        "status": "failed" if failures else "passed", "files_checked": len(rows), "failures": failures,
        "previous_continuation_files_verified_before_edit": len(previous["files"]),
        "original_source_files_verified": 421, "linux_executed": False, "gate_credit_added": 0})
    print(json.dumps({"status": "integrated", "files_checked": len(rows), "failures": failures,
                      "progress_percent": status["progress_percent"]}))


if __name__ == "__main__":
    main()
