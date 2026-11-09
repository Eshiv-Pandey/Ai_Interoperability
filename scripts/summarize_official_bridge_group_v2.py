"""Summarize preserved v2 controls and their disclosed corrected replays."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
CONTROL=ROOT/"runs/official-handler-bridge-control"
REPORTS=[
    ("B1","R1-amirk_a2a_to_mcp-reference-v1-2026-10-24T18-02-06-000Z-19188"),
    ("B2","R2-amirk_a2a_to_mcp-reference-v1-2026-10-24T18-03-51-242Z-23884"),
    ("B3","R3-mgcrea_mcp_a2a-reference-v1-2026-10-24T18-04-13-453Z-9912"),
    ("B4","R4-mgcrea_mcp_a2a-reference-v1-2026-10-24T18-05-16-225Z-7844")]

def read(path):return json.loads(path.read_bytes())
def file_record(path):
    raw=path.read_bytes()
    return {"path":path.relative_to(ROOT).as_posix(),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}

def main():
    target=CONTROL/"group-status-v2.json"
    if target.exists():raise FileExistsError(target)
    frozen=read(CONTROL/"pre-execution-group-v2.json")
    current=[file_record(ROOT/row["path"]) for row in frozen["files"]]
    assert all(row=={k:before[k] for k in row} for row,before in zip(current,frozen["files"]))
    rows=[];pids=[];evidence=[file_record(CONTROL/"pre-execution-group-v2.json"),
                          file_record(CONTROL/"post-capture-checker-correction-v2.1.json")]
    for variant,directory in REPORTS:
        report_path=ROOT/"runs/reference-bridge-observation"/directory/"runtime.json"
        report=read(report_path)
        old=read(CONTROL/("check-"+variant+"-v2.json"))
        checked=read(CONTROL/("check-"+variant+"-v2.1.json"))
        replay=read(CONTROL/("clean-replay-"+variant+"-v2.1.json"))
        old_replay=read(CONTROL/("clean-replay-"+variant+"-v2.json"))
        assert report["experiment_id"]=="official-handler-bridge-fidelity/2" and report["official_variant"]==variant
        assert report["outcome"]=="recorded" and report["exit_code"]==0
        assert checked["valid"] and checked["complete"] and checked["expected_outcome_observed"]
        assert checked["report_sha256"]==file_record(report_path)["sha256"]
        assert replay["valid"] and replay["archive_unchanged"] and replay["worker_exit_code"]==0
        mutations=replay["result"]["mutation_checks"]
        assert all(x["claim_rejected"] and not x.get("mutation_setup_error") for x in mutations)
        assert len(mutations)=={"B1":26,"B2":27,"B3":28,"B4":28}[variant]
        supervisor=read(ROOT/report["process_supervisor_attempt"]/"supervisor-report.json")
        pids.append(supervisor["pid"]);pids.extend(x["pid"] for x in supervisor["cleanup"])
        assert all(x["already_terminal"] and x["exit_code"]==0 and not x.get("fallback_kill") for x in supervisor["cleanup"])
        assert report["model_calls"]==report["remote_network_requests"]==0
        assert len(report["native_controls"])==3 and all(x["executed"] for x in report["native_controls"])
        assert checked["observations"]["evaluator_original_state"]=="TASK_STATE_INPUT_REQUIRED"
        events=[json.loads(line) for line in (report_path.parent/"private-native-http.jsonl").read_text().splitlines()]
        completed=[x for x in events if x.get("type")=="exchange-completed"]
        answer=next(x for x in completed if (x.get("request",{}).get("json") or {}).get("method")=="SendMessage"
                    and x["request"]["json"]["params"]["message"]["parts"][0]["text"]=="Well done!")
        old_mutations=old_replay.get("result",{}).get("mutation_checks",[])
        row={"variant":variant,"attempts":1,"report":file_record(report_path),
             "supervisor":file_record(ROOT/report["process_supervisor_attempt"]/"supervisor-report.json"),
             "initial_native_state":checked["observations"]["initial_bridge_native_state"],
             "native_eligible":report["native_eligible"],"answer_version_header":answer["request"]["headers"].get("a2a-version"),
             "answer_reference_task_ids":answer["request"]["json"]["params"]["message"].get("referenceTaskIds",[]),
             "answer_http_status":answer["response"]["status"],"answer_rpc_error":answer["response"]["json"].get("error"),
             "bridge_goal_achieved":report["observation"]["goal_achieved"],
             "evaluator_original_state":checked["observations"]["evaluator_original_state"],
             "original_check_valid":old["valid"],"original_check_complete":old["complete"],
             "original_expectation_deviations":old["expectation_deviations"],"original_validation_errors":old["validation_errors"],
             "original_replay_valid":old_replay["valid"],"original_replay_archive_unchanged":old_replay["archive_unchanged"],
             "original_mutation_setup_errors":[x for x in old_mutations if x.get("mutation_setup_error")],
             "corrected_check_valid":True,"corrected_replay_valid":True,
             "corrected_archive_files":replay["archive_files"],"corrected_archive_unchanged":True,
             "mutations_rejected":len(mutations),"derived_costs":checked["observations"]["derived_costs"],
             "process_boundary":{k:v for k,v in checked["observations"].items() if k.startswith("actual_") or k=="process_boundary_complete"}}
        rows.append(row)
        for kind in ("check", "clean-replay"):
            for version in ("v2", "v2.1"):
                evidence.append(file_record(CONTROL/(kind+"-"+variant+"-"+version+".json")))
    ps=r"C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe"
    command=[ps,"-NoProfile","-Command","ConvertTo-Json -Compress -InputObject @(Get-Process -Id "+
             ",".join(map(str,pids))+" -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,StartTime)"]
    result=subprocess.run(command,capture_output=True,text=True,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
    observed=json.loads(result.stdout)
    assert observed==[],"A recorded PID is present; inspect process identity before claiming absence"
    process_check={"observed_at":datetime.now(timezone.utc).isoformat(),"command":command,
                   "exit_code":result.returncode,"stdout":result.stdout,"stderr":result.stderr,"recorded_pids":pids,
                   "present":observed,"action":"Read-only current PID inventory; no process stopped"}
    with (CONTROL/"post-group-process-check-v2.json").open("x",encoding="utf-8") as stream:json.dump(process_check,stream,indent=2)
    value={"schema_version":"official-handler-bridge-group-status/2","observed_at":datetime.now(timezone.utc).isoformat(),
           "ordered_variants":[x[0] for x in REPORTS],"cases":rows,"service_cases_executed_once":4,
           "native_control_requests":sum(x["derived_costs"]["native_control_requests"] for x in rows),
           "evaluator_only_requests":sum(x["derived_costs"]["evaluator_only_requests"] for x in rows),
           "bridge_native_requests":sum(x["derived_costs"]["bridge_native_requests"] for x in rows),
           "server_ingress_requests":sum(x["derived_costs"]["server_ingress_requests"] for x in rows),
           "mcp_rpc_requests":sum(x["derived_costs"]["mcp_rpc_requests"] for x in rows),
           "mcp_notifications":sum(x["derived_costs"]["mcp_notifications_sent"] for x in rows),
           "corrected_mutations_rejected":sum(x["mutations_rejected"] for x in rows),
           "corrected_archive_files":sum(x["corrected_archive_files"] for x in rows),
           "group_sources_unchanged":True,"current_group_source_files":current,"evidence":evidence,
           "process_check":file_record(CONTROL/"post-group-process-check-v2.json"),
           "service_reruns":0,"model_calls":0,"remote_network_requests":0,
           "checkpoint_progress_percent":5,"cp2_status":"in_progress",
           "checker_correction_disclosed":True,"independent_human_review_completed":False,
           "claim_limit":"Bounded official-handler control with authored executor; no C1 novelty, second domain or scientific gate credit"}
    with target.open("x",encoding="utf-8") as stream:json.dump(value,stream,indent=2);stream.write("\n")
    print(json.dumps({"record":target.relative_to(ROOT).as_posix(),"cases":4,"rejected_mutations":value["corrected_mutations_rejected"],
                      "archive_files":value["corrected_archive_files"],"sources_unchanged":True,"recorded_pids_absent":True}))

if __name__=="__main__":main()
