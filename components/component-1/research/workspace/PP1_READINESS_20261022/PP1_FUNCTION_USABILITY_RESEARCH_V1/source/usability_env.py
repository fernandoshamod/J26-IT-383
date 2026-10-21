from io_lab import *
FLAGS,EVENTS=offline()
RUN_NAME=os.environ.get('USABILITY_RUN_NAME')
if RUN_NAME:
    import re
    assert re.fullmatch('[A-Za-z0-9_]+',RUN_NAME),'INVALID_REPEAT_NAME'
    H=H/'repeats'/RUN_NAME;H.mkdir(parents=True,exist_ok=True)
import time,copy,math,sqlite3
import numpy as np
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union
sys.path.insert(0,str(PP1/'PP1_ORIGINAL_LAYOUT_RESEARCH_V1'))
import joint_core as jc
# The legacy import sets a historical plotting cache; restore our output-only configuration.
os.environ['MPLCONFIGDIR']=FLAGS['MPLCONFIGDIR']
sys.path.insert(0,str(PP1/'PP1_FINAL_PANEL_RESOLUTION_V1/07_PROTOTYPE_AND_SOURCE'))
from typed_qualification import composed
RADIUS=.3
ORIGIN=(1.,1.)
STEP=.25
METHODS=['B0','B1','B2','NEW','ABLATION']

def preserve_before():
    old=PP1/'PP1_FINAL_PANEL_RESOLUTION_V1'
    pins=read(old/'PRESERVATION_BEFORE.json')
    for folder in [old,PP1/'PP1_ORIGINAL_LAYOUT_RESEARCH_V1']:
        for p in folder.glob('*.json'):pins[str(p.relative_to(ROOT))]=sha(p)
        for p in folder.glob('*.md'):pins[str(p.relative_to(ROOT))]=sha(p)
        for p in folder.glob('*.py'):pins[str(p.relative_to(ROOT))]=sha(p)
    for p in (old/'07_PROTOTYPE_AND_SOURCE').glob('*.*'):
        pins[str(p.relative_to(ROOT))]=sha(p)
    master=next(ROOT.glob('Component 1 *Updated Full Research.txt'))
    pins[str(master.relative_to(ROOT))]=sha(master)
    mismatches=[p for p,h in pins.items() if sha(ROOT/p)!=h]
    assert not mismatches,mismatches
    if (H/'PRESERVATION_BEFORE.json').exists():
        assert read(H/'PRESERVATION_BEFORE.json')==pins
    else:save(H/'PRESERVATION_BEFORE.json',pins)
    return pins

def physical_and_goals(x,c):
    x,u,stage,sa,bf,ba,dance,active=jc.geometry(x,c)
    # Deliberately conservative seating envelopes, not a human-body/individual-chair model.
    physical=[Point(*x[2*i:2*i+2]).buffer(1.72,quad_segs=32) for i in range(4)]
    physical += [stage]+[bf[k] for k in active]+[Polygon(o['polygon']) for o in c['fixed']]
    goals=[('seating',i,(float(x[2*i]),float(x[2*i+1]-2.12))) for i in range(4)]
    goals += [('stage',4,tuple(sa.centroid.coords[0]))]
    goals += [('buffet',5+k,tuple(ba[k].centroid.coords[0])) for k in active]
    goals += [('dance',7,tuple(dance.centroid.coords[0]))]
    return physical,goals

def access_fitness(x,c):
    physical,goals=physical_and_goals(x,c)
    free=Polygon(c['boundary']).buffer(-RADIUS).difference(unary_union([p.buffer(RADIUS,quad_segs=16) for p in physical]))
    regions=list(free.geoms) if hasattr(free,'geoms') else [free]
    origin=Point(ORIGIN)
    component=next((q for q in regions if q.covers(origin)),None)
    fails=[dict(function=f,block=b,goal=list(g)) for f,b,g in goals if component is None or not component.covers(Point(g))]
    return fails,free

def revision(c,reference):
    d=copy.deepcopy(c);d['version']=2;d['dance_area_m2']=25.;d['minimum_buffets']=2
    d['locked_group_0']=reference['group_centers_m']['seating_group_0001']
    d['authority'].update(allow_revision=True,reference_sha256=digest(reference),reference_case_sha256=reference['binding']['case_sha256'],revoked=False,allow_function_change=True,allow_allocation_change=True,permitted_move_ids=d['table_ids'][1:]+d['chair_ids'][8:]+[d['stage_id']]+d['buffet_pool_ids'],permitted_zone_ids=['dance'],protected_group='seating_group_0001')
    return d
