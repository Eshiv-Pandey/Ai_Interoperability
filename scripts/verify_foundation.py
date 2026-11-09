"""Capture real foundation checks without converting them to research findings."""

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    report_path = ROOT / "runs/foundation/verification-v1.json"
    if report_path.exists():
        raise SystemExit("verification-v1 exists; use an explicitly versioned verification run")
    freeze_dir = ROOT / "docs/research/frozen/v1"
    manifest = json.loads((freeze_dir / "manifest.json").read_text(encoding="utf-8"))
    snapshot_results = []
    for record in manifest["files"]:
        actual = hashlib.sha256((freeze_dir / record["snapshot"]).read_bytes()).hexdigest()
        snapshot_results.append({"snapshot": record["snapshot"], "sha256": actual,
                                 "matches_frozen_digest": actual == record["sha256"]})
    command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
    started_at = datetime.now(timezone.utc).isoformat()
    run = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, encoding="utf-8")
    sources = {
        str(path.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
        for base in (ROOT / "src", ROOT / "tests", ROOT / "examples/development")
        for path in sorted(base.rglob("*")) if path.is_file() and path.suffix in (".py", ".json", ".md")
    }
    report = {
        "kind": "foundation-verification", "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "command": command, "exit_code": run.returncode,
        "stdout": run.stdout, "stderr": run.stderr,
        "frozen_snapshots": snapshot_results, "source_sha256": sources,
        "claim_limit": "Software foundation validation; not method novelty, bridge results or human review",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print(run.stdout, end="")
    print(run.stderr, end="", file=sys.stderr)
    print(f"Evidence saved: {report_path}")
    return int(run.returncode != 0 or not all(r["matches_frozen_digest"] for r in snapshot_results))


if __name__ == "__main__":
    raise SystemExit(main())
