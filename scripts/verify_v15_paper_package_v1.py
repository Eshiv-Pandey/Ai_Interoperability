"""Restore the exact published V15 inputs and run its fresh-output read audit.

Use an isolated checkout. No original application, SDK, solver, evaluator,
certificate checker or provider is imported or executed. Existing evidence is
verified before missing files are added; it is never overwritten.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
RESTORES = (
    ("ap2-native-bridge-development/v8/retained-42897177156-1", "v1"),
    ("ap2-native-bridge-development/v8/retained-42897325489-1", "v1"),
    ("inherited", None),
    ("ap2-native-bridge-development/v9/retained-42902256098-1", "v1"),
    ("ap2-native-bridge-development/v10/retained-42905259371-1", "v1"),
    ("ap2-native-bridge-development/v11/retained-42911850107-1", "v2"),
    ("ap2-native-bridge-development/v12/retained-42915964952-1", "v2"),
    ("ap2-native-bridge-development/v13/retained-42918421487-4", "v3"),
    ("common-cost-development/v1/retained-42927208534-1", "v3"),
    ("ci-manuscript-v7/retained-42891705471-1", None),
    ("ci-refutation-prefix-dag-v2/retained-42910442359-1", None),
    ("ap2-original-native-provider-development/v1/retained-42982595287-1", "v3"),
    ("ap2-original-native-provider-development/v2/retained-42995902326-1", "v3"),
    ("ap2-original-native-provider-development/v3/retained-43014447502-1", "v3"),
    ("agentops-workflow-reference-development/v1/retained-43036777469-1", "v3"),
    ("agentops-workflow-reference-development/v2/retained-43055395848-1", "v3"),
    ("ap2-native-shopper-provider-development/v1/retained-43038234376-1", "v3"),
    ("ap2-native-shopper-provider-development/v2/retained-43045731741-1", "v3"),
    ("ap2-native-shopper-provider-development/v3/retained-43055390208-1", "v3"),
)


def identify(path):
    h, count = hashlib.sha256(), 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(262144), b""):
            count += len(block)
            h.update(block)
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": count, "sha256": h.hexdigest()}


def write(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def run(output):
    output = output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / "runs"):
        raise ValueError("fresh_paper_verification_allocation_required_under_runs")
    output.mkdir(parents=True)
    package = [ROOT / name for name in (
        "paper/working-draft-v15.md", "paper/working-draft-v15.provenance.json",
        "paper/claim-ledger-v15.json", "paper/audit_draft_v15.py",
        "scripts/verify_v15_paper_package_v1.py",
        "docs/research/paper-v15-offline-restoration-guide-v1.md")]
    before = [identify(path) for path in package]
    commands = []
    for base, index in RESTORES:
        if base == "inherited":
            argv = [sys.executable, "-I", "-S", "-B", "scripts/restore_retained_paper_evidence_v3.py", "--restore"]
        else:
            relative = "runs/" + base
            argv = [sys.executable, "-I", "-S", "-B", "scripts/restore_retained_evidence_v1.py",
                    "--base", relative, "--restore-missing"]
            if index:
                argv += ["--index", relative + "/archive-parts-" + index + "/index.json"]
        commands.append((base.replace("/", "--"), argv))
    audit = ROOT / "paper" / ("working-draft-v15.clean-checkout-" + uuid.uuid4().hex + ".json")
    commands.append(("current-paper-read-audit", [sys.executable, "-I", "-S", "-B", "paper/audit_draft_v15.py",
        "--draft", "paper/working-draft-v15.md", "--provenance", "paper/working-draft-v15.provenance.json",
        "--ledger", "paper/claim-ledger-v15.json", "--output", str(audit)]))
    result = {"schema_version": "v15-paper-package-restoration-verification/1", "status": "failed",
              "created_utc": datetime.now(timezone.utc).isoformat(), "inputs_before": before,
              "commands": [], "scheduled_commands": len(commands), "original_runtime_or_provider_calls": 0,
              "scientific_or_human_review_claimed": False}
    try:
        for label, argv in commands:
            print("Running " + label, flush=True)
            tick = datetime.now(timezone.utc).isoformat()
            timed_out, returncode = False, None
            with (output / (label + ".stdout.bin")).open("xb") as stdout, (output / (label + ".stderr.bin")).open("xb") as stderr:
                try:
                    child = subprocess.run(argv, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, timeout=180)
                    returncode = child.returncode
                except subprocess.TimeoutExpired:
                    timed_out = True
            receipt = {"label": label, "argv": argv, "cwd": str(ROOT), "started_utc": tick,
                       "returncode": returncode, "timed_out": timed_out, "timeout_seconds": 180}
            result["commands"].append(receipt)
            write(output / (label + ".command.json"), receipt)
            if returncode != 0 or timed_out:
                raise ValueError("failed_consumed_paper_verification_command:" + label)
        observed = json.loads(audit.read_bytes())
        if observed["passed"] is not True or observed["checks_passed"] != 19:
            raise ValueError("paper_read_audit_did_not_pass_all_current_checks")
        after = [identify(path) for path in package]
        if before != after:
            raise ValueError("published_paper_or_verification_sources_changed")
        result.update(status="passed", inputs_after=after, published_inputs_unchanged=True,
                      fresh_paper_audit=identify(audit), checks_passed=observed["checks_passed"])
    except Exception as error:
        result["error"] = type(error).__name__ + ": " + str(error)
    finally:
        result["finished_utc"] = datetime.now(timezone.utc).isoformat()
        write(output / "result.json", result)
        write(output / "manifest.json", {"files": [identify(path) for path in sorted(output.rglob("*")) if path.is_file()]})
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = run(args.output)
    print(json.dumps({"status": value["status"], "commands_completed": len(value["commands"]),
                      "new_application_or_provider_calls": 0}))
    raise SystemExit(value["status"] != "passed")
