"""No overwrite; subprocess command/exit/stdout/stderr evidence."""
import sys,json,time,subprocess,datetime
from pathlib import Path
H=Path(__file__).resolve().parent
name,script,*args=sys.argv[1:];logs=H/'logs';logs.mkdir(exist_ok=True)
record=logs/(name+'.COMMAND.json')
if record.exists():raise FileExistsError(record)
argv=[sys.executable,'-B',str(H/script),*args];started=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.perf_counter()
with (logs/(name+'.stdout.txt')).open('x',encoding='utf-8') as out,(logs/(name+'.stderr.txt')).open('x',encoding='utf-8') as err:
    p=subprocess.run(argv,cwd=H.parent.parent,stdout=out,stderr=err)
with record.open('x',encoding='utf-8') as f:json.dump({'argv':argv,'cwd':str(H.parent.parent),'started_utc':started,'exit_code':p.returncode,'wall_s':time.perf_counter()-t},f,indent=2)
print(name,'exit',p.returncode,'wall_s',round(time.perf_counter()-t,3));sys.exit(p.returncode)
