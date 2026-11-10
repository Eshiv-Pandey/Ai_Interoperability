"""Source publication refusal controls without downloads, SDKs or applications."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile

from stage_agentops_original_source_v1 import SOURCE, publish_missing, sha


def main():
    checks = []
    with tempfile.TemporaryDirectory(prefix="agentops-stage-control-") as allocated:
        base = Path(allocated)
        staged, checkout = base / "staged", base / "checkout"
        rows = []
        for name, raw in (("agents/data/incidents.db", b"constructed-source-bytes"), ("agents/python/pyproject.toml", b"constructed-pin")):
            relative = SOURCE + "/" + name
            path = staged / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            rows.append({"path": relative, "bytes": len(raw), "sha256": sha(raw)})
        first = checkout / rows[0]["path"]
        first.parent.mkdir(parents=True)
        first.write_bytes((staged / rows[0]["path"]).read_bytes())
        result = publish_missing(staged, checkout, rows)
        assert result["existing_files_verified_without_overwrite"] == 1 and result["missing_files_exclusively_created"] == 1
        checks.append("existing_member_preserved_and_only_missing_member_created")
        result = publish_missing(staged, checkout, rows)
        assert result["missing_files_exclusively_created"] == 0
        checks.append("complete_source_is_verified_without_rewriting")
        first.write_bytes(b"changed")
        missing = checkout / rows[1]["path"]
        missing.unlink()
        try:
            publish_missing(staged, checkout, rows)
        except ValueError:
            assert first.read_bytes() == b"changed" and not missing.exists()
            checks.append("mismatched_existing_member_blocks_before_any_publication")
        else:
            raise AssertionError("source mismatch accepted")
        first.write_bytes((staged / rows[0]["path"]).read_bytes())
        extra = checkout / SOURCE / "unexpected.txt"
        extra.write_bytes(b"untracked-extra")
        try:
            publish_missing(staged, checkout, rows)
        except ValueError:
            assert extra.exists() and not missing.exists()
            checks.append("unpinned_extra_member_blocks_without_delete_or_publication")
        else:
            raise AssertionError("source extra accepted")
    print(json.dumps({"status": "source_stage_controls_passed", "checks": checks,
        "source_downloads": 0, "application_execution": False}, indent=2))


if __name__ == "__main__":
    main()
