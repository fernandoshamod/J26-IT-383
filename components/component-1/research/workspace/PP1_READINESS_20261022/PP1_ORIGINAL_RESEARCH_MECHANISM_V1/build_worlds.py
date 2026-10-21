"""Actual frozen optimizer/qualification worlds; real predictions are anchors only."""
from lab import *
import copy,shutil,time,collections,tracemalloc,ctypes
events=guard();runtime,adapter=boot()
from repair import run
from independent import verify_envelope
before=read(P/'PP1_FINAL_BACKEND_FREEZE_V1/BACKEND_RUNTIME_FREEZE.json')['files']
assert all(sha(ROOT/k)==v for k,v in before.items())
save('PRESERVATION_BEFORE.json',before)
sources=[P/'PP1_REAL_INDOOR_ACCEPTANCE_V1/backend_003/PLAN_2/ANALYSIS.json',P/'PP1_FINAL_MODEL_INTEGRATION_V1/outputs/NATIVE_CLI_001/CANDIDATE_BUNDLE.json',P/'PP1_REAL_INDOOR_ACCEPTANCE_V1/backend_003/PLAN_3/ANALYSIS.json',P/'PP1_REAL_INDOOR_ACCEPTANCE_V1/backend_003/PLAN_1/ANALYSIS.json']
anchors=[]
for path in sources:
 d=read(path);b=d.get('candidate_bundle',d);objects=b['objects'];ops=[o for o in objects if o.get('model')=='YOLO' or o['id'].startswith('OPENING_YOLO')]
 assert len(ops)>=2 and not b['optimization_ready']
 anchors.append(dict(artifact=str(path),sha256=sha(path),source=b['source'],models=b['models'],unet_candidate=next(o for o in objects if o['id'].startswith('UNET')),opening_candidates=ops[:2],metric_transfer=False,ground_truth_used=False))
save('ACTUAL_PREDICTION_ANCHORS.json',anchors)
(H/'HTTP').mkdir();base=P/'PP1_FINAL_BACKEND_FREEZE_V1'
for n in ['TWIN_RECEIPT.json','research.sqlite3']:shutil.copyfile(base/'HTTP'/n,H/'HTTP'/n)
scene,binding=adapter.convert(read(H/'HTTP/TWIN_RECEIPT.json'),H/'HTTP/research.sqlite3',read(base/'SCENE_BRIEF.json'),H/'BASE_ADMISSION')
save('REGISTERED_BASE_BINDING.json',binding)
freeze={str(p.relative_to(ROOT)):sha(p) for p in list(H.glob('*.py'))+[H/'PROTOCOL.md']+sources}
save('PRE_EXECUTION_FREEZE.json',freeze)
trace=collections.Counter()
def profile(frame,event,arg):
 if event=='call' and frame.f_code.co_name in ['run','execute','minimize','validate_layout','qualify','compile_scene','validate_spec']:
  name=frame.f_code.co_filename
  if any(s in name for s in ['PP1_EXECUTABLE_V1','PP1_EVENT_SCENE_INTELLIGENCE_V1','PP1_EAG_APR_IMPLEMENTATION_V1','pymoo']):trace[(name,frame.f_code.co_name)]+=1
sys.setprofile(profile);tracemalloc.start();start=time.perf_counter();worlds=[]
cases=[('ENTRANCE_PARTITION',80),('REGION_OBSTACLE',80),('ACTIVITY_GUEST_CHANGE',96),('CONFLICT_PROTECTED_STAGE',112)]
for ci,(name,guests) in enumerate(cases):
 for a in [0,1]:
  for b in [0,1]:
   out=H/'worlds'/name/f'{a}{b}';r=copy.deepcopy(scene);r['venue']['version']+=ci*4+a*2+b+1
   r['client']['guest_count']=r['planner']['guest_count']=guests
   def obstacle(i,x,y,w,h):
    r['venue']['existing'].append(dict(instance_id=i,class_name='restricted_zone',footprint_m=runtime.fixtures.ring(x,y,w,h),status='fixed',review_status='approved',protected=True,candidate_ref='CONTROLLED_HYPOTHESIS_NOT_REAL_GEOMETRY'))
   if ci==0:
    if a:obstacle('hyp_corridor',0.,0.,32.,3.)
    if b:obstacle('hyp_partition',15.,6.,.5,10.)
   if ci==1:
    if a:r['venue']['boundary_m']=runtime.fixtures.ring(0.,5.,32.,19.);r['venue']['boundary_px']=[[x*10,y*10] for x,y in r['venue']['boundary_m']]
    if b:obstacle('hyp_obstacle',4.,8.,3.,3.)
   if ci==2:
    if a:r['client']['optional_functions']=r['planner']['optional_functions']=['dancing'];r['dance_zone_m']=runtime.fixtures.ring(26.,7.,4.,4.)
    if b:obstacle('hyp_obstacle',18.,7.,3.,3.)
   if ci==3:
    if a:obstacle('hyp_interpretation_a',7.,7.,2.,5.)
    if b:obstacle('hyp_interpretation_b',23.,8.,2.,5.)
   r=runtime.fixtures.seal(r,out/'EXPLICIT_SIMULATED_WORLD_REVIEW')
   c=dict(version=1,scope='SIMULATED_FIXTURE',scenario='CONTROLLED_OPERATIONAL_RESTRICTION',protected_object_ids=[o['instance_id'] for o in r['venue']['existing']],allowed_groups=[],new_supply_permitted=True,requested_group=None,object_moves=[],reference_sha256=None)
   packet=runtime.seal_packet(r,c,out/'SIMULATED_AUTHORITY')
   response,graph=run(packet,out/'ACTUAL_SEARCH','EAG',20261017)
   check=verify_envelope(packet,response);assert check['valid'],check
   item=dict(case=name,bits=[a,b],guests=guests,anchor_index=ci,input=str(out/'ACTUAL_SEARCH/INPUT.json'),result=str(out/'ACTUAL_SEARCH/RESULT.json'),status=response['status'],evaluations=response['optimizer_evaluations'],candidates=len(response['candidate_layouts']),result_sha256=sha(out/'ACTUAL_SEARCH/RESULT.json'))
   worlds.append(item);save(out/'WORLD_INDEX.json',item);print(name,a,b,item['status'],item['evaluations'],item['candidates'],flush=True)
sys.setprofile(None);current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
save('WORLD_INDEX.json',worlds)
save('EXECUTION.json',dict(seconds=time.perf_counter()-start,python_tracemalloc_peak_bytes=peak,guard=events,call_trace=[dict(path=k[0],function=k[1],calls=v) for k,v in trace.items()],preservation_match=all(sha(ROOT/k)==v for k,v in before.items()),actual_evaluations=sum(w['evaluations'] for w in worlds),searches=len(worlds),source_count=len(anchors),real_metric_venues=0,controlled_base_venues=1))
assert all(sha(ROOT/k)==v for k,v in before.items())
