"""Fresh registered-controlled-Twin matched benchmark; no old output writes."""
from lab import *
import copy,csv,shutil,time,sqlite3,importlib.metadata,collections
events=guard();runtime,adapter=boot()
from repair import run as eag_run,make_reference
from constraint_graph import build
from scenarios import change
from independent import verify_candidate,verify_envelope
from conventional import run_standard
METHODS=['B0','B1','B2','B3','B4','EAG'];SEEDS=[20261017,20261018];GUESTS=[80,96]
EXPECTED={'unchanged':'eligible','source_version_updated':'eligible','planner_lock_added':'eligible','unauthorized_stage_relocation':'refused','guest_count_increased':'eligible','mandatory_dance_added':'eligible','authorized_observed_stock_move':'refused','usable_zone_reduced':'eligible','missing_metric_verification':'pending','client_planner_conflict':'refused','insufficient_area':'infeasible','multiple_dependent_changes':'eligible','authorized_singleton_repair':'eligible','guest_count_decreased':'refused','stale_reference_hash':'refused','tampered_authority':'refused','revoked_adapter_authority':'refused','changed_protected_obstacle':'refused'}
config=dict(methods=METHODS,seeds=SEEDS,guest_counts=GUESTS,venue='SAME_REGISTERED_CONTROLLED_32x24m_TWIN',expectations=EXPECTED,initial_budget=1200,singleton_budget=1680,initial_population=48,initial_generations=25,adaptive_population=48,adaptive_generations=35,objectives='Same initial stage/initializer-assignment objectives for full searches; same target-stage/stable-target-displacement objectives for singleton. No cross-objective pooled quality claim.',B0_exclusions=['singleton target-objective changes','protected seating identities unsupported by frozen full engine'],B1_scope='Reuse only; no new-layout search. NO_VALID_REUSE/NOT_COMPARABLE are capability limits, not successful repair or broad false-refusal evidence.',independence='B4 independently coded qualification/dispatch/certificate issuer; shared conventional compiler, original graph schema, actual engines, geometry verifier and numeric libraries. Not an external laboratory replication.',factorial_units=4,case_types=18,outcomes=432,labels='Pre-authored controlled synthetic expected outcomes, no genuine human authority',no_significance_claim=True,registered_twin_successors='Initial scene comes through registered HTTP adapter. Changed Scene review/versions are explicitly simulated sealed successors, not new HTTP registrations.',unsupported_multigroup='Multiple event-dependent changes may use full fallback; simultaneous selective multigroup execution NOT_IMPLEMENTED',revocation='Existing adapter.verify_scene state-revocation gate uniformly precedes all six strategies; not a newly invented EAG feature')
save('EXPERIMENT_CONFIGURATION.json',config)
files=read(P/'PP1_FINAL_BACKEND_FREEZE_V1/BACKEND_RUNTIME_FREEZE.json')['files'];before={k:sha(ROOT/k) for k in files};assert before==files
for base in [P/'PP1_MASTER_ORGANIZATION_V1',P/'PP1_SAFE_PROJECT_CLEANUP_V1']:
 for n in ['README.md','FINAL_PRESERVATION_CHECK.json','AUTHORITATIVE_HASH_CATALOG.json']:
  if (base/n).is_file():before[str((base/n).relative_to(ROOT))]=sha(base/n)
save('PRESERVATION_BEFORE.json',before)
protocol_sources={str(p.relative_to(ROOT)):sha(p) for p in list(H.glob('*.py'))+[P/'PP1_EAG_APR_IMPLEMENTATION_V1'/n for n in ['repair.py','authority.py','certificates.py','independent.py','optimizer_adapter.py','constraint_graph.py','runtime.py','scenarios.py']]+[P/'PP1_EVENT_SCENE_INTELLIGENCE_V1'/n for n in ['compiler.py','baseline.py','core.py','models.py','oracle.py','profiles.json']]}
save('PROTOCOL_SOURCE_FREEZE.json',protocol_sources)
(H/'HTTP').mkdir();base=P/'PP1_FINAL_BACKEND_FREEZE_V1'
for n in ['TWIN_RECEIPT.json','research.sqlite3']:shutil.copyfile(base/'HTTP'/n,H/'HTTP'/n)
receipt=read(H/'HTTP/TWIN_RECEIPT.json');brief=read(base/'SCENE_BRIEF.json')
scene,binding=adapter.convert(receipt,H/'HTTP/research.sqlite3',brief,H/'BASE_ADMISSION')
save('REGISTERED_BASE_BINDING.json',binding)
units=[]
for guests in GUESTS:
 for seed in SEEDS:
  unit=f'GUESTS_{guests}_SEED_{seed}';folder=H/'inputs'/unit;r=copy.deepcopy(scene)
  if guests!=80:r['client']['guest_count']=r['planner']['guest_count']=guests;r=runtime.fixtures.seal(r,folder/'SIMULATED_DEMAND_REVIEW')
  c=dict(version=1,scope='SIMULATED_FIXTURE',scenario='CONTROLLED_NOMINAL',protected_object_ids=[o['instance_id'] for o in r['venue']['existing']],allowed_groups=[],new_supply_permitted=True,requested_group=None,object_moves=[],reference_sha256=None)
  packet=runtime.seal_packet(r,c,folder/'INITIAL_INPUT')
  initial,graph=eag_run(packet,H/'setup'/unit/'INITIAL','EAG',seed);assert initial['status']=='eligible'
  reference=make_reference(r,initial,graph,H/'setup'/unit/'INITIAL')
  c=copy.deepcopy(c);c.update(version=2,reference_sha256=digest(reference['layout']),allowed_groups=sorted(reference['layout']['group_centers_m']))
  approved=runtime.seal_packet(r,c,folder/'SIMULATED_LAYOUT_APPROVAL');approval,graph=eag_run(approved,H/'setup'/unit/'APPROVAL','EAG',seed,reference);assert approval['status']=='eligible' and approval['optimizer_evaluations']==0
  reference.update(certificate=approval['certificate'],pool=approval['candidate_layouts'],graph=graph)
  save(folder/'REFERENCE.json',reference);cases=[]
  for name,expected in EXPECTED.items():
   where=folder/name
   if name in ['guest_count_decreased','stale_reference_hash','tampered_authority','revoked_adapter_authority','changed_protected_obstacle']:
    rr=copy.deepcopy(approved['scene']);cc=copy.deepcopy(approved['context']);cc['version']+=1
    if name=='guest_count_decreased':rr['client']['guest_count']=rr['planner']['guest_count']=guests-8;rr=runtime.fixtures.seal(rr,where/'SIMULATED_CHANGED_REVIEW')
    if name=='stale_reference_hash':cc['reference_sha256']='0'*64
    if name=='changed_protected_obstacle':
     for xy in rr['venue']['existing'][2]['footprint_m']:xy[0]-=3.
     rr=runtime.fixtures.seal(rr,where/'SIMULATED_CHANGED_REVIEW')
    q=runtime.seal_packet(rr,cc,where/'CONTROLLED_AUTHORITY')
    if name=='tampered_authority':q['authority']['sha256']='0'*64
   else:
    q=change(name,approved,reference,where/'CONTROLLED_INPUT')
    if name in ['guest_count_increased','multiple_dependent_changes'] and guests!=80:
     q['scene']['client']['guest_count']=q['scene']['planner']['guest_count']=guests+8
     rr=runtime.fixtures.seal(q['scene'],where/'SIMULATED_DEMAND_CORRECTION');q=runtime.seal_packet(rr,q['context'],where/'SIMULATED_AUTHORITY_CORRECTION')
   save(where/'INPUT.json',q);cases.append(dict(case=name,input=str(where/'INPUT.json'),input_sha256=sha(where/'INPUT.json'),expected=expected))
  units.append(dict(unit=unit,guests=guests,seed=seed,reference=str(folder/'REFERENCE.json'),reference_sha256=sha(folder/'REFERENCE.json'),cases=cases))
  print('Frozen unit',unit,flush=True)
save('FROZEN_BENCHMARK_MANIFEST.json',dict(frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),protocol_sha256=sha(H/'EXPERIMENT_CONFIGURATION.json'),source_freeze_sha256=sha(H/'PROTOCOL_SOURCE_FREEZE.json'),registered_twin_sha256=receipt['twin_sha256'],registered_db_copy_sha256=sha(H/'HTTP/research.sqlite3'),simulated=True,units=units,setup_evaluations=4800,setup_not_comparative=True,scenario_inference_not_model_based=True))
records=[];failures=[];calltrace=collections.Counter()
def profile(frame,event,arg):
 if event=='call' and frame.f_code.co_name in ['run','execute','minimize','validate_layout','validate_spec']:
  filename=frame.f_code.co_filename
  if any(x in filename for x in ['PP1_EXECUTABLE_V1','PP1_EVENT_SCENE_INTELLIGENCE_V1','pymoo']):calltrace[(filename,frame.f_code.co_name)]+=1
sys.setprofile(profile)
for u in units:
 reference=read(u['reference']);seed=u['seed']
 for case in u['cases']:
  packet=read(case['input']);assert sha(case['input'])==case['input_sha256'];responses={}
  graph=build(packet,runtime.compiler.compile_scene(packet['scene'],runtime.POLICY))
  # Balanced rotation reduces fixed-order bias; still one-run timings, not speed proof.
  offset=(list(EXPECTED).index(case['case'])+SEEDS.index(seed))%6;order=METHODS[offset:]+METHODS[:offset]
  for method in order:
   out=H/'raw'/u['unit']/case['case']/method;t=time.perf_counter()
   if case['case']=='revoked_adapter_authority':
    out.mkdir(parents=True);state=out/'AUTHORITY_STATE.json';save(state,dict(status='revoked',twin_sha256=receipt['twin_sha256'],scope='SIMULATED_FIXTURE'));b=copy.deepcopy(binding);b['authority_state_path']=str(state)
    try:adapter.verify_scene(packet,b);raise AssertionError('REVOKED_ADAPTER_ACCEPTED')
    except adapter.AdmissionError as e:
     assert str(e)=='ADAPTER_AUTHORITY_REVOKED_OR_MISMATCH';response=dict(status='refused',reason=str(e),candidate_layouts=[],optimizer_evaluations=0,operation='REGISTERED_ADAPTER_REFUSAL');save(out/'INPUT.json',packet);save(out/'RESULT.json',response)
   elif method=='EAG':response,_=eag_run(packet,out,'EAG',seed,reference)
   else:
    response,_=run_standard(packet,out,method,seed,reference,graph)
    if not (out/'RESULT.json').exists():save(out/'RESULT.json',response)
   wall=time.perf_counter()-t;status=response['status'];comparable=status not in ['NOT_COMPARABLE','NO_VALID_REUSE'];expected=case['expected']
   validations=response.get('validation',{});layouts=response.get('candidate_layouts',[])
   fullcheck=verify_envelope(packet,response,reference) if 'certificate' in response else None
   if fullcheck is not None:assert fullcheck['valid'],fullcheck
   if comparable and status!=expected:failures.append(dict(unit=u['unit'],case=case['case'],method=method,expected=expected,actual=status))
   rec=dict(unit=u['unit'],seed=seed,guests=u['guests'],case=case['case'],method=method,method_order=order.index(method),status=status,expected=expected,comparable=comparable,false_accept=status=='eligible' and expected!='eligible',false_refusal=comparable and status!='eligible' and expected=='eligible',operation=response.get('operation'),evaluations=response['optimizer_evaluations'],optimizer_calls=response.get('optimizer_calls',0),optimizer_seconds=response.get('optimizer_seconds',0.),wall_seconds=wall,revalidation_seconds=read(out/'REVALIDATION_TIMING.json')['seconds'] if (out/'REVALIDATION_TIMING.json').exists() else None,candidates=len(layouts),material_alternatives=len(response.get('selected_ids',[])),protected_changes=sum(len(v['protected_changes']) for v in validations.values()),geometry_failures=sum(not v['valid'] for v in validations.values()),function_omissions=sum(v['geometry']['allocated_counts']!=response['spec']['required_quantities'] for v in validations.values()),envelope_valid=fullcheck['valid'] if fullcheck else None,pool_sha256=digest(layouts),response_path=str(out/'RESULT.json'),response_sha256=sha(out/'RESULT.json'),metrics=[dict(layout_id=l['layout_id'],stage=l['objective_metrics']['mean_stage_distance_m'],initializer_assignment=l['objective_metrics']['initializer_assignment_movement_m'],search=l.get('search_objectives',l['objective_metrics']),moved_objects=validations[l['layout_id']]['moved_object_count'],group_relocation_m=validations[l['layout_id']]['stable_group_relocation_m'],individual_relocation_m=validations[l['layout_id']]['stable_individual_relocation_m']) for l in layouts])
   records.append(rec);responses[method]=response
  save(Path('raw')/u['unit']/case['case']/'CASE_INDEX.json',[r for r in records if r['unit']==u['unit'] and r['case']==case['case']])
  print(u['unit'],case['case'],{k:(v['status'],v['optimizer_evaluations']) for k,v in responses.items()},flush=True)
sys.setprofile(None)
save('RAW_EXPERIMENT_RESULTS.json',records)
with (H/'RAW_EXPERIMENT_RESULTS.csv').open('x',encoding='utf-8-sig',newline='') as f:
 keys=list(records[0]);w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows([{k:json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in records])
save('EXECUTION_RESULTS.json',dict(status='PASS' if not failures else 'EXPECTATION_FAILURE',failures=failures,records=len(records),scenario_instances=len(units)*len(EXPECTED),search_evaluations=sum(r['evaluations'] for r in records),setup_evaluations=4800,guard=events,trace=[dict(source=k[0],function=k[1],calls=v) for k,v in calltrace.items()],environment=dict(python=sys.version,packages={n:importlib.metadata.version(n) for n in ['numpy','scipy','shapely','pymoo','pydantic']},seeds=SEEDS),preservation_match=all(sha(ROOT/k)==v for k,v in before.items())))
assert all(sha(ROOT/k)==v for k,v in before.items())
print('Experiment outcomes',len(records),'expectation failures',len(failures),flush=True)
if failures:raise SystemExit(1)
