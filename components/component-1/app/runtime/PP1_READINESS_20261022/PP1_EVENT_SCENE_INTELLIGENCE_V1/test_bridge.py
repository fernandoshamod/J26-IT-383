import argparse,copy,sqlite3,json
from common import *
from bridge import execute
from oracle import validate_result,validate_spec
from compiler import compile_scene

def run(compiler_run,out):
    assert read(compiler_run/'COMPILER_ACCEPTANCE.json')['passed'],'COMPILER_ORACLE_GATE_MUST_PASS_FIRST'
    out.mkdir(parents=True,exist_ok=False);results=[];runs=[]
    def check(name,passed,detail=None):results.append(dict(name=name,passed=bool(passed),detail=detail));print(name,bool(passed),flush=True)
    for name in ['wedding_EMPTY','WEDDING_PARTIAL','WEDDING_DANCING','WEDDING_120','PERMITTED_EXCESS_REMOVAL','STRICTER_HARD_CONSTRAINTS']:
        r=read(compiler_run/name/'REQUEST.json');spec=read(compiler_run/name/'SPEC.json');response=execute(r,spec,out/name);v=validate_result(r,spec,response);save(out/name/'INDEPENDENT_RESULT.json',v)
        check(name+'_ACTUAL_OPTIMIZER',response['status']=='success' and response['optimizer_calls']==1 and response['optimizer_evaluations']>0,dict(status=response['status'],reason=response['reason'],evaluations=response['optimizer_evaluations'],candidate_count=len(response['candidate_layouts']),menu_count=len(response['selected_ids'])))
        check(name+'_INDEPENDENT_GEOMETRY_FUNCTION_XAI',v['valid'],v)
        with sqlite3.connect(out/name/'scene.sqlite3') as c:row=c.execute('SELECT response,sha FROM results WHERE run_id=?',(response['run_id'],)).fetchone()
        check(name+'_PERSISTENCE',digest(json.loads(row[0]))==row[1]==digest(response))
        runs.append(dict(name=name,status=response['status'],candidates=len(response['candidate_layouts']),selected=len(response['selected_ids']),evaluations=response['optimizer_evaluations'],optimizer_seconds=response['optimizer_seconds'],elapsed_seconds=response['elapsed_seconds']))
        if name=='wedding_EMPTY':
            bs=read(compiler_run/name/'BASELINE_SPEC.json');br=execute(r,bs,out/'STRONG_BASELINE_EMPTY');bv=validate_result(r,bs,br);save(out/'STRONG_BASELINE_EMPTY/INDEPENDENT_RESULT.json',bv)
            equal=br['status']=='success' and digest(br['candidate_layouts'])==digest(response['candidate_layouts'])
            check('ACTUAL_STRONG_BASELINE_EQUIVALENCE',equal and bv['valid'],dict(equal_returned_polygons=equal,baseline_evaluations=br['optimizer_evaluations']))
    for name in ['conference_EMPTY','concert_EMPTY','WEDDING_161_SPEC_ONLY','PENDING_PLANNER','UNCERTAIN_EXISTING','PROTECTED_REMOVAL']:
        r=read(compiler_run/name/'REQUEST.json');spec=read(compiler_run/name/'SPEC.json');res=execute(r,spec,out/('DENY_'+name));v=validate_result(r,spec,res)
        check(name+'_NO_UNSUPPORTED_OPTIMIZATION',res['status']!='success' and res['optimizer_evaluations']==0 and res['optimizer_calls']==0 and v['valid'],res.get('reason'))
    r=read(compiler_run/'wedding_EMPTY/REQUEST.json');spec=read(compiler_run/'wedding_EMPTY/SPEC.json');good=read(out/'wedding_EMPTY/RESULT.json')
    for name,mutate in [('FALSE_NUMERICAL_XAI',lambda x:x['xai']['explanations'][0]['metrics'].update(mean_stage_distance_m=0.)),('MISSING_FUNCTION_ZONE',lambda x:x['candidate_layouts'][0].update(zones=[])),('MOVED_PINNED_STAGE',lambda x:x['candidate_layouts'][0]['objects'][0]['footprint_coordinates_m'][0].__setitem__(0,100.))]:
        bad=copy.deepcopy(good);mutate(bad);v=validate_result(r,spec,bad);save(out/(name+'.json'),dict(poisoned_response=bad,verification=v));check(name+'_REJECTED',not v['valid'],v['errors'])
    tampered=copy.deepcopy(spec);tampered['required_quantities']['chair']=1;res=execute(r,tampered,out/'DENY_TAMPERED_SPEC');check('TAMPERED_SPEC_NO_SEARCH',res['status']=='rejected' and res['optimizer_calls']==0)
    save(out/'BRIDGE_ACCEPTANCE.json',dict(passed=all(x['passed'] for x in results),checks=results,runs=runs,no_superiority_claim=True))
    if not all(x['passed'] for x in results):raise SystemExit(1)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--compiler-run',required=True);a.add_argument('--out',required=True);args=a.parse_args();run(HERE/args.compiler_run,HERE/args.out)
