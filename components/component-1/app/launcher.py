"""Four-service local launcher with health checks and identity-safe shutdown."""
from __future__ import annotations
import argparse, datetime, json, os, shutil, socket, subprocess, sys, time, urllib.request, uuid
from pathlib import Path
import psutil
from portable_runtime import PACKAGE_ROOT as ROOT, RUNTIME_ROOT, STATE_ROOT, PORTS

FRONT=ROOT/'frontend'
BACKEND=RUNTIME_ROOT/'PP1_READINESS_20261022/PP1_FINAL_BACKEND_FREEZE_V1/backend.py'
COMPANION=RUNTIME_ROOT/'PP1_READINESS_20261022/PP1_REAL_TWIN_LAYOUT_COMPLETION_V1/companion/layout_edit_api.py'
SCENE=RUNTIME_ROOT/'PP1_READINESS_20261022/PP1_COMPLETE_LO1_LO2_LO3_RELEASE_V1/scene_compiler_service.py'
RUNS=STATE_ROOT/'runs'
HEALTH={'backend':f"http://127.0.0.1:{PORTS['backend']}/health",'companion':f"http://127.0.0.1:{PORTS['companion']}/health",'scene':f"http://127.0.0.1:{PORTS['scene']}/health",'frontend':f"http://127.0.0.1:{PORTS['frontend']}/"}

def identity(pid):
    p=psutil.Process(pid)
    return {'pid':pid,'create_time':p.create_time(),'exe':p.exe(),'cmdline':p.cmdline()}

def ports_free():
    result=[]
    for name,port in PORTS.items():
        with socket.socket() as s:
            try:s.bind(('127.0.0.1',port))
            except OSError:result.append({'service':name,'port':port,'reason':'PORT_IN_USE_NO_PROCESS_TERMINATED'})
    return result

def commands(out):
    py=str(Path(sys.executable).resolve());node=shutil.which('node')
    if not node:raise RuntimeError('NODE_22_NOT_FOUND_ON_PATH')
    return [
      ('backend',[py,'-B',str(BACKEND),'serve','--db',str(out/'backend.sqlite3'),'--port',str(PORTS['backend'])],RUNTIME_ROOT),
      ('companion',[py,'-B',str(COMPANION),'--db',str(out/'companion.sqlite3'),'--backend',f"http://127.0.0.1:{PORTS['backend']}",'--port',str(PORTS['companion'])],RUNTIME_ROOT),
      ('scene',[py,'-B',str(SCENE),'--port',str(PORTS['scene'])],RUNTIME_ROOT),
      ('frontend',[node,str(FRONT/'node_modules/vite/bin/vite.js'),'preview','--host','127.0.0.1','--port',str(PORTS['frontend'])],FRONT)]

def wait_health(child,url,log_path,timeout=90):
    end=time.monotonic()+timeout;last=''
    while time.monotonic()<end:
        if child.poll() is not None:raise RuntimeError(f'SERVICE_EXITED:{child.returncode}; inspect {log_path}')
        try:
            with urllib.request.urlopen(url,timeout=2) as response:
                if response.status==200:return
        except Exception as exc:last=str(exc)
        time.sleep(.35)
    raise RuntimeError(f'HEALTH_TIMEOUT:{url}:{last}; inspect {log_path}')

def start(run):
    if not run.replace('_','').replace('-','').isalnum():raise ValueError('UNSAFE_RUN_ID')
    errors=ports_free()
    if errors:raise RuntimeError(json.dumps(errors))
    out=RUNS/run
    out.mkdir(parents=True,exist_ok=False)
    env=os.environ.copy();env.update(PP1_RUNTIME_STATE=str(STATE_ROOT),PP1_RUN_STATE=str(out),PP1_PRIVATE_ASSETS=str(ROOT/'private-assets'),PP1_FRONTEND_PORT=str(PORTS['frontend']),PP1_BACKEND_PORT=str(PORTS['backend']),PP1_COMPANION_PORT=str(PORTS['companion']),PP1_SCENE_PORT=str(PORTS['scene']),PYTHONDONTWRITEBYTECODE='1',YOLO_AUTOINSTALL='false',YOLO_OFFLINE='true')
    state={'schema':'PP1_PORTABLE_RUN_V1','run':run,'status':'STARTING','ports':PORTS,'processes':[],'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (out/'STATE.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
    try:
        for name,argv,cwd in commands(out):
            stdout=(out/f'{name}.stdout.log').open('w',encoding='utf-8');stderr=(out/f'{name}.stderr.log').open('w',encoding='utf-8')
            flags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP if os.name=='nt' else 0
            proc=subprocess.Popen(argv,cwd=cwd,env=env,stdout=stdout,stderr=stderr,creationflags=flags)
            stdout.close();stderr.close();record=identity(proc.pid);record.update(role=name,launch_argv=argv,cwd=str(cwd),health_url=HEALTH[name]);state['processes'].append(record)
            (out/'STATE.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
            wait_health(proc,HEALTH[name],out/f'{name}.stderr.log')
        state['status']='READY';state['ready_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();(out/'STATE.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
        (STATE_ROOT/'CURRENT_RUN.json').write_text(json.dumps({'run':run},indent=2),encoding='utf-8')
        print(json.dumps({'status':'READY','url':HEALTH['frontend'],'run':run,'stop':f'.\\stop.ps1 -Run {run}'},indent=2))
    except Exception as exc:
        state['status']='START_FAILED';state['failure']=repr(exc);(out/'STATE.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
        stop(run);raise

def stop(run):
    out=RUNS/run;state=json.loads((out/'STATE.json').read_text(encoding='utf-8'));actions=[]
    for record in reversed(state.get('processes',[])):
        try:
            p=psutil.Process(record['pid']);live=identity(record['pid'])
            if abs(live['create_time']-record['create_time'])>.02 or live['exe'].lower()!=record['exe'].lower() or live['cmdline']!=record['cmdline']:
                actions.append({'role':record['role'],'status':'REFUSED_IDENTITY_MISMATCH'});continue
            children=p.children(recursive=True)
            snapshots={proc.pid:identity(proc.pid) for proc in [p,*children] if proc.is_running()}
            for child in children:child.terminate()
            p.terminate();_,alive=psutil.wait_procs([p,*children],timeout=8)
            for proc in alive:
                snap=snapshots.get(proc.pid)
                if snap and abs(proc.create_time()-snap['create_time'])<.02:proc.kill()
            actions.append({'role':record['role'],'status':'STOPPED_OWNED_PROCESS_TREE'})
        except psutil.NoSuchProcess:actions.append({'role':record['role'],'status':'ALREADY_EXITED'})
    state['status']='STOPPED';state['shutdown']={'actions':actions,'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (out/'STATE.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
    print(json.dumps(state['shutdown'],indent=2))
    return 2 if any(x['status']=='REFUSED_IDENTITY_MISMATCH' for x in actions) else 0

def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='action',required=True)
    s=sub.add_parser('start');s.add_argument('--run',default='PP1_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6])
    x=sub.add_parser('stop');x.add_argument('--run',required=True)
    a=ap.parse_args()
    if a.action=='start':start(a.run);return 0
    return stop(a.run)
if __name__=='__main__':raise SystemExit(main())
