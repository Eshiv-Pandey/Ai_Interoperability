"""Regenerate local source evidence; never modifies an upstream checkout."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
PINS = {
    "a2a-to-mcp": "58eff9da469bccdc432bf164662727947de646b4",
    "mcp-a2a": "c4d9d3c57c1746abbf9f6aadd3a9912d464eb1f5",
}
EXCERPTS = {
    "external/a2a-to-mcp/src/tools.ts": [(254, 300), (357, 386)],
    "external/a2a-to-mcp/src/envelope.ts": [(150, 190)],
    "external/a2a-to-mcp/src/parts.ts": [(55, 90), (149, 166), (188, 207)],
    "external/a2a-to-mcp/src/tasks/handlers.ts": [(31, 38), (193, 241), (252, 267), (287, 307), (388, 403), (406, 441)],
    "external/a2a-to-mcp/src/tasks/store.ts": [(78, 120)],
    "external/a2a-to-mcp/src/handles.ts": [(1, 45)],
    "external/a2a-to-mcp/src/agent-card.ts": [(1, 25), (110, 155)],
    "external/a2a-to-mcp/src/a2a-client.ts": [(138, 156), (168, 193)],
    "external/a2a-to-mcp/src/server.ts": [(38, 53), (77, 115)],
    "external/a2a-to-mcp/README.md": [(44, 46), (179, 182)],
    "external/a2a-to-mcp/fixtures/agent/executor.ts": [(155, 169), (213, 225), (264, 287)],
    "external/mcp-a2a/src/tools/tasks.ts": [(17, 44), (47, 82)],
    "external/mcp-a2a/src/client/shape.ts": [(80, 128), (202, 246)],
    "external/mcp-a2a/src/tools/request.ts": [(7, 17), (26, 34), (39, 77)],
    "external/mcp-a2a/src/client/peer.ts": [(102, 126), (198, 213), (251, 318)],
    "external/mcp-a2a/src/tools/agents.ts": [(38, 56)],
    "external/mcp-a2a/src/tools/writes.ts": [(19, 99)],
    "external/mcp-a2a/src/store/tasks.ts": [(90, 110)],
    "external/mcp-a2a/src/tools/index.ts": [(41, 49)],
    "external/mcp-a2a/src/server.ts": [(41, 90)],
}
WIRE_OBSERVATIONS = [
    "runs/wire-observation/amirk_a2a_to_mcp-2026-10-23T20-02-10-750Z-3828/runtime.json",
    "runs/wire-observation/mgcrea_mcp_a2a-2026-10-23T20-03-35-396Z-23096/runtime.json",
]


records = []
for relative, ranges in EXCERPTS.items():
    source = ROOT / relative
    raw = source.read_bytes()
    lines = raw.decode("utf-8").splitlines()
    bridge = relative.split("/")[1]
    records.append({
        "path": relative,
        "bridge_commit": PINS[bridge],
        "sha256": hashlib.sha256(raw).hexdigest(),
        "line_count": len(lines),
        "excerpts": [{"start": a, "end": min(b, len(lines)), "text": "\n".join(lines[a - 1:b])} for a, b in ranges],
    })

wire = ROOT / "docs/research/bridge-evidence/mgcrea-wire-smoke.json"
wire_raw = wire.read_bytes()
wire_doc = json.loads(wire_raw)
handshake = next(row["message"]["result"] for row in wire_doc["mcp_exchanges"] if row["message"].get("id") == 0 and "result" in row["message"])
manifest = {
    "kind": "read_only_source_query_feasibility_index",
    "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
    "scope": "pinned local implementations and existing development wire evidence; no candidate efficacy measurement",
    "model_calls": 0,
    "source_files": records,
    "existing_wire": {
        "path": str(wire.relative_to(ROOT)).replace("\\", "/"),
        "sha256": hashlib.sha256(wire_raw).hexdigest(),
        "observed_at_utc": wire_doc["observed_at_utc"],
        "initialize_result": handshake,
    },
}
observations = []
for relative in WIRE_OBSERVATIONS:
    observation_raw = (ROOT / relative).read_bytes()
    observation = json.loads(observation_raw)
    queries = []
    for exchange in observation["exchanges"]:
        if "get" not in exchange["phase"] and "mirror" not in exchange["phase"]:
            continue
        response = exchange.get("response")
        if not response:
            continue
        queries.append({
            "exchange_id": exchange["exchange_id"],
            "phase": exchange["phase"],
            "request": exchange["request"]["json"],
            "response": response["json"],
            "response_sha256": response["sha256"],
            "observed_at_utc": response["observed_at_utc"],
            "elapsed_ms": exchange["elapsed_ms"],
        })
    observations.append({
        "path": relative,
        "sha256": hashlib.sha256(observation_raw).hexdigest(),
        "route_id": observation["route_id"],
        "protocol": observation["protocol"],
        "source_commit": observation["source_commit"],
        "label": "observed upstream-authored development fixture; not independent gold, performance comparison or fresh-state lease",
        "queries": queries,
    })
manifest["development_wire_observations"] = observations
(OUT / "source-index.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({"source_files": len(records), "output": "docs/research/source-evidence/query-feasibility/source-index.json", "mcp_revision": handshake["protocolVersion"]}))
