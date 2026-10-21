import subprocess,time
from common import *
stage=sys.argv[1];assert stage in {"train_unet","evaluate_unet","prepare_cad","train_cad","evaluate_cad","test_uploads","finalize"}
argv=[sys.executable,"-B",str(H/(stage+".py"))];t=time.perf_counter()
with (H/(stage+".stdout.log")).open("x",encoding="utf-8") as out,(H/(stage+".stderr.log")).open("x",encoding="utf-8") as err:
 p=subprocess.run(argv,cwd=ROOT,stdout=out,stderr=err)
save(stage+".COMMAND.json",{"argv":argv,"cwd":str(ROOT),"exit_code":p.returncode,"seconds":time.perf_counter()-t})
print(stage,"exit",p.returncode,flush=True)
raise SystemExit(p.returncode)
