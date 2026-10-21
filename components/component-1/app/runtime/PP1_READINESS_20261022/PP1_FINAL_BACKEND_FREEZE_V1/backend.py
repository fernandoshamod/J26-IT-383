"""Single final entrypoint: verify-freeze, serve, lifecycle, handoff."""
import sys,argparse,subprocess,socket
from pathlib import Path
H=Path(__file__).resolve().parent
def main():
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
 sub.add_parser('verify-freeze')
 s=sub.add_parser('serve');s.add_argument('--db',required=True);s.add_argument('--port',type=int,default=8765)
 s=sub.add_parser('lifecycle');s.add_argument('--name',required=True)
 s=sub.add_parser('handoff');s.add_argument('--receipt',required=True);s.add_argument('--db',required=True);s.add_argument('--brief',required=True);s.add_argument('--out',required=True)
 a=p.parse_args()
 from runtime_check import verify
 import json
 proof=verify()
 if a.command=='verify-freeze':print(json.dumps(proof));return
 if a.command=='serve':
  # Do not terminate another server or change its port silently.
  with socket.socket() as probe:
   try:probe.bind(('127.0.0.1',a.port))
   except OSError:raise SystemExit('PORT_IN_USE: stop the identified existing server or explicitly choose another port')
  from application import create_app
  import uvicorn
  uvicorn.run(create_app(a.db),host='127.0.0.1',port=a.port,log_level='info');return
 if a.command=='lifecycle':
  if Path(a.name).name!=a.name:raise ValueError('SIMPLE_NEW_OUTPUT_NAME_REQUIRED')
  argv=[sys.executable,'-B',str(H/'stages.py'),'lifecycle',a.name]
 else:
  argv=[sys.executable,'-B',str(H/'stages.py'),'scene_handoff','--receipt',a.receipt,'--db',a.db,'--brief',a.brief,'--out',a.out]
 raise SystemExit(subprocess.run(argv,cwd=H.parents[1]).returncode)
if __name__=='__main__':main()
