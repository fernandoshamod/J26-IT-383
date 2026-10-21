"""Capture exact stage subprocess commands and preserve failures."""
import subprocess,sys,time,datetime
from common import *
name=sys.argv[1]
assert name in {"train_yolo","evaluate_yolo","test_adapter","qualify_unet","closeout"}
argv=[sys.executable,"-B",str(H/(name+".py"))]
t=time.perf_counter()
with (H/(name+".stdout.log")).open("x",encoding="utf-8") as out,(H/(name+".stderr.log")).open("x",encoding="utf-8") as err:
 p=subprocess.run(argv,cwd=ROOT,stdout=out,stderr=err)
save(name+".COMMAND.json",{"argv":argv,"cwd":str(ROOT),"exit_code":p.returncode,"seconds":time.perf_counter()-t,"finished_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()})
print(name,"exit",p.returncode,flush=True)
raise SystemExit(p.returncode)
