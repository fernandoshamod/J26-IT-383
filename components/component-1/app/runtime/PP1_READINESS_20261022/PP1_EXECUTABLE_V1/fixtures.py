"""Explicit synthetic calibration/review fixtures, never real review evidence."""
from pathlib import Path
from PIL import Image,ImageDraw
from support import ROOT,digest,filehash,read
def controlled_registration(out,width=32,height=24,venue_id='CONTROLLED_32X24',version=1):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);source=out/(venue_id+f'_v{version}.png');old=read(ROOT/'PP1_STAGE_E_RESEARCH_CORE/outputs/f2b_test_request_v1.json')['venue_twin'];fixed=old['fixed_obstacles']
    im=Image.new('RGB',(width*10,height*10),'white');draw=ImageDraw.Draw(im)
    for ob in fixed:draw.polygon([(x*10,y*10) for x,y in ob['footprint_coordinates_m']],fill='gray')
    im.save(source);meta=dict(path=str(source.resolve()),sha256=filehash(source),width_pixels=width*10,height_pixels=height*10,domain='controlled_synthetic')
    bundle=dict(schema='IMAGE_SPACE_TWIN_CANDIDATE_V2',source=meta,objects=[{'id':o['object_id'],'source_kind':'CONTROLLED_GENERATOR_GEOMETRY_NOT_MODEL_PREDICTION'} for o in fixed],planner_reviewed=False,optimization_ready=False)
    review=dict(contract_id='COMPONENT1_REVIEWED_TWIN_V1',venue_id=venue_id,venue_version=version,source=meta,candidate_bundle_sha256=digest(bundle),calibration={'method':'isotropic_two_point_controls','controls':[{'point_a_px':[0.,0.],'point_b_px':[float(width*10),0.],'known_distance_m':float(width),'evidence_ref':'CONTROLLED_GENERATOR_HORIZONTAL_DIMENSION'},{'point_a_px':[0.,0.],'point_b_px':[0.,float(height*10)],'known_distance_m':float(height),'evidence_ref':'CONTROLLED_GENERATOR_VERTICAL_DIMENSION'}],'metric_origin_px':[0.,0.]},boundary_px=[[float(x*10),float(y*10)] for x,y in [[0,0],[width,0],[width,height],[0,height],[0,0]]],objects=[dict(object_id=o['object_id'],class_name=o['class'],status='fixed',polygon_px=[[float(x*10),float(y*10)] for x,y in o['footprint_coordinates_m']],candidate_refs=[o['object_id']],decision_evidence_ref='CONTROLLED_SYNTHETIC_TEST_DECISION_NOT_REAL_REVIEW') for o in fixed],review={'status':'approved','reviewer_id':'SIMULATED_FIXTURE_REVIEWER','evidence_ref':'EXPLICIT_SYNTHETIC_CALIBRATION_FIXTURE_TEST','scope':'SIMULATED_FIXTURE_REVIEW','geometry_confirmed':True,'metric_dimensions_confirmed':True})
    return dict(review=review,candidate_bundle=bundle)
def optimization(twin,guests=160,seed=20261016):
    party={'requirement_id':'CLIENT_TEST_REQUIREMENTS','provenance_ref':'CONTROLLED_SYNTHETIC_TEST_INPUT','approval_status':'approved','guest_count':guests,'quantities':{'round_table':guests//8,'chair':guests},'hard':{'minimum_clearance_m':.5},'alternative_preference':'stage_proximity'}
    import copy
    planner=copy.deepcopy(party);planner['requirement_id']='PLANNER_TEST_REQUIREMENTS'
    return dict(contract_id='COMPONENT1_PP1_EXECUTABLE_V1',mode='initial_design',venue_id=twin['venue_id'],venue_version=twin['venue_version'],twin_sha256=twin['twin_sha256'],requirements={'event_id':'CONTROLLED_EVENT_001','event_type':'Wedding','guest_count':guests,'seats_per_table':8,'quantities':{'round_table':guests//8,'chair':guests},'client':party,'planner':planner,'protected_group_ids':[],'protected_object_ids':[]},seed=seed)
def approval(response,version=1,layout_id=None):
    layout=next(l for l in response['candidate_layouts'] if l['layout_id']==(layout_id or response['selected_layout_id']))
    return dict(layout_id=layout['layout_id'],layout_sha256=digest(layout),venue_version=version,reviewer_id='SIMULATED_FIXTURE_REVIEWER',evidence_ref='EXPLICIT_SIMULATED_LAYOUT_APPROVAL_FOR_TEST',scope='SIMULATED_FIXTURE_REVIEW')
def revise(initial,approved,request,target='seating_group_0013'):
    import copy
    result=copy.deepcopy(request);selected=approval(initial);result.update(mode='adaptive_revision',reference={'run_id':initial['run_id'],'layout_id':selected['layout_id'],'layout_sha256':selected['layout_sha256'],'approval_id':approved['approval_id']},affected_group_ids=[target],permissions=[{'group_id':target,'action':'move','approved':True,'reviewer_id':'SIMULATED_FIXTURE_REVIEWER','reason':'Explicit simulated controlled revision','scope':'SIMULATED_FIXTURE_REVIEW'}]);return result
