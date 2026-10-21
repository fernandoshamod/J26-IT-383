"""Exclusive logged execution; outputs and cache constrained to this workspace."""
from common import *
import subprocess,time,platform
stage=sys.argv[1];attempt=sys.argv[2] if len(sys.argv)>2 else '001'
assert stage in ['train_objects','evaluate_objects','test_integration','verify_objects','qualify_outdoor','test_annotation']
prefix=H/'evidence'/(stage+'_'+attempt);prefix.parent.mkdir(exist_ok=True)
argv=[sys.executable,'-B',str(H/(stage+'.py'))];t=time.perf_counter()
with prefix.with_suffix('.stdout.log').open('x',encoding='utf-8') as out,prefix.with_suffix('.stderr.log').open('x',encoding='utf-8') as err:
 child=subprocess.run(argv,cwd=ROOT,stdout=out,stderr=err)
save(prefix.relative_to(H).with_suffix('.COMMAND.json'),{'argv':argv,'cwd':str(ROOT),'exit_code':child.returncode,'seconds':time.perf_counter()-t,'python':sys.executable,'environment':{k:v for k,v in os.environ.items() if k in ['HF_HUB_OFFLINE','YOLO_AUTOINSTALL','YOLO_OFFLINE','TEMP','TORCH_HOME','YOLO_CONFIG_DIR']}})
print(stage,'exit',child.returncode,'seconds',time.perf_counter()-t);raise SystemExit(child.returncode)
