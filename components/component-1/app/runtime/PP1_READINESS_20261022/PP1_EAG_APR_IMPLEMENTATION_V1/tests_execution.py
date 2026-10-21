"""Independent/adversarial tests on actual saved and newly executed outputs.
No writes to preserved experiment inputs; all corruptions use fresh local files.
"""
import argparse,copy,ast
from runtime import *
import repair
from independent import verify_envelope,verify_candidate
from certificates import is_current,issue

def main(out):
    out.mkdir(parents=True,exist_ok=False);base=HERE/'outputs/EXPERIMENT_FINAL/VENUE_32_24_SEED_20261017';packet=read(base/'unchanged/INPUT.json');first=read(base/'INITIAL/EAG/RESULT.json');ref=repair.make_reference(read(base/'INITIAL/EAG/INPUT.json')['scene'],first,read(base/'INITIAL/EAG/GRAPH.json'),base/'INITIAL/EAG');approval=read(base/'COMMON_APPROVAL/EAG/RESULT.json');ref.update(certificate=approval['certificate'],graph=read(base/'COMMON_APPROVAL/EAG/GRAPH.json'),pool=approval['candidate_layouts']);checks=[]
    good=read(base/'unchanged/EAG/RESULT.json')
    def check(name,ok,detail=None):checks.append(dict(name=name,passed=bool(ok),detail=detail));print(name,bool(ok),flush=True)
    check('ACTUAL_CONTEXT_CERTIFICATE_CURRENT',is_current(packet,good['certificate']))
    check('ACTUAL_RESPONSE_FULL_REPLAY',verify_envelope(packet,good,ref)['valid'])
    altered=copy.deepcopy(packet);altered['context']['version']+=1;check('CONTEXT_CHANGE_INVALIDATES_CERTIFICATE',not is_current(altered,good['certificate']))
    altered=copy.deepcopy(packet);altered['context']['allowed_groups']=[];check('PERMISSION_CHANGE_INVALIDATES_CERTIFICATE',not is_current(altered,good['certificate']))
    altered=copy.deepcopy(packet);altered['scene']['venue']['version']+=1;check('SOURCE_VERSION_INVALIDATES_CERTIFICATE',not is_current(altered,good['certificate']))
    poisoned=copy.deepcopy(good);poisoned['xai']['claims'][0]['mean_stage_distance_m']+=1.;v=verify_envelope(packet,poisoned,ref);save(out/'WRONG_XAI_REPLAY.json',v);check('WRONG_NUMERICAL_XAI_REJECTED',not v['valid'] and 'XAI_FIDELITY' in v['errors'])
    # Reissuing a self-consistent unsigned certificate cannot make bad geometry valid.
    body=copy.deepcopy({k:v for k,v in good.items() if k not in ['certificate','xai']});body['candidate_layouts'][0]['objects'][0]['footprint_coordinates_m'][0][0]+=.15;poisoned=issue(packet,body);v=verify_envelope(packet,poisoned,ref);save(out/'SELF_HASHED_POISON_GEOMETRY_REPLAY.json',v);check('SELF_CONSISTENT_FALSE_VALIDATION_REJECTED',not v['valid'] and 'RAW_REPLAY_DISAGREES_WITH_CLAIMED_VALIDATION' in v['errors'])
    geometry=copy.deepcopy(good['candidate_layouts'][0]);geometry['objects'][0]['footprint_coordinates_m'][0][0]+=.2;v=verify_candidate(packet,good['spec'],geometry,good['initialization_centers_m'],ref);check('PROTECTED_POLYGON_CHANGE_REJECTED','PROTECTED_OBJECT_CHANGED' in v['errors'])
    context=copy.deepcopy(packet['context']);context['requested_group']=sorted(ref['layout']['group_centers_m'])[0];context['allowed_groups']=[];denied=seal_packet(packet['scene'],context,out/'NO_MOVE_PERMISSION');r,g=repair.run(denied,out/'DENIED_EXECUTION','EAG',20261017,ref);check('MISSING_MOVE_PERMISSION_ZERO_SEARCH',r['status']=='refused' and r['optimizer_evaluations']==0 and not r['candidate_layouts'])
    # Deliberately delete dependency propagation in memory. Full independent
    # function/geometry replay must catch the old pool and trigger real fallback.
    dance=read(base/'mandatory_dance_added/INPUT.json');real_impact=repair.impact
    try:
        repair.impact=lambda old,new,mode:dict(directly_changed_dependencies=[],affected_constraints=[],affected_object_variables=[],qualification_nodes_evaluated=0,fault_injected=True)
        r,g=repair.run(dance,out/'FAULT_INJECTED_GRAPH_REAL_FALLBACK','EAG',20261017,ref)
    finally:repair.impact=real_impact
    check('MISSED_DEPENDENCY_DETECTED_BY_FULL_REPLAY',r['fallback'] and len(r['invalidated_previous_candidates'])==len(ref['pool']) and r['optimizer_evaluations']==1200 and r['status']=='eligible',dict(invalidated=r['invalidated_previous_candidates'],actual_evaluations=r['optimizer_evaluations']))
    # Evidence changes between verified output and final write are not accepted.
    local=seal_packet(packet['scene'],copy.deepcopy(packet['context']),out/'RACE_LOCAL_EVIDENCE');real_issue=repair.issue;intercepted=False
    try:
        def changed_after_issue(p,b):
            result=real_issue(p,b);path=Path(p['authority']['path']);before=path.read_bytes();save(out/'RACE_ORIGINAL_RECORD.json',read(path));path.write_bytes(before+b'\nCONTROLLED_REVOKED');return result
        repair.issue=changed_after_issue
        try:repair.run(local,out/'RACE_EXECUTION','EAG',20261017,ref)
        except RuntimeError as e:intercepted=str(e)=='EVIDENCE_CHANGED_DURING_CERTIFICATE_ISSUANCE';save(out/'RACE_FAILURE.json',dict(error=str(e),expected=True))
    finally:repair.issue=real_issue
    check('REVOKED_EVIDENCE_CANNOT_YIELD_SAVED_SUCCESS',intercepted and not (out/'RACE_EXECUTION/RESULT.json').exists())
    for n in [1,2]:
        m=bridge.menu(good['candidate_layouts'][:n]);check('NO_PADDED_'+str(n)+'_MENU',len(m['selected_ids'])<=n)
    duplicated=[copy.deepcopy(good['candidate_layouts'][0]) for _ in range(3)]
    for i,l in enumerate(duplicated):l['layout_id']='DUPLICATE_'+str(i)
    check('DUPLICATE_GEOMETRY_NOT_THREE_CHOICES',len(bridge.menu(duplicated)['selected_ids'])==1)
    singleton=read(base/'authorized_singleton_repair/EAG/RESULT.json');check('ACTUAL_SINGLETON_HAS_MOVED_OPTION',any(v['moved_object_count']>0 for v in singleton['validation'].values()) and singleton['optimizer_evaluations']==1680)
    graph=read(base/'mandatory_dance_added/EAG/GRAPH.json');required={'constraint_id','constraint_version','evidence_ids','source_version','verification_status','responsible_authorities','dependent_objects','dependent_functions','scenario','classification','qualification_status'};check('ALL_GRAPH_NODES_EVIDENCE_AUTHORITY_TYPED',all(required<=set(n) for n in graph['nodes']))
    for p in HERE.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
    check('ALL_SOURCE_SYNTAX',True)
    save(out/'TEST_RESULTS.json',dict(passed=all(c['passed'] for c in checks),checks=checks,skipped=0,scope='Controlled/adversarial records; not human approval or full research coverage'))
    if not all(c['passed'] for c in checks):raise SystemExit(1)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',default='outputs/TESTS_FINAL');a=p.parse_args();out=(HERE/a.out).resolve()
    if not out.is_relative_to(HERE):raise ValueError('ISOLATION')
    main(out)
