"""Independent body/identity check of the fixed native 1.0 port controls.

Reads saved records only. No driver, application or SDK logic is imported.
This checks the captured P1/P2/P3 fragment, not arbitrary A2A conformance.
"""

import argparse
import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def decode(raw):
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      allow_nan=False, separators=(",", ":"))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def stamp(value):
    return datetime.fromisoformat(value["utc"].replace("Z", "+00:00")), int(value["monotonic_ns"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Refusing to overwrite validation evidence")
    record = decode(args.input.read_text(encoding="utf-8"))
    checks = []

    def require(name, condition):
        checks.append({"check": name, "valid": condition is True})
        if condition is not True:
            raise ValueError(name)

    try:
        require("native-1.0-profile", record["schema_version"] == "carol-port-native-preservation/1"
                and record["protocol"]["version"] == "1.0" and record["protocol"]["binding"] == "JSONRPC")
        require("all-control-attempts-observed", record["outcome"] == "passed"
                and [row["control_id"] for row in record["controls"]] == ["P1", "P2", "P3"]
                and all(row["attempt"] == 1 and row["outcome"] == "observed" for row in record["controls"]))
        phases, request_ids = {}, set()
        previous = stamp(record["server_process"]["ready"]["observed"])
        request_bytes = response_bytes = 0
        methods = []
        for exchange in record["exchanges"]:
            request, response = exchange["request"], exchange["response"]
            start, end = stamp(request["started"]), stamp(response["observed"])
            require(exchange["exchange_id"] + ":serial-interval", all(previous[i] <= start[i] <= end[i] for i in (0, 1)))
            previous = end
            for kind, part in (("request", request), ("response", response)):
                raw = part["raw"].encode("utf-8")
                require(exchange["exchange_id"] + ":" + kind + "-bytes",
                        base64.b64decode(part["base64"], validate=True) == raw
                        and base64.b64encode(raw).decode() == part["base64"]
                        and part["bytes"] == len(raw) and part["sha256"] == digest(raw))
                if raw:
                    require(exchange["exchange_id"] + ":" + kind + "-json",
                            canonical(decode(part["raw"])) == canonical(part["json"]))
                if kind == "request":
                    request_bytes += len(raw)
                else:
                    response_bytes += len(raw)
            require(exchange["exchange_id"] + ":HTTP-success", response["status"] == 200)
            if request["method"] == "GET":
                require("single-declared-card", exchange["phase"] == "discovery"
                        and request["json"] is None and request["raw"] == ""
                        and response["json"]["supportedInterfaces"][0]["protocolVersion"] == "1.0"
                        and response["json"]["supportedInterfaces"][0]["url"] == record["endpoint"] + "/a2a")
                continue
            q, a = request["json"], response["json"]
            require(exchange["exchange_id"] + ":RPC-correlation",
                    type(q["id"]) is int and q["id"] not in request_ids
                    and type(a["id"]) is int and a["id"] == q["id"]
                    and q["jsonrpc"] == a["jsonrpc"] == "2.0"
                    and "error" not in a and "result" in a
                    and request["url"] == record["endpoint"] + "/a2a"
                    and request["headers"].get("a2a-version") == "1.0")
            request_ids.add(q["id"])
            require(exchange["exchange_id"] + ":unique-phase", exchange["phase"] not in phases)
            phases[exchange["phase"]] = (q, a)
            methods.append(q["method"])

        waiting, completed = "TASK_STATE_INPUT_REQUIRED", "TASK_STATE_COMPLETED"
        task_ids = set()
        initial_text = record["contract"]["initial_text"]
        require("source-valid-one-entry-input", decode(initial_text) == {
            "action": "shuffle", "history": [{"guess": 25, "response": "Go higher"}]})
        rows = []
        for control in record["controls"]:
            name = control["control_id"]
            initial_q, initial_a = phases[name + ":initial-send"]
            pending_q, pending_a = phases[name + ":initial-get"]
            answer_q, answer_a = phases[name + ":followup-send"]
            get_q, get_a = phases[name + ":original-get-after-answer"]
            initial, pending = initial_a["result"]["task"], pending_a["result"]
            answer, final = answer_a["result"]["task"], get_a["result"]
            task_id, context_id = initial["id"], initial["contextId"]
            message = answer_q["params"]["message"]
            require(name + ":actual-public-binding", task_id not in task_ids
                    and control["original_task_id"] == task_id and control["original_context_id"] == context_id
                    and pending_q["params"]["id"] == task_id and get_q["params"]["id"] == task_id
                    and pending["id"] == final["id"] == task_id
                    and pending["contextId"] == final["contextId"] == context_id)
            task_ids.add(task_id)
            require(name + ":method-and-initial-contract", initial_q["method"] == answer_q["method"] == "SendMessage"
                    and pending_q["method"] == get_q["method"] == "GetTask"
                    and initial_q["params"]["message"]["parts"][0]["text"] == initial_text
                    and pending["status"]["state"] == waiting)
            require(name + ":answer-contract", message["contextId"] == context_id
                    and message["role"] == "ROLE_USER" and message["parts"] == [{"text": "Well done!", "mediaType": "text/plain"}]
                    and record["contract"]["answer_text"] == "Well done!"
                    and record["contract"]["completed_artifact_required"] is False)
            require(name + ":references", message.get("referenceTaskIds", []) == ([task_id] if name == "P1" else []))
            if name in ("P1", "P2"):
                target = completed if name == "P1" else waiting
                require(name + ":same-task-state", message["taskId"] == task_id
                        and answer["id"] == task_id and answer["contextId"] == context_id
                        and answer["status"]["state"] == final["status"]["state"] == target)
            else:
                extra_q, extra_a = phases[name + ":returned-task-get-after-answer"]
                new = extra_a["result"]
                require(name + ":distinct-task-with-same-context", not message.get("taskId")
                        and answer["id"] != task_id and extra_q["params"]["id"] == answer["id"]
                        and new["id"] == answer["id"] and new["contextId"] == answer["contextId"] == context_id
                        and answer["status"]["state"] == new["status"]["state"] == final["status"]["state"] == waiting)
            # SDK task summaries use numeric enums. Check the goal-bearing fields
            # against actual wire states; do not import a driver normalization.
            for key, native in (("initial_required_receipt", pending), ("followup_send", answer), ("original_after", final)):
                saved = control[key]
                require(name + ":" + key + "-summary", saved["id"] == native["id"]
                        and saved["contextId"] == native["contextId"]
                        and type(saved["status"]["state"]) is int
                        and saved["status"]["state"] == (3 if native["status"]["state"] == completed else 6))
            rows.append({"control": name, "original_state": final["status"]["state"],
                         "answer_preserves_task": answer["id"] == task_id})
        require("all-frozen-requests-counted", len(record["exchanges"]) == 14 and len(phases) == 13
                and methods.count("SendMessage") == 6 and methods.count("GetTask") == 7
                and record["costs"]["http_attempts"] == 14 and record["costs"]["rpc_requests"] == 13
                and record["costs"]["request_bytes"] == request_bytes
                and record["costs"]["response_bytes"] == response_bytes)
        for relative, expected in record["pre_execution"]["source_hashes"].items():
            require(relative + ":snapshot-source-hash", digest((ROOT / relative).read_bytes()) == expected["sha256"]
                    and digest((ROOT / expected["snapshot"]).read_bytes()) == expected["sha256"])
        cleanup = record["cleanup"]
        require("normal-specific-server-cleanup", cleanup["pid"] == record["server_process"]["pid"]
                and cleanup["server_close"]["pid"] == cleanup["pid"]
                and cleanup["server_close"]["server_listening"] is False
                and cleanup["exit"]["code"] == 0 and cleanup["exit"]["signal"] is None
                and all(previous[i] <= stamp(cleanup["requested"])[i] for i in (0, 1)))
        valid, error = True, None
    except (ValueError, KeyError, TypeError, OSError) as failure:
        valid, error, rows = False, str(failure), []
    result = {"schema_version": "native-port-parent-check/1", "valid": valid,
              "recorded_at": datetime.now(timezone.utc).isoformat(),
              "input": str(args.input), "input_sha256": digest(args.input.read_bytes()),
              "checker_sha256": digest(Path(__file__).read_bytes()),
              "claim_limit": "Independent saved-body/identity checks of three native port controls; no complete logging, arbitrary conformance, bridge behavior, efficacy, novelty or human validation",
              "checks": checks, "controls": rows, "error": error}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"valid": valid, "checks": len(checks), "error": error, "output": str(args.output)}))
    return int(not valid)


if __name__ == "__main__":
    raise SystemExit(main())
