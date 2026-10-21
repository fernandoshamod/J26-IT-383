from pathlib import Path
import sys,subprocess,json,time,datetime
H=Path(__file__).resolve().parent
name,script=sys.argv[1:3];out=H/'logs';out.mkdir(exist_ok=True)
cmd=[sys.executable,'-B',str(H/script),*sys.argv[3:]];start=time.perf_counter()
with (out/(name+'.stdout.txt')).open('x',encoding='utf8') as so,(out/(name+'.stderr.txt')).open('x',encoding='utf8') as se:
 p=subprocess.run(cmd,cwd=H.parents[1],stdout=so,stderr=se)
with (out/(name+'.COMMAND.json')).open('x',encoding='utf8') as f:json.dump(dict(argv=cmd,cwd=str(H.parents[1]),exit_code=p.returncode,seconds=time.perf_counter()-start,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()),f,indent=2)
print(name,'exit',p.returncode,flush=True);sys.exit(p.returncode)
