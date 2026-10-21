"""Read-only dependencies, isolated writers, no model/API/frontend changes."""
import sys,json,hashlib,importlib.util,uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];SCENE=HERE.parent/'PP1_EVENT_SCENE_INTELLIGENCE_V1';BACKEND=HERE.parent/'PP1_EXECUTABLE_V1'
sys.dont_write_bytecode=True;sys.path.insert(0,str(SCENE))
import common,compiler,baseline,fixtures,bridge,oracle
# Explicit in-memory output relocation, preserving old policy/input paths.
common.HERE=HERE;bridge.HERE=HERE
digest=common.digest;read=common.read;save=common.save;filehash=common.filehash
POLICY=read(SCENE/'profiles.json')
sys.path.append(str(ROOT/'PP1_STAGE_E_RESEARCH_CORE/research'))

def load_engine(name):
    loader=importlib.util.spec_from_file_location('eag_frozen_'+uuid.uuid4().hex,BACKEND/(name+'.py'));m=importlib.util.module_from_spec(loader);loader.loader.exec_module(m);return m

def source_versions():return {str(p.relative_to(ROOT)):filehash(p) for p in [SCENE/n for n in ['compiler.py','baseline.py','core.py','models.py','oracle.py','profiles.json']]+[BACKEND/n for n in ['engine_initial.py','engine_adaptive.py','engine_support.py']]}

def facts(packet):
    r=packet['scene'];v=r['venue'];paths=[v['source']['path'],v['review']['evidence']['path'],r['client']['evidence']['path'],r['planner']['evidence']['path'],packet['authority']['path']]
    return dict(scene=digest(r),context=digest(packet['context']),authority=digest(packet['authority']),artifacts={p:filehash(p) if Path(p).is_file() else None for p in paths},policy=digest(POLICY),code=source_versions())

def snapshot():
    # Reuse previous preserved reference inventory, avoiding repeated raw-data hashes.
    prior=read(HERE.parent/'PP1_PANEL_WARNING_CLOSURE_FINAL_V1/outputs/EXPERIMENT_FINAL/PRESERVATION_BEFORE.json')
    paths={ROOT/p for p in prior}
    for folder,manifest in [('PP1_PANEL_WARNING_CLOSURE_FINAL_V1','ARTIFACT_SHA256.json'),('PP1_MASTER_AUDIT_AND_CLEANUP_PLAN_V1','ARTIFACT_SHA256.json')]:
        base=HERE.parent/folder;paths.add(base/manifest);paths.update(base/p for p in read(base/manifest))
    # Check metadata for all large baseline dependencies; hash small source/evidence.
    return {str(p.relative_to(ROOT)):dict(bytes=p.stat().st_size,mtime_ns=p.stat().st_mtime_ns,sha256=filehash(p) if p.stat().st_size<=1000000 else None) for p in sorted(paths)}

def seal_packet(scene,context,out):
    payload=dict(scene_sha256=digest(scene),context=context,scope='SIMULATED_FIXTURE_NOT_AUTHENTICATED_AUTHORITY');p=out/'AUTHORITY_SIMULATED.json';save(p,payload)
    return dict(scene=scene,context=context,authority=dict(path=str(p.resolve()),sha256=filehash(p)))
