from lab import *
import copy,math,time,csv,sqlite3,collections,itertools,tracemalloc
events=guard();runtime,adapter=boot()
from independent import verify_envelope
from policies import *
import numpy as np
from scipy.optimize import linear_sum_assignment
from shapely.geometry import Polygon

def geometry_digest(layout):return digest({k:layout[k] for k in ['objects','group_centers_m']})

def transplant(decision,world):
 """Preserve actual returned seating polygons; substitute reviewed world statics."""
 spec=world['response']['spec'];r=world['packet']['scene'];l=copy.deepcopy(decision)
 l['objects']=[o for o in l['objects'] if o['group_id']]+[dict(object_id=o['instance_id'],**{'class':o['class']},group_id=None,footprint_coordinates_m=o['footprint_m']) for o in spec['retained_existing']+spec['new_equipment'] if o['footprint_m'] is not None]
 l['zones']=spec['zones'];stage=Polygon(next(o['footprint_coordinates_m'] for o in l['objects'] if o['class']=='stage')).centroid
 mean=sum(math.dist(x,[stage.x,stage.y]) for x in l['group_centers_m'].values())/len(l['group_centers_m'])
 aa=np.array(list(world['response']['initialization_centers_m'].values()));bb=np.array([l['group_centers_m'][g] for g in sorted(l['group_centers_m'])]);cost=np.linalg.norm(aa[:,None,:]-bb[None,:,:],axis=2);rr,cc=linear_sum_assignment(cost)
 l['objective_metrics']=dict(mean_stage_distance_m=mean,initializer_assignment_movement_m=float(cost[rr,cc].sum()))
 return l

save('POLICY_CODE_FREEZE.json',{str(p.relative_to(ROOT)):sha(p) for p in [H/'policies.py',H/'evaluate_policies.py',H/'PROTOCOL.md']})
start=time.perf_counter();tracemalloc.start();cases=collections.defaultdict(list)
for index in read(H/'WORLD_INDEX.json'):
 response=read(index['result']);packet=read(index['input']);assert sha(index['result'])==index['result_sha256']
 assert verify_envelope(packet,response)['valid']
 cases[index['case']].append(dict(index=index,response=response,packet=packet))
rows=[];matrices=[]
for case,worlds in cases.items():
 decisions=[];seen=set()
 for w in worlds:
  for l in w['response']['candidate_layouts']:
   sig=digest(l['group_centers_m'])
   if sig not in seen:seen.add(sig);decisions.append(l)
 assert decisions,'NO_AVAILABLE_SEARCH_CANDIDATES'
 # Decision zero is abstention, not a fabricated layout.
 valid={};checks=[]
 for w in worlds:
  key=tuple(w['index']['bits']);valid[key]=[]
  for d,l in enumerate(decisions,1):
   x=transplant(l,w);v=runtime.oracle.validate_layout(w['packet']['scene'],w['response']['spec'],x,w['response']['initialization_centers_m']);valid[key].append(v['valid'])
   checks.append(dict(bits=list(key),decision=d,layout=x,verification=v))
 loss=[];loss_noauthority=[]
 for a,b,q in STATES:
  v=valid[a,b];quality=[l['objective_metrics']['mean_stage_distance_m']/32 for l in decisions]
  loss.append([2.]+[s if ok and q else 100. for s,ok in zip(quality,v)])
  loss_noauthority.append([2.]+[s if ok else 100. for s,ok in zip(quality,v)])
 anchors=read(H/'ACTUAL_PREDICTION_ANCHORS.json')[worlds[0]['index']['anchor_index']]
 confidences=[o['confidence'] for o in anchors['opening_candidates']]
 uncertainty=sorted([0,1],key=lambda k:(confidences[k],k))+[2]
 areas={'ENTRANCE_PARTITION':[96,5,0],'REGION_OBSTACLE':[160,9,0],'ACTIVITY_GUEST_CHANGE':[16,9,0],'CONFLICT_PROTECTED_STAGE':[10,10,0]}[case]
 geometric=sorted(range(3),key=lambda k:(-areas[k],k))
 sensitivity=[]
 for k in range(3):
  n=sum((loss[i][d]<2)!=(loss[STATES.index(tuple(1-v if j==k else v for j,v in enumerate(s)))][d]<2) for i,s in enumerate(STATES) for d in range(1,len(loss[0])))
  sensitivity.append(n)
 graph_order=sorted(range(3),key=lambda k:(-sensitivity[k],k))
 matrix=dict(case=case,states=STATES,loss=loss,loss_noauthority=loss_noauthority,decisions=decisions,checks=checks,uncertainty_order=uncertainty,geometry_order=geometric,graph_order=graph_order,sensitivity=sensitivity,source_anchor_sha256=digest(anchors))
 save(H/'policy_inputs'/case/'OUTCOME_TABLE.json',matrix);matrices.append(dict(case=case,path=str(H/'policy_inputs'/case/'OUTCOME_TABLE.json'),sha256=sha(H/'policy_inputs'/case/'OUTCOME_TABLE.json')))
 for budget in range(4):
  for ti,truth in enumerate(STATES):
   variants=[(f'B0_{i}',list(order)) for i,order in enumerate(itertools.permutations(range(3)))]+[(m,o) for m,o in [('B1',uncertainty),('B2',geometric),('B3',None),('B4',graph_order),('B5',None),('B6',[0,1,2]),('NEW',None),('NO_EVENT',geometric),('NO_FEEDBACK',uncertainty),('NO_AUTHORITY',None)]]
   for method,order in variants:
    t=time.perf_counter();loss_used=loss_noauthority if method=='NO_AUTHORITY' else loss
    result=replay(method,loss_used,truth,3 if method=='B6' else budget,order);elapsed=time.perf_counter()-t
    d=result['decision'];observed=result['observed'];conditional=d!=0;ok=conditional and loss[ti][d]<2
    target_world=next(w for w in worlds if w['index']['bits']==list(truth[:2]));actual=target_world['response']
    # Actual eligibility refers ONLY to the original engine-returned target-world
    # envelope, never to a transplanted counterfactual seating decision.
    ready=len(observed)==3 and truth[2]==1 and actual['status']=='eligible' and method!='NO_AUTHORITY'
    actual_layout=min(actual['candidate_layouts'],key=lambda l:l['objective_metrics']['mean_stage_distance_m']) if ready else None
    actual_status='EXPECTED_REFUSAL' if observed.get(2)==0 else 'EXPECTED_PENDING' if len(observed)<3 else 'ACTUAL_CONTROLLED_WORLD_RESULT_AVAILABLE' if ready else 'EXPECTED_REFUSAL'
    fullrisk,fulld=terminal(loss,[ti]);regret=(loss[ti][d]-fullrisk)*32 if ok else None
    row=dict(case=case,budget=budget,truth=list(truth),method=method,weight=1/6 if method.startswith('B0') else 1.,policy_seconds=elapsed,**result,conditional_plan=conditional,conditional_valid=bool(ok),actual_loss=loss[ti][d],false_conditional_accept=conditional and not ok,ready=bool(ready),false_readiness=ready and not ok,actual_status=actual_status,missed_mandatory_facts=3-len(observed),stage_regret_m=regret,full_information_best_loss=fullrisk,feasible_signature_count=sum(all(loss[i][j]<2 for i in result['posterior']) for j in range(1,len(loss[0]))),source_anchor_sha256=digest(anchors),world_table_sha256=sha(H/'policy_inputs'/case/'OUTCOME_TABLE.json'),fresh_optimizer_evaluations=0,explanation='Conditional plan only until all source-bound controlled facts and authority reviewed; real venue remains pending.')
    row.update(qualified_result_path=target_world['index']['result'] if ready else None,qualified_result_sha256=target_world['index']['result_sha256'] if ready else None,qualified_layout_sha256=digest(actual_layout) if ready else None,qualified_stage_distance_m=actual_layout['objective_metrics']['mean_stage_distance_m'] if ready else None,qualified_result_is_conditional_seating_decision=False,conditional_refusal_with_full_information_feasible=not conditional and fullrisk<2)
    row['xai_binding']=digest({k:v for k,v in row.items() if k!='policy_seconds'});rows.append(row)
 print('Policy replay',case,len(decisions),'decisions',flush=True)
save('POLICY_INPUT_MANIFEST.json',matrices);save('RAW_REVIEW_RESULTS.json',rows)
with (H/'RAW_REVIEW_RESULTS.csv').open('x',encoding='utf-8',newline='') as f:
 keys=list(rows[0]);writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows({k:json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows)
save('POLICY_EXECUTION.json',dict(seconds=time.perf_counter()-start,python_tracemalloc_peak_bytes=tracemalloc.get_traced_memory()[1],guard=events,rows=len(rows),fresh_optimizer_evaluations=0,calibration_ablation='NOT_COMPARABLE_NO_CALIBRATED_UNCERTAINTY',authority_ablation='DIAGNOSTIC_ONLY_NEVER_APPROVED'))
