from common import *
import subprocess,time
stage=sys.argv[1];attempt=sys.argv[2] if len(sys.argv)>2 else '001'
assert stage in ['integration_checks','run_regression','tcp_check','finalize']
folder=H/'logs';folder.mkdir(exist_ok=True);prefix=folder/(stage+'_'+attempt);argv=[sys.executable,'-B',str(H/(stage+'.py'))];t=time.perf_counter()
with prefix.with_suffix('.stdout.log').open('x',encoding='utf-8') as out,prefix.with_suffix('.stderr.log').open('x',encoding='utf-8') as err:p=subprocess.run(argv,cwd=ROOT,stdout=out,stderr=err)
save(prefix.relative_to(H).with_suffix('.COMMAND.json'),{'argv':argv,'cwd':str(ROOT),'exit_code':p.returncode,'seconds':time.perf_counter()-t,'python':sys.version,'offline_flags':{k:os.environ[k] for k in ['HF_HUB_OFFLINE','YOLO_OFFLINE','YOLO_AUTOINSTALL','YOLO_CONFIG_DIR','TORCH_HOME']}})
print(stage,'exit',p.returncode);raise SystemExit(p.returncode)
