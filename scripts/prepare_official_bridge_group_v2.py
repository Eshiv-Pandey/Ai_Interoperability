"""Freeze v2 group and syntax checks before any SDK/service case."""
from __future__ import annotations
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
NODE = r"C:\Program Files\nodejs\node.exe"
FILES = ["docs/research/official-handler-bridge-probe-v2.md",
         "scripts/capture-official-handler-bridge-v2.mjs", "scripts/official-session-freeze-v2.mjs",
         "scripts/official-process-relay-v2.mjs", "scripts/official-bridge-preload-v2.mjs",
         "scripts/supervise_official_bridge_v2.py", "scripts/check_official_handler_bridge_v2.py",
         "scripts/replay_official_handler_bridge_v2.py", "scripts/prepare_official_bridge_group_v2.py",
         "scripts/official-handler-amir-v1.mjs", "scripts/reference-mgcrea-v1.mjs",
         "scripts/log-reference-http.mjs", "scripts/fixtures/carol-reference-v1.mjs"]

def main():
    target = ROOT/"runs/official-handler-bridge-control/pre-execution-group-v2.json"
    if target.exists():raise FileExistsError(target)
    records=[]
    for name in FILES:
        path=ROOT/name;raw=path.read_bytes()
        row={"path":name,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}
        if path.suffix==".mjs":
            result=subprocess.run([NODE,"--check",str(path)],capture_output=True,text=True,timeout=10)
            row["syntax_check"]={"exit_code":result.returncode,"stdout":result.stdout,"stderr":result.stderr}
            if result.returncode:raise ValueError("Syntax failure: "+name+result.stderr)
        elif path.suffix==".py":
            compile(raw,name,"exec");row["syntax_check"]={"python_compile":True,"code_executed":False}
            if "replay_" in path.name:
                tree=ast.parse(raw)
                worker=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
                            and any(isinstance(x,ast.Name) and x.id=="WORKER" for x in n.targets))
                compile(worker,"embedded-worker","exec");row["embedded_worker_syntax_checked"]=True
        records.append(row)
    older=json.loads((ROOT/"runs/official-handler-bridge-control/pre-execution-group-v1.json").read_bytes())
    originals=["scripts/official-handler-amir-v1.mjs", "scripts/reference-mgcrea-v1.mjs", "scripts/log-reference-http.mjs"]
    for name in originals:
        new=next(r for r in records if r["path"]==name)
        old=next(r for r in older["files"] if r["path"]==name)
        if new["sha256"]!=old["sha256"] or new["bytes"]!=old["bytes"]:raise ValueError("Inherited caller/logger changed: "+name)
    value={"schema_version":"official-handler-group-pre-execution/2",
           "frozen_at":datetime.now(timezone.utc).isoformat(),"ordered_variants":["B1","B2","B3","B4"],
           "attempts_per_variant":1,"files":records,"unchanged_inherited_files":originals,
           "sdk_imported":False,"bridge_started":False,"service_requests":0,
           "checker_authorship":"Separate-agent v1 base; integrating-assistant v2 adaptation disclosed",
           "claim_limit":"Software fidelity controls; full method objective retained; no C1, domain, human-review or checkpoint credit"}
    with target.open("x",encoding="utf-8") as stream:json.dump(value,stream,indent=2);stream.write("\n")
    print(json.dumps({"frozen":target.relative_to(ROOT).as_posix(),"files":len(records),"all_syntax_checks_passed":True}))

if __name__=="__main__":main()
