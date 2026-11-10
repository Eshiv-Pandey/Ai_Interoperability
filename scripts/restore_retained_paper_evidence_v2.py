"""Restore hash-bound public manuscript-v7 archives without overwriting evidence."""
import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("_frozen_public_evidence_restore_v1", ROOT / "scripts/restore_retained_paper_evidence_v1.py")
restorer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restorer)
restorer.ARCHIVES += (
    ("runs/shared-cache-ablation/retained-42879031721-1/artifact.zip", "runs/shared-cache-ablation/retained-42879031721-1/extracted",
     "2307d848494e8397b2b28794ff538e707ca534441294a2d436a20c67b1a52cb1"),
    ("runs/ap2-reference-development/v5/retained-42881390576-2/artifact.zip", "runs/ap2-reference-development/v5/retained-42881390576-2/extracted",
     "7efb2a74e0b6da56613575ed2517ddaee8f37f3c73a5cf58e4789d65e6e273b9"),
    ("runs/ap2-original-shopper-development/v7/retained-42886479185-1/artifact.zip", "runs/ap2-original-shopper-development/v7/retained-42886479185-1/extracted",
     "a0177b17d698f3d279537d938761dc125f9edb24a5796d869bf64e89cf087d8b"),
    ("runs/ci-agentops-governed-app-reference-v4/retained-42887519756-1/artifact.zip", "runs/ci-agentops-governed-app-reference-v4/retained-42887519756-1/extracted",
     "41b53dda0102e3f9cbea573b67b16cf053fd0615f7a71f36ad5202f444c3fcb4"),
)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    print(json.dumps(restorer.verify_or_restore(args.restore), indent=2))
