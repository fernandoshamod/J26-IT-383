"""Fresh actual localhost HTTP test of new launcher and frozen backend contracts."""
from common import *
import socket,subprocess,time,urllib.request,urllib.error,hashlib
from perception import backend_modules
backend_modules()
from fixtures import optimization
out=H/'outputs/TCP_002';out.mkdir(parents=True,exist_ok=False)
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
argv=[sys.executable,'-B',str(H/'research.py'),'serve','--db',str(out/'research.sqlite3'),'--port',str(port)]
records=[]
def request(path,body=None,binary=False):
 req=urllib.request.Request('http://127.0.0.1:'+str(port)+path,data=body if binary else json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/octet-stream' if binary else 'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=120) as r:code,data=r.status,r.read()
 except urllib.error.HTTPError as e:code,data=e.code,e.read()
 try:response=json.loads(data)
 except (ValueError,UnicodeDecodeError):response={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
 records.append({'path':path,'http':code,'response':response});return code,response
with (out/'SERVER.stdout.log').open('x',encoding='utf-8') as stdout,(out/'SERVER.stderr.log').open('x',encoding='utf-8') as stderr:
 server=subprocess.Popen(argv,cwd=ROOT,stdout=stdout,stderr=stderr)
 try:
  for _ in range(80):
   if server.poll() is not None:raise RuntimeError('SERVER_EARLY_EXIT')
   try:
    code,health=request('/health')
    if code==200:break
   except OSError:time.sleep(.2)
  else:raise RuntimeError('SERVER_START_TIMEOUT')
  code,contracts=request('/contracts');assert code==200 and contracts['analysis']['properties']['experimental_chair']['default'] is False
  source=ROOT/'01_DATASET_DOWNLOADS/CubiCasa5K/cubicasa5k/cubicasa5k/high_quality_architectural/1848/F1_scaled.png'
  code,uploaded=request('/images',source.read_bytes(),True);assert code==200 and uploaded['sha256']==sha(source)
  code,analysis=request('/analyses',{'image_path':uploaded['image_path']});assert code==200
  assert analysis['status']=='review_required' and analysis['model_report']['actual_model_calls']=={'unet':1,'opening_yolo':1} and analysis['model_report']['event_objects']['calls']==0
  assert 'GEOMETRY_CANDIDATES.png' in analysis['artifacts'] and isinstance(analysis['model_report']['structural_candidates'],int) and isinstance(analysis['model_report']['yolo_candidates'],int)
  save(out.relative_to(H)/'ACTUAL_ANALYSIS_RESPONSE.json',analysis)
  code,retrieved=request('/analyses/'+analysis['analysis_id']);assert code==200 and retrieved==analysis
  meta=analysis['artifacts']['UNET_OVERLAY.png'];code,artifact=request(meta['url']);assert code==200 and artifact['sha256']==meta['sha256']
  code,refusal=request('/twins',{'review':analysis['pending_review_template'],'candidate_bundle':analysis['candidate_bundle']});assert code==422
  code,denial=request('/optimize',optimization({'venue_id':'UNREGISTERED_REAL_PIXELS','venue_version':1,'twin_sha256':'0'*64}));assert code==200 and denial['status']!='success' and denial['optimizer_evaluations']==0
  code,readback=request('/runs/'+denial['run_id']);assert code==200 and readback['response']==denial
  node=H.parent/'PP1_FRONTEND_V1/tooling/node-v22.23.3-win-x64/node.exe'
  validate=[str(node),str(H/'check_frontend_contract.mjs'),str(out/'ACTUAL_ANALYSIS_RESPONSE.json')]
  p=subprocess.run(validate,cwd=ROOT,capture_output=True,text=True);assert p.returncode==0,p.stderr
  save(out.relative_to(H)/'FRONTEND_CONTRACT_CHECK.json',{'argv':validate,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
 finally:
  server.terminate();server.wait(timeout=15)
  save(out.relative_to(H)/'TCP_RESULT.json',{'server_argv':argv,'cwd':str(ROOT),'pid':server.pid,'server_stopped_by_harness':True,'server_exit_after_termination':server.returncode,'records':records,'note':'Localhost HTTP is intentionally used; not a claim of no APIs. This check does not execute an optimization search.'})
print('TCP updated-model upload/analysis, pending refusal, zero-evaluation denial/readback and existing frontend response schema PASS')
