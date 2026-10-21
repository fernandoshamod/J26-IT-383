"""Read-only research review recommendation; never a metric approval endpoint."""
from lab import *
import argparse
from policies import proposed
arg=argparse.ArgumentParser();arg.add_argument('--case',required=True,choices=['ENTRANCE_PARTITION','REGION_OBSTACLE','ACTIVITY_GUEST_CHANGE','CONFLICT_PROTECTED_STAGE']);arg.add_argument('--budget',type=int,choices=range(4),required=True);arg.add_argument('--observed',default='{}');a=arg.parse_args()
events=guard();manifest=next(m for m in read(H/'POLICY_INPUT_MANIFEST.json') if m['case']==a.case);assert sha(manifest['path'])==manifest['sha256']
table=read(manifest['path']);anchors=read(H/'ACTUAL_PREDICTION_ANCHORS.json');anchor=next(x for x in anchors if digest(x)==table['source_anchor_sha256'])
assert sha(anchor['artifact'])==anchor['sha256'] and sha(anchor['source']['path'])==anchor['source']['sha256'],'STALE_SOURCE_OR_PREDICTION'
observed={int(k):v for k,v in json.loads(a.observed).items()};assert all(k in range(3) and type(v) is int and v in [0,1] for k,v in observed.items())
risk,fact,decision=proposed(table['loss'],observed,a.budget)
print(json.dumps(dict(case=a.case,observed=observed,additional_review_budget=a.budget,next_fact=fact,expected_terminal_loss=risk,terminal_decision_without_further_review=decision,planning_table_sha256=manifest['sha256'],source_anchor_sha256=table['source_anchor_sha256'],status='RESEARCH_RECOMMENDATION_ONLY',optimization_ready=False,warning='Controlled hypothetical alternatives and simulated query outcomes; real metric review not supplied.'),indent=2))
