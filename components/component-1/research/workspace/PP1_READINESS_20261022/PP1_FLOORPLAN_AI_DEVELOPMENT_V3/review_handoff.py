"""Structured editing and genuine-evidence handoff to the unchanged metric review gate."""
import sys
from common import *
from shapely.geometry import Polygon
def edit_proposal(bundle,changes):
 required={"source_sha256","reviewer_id","reason","boundary_px"}
 if set(changes)!=required or not all(isinstance(changes[k],str) and changes[k].strip() for k in ["source_sha256","reviewer_id","reason"]):
  raise ValueError("EXPLICIT_SOURCE_REVIEWER_REASON_AND_BOUNDARY_REQUIRED")
 if changes["source_sha256"]!=bundle["source"]["sha256"]:raise ValueError("STALE_SOURCE_EDIT")
 ring=changes["boundary_px"];p=Polygon(ring)
 if not p.is_valid or p.area<=0:raise ValueError("INVALID_EDIT_POLYGON")
 w,h=bundle["source"]["width_pixels"],bundle["source"]["height_pixels"]
 if any(not(0<=x<=w and 0<=y<=h) for x,y in ring):raise ValueError("EDIT_OUTSIDE_SOURCE")
 return {"source":bundle["source"],"edited_boundary_px":ring,"reviewer_assertion":changes["reviewer_id"],"reason":changes["reason"],
  "status":"LOCAL_UNAUTHENTICATED_EDIT","metric_calibrated":False,"planner_approval_verified":False,"optimization_ready":False,
  "next":"Submit actual source-bound metric evidence and explicit review using unchanged TwinReview contract; edit alone is not approval."}
def validate_metric_review(bundle,review_payload):
 # Read-only invocation: no server, database, frozen code edit or invented route.
 sys.path.insert(0,str(ROOT/"PP1_READINESS_20261022/PP1_EXECUTABLE_V1"))
 from contracts import TwinReview
 from review_gate import reviewed_metric_twin
 return reviewed_metric_twin(TwinReview.model_validate(review_payload),bundle)
