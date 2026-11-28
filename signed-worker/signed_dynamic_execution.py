"""Experimental dynamic execution; reuse pinned sandbox and gateway."""
import json, os, re, subprocess, tempfile
from pathlib import Path
from gateway import dispatch, validate
from dynamic_proof import audit
from real_bridge import executor
from signed_execution import sha
from dynamic_lemma_source import build_dynamic

def signed_dynamic_execution(raw, authorization):
    code, receipt = dispatch(raw, authorization, os.environ.get("LNZ_LEAN_WORKER_TOKEN"))
    if code != 200:
        return code, receipt
    q = validate(raw)
    try:
        prefix, source = build_dynamic(q["statement"], q["proof"])
    except ValueError:
        return 400, {"error": "DYNAMIC_GRAMMAR"}
    commit = os.environ["LNZ_WORKER_COMMIT"]
    if not re.fullmatch("[0-9a-f]{40}", commit):
        raise ValueError("invalid worker commit")
    lean = Path(os.environ["LNZ_LEAN_DIST"]).resolve(strict=True)
    version = subprocess.check_output([str(lean/"bin/lean"), "--version"], timeout=10).decode().strip()
    rc, log = executor(source, q["timeoutSeconds"])
    if type(rc) is not int or not isinstance(log, str) or len(log.encode("utf8")) > 65536:
        raise ValueError("invalid executor output")
    reports = re.findall(r"^'lnz_candidate' (does not depend on any axioms|depends on axioms: \[([^\]\n]*)\])\s*$", log, re.M)
    axioms = None if len(reports) != 1 else sorted(x.strip() for x in reports[0][1].split(",") if x.strip())
    status = "UNAVAILABLE"
    if rc == 0 and audit(log) and axioms is not None:
        status = "ACCEPTED"
    elif rc == 1 and "error:" in log:
        status = "REJECTED"
    elif rc == 0 and axioms is not None and "sorryAx" in axioms:
        status = "REJECTED"
    key = os.environ["LNZ_SIGNING_KEY"]
    public = subprocess.check_output(["openssl","pkey","-in",key,"-pubout","-outform","DER"],timeout=10)
    envelope = dict(receipt, status=status, diagnostic=log[:4000],
                    worker=sha(public), contextHash=sha(prefix.encode("utf8")),
                    sourceHash=sha(source.encode("utf8")), proofHash=q["proofHash"],
                    leanVersion=version, workerCommit=commit, axioms=axioms,
                    imageId=os.environ["LNZ_IMAGE_ID"], certified=False,
                    exitCode=rc, log=log, logHash=sha(log.encode("utf8")))
    payload = json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",",":")).encode()
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp)/"payload"
        p.write_bytes(payload)
        signature = subprocess.check_output(["openssl","pkeyutl","-sign","-rawin","-inkey",key,"-in",str(p)],timeout=10)
    return 200, {"payload":payload.decode(),"signature":signature.hex()}

if __name__ == "__main__":
    import sys
    from gateway import MAX_BODY
    code, result = signed_dynamic_execution(sys.stdin.buffer.read(MAX_BODY+1), "Bearer "+os.environ["LNZ_LEAN_WORKER_TOKEN"])
    if code != 200:
        raise RuntimeError(str(code))
    print(json.dumps(result))
