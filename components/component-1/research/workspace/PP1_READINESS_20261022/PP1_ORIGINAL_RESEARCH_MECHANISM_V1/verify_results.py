"""Independent saved-output replay, direct SQLite, geometry, Bayes accounting.
Does not import the review-policy selector or primary transplant/metric helper.
"""
from lab import *
import collections,sqlite3,math,itertools,time
events=guard();runtime,adapter=boot()
from independent import verify_envelope
from shapely.geometry import Polygon
start=time.perf_counter();assertions=0
def check(value,label):
 global assertions
 assertions+=1
 if not value:raise AssertionError(label)
for anchor in read(H/'ACTUAL_PREDICTION_ANCHORS.json'):
 check(sha(anchor['artifact'])==anchor['sha256'],'ACTUAL_PREDICTION_ARTIFACT_HASH')
 check(sha(anchor['source']['path'])==anchor['source']['sha256'],'ORIGINAL_SOURCE_HASH')
 check(anchor['metric_transfer'] is False and anchor['ground_truth_used'] is False,'ANCHOR_IS_NOT_METRIC_TRUTH')
 check(anchor['unet_candidate']['id'].startswith('UNET') and all(o['id'].startswith('OPENING_YOLO') for o in anchor['opening_candidates']),'ACTUAL_V3_PREDICTIONS_CONSUMED')
worlds=read(H/'WORLD_INDEX.json');dbs=[];candidate_count=0;seating_hashes=set();pool_sets={}
for w in worlds:
 response=read(w['result']);packet=read(w['input']);check(sha(w['result'])==w['result_sha256'],'WORLD_RESULT_SHA');check(verify_envelope(packet,response)['valid'],'EAG_REPLAY')
 candidates=response['candidate_layouts'];candidate_count+=len(candidates)
 pool_sets[w['case'],tuple(w['bits'])]={digest(l['group_centers_m']) for l in candidates};seating_hashes.update(pool_sets[w['case'],tuple(w['bits'])])
 for l in candidates:
  polygons=[Polygon(o['footprint_coordinates_m']) for o in l['objects']];boundary=Polygon(packet['scene']['venue']['boundary_m'])
  check(all(boundary.covers(p) for p in polygons),'DIRECT_CONTAINMENT');check(all(p.intersection(q).area<1e-8 for i,p in enumerate(polygons) for q in polygons[:i]),'DIRECT_OVERLAP')
  check(sum(o['class']=='chair' for o in l['objects'])==w['guests'],'EXACT_CHAIR_COUNT')
  for stock in packet['scene']['venue']['existing']:
   check(next(o for o in l['objects'] if o['object_id']==stock['instance_id'])['footprint_coordinates_m']==stock['footprint_m'],'FIXED_OBJECT_PRESERVED')
 db=Path(w['result']).parent/'assurance.sqlite3'
 with sqlite3.connect(f'file:{db.as_posix()}?mode=ro',uri=True) as c:
  record=c.execute('SELECT input_json,response_json,sha256 FROM records').fetchall();check(len(record)==1,'DB_ROW_COUNT')
  stored_input,stored_response,hashed=record[0];check(json.loads(stored_input)==packet,'DB_INPUT');check(json.loads(stored_response)==response and digest(response)==hashed,'DB_RESPONSE')
 dbs.append(str(db))

matrices={};cross_checks=0;failures_by_error=collections.Counter();finite_bellman=[]
for m in read(H/'POLICY_INPUT_MANIFEST.json'):
 check(sha(m['path'])==m['sha256'],'MATRIX_HASH');table=read(m['path']);matrices[m['case']]=table
 states=table['states'];loss=table['loss'];bybits={tuple(w['bits']):w for w in worlds if w['case']==m['case']}
 for item in table['checks']:
  w=bybits[tuple(item['bits'])];response=read(w['result']);packet=read(w['input']);v=runtime.oracle.validate_layout(packet['scene'],response['spec'],item['layout'],response['initialization_centers_m']);check(v==item['verification'],'CROSS_WORLD_ORACLE_REPLAY');cross_checks+=1;failures_by_error.update(v['errors'])
  for si,s in enumerate(states):
   if s[:2]==item['bits']:check(abs(loss[si][item['decision']]-(item['layout']['objective_metrics']['mean_stage_distance_m']/32 if v['valid'] and s[2] else 100.))<1e-10,'LOSS_FROM_RAW_CHECK')
 # Independently enumerate belief partitions; no review implementation imported.
 def value(ids,known,b):
  risk=min(sum(loss[i][d] for i in ids)/len(ids) for d in range(len(loss[0])))
  if b:
   for k in set(range(3))-known:
    partitions=[[i for i in ids if states[i][k]==a] for a in [0,1]]
    risk=min(risk,sum(len(p)*value(p,known|{k},b-1) for p in partitions if p)/len(ids))
  return risk
 for budget in range(4):finite_bellman.append(dict(case=m['case'],budget=budget,expected_loss=value(list(range(8)),set(),budget)))

rows=read(H/'RAW_REVIEW_RESULTS.json');pairs=[];lookup={(r['case'],r['budget'],tuple(r['truth']),r['method']):r for r in rows}
for r in rows:
 table=matrices[r['case']];truth=r['truth'];states=table['states'];loss=table['loss'];ti=states.index(truth);obs={int(k):v for k,v in r['observed'].items()};ids=[i for i,s in enumerate(states) if all(s[k]==v for k,v in obs.items())]
 check(ids==r['posterior'],'POSTERIOR');check(r['review_cost']==len(obs)==len(r['trace']),'REVIEW_ACCOUNTING');check(r['review_cost']<=(3 if r['method']=='B6' else r['budget']),'BUDGET')
 check(obs.get(2)!=0 or r['actual_status']=='EXPECTED_REFUSAL','KNOWN_AUTHORITY_REFUSAL')
 check(loss[ti][r['decision']]==r['actual_loss'],'ACTUAL_LOSS');check(not r['false_readiness'],'NO_FALSE_READY');check(not r['ready'] or len(obs)==3 and truth[2] and r['method']!='NO_AUTHORITY','READINESS_GATE')
 if r['ready']:
  target=read(r['qualified_result_path']);check(sha(r['qualified_result_path'])==r['qualified_result_sha256'],'QUALIFIED_ACTUAL_RESULT_HASH');check(any(digest(l)==r['qualified_layout_sha256'] and l['objective_metrics']['mean_stage_distance_m']==r['qualified_stage_distance_m'] for l in target['candidate_layouts']),'QUALIFIED_ACTUAL_ENGINE_POLYGONS')
 if r['method']=='NEW':
  b=lookup[r['case'],r['budget'],tuple(truth),'B5'];same=all(r[k]==b[k] for k in ['decision','observed','actual_loss','ready']) and abs(r['conditional_expected_loss']-b['conditional_expected_loss'])<1e-10 and len(r['trace'])==len(b['trace']) and all(a['fact']==c['fact'] and a['answer']==c['answer'] and abs(a['predicted_remaining_risk']-c['predicted_remaining_risk'])<1e-10 for a,c in zip(r['trace'],b['trace']))
  check(same,'STRONG_BASELINE_MATCH');pairs.append(dict(case=r['case'],budget=r['budget'],truth=truth,identical=same))
 # Verify numerical explanation payload binding (timing deliberately excluded).
 check(r['xai_binding']==digest({k:v for k,v in r.items() if k not in ['policy_seconds','xai_binding']}),'XAI_BINDING')
for v in finite_bellman:
 values=[r['actual_loss'] for r in rows if r['case']==v['case'] and r['budget']==v['budget'] and r['method']=='NEW']
 check(abs(sum(values)/len(values)-v['expected_loss'])<1e-10,'BAYES_VALUE_REPLAY')
summary=[]
for method in ['B0','B1','B2','B3','B4','B5','B6','NEW','NO_EVENT','NO_FEEDBACK','NO_AUTHORITY']:
 for budget in range(4):
  selected=[r for r in rows if r['budget']==budget and (r['method'].startswith('B0_') if method=='B0' else r['method']==method)];den=sum(r['weight'] for r in selected)
  def mean(k):return sum(r[k]*r['weight'] for r in selected)/den
  regrets=[r for r in selected if r['stage_regret_m'] is not None]
  summary.append(dict(method=method,budget=budget,finite_world_weight=den,raw_rows=len(selected),review_cost_mean=mean('review_cost'),loss_mean=mean('actual_loss'),conditional_coverage=mean('conditional_plan'),conditional_valid_rate=mean('conditional_valid'),false_conditional_accept_rate=mean('false_conditional_accept'),conditional_refusal_when_full_information_feasible_rate=mean('conditional_refusal_with_full_information_feasible'),qualified_coverage=mean('ready'),false_ready_rate=mean('false_readiness'),unknown_mandatory_mean=mean('missed_mandatory_facts'),robust_feasible_signatures_mean=mean('feasible_signature_count'),stage_regret_m_conditional_mean=sum(r['stage_regret_m']*r['weight'] for r in regrets)/sum(r['weight'] for r in regrets) if regrets else None,policy_seconds_mean=mean('policy_seconds')))
before=read(H/'PRESERVATION_BEFORE.json');check(all(sha(ROOT/k)==v for k,v in before.items()),'FROZEN_FILES_UNCHANGED')
pool_stability=[]
for case in matrices:
 keys=[k for k in pool_sets if k[0]==case]
 for left,right in itertools.combinations(keys,2):
  aa=pool_sets[left];bb=pool_sets[right];pool_stability.append(dict(case=case,left_bits=left[1],right_bits=right[1],seating_signature_intersection=len(aa&bb),seating_signature_union=len(aa|bb),jaccard=len(aa&bb)/len(aa|bb),interpretation='Returned independently nondominated source-world pool overlap, NOT distance to true Pareto front or cross-world objective dominance'))
save('RETURNED_POOL_STABILITY.json',pool_stability)
save('STRONG_BASELINE_PAIRS.json',pairs);save('MEASURED_SUMMARY.json',summary)
save('INDEPENDENT_VERIFICATION.json',dict(status='PASS',assertions=assertions,worlds=len(worlds),actual_candidate_occurrences=candidate_count,distinct_seating_geometry_hashes=len(seating_hashes),cross_world_candidate_checks=cross_checks,cross_world_error_occurrences=dict(failures_by_error),strong_pairs=len(pairs),strong_matches=sum(p['identical'] for p in pairs),sqlite_rows=len(dbs),sqlite_paths=dbs,bellman=finite_bellman,guard=events,seconds=time.perf_counter()-start,preservation_files=len(before),preservation_match=True))
print('Independent replay PASS',assertions,'assertions;',len(pairs),'strong pairs',flush=True)
