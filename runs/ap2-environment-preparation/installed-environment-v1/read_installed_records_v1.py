"""Read-only diagnostic of the consumed first installation's RECORD failure."""
import base64
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).absolute().parent
ENV = ROOT / "environment"
SITE = ENV / "Lib/site-packages"
errors, algorithms, rows = [], {}, 0
for record in sorted(SITE.glob("*.dist-info/RECORD")):
    for name, encoded_hash, size in csv.reader(record.read_text(encoding="utf-8").splitlines()):
        rows += 1
        if not encoded_hash:
            continue
        algorithm, declared = encoded_hash.split("=", 1)
        algorithms[algorithm] = algorithms.get(algorithm, 0) + 1
        path = (SITE / name).resolve()
        if not path.is_relative_to(ENV):
            errors.append({"record": record.relative_to(ROOT).as_posix(), "file": name, "error": "path_escape"})
            continue
        raw = path.read_bytes()
        actual = base64.urlsafe_b64encode(hashlib.new(algorithm, raw).digest()).rstrip(b"=").decode()
        hash_ok, size_ok = actual == declared, bool(size) and int(size) == len(raw)
        if algorithm != "sha256" or not hash_ok or not size_ok:
            errors.append({"record": record.relative_to(ROOT).as_posix(), "file": name, "algorithm": algorithm,
                           "hash_matches": hash_ok, "size_matches": size_ok, "declared_hash": declared,
                           "actual_hash": actual, "declared_bytes": size, "actual_bytes": len(raw)})
report = {"schema_version": "ap2-installed-record-failure-diagnostic/1", "record_rows": rows,
          "algorithms": algorithms, "mismatch_count": len(errors), "mismatches": errors,
          "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          "installation_result_sha256": hashlib.sha256((ROOT / "result.json").read_bytes()).hexdigest(),
          "scope": "Current files and declared RECORD hashes only; no package imports, install replay, .pth startup or file repairs."}
with (ROOT / "installed-record-diagnostic-v1.json").open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(report, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({"rows": rows, "algorithms": algorithms, "mismatch_count": len(errors), "mismatches": errors[:20]}, indent=2))
