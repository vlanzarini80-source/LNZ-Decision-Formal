import json,os,sys
from signed_execution import signed_execution
code,result=signed_execution(sys.stdin.buffer.read(),"Bearer "+os.environ["LNZ_LEAN_WORKER_TOKEN"])
if code!=200: raise RuntimeError(str(code))
print(json.dumps(result))
