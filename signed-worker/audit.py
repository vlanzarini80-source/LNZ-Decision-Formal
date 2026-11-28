import hashlib,json,os,uuid,sys
from signed_execution import signed_execution
statement="(α : Type) (xs ys : List α) : (xs ++ ys).reverse = ys.reverse ++ xs.reverse"
sha=lambda s:hashlib.sha256(s.encode()).hexdigest()
for tactic in ("rfl","simp"):
    proof="by\n  "+tactic
    q=dict(protocol="LNZ-WORKER-1",requestId=str(uuid.uuid4()),statement=statement,statementHash=sha(statement),proof=proof,proofHash=sha(proof),timeoutSeconds=120)
    code,r=signed_execution(json.dumps(q).encode(),"Bearer "+os.environ["LNZ_LEAN_WORKER_TOKEN"])
    assert code==200 and "signature" in r
    with open("signed-"+tactic+".json","w") as f: json.dump(r,f)
    print(json.dumps(json.loads(r["payload"]),ensure_ascii=False))
