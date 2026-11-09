"""Python process supervisor for unchanged Node bridge callers, v2.
No SDK import or inference. Relays real subprocess pipe bytes without rewriting.
"""
from __future__ import annotations
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
NODE = r"C:\Program Files\nodejs\node.exe"
PINS = {"amirk_a2a_to_mcp": ("external/a2a-to-mcp", "58eff9da469bccdc432bf164662727947de646b4"),
        "mgcrea_mcp_a2a": ("external/mcp-a2a", "c4d9d3c57c1746abbf9f6aadd3a9912d464eb1f5")}

def stamp():
    return {"utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "monotonic_ns": str(time.perf_counter_ns())}

def entity(raw):
    return {"base64":base64.b64encode(raw).decode(),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}

def dump(path, value):
    with path.open("x",encoding="utf-8") as stream:
        json.dump(value,stream,indent=2);stream.write("\n")

def inside(path):
    value=Path(path).resolve()
    if not value.is_relative_to(ROOT):raise ValueError("Path escapes workspace")
    return value

def env(extra=None):
    result={key:os.environ[key] for key in ("PATH","SystemRoot","TEMP","TMP") if key in os.environ}
    result.update(extra or {})
    return result

def popen(command, cwd, environment):
    return subprocess.Popen(command,cwd=cwd,env=environment,stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("variant",choices=["B1","B2","B3","B4"])
    args=parser.parse_args()
    attempt=ROOT/"runs/official-handler-bridge-control"/(
        "supervisor-v2-"+args.variant+"-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")+"-"+str(os.getpid()))
    attempt.mkdir(parents=True,exist_ok=False)
    receipt={"schema_version":"external-git-source-receipt/2","observed":stamp(),"routes":[],"network_requests":0}
    for route,(directory,pin) in PINS.items():
        row={"route_id":route,"directory":directory}
        for label,tail in (("head",["rev-parse","HEAD"]),("status",["status","--porcelain","--untracked-files=no"])):
            command=["git","-C",str(ROOT/directory),*tail]
            result=subprocess.run(command,capture_output=True,text=True,timeout=10)
            row[label]={"command":command,"exit_code":result.returncode,"stdout":result.stdout,
                        "stderr":result.stderr,"observed":stamp()}
            if result.returncode:raise RuntimeError("Git source receipt failed: "+result.stderr)
        if row["head"]["stdout"].strip()!=pin or row["status"]["stdout"]:
            raise RuntimeError("Dirty/unpinned source checkout")
        receipt["routes"].append(row)
    receipt_file=attempt/"git-source-receipt.json";dump(receipt_file,receipt)
    command=[NODE,str(ROOT/"scripts/capture-official-handler-bridge-v2.mjs"),args.variant,str(receipt_file)]
    dump(attempt/"pre-worker-launch.json",{"frozen":stamp(),"command":command,"variant":args.variant,
        "supervisor_source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"git_receipt":entity(receipt_file.read_bytes())})
    events=queue.Queue()
    worker=bridge=None
    readers=[]
    run_dir=None
    relay_file=None
    final=None
    worker_done=0
    bridge_done=0
    bridge_exit_sent=False
    raw_out=(attempt/"worker-stdout.raw").open("xb")
    raw_err=(attempt/"worker-stderr.raw").open("xb")
    launch_events=(attempt/"supervisor-events.jsonl").open("x",encoding="utf-8")

    def record(value):
        payload={"observed":stamp(),**value}
        launch_events.write(json.dumps(payload,separators=(",",":"))+"\n");launch_events.flush()
        if relay_file:
            relay_file.write(json.dumps(payload,separators=(",",":"))+"\n");relay_file.flush()

    def send(value):
        raw=(json.dumps(value,separators=(",",":"))+"\n").encode()
        written=worker.stdin.write(raw);worker.stdin.flush()
        if written!=len(raw):raise RuntimeError("Partial supervisor-to-worker control write")
        return entity(raw)

    def reader(stream, kind, lines=False):
        try:
            while True:
                raw=stream.readline() if lines else stream.read1(65536)
                if not raw:break
                events.put((kind,raw))
        finally:events.put((kind+"-done",None))

    def start_reader(stream,kind,lines=False):
        thread=threading.Thread(target=reader,args=(stream,kind,lines),daemon=True)
        readers.append(thread);thread.start()

    started=stamp()
    try:
        worker=popen(command,ROOT,env())
        record({"type":"worker-spawned","pid":worker.pid,"command":command,"started":started})
        print(json.dumps({"type":"worker-started","variant":args.variant,"pid":worker.pid,"attempt":str(attempt.relative_to(ROOT))}),flush=True)
        start_reader(worker.stdout,"worker-stdout",True);start_reader(worker.stderr,"worker-stderr")
        deadline=time.monotonic()+180
        while time.monotonic()<deadline:
            try:kind,raw=events.get(timeout=0.1)
            except queue.Empty:kind,raw="poll",None
            if kind=="worker-stdout":
                raw_out.write(raw);raw_out.flush()
                packet=json.loads(raw)
                if packet.get("type")=="start-bridge":
                    if bridge is not None:raise RuntimeError("A second bridge start was requested")
                    run_dir=inside(packet["run_dir"])
                    if run_dir.parent!=ROOT/"runs/reference-bridge-observation":raise ValueError("Unexpected run directory")
                    relay_file=(run_dir/"supervisor-relay.jsonl").open("x",encoding="utf-8")
                    cwd=inside(packet["cwd"])
                    amir=args.variant in ("B1","B2")
                    expected_cwd=ROOT/("external/a2a-to-mcp" if amir else "external/mcp-a2a")
                    expected_prefix=[NODE,"--import",(ROOT/"scripts/official-bridge-preload-v2.mjs").as_uri(),str(expected_cwd/"dist/cli.js")]
                    if cwd!=expected_cwd or packet["command"][:4]!=expected_prefix:
                        raise ValueError("Bridge launch command differs from pinned profile")
                    extra=packet["environment"]
                    if inside(extra["REFERENCE_HTTP_LOG"]).parent!=run_dir or inside(extra["REFERENCE_CLOSE_CONTROL"]).parent!=run_dir:
                        raise ValueError("Bridge control/log path differs from attempt")
                    before=stamp()
                    try:bridge=popen(packet["command"],cwd,env(extra))
                    except Exception as error:
                        record({"type":"bridge-start-error","error":repr(error)})
                        send({"type":"bridge-start-error","error":repr(error)})
                        continue
                    record({"type":"bridge-spawned","pid":bridge.pid,"command":packet["command"],"cwd":str(cwd),
                            "environment":extra,"started":before})
                    send({"type":"bridge-started","pid":bridge.pid,"supervisor_pid":os.getpid(),"started":before})
                    start_reader(bridge.stdout,"bridge-stdout");start_reader(bridge.stderr,"bridge-stderr")
                elif packet.get("type")=="write-bridge-stdin":
                    if bridge is None:raise RuntimeError("STDIN request before bridge spawn")
                    data=base64.b64decode(packet["base64"],validate=True)
                    record({"type":"bridge-stdin-request","operation_id":packet["operation_id"],"entity":entity(data)})
                    error=None
                    try:
                        written=bridge.stdin.write(data);bridge.stdin.flush()
                        if written!=len(data):raise RuntimeError("Partial actual bridge stdin write")
                        record({"type":"bridge-stdin-written","operation_id":packet["operation_id"],"entity":entity(data)})
                    except Exception as failure:
                        error=repr(failure);record({"type":"bridge-stdin-error","operation_id":packet["operation_id"],"error":error})
                    send({"type":"bridge-stdin-written","operation_id":packet["operation_id"],"error":error})
                elif packet.get("type")=="close-bridge":
                    if bridge is None or packet["pid"]!=bridge.pid:raise ValueError("Wrong shutdown PID")
                    control=inside(packet["control"])
                    if control.parent!=run_dir:raise ValueError("Wrong shutdown directory")
                    dump(control,{"action":"close","pid":bridge.pid,"run_id":packet["run_id"]})
                    record({"type":"bridge-close-control-written","pid":bridge.pid,"path":str(control.relative_to(ROOT)),"entity":entity(control.read_bytes())})
                elif packet.get("type")=="kill-bridge":
                    if bridge is None or packet["pid"]!=bridge.pid:raise ValueError("Wrong fallback PID")
                    record({"type":"bridge-fallback-kill","pid":bridge.pid});bridge.kill()
                elif "outcome" in packet and "output" in packet:
                    final=packet
                    print(json.dumps({"type":"variant-recorded","variant":args.variant,**packet}),flush=True)
                else:raise ValueError("Unknown worker control packet")
            elif kind=="worker-stderr":
                raw_err.write(raw);raw_err.flush()
            elif kind in ("bridge-stdout","bridge-stderr"):
                item=entity(raw)
                record({"type":kind+"-read","entity":item})
                send({"type":kind,"base64":item["base64"]})
                record({"type":kind+"-forwarded","entity":item})
            elif kind in ("worker-stdout-done","worker-stderr-done"):
                worker_done+=1;record({"type":kind})
            elif kind in ("bridge-stdout-done","bridge-stderr-done"):
                bridge_done+=1;record({"type":kind})
            if bridge is not None and not bridge_exit_sent and bridge.poll() is not None and bridge_done==2:
                code=bridge.returncode
                record({"type":"bridge-exited","pid":bridge.pid,"code":code,"signal":None})
                send({"type":"bridge-exit","code":code,"signal":None})
                bridge_exit_sent=True
            if worker.poll() is not None and worker_done==2:
                record({"type":"worker-exited","pid":worker.pid,"code":worker.returncode})
                break
        else:raise TimeoutError("Supervisor overall deadline reached; attempt retained")
    except Exception as error:
        record({"type":"supervisor-error","error":repr(error),"traceback":traceback.format_exc()})
        print(json.dumps({"type":"supervisor-error","variant":args.variant,"error":repr(error),"attempt":str(attempt.relative_to(ROOT))}),flush=True)
    finally:
        cleanup=[]
        for role,process in (("bridge",bridge),("worker",worker)):
            if process is None:continue
            row={"role":role,"pid":process.pid,"already_terminal":process.poll() is not None}
            if process.poll() is None:
                process.kill();row["fallback_kill"]=True
            row["exit_code"]=process.wait(timeout=10);cleanup.append(row)
            record({"type":"supervisor-final-cleanup",**row})
        raw_out.close();raw_err.close();launch_events.close()
        if relay_file:relay_file.close()
        summary={"schema_version":"python-official-bridge-supervisor/2","variant":args.variant,"pid":os.getpid(),
            "attempt":str(attempt.relative_to(ROOT)),"run_dir":str(run_dir.relative_to(ROOT)) if run_dir else None,
            "final":final,"cleanup":cleanup,"model_calls":0,"remote_network_requests":0,
            "claim_limit":"Process orchestration and actual pipe relay; no novel method or human review"}
        dump(attempt/"supervisor-report.json",summary)
        print(json.dumps({"type":"supervisor-terminal","variant":args.variant,"run_dir":summary["run_dir"],"cleanup":cleanup}),flush=True)
    return 0 if final and final.get("exit_code")==0 and all(row["exit_code"]==0 and not row.get("fallback_kill") for row in cleanup) else 1

if __name__=="__main__":raise SystemExit(main())

