"""Gateway only: no Lean execution until a trusted sandbox adapter is installed."""
import hashlib
import hmac
import json
import os
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

MAX_BODY = 160000
FIELDS = {"protocol", "requestId", "statement", "statementHash", "proof", "proofHash", "timeoutSeconds"}

def unique(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError("duplicate key")
        result[k] = v
    return result

def validate(raw):
    if len(raw) > MAX_BODY:
        raise ValueError("body limit")
    q = json.loads(raw, object_pairs_hook=unique)
    if not isinstance(q, dict) or set(q) != FIELDS or q["protocol"] != "LNZ-WORKER-1":
        raise ValueError("schema")
    if str(uuid.UUID(q["requestId"])) != q["requestId"]:
        raise ValueError("request id")
    if type(q["timeoutSeconds"]) is not int or not 1 <= q["timeoutSeconds"] <= 120:
        raise ValueError("timeout")
    for field, limit in (("statement", 12000), ("proof", 24000)):
        value = q[field]
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError("input")
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        if q[field + "Hash"] != digest:
            raise ValueError("hash mismatch")
    return q

def dispatch(raw, authorization, token):
    if not isinstance(token, str) or len(token) < 32:
        return 503, {"error": "AUTH_NOT_CONFIGURED"}
    if not hmac.compare_digest(authorization.encode(), ("Bearer " + token).encode()):
        return 401, {"error": "UNAUTHORIZED"}
    try:
        q = validate(raw)
    except (ValueError, TypeError, AttributeError, UnicodeError, RecursionError):
        return 400, {"error": "INVALID_REQUEST"}
    return 200, {k: q[k] for k in ("protocol", "requestId", "statementHash", "proofHash")} | {
        "status": "UNAVAILABLE", "diagnostic": "Trusted sandbox adapter not installed"
    }

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/verify":
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            size = -1
        if not 0 <= size <= MAX_BODY or self.headers.get("Transfer-Encoding"):
            self.send_error(400)
            return
        self.connection.settimeout(10)
        try:
            raw = self.rfile.read(size)
            status, result = dispatch(raw, self.headers.get("Authorization", ""), os.environ.get("LNZ_LEAN_WORKER_TOKEN"))
        except (OSError, TimeoutError):
            return
        body = json.dumps(result).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    # Local development only; production requires hardened HTTPS ingress.
    HTTPServer(("127.0.0.1", 8080), Handler).serve_forever()
