"""Preserve prior context and link the prepared HTTP control without gate credit."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def record(path):
    raw = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def write_json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def main():
    evidence = ROOT / "docs/research/source-evidence/agentops-http-control-v1"
    snapshot = ROOT / "docs/research/snapshots/continuation-v8"
    snapshot.mkdir(parents=True, exist_ok=False)
    context = [ROOT / "docs/research/execution-handoff.md",
               ROOT / "docs/research/checkpoint-status.json", ROOT / "RESEARCH_WORKFLOW.md"]
    preserved = []
    for path in context:
        destination = snapshot / path.name
        shutil.copyfile(path, destination)
        preserved.append({"before": record(path), "snapshot": record(destination)})
    write_json(snapshot / "manifest.json", preserved)
    note = """**Latest continuation (26 October 2026):**

The [native/HTTP continuation record](docs/research/source-evidence/agentops-http-control-v1/decision.md)
supersedes the older dependency-setup next step. The installed recovery runtime
has 168 lock-matching distribution versions; native v3 source/harness/runtime
revalidation passes. A fresh sandbox mode-0700 probe still fails. Native v3 has
not executed; the pending user-side command is
`powershell -NoProfile -File .\\scripts\\run_agentops_native_v3.ps1` from this
workspace in normal PowerShell. Preserve and inspect its result; never rerun a
reserved attempt. The separate HTTP control is implemented, tested on authored
evidence (seven passing tests), source-pinned and prepared, but cannot execute
until the original native test/effect check passes. No native/HTTP/bridge result
or new research-gate credit follows. CP2 remains open, CP7 pending, credit 5%.
The original C1 distinction, full evaluation and human-review gates remain open.

"""
    handoff = context[0].read_text(encoding="utf-8")
    marker = "# Current execution handoff\n\n"
    if not handoff.startswith(marker):
        raise ValueError("Unexpected handoff title")
    context[0].write_text(marker + note.replace("docs/research/source-evidence/", "source-evidence/")
                          + handoff[len(marker):], encoding="utf-8", newline="\n")
    workflow = context[2].read_text(encoding="utf-8")
    marker = "## 1. Research direction and what changes\n\n"
    if workflow.count(marker) != 1:
        raise ValueError("Unexpected workflow section")
    context[2].write_text(workflow.replace(marker, marker + note, 1), encoding="utf-8", newline="\n")
    status = json.loads(context[1].read_text(encoding="utf-8"))
    assert status["progress_percent"] == 5 and status["novelty_demonstrated"] is False
    cp2 = next(row for row in status["checkpoints"] if row["id"] == "CP2")
    assert cp2["status"] == "in_progress"
    cp2["evidence"].extend([
        "source-evidence/agentops-native-probe-v2/protocol.md",
        "source-evidence/agentops-native-probe-v3/protocol.md",
        "../../runs/agentops-native-eligibility/native-probe-v3/plan.json",
        "../../runs/agentops-native-eligibility/native-probe-v3/preparation-result.json",
        "../../runs/agentops-native-eligibility/session-resume-v4/result.json",
        "source-evidence/agentops-http-control-v1/protocol.md",
        "source-evidence/agentops-http-control-v1/decision.md",
        "source-evidence/agentops-http-control-v1/manifest.json",
        "../../runs/agentops-http-control/software-validation-v1.1/result.json",
        "../../runs/agentops-http-control/native-http-v1/plan.json"])
    cp2["source_leads"]["agentops_runtime_setup"] = (
        "168 installed recovery distributions match lock; source/harness/runtime revalidated; "
        "installation history/full runtime authenticity unresolved; native v3 requires normal-terminal execution")
    cp2["source_leads"]["agentops_http_control"] = (
        "Prospective original-factory/offline fixture with raw HTTP capture and six domain snapshots; "
        "seven software tests pass; prepared, not executed; gated on native v3 success")
    status["as_of"] = "2026-10-26"
    context[1].write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8", newline="\n")
    paths = set(context)
    paths.update(snapshot.iterdir())
    paths.update(evidence.iterdir())
    paths.update(ROOT / "scripts" / name for name in (
        "inspect_agentops_resume_v4.py", "agentops_http_bytes_v1.py", "serve_agentops_http_v1.py",
        "agentops_http_control_v1.py", "check_agentops_http_v1.py", "run_agentops_http_v1.ps1",
        "integrate_agentops_http_v8.py"))
    paths.add(ROOT / "tests/test_agentops_http_control.py")
    # Include direct receipts and their saved software inputs. Never traverse
    # inaccessible mode-0700 probe directories or live runtime state.
    for directory in (ROOT / "runs/agentops-native-eligibility/session-resume-v4",
                      ROOT / "runs/agentops-http-control/native-http-v1",
                      ROOT / "runs/agentops-http-control/software-validation-v1",
                      ROOT / "runs/agentops-http-control/software-validation-v1.1"):
        paths.update(path for path in directory.iterdir() if path.is_file())
        if (directory / "sources").is_dir():
            paths.update((directory / "sources").iterdir())
    entries = [record(path) for path in sorted(paths)]
    write_json(evidence / "manifest.json", {
        "schema_version": "agentops-http-preparation-integrity/1", "files": entries,
        "application_requests": 0, "live_model_calls": 0, "research_gate_credit_added": 0})
    failures = [row["path"] for row in entries if record(ROOT / row["path"]) != row]
    write_json(evidence / "verification.json", {"status": "failed" if failures else "passed",
        "files_checked": len(entries), "failures": failures,
        "scope": "Current preparation/context bytes only; not experimental or scientific validity"})
    print(json.dumps({"status": "integrated", "files_checked": len(entries), "failures": failures,
                      "progress_percent": status["progress_percent"]}))


if __name__ == "__main__":
    main()
