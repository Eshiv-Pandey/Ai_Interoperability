"""Bounded primary-byte source screen; no application or model execution."""
from __future__ import annotations
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
REPOS=("prebid/salesagent","IABTechLab/agentic-mobile")

def stamp():return datetime.now(timezone.utc).isoformat()
def save(path,raw):
    with path.open("xb") as stream:stream.write(raw)

def fetch(directory,url,label,requests):
    record={"url":url,"started_at":stamp(),"purpose":"read-only primary-source eligibility screen"}
    request=urllib.request.Request(url,headers={"User-Agent":"interop-research-source-screen/2","Accept":"application/vnd.github+json"})
    try:
        with urllib.request.urlopen(request,timeout=10) as response:
            raw=response.read(4_000_001)
            if len(raw)>4_000_000:raise ValueError("Bounded response limit exceeded")
            path=directory/(label+".raw")
            save(path,raw)
            record.update(status=response.status,headers=dict(response.headers),final_url=response.url,
                          path=path.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    except Exception as error:
        raw=None;record.update(error_type=type(error).__name__,error=str(error))
    record["completed_at"]=stamp();requests.append(record)
    save(directory/(label+".receipt.json"),(json.dumps(record,indent=2)+"\n").encode())
    return raw

def main():
    directory=ROOT/"docs/research/source-evidence"/("advertising-screen-v2-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")+"-"+str(os.getpid()))
    directory.mkdir(exist_ok=False)
    requests=[];repositories=[]
    for repo in REPOS:
        slug=repo.replace("/","__")
        raw=fetch(directory,"https://api.github.com/repos/"+repo+"/commits/main",slug+"-head",requests)
        if raw is None:
            repositories.append({"repository":repo,"pin":None,"screen":"source acquisition failed; no eligibility conclusion"});continue
        value=json.loads(raw);pin=value["sha"]
        if len(pin)!=40 or any(c not in "0123456789abcdef" for c in pin):raise ValueError("Unexpected commit pin")
        row={"repository":repo,"pin":pin,"commit_date":value["commit"]["committer"]["date"]}
        raw=fetch(directory,"https://api.github.com/repos/"+repo+"/git/trees/"+pin+"?recursive=1",slug+"-tree",requests)
        if raw is not None:
            tree=json.loads(raw);row["tree_truncated"]=tree["truncated"]
            entries=[x for x in tree["tree"] if x["type"]=="blob"]
            row["file_count"]=len(entries)
            row["candidate_paths"]=[x["path"] for x in entries if any(token in x["path"].lower() for token in
                                       ("a2a","approval","media_buy","mock","simulation","workflow","human"))]
        license_raw=fetch(directory,"https://raw.githubusercontent.com/"+repo+"/"+pin+"/LICENSE",slug+"-license",requests)
        row["license_body_preserved"]=license_raw is not None
        repositories.append(row)
    value={"schema_version":"advertising-domain-source-screen/2","captured_at":stamp(),"repositories":repositories,
           "requests":requests,"application_execution":False,"model_calls":0,"paid_services":0,
           "qualified_second_domain":False,"claim_limit":"Source acquisition only; no runtime, novelty or gate credit"}
    save(directory/"screen.json",(json.dumps(value,indent=2)+"\n").encode())
    print(json.dumps({"directory":directory.relative_to(ROOT).as_posix(),"repositories":repositories,
                      "failures":[x for x in requests if x.get("error")]}))

if __name__=="__main__":main()
