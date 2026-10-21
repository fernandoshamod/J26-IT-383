import os,sys,json,hashlib,datetime
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
sys.dont_write_bytecode=True
os.environ.update(PYTHONDONTWRITEBYTECODE="1",HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",
 HF_HUB_DISABLE_TELEMETRY="1",YOLO_OFFLINE="true",YOLO_AUTOINSTALL="false",PIP_NO_INDEX="1",
 YOLO_CONFIG_DIR=str(H/"runtime/ultralytics"),TORCH_HOME=str(H/"runtime/torch"),
 HF_HOME=str(H/"runtime/hf"),TEMP=str(H/"runtime/tmp"),TMP=str(H/"runtime/tmp"),MPLCONFIGDIR=str(H/"runtime/mpl"))
(H/"runtime/tmp").mkdir(parents=True,exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def save(name,obj):
 p=H/name;assert p.resolve().is_relative_to(H);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open("x",encoding="utf-8") as f:json.dump(obj,f,indent=2,allow_nan=False)
def guard():
 events={"network":[],"denied_writes":[]}
 def hook(event,args):
  if event in {"socket.connect","socket.getaddrinfo","socket.gethostbyname","socket.sendto","socket.bind"}:
   events["network"].append({"event":event,"arguments":repr(args)[:250]});raise RuntimeError("NETWORK_BLOCKED")
  if event=="open" and isinstance(args[0],(str,bytes,os.PathLike)):
   p=Path(os.fsdecode(args[0])).resolve();mode,bits=args[1:3]
   writing=(isinstance(mode,str) and any(c in mode for c in "wax+")) or isinstance(bits,int) and bits&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)
   if writing and str(p).lower()!=str(Path(os.devnull).resolve()).lower() and not p.is_relative_to(H):
    events["denied_writes"].append(str(p));raise RuntimeError("WRITE_OUTSIDE_V3:"+str(p))
  if event in {"os.mkdir","os.remove","os.rmdir"} and not Path(os.fsdecode(args[0])).resolve().is_relative_to(H):raise RuntimeError("MUTATION_OUTSIDE_V3")
 sys.addaudithook(hook);return events
