import os, json, re, subprocess, tempfile, uuid
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from bridge import bridge
from gateway import MAX_BODY

def executor(source, timeout):
    image=os.environ["LNZ_IMAGE_ID"]
    if not re.fullmatch(r"sha256:[0-9a-f]{64}",image):
        raise ValueError("image ID required")
    lean=Path(os.environ["LNZ_LEAN_DIST"]).resolve(strict=True)
    name="lnz-"+uuid.uuid4().hex
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)/"Candidate.lean"
        p.write_text(source,encoding="utf8")
        p.chmod(0o644)
        args=["docker","run","--pull=never","--name",name,"--rm","--network","none","--read-only","--cap-drop","ALL","--security-opt","no-new-privileges","--pids-limit","64","--memory","2g","--memory-swap","2g","--cpus","2","--user","65534:65534","--tmpfs","/tmp:rw,noexec,nosuid,size=64m","-v",str(lean)+":/opt/lean:ro","-v",str(p)+":/input/Candidate.lean:ro",image,"/opt/lean/bin/lean","/input/Candidate.lean"]
        try:
            r=subprocess.run(args,capture_output=True,timeout=timeout)
            log=r.stdout+r.stderr
            if len(log)>65536:
                return 125,"output limit"
            return r.returncode,log.decode("utf8",errors="replace")
        except subprocess.TimeoutExpired:
            return 124,"timeout"
        finally:
            subprocess.run(["docker","rm","-f",name],capture_output=True,timeout=15)

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path!="/verify":
            self.send_error(404)
            return
        try:
            lengths=self.headers.get_all("Content-Length",[])
            if len(lengths)!=1 or self.headers.get("Transfer-Encoding"):
                raise ValueError()
            size=int(lengths[0])
            if not 0<=size<=MAX_BODY:
                raise ValueError()
            self.connection.settimeout(10)
            raw=self.rfile.read(size)
            if len(raw)!=size:
                raise ValueError()
        except (ValueError,OSError):
            self.send_error(400)
            return
        code,result=bridge(raw,self.headers.get("Authorization",""),os.environ.get("LNZ_LEAN_WORKER_TOKEN"),executor)
        body=json.dumps(result).encode()
        self.send_response(code)
        self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(body)))
        self.end_headers()
        self.wfile.write(body)

if __name__=="__main__":
    HTTPServer(("127.0.0.1",8080),Handler).serve_forever()
