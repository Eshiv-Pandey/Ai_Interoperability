"""Restore exact retained public ZIP evidence for manuscript audits; never overwrite."""
from pathlib import Path, PurePosixPath, PureWindowsPath
import argparse
import hashlib
import json
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVES = (
    ("runs/ci-research-core/retained-42819352517.zip", "runs/ci-research-core/download-42819352517",
     "dbc7a5fa93e105bee92882b7f9be6281be56a462d0a68b1f6e1f182418e9df6d"),
    ("runs/guard-pruned-comparison/retained-42836579527.zip", "runs/guard-pruned-comparison/download-42836579527",
     "ae24d4ed85f23100f6e994d26386322d7d7ac781d22d180200c687d611c666fc"),
    ("runs/ap2-reference-development/v3/retained-42845852651.zip", "runs/ap2-reference-development/v3/hosted-42845852651",
     "bd5a9636dbf4534b2512cd05512df057d4d7c3aa34e60b24c7ad49c29a3e6d70"),
    ("runs/ap2-reference-development/v4/hosted-42858644500/artifact.zip", "runs/ap2-reference-development/v4/hosted-42858644500/extracted",
     "b169c88da578f70210b01e7e63578ab59ca7e8b236e3c334682053929066f7cf"),
    ("runs/ci-agentops-governed-app-pilot/hosted-42859288563-2/artifact.zip", "runs/ci-agentops-governed-app-pilot/hosted-42859288563-2/extracted",
     "4829158200ecef065a7afb4a49baffbce3061532ba53d572cc7236296f6459d6"),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_or_restore(restore):
    reports = []
    for name, destination, expected in ARCHIVES:
        archive, base = ROOT / name, ROOT / destination
        if archive.is_symlink() or sha(archive.read_bytes()) != expected:
            raise ValueError("Retained archive binding differs: " + name)
        existing = missing = restored = 0
        with zipfile.ZipFile(archive) as source:
            seen, planned = set(), []
            for item in source.infolist():
                parts = PurePosixPath(item.filename)
                if item.filename in seen or parts.is_absolute() or PureWindowsPath(item.filename).drive or ".." in parts.parts:
                    raise ValueError("Unsafe/duplicate archive member")
                seen.add(item.filename)
                if stat.S_ISLNK(item.external_attr >> 16) or "\\" in item.filename:
                    raise ValueError("Archive links/noncanonical paths are refused")
                target = base.joinpath(*parts.parts)
                if not target.resolve().is_relative_to(base.resolve()) or not base.resolve().is_relative_to(ROOT):
                    raise ValueError("Archive member leaves its intended workspace directory")
                for ancestor in (target, *target.parents):
                    if ancestor.is_symlink():
                        raise ValueError("Existing path contains a symbolic link")
                    if ancestor == ROOT:
                        break
                if item.is_dir():
                    continue
                data = source.read(item)
                if target.exists():
                    if not target.is_file() or sha(target.read_bytes()) != sha(data):
                        raise ValueError("Existing evidence differs; choose a separate checkout: " + target.relative_to(ROOT).as_posix())
                    existing += 1
                else:
                    missing += 1
                    planned.append((item.filename, target))
            # Finish validating the archive before creating any evidence files.
            if restore:
                for member, target in planned:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with target.open("xb") as stream:
                        stream.write(source.read(member))
                    restored += 1
        reports.append({"archive": name, "destination": destination, "sha256": expected,
                        "existing_exact_files": existing, "missing_files": missing, "restored_files": restored})
    return {"status": "exact_archives_and_existing_evidence_verified", "mode": "restore_missing_only" if restore else "read_only_check",
            "archives": reports, "new_solver_checker_application_or_model_calls": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restore", action="store_true", help="Create only missing archive members after exact-byte validation")
    args = parser.parse_args()
    print(json.dumps(verify_or_restore(args.restore), indent=2))
