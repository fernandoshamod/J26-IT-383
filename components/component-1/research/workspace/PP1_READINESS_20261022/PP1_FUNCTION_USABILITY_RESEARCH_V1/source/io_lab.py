from pathlib import Path
import sys,os,json,hashlib
H=Path(__file__).resolve().parent.parent;ROOT=H.parent.parent;PP1=H.parent
sys.dont_write_bytecode=True
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def sha(p):return hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
def save(p,x):
    p=Path(p).resolve();assert p.is_relative_to(H);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:json.dump(x,f,indent=2,allow_nan=False)
def offline():
    flags={'YOLO_OFFLINE':'true','YOLO_AUTOINSTALL':'false','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','PIP_NO_INDEX':'1','WANDB_MODE':'offline','WANDB_DISABLED':'true','PYTHONDONTWRITEBYTECODE':'1','MPLBACKEND':'Agg'}
    for k,d in [('YOLO_CONFIG_DIR','ultralytics'),('TORCH_HOME','torch'),('HF_HOME','hf'),('MPLCONFIGDIR','mpl'),('TEMP','tmp'),('TMP','tmp'),('TMPDIR','tmp')]:
        p=H/'runtime'/d;p.mkdir(parents=True,exist_ok=True);flags[k]=str(p)
    (H/'runtime/ultralytics/Ultralytics').mkdir(parents=True,exist_ok=True)
    os.environ.update(flags);events={'network':[],'denied_writes':[],'model_opens':[]}
    def audit(event,args):
        if event in {'socket.connect','socket.connect_ex','socket.getaddrinfo','socket.gethostbyname','socket.sendto','socket.sendmsg','socket.bind'}:
            events['network'].append({'event':event,'args':str(args)[:200]});raise RuntimeError('OFFLINE_NETWORK_DENIED')
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            path=Path(os.fsdecode(args[0])).resolve();mode,bits=args[1:]
            if path.suffix.lower() in ['.pt','.pth']:events['model_opens'].append(str(path))
            writing=(isinstance(mode,str) and any(s in mode for s in 'wax+')) or (isinstance(bits,int) and bits&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_APPEND|os.O_TRUNC))
            if writing and not path.is_relative_to(H) and str(path).lower()!=str(Path(os.devnull).resolve()).lower():events['denied_writes'].append(str(path));raise RuntimeError('WRITE_OUTSIDE_NEW_WORKSPACE')
        if event in {'os.mkdir','os.remove','os.rmdir'} and not Path(os.fsdecode(args[0])).resolve().is_relative_to(H):raise RuntimeError('MUTATION_OUTSIDE_WORKSPACE')
    sys.addaudithook(audit);return flags,events
