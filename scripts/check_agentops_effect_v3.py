"""Check new observer metadata plus unchanged v2 boundary/effect semantics."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import check_agentops_effect_v2 as previous
from check_agentops_socket_policy_v1 import check_policy

seed_snapshot = previous.seed_snapshot


def check_record(profile, seed):
    previous.require(profile.get("schema_version") == "agentops-passive-upstream-observation/3", "profile version")
    policy = check_policy(profile["socket_policy"])
    previous.require(profile["network_attempts"] == profile["socket_policy"]["unexpected"], "network record binding")
    # Only the envelope schema changes; all original effect requirements apply.
    normalized = dict(profile, schema_version="agentops-passive-upstream-observation/2")
    return dict(previous.check_record(normalized, seed), socket_policy=policy)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--seed-db", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Retain existing check")
    result = {"schema_version": "agentops-independent-effect-check/3", "status": "failed",
              "checked_at_utc": datetime.now(timezone.utc).isoformat(), "seed_sha256": previous.SEED_SHA256}
    try:
        raw = args.profile.read_bytes()
        result["profile_sha256"] = hashlib.sha256(raw).hexdigest()
        result.update(check_record(previous.decode_json(raw), seed_snapshot(args.seed_db)))
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result, indent=2))
    if result["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
