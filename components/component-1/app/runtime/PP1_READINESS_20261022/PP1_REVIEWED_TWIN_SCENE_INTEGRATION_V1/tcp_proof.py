import sys,subprocess,json,time,socket,urllib.request,urllib.error
from pathlib import Path
H=Path(__file__).resolve().parent;out=H/'TCP_PROOF';out.mkdir(exist_ok=False)
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
argv=[sys.executable,'-B',str(H/'serve.py'),'--db',str(H/'HTTP/research.sqlite3'),'--port',str(port)]
stdout=(out/'server.stdout.txt').open('x');stderr=(out/'server.stderr.txt').open('x');proc=subprocess.Popen(argv,stdout=stdout,stderr=stderr,cwd=H.parents[1]);records=[]
def call(path,body=None):
 data=None if body is None else json.dumps(body).encode()
 req=urllib.request.Request(f'http://127.0.0.1:{port}'+path,data=data,headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=30) as r:status=r.status;result=json.load(r)
 records.append(dict(path=path,http=status,response=result));return result
try:
 for i in range(150):
  if proc.poll() is not None:raise RuntimeError('SERVER_EXITED')
  try:call('/health');break
  except (urllib.error.URLError,ConnectionError):time.sleep(.1)
 else:raise RuntimeError('SERVER_START_TIMEOUT')
 receipt=json.loads((H/'HTTP/TWIN_RECEIPT.json').read_text());reg=json.loads((H/'HTTP/REGISTER_REQUEST.json').read_text())
 assert call('/twins',reg)==receipt
 assert call(f"/twins/{receipt['venue_id']}/versions/{receipt['venue_version']}")==receipt
 schema=call('/openapi.json');assert schema==json.loads((H/'HTTP/OPENAPI.json').read_text())
 (out/'RESULT.json').write_text(json.dumps(dict(status='PASS',records=records,argv=argv,transport='Actual localhost TCP',optimizer_calls=0),indent=2))
finally:
 proc.terminate();proc.wait(timeout=30);stdout.close();stderr.close()
 (out/'SERVER_STOPPED.json').write_text(json.dumps(dict(stopped=proc.poll() is not None,returncode=proc.returncode)))
print('TCP register/readback and exact OpenAPI PASS; server stopped')
