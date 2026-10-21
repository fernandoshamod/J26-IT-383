from pathlib import Path
import sys,subprocess,time,json,datetime,os
H=Path(__file__).resolve().parent.parent;ROOT=H.parent.parent
SOURCE=H/'source'
if os.environ.get('USABILITY_RUN_NAME'):
    import re
    repeat=os.environ['USABILITY_RUN_NAME'];assert re.fullmatch('[A-Za-z0-9_]+',repeat)
    H=H/'repeats'/repeat;H.mkdir(parents=True,exist_ok=True)
name,script,*args=sys.argv[1:];logs=H/'logs';logs.mkdir(exist_ok=True)
cmd=[sys.executable,'-B',str(SOURCE/script),*args];start=time.perf_counter()
with (logs/(name+'.stdout.txt')).open('x',encoding='utf-8') as out,(logs/(name+'.stderr.txt')).open('x',encoding='utf-8') as err:
    p=subprocess.run(cmd,cwd=ROOT,stdout=out,stderr=err,env={**os.environ,'PYTHONIOENCODING':'utf-8','PYTHONDONTWRITEBYTECODE':'1'})
with (logs/(name+'.COMMAND.json')).open('x',encoding='utf-8') as f:json.dump(dict(argv=cmd,cwd=str(ROOT),repeat_name=os.environ.get('USABILITY_RUN_NAME'),exit=p.returncode,elapsed_s=time.perf_counter()-start,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()),f,indent=2)
print(name,'exit',p.returncode,'elapsed',round(time.perf_counter()-start,2));sys.exit(p.returncode)
