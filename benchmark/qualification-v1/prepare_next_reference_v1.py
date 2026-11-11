"""Emit a source-bound, public-only candidate preparation packet.

No runtime/application/model imports, requests, state allocation or dispatch.
Human/evidence/route gaps stay explicit; only an owner can allocate a later run.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--proposal-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Output already exists; refusing overwrite")
    # This public preparation process never opens evaluator-private.json,
    # candidate-table.json or candidate-notes.json.
    public_path = args.proposal_dir / "application.json"
    public = json.loads(public_path.read_text(encoding="utf-8"))
    matches = [row for row in public["records"] if row["id"] == args.candidate]
    if len(matches) != 1:
        raise SystemExit("Candidate must match one exact public row")
    row = matches[0]
    if row["domain"] not in {"agentops", "ap2"} or not row["id"].startswith(row["domain"] + "-"):
        raise SystemExit("Candidate domain and source path are not supported")
    if set(row) != {"id", "domain", "split", "template_family", "public"}:
        raise SystemExit("Unexpected field in application projection")
    source_path = ROOT / f"benchmark/tasks-v1/{row['domain']}/application.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    original = next(r for r in source["records"] if r["id"] == args.candidate)
    if row["public"] != original["public"]:
        raise SystemExit("Public fixture does not match original source-derived bank")
    packet = {"schema_version": "public-only-next-reference-preparation/1", "candidate_id": args.candidate,
              "source_pin": source["source_pin"], "public_record": row,
              "source_application_path": source_path.relative_to(ROOT).as_posix(), "source_application_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
              "proposal_application_sha256": hashlib.sha256(public_path.read_bytes()).hexdigest(),
              "execution_allowed": False, "allocation": None, "provider_calls_allowed": 0,
              "purpose": "Concrete reviewable original public recipe; later allocation requires owner coordination and separate route/resource/task gates",
              "evaluator_material_read": False,
              "guards": ["Retain all failures and unsupported/unexecuted outcomes", "Use original entrypoint/tools/source restrictions", "Bind actual observed task/context/session/user/invocation; no invented confirmations or OTP", "Direct boundary evidence cannot substitute for original workflow completion", "Use fresh exclusive state only in a separately coordinated execution"]}
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(packet, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"candidate": args.candidate, "output": str(args.output), "execution_allowed": False, "evaluator_material_read": False}))


if __name__ == "__main__":
    main()
