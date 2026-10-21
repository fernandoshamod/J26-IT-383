"""Conventional finite-domain grouped constraint relaxation. No new algorithm claim."""
from io_context import *
import copy,itertools,math
from shapely.geometry import Polygon,box

FIELDS={'dance_area_m2','minimum_buffets','service_front_m','stage_target'}
def request_hash(r):return digest({k:v for k,v in r.items() if k!='recovery_authority'})
def check_request(r):
    if set(r)!={'schema','case_id','core','reference','requested','domains','operations','mandatory','protected_stage','recovery_authority'}:raise ValueError('REQUEST_FIELDS')
    if r['schema']!='CONTROLLED_RECOVERY_V1':raise ValueError('UNSUPPORTED_SCHEMA')
    if set(r['requested'])!=FIELDS or set(r['domains'])!=FIELDS:raise ValueError('UNSUPPORTED_REQUIREMENT_FIELD')
    core=r['core']
    if core['client']['guests']!=32 or core['planner']['guests']!=32 or len(core['table_ids'])!=4 or len(core['chair_ids'])!=32:raise ValueError('UNSUPPORTED_GUEST_OR_FURNITURE_QUANTITY')
    if set(core['required_functions'])!={'dining','presentation','buffet','dancing'}:raise ValueError('UNSUPPORTED_FUNCTION_SET')
    if not set(r['mandatory'])<=FIELDS:raise ValueError('UNSUPPORTED_MANDATORY_FIELD')
    for values in r['domains'].values():
        if not isinstance(values,list) or not values:raise ValueError('EMPTY_OR_INVALID_DOMAIN')
    for k in ['dance_area_m2','minimum_buffets','service_front_m']:
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in r['domains'][k]):raise ValueError('INVALID_NUMERIC_DOMAIN')
    for pin in r['domains']['stage_target']+[r['protected_stage']]:
        if pin is not None and (not isinstance(pin,list) or len(pin)!=3 or any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in pin) or pin[2] not in [0,1]):raise ValueError('INVALID_STAGE_POSE')
    a=r['recovery_authority']
    if a.get('scope')!='SIMULATED_CONTROLLED_RESEARCH_NOT_HUMAN_CONSENT' or a.get('request_sha256')!=request_hash(r) or a.get('revoked') is not False:raise ValueError('STALE_REVOKED_OR_MISSING_RECOVERY_AUTHORITY')
    for op in r['operations']:
        if set(op)!={'id','from','to','cost','function','reason'} or set(op['from'])!=set(op['to']) or not set(op['to'])<=FIELDS:raise ValueError('OPERATION_SCHEMA')
        if not math.isfinite(op['cost']) or op['cost']<0:raise ValueError('INVALID_COST')
        if any(r['requested'][k]!=v for k,v in op['from'].items()):raise ValueError('OPERATION_PRECONDITION')
    if len({o['id'] for o in r['operations']})!=len(r['operations']):raise ValueError('DUPLICATE_OPERATION_ID')
    if not set(a.get('permitted_operations',[]))<={o['id'] for o in r['operations']}:raise ValueError('EXCESS_PERMISSION')
    for k,values in r['domains'].items():
        if r['requested'][k] not in values:raise ValueError('REQUEST_OUTSIDE_DOMAIN')
    if r['core']['scope']!='CONTROLLED_EXPLORATORY_SIMULATED_AUTHORITY':raise ValueError('EXTERNAL_INPUT_UNSUPPORTED')
    return True

def configuration_errors(r,v,ops):
    errors=[];by={o['id']:o for o in r['operations']};a=r['recovery_authority']
    if any(o not in a['permitted_operations'] for o in ops):errors.append('MISSING_CONCESSION_PERMISSION')
    changed={k for k in FIELDS if v[k]!=r['requested'][k]}
    if changed&set(r['mandatory']):errors.append('MANDATORY_REQUIREMENT_CHANGE')
    target=copy.deepcopy(r['requested']);written=set()
    for oid in ops:
        op=by[oid]
        if written&set(op['to']):errors.append('OVERLAPPING_CONCESSION')
        written.update(op['to']);target.update(op['to'])
    if target!=v:errors.append('UNEXPLAINED_OR_PARTIAL_CONCESSION')
    # A service configuration is a coupled count/frontage contract, not independent field discounts.
    if v['minimum_buffets'] not in [1,2] or v['service_front_m']!=2.5*v['minimum_buffets']:errors.append('BROKEN_SERVICE_FUNCTION_DEPENDENCY')
    if not isinstance(v['dance_area_m2'],(int,float)) or not math.isfinite(v['dance_area_m2']) or v['dance_area_m2']<16:errors.append('MANDATORY_DANCE_FUNCTION_FLOOR')
    if any(v[k] not in r['domains'][k] for k in FIELDS):errors.append('OUTSIDE_DECLARED_DOMAIN')
    return sorted(set(errors))

def enumerate_grouped(r,ignore_authority=False,split_bundles=False):
    """Enumerate atomic concession bundles; conventional grouped relaxation."""
    check_request(r);out=[];bad=[]
    ops=r['operations']
    if split_bundles:
        ops=[dict(o,id=o['id']+'__'+k,**{'from':{k:o['from'][k]},'to':{k:o['to'][k]}}) for o in ops for k in o['to']]
    for mask in itertools.product([False,True],repeat=len(ops)):
        picked=[o for o,on in zip(ops,mask) if on];v=copy.deepcopy(r['requested'])
        for o in picked:v.update(o['to'])
        ids=[o['id'] for o in picked]
        if split_bundles:
            # Deliberately diagnostic only: split edits never reach the real optimizer.
            full=[o['id'] for o in r['operations'] if all(v[k]==val for k,val in o['to'].items()) and all(k in {k2 for q in picked for k2 in q['to']} for k in o['to'])]
            err=configuration_errors(r,v,full)
        else:err=configuration_errors(r,v,ids)
        if ignore_authority:err=[e for e in err if e not in ['MISSING_CONCESSION_PERMISSION','MANDATORY_REQUIREMENT_CHANGE']]
        rec={'values':v,'operations':ids,'concession_cost':sum(o['cost'] for o in picked)}
        (bad if err else out).append(dict(rec,errors=err) if err else rec)
    unique={digest(x['values']):x for x in out}
    return sorted(unique.values(),key=lambda x:(x['concession_cost'],digest(x['values']))),bad

def screen(r,state):
    """Only simple sound impossibility witnesses; never infer unsat from failed search."""
    v=state['values'];c=r['core'];area=Polygon(c['boundary']).area
    if v['dance_area_m2']>area:return ['DANCE_AREA_EXCEEDS_ENTIRE_VENUE_AREA']
    if len(c['available_buffet_ids'])<v['minimum_buffets']:return ['STOCK_COUNT_BELOW_REQUIRED_COUNT']
    if v['stage_target'] is not None:
        x,y,o=v['stage_target'];w,h=(8.,2.5) if o==0 else (2.5,8.)
        if not Polygon(c['boundary']).covers(box(x-w/2,y-h/2,x+w/2,y+h/2)):return ['REQUIRED_STAGE_FOOTPRINT_OUTSIDE_VENUE']
    if r['protected_stage'] is not None and v['stage_target'] is not None and v['stage_target']!=r['protected_stage']:return ['REQUIRED_STAGE_CONFLICTS_WITH_PROTECTED_POSE']
    return []

_ENGINE=None
def engine():
    global _ENGINE
    if _ENGINE is None:
        sys.path.insert(0,str(PP1/'PP1_ORIGINAL_LAYOUT_RESEARCH_V1'))
        import joint_core as jc
        _ENGINE=jc
    return _ENGINE

def solve_state(r,state,seed,budget):
    jc=engine();c=copy.deepcopy(r['core']);v=state['values']
    c.update(dance_area_m2=v['dance_area_m2'],minimum_buffets=v['minimum_buffets'])
    c['recovery_binding']={'request_sha256':request_hash(r),'state_sha256':digest(state),'required_service_front_m':v['service_front_m'],'authority_sha256':digest(r['recovery_authority'])}
    c['recovery_stage_target']=v['stage_target'];c['recovery_protected_stage']=r['protected_stage']
    # Conventional frozen-variable adapter, output-only memory binding; frozen files unchanged.
    original=jc.canonical
    def frozen_variables(x,case):
        x=original(x,case)
        pin=case.get('recovery_protected_stage') or case.get('recovery_stage_target')
        if pin is not None:x[8:11]=pin
        return x
    jc.canonical=frozen_variables
    try:result=jc.solve(c,'B1',seed,reference=r['reference'],budget=budget)
    finally:jc.canonical=original
    return c,result

def functional_loss(r,v):
    old=r['requested']
    return max(0.,old['dance_area_m2']-v['dance_area_m2'])/old['dance_area_m2']+max(0,old['minimum_buffets']-v['minimum_buffets'])/old['minimum_buffets']

def nondominated(records):
    return [r for r in records if not any(all(a<=b+1e-10 for a,b in zip(q['recovery_objectives'],r['recovery_objectives'])) and any(a<b-1e-10 for a,b in zip(q['recovery_objectives'],r['recovery_objectives'])) for q in records)]
