"""Artifact/SQL/label/geometry/XAI replay, separate from experiment dispatch."""
from lab import *
import csv,sqlite3,collections,math,copy,ast,statistics,time
events=guard();runtime,adapter=boot()
from independent import verify_envelope,verify_candidate
manifest=read(H/'FROZEN_BENCHMARK_MANIFEST.json');records=read(H/'RAW_EXPERIMENT_RESULTS.json');checks=[];candidates=0;sqlrows=0
lookup={(r['unit'],r['case'],r['method']):r for r in records};pairs=[];issues=[];rejected_proposals=[];unique_geometry=set()
for u in manifest['units']:
 reference=read(u['reference']);assert sha(u['reference'])==u['reference_sha256']
 for case in u['cases']:
  q=read(case['input']);assert sha(case['input'])==case['input_sha256']
  responses={}
  for method in ['B0','B1','B2','B3','B4','EAG']:
   row=lookup[(u['unit'],case['case'],method)];p=Path(row['response_path']);r=read(p);assert sha(p)==row['response_sha256'];assert r['status']==row['status'];responses[method]=r
   assert not (row['status']=='eligible' and case['expected']!='eligible')
   if 'certificate' not in r:
    assert not r['candidate_layouts'] and r['optimizer_evaluations']==0;continue
   started=time.perf_counter();v=verify_envelope(q,r,reference);verification_seconds=time.perf_counter()-started;assert v['valid'],v
   search_file=p.parent/'ACTUAL_SEARCH/RESULT.json'
   if r['status']=='refused' and search_file.is_file():
    for proposal in read(search_file)['candidate_layouts']:
     invalid=verify_candidate(q,r['spec'],proposal,r['initialization_centers_m'],reference,q['context']['requested_group'])
     assert not invalid['valid']
     if case['case']=='guest_count_decreased':assert 'UNSUPPORTED_REFERENCE_REMOVAL' in invalid['errors']
     if case['case']=='changed_protected_obstacle':assert 'PROTECTED_OBJECT_CHANGED' in invalid['errors']
     rejected_proposals.append(dict(unit=u['unit'],case=case['case'],method=method,layout_id=proposal['layout_id'],errors=invalid['errors'],current_scene_geometry_valid=invalid['geometry']['valid']))
   with sqlite3.connect((p.parent/'assurance.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
    rows=db.execute('select input_json,response_json,sha256 from records').fetchall();assert len(rows)==1
    qr,rr,hh=rows[0];assert read(p)==json.loads(rr) and json.loads(qr)==q and digest(json.loads(rr))==hh;sqlrows+=1
   for layout in r['candidate_layouts']:
    candidates+=1;obs=layout['objects'];count=collections.Counter(o['class'] for o in obs)
    unique_geometry.add(digest(dict(objects=obs,zones=layout['zones'],group_centers_m=layout['group_centers_m'])))
    # Independent literal seating count oracle for supported exact8 policy.
    assert count['chair']==q['scene']['client']['guest_count'] and count['round_table']*8==count['chair']
    assert len({o['object_id'] for o in obs})==len(obs)
    old={o['object_id']:o for o in reference['layout']['objects']};now={o['object_id']:o for o in obs}
    for oid in q['context']['protected_object_ids']:assert now[oid]==old[oid]
    target=q['context']['requested_group']
    if target:
     for oid,ob in old.items():
      if ob['group_id']!=target:assert now[oid]==ob
    from shapely.geometry import Polygon
    stage=Polygon(next(o['footprint_coordinates_m'] for o in obs if o['class']=='stage')).centroid
    d=sum(math.hypot(x-stage.x,y-stage.y) for x,y in layout['group_centers_m'].values())/len(layout['group_centers_m']);assert abs(d-layout['objective_metrics']['mean_stage_distance_m'])<1e-7
   checks.append(dict(unit=u['unit'],case=case['case'],method=method,envelope=True,sql=True,candidates=len(r['candidate_layouts']),verification_seconds=verification_seconds))
  a,b=responses['EAG'],responses['B4']
  closure_comparable='impact' in a and 'impact' in responses['B3']
  anchor_equal=digest(a.get('initialization_centers_m'))==digest(b.get('initialization_centers_m'))
  if a['status']==b['status']=='eligible':assert anchor_equal
  b0=responses['B0'];b0_anchor_equal=digest(a.get('initialization_centers_m'))==digest(b0.get('initialization_centers_m')) if a['status']==b0['status']=='eligible' else None
  pair=dict(unit=u['unit'],case=case['case'],status_equal=a['status']==b['status'],pool_equal=digest(a['candidate_layouts'])==digest(b['candidate_layouts']),evaluations_equal=a['optimizer_evaluations']==b['optimizer_evaluations'],objective_reference_equal=anchor_equal,B0_eligible_objective_reference_equal=b0_anchor_equal,operation_equal=a.get('operation')==b.get('operation'),closure_comparable=closure_comparable,closure_equal=a['impact']['affected_constraints']==responses['B3']['impact']['affected_constraints'] if closure_comparable else None,shared_adapter_gate=case['case']=='revoked_adapter_authority')
  pairs.append(pair)
  if not pair['status_equal'] or not pair['pool_equal'] or not pair['evaluations_equal']:issues.append(pair)
before=read(H/'PRESERVATION_BEFORE.json');assert all(sha(ROOT/k)==v for k,v in before.items())
save('INDEPENDENT_VERIFICATION.json',dict(status='PASS',outcome_records=len(records),scenario_instances=len(pairs),returned_candidate_records=candidates,unique_returned_geometry_hashes=len(unique_geometry),validated_sql_rows=sqlrows,pair_checks=pairs,paired_equivalence_failures=issues,rejected_raw_proposals=rejected_proposals,checks=checks,preservation=dict(tracked_files=len(before),all_match=True),guard=events,limits='Existing independent geometry/function checker shared by all methods. Added literal seating/identity/lock/stage/SQLite/expected-label checks; shared Shapely kernels and controlled labels. Not independent human certification.'))
print('Replay PASS:',len(records),'outcomes;',candidates,'candidate records;',sqlrows,'SQLite rows; B4 disagreements',len(issues))
