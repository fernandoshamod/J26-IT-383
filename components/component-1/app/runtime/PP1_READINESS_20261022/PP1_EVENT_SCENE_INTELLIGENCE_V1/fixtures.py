"""Controlled generator inputs and explicit simulated role/review evidence only."""
import copy,math
from PIL import Image,ImageDraw
from shapely.geometry import box
from common import *
from models import Request,Venue,Party,venue_payload,party_payload,planner_payload

def ring(x,y,w,h):return [list(p) for p in box(x,y,x+w,y+h).exterior.coords]
def stub():return dict(path='PENDING',sha256='0'*64,source_sha256='0'*64)
def seal(raw,out):
    raw=copy.deepcopy(raw);source=raw['venue']['source']['sha256'];r=Request.model_validate(raw)
    for name,payload in [('venue',venue_payload(r.venue)),('client',party_payload(r.client)),('planner',planner_payload(r))]:
        path=out/(name+'_SIMULATED_RECORD.json');save(path,dict(scope='SIMULATED_FIXTURE_NOT_GENUINE_REVIEW_OR_CONSENT',source_sha256=source,payload_sha256=digest(payload)))
        e=dict(path=str(path.resolve()),sha256=filehash(path),source_sha256=source)
        if name=='venue':raw['venue']['review']['evidence']=e
        else:raw[name]['evidence']=e
    return Request.model_validate(raw).model_dump()

def fixture(out,event='wedding',guests=160,partial=False,width=32,height=24,optional=None):
    out.mkdir(parents=True,exist_ok=True);image=out/'CONTROLLED_SOURCE.png';im=Image.new('RGB',(width*10,height*10),'white');draw=ImageDraw.Draw(im)
    templates=[('existing_stage','stage',ring(width/2-4,height-3.5,8.,2.5)),('existing_buffet_1','buffet_counter',ring(2.,height-3,2.5,1.2)),('existing_buffet_2','buffet_counter',ring(width-5.,height-3,2.5,1.2))]
    existing=[];actions=[]
    if partial:
        for iid,cls,poly in templates:
            draw.polygon([(x*10,y*10) for x,y in poly],fill='gray');existing.append(dict(instance_id=iid,class_name=cls,footprint_m=poly,status='fixed',review_status='approved',protected=True,candidate_ref='CONTROLLED_GENERATOR:'+iid))
            actions.append(dict(instance_id=iid,action='reuse',approved=True,actor_id='SIMULATED_PLANNER',scope='SIMULATED_FIXTURE'))
    im.save(image);sha=filehash(image)
    v=dict(venue_id=out.name,version=1,source=dict(path=str(image.resolve()),sha256=sha,width_px=width*10,height_px=height*10,domain='controlled_synthetic',origin='CONTROLLED_GENERATOR'),boundary_px=ring(0.,0.,float(width*10),float(height*10)),origin_px=[0.,0.],controls=[dict(a_px=[0.,0.],b_px=[float(width*10),0.],distance_m=float(width)),dict(a_px=[0.,0.],b_px=[0.,float(height*10)],distance_m=float(height))],boundary_m=ring(0.,0.,float(width),float(height)),existing=existing,review=dict(status='approved',reviewer_id='SIMULATED_GENERATOR_REVIEW',scope='SIMULATED_FIXTURE',evidence=stub()))
    party=dict(actor_id='SIMULATED_CLIENT',scope='SIMULATED_FIXTURE',approval_status='approved',policy_sha256=digest(read(HERE/'profiles.json')),event_type=event,guest_count=guests,optional_functions=optional or [],hard=dict(minimum_clearance_m=.5,maximum_mean_stage_distance_m=None,maximum_assignment_movement_m=None),evidence=stub());client=dict(party,role='client');planner=dict(copy.deepcopy(party),role='planner',actor_id='SIMULATED_PLANNER')
    counts={'wedding':{'stage':1,'buffet_counter':math.ceil(guests/80)},'birthday':{'cake_table':1},'anniversary':{'cake_table':1},'corporate':{'stage':1,'lectern':1,'screen':1},'conference':{'stage':1,'lectern':1,'screen':1},'concert':{'stage':1,'speaker':2},'musical_show':{'stage':1,'speaker':2}}[event].copy()
    for f in optional or []:
        if f=='buffet':counts['buffet_counter']=math.ceil(guests/80)
        if f=='presentation':counts['stage']=1
        if f=='networking':counts['standing_table']=math.ceil(guests/10)
    policy=read(HERE/'profiles.json');placements=[];index=0
    for cls,n in sorted(counts.items()):
        need=max(0,n-sum(o['class_name']==cls for o in existing))
        for k in range(1,need+1):
            cat=policy['catalog'][cls]
            if cls=='stage':poly=templates[0][2]
            elif cls=='buffet_counter' and k<=2:poly=templates[k][2]
            else:poly=ring(2.+(index%8)*3.,2.+(index//8)*3.,cat['width_m'],cat['depth_m']);index+=1
            placements.append(dict(class_name=cls,ordinal=k,footprint_m=poly))
    raw=dict(schema_id='EVENT_SCENE_INPUT_V1',event_id='EV_'+out.name,venue=v,client=client,planner=planner,actions=actions,placements=placements,dance_zone_m=ring(width-6.,1.,4.,4.) if 'dancing' in (optional or []) else None)
    return seal(raw,out)
