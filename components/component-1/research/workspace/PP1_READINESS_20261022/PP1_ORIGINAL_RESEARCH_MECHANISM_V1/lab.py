"""Output-only bindings to unchanged registered-Twin/Scene/EAG research code."""
import os,sys,json,hashlib,platform,datetime,importlib.util
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=H.parent
sys.dont_write_bytecode=True
os.environ.update(PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',YOLO_OFFLINE='true',YOLO_AUTOINSTALL='false',PIP_NO_INDEX='1',MPLBACKEND='Agg',MPLCONFIGDIR=str(H/'runtime/mpl'),TEMP=str(H/'runtime/tmp'),TMP=str(H/'runtime/tmp'))
(H/'runtime/tmp').mkdir(parents=True,exist_ok=True)
platform.uname()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def save(p,v):
 p=Path(p);p=p if p.is_absolute() else H/p;assert p.resolve().is_relative_to(H)
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8') as f:json.dump(v,f,indent=2,allow_nan=False)
def guard():
 events=dict(network=[],denied_writes=[])
 def check(p):
  if isinstance(p,(str,bytes,os.PathLike)):
   q=Path(os.fsdecode(p)).resolve()
   if str(q).lower()!=str(Path(os.devnull).resolve()).lower() and not q.is_relative_to(H):events['denied_writes'].append(str(q));raise RuntimeError('WRITE_OUTSIDE_EXPERIMENT')
 def hook(e,a):
  if e in ['socket.connect','socket.connect_ex','socket.getaddrinfo','socket.sendto','socket.bind']:
   events['network'].append(dict(event=e,args=repr(a)[:200]));raise RuntimeError('NETWORK_BLOCKED')
  if e=='open' and isinstance(a[0],(str,bytes,os.PathLike)):
   mode,bits=a[1:3]
   if isinstance(mode,str) and any(c in mode for c in 'wax+') or isinstance(bits,int) and bits&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):check(a[0])
  if e in ['os.mkdir','os.remove','os.rmdir']:check(a[0])
  if e=='os.rename':check(a[0]);check(a[1])
  if e=='sqlite3.connect' and not str(a[0]).endswith('?mode=ro'):check(a[0])
 sys.addaudithook(hook);return events
def boot():
 sys.path.insert(0,str(P/'PP1_EAG_APR_IMPLEMENTATION_V1'))
 import runtime
 runtime.HERE=H;runtime.common.HERE=H;runtime.bridge.HERE=H
 sys.path.append(str(P/'PP1_EXECUTABLE_V1'))
 spec=importlib.util.spec_from_file_location('registered_twin_adapter',P/'PP1_REVIEWED_TWIN_SCENE_INTEGRATION_V1/adapter.py');adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter);adapter.H=H
 return runtime,adapter
