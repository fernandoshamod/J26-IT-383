"""One integration entrypoint; actual perception and controlled lifecycle remain explicit paths."""
from common import *
import argparse,subprocess,time
def main():
 parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
 p=sub.add_parser('perceive');p.add_argument('--source',required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--route',choices=['indoor','outdoor','hybrid'],default='indoor');p.add_argument('--experimental-chair',action='store_true')
 p=sub.add_parser('lifecycle');p.add_argument('--name',default='CONTROLLED_001')
 p=sub.add_parser('serve');p.add_argument('--db',type=Path,required=True);p.add_argument('--port',type=int,default=8765)
 a=parser.parse_args()
 if a.command=='perceive':
  from perception import understand
  events=guard();result=understand(a.source,a.out,a.route,a.experimental_chair);save(a.out.resolve().relative_to(H)/'GUARD.json',events);print('EXPECTED_PENDING',len(result),'page(s), no optimizer call')
 elif a.command=='lifecycle':
  if Path(a.name).name!=a.name or a.name in ['.','..']:raise ValueError('SIMPLE_NEW_RUN_NAME_REQUIRED')
  out=H/a.name;out.mkdir(exist_ok=False)
  argv=[sys.executable,'-B',str(H/'lifecycle_worker.py'),a.name];t=time.perf_counter()
  with (out/'STDOUT.log').open('x',encoding='utf-8') as stdout,(out/'STDERR.log').open('x',encoding='utf-8') as stderr:child=subprocess.run(argv,cwd=ROOT,stdout=stdout,stderr=stderr)
  save(out.relative_to(H)/'COMMAND.json',{'argv':argv,'cwd':str(ROOT),'exit_code':child.returncode,'seconds':time.perf_counter()-t});raise SystemExit(child.returncode)
 else:
  from integrated_api import create_app
  import uvicorn
  uvicorn.run(create_app(a.db),host='127.0.0.1',port=a.port)
if __name__=='__main__':main()
