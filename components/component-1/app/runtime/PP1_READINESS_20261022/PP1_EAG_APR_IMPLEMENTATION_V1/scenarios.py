"""Controlled fixtures and independently specified expected statuses.
No genuine approval, weather or historical preference claim.
"""
import copy
from runtime import *

EXPECTED={'unchanged':'eligible','source_version_updated':'eligible','planner_lock_added':'eligible','unauthorized_stage_relocation':'refused','guest_count_increased':'eligible','mandatory_dance_added':'eligible','authorized_observed_stock_move':'unsupported','usable_zone_reduced':'eligible','missing_metric_verification':'pending','client_planner_conflict':'refused','insufficient_area':'infeasible','multiple_dependent_changes':'eligible','authorized_singleton_repair':'eligible'}

def initial(out,width,height):
    r=fixtures.fixture(out/'SCENE',guests=80,partial=True,width=width,height=height)
    r['venue']['existing'][2].update(status='movable',protected=False)
    r=fixtures.seal(r,out/'EXPLICIT_SIMULATED_STOCK_REVIEW')
    c=dict(version=1,scope='SIMULATED_FIXTURE',scenario='CONTROLLED_NOMINAL',protected_object_ids=['existing_stage','existing_buffet_1'],allowed_groups=[],new_supply_permitted=True,requested_group=None,object_moves=[],reference_sha256=None)
    return seal_packet(r,c,out)

def change(name,base,reference,out):
    r=copy.deepcopy(base['scene']);c=copy.deepcopy(base['context']);c['reference_sha256']=digest(reference['layout']);c['allowed_groups']=sorted(reference['layout']['group_centers_m']);c['version']+=1
    if name=='source_version_updated':r['venue']['version']+=1
    elif name=='planner_lock_added':c['protected_object_ids'].append(next(o['object_id'] for o in reference['layout']['objects'] if o['class']=='chair'))
    elif name=='unauthorized_stage_relocation':c['object_moves']=[dict(object_id='existing_stage',approved=False,actor_id='SIMULATED_CLIENT')]
    elif name=='guest_count_increased':r['client']['guest_count']=r['planner']['guest_count']=88
    elif name=='mandatory_dance_added':
        r['client']['optional_functions']=r['planner']['optional_functions']=['dancing'];r['dance_zone_m']=fixtures.ring(26.,1.,4.,4.)
    elif name=='authorized_observed_stock_move':c['object_moves']=[dict(object_id='existing_buffet_2',approved=True,actor_id=r['planner']['actor_id'])]
    elif name in ['usable_zone_reduced','insufficient_area','multiple_dependent_changes']:
        c['scenario']='CONTROLLED_OPERATIONAL_RESTRICTION';bottom=r['venue']['source']['height_px']/10.-5. if name=='insufficient_area' else 6.
        r['venue']['boundary_m']=fixtures.ring(0.,bottom,32.,24.-bottom) if r['venue']['source']['width_px']==320 else fixtures.ring(0.,bottom,36.,28.-bottom)
        r['venue']['boundary_px']=[[x*10,y*10] for x,y in r['venue']['boundary_m']]
        r['venue']['version']+=1
        if name=='multiple_dependent_changes':
            r['client']['guest_count']=r['planner']['guest_count']=88;r['client']['optional_functions']=r['planner']['optional_functions']=['dancing'];r['dance_zone_m']=fixtures.ring(26.,7.,4.,4.)
    elif name=='missing_metric_verification':r['venue']['review']['status']='pending'
    elif name=='client_planner_conflict':r['planner']['guest_count']=88
    elif name=='authorized_singleton_repair':c['requested_group']=sorted(reference['layout']['group_centers_m'])[0]
    elif name=='unchanged':
        # Exact current context of the original initial result: no newly supplied approval.
        return copy.deepcopy(base)
    if name not in ['source_version_updated'] and name not in EXPECTED:raise ValueError('UNKNOWN_SCENARIO')
    # A move permission alone does not change the reviewed scene or role brief.
    # Reissuing its evidence paths would falsely look like a scene change to the
    # deliberately strict singleton eligibility gate.
    if name!='authorized_singleton_repair':r=fixtures.seal(r,out/'EXPLICIT_SIMULATED_CHANGED_REVIEW')
    return seal_packet(r,c,out)
