"""Experimental signed composition; independent registered lemmas only."""
import json,os,re,subprocess,tempfile,uuid
from pathlib import Path
from dependency_plan import prepare_registered_composition
from dependency_extract import inspection_suffix,extract_dependencies,compare_plan
from lemma_registry import sha
from real_bridge import executor

def execute(registry,statement,proof,graph,timeout=60):
    if type(timeout) is not int or not 1<=timeout<=120: raise ValueError("timeout")
    event=dict(protocol="LNZ-COMPOSITION-1",requestId=str(uuid.uuid4()),statement=statement,proof=proof,proposedGraph=graph,certified=False,status="UNAVAILABLE")
    try:
        source,manifest=prepare_registered_composition(registry,statement,proof,graph)
        names=[d["name"] for d in manifest["declarations"]]
        for d in manifest["declarations"]:
            raw=registry.db.execute("SELECT receipt FROM lemmas WHERE id=?",(d["id"],)).fetchone()[0]
            if registry.authenticate(d["statement"],d["proof"],raw)!=d["id"]: raise ValueError("receipt binding")
            d["receipt"]=raw
        full=source+inspection_suffix(names)+"\n"+"\n".join("#print axioms "+n for n in names)+"\n"
        event.update(manifest=manifest,source=full,sourceHash=sha(full))
        rc,log=executor(full,timeout)
        event.update(exitCode=rc,log=log,logHash=sha(log))
        if rc!=0: raise ValueError("Lean execution failed")
        axioms={}
        for n in names+["lnz_candidate"]:
            reports=re.findall(r"^'"+n+r"' (does not depend on any axioms|depends on axioms: \[([^\]\n]*)\])\s*$",log,re.M)
            if len(reports)!=1: raise ValueError("axiom report")
            a=sorted(x.strip() for x in reports[0][1].split(",") if x.strip())
            if any(x not in ("propext","Classical.choice","Quot.sound") for x in a): raise ValueError("forbidden axiom")
            axioms[n]=a
        event["axioms"]=axioms
        event.update(compare_plan(manifest,extract_dependencies(log,names)))
        event["status"]="ACCEPTED" if event["planMatches"] else "PLAN_MISMATCH"
    except Exception as e:
        event["error"]=str(e)
    key=os.environ["LNZ_SIGNING_KEY"]
    der=subprocess.check_output(["openssl","pkey","-in",key,"-pubout","-outform","DER"],timeout=10)
    if sha(der)!=registry.worker: raise ValueError("signing identity")
    version=subprocess.check_output([str(Path(os.environ["LNZ_LEAN_DIST"])/"bin/lean"),"--version"],timeout=10).decode().strip()
    if version!=registry.version or os.environ["LNZ_WORKER_COMMIT"]!=registry.commit: raise ValueError("worker identity")
    event.update(worker=sha(der),workerCommit=registry.commit,leanVersion=version,imageId=os.environ["LNZ_IMAGE_ID"],compositionCommit=os.environ["GITHUB_SHA"])
    payload=json.dumps(event,ensure_ascii=False,sort_keys=True,separators=(",",":"))
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/"payload";p.write_bytes(payload.encode())
        sig=subprocess.check_output(["openssl","pkeyutl","-sign","-rawin","-inkey",key,"-in",str(p)],timeout=10)
    result=dict(payload=payload,signature=sig.hex())
    with registry.db:
        registry.db.execute("INSERT INTO attempts(data) VALUES(?)",(json.dumps(result),))
    return result
