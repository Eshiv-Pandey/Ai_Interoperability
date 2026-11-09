"""Fresh, once-only Linux attempt after the old /tmp workspace disappeared.

Uses /var/tmp ext4 storage, original locked inputs, corrected native inspection,
and unchanged application/observer/wire fixtures. Prior attempts are retained.
"""
from pathlib import Path
import json
import sys
import tempfile

import agentops_native_probe_v2 as evidence
import run_agentops_linux_workspace_v5 as previous
from export_agentops_workspace_v7 import export_evidence

ROOT = evidence.WORKSPACE
OUTPUT = ROOT / "runs/agentops-native-eligibility/linux-persistent-v7"
PRIOR_LAUNCH = ROOT / "runs/agentops-native-eligibility/resume-v6-launch-v1"
SPEC = "docs/research/source-evidence/agentops-persistent-v7/protocol.md"
INPUTS = [
    "docs/research/source-evidence/agentops-local-archive-v1/ingestion.json",
    "external/downloads/agentops-c806b7f1.zip",
    "docs/research/source-evidence/agentops-local-archive-v1/symlink-payloads/agents/python/agent",
    "docs/research/source-evidence/agentops-local-archive-v1/symlink-payloads/infra/observability/prometheus-rules.yml",
    "docs/research/source-evidence/agentops-native-probe-v2/protocol.md",
    "docs/research/source-evidence/agentops-native-probe-v6/protocol.md",
    "docs/research/source-evidence/agentops-http-control-v4/protocol.md", SPEC,
    "scripts/agentops_native_probe_v2.py", "scripts/agentops_native_probe_v2_plugin.py",
    "scripts/check_agentops_effect_v2.py", "scripts/agentops_native_probe_v6.py",
    "scripts/inspect_agentops_runtime_v6.py", "scripts/setup_agentops_linux_v7.py",
    "scripts/agentops_http_control_v4.py", "scripts/agentops_http_bytes_v1.py",
    "scripts/serve_agentops_http_v1.py", "scripts/check_agentops_http_v1.py",
    "tests/test_agentops_http_control_v4.py", "scripts/run_agentops_linux_workspace_v5.py",
    "scripts/export_agentops_workspace_v7.py", "scripts/run_agentops_persistent_workspace_v7.py",
]


def capture(replica, label, arguments, timeout):
    previous_output = previous.OUTPUT
    previous.OUTPUT = OUTPUT
    try:
        receipt = previous.capture(replica, label, arguments, timeout)
    finally:
        previous.OUTPUT = previous_output
    if receipt.get("returncode") != 0:
        raise ValueError(f"{label} failed; retained without retry")


def main():
    if sys.platform != "linux":
        raise ValueError("Requires Linux; launch once through explicit Ubuntu")
    previous.require_native_filesystem(Path("/var/tmp"))
    prior = evidence.load_json(PRIOR_LAUNCH / "result.json")
    if prior.get("returncode") != 1:
        raise ValueError("Expected the recorded terminal v6 launch failure")
    for row in prior["streams"]:
        if previous.record(PRIOR_LAUNCH / row["path"], PRIOR_LAUNCH) != row:
            raise ValueError("Prior launch bytes changed")
    if "recorded Linux workspace is missing or inconsistent" not in (PRIOR_LAUNCH / "stderr.bin").read_text():
        raise ValueError("Prior failure is not the missing-workspace case")
    old = evidence.load_json(ROOT / "runs/agentops-native-eligibility/linux-filesystem-v5/result.json")
    if Path(old["linux_workspace"]).exists():
        raise ValueError("Original workspace exists again; inspect instead of reinstalling")
    inputs = [previous.record(ROOT / name, ROOT) for name in
              sorted({row["path"] for row in evidence.source_inventory()} | set(INPUTS))]
    OUTPUT.mkdir(parents=True, exist_ok=False)
    state = {"schema_version": "agentops-linux-persistent-attempt/7", "status": "failed",
             "started_at_utc": evidence.now(), "prior_launch": evidence.digest(PRIOR_LAUNCH / "result.json"),
             "native_result": "not_run", "http_result": "not_run", "live_model_calls": 0,
             "qualified_second_domain": False, "research_gate_credit_added": 0}
    evidence.write_json(OUTPUT / "execution.json", {**state, "inputs": inputs})
    replica = None
    try:
        replica = Path(tempfile.mkdtemp(prefix="agentops-research-v7-", dir="/var/tmp")).resolve()
        state["linux_workspace"] = str(replica)
        state["filesystem"] = previous.require_native_filesystem(replica)
        evidence.write_json(OUTPUT / "linux-workspace.json", {"path": str(replica)})
        state["filesystem_probe"] = previous.filesystem_probe(replica)
        (replica / "bootstrap-temp").mkdir()
        previous.copy_exact(ROOT, replica, inputs)
        print(f"New Linux workspace: {replica}", flush=True)
        for label, arguments, timeout in (
            ("setup", ["scripts/setup_agentops_linux_v7.py", "--setup-only"], 2100),
            ("native-prepare", ["scripts/agentops_native_probe_v6.py", "prepare"], 180),
            ("native-control", ["scripts/agentops_native_probe_v6.py", "run"], 480),
            ("http-prepare", ["scripts/agentops_http_control_v4.py", "prepare"], 180),
            ("http-control", ["scripts/agentops_http_control_v4.py", "run"], 600),
        ):
            state["stage"] = label
            print(f"Starting {label}; logs in {OUTPUT}", flush=True)
            capture(replica, label, arguments, timeout)
            if label == "native-control":
                state["native_result"] = evidence.load_json(replica / "runs/agentops-native-eligibility/native-probe-v6/result.json")["status"]
                if state["native_result"] != "upstream_and_boundary_effect_check_passed":
                    raise ValueError("Native result did not pass")
            if label == "http-control":
                state["http_result"] = evidence.load_json(replica / "runs/agentops-http-control/native-http-linux-v4/result.json")["status"]
                if state["http_result"] != "wire_and_effect_check_passed":
                    raise ValueError("HTTP result did not pass")
        state["status"] = "native_and_http_controls_passed"
    except (Exception, KeyboardInterrupt) as error:
        state["error"] = f"{type(error).__name__}: {error}"
    finally:
        if replica is not None:
            for field, name in (("native_result", "runs/agentops-native-eligibility/native-probe-v6/result.json"),
                                ("http_result", "runs/agentops-http-control/native-http-linux-v4/result.json")):
                if (replica / name).is_file():
                    state[field] = evidence.load_json(replica / name)["status"]
            try:
                exported = export_evidence(replica, OUTPUT / "workspace", inputs)
                evidence.write_json(OUTPUT / "export-manifest.json", exported)
                state["exported_files"] = len(exported["files"])
                state["export_reference_failures"] = exported["reference_failures"]
                if exported["reference_failures"]:
                    state["status"] = "failed_evidence_export"
            except Exception as error:
                state["status"] = "failed_evidence_export"
                state["export_error"] = f"{type(error).__name__}: {error}"
        try:
            state["parent_inputs_unchanged"] = all(previous.record(ROOT / row["path"], ROOT) == row for row in inputs)
        except Exception as error:
            state["parent_inputs_unchanged"] = False
            state["parent_input_error"] = f"{type(error).__name__}: {error}"
        if not state["parent_inputs_unchanged"]:
            state["status"] = "failed_parent_integrity"
        state["finished_at_utc"] = evidence.now()
        evidence.write_json(OUTPUT / "result.json", state)
    print(json.dumps(state, indent=2), flush=True)
    if state["status"] != "native_and_http_controls_passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
