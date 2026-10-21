"""Boundary, source, CLI, failed-search and offline runtime probes; not a new algorithm."""
import copy,sys,subprocess,ast,argparse
from common import *
from compiler import compile_scene
from bridge import execute,menu
from fixtures import seal
from models import Request
from oracle import validate_result

a=argparse.ArgumentParser();a.add_argument('--out',default='outputs/SUPPLEMENTAL_FINAL');args=a.parse_args();out=(HERE/args.out).resolve()
if not out.is_relative_to(HERE):raise ValueError('ISOLATION')
out.mkdir(parents=True,exist_ok=False);relative=out.relative_to(HERE).as_posix();base=HERE/'outputs/COMPILER_FINAL';checks=[]
def check(name,ok,detail=None):checks.append(dict(name=name,passed=bool(ok),detail=detail));print(name,bool(ok),flush=True)
good=read(HERE/'outputs/BRIDGE_FINAL/wedding_EMPTY/RESULT.json')
for n in [1,2]:
    r=menu(good['candidate_layouts'][:n]);save(out/f'MENU_{n}.json',r);check(f'NO_MANUFACTURED_{n}_TO_THREE',len(r['selected_ids'])<=n)
duplicates=[copy.deepcopy(good['candidate_layouts'][0]) for _ in range(3)]
for i,x in enumerate(duplicates):x['layout_id']='POISON_DUPLICATE_'+str(i)
res=menu(duplicates);save(out/'DUPLICATE_MENU_NEGATIVE.json',dict(test_input=duplicates,result=res));check('NO_DUPLICATE_LAYOUT_MENU',len(res['selected_ids'])==1)
for event in ['birthday_EMPTY','anniversary_EMPTY','corporate_EMPTY','musical_show_EMPTY']:
    r=read(base/event/'REQUEST.json');s=read(base/event/'SPEC.json');res=execute(r,s,out/('UNSUPPORTED_'+event));check(event+'_EXECUTION_SCOPE',res['status']=='rejected' and res['optimizer_calls']==0 and res['reason']=='FROZEN_OPTIMIZER_EVENT_PROFILE_UNSUPPORTED')
r=read(base/'wedding_EMPTY/REQUEST.json');r['planner']['hard']['maximum_mean_stage_distance_m']=.001;r=seal(r,out/'IMPOSSIBLE_BOUND_INPUT');s=compile_scene(r);res=execute(r,s,out/'ACTUAL_FAILED_SEARCH');save(out/'ACTUAL_FAILED_SEARCH/INDEPENDENT_RESULT.json',validate_result(r,s,res));check('ACTUAL_FINITE_SEARCH_FAILURE_HONEST',res['status']=='failed_search' and res['optimizer_calls']==1 and res['optimizer_evaluations']>0 and res.get('global_infeasibility_proven') is False,dict(reason=res['reason'],evaluations=res['optimizer_evaluations']))
r=read(base/'WEDDING_PARTIAL/REQUEST.json');r['client']['weather_score']=1.
try:Request.model_validate(r);check('UNKNOWN_UNSUPPORTED_FIELDS_REJECTED',False)
except ValueError as e:check('UNKNOWN_UNSUPPORTED_FIELDS_REJECTED',True,str(e))
# A foreign-source document cannot be rebound by editing only its Evidence envelope.
r=read(base/'WEDDING_PARTIAL/REQUEST.json');record=read(r['planner']['evidence']['path']);record['source_sha256']='e'*64;path=out/'FOREIGN_DOCUMENT.json';save(path,record);r['planner']['evidence'].update(path=str(path),sha256=filehash(path));s=compile_scene(r);check('FOREIGN_DOCUMENT_SOURCE_REJECTED',s['status']=='rejected' and any(i['code']=='EVIDENCE_DOCUMENT_SOURCE_MISMATCH' for i in s['issues']));save(out/'FOREIGN_DOCUMENT_RESULT.json',s)
# Real CLI command and output; no copied or simulated response.
cmd=[sys.executable,'-B',str(HERE/'research.py'),'compile','--input',str(base/'WEDDING_PARTIAL/REQUEST.json'),'--out',relative+'/CLI_COMPILE']
proc=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);save(out/'CLI_COMPILE_COMMAND.json',dict(args=cmd,exit_code=proc.returncode,stdout=proc.stdout,stderr=proc.stderr));check('CLI_COMPILE',proc.returncode==0)
# Guard is installed before runtime imports in a fresh interpreter. It is Python-level, not OS capture.
code="""import sys,runpy,json
from pathlib import Path
events=[];local=[];networklog=Path(sys.argv[3]);output=sys.argv[4]
def guard(event,args):
 if event=='socket.gethostname':local.append(event)
 if event in ['socket.connect','socket.connect_ex','socket.getaddrinfo','socket.gethostbyname','socket.gethostbyaddr','socket.sendto','socket.sendmsg','socket.bind']:
  events.append(event)
  raise RuntimeError('PYTHON_NETWORK_ATTEMPT:'+event)
sys.addaudithook(guard)
sys.path.insert(0,str(Path(sys.argv[1]).parent))
sys.argv=[sys.argv[1],'run','--input',sys.argv[2],'--out',output]
try:runpy.run_path(sys.argv[0],run_name='__main__')
finally:networklog.write_text(json.dumps({'denied_network_events':events,'local_hostname_reads':local,'scope':'Python audit events only, not OS/native traffic capture'},indent=2),encoding='utf-8')
"""
cmd=[sys.executable,'-B','-c',code,str(HERE/'research.py'),str(base/'WEDDING_PARTIAL/REQUEST.json'),str(out/'NETWORK_EVENTS.json'),relative+'/OFFLINE_CLI']
proc=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);save(out/'OFFLINE_CLI_COMMAND.json',dict(args=cmd,exit_code=proc.returncode,stdout=proc.stdout,stderr=proc.stderr));check('ACTUAL_OFFLINE_CLI_OPTIMIZATION',proc.returncode==0,dict(stdout=proc.stdout,stderr=proc.stderr))
for p in HERE.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
check('ALL_SOURCE_SYNTAX',True)
save(out/'SUPPLEMENTAL_ACCEPTANCE.json',dict(passed=all(c['passed'] for c in checks),checks=checks))
if not all(c['passed'] for c in checks):raise SystemExit(1)
