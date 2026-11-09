"""Compare the five observed installed docs collisions with frozen wheel bytes."""
import base64
import csv
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).absolute().parent
plan = json.loads((ROOT / "plan.json").read_bytes())
diagnostic = json.loads((ROOT / "installed-record-diagnostic-v1.json").read_bytes())
paths = sorted({row["file"] for row in diagnostic["mismatches"]})
owners = {name: [] for name in paths}
for wheel in plan["wheels"]:
    path = ROOT / "wheels" / wheel["filename"]
    with zipfile.ZipFile(path) as archive:
        members = set(archive.namelist())
        matching = members.intersection(paths)
        if not matching:
            continue
        metadata_record = [name for name in members if name.endswith(".dist-info/RECORD") and len(Path(name).parts) == 2]
        record_rows = {row[0]: row[1:] for row in csv.reader(archive.read(metadata_record[0]).decode().splitlines())}
        for name in sorted(matching):
            original = archive.read(name)
            actual = (ROOT / "environment/Lib/site-packages" / name).read_bytes()
            encoded = base64.urlsafe_b64encode(hashlib.sha256(original).digest()).rstrip(b"=").decode()
            owners[name].append({"distribution": wheel["name"], "version": wheel["version"], "wheel_filename": wheel["filename"],
                "wheel_sha256": wheel["sha256"], "wheel_payload_bytes": len(original), "wheel_payload_sha256": hashlib.sha256(original).hexdigest(),
                "wheel_record": record_rows[name], "wheel_record_matches_payload": record_rows[name] == ["sha256=" + encoded, str(len(original))],
                "installed_payload_matches_this_wheel": actual == original})
report = {"schema_version": "ap2-installed-docs-wheel-collision-comparison/1", "paths": owners,
          "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          "diagnostic_sha256": hashlib.sha256((ROOT / "installed-record-diagnostic-v1.json").read_bytes()).hexdigest(),
          "scope": "Read-only comparison of the five observed docs paths with frozen selected wheel payloads and original wheel RECORD rows; no fixes or imports."}
with (ROOT / "record-collision-wheel-comparison-v1.json").open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(report, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({name: [{"distribution": row["distribution"], "bytes": row["wheel_payload_bytes"],
                        "original_record_matches": row["wheel_record_matches_payload"], "installed_matches": row["installed_payload_matches_this_wheel"]}
                       for row in rows] for name, rows in owners.items()}, indent=2))
