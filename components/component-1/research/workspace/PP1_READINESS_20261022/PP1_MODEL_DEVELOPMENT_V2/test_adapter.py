"""Real inference plus independently counted image geometry and frozen review refusal."""
import platform,sys,math
from common import *
platform.uname();events=guard()
import torch,numpy as np
torch.set_num_threads(4)
from PIL import Image
from shapely.geometry import shape,Point
from adapter import AnalyzeRequest,route,analyze
from pydantic import ValidationError
checks=[]
def check(name,value):
 checks.append({"name":name,"passed":bool(value)})
 if not value:raise AssertionError(name)
p=sorted((H/"yolo/dataset/train/images").glob("*INDOOR*"))[0]
outdoor_p=sorted((H/"yolo/dataset/test/images").glob("*OUTDOOR*"))[0]
base={"image_path":str(p),"venue_type":"indoor","input_kind":"floorplan_raster","source_domain":"controlled_synthetic"}
check("outdoor is never forced through indoor classes",route(AnalyzeRequest(**(base|{"venue_type":"outdoor","input_kind":"siteplan_raster"})))["segmentation_regions"]==[])
check("hybrid needs explicitly supplied indoor region",route(AnalyzeRequest(**(base|{"venue_type":"hybrid"})))["status"]=="pending_review")
for kind in ["pdf","cad","venue_photo"]:
 check(kind+" unsupported",route(AnalyzeRequest(**(base|{"input_kind":kind})))["status"]=="unsupported")
try:AnalyzeRequest(**(base|{"approval":True}));raise AssertionError("extra field accepted")
except ValidationError:check("caller cannot supply invented approval flag",True)
out=H/"adapter_outputs/INDOOR_CONTROLLED"
result=analyze(AnalyzeRequest(**base),out);bundle=result["candidate_bundle"]
check("actual two models called",result["actual_model_calls"]=={"unet":1,"yolo":1})
check("source identity preserved",bundle["source"]["sha256"]==sha(p))
check("optimization remains blocked",not bundle["optimization_ready"] and not result["metric_twin_ready"] and bundle["boundary"] is None and bundle["metres_per_pixel"] is None)
check("all output objects uncertain and unapproved",all(o["status"]=="uncertain" and not o["planner_confirmed"] and not o["relocation_allowed"] for o in bundle["objects"]))
check("unique object IDs",len({o["id"] for o in bundle["objects"]})==len(bundle["objects"]))
with Image.open(out/"UNET_REGION_00_ACCEPTED_LABELS.png") as im:accepted=np.array(im);aw,ah=im.size
w,h=bundle["source"]["width_pixels"],bundle["source"]["height_pixels"]
for c,name in enumerate(["room_region","wall","door","window"],1):
 # Separate flood fill on saved grid; count only components meeting frozen >=12 cell rule.
 cells=set(map(tuple,np.argwhere(accepted==c).tolist()));expected=0
 while cells:
  seed=cells.pop();stack=[seed];count=0
  while stack:
   y,x=stack.pop();count+=1
   for dy in [-1,0,1]:
    for dx in [-1,0,1]:
     n=(y+dy,x+dx)
     if n in cells:cells.remove(n);stack.append(n)
  if count>=12:expected+=count
 geoms=[shape(o["geometry"]) for o in bundle["objects"] if o["model"]=="U-Net ResNet18" and o["semantic_class"]==name]
 check(name+" independent polygon validity",all(g.is_valid for g in geoms))
 check(name+" independent flood-fill count / polygon area",math.isclose(sum(g.area for g in geoms),expected*w/aw*h/ah,rel_tol=0,abs_tol=1e-6))
# Exercise actual frozen schema and review gate; never supply invented measurements or approval.
sys.path.insert(0,str(ROOT/"PP1_READINESS_20261022/PP1_EXECUTABLE_V1"))
from contracts import TwinReview
from review_gate import reviewed_metric_twin
import hashlib,json
digest=hashlib.sha256(json.dumps(bundle,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
pending={"contract_id":"COMPONENT1_REVIEWED_TWIN_V1","venue_id":"PENDING_ADAPTER_REVIEW","venue_version":1,"source":bundle["source"],"candidate_bundle_sha256":digest,
 "calibration":{"method":"isotropic_two_point_controls","controls":[],"metric_origin_px":[0.,0.]},
 "boundary_px":[],"objects":[],"review":{"status":"pending","reviewer_id":"","evidence_ref":"","scope":"SIMULATED_FIXTURE_REVIEW","geometry_confirmed":False,"metric_dimensions_confirmed":False}}
try:
 review=TwinReview.model_validate(pending);reviewed_metric_twin(review,bundle);raise AssertionError("Missing review accepted")
except (ValidationError,ValueError) as e:
 check("frozen gate refuses missing measurement/review",True)
 save("adapter_outputs/FROZEN_GATE_REJECTION.json",{"rejected":True,"exception_type":type(e).__name__,"details":str(e),"scope":"Schema/gate negative test only; no successful real-Twin registration claim"})
try:
 analyze(AnalyzeRequest(**(base|{"image_path":str(outdoor_p)})),H/"adapter_outputs/WRONG_SOURCE_ROUTE")
 raise AssertionError("Outdoor source accepted as indoor")
except ValueError as e:check("source-group routing conflict refused",str(e)=="DECLARED_ROUTE_CONFLICTS_WITH_CONTROLLED_SOURCE_GROUP")
outdoor=analyze(AnalyzeRequest(**(base|{"image_path":str(outdoor_p),"venue_type":"outdoor","input_kind":"siteplan_raster"})),H/"adapter_outputs/OUTDOOR_PENDING")
check("outdoor actual model calls zero",outdoor["actual_model_calls"]=={"unet":0,"yolo":0} and outdoor["candidate_bundle"]["objects"]==[])
save("adapter_outputs/REQUEST_SCHEMA.json",AnalyzeRequest.model_json_schema())
save("adapter_outputs/TEST_RESULTS.json",{"status":"PASS","checks":checks,"real_inference_input":str(p),"source_domain":"controlled_synthetic","input_partition":"train; functional adapter demonstration only, not held-out accuracy","positive_real_calibrated_twin_tested":False,"hybrid_crop_inference_tested":False})
save("adapter_outputs/GUARD.json",events)
print("Adapter PASS",len(checks),"checks; actual inference and independent geometry replay, pending gate intact")
