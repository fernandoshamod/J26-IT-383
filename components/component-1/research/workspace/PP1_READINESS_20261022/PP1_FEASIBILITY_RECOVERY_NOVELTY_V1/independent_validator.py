"""Raw readback validation; no import of recovery or its enumeration/screen/objectives."""
from io_context import *
import math,copy
from shapely.geometry import Polygon
sys.path.insert(0,str(PP1/'PP1_ORIGINAL_LAYOUT_RESEARCH_V1'))
from independent import validate as frozen_geometry_oracle

def validate(r,state,c,layout):
    issues=[];old=r['requested'];new=state['values'];changed={k for k in old if old[k]!=new[k]}
    core=r['core'];auth=core['authority'];ref=r['reference']
    raw=read(core['original_input_path'])
    if sha(core['source_path'])!=core['source_sha256'] or digest(raw)!=core['compiler_input_sha256']:issues.append('SOURCE_OR_REVIEW_EVIDENCE_CHANGED')
    if core['boundary']!=raw['venue']['boundary_m'] or core['metric_controls']!=raw['venue']['controls'] or core['review_status']!='approved' or len(core['metric_controls'])!=2:issues.append('METRIC_REVIEW_BINDING')
    if not auth.get('allow_design') or any(core[k].get('approved') is not True for k in ['client','planner']):issues.append('MISSING_DESIGN_AUTHORITY')
    if core['version']==2:
        permitted=set(core['table_ids'][1:]+core['chair_ids'][8:]+[core['stage_id']]+core['buffet_pool_ids'])
        if not ref or auth.get('reference_sha256')!=digest(ref) or auth.get('reference_case_sha256')!=ref['binding']['case_sha256'] or ref['binding']['version']!=core['version']-1 or auth.get('revoked') or auth.get('allow_revision') is not True or set(auth.get('permitted_move_ids',[]))!=permitted or auth.get('allow_function_change') is not True or auth.get('allow_allocation_change') is not True or set(auth.get('permitted_zone_ids',[]))!={'dance'}:issues.append('MISSING_STALE_OR_REVOKED_REVISION_PERMISSION')
    a=r['recovery_authority'];body={k:v for k,v in r.items() if k!='recovery_authority'}
    if a.get('request_sha256')!=digest(body) or a.get('revoked') is not False:issues.append('AUTHORITY_BINDING')
    if a.get('scope')!='SIMULATED_CONTROLLED_RESEARCH_NOT_HUMAN_CONSENT':issues.append('AUTHORITY_SCOPE')
    if changed&set(r['mandatory']):issues.append('MANDATORY_RELAXED')
    defs={o['id']:o for o in r['operations']};applied={};cost=0.
    for oid in state['operations']:
        if oid not in defs or oid not in a.get('permitted_operations',[]):issues.append('UNAUTHORIZED_OPERATION');continue
        op=defs[oid];cost+=op['cost']
        if op['from']!={k:old[k] for k in op['from']}:issues.append('PRECONDITION')
        for k,v in op['to'].items():
            if k in applied:issues.append('DUPLICATE_EDIT')
            applied[k]=v
    if set(applied)!=changed or any(new[k]!=v for k,v in applied.items()):issues.append('PARTIAL_OR_UNEXPLAINED_EDIT')
    if state['concession_cost']!=cost:issues.append('WRONG_CONCESSION_COST')
    if new['service_front_m']!=new['minimum_buffets']*2.5:issues.append('BROKEN_COUPLED_FUNCTION')
    if new['dance_area_m2']<16:issues.append('MISSING_MANDATORY_FUNCTION_FLOOR')
    expected=copy.deepcopy(r['core']);expected.update(dance_area_m2=new['dance_area_m2'],minimum_buffets=new['minimum_buffets'])
    binding={'request_sha256':digest(body),'state_sha256':digest(state),'required_service_front_m':new['service_front_m'],'authority_sha256':digest(a)}
    expected.update(recovery_binding=binding,recovery_stage_target=new['stage_target'],recovery_protected_stage=r['protected_stage'])
    if c!=expected:issues.append('UNDECLARED_CORE_MUTATION')
    check=frozen_geometry_oracle(c,layout,r['reference'])
    issues.extend(check['errors'])
    vector=layout['decision_vector'];stage_pose=vector[8:11]
    for pin in [r['protected_stage'],new['stage_target']]:
        if pin is not None and stage_pose!=pin:issues.append('PROTECTED_OR_REQUIRED_STAGE_CHANGED')
    counters=[o for o in layout['objects'] if o['class']=='buffet_counter']
    if len(counters)*2.5<new['service_front_m']:issues.append('SERVICE_FRONTAGE_SHORTFALL')
    if any(o['object_id'] not in c['available_buffet_ids'] for o in counters):issues.append('UNAVAILABLE_STOCK')
    loss=max(0.,old['dance_area_m2']-new['dance_area_m2'])/old['dance_area_m2']+max(0,old['minimum_buffets']-new['minimum_buffets'])/old['minimum_buffets']
    return {'valid':not issues,'errors':sorted(set(issues)),'function_complete':check['function_complete'] and not issues,'hard_violations':len(set(issues)),'protected_violations':check['protected_violations']+int('PROTECTED_OR_REQUIRED_STAGE_CHANGED' in issues),'concession_cost':cost,'functional_loss':loss,'recovery_objectives':[loss,cost,check['recomputed_objectives'][1],check['recomputed_objectives'][0]],'geometry_oracle':check}

def prove_screen(r,state,reported):
    v=state['values'];c=r['core'];area=Polygon(c['boundary']).area
    from shapely.geometry import box
    true=[]
    if v['dance_area_m2']>area:true.append('DANCE_AREA_EXCEEDS_ENTIRE_VENUE_AREA')
    if len(c['available_buffet_ids'])<v['minimum_buffets']:true.append('STOCK_COUNT_BELOW_REQUIRED_COUNT')
    if v['stage_target'] is not None:
        x,y,o=v['stage_target'];w,h=(8.,2.5) if o==0 else (2.5,8.)
        if not Polygon(c['boundary']).covers(box(x-w/2,y-h/2,x+w/2,y+h/2)):true.append('REQUIRED_STAGE_FOOTPRINT_OUTSIDE_VENUE')
    if r['protected_stage'] is not None and v['stage_target'] is not None and r['protected_stage']!=v['stage_target']:true.append('REQUIRED_STAGE_CONFLICTS_WITH_PROTECTED_POSE')
    return bool(reported) and set(reported)<=set(true)
