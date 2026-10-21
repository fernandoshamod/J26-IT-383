from common import *
import subprocess,time
source=ROOT/'01_DATASET_DOWNLOADS/CubiCasa5K/cubicasa5k/cubicasa5k/high_quality_architectural/1848/F1_scaled.png'
argv=[sys.executable,'-B',str(H/'research.py'),'perceive','--source',str(source),'--route','indoor','--out',str(H/'outputs/NATIVE_CLI_001')]
t=time.perf_counter()
with (H/'logs/NATIVE_CLI.stdout.log').open('x',encoding='utf-8') as out,(H/'logs/NATIVE_CLI.stderr.log').open('x',encoding='utf-8') as err:p=subprocess.run(argv,cwd=ROOT,stdout=out,stderr=err)
save('logs/NATIVE_CLI.COMMAND.json',{'argv':argv,'cwd':str(ROOT),'exit_code':p.returncode,'seconds':time.perf_counter()-t})
assert p.returncode==0
result=read(H/'outputs/NATIVE_CLI_001/DOCUMENT_RESULT.json');assert result['metric_twin_ready'] is False
print('Fresh native CLI EXPECTED_PENDING')
