"""Experimental signed wrapper around pinned restricted worker."""
import hashlib, json, os, re, subprocess
from pathlib import Path
from bridge import bridge
from gateway import validate
from dynamic_proof import TARGETS, context_sha256
from real_bridge import executor

def sha(data):
    return hashlib.sha256(data).hexdigest()

def signed_execution(raw, authorization):
    observed = {}
    def capture(source, timeout):
        rc, log = executor(source, timeout)
        observed.update(sourceHash=sha(source.encode("utf8")), exitCode=rc,
                        logHash=sha(log.encode("utf8")), log=log)
        return rc, log
    code, receipt = bridge(raw, authorization, os.environ.get("LNZ_LEAN_WORKER_TOKEN"), capture)
    if code != 200 or not observed:
        return code, receipt
    q = validate(raw)
    target = next(k for k,v in TARGETS.items() if v == q["statement"])
    lean = Path(os.environ["LNZ_LEAN_DIST"]).resolve(strict=True)
    version = subprocess.check_output([str(lean/"bin/lean"), "--version"], timeout=10).decode().strip()
    commit = os.environ["LNZ_WORKER_COMMIT"]
    if not re.fullmatch("[0-9a-f]{40}", commit):
        raise ValueError("invalid worker commit")
    reports = re.findall(r"^'lnz_candidate' (does not depend on any axioms|depends on axioms: \[([^\]\n]*)\])\s*$", observed["log"], re.M)
    axioms = None if len(reports)!=1 else sorted(x.strip() for x in reports[0][1].split(",") if x.strip())
    key = os.environ["LNZ_SIGNING_KEY"]
    public = subprocess.check_output(["openssl","pkey","-in",key,"-pubout","-outform","DER"],timeout=10)
    envelope = dict(receipt, worker=sha(public), contextHash=context_sha256(target),
                    leanVersion=version, workerCommit=commit, axioms=axioms,
                    imageId=os.environ["LNZ_IMAGE_ID"], certified=False, **observed)
    # Sign exact UTF-8 bytes; consumers verify before parsing.
    payload = json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",",":")).encode()
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)/"payload"
        p.write_bytes(payload)
        signature=subprocess.check_output(["openssl","pkeyutl","-sign","-rawin","-inkey",key,"-in",str(p)],timeout=10)
    return code, {"payload":payload.decode(),"signature":signature.hex()}
