import sys,subprocess,json,time,os
from pathlib import Path
H=Path(__file__).resolve().parent;stage=sys.argv[1];name=sys.argv[2] if len(sys.argv)>2 else stage
log=H/'logs';log.mkdir(exist_ok=True);argv=[sys.executable,'-B',str(H/(stage+'.py')),*sys.argv[3:]]
start=time.time()
with (log/(name+'.stdout.txt')).open('x') as stdout,(log/(name+'.stderr.txt')).open('x') as stderr:
 result=subprocess.run(argv,cwd=H.parents[1],stdout=stdout,stderr=stderr,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
with (log/(name+'.COMMAND.json')).open('x') as f:json.dump(dict(argv=argv,cwd=str(H.parents[1]),exit_code=result.returncode,elapsed_seconds=time.time()-start),f,indent=2)
print(stage,'exit',result.returncode)
sys.exit(result.returncode)
