"""Isolated read-only dependency access; all new evidence is exclusive-created here."""
import os,sys,json,hashlib,time
from pathlib import Path
H=Path(__file__).resolve().parent
PP1=H.parent
ROOT=PP1.parent
sys.dont_write_bytecode=True
for k,v in {'PYTHONDONTWRITEBYTECODE':'1','YOLO_OFFLINE':'true','YOLO_AUTOINSTALL':'false','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','PIP_NO_INDEX':'1','WANDB_DISABLED':'true','MPLBACKEND':'Agg'}.items():os.environ[k]=v
for k,n in [('TEMP','tmp'),('TMP','tmp'),('TMPDIR','tmp'),('MPLCONFIGDIR','mpl')]:
    p=H/'runtime'/n;p.mkdir(parents=True,exist_ok=True);os.environ[k]=str(p)
AUDIT={'network':[],'denied_writes':[]}
def audit(event,args):
    if event in {'socket.connect','socket.getaddrinfo','socket.sendto','socket.bind'}:
        AUDIT['network'].append({'event':event,'args':str(args)[:200]});raise RuntimeError('OFFLINE_NETWORK_DENIED')
    if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
        p=Path(os.fsdecode(args[0])).resolve();mode,bits=args[1:]
        writing=(isinstance(mode,str) and any(v in mode for v in 'wax+')) or (isinstance(bits,int) and bits&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_APPEND|os.O_TRUNC))
        if writing and not p.is_relative_to(H) and p!=Path(os.devnull).resolve():
            AUDIT['denied_writes'].append(str(p));raise RuntimeError('WRITE_OUTSIDE_WORKSPACE')
    if event in {'os.remove','os.mkdir','os.rmdir','os.rename'}:
        if not Path(os.fsdecode(args[0])).resolve().is_relative_to(H):raise RuntimeError('MUTATION_OUTSIDE_WORKSPACE')
sys.addaudithook(audit)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,x):
    p=Path(p).resolve();assert p.is_relative_to(H);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:json.dump(x,f,indent=2,allow_nan=False)
def snapshot():
    pins=read(PP1/'PP1_FINAL_BACKEND_FREEZE_V1/BACKEND_RUNTIME_FREEZE.json')['files']
    extra=[ROOT/p for p in ['Component 1 \u2014 Updated Full Research.txt']]
    for folder in ['PP1_NOVELTY_VALIDATION_V1','PP1_ORIGINAL_RESEARCH_MECHANISM_V1','PP1_ORIGINAL_LAYOUT_RESEARCH_V1','PP1_FUNCTION_USABILITY_RESEARCH_V1','PP1_FINAL_PANEL_RESOLUTION_V1']:
        extra.extend((PP1/folder).glob('*.py'));extra.extend((PP1/folder).glob('*VERDICT.md'))
        extra.extend((PP1/folder/'source').glob('*.py'))
    files={p:sha(ROOT/p) for p in pins}
    files.update({str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in extra})
    return {'files':files,'pinned_count':len(pins),'pin_mismatches':[p for p,s in pins.items() if files[p]!=s]}
