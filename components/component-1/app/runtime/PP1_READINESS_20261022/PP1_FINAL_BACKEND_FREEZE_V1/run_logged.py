import sys,subprocess,json,time,os
from pathlib import Path
H=Path(__file__).resolve().parent;name=sys.argv[1];argv=[sys.executable,'-B',*sys.argv[2:]]
log=H/'logs';log.mkdir(exist_ok=True);start=time.time()
with (log/(name+'.stdout.txt')).open('x') as out,(log/(name+'.stderr.txt')).open('x') as err:
 r=subprocess.run(argv,cwd=H.parents[1],stdout=out,stderr=err,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
with (log/(name+'.COMMAND.json')).open('x') as f:json.dump(dict(argv=argv,cwd=str(H.parents[1]),exit_code=r.returncode,elapsed_seconds=time.time()-start),f,indent=2)
print(name,'exit',r.returncode);sys.exit(r.returncode)
