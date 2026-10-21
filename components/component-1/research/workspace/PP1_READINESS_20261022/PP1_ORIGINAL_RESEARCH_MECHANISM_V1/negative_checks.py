from lab import *
import copy
events=guard();runtime,adapter=boot()
from repair import run
from independent import verify_envelope
base=read(H/'worlds/ENTRANCE_PARTITION/00/ACTUAL_SEARCH/INPUT.json');tests=[]
for name in ['missing_metric_review','missing_authority','protected_stage_move','client_planner_conflict']:
 out=H/'negative'/name;p=copy.deepcopy(base)
 if name=='missing_metric_review':
  p['scene']['venue']['review']['status']='pending';r=runtime.fixtures.seal(p['scene'],out/'SIMULATED_PENDING');p=runtime.seal_packet(r,p['context'],out/'PENDING_AUTHORITY')
 elif name=='missing_authority':p['authority']['sha256']='0'*64
 elif name=='protected_stage_move':
  p['context']['object_moves']=[dict(object_id='existing_stage',approved=True,actor_id='SIMULATED_PLANNER')];p=runtime.seal_packet(p['scene'],p['context'],out/'SIMULATED_UNLAWFUL_ACTION')
 else:
  p['scene']['planner']['guest_count']+=8;r=runtime.fixtures.seal(p['scene'],out/'SIMULATED_CONFLICT');p=runtime.seal_packet(r,p['context'],out/'CONFLICT_AUTHORITY')
 response,_=run(p,out/'RESULT','EAG',20261017);check=verify_envelope(p,response)
 assert response['status']!='eligible' and response['optimizer_evaluations']==0 and not response['candidate_layouts'] and check['valid']
 tests.append(dict(name=name,status=response['status'],reasons=response['reasons'],evaluations=response['optimizer_evaluations'],independent=check))
save('NEGATIVE_CHECKS.json',dict(tests=tests,guard=events))
