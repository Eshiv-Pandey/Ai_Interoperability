"""Replay retained official-handler bridge evidence; never run its services."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

WORKER = r'''
import base64,copy,hashlib,importlib.util,json,pathlib,sys
root=pathlib.Path(sys.argv[1]);report_path=sys.argv[2]
spec=importlib.util.spec_from_file_location("frozen_official_checker",root/"scripts/check_official_handler_bridge.py")
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
checked=module.check_archive(root,report_path)
records=checked.pop("records",{})
def reencode(value):
    raw=json.dumps(value["json"],ensure_ascii=False,separators=(",",":")).encode()
    value.update(raw=raw.decode(),base64=base64.b64encode(raw).decode(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def sync_ingress(records, old_sha, request):
    for entry in records["report"]["ingress"]:
        if entry["body"]["sha256"]==old_sha:
            entry["body"]={k:request[k] for k in ("raw","base64","bytes","sha256")}
            return
    raise ValueError("No ingress for mutation")
def bad_native_reference(records):
    request=records["report"]["native_controls"][1]["request"];old=request["sha256"]
    request["json"]["params"]["message"]["referenceTaskIds"]=["different-task"]
    reencode(request);sync_ingress(records,old,request)
def bad_artifact(records):
    response=records["report"]["native_controls"][0]["response"]
    response["json"]["result"]["task"]["artifacts"][0]["parts"][0]["text"]="[]";reencode(response)
def bad_context(records):
    response=records["report"]["origin_diagnostic"]["response"]
    response["json"]["result"]["contextId"]="different-context";reencode(response)
def answer_native(records):
    return next(e for e in records["native_events"] if e.get("type")=="exchange-completed"
                and e.get("request",{}).get("json",{}).get("method")=="SendMessage"
                and e["request"]["json"]["params"]["message"]["parts"][0].get("text")=="Well done!")
def bad_outgoing_header(records):
    target=answer_native(records);eid=target["exchange_id"]
    for e in records["native_events"]:
        if e.get("exchange_id")==eid:e["request"]["headers"]["a2a-version"]="0.3"
    for i in records["report"]["ingress"]:
        if i["body"]["sha256"]==target["request"]["sha256"]:i["headers"]["a2a-version"]="0.3"
def bad_outgoing_reference(records):
    target=answer_native(records);old=target["request"]["sha256"];eid=target["exchange_id"]
    for e in records["native_events"]:
        if e.get("exchange_id")==eid:
            e["request"]["json"]["params"]["message"]["referenceTaskIds"]=["different-task"];reencode(e["request"])
    sync_ingress(records,old,target["request"])
def bad_http_status(records):
    target=answer_native(records);response=target["response"]
    response["status"]=200 if response["status"]==500 else 500
    for i in records["report"]["ingress"]:
        if i["body"]["sha256"]==target["request"]["sha256"]:i["response_status"]=response["status"]
def bad_tree(records):
    inventory=next(iter(records["tree_inventory"].values()))
    next(iter(inventory.values()))["sha256"]="0"*64
def bad_source(records):
    records["source_entities"]["docs/research/official-handler-bridge-probe-v1.md"]["raw"]+="\n"
def duplicated_answer(records):
    report=records["report"]
    answer=next(e for e in report["exchanges"] if e.get("phase") in
                ("fixed_same_task_answer_send","fixed_same_task_answer_update","fixed_same_task_answer"))
    report["exchanges"].append(copy.deepcopy(answer))
def bad_card(records):
    records["report"]["card"]["supportedInterfaces"][0]["protocolVersion"]="0.3"
def bad_evaluator_order(records):
    records["report"]["origin_diagnostic"]["started"]["monotonic_ns"]="0"
mutations=[
("wrong-native-positive-reference",bad_native_reference),
("changed-native-source-artifact",bad_artifact),
("evaluator-different-context",bad_context),
("changed-outgoing-version",bad_outgoing_header),
("changed-serialized-answer-reference",bad_outgoing_reference),
("changed-delivered-http-status",bad_http_status),
("changed-runtime-tree-entry",bad_tree),
("changed-frozen-specification-bytes",bad_source),
("duplicated-answer-attempt",duplicated_answer),
("different-advertised-version",bad_card),
("evaluator-before-caller",bad_evaluator_order),
("missing-native-case",lambda d:d["report"]["native_controls"].pop()),
("reversed-native-cases",lambda d:d["report"]["native_controls"].reverse()),
("invented-agent-goal",lambda d:d["report"]["observation"].update(goal_achieved=True)),
("unclosed-service",lambda d:d["report"]["official_service"].update(server_listening=True)),
("wrong-control-cost",lambda d:d["report"]["control_costs"].update(native_control_requests=0)),
("private-binding-fed-to-arm",lambda d:d["report"]["evaluator_binding"].update(fed_to_bridge_caller=True)),
("altered-default-builder",lambda d:d["report"]["official_service"].update(default_context_builder=False)),
]
results=[]
if checked.get("valid") and checked.get("complete") and checked.get("expected_outcome_observed"):
    for name,mutate in mutations:
        changed=copy.deepcopy(records)
        try:
            mutate(changed)
            result=module.check_records(changed)
            refused=not result["valid"] or not result["complete"] or not result["expected_outcome_observed"]
            results.append({"name":name,"claim_rejected":refused,"validation_errors":result["validation_errors"],
                            "expectation_deviations":result["expectation_deviations"]})
        except Exception as error:
            results.append({"name":name,"claim_rejected":False,"mutation_setup_error":str(error)})
else:
    results.append({"name":"mutations-not-run","claim_rejected":False,
                    "reason":"Retained attempt does not validate the planned claim; no favorable service replacement"})
checked.update(mutation_checks=results,mutation_claims_rejected=all(x["claim_rejected"] for x in results),
               checker_imported=True,sdk_imported=False,bridge_started=False,service_requests=0,model_calls=0)
print(json.dumps(checked));sys.exit(0 if checked["valid"] and checked["complete"]
                                  and checked["expected_outcome_observed"] and checked["mutation_claims_rejected"] else 1)
'''

def sha(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()

def inventory(root):
    return [{"path":p.relative_to(root).as_posix(),"bytes":p.stat().st_size,"sha256":sha(p)}
            for p in sorted(root.rglob("*")) if p.is_file()]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    report=(root/args.report).resolve();output=(root/args.output).resolve()
    if not report.is_relative_to(root) or not output.is_relative_to(root):
        raise ValueError("Path escapes workspace")
    if output.exists():raise FileExistsError(output)
    archive=output.with_suffix(".sources")
    archive.mkdir(parents=True,exist_ok=False)
    shutil.copytree(report.parent,archive/report.parent.relative_to(root))
    (archive/"scripts").mkdir()
    for name in ("check_official_handler_bridge.py","replay_official_handler_bridge.py"):
        shutil.copyfile(root/"scripts"/name,archive/"scripts"/name)
    before=inventory(archive)
    with output.with_suffix(".manifest.json").open("x",encoding="utf-8") as f:
        json.dump({"files":before,"report_sha256":sha(report),"checker_sha256":sha(root/"scripts/check_official_handler_bridge.py")},f,indent=2);f.write("\n")
    worker=subprocess.run([sys.executable,"-I","-B","-c",WORKER,str(archive),report.relative_to(root).as_posix()],
                          cwd=archive,capture_output=True,text=True,timeout=60)
    after=inventory(archive)
    try:result=json.loads(worker.stdout)
    except ValueError:result=None
    checked={"schema_version":"official-handler-bridge-archive-replay/1",
             "valid":worker.returncode==0 and before==after,"checked_at":datetime.now(timezone.utc).isoformat(),
             "archive_files":len(before),"archive_unchanged":before==after,
             "worker_exit_code":worker.returncode,"worker_stderr":worker.stderr,
             "worker_stdout":worker.stdout if result is None else None,"result":result,
             "replay_driver_sha256":sha(Path(__file__)),
             "claim_limit":"Replay of retained control only; no service rerun, new scientific trial, novelty or human review"}
    with output.open("x",encoding="utf-8") as f:
        json.dump(checked,f,indent=2);f.write("\n")
    print(json.dumps({"valid":checked["valid"],"archive_files":len(before),"archive_unchanged":before==after,
                      "mutation_claims_rejected":len(result["mutation_checks"]) if result and result.get("mutation_claims_rejected") else 0,
                      "worker_exit_code":worker.returncode}))
    return int(not checked["valid"])

if __name__=="__main__":
    raise SystemExit(main())

