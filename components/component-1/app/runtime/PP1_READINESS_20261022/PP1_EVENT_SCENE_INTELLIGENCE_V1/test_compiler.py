"""Compiler/oracle gates execute before any optimizer bridge is attempted."""
import argparse,copy,time
from common import *
from fixtures import fixture,seal
from compiler import compile_scene
from baseline import baseline_scene
from oracle import validate_spec
from models import Request

def canonical(spec):return {k:v for k,v in spec.items() if k not in ['method','spec_sha256']}
def run(out):
    out.mkdir(parents=True,exist_ok=False);save(out/'PRESERVATION_BEFORE.json',immutable_snapshot());p=read(HERE/'profiles.json');results=[];cases=[]
    def evaluate(name,r,status='accepted',counts=None,reason=None,policy=None):
        dest=out/name;dest.mkdir();policy=p if policy is None else policy;save(dest/'REQUEST.json',r);save(dest/'POLICY.json',policy)
        start=time.perf_counter();a=compile_scene(r,policy);seconds=time.perf_counter()-start
        t=time.perf_counter();b=baseline_scene(r,policy);bt=time.perf_counter()-t
        o=validate_spec(r,a,policy,status,counts);bo=validate_spec(r,b,policy,status,counts)
        checks=dict(oracle=o['valid'],baseline_oracle=bo['valid'],baseline_semantic_equivalence=digest(canonical(a))==digest(canonical(b)),expected_reason=reason is None or reason in [x['code'] for x in a['issues']])
        rec=dict(name=name,passed=all(checks.values()),checks=checks,expected_status=status,status=a['status'],compiler_seconds=seconds,baseline_seconds=bt,compiler_issues=a['issues'],oracle_errors=o['errors'],baseline_oracle_errors=bo['errors'])
        save(dest/'SPEC.json',a);save(dest/'BASELINE_SPEC.json',b);save(dest/'INDEPENDENT_ORACLE.json',o);results.append(rec);cases.append(dict(name=name,expected_status=status,expected_counts=counts,expected_reason=reason));print(name,a['status'],rec['passed'],flush=True);return a
    families=[('wedding',{'round_table':20,'chair':160,'stage':1,'buffet_counter':2}),('birthday',{'round_table':20,'chair':160,'cake_table':1}),('anniversary',{'round_table':20,'chair':160,'cake_table':1}),('corporate',{'chair':160,'stage':1,'lectern':1,'screen':1}),('conference',{'chair':160,'stage':1,'lectern':1,'screen':1}),('musical_show',{'chair':160,'stage':1,'speaker':2}),('concert',{'chair':160,'stage':1,'speaker':2})]
    for event,expected in families:
        r=fixture(out/('input_'+event),event=event);evaluate(event+'_EMPTY',r,counts=expected)
    r=fixture(out/'input_wedding_partial',partial=True);evaluate('WEDDING_PARTIAL',r,counts=families[0][1])
    r=fixture(out/'input_wedding_dancing',optional=['dancing']);evaluate('WEDDING_DANCING',r,counts=families[0][1])
    r=fixture(out/'input_wedding_120',guests=120);evaluate('WEDDING_120',r,counts={'round_table':15,'chair':120,'stage':1,'buffet_counter':2})
    r=fixture(out/'input_wedding_161',guests=161);evaluate('WEDDING_161_SPEC_ONLY',r,counts={'round_table':21,'chair':161,'stage':1,'buffet_counter':3})
    r=fixture(out/'input_networking',event='conference',guests=80,optional=['networking']);evaluate('CONFERENCE_NETWORKING',r,counts={'chair':80,'stage':1,'lectern':1,'screen':1,'standing_table':8})
    base=fixture(out/'input_base',partial=True)
    def mutate(name,fn,status,reason):
        r=copy.deepcopy(base);fn(r);r=seal(r,out/('input_'+name));evaluate(name,r,status=status,reason=reason)
    mutate('PENDING_PLANNER',lambda r:r['planner'].update(approval_status='pending'),'pending_review','PARTY_APPROVAL_REQUIRED')
    mutate('PENDING_VENUE',lambda r:r['venue']['review'].update(status='pending'),'pending_review','VENUE_REVIEW_REQUIRED')
    mutate('UNCERTAIN_EXISTING',lambda r:r['venue']['existing'][0].update(status='uncertain'),'pending_review','OBJECT_REVIEW_REQUIRED')
    mutate('UNREVIEWED_EXISTING',lambda r:r['venue']['existing'][0].update(review_status='pending'),'pending_review','OBJECT_REVIEW_REQUIRED')
    mutate('ROLE_CONFLICT',lambda r:r['planner'].update(guest_count=120),'conflict','CLIENT_PLANNER_GUEST_COUNT_CONFLICT')
    mutate('FUNCTION_CONFLICT',lambda r:r['planner'].update(optional_functions=['dancing']),'conflict','CLIENT_PLANNER_OPTIONAL_FUNCTIONS_CONFLICT')
    mutate('PROTECTED_REMOVAL',lambda r:r['actions'].append(dict(r['actions'][0],action='remove')),'conflict','PROTECTED_OR_FIXED_ACTION')
    mutate('DUPLICATE_PERMISSION',lambda r:r['actions'].append(copy.deepcopy(r['actions'][0])),'conflict','DUPLICATE_ACTION')
    mutate('UNAUTHORIZED_ACTOR',lambda r:r['actions'][0].update(actor_id='NOT_PLANNER'),'conflict','ACTION_AUTHORITY_MISMATCH')
    def missinguse(r):r['actions']=[]
    mutate('MISSING_REUSE_AND_DESIGN',missinguse,'pending_review','NEW_EQUIPMENT_PLACEMENT_REQUIRED')
    mutate('EXISTING_RELOCATION',lambda r:(r['venue']['existing'][0].update(status='movable',protected=False),r['actions'].append(dict(r['actions'][0],action='move'))),'unsupported','EXISTING_RELOCATION_UNSUPPORTED')
    mutate('UNKNOWN_ACTION',lambda r:r['actions'].append(dict(r['actions'][0],instance_id='unknown')),'conflict','UNKNOWN_ACTION_OBJECT')
    mutate('UNKNOWN_FUNCTION',lambda r:(r['client'].update(optional_functions=['weather']),r['planner'].update(optional_functions=['weather'])),'unsupported','FUNCTION_NOT_SUPPORTED_BY_PROFILE')
    mutate('METRIC_MISMATCH',lambda r:r['venue'].update(boundary_m=[[0.,0.],[31.,0.],[31.,24.],[0.,24.],[0.,0.]]),'rejected','METRIC_BOUNDARY_MISMATCH')
    mutate('EXISTING_CLASS_MISMATCH',lambda r:r['venue']['existing'][0].update(class_name='cake_table'),'conflict','REUSE_CATALOG_INCOMPATIBLE')
    mutate('SOURCE_HASH_MISMATCH',lambda r:r['venue']['source'].update(sha256='f'*64),'rejected','SOURCE_HASH_OR_PATH_MISMATCH')
    mutate('UNAPPROVED_POLICY_VERSION',lambda r:r['planner'].update(policy_sha256='0'*64),'rejected','POLICY_APPROVAL_BINDING_MISMATCH')
    mutate('DUPLICATE_EXISTING_ID',lambda r:r['venue']['existing'][1].update(instance_id=r['venue']['existing'][0]['instance_id']),'rejected','DUPLICATE_EXISTING_ID')
    mutate('MOVABLE_REUSE_IN_PLACE',lambda r:r['venue']['existing'][0].update(status='movable',protected=False),'accepted',None)
    mutate('STRICTER_HARD_CONSTRAINTS',lambda r:r['planner']['hard'].update(minimum_clearance_m=.7,maximum_mean_stage_distance_m=18.,maximum_assignment_movement_m=10.),'accepted',None)
    r=fixture(out/'input_remove_excess',partial=True,guests=80)
    iid=r['venue']['existing'][2]['instance_id'];r['venue']['existing'][2].update(status='movable',protected=False);r['actions']=[a for a in r['actions'] if a['instance_id']!=iid];r['actions'].append(dict(instance_id=iid,action='remove',approved=True,actor_id=r['planner']['actor_id'],scope='SIMULATED_FIXTURE'))
    r=seal(r,out/'input_remove_excess_sealed');evaluate('PERMITTED_EXCESS_REMOVAL',r,counts={'round_table':10,'chair':80,'stage':1,'buffet_counter':1})
    r=fixture(out/'input_missing_dance',optional=['dancing']);r['dance_zone_m']=None;r=seal(r,out/'input_missing_dance_sealed');evaluate('MISSING_DANCE_CONTROL',r,'pending_review',reason='DANCE_ZONE_REQUIRED')
    r=fixture(out/'input_blocked_access');r['placements'][1]['footprint_m']=copy.deepcopy(r['placements'][0]['footprint_m']);r=seal(r,out/'input_blocked_access_sealed');evaluate('OVERLAPPING_DESIGN_EQUIPMENT',r,'conflict',reason='DESIGN_OBJECT_OVERLAP')
    # Deliberately keep old hashed records while changing decision metadata.
    stale=copy.deepcopy(base);stale['venue']['review']['reviewer_id']='ALTERED_WITHOUT_EVIDENCE';evaluate('REVIEW_DECISION_NOT_BOUND',stale,'rejected',reason='EVIDENCE_PAYLOAD_MISMATCH')
    stale=copy.deepcopy(base);stale['actions'][0]['approved']=False;evaluate('PERMISSION_RECORD_NOT_BOUND',stale,'rejected',reason='EVIDENCE_PAYLOAD_MISMATCH')
    r=fixture(out/'input_custom_policy',guests=160)
    custom=copy.deepcopy(p);custom['version']='1.0.1_CONTROLLED_TEST';custom['functions']['buffet']['objects'][0]['divisor']=160
    for role in ['client','planner']:r[role]['policy_sha256']=digest(custom)
    r['placements']=[x for x in r['placements'] if x['class_name']!='buffet_counter' or x['ordinal']==1];r=seal(r,out/'input_custom_sealed')
    evaluate('CUSTOM_POLICY_BUFFET',r,counts={'round_table':20,'chair':160,'stage':1,'buffet_counter':1},policy=custom)
    # A profile can activate another supported function without changing compiler code.
    r=fixture(out/'input_custom_profile',event='birthday',guests=80,optional=['buffet'])
    custom=copy.deepcopy(p);custom['version']='1.0.2_PROFILE_TEST';custom['profiles']['celebration']['required_functions'].append('buffet');custom['profiles']['celebration']['optional_functions'].remove('buffet')
    for role in ['client','planner']:r[role]['optional_functions']=[];r[role]['policy_sha256']=digest(custom)
    r=seal(r,out/'input_custom_profile_sealed');evaluate('CUSTOM_PROFILE_FUNCTION',r,counts={'round_table':10,'chair':80,'cake_table':1,'buffet_counter':1},policy=custom)
    good=compile_scene(base,p)
    for name,poison in [('DOUBLE_ALLOCATION',lambda s:s['allocations'].append(copy.deepcopy(s['allocations'][0]))),('MISSING_FUNCTION',lambda s:s['functions'].remove('buffet')),('MISSING_ZONE',lambda s:s.update(zones=[])),('UNBOUND_SOURCE',lambda s:s['binding'].update(source_sha256='0'*64)),('MISNAMED_POLICY_ZONE',lambda s:s['zones'][0].update(kind='UNCONFIGURED_ZONE')),('DISPLACED_ACCESS_ZONE',lambda s:s['zones'][0].update(footprint_m=[[0.,0.],[2.,0.],[2.,1.],[0.,1.],[0.,0.]]))]:
        bad=copy.deepcopy(good);poison(bad);bad['spec_sha256']=digest({k:v for k,v in bad.items() if k!='spec_sha256'});v=validate_spec(base,bad,p)
        results.append(dict(name='ORACLE_POISON_'+name,passed=not v['valid'],detail=v));save(out/('POISON_'+name+'.json'),bad)
    schema=Request.model_json_schema();save(out/'INPUT_SCHEMA.json',schema);save(out/'CASE_ORACLE_EXPECTATIONS.json',cases)
    result=dict(passed=all(x['passed'] for x in results),results=results,case_count=len(cases),baseline_equivalent=sum(x.get('checks',{}).get('baseline_semantic_equivalence',False) for x in results),no_optimizer_invoked=True)
    save(out/'COMPILER_ACCEPTANCE.json',result)
    if not result['passed']:raise SystemExit(1)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--out',required=True);args=a.parse_args();out=(HERE/args.out).resolve()
    if not out.is_relative_to(HERE):raise ValueError('ISOLATION')
    run(out)
