import subprocess,sys,json,time,datetime
from pathlib import Path
H=Path(__file__).resolve().parent;name=sys.argv[1];script=sys.argv[2];folder=H/'logs';folder.mkdir(exist_ok=True);t=time.perf_counter();argv=[sys.executable,'-B',str(H/script),*sys.argv[3:]]
with (folder/(name+'.stdout.txt')).open('x',encoding='utf-8') as out,(folder/(name+'.stderr.txt')).open('x',encoding='utf-8') as err:code=subprocess.call(argv,cwd=H.parents[1],stdout=out,stderr=err)
with (folder/(name+'.COMMAND.json')).open('x',encoding='utf-8') as f:json.dump(dict(argv=argv,cwd=str(H.parents[1]),exit_code=code,seconds=time.perf_counter()-t,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()),f,indent=2)
print(name,'exit',code);sys.exit(code)
