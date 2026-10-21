"""Versioned local candidate adapter. It never registers or approves a metric Twin."""
import ast,importlib.util,copy
from typing import Literal
from common import *
from pydantic import BaseModel,ConfigDict,Field,model_validator
class AnalyzeRequest(BaseModel):
 model_config=ConfigDict(extra="forbid",strict=True)
 image_path:str
 venue_type:Literal["indoor","outdoor","hybrid"]
 input_kind:Literal["floorplan_raster","siteplan_raster","venue_photo","pdf","cad"]
 source_domain:Literal["real_source","controlled_synthetic"]
 indoor_regions:list[list[int]]=Field(default_factory=list)
 @model_validator(mode="after")
 def regions(self):
  for box in self.indoor_regions:
   if len(box)!=4 or any(type(v)!=int for v in box) or not(0<=box[0]<box[2] and 0<=box[1]<box[3]):raise ValueError("INVALID_INDOOR_REGION")
  return self
def route(req):
 if req.input_kind in {"pdf","cad"}:return {"status":"unsupported","reason":"RASTER_OR_VERIFIED_GEOMETRY_CONVERSION_REQUIRED","segmentation_regions":[],"detect":False}
 if req.input_kind=="venue_photo":return {"status":"unsupported","reason":"PHOTO_DOMAIN_NOT_VALIDATED_FOR_EITHER_MODEL","segmentation_regions":[],"detect":False}
 if req.venue_type=="outdoor":return {"status":"pending_review","reason":"NO_OUTDOOR_BOUNDARY_MODEL; PLANNER_BOUNDARY_EVIDENCE_REQUIRED","segmentation_regions":[],"detect":False}
 if req.input_kind!="floorplan_raster":return {"status":"unsupported","reason":"INDOOR_MODEL_REQUIRES_FLOORPLAN_RASTER","segmentation_regions":[],"detect":False}
 if req.venue_type=="hybrid" and not req.indoor_regions:return {"status":"pending_review","reason":"EXPLICIT_INDOOR_REGIONS_REQUIRED; TRANSITIONS_NOT_INFERRED","segmentation_regions":[],"detect":False}
 return {"status":"review_required","reason":"UNQUALIFIED_PREDICTIONS_ARE_CANDIDATES_ONLY","segmentation_regions":req.indoor_regions or [None],"detect":True}
def load_module(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def analyze(req:AnalyzeRequest,out):
 import numpy as np,torch,cv2
 from PIL import Image
 from shapely.geometry import box,mapping
 from shapely.ops import unary_union
 from shapely.affinity import scale,translate
 out=Path(out).resolve();assert out.is_relative_to(H)
 out.mkdir(parents=True,exist_ok=False)
 p=Path(req.image_path).resolve()
 if not p.is_relative_to(ROOT) or not p.is_file():raise ValueError("SOURCE_MISSING_OR_OUTSIDE_PROJECT")
 with Image.open(p,formats=["PNG","JPEG"]) as im:
  if im.width*im.height>16000000:raise ValueError("SOURCE_OVER_16_MEGAPIXELS")
  w,h=im.size
 for b in req.indoor_regions:
  if b[2]>w or b[3]>h:raise ValueError("REGION_OUTSIDE_IMAGE")
 source={"path":str(p),"sha256":sha(p),"width_pixels":w,"height_pixels":h,"domain":req.source_domain}
 if req.source_domain=="controlled_synthetic":
  exported=read(H/"yolo/DATASET_EXPORT.json")
  matches=[r for r in exported["copies"] if r["sha256"]==source["sha256"]]
  if matches:
   catalog=read(ROOT/"02_GENERATED_RESEARCH_DATA/STAGE_C_OBJECTS/C3_17_V3_CLEAN_YOLO_CANDIDATE_157/C3_17_RECORD_MANIFEST.json")
   groups={r["source_group"] for m in matches for r in catalog if Path(m["source"]).stem==r["id"]+"_input_BW"}
   types={kind for kind in ["indoor","outdoor","hybrid"] if any("_"+kind.upper()+"_" in g for g in groups)}
   if len(types)!=1 or req.venue_type not in types:raise ValueError("DECLARED_ROUTE_CONFLICTS_WITH_CONTROLLED_SOURCE_GROUP")
 decision=route(req)
 objects=[];checks=[];models={};executed={"unet":0,"yolo":0}
 if decision["segmentation_regions"]:
  infer=load_module(ROOT/"PP1_STAGE_E_EVENT_LAYOUT_V2/backend/venue_unet_inference_v2.py","frozen_unet")
  cp=ROOT/"02_GENERATED_RESEARCH_DATA/STAGE_B_PP1_BASELINE/best_unet_resnet18.pt"
  models["unet_checkpoint_sha256"]=sha(cp)
  assert models["unet_checkpoint_sha256"]=="480f15179818f63b1bdcfc5f72eef62cfdb0db092f27459f274fc72268888a5a"
  model=infer.load_model(cp,torch.device("cpu"));image=infer.load_image(p)
  geometry_source=ROOT/"PP1_READINESS_20261022/10_FINAL_VERIFICATION/FUNCTIONAL_V2/prediction_bridge_v3.py"
  # Reuse exact existing pure function without executing historical module-level imports.
  tree=ast.parse(geometry_source.read_text(encoding="utf-8"));fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="exact_components")
  ns=dict(np=np,cv2=cv2,box=box,mapping=mapping,unary_union=unary_union,scale=scale)
  exec(compile(ast.Module(body=[fn],type_ignores=[]),str(geometry_source),"exec"),ns)
  models["geometry_function_source_sha256"]=sha(geometry_source)
  for ri,region in enumerate(decision["segmentation_regions"]):
   x1,y1,x2,y2=region or [0,0,w,h];crop=image.crop((x1,y1,x2,y2));cw,ch=crop.size
   rgb=np.array(crop.resize((512,512),Image.Resampling.BILINEAR),np.float32)/255
   norm=(rgb-np.array([.485,.456,.406],np.float32))/np.array([.229,.224,.225],np.float32)
   with torch.inference_mode():prob=model(torch.from_numpy(norm.transpose(2,0,1).copy()).unsqueeze(0)).softmax(1)[0].numpy()
   executed["unet"]+=1;raw=prob.argmax(0).astype(np.uint8)
   accepted=np.where(prob.max(0)>=.7,raw+1,0).astype(np.uint8)
   oo,cc=ns["exact_components"](accepted,cw,ch)
   for ob in oo:
    ob["id"]="REGION_%02d_"%ri+ob["id"]
    # Shift every exterior/interior ring into the unchanged original source frame.
    ob["geometry"]["coordinates"]=[[[[float(x+x1),float(y+y1)] for x,y in ring] for ring in poly] for poly in ob["geometry"]["coordinates"]]
    ob["confidence"]=None
    ob["confidence_note"]="0.7 uncalibrated pixel-softmax filter; no certified object confidence"
   for c in cc:c["id"]="REGION_%02d_"%ri+c["id"]
   objects+=oo;checks+=cc
   Image.fromarray(raw).save(out/("UNET_REGION_%02d_MASK.png"%ri))
   Image.fromarray(accepted).save(out/("UNET_REGION_%02d_ACCEPTED_LABELS.png"%ri))
   full=np.array(Image.fromarray(raw).resize((cw,ch),Image.Resampling.NEAREST))
   Image.blend(crop,Image.fromarray(infer.COLORS[full]),.35).save(out/("UNET_REGION_%02d_OVERLAY.png"%ri))
 if decision["detect"]:
  from ultralytics import YOLO
  selection=read(H/"yolo/MODEL_SELECTION.json");cp=selection["selected_checkpoint"]
  assert sha(cp)==selection["selected_sha256"]
  models["yolo_checkpoint_sha256"]=sha(cp)
  detector=YOLO(cp)
  prediction=detector.predict(str(p),imgsz=960,conf=.25,iou=.7,max_det=300,device="cpu",verbose=False,save=False)[0]
  executed["yolo"]+=1
  Image.fromarray(prediction.plot()[:,:,::-1]).save(out/"YOLO_OVERLAY.png")
  for i,(b,c,s) in enumerate(zip(prediction.boxes.xyxy.tolist(),prediction.boxes.cls.tolist(),prediction.boxes.conf.tolist())):
   a,d,e,f=b
   objects.append({"id":"YOLO_%04d"%i,"semantic_class":detector.names[int(c)],"model":"YOLOv8n","confidence":s,"status":"uncertain","source_kind":"actual_trained_model_prediction","planner_confirmed":False,"relocation_allowed":False,"geometry":{"type":"Polygon","coordinates":[[[a,d],[e,d],[e,f],[a,f],[a,d]]],"unit":"original_image_pixels","kind":"bbox_not_exact_physical_footprint"}})
 if sha(p)!=source["sha256"]:raise ValueError("SOURCE_CHANGED")
 bundle={"schema":"IMAGE_SPACE_TWIN_CANDIDATE_V2","source":source,"models":models,"objects":objects,"boundary":None,"metres_per_pixel":None,"planner_reviewed":False,"optimization_ready":False}
 result={"adapter_version":"2.0.0","request":req.model_dump(),"route":decision,"candidate_bundle":bundle,"actual_model_calls":executed,
  "extraction_checks":checks,"review_required":True,"metric_twin_ready":False,
  "unknown":["physical_scale","usable_boundary","physical_object_footprints","outdoor_regions","transitions","planner_authority"],
  "limitations":["U-Net native-CVC pooled mIoU 0.28178; no background channel","YOLO validated only on procedural diagrams","Declared source domain is caller input, not provenance certification","No registered Twin or optimizer route is called","Pending source-bound review and two distinct measured controls required"]}
 with (out/"RESULT.json").open("x",encoding="utf-8") as f:json.dump(result,f,indent=2,allow_nan=False)
 return result
