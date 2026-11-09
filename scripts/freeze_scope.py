"""Save immutable planning snapshots; refuse accidental replacement."""

import hashlib
import json
import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = ["RESEARCH_WORKFLOW.md", "docs/research/student-budget-experiment-design.md",
         "docs/research/finite-model-v1.md", "docs/research/checkpoints.md"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="v1")
    parser.add_argument("--reason", default="Approved local scope freeze")
    args = parser.parse_args()
    if not re.fullmatch(r"v[0-9]+(?:\.[0-9]+)*", args.version):
        raise SystemExit("version must be v plus numeric components")
    target = ROOT / "docs/research/frozen" / args.version
    if target.exists():
        raise SystemExit(f"{args.version} already exists; verify it or create an explicit new version")
    selected = FILES + (["docs/research/execution-addendum-v1.1.md"] if args.version == "v1.1" else [])
    payloads = [(name, (ROOT / name).read_bytes()) for name in selected]
    target.mkdir(parents=True)
    records = []
    for name, payload in payloads:
        local = target / name
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(payload)
        records.append({"source": name, "snapshot": name, "sha256": hashlib.sha256(payload).hexdigest()})
    manifest = {
        "version": args.version, "created_at": datetime.now(timezone.utc).isoformat(),
        "reason": args.reason,
        "authorization": "User instructed: Freeze it and start working on the project now.",
        "scope": "Candidate method, independent bridges/oracle, gates and deliverables; no model or quota entitlement",
        "execution_start": "2026-10-24", "day_45": "2026-12-07", "files": records,
    }
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Frozen {len(records)} files at {target}")


if __name__ == "__main__":
    main()
