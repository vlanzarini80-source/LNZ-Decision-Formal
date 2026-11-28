"""Persistent registry for independently proved lemmas.
Only receipts signed by the configured worker key are admitted.
Dependencies are not inferred from caller claims.
"""
import hashlib,json,re,sqlite3,subprocess,tempfile
from pathlib import Path
from dynamic_lemma_source import build_dynamic

def sha(x):
    return hashlib.sha256(x.encode("utf8") if isinstance(x,str) else x).hexdigest()

class LemmaRegistry:
    def __init__(self,path,public_key,commit,version):
        self.public_key=bytes(public_key)
        self.commit=commit
        self.version=version
        der=subprocess.check_output(["openssl","pkey","-pubin","-outform","DER"],input=self.public_key,timeout=10)
        self.worker=sha(der)
        self.db=sqlite3.connect(path)
        self.db.executescript("""PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;
        CREATE TABLE IF NOT EXISTS lemmas(id TEXT PRIMARY KEY, statement TEXT NOT NULL, proof TEXT NOT NULL, receipt TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY, data TEXT NOT NULL);""")
    def authenticate(self,s,p,raw):
        prefix,source=build_dynamic(s,p)
        if len(raw.encode("utf8"))>200000: raise ValueError("receipt limit")
        x=json.loads(raw)
        if set(x)!={"payload","signature"} or not re.fullmatch("[0-9a-f]{128}",x["signature"]): raise ValueError("receipt schema")
        with tempfile.TemporaryDirectory() as d:
            k=Path(d)/"key"; m=Path(d)/"message"; sig=Path(d)/"signature"
            k.write_bytes(self.public_key);m.write_bytes(x["payload"].encode());sig.write_bytes(bytes.fromhex(x["signature"]))
            r=subprocess.run(["openssl","pkeyutl","-verify","-pubin","-inkey",str(k),"-rawin","-in",str(m),"-sigfile",str(sig)],capture_output=True,timeout=10)
            if r.returncode: raise ValueError("signature")
        e=json.loads(x["payload"])
        expected=dict(statementHash=sha(s),proofHash=sha(p),contextHash=sha(prefix),sourceHash=sha(source),worker=self.worker,workerCommit=self.commit,leanVersion=self.version,protocol="LNZ-WORKER-1",status="ACCEPTED",exitCode=0)
        if any(e.get(k)!=v for k,v in expected.items()) or e.get("certified") is not False: raise ValueError("binding")
        if not isinstance(e.get("axioms"),list) or any(a not in ("propext","Classical.choice","Quot.sound") for a in e["axioms"]): raise ValueError("axioms")
        if not isinstance(e.get("log"),str) or sha(e["log"])!=e.get("logHash"): raise ValueError("log")
        if not isinstance(e.get("requestId"),str) or not e["requestId"]: raise ValueError("request id")
        return e["requestId"]
    def admit(self,s,p,raw):
        try:
            key=self.authenticate(s,p,raw)
            with self.db:
                self.db.execute("INSERT INTO lemmas VALUES(?,?,?,?)",(key,s,p,raw))
                self.db.execute("INSERT INTO attempts(data) VALUES(?)",(json.dumps(dict(status="ACCEPTED",id=key)),))
            return key
        except Exception as e:
            with self.db:
                self.db.execute("INSERT INTO attempts(data) VALUES(?)",(json.dumps(dict(status="REJECTED",statement=s,proof=p,receipt=raw,error=str(e))),))
            raise
    def load(self,key):
        row=self.db.execute("SELECT statement,proof,receipt FROM lemmas WHERE id=?",(key,)).fetchone()
        if row is None: raise ValueError("unknown lemma")
        s,p,raw=row
        if self.authenticate(s,p,raw)!=key: raise ValueError("registry binding")
        return dict(statement=s,proof=p,statementHash=sha(s),proofHash=sha(p))
    def close(self):
        self.db.close()
