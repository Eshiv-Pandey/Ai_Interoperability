"""Read-only independent audit of the actual V8 failure appendix.

No original application, actor, evaluator, provider, SDK or builder is imported.
The archive is read as data; historical V7 and V8 evidence are never modified.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "runs/ap2-native-bridge-development/v8/retained-42897325489-1"
STEM = ROOT / "paper/ap2-v8-native-smoke-failure-appendix-v1"
ARMS = ("reference", "conventional", "recovery", "shared", "recovery_shared", "amir_typed", "mg_typed", "mg_raw")
MISSING = "missing_or_pre_execution_failure_retained"
ABSENT = ("runtime-manifest.json", "original-callable-code-checks.json", "source-tool-invocations.json",
          "native-servers-started.json", "native-wire-attempts.jsonl", "native-wire-responses.jsonl",
          "native-socket-cleanup.json", "original-state-before.json", "original-state-after.json",
          "observations/events.jsonl", "observations/terminal.json")


def parse(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate_json_key")
            result[key] = value
        return result
    def invalid(_):
        raise ValueError("nonfinite_json")
    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)


def digest(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def identify(path):
    path = path.resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("input_outside_workspace")
    return {"path": path.relative_to(ROOT).as_posix(), **digest(path.read_bytes())}


def audit():
    text = STEM.with_suffix(".md").read_text(encoding="utf-8")
    flat = re.sub(r"\s+", " ", text)
    claim = parse(STEM.with_suffix(".json").read_bytes())
    run = parse((BASE / "github-run.json").read_bytes())
    checks = []
    def check(name, passed, evidence):
        checks.append({"id": name, "passed": bool(passed), "evidence": evidence})
    check("appendix_and_V7_bound_to_exact_claim_inputs", claim["appendix"] == identify(STEM.with_suffix(".md"))
          and all(identify(ROOT / row["path"]) == row for row in claim["inputs"]), len(claim["inputs"]))
    check("real_retained_completed_run", run["id"] == 42897325489 and run["run_attempt"] == 1
          and run["status"] == "completed" and run["html_url"] in text, {"run": run["id"], "attempt": run["run_attempt"]})
    with zipfile.ZipFile(BASE / "artifact.zip") as archive:
        names = set(archive.namelist())
        def raw(name):
            data = archive.read(name)
            if len(data) > 64 * 1024 * 1024:
                raise ValueError("archive_member_byte_bound")
            return data
        def read(name):
            return parse(raw(name))
        check("selected_extracted_evidence_equals_archived_bytes", all(
              (BASE / "extracted" / row["archive_member"]).read_bytes() == raw(row["archive_member"])
              and digest(raw(row["archive_member"])) == {k: row[k] for k in ("bytes", "sha256")}
              for row in claim["archive_inputs"]), len(claim["archive_inputs"]))
        manifest, allocation, execution, evaluation = [read(name) for name in (
            "matrix/public-manifest.json", "matrix/allocation-manifest.json", "matrix/execution-results.json", "independent-evaluation/result.json")]
        expected = [(case["id"], arm["id"]) for case in manifest["cases"] for arm in manifest["arms"]]
        check("all_104_original_ordered_identities_retained", len(expected) == len(set(expected)) == 104
              and len(manifest["cases"]) == 13 and tuple(row["id"] for row in manifest["arms"]) == ARMS
              and all([(row["case_id"], row["arm_id"]) for row in source["cells"]] == expected
                      for source in (allocation, execution, evaluation)), {"cells": len(expected), "arms": list(ARMS)})
        check("all_matrix_cells_unexecuted_and_missing", all(row["returncode"] is None
              and row["allocation_status"] == "not_executed_before_workflow_finalization"
              and row["captured_cell_output_present"] is False and row["matrix_after_dispatch_receipt_present"] is False
              for row in execution["cells"]) and all(row["evaluation_status"] == MISSING
              and row["returncode"] is None and row["purchase_completed"] is False for row in evaluation["cells"]), 104)
        expected_totals = {"missing_cells": 104, "verified_captures": 0, "verified_native_cells": 0,
                           "verified_legal_bridge_initiation_cells": 0, "verified_purchases": 0}
        check("independent_matrix_totals_bound", all(evaluation["totals"][key] == value for key, value in expected_totals.items()), expected_totals)
        counts = Counter(row["arm_id"] for row in execution["cells"])
        check("every_arm_table_recomputed", all(counts[arm] == 13 and f"| {arm} | 13 | 0 | 0 | 0 |" in text
              for arm in ARMS), dict(counts))
        smoke, failure, separation, plan = [read("smoke/conventional/" + name) for name in (
            "result.json", "worker-failure.json", "actor-input-separation.json", "plan.json")]
        check("actual_smoke_case_and_failure_exact", plan["case"]["id"] == "human_demo_otp"
              and plan["policy"]["id"] == "conventional" and smoke["returncode"] == 3
              and failure["error_type"] == "PermissionError" and failure["reason"] == "actor_private_evaluator_or_saved_credential_read_denied"
              and failure["reason"] in text and "human_demo_otp" in text, {"smoke": smoke, "failure": failure})
        denied = separation["denials"]
        check("all_smoke_counters_exact", denied["private_reads_blocked"] == 2
              and denied["external_network_operations_blocked"] == 1 and denied["allowed_owned_loopback_operations"] == 0
              and denied["allowed_allocated_bridge_client_processes"] == 0 and smoke["provider_requests"] == 0,
              {"denials": denied, "reported_provider_requests": smoke["provider_requests"]})
        check("no_first_callable_or_native_capture_and_no_traceback", all("smoke/conventional/" + name not in names for name in ABSENT)
              and not raw("smoke/conventional/stdout.txt") and not raw("smoke/conventional/stderr.txt")
              and "traceback" not in failure and "the exact denied path and traceback were not retained" in flat.lower(), list(ABSENT))
        stage = read("smoke/conventional/source-stage-manifest.json")
        source_entries = {row["path"]: {key: row[key] for key in ("bytes", "sha256")} for row in stage["files"] if row["project"] == "ap2"}
        certs = []
        for name in ("ds_cert_sdjwt.pem", "issuer_cert_sdjwt.pem"):
            path = "code/samples/certs/" + name
            value = raw("smoke/conventional/original-source/" + path)
            certs.append({"path": path, **digest(value), "public_certificate": value.startswith(b"-----BEGIN CERTIFICATE-----"),
                          "private_key_marker": b"PRIVATE KEY" in value, "source_identity_matches": digest(value) == source_entries[path]})
        check("both_original_public_certificate_identities_exact", all(row["public_certificate"] and not row["private_key_marker"]
              and row["source_identity_matches"] and row["sha256"] in text for row in certs), certs)
        peer_path = ROOT / "docs/research/ap2-v8-actual-smoke-failure-peer-audit-v1.json"
        peer = parse(peer_path.read_bytes())
        check("source_guard_conflict_peer_bound_with_unknown_actual_path", peer["passed"] is True
              and peer["archive"]["sha256"] == identify(BASE / "artifact.zip")["sha256"]
              and peer["controls"]["exact_retained_guard_rejects_both_required_public_source_cert_paths"] is True
              and "if the source-verification statement is reached" in flat
              and "It does not recover the smoke's omitted denied path" in flat,
              identify(peer_path))
    check("no_native_pair_or_task_success_inference", "All 65 planned ASGI/TCP pairs remain non-evaluable" in flat
          and "not a measured zero-percent task success rate" in flat
          and "The one failed smoke is separate from these 104 unexecuted matrix cells" in flat
          and "adds no native performance result" in flat, "Unexecuted cells are not measured failed task trials.")
    broken = []
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
        if not urlparse(target).scheme and not (STEM.parent / target).resolve().exists():
            # The current audit output is written only after this read-only audit.
            if target != "ap2-v8-native-smoke-failure-appendix-v1.audit.json":
                broken.append(target)
    check("all_appendix_local_links_resolve", not broken, broken)
    return {"schema_version": "ap2-v8-failure-appendix-independent-audit/1", "reviewed_utc": datetime.now(timezone.utc).isoformat(),
            "passed": all(row["passed"] for row in checks), "checks": checks,
            "appendix": identify(STEM.with_suffix(".md")), "claim_provenance": identify(STEM.with_suffix(".json")),
            "auditor": identify(Path(__file__)), "new_App_SDK_actor_evaluator_provider_network_calls": 0,
            "human_scientific_review": False, "native_performance_credit": False,
            "limits": ["Archive/claim audit only. Actual V8 denied path and traceback were not retained; reconstructed obstruction is not recovered actual path.",
                       "No native performance result, original task success, provider utility, human-gold or publication approval."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output != STEM.with_suffix(".audit.json") or output.exists():
        raise ValueError("fresh_owned_failure_appendix_audit_required")
    value = audit()
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"passed": value["passed"], "checks": len(value["checks"]), "failed": [row["id"] for row in value["checks"] if not row["passed"]]}))
    raise SystemExit(0 if value["passed"] else 1)


if __name__ == "__main__":
    main()
