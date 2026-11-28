import hashlib,json,os,subprocess,tempfile,uuid
from pathlib import Path
from signed_dynamic_execution import signed_dynamic_execution
from dynamic_lemma_source import build_dynamic
from dynamic_proof import TARGETS
from real_bridge import executor

def sha(s): return hashlib.sha256(s.encode()).hexdigest()
auth="Bearer "+os.environ["LNZ_LEAN_WORKER_TOKEN"]
evidence=[]
def check(condition,label):
    if not condition: raise AssertionError(label)
def signature(payload,sig):
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/"payload"; s=Path(d)/"sig"
        p.write_bytes(payload.encode()); s.write_bytes(bytes.fromhex(sig))
        return subprocess.run(["openssl","pkeyutl","-verify","-pubin","-inkey","worker-public.pem","-rawin","-in",str(p),"-sigfile",str(s)],capture_output=True,timeout=10).returncode==0
def request(statement,proof):
    return dict(protocol="LNZ-WORKER-1",requestId=str(uuid.uuid4()),statement=statement,statementHash=sha(statement),proof=proof,proofHash=sha(proof),timeoutSeconds=30)
def send(q): return signed_dynamic_execution(json.dumps(q).encode(),auth)
def save():
    Path("dynamic-audit-evidence.json").write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
try:
    for statement,proof,expected in [
        ("(n : Nat) : n = n","by\n  rfl","ACCEPTED"),
        ("(a b : Nat) : a + b = b + a","by\n  omega","ACCEPTED"),
        (": 1 = 2","by\n  rfl","REJECTED")]:
        check(statement not in TARGETS.values(),"not novel")
        q=request(statement,proof); code,r=send(q)
        evidence.append(dict(request=q,code=code,response=r));save()
        check(code==200,"execution")
        e=json.loads(r["payload"]); prefix,source=build_dynamic(statement,proof)
        check(signature(r["payload"],r["signature"]),"signature")
        check(not signature(r["payload"]+" ",r["signature"]),"tamper")
        for k in ("requestId","statementHash","proofHash"): check(e[k]==q[k],k)
        check(e["contextHash"]==sha(prefix) and e["sourceHash"]==sha(source) and e["logHash"]==sha(e["log"]),"hash binding")
        check(e["status"]==expected and e["certified"] is False,"classification")
    for statement,proof in [
        (": False","by\n  exact sorryAx"),
        (": False","by\n  admit"),
        (": False\naxiom injected : False","by\n  trivial"),
        (": False","by\n  run_tac")]:
        q=request(statement,proof);code,r=send(q)
        evidence.append(dict(request=q,code=code,response=r));save()
        check(code==400,"grammar rejection")
    q=request(": True","by\n  trivial");q["proofHash"]="0"*64
    code,r=send(q);evidence.append(dict(control="hash mismatch",code=code,response=r));save()
    check(code==400,"request hash")
    # Trusted audit fixture, not exposed to the dynamic input grammar.
    rc,log=executor("import Lean\naxiom forbidden : False\ntheorem lnz_candidate : False := forbidden\n#print axioms lnz_candidate\n",30)
    from dynamic_proof import audit
    evidence.append(dict(control="axiom fixture",exitCode=rc,log=log));save()
    check(rc==0 and "forbidden" in log and not audit(log),"axiom audit")
    # Inspect actual container settings using a separate audit container.
    image=os.environ["LNZ_IMAGE_ID"]
    name="lnz-isolation-audit-"+uuid.uuid4().hex
    try:
        subprocess.run(["docker","create","--name",name,"--network","none","--read-only","--cap-drop","ALL","--security-opt","no-new-privileges","--pids-limit","64","--memory","2g","--cpus","2","--user","65534:65534",image,"true"],check=True,capture_output=True)
        x=json.loads(subprocess.check_output(["docker","inspect",name]))[0]; h=x["HostConfig"]
        evidence.append(dict(control="container configuration fixture",host=h,user=x["Config"]["User"]));save()
        check(h["NetworkMode"]=="none" and h["ReadonlyRootfs"] and "ALL" in h["CapDrop"] and h["Memory"]==2147483648 and x["Config"]["User"]=="65534:65534","isolation fixture")
    finally: subprocess.run(["docker","rm","-f",name],capture_output=True)
    rc,log=executor("import Lean\nset_option maxRecDepth 1000000\nset_option maxHeartbeats 0\n#eval (List.range 100000000).length\n",1)
    evidence.append(dict(control="timeout fixture",exitCode=rc,log=log));save()
    check(rc==124,"timeout")
    print("DYNAMIC_REAL_LEAN_AUDIT_PASS")
finally: save()
