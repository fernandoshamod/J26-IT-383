"""Actual document inference, source-coordinate verification, review edits and refusals."""
import platform,time
from common import *
platform.uname();events=guard()
import numpy as np,torch
from PIL import Image
from shapely.geometry import shape,box
from upload_inference import UploadRequest,infer
from outdoor_geometry import vector_regions
from review_handoff import edit_proposal,validate_metric_review
torch.set_num_threads(4);parts=read(H/"unet/ELIGIBLE_NATIVE_SPLITS.json")
checks=[];runs=[];t=time.perf_counter()
def check(n,v):
 checks.append({"name":n,"passed":bool(v)})
 if not v:raise AssertionError(n)
def run(name,path,route):
 r=infer(UploadRequest(path=str(path),route=route),H/"uploads"/name)
 runs.append({"name":name,"source":str(path),"source_sha256":sha(path),"route":route,"pages":len(r["pages"]),"model_calls":[p["actual_model_calls"] for p in r["pages"]],"statuses":[p["status"] for p in r["pages"]],"candidate_counts":[len(p["candidate_bundle"]["objects"]) for p in r["pages"]],"outdoor_proposal_counts":[len(p["algorithmic_region_proposals"]) for p in r["pages"]],"vector_region_counts":[len(p["vector_source_regions"]["regions"]) for p in r["pages"]],"metric_ready":r["metric_twin_ready"]})
 check(name+" doc identity",r["original_document"]["source_sha256"]==sha(path) if "source_sha256" in r["original_document"] else r["original_document"]["sha256"]==sha(path))
 check(name+" metric gate remains pending",not r["metric_twin_ready"] and not r["approved"] and all(not p["candidate_bundle"]["optimization_ready"] and p["candidate_bundle"]["metres_per_pixel"] is None for p in r["pages"]))
 for pi,p in enumerate(r["pages"],1):
  src=p["candidate_bundle"]["source"];w,h=src["width_pixels"],src["height_pixels"]
  for o in p["candidate_bundle"]["objects"]:
   g=shape(o["geometry"]);check(name+" object valid/in bounds "+o["id"],g.is_valid and box(-1e-6,-1e-6,w+1e-6,h+1e-6).covers(g))
  accepted=H/"uploads"/name/("page_%03d"%pi)/"ACCEPTED_CONTENT_MASK.png"
  if accepted.exists():
   # Independent total area by saved pixel counts and direct shapely areas.
   with Image.open(accepted) as im:a=np.array(im);aw,ah=im.size
   expected=sum(c["predicted_component_pixels"] for c in p["extraction_checks"])*w/aw*h/ah
   actual=sum(shape(o["geometry"]).area for o in p["candidate_bundle"]["objects"] if o.get("model")=="U-Net ResNet18")
   check(name+" source-frame polygon area",abs(actual-expected)<1e-5)
 return r
first=parts["diagnostic_test"][0]
r=run("INDOOR_NATIVE",Path(first["source_image"]),"indoor")
check("indoor actual inference",r["pages"][0]["actual_model_calls"]=={"unet":1,"opening_yolo":1})
different=next(x for x in parts["diagnostic_test"] if x["style"]!=first["style"])
run("INDEPENDENT_DRAWING_STYLE",Path(different["source_image"]),"indoor")
site=run("NPS_OUTDOOR_SITE",H/"acquired/NPS_PINES_SITE_PLAN.jpg","outdoor")
check("pure outdoor not sent to indoor ontology",all(p["actual_model_calls"]=={"unet":0,"opening_yolo":0} for p in site["pages"]))
run("PUBLIC_PDF",H/"acquired/NPS_CAMPGROUND_MAP.pdf","outdoor")
# Genuine native annotated SVG: select by source semantic support only, not model score.
chosen=None
for r0 in parts["train"]:
 import xml.etree.ElementTree as ET
 tree=ET.parse(r0["source_svg"]).getroot();cl=[e.get("class","") for e in tree.iter()]
 if any(c.startswith("Space Outdoor") for c in cl) and any(c.startswith("Space Bedroom") for c in cl):
  vb=list(map(float,tree.get("viewBox").split()));regions=vector_regions(r0["source_svg"],round(vb[2]),round(vb[3]))
  kinds={p["semantic_class"] for p in regions["regions"]}
  if {"indoor_region","outdoor_region"}<=kinds and not regions["conflicts"]:chosen=r0;break
if chosen:
 hybrid=run("NATIVE_HYBRID_VECTOR",Path(chosen["source_svg"]),"hybrid")
 check("hybrid beyond routing: explicit source regions",hybrid["pages"][0]["mixed_region_status"]=="SOURCE_SEMANTIC_VECTOR_REGIONS_WITH_OVERLAP_CHECK")
else:save("uploads/HYBRID_SOURCE_BLOCKED.json",{"status":"DATA_BLOCKED","reason":"No inspected source with valid explicit indoor/outdoor vector regions"})
# Existing user-provided document: functional decoding/inference only; rights/provenance not certified for training.
multi=ROOT/"03_REAL_VENUE_REFERENCES/00_INBOX/PDF_ORIGINALS/feb-2025-floor-plan.pdf"
multiresult=run("USER_MULTIPAGE_PDF",multi,"indoor")
check("actual multipage PDF processed",len(multiresult["pages"])==4)
fixtures=H/"upload_test_fixtures";fixtures.mkdir(exist_ok=False)
Image.new("RGB",(160,120),"white").save(fixtures/"EMPTY.png")
empty=run("EMPTY_REFUSAL",fixtures/"EMPTY.png","indoor")
check("empty plan refused without model calls",empty["pages"][0]["status"]=="rejected_empty_drawing" and empty["pages"][0]["actual_model_calls"]=={"unet":0,"opening_yolo":0})
# Explicit analytic synthetic conflict fixture; no claimed real annotation.
(fixtures/"OVERLAP.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><g class="Space Bedroom"><polygon points="0,0 60,0 60,90 0,90"/></g><g class="Space Outdoor"><polygon points="50,0 100,0 100,90 50,90"/></g></svg>',encoding="utf-8")
conflict=run("CONTROLLED_REGION_CONFLICT",fixtures/"OVERLAP.svg","hybrid")
check("conflicting indoor/outdoor polygons refused",conflict["pages"][0]["status"]=="rejected_conflicting_regions" and conflict["pages"][0]["actual_model_calls"]=={"unet":0,"opening_yolo":0})
for name,data in [("INVALID.jpg",b"not an image"),("UNSUPPORTED.dxf",b"unimplemented CAD fixture")]:
 (fixtures/name).write_bytes(data)
 try:infer(UploadRequest(path=str(fixtures/name),route="indoor"),H/"uploads"/name);raise AssertionError("Invalid accepted")
 except ValueError as e:check(name+" decoder refusal",str(e).startswith("DOCUMENT_DECODE_REJECTED"))
bundle=r["pages"][0]["candidate_bundle"]
try:edit_proposal(bundle,{});raise AssertionError("Missing reviewer accepted")
except ValueError:check("missing explicit edit review rejected",True)
try:validate_metric_review(bundle,{});raise AssertionError("Missing measurements accepted")
except ValueError as e:
 check("actual frozen metric review rejects absent evidence/measurements",True)
 save("uploads/FROZEN_REVIEW_REJECTION.json",{"error":str(e),"scope":"Actual frozen schema negative test, not genuine positive planner approval"})
w,h=bundle["source"]["width_pixels"],bundle["source"]["height_pixels"]
edited=edit_proposal(bundle,{"source_sha256":bundle["source"]["sha256"],"reviewer_id":"CONTROLLED_UNIT_TEST_NOT_A_PLANNER","reason":"Explicit analytic edit-function test; no real boundary assertion","boundary_px":[[1,1],[w-1,1],[w-1,h-1],[1,h-1]]})
check("edit is not metric approval",not edited["optimization_ready"] and not edited["planner_approval_verified"])
save("uploads/CONTROLLED_EDIT_RESULT.json",edited)
save("uploads/REQUEST_SCHEMA.json",UploadRequest.model_json_schema())
save("uploads/TEST_RESULTS.json",{"status":"PASS","checks":checks,"runs":runs,"seconds":time.perf_counter()-t,
 "claims":"Functional user-upload-equivalent processing and pending review, not approved real-venue metric truth. Multi-page private document is user-provided inference only, not training/redistribution data. Controlled fixtures explicitly synthetic."})
save("uploads/GUARD.json",events)
print("Upload tests PASS",len(checks),"assertions",len(runs),"document cases")
