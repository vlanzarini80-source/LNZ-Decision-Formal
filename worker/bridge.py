"""Restricted bridge; executor is a trusted server-side dependency."""
import hashlib
from gateway import dispatch, validate
from dynamic_proof import TARGETS, build, audit

def bridge(raw, authorization, token, execute):
    code, response = dispatch(raw, authorization, token)
    if code != 200:
        return code, response
    q = validate(raw)
    def result(status, diagnostic):
        return 200, dict(response, status=status, diagnostic=diagnostic[:8000])
    targets = {v:k for k,v in TARGETS.items()}
    if q["statement"] not in targets:
        return result("UNAVAILABLE", "Formal target not registered")
    lines = q["proof"].split("\n")
    if lines[0] != "by" or any(not x.startswith("  ") for x in lines[1:]):
        return result("REJECTED", "Expected restricted tactic proof")
    try:
        source, digest = build(targets[q["statement"]], [x[2:] for x in lines[1:]])
    except ValueError:
        return result("REJECTED", "Unsupported tactic sequence")
    if digest != q["statementHash"]:
        return result("UNAVAILABLE", "Target binding failed")
    try:
        rc, log = execute(source, q["timeoutSeconds"])
        if type(rc) is not int or not isinstance(log,str) or len(log)>65536:
            return result("UNAVAILABLE", "Invalid executor result")
        if rc == 0 and audit(log):
            return result("ACCEPTED", log)
        if rc == 1 and "error:" in log:
            return result("REJECTED", log)
        return result("UNAVAILABLE", "Execution or axiom audit failed")
    except Exception:
        return result("UNAVAILABLE", "Executor failure")
