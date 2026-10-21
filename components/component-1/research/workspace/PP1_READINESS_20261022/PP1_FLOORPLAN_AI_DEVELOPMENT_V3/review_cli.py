"""Operator-supplied structured pixel edit or unchanged metric-gate validation."""
import argparse
from common import *
from review_handoff import edit_proposal,validate_metric_review
p=argparse.ArgumentParser();p.add_argument("--page",required=True,type=Path);p.add_argument("--review",required=True,type=Path);p.add_argument("--mode",choices=["edit","metric"],required=True);p.add_argument("--out",required=True,type=Path);a=p.parse_args()
target=a.out.resolve();assert target.is_relative_to(H)
try:
 bundle=read(a.page)["candidate_bundle"];review=read(a.review)
 result=edit_proposal(bundle,review) if a.mode=="edit" else validate_metric_review(bundle,review)
 save(target.relative_to(H),{"status":"local_edit_pending_metric_review" if a.mode=="edit" else "passed_unchanged_metric_gate","result":result,
  "authenticated_planner_identity":False,"backend_registration_performed":False})
 print("Input processed through",a.mode,"contract")
except ValueError as e:
 save(target.relative_to(H),{"status":"rejected","reason":str(e),"exception":type(e).__name__,"backend_registration_performed":False})
 print("Rejected:",type(e).__name__);raise SystemExit(2)
