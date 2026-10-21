"""Independent ordinary qualification/dispatch baseline, no repair.run/qualify calls.
Shared compiler/oracle/engines are deliberate controls. No new optimizer.
"""
import copy,time,sqlite3,json
from lab import *
import runtime
from independent import verify_candidate,verify_envelope
from optimizer_adapter import full,singleton

def qualify_standard(packet,spec,reference):
 r,c=packet['scene'],packet['context'];errors=[]
 if set(c)!={'version','scope','scenario','protected_object_ids','allowed_groups','new_supply_permitted','requested_group','object_moves','reference_sha256'}:errors.append('UNKNOWN_OR_MISSING_CONTEXT_FIELDS')
 try:
  path=Path(packet['authority']['path']).resolve();document=read(path)
  if not path.is_relative_to(ROOT) or sha(path)!=packet['authority']['sha256'] or document!={'scene_sha256':digest(r),'context':c,'scope':'SIMULATED_FIXTURE_NOT_AUTHENTICATED_AUTHORITY'}:errors.append('AUTHORITY_EVIDENCE_BINDING')
 except (OSError,KeyError,ValueError):errors.append('AUTHORITY_EVIDENCE_MISSING')
 if c['scope']!='SIMULATED_FIXTURE' or c['scenario'] not in ('CONTROLLED_NOMINAL','CONTROLLED_OPERATIONAL_RESTRICTION'):errors.append('CONTEXT_SCOPE_UNSUPPORTED')
 if type(c['version'])!=int or c['version']<1:errors.append('CONTEXT_VERSION_INVALID')
 for k in ['protected_object_ids','allowed_groups']:
  if len(c[k])!=len(set(c[k])):errors.append('DUPLICATE_CONTEXT_IDS')
 if reference is None:
  if c['reference_sha256'] is not None or c['requested_group'] or c['object_moves']:errors.append('REFERENCE_REQUIRED')
 else:
  layout=reference['layout'];objects={o['object_id']:o for o in layout['objects']}
  if digest(layout)!=c['reference_sha256']:errors.append('REFERENCE_HASH_MISMATCH')
  if not set(c['allowed_groups']).issubset(layout['group_centers_m']) or not set(c['protected_object_ids']).issubset(objects):errors.append('UNKNOWN_PERMISSION_OR_LOCK_ID')
  for m in c['object_moves']:
   candidates=[o for o in r['venue']['existing'] if o['instance_id']==m.get('object_id')]
   if not candidates or candidates[0]['protected'] or candidates[0]['status']=='fixed' or not m.get('approved') or m.get('actor_id')!=r['planner']['actor_id']:errors.append('PROTECTED_OR_UNAUTHORIZED_STOCK_MOVE')
   else:errors.append('OBSERVED_STOCK_RELOCATION_UNSUPPORTED')
  if r['client']['guest_count']>reference['request']['client']['guest_count'] and not c['new_supply_permitted']:errors.append('NEW_SUPPLY_PERMISSION_REQUIRED')
  target=c['requested_group']
  if target:
   if target not in c['allowed_groups']:errors.append('MOVE_PERMISSION_REQUIRED')
   if any(o['group_id']==target and oid in c['protected_object_ids'] for oid,o in objects.items()):errors.append('PROTECTED_GROUP_MOVE')
 if spec['status']!='accepted':return {'pending_review':'pending','unsupported':'unsupported'}.get(spec['status'],'refused'),errors+[i['code'] for i in spec['issues']]
 if errors:return ('unsupported' if all(x.endswith('UNSUPPORTED') for x in errors) else 'refused'),errors
 return 'qualified',[]

def ordinary_impact(old,new,full_check):
 changed={k for k,v in new['tokens'].items() if old.get('tokens',{}).get(k)!=v}
 reverse={}
 for n in new['nodes']:
  for d in n['fact_dependencies']+n['constraint_dependencies']:reverse.setdefault(d,[]).append(n['constraint_id'])
 queue=list(changed);dirty=set(n['constraint_id'] for n in new['nodes']) if full_check else set()
 while queue:
  for cid in reverse.get(queue.pop(),[]):
   if cid not in dirty:dirty.add(cid);queue.append(cid)
 return dict(directly_changed_dependencies=sorted(changed),affected_constraints=sorted(dirty),affected_object_variables=sorted({o for n in new['nodes'] if n['constraint_id'] in dirty for o in n['dependent_objects']}),qualification_nodes_evaluated=len(dirty),not_a_minimum_repair_set=True)

def ordinary_issue(packet,body):
 fingerprint=runtime.facts(packet)
 cert=dict(schema='EAG_CONTEXTUAL_VALIDITY_CERTIFICATE_V1',context_version=packet['context']['version'],venue_version=packet['scene']['venue']['version'],fingerprint=fingerprint,verified_evidence_dependencies=[dict(path=p,sha256=h) for p,h in fingerprint['artifacts'].items()],active_hard_constraints=body['spec']['hard'],protected_object_ids=packet['context']['protected_object_ids'],mandatory_functions=body['spec']['functions'],validation=body['validation'],status=body['status'],recommendation_ready=body['status']=='eligible' and bool(body['candidate_layouts']),result_payload_sha256=digest(body),reasons=body['reasons'],global_infeasibility_proven=False,regulatory_certification=False,authenticated_identity=False)
 cert['certificate_sha256']=digest(cert)
 claims=[dict(layout_id=l['layout_id'],layout_sha256=digest(l),constraint_ids=sorted(body['graph_constraint_ids']),counts=body['validation'][l['layout_id']]['geometry']['allocated_counts'],mean_stage_distance_m=l['objective_metrics']['mean_stage_distance_m'],initializer_assignment_movement_m=l['objective_metrics']['initializer_assignment_movement_m'],stable_group_relocation_m=body['validation'][l['layout_id']]['stable_group_relocation_m']) for l in body['candidate_layouts']]
 xai=dict(certificate_sha256=cert['certificate_sha256'],context_sha256=digest(packet['context']),request_sha256=digest(packet['scene']),evidence_ids=cert['verified_evidence_dependencies'],claims=claims,reasons=body['reasons'],weather_used=False,sgcn_used=False,causal_claim=False)
 return dict(body,certificate=cert,xai=xai)

def run_standard(packet,out,method,seed,reference,graph):
 out=Path(out);out.mkdir(parents=True,exist_ok=False);start=time.perf_counter();save(out/'INPUT.json',packet)
 spec=runtime.baseline.baseline_scene(packet['scene'],runtime.POLICY);save(out/'SPEC.json',spec)
 impact=ordinary_impact(reference['graph'],graph,method in ['B0','B1','B2','B4']);save(out/'IMPACT.json',impact);save(out/'GRAPH.json',graph)
 status,reasons=qualify_standard(packet,spec,reference);layouts=[];verified={};initial=reference['initial'];operation='REFUSE';evaluations=0;calls=0;seconds=0.;invalid=[];target=packet['context']['requested_group'];fallback=False;replay_seconds=0.
 if status=='qualified':
  if target and (digest(packet['scene'])!=digest(reference['request']) or spec['hard']!=reference['spec']['hard']):status='unsupported';reasons=['SINGLETON_CONTEXT_CHANGE_REQUIRES_UNSUPPORTED_REPAIR']
  # Frozen initial engine cannot enforce seating-identity locks or adaptive
  # target-only objective; do not weaken these for a full-search comparison.
  elif method=='B0' and (target or any(oid not in {o['instance_id'] for o in reference['request']['venue']['existing']} for oid in packet['context']['protected_object_ids'])):
   return dict(status='NOT_COMPARABLE',reason='FROZEN_FULL_ENGINE_LACKS_EQUIVALENT_SEATING_LOCK_OR_TARGET_OBJECTIVE',optimizer_evaluations=0,candidate_layouts=[]),graph
  if status=='qualified':
   if method!='B0' and (not target or method=='B1'):
    operation='REVALIDATE_EXISTING_POOL';t=time.perf_counter()
    for layout in reference['pool']:
     v=verify_candidate(packet,spec,layout,initial,reference)
     if v['valid']:layouts.append(copy.deepcopy(layout));verified[layout['layout_id']]=v
     else:invalid.append(dict(layout_id=layout['layout_id'],errors=v['errors']))
    replay_seconds+=time.perf_counter()-t
    if method=='B1' and target:status='NOT_COMPARABLE';reasons=['REUSE_CANNOT_EXECUTE_REQUESTED_MOVE']
   if status=='qualified' and (not layouts or target):
    if method=='B1':status='NO_VALID_REUSE';reasons=['REUSE_ONLY_NO_FEASIBLE_SAVED_CANDIDATE']
    else:
     operation='SELECTIVE_SINGLETON' if target else 'FULL_RECOMPUTATION';fallback=not target
     raw=singleton(packet['scene'],spec,out/'ACTUAL_SEARCH',seed,reference,target) if target else full(packet['scene'],spec,out/'ACTUAL_SEARCH',seed)
     evaluations=raw['evaluations'];calls=raw['optimizer_calls'];seconds=raw['seconds'];initial=raw['initial']
     if raw['status']!='success':status='infeasible' if raw['status']=='failed_search' else 'refused';reasons=[raw['reason']]
     else:
      t=time.perf_counter()
      for layout in raw['layouts']:
       v=verify_candidate(packet,spec,layout,initial,reference,target)
       if v['valid']:layouts.append(layout);verified[layout['layout_id']]=v
       else:invalid.append(dict(layout_id=layout['layout_id'],errors=v['errors']))
      replay_seconds+=time.perf_counter()-t
   if status=='qualified':status='eligible' if layouts else 'refused';reasons=['CURRENT_CONTEXT_AND_ALL_RETURNED_RECOMMENDATIONS_VERIFIED'] if layouts else ['NO_RETURNED_CANDIDATE_PASSES_FULL_AUTHORITY_AND_GEOMETRY_VALIDATION']
 if status!='eligible':layouts=[];verified={}
 if status in ['NOT_COMPARABLE','NO_VALID_REUSE']:
  result=dict(status=status,reasons=reasons,candidate_layouts=[],optimizer_evaluations=0,elapsed_seconds=time.perf_counter()-start,revalidation_seconds=replay_seconds,invalidated_previous_candidates=invalid);save(out/'RESULT.json',result);return result,graph
 fresh=runtime.baseline.baseline_scene(packet['scene'],runtime.POLICY)
 if status=='eligible' and (fresh['spec_sha256']!=spec['spec_sha256'] or qualify_standard(packet,fresh,reference)[0]!='qualified'):raise RuntimeError('BASELINE_INPUT_CHANGED')
 menu=runtime.bridge.menu(layouts);fingerprint=runtime.facts(packet)
 from certificates import is_current
 rr=[dict(code=r,constraint_id='EVIDENCE' if any(s in r for s in ['EVIDENCE','SOURCE','METRIC','REVIEW']) else 'PERMISSIONS' if any(s in r for s in ['PERMISSION','PROTECTED','REFERENCE','MOVE']) else 'FUNCTION_DEMAND' if any(s in r for s in ['CONFLICT','SUPPLY']) else 'GEOMETRY') for r in reasons]
 body=dict(schema='EAG_APR_RESULT_V1',method=method,status=status,spec=spec,candidate_layouts=layouts,selected_ids=menu['selected_ids'],menu=menu,validation=verified,graph_constraint_ids=[n['constraint_id'] for n in graph['nodes']],impact=impact,operation=operation,fallback=fallback,previous_certificate_stale=not is_current(packet,reference['certificate']),optimizer_evaluations=evaluations,optimizer_calls=calls,optimizer_seconds=seconds,elapsed_seconds=time.perf_counter()-start,invalidated_previous_candidates=invalid,initialization_centers_m=initial,reference_sha256=packet['context']['reference_sha256'],qualification_fingerprint=fingerprint,seed=seed,global_infeasibility_proven=False)
 response=ordinary_issue(packet,body);check=verify_envelope(packet,response,reference);assert check['valid'],check
 save(out/'RESULT.json',response);save(out/'INDEPENDENT_ENVELOPE.json',check);save(out/'REVALIDATION_TIMING.json',dict(seconds=replay_seconds,scope='Candidate validation only; final envelope replay adds further work'))
 with sqlite3.connect(out/'assurance.sqlite3') as db:db.execute('CREATE TABLE records(input_json TEXT,response_json TEXT,sha256 TEXT)');db.execute('INSERT INTO records VALUES(?,?,?)',(json.dumps(packet),json.dumps(response),digest(response)))
 return response,graph
