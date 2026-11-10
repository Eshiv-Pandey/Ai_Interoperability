"""Restore inherited manuscript evidence and both failed native V8 allocations."""
import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "_frozen_public_evidence_restore_v2", ROOT / "scripts/restore_retained_paper_evidence_v2.py")
inherited = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inherited)
restorer = inherited.restorer
restorer.ARCHIVES += (
    ("runs/ap2-native-bridge-development/v8/retained-42897177156-1/artifact.zip",
     "runs/ap2-native-bridge-development/v8/retained-42897177156-1/extracted",
     "024532ee2686a8a2c8f87fa5e630a204eb33b90dea6c22009037bae2b95ef1b0"),
    ("runs/ap2-native-bridge-development/v8/retained-42897325489-1/artifact.zip",
     "runs/ap2-native-bridge-development/v8/retained-42897325489-1/extracted",
     "1df360078ff1455441980d6c3d3731b1863a8d90cf797b9a42ee772b19a89866"),
)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    print(json.dumps(restorer.verify_or_restore(args.restore), indent=2))
