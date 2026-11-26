"""Batch entry point for trusted CI; never executes arbitrary submitted source."""
import json, os, hashlib, secrets
from pathlib import Path
from bridge import bridge
from real_bridge import executor
from gateway import validate

def run(raw, execute=executor):
    q=validate(raw)
    token=secrets.token_hex(32)
    code, receipt=bridge(raw,"Bearer "+token,token,execute)
    if code != 200:
        raise ValueError("invalid request")
    return dict(receipt, request_sha256=hashlib.sha256(raw).hexdigest(),
                certified=False, backend="github-actions")

if __name__=="__main__":
    raw=os.environ["LNZ_REQUEST_JSON"].encode("utf8")
    result=run(raw)
    Path("lnz-receipt.json").write_text(json.dumps(result,indent=2),encoding="utf8")
