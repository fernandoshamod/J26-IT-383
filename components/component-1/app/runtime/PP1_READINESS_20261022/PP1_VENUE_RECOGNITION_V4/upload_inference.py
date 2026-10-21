"""Actual local PNG/JPG/PDF/SVG -> candidate-only reviewed-Twin handoff."""
import subprocess,sys,ast,importlib.util,os
from typing import Literal
from common import *
from pydantic import BaseModel,ConfigDict
V3=H.parent/"PP1_FLOORPLAN_AI_DEVELOPMENT_V3"
PACKAGE_ROOT=H.parents[2]
PRIVATE_MODELS=PACKAGE_ROOT/"private-assets"/"models"
STATE_ROOT=Path(os.environ.get("PP1_RUN_STATE",Path(os.environ.get("PP1_RUNTIME_STATE",PACKAGE_ROOT/"runtime-state"))/"runs"/"manual")).resolve()
class UploadRequest(BaseModel):
 model_config=ConfigDict(extra="forbid",strict=True)
 path:str
 experimental_objects:bool=False
 route:Literal["indoor","outdoor","hybrid"]
 domain:Literal["real_source","controlled_synthetic"]="real_source"
def infer(request:UploadRequest,output):
 import numpy as np,torch,cv2
 from PIL import Image,ImageDraw
 from shapely.geometry import box,mapping,shape
 from shapely.ops import unary_union
 from shapely.affinity import scale
 from native_data import letterbox
 from outdoor_geometry import vector_regions,raster_proposals
 torch.set_num_threads(4)
 output=Path(output).resolve();assert output.is_relative_to(STATE_ROOT)
 output.mkdir(parents=True,exist_ok=False)
 source=Path(request.path).resolve()
 if not source.is_relative_to(PACKAGE_ROOT) or not source.is_file():raise ValueError("SOURCE_OUTSIDE_PORTABLE_PACKAGE_OR_MISSING")
 original_sha=sha(source)
 # Separate installed rendering runtime; no installation or original-environment changes.
 decode=output/"decoded"
 argv=[sys.executable,"-B",str(H/"decode_document.py"),str(source),str(decode)]
 with (output/"decoder.stdout.log").open("x",encoding="utf-8") as out,(output/"decoder.stderr.log").open("x",encoding="utf-8") as err:
  child=subprocess.run(argv,cwd=ROOT,stdout=out,stderr=err)
 if child.returncode:raise ValueError("DOCUMENT_DECODE_REJECTED; SEE PRESERVED DECODER LOG")
 doc=read(decode/"DECODE.json");pages=[];models=None;detector=None
 original_copy=output/("ORIGINAL"+source.suffix.lower());original_copy.write_bytes(source.read_bytes())
 for page in doc["pages"]:
  folder=output/("page_%03d"%page["page"]);folder.mkdir(exist_ok=False)
  with Image.open(page["image"]) as im:image=im.convert("RGB")
  w,h=image.size;vectors={"regions":[],"conflicts":[],"unresolved":[]}
  if source.suffix.lower()==".svg":vectors=vector_regions(source,w,h)
  regions=vectors["regions"];indoor=[o for o in regions if o["semantic_class"]=="indoor_region"];outdoor=[o for o in regions if o["semantic_class"]=="outdoor_region"]
  empty=float(np.array(image.convert("L"),np.float32).std())<1.
  blocked=bool(vectors["conflicts"]) or empty
  supported_structure=request.route=="indoor" or request.route=="hybrid" and bool(indoor) and bool(outdoor) and not blocked
  if request.route=="outdoor":supported_structure=False
  candidates=[];calls={"unet":0,"opening_yolo":0};extraction=[]
  if supported_structure and not blocked:
   if models is None:
    p=ROOT/"PP1_STAGE_E_EVENT_LAYOUT_V2/backend/venue_unet_inference_v2.py";sp=importlib.util.spec_from_file_location("native_unet_loader",p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
    models=m.load_model(PRIVATE_MODELS/"unet-v3.pt",torch.device("cpu"))
    from ultralytics import YOLO
    detector=YOLO(str(PRIVATE_MODELS/"opening-yolo-v3.pt"))
   x,_,transform=letterbox(image,Image.new("L",image.size,255));a=np.array(x,np.float32)/255
   a=(a-np.array([.485,.456,.406],np.float32))/np.array([.229,.224,.225],np.float32)
   with torch.inference_mode():prob=models(torch.from_numpy(a.transpose(2,0,1).copy()).unsqueeze(0)).softmax(1)[0].numpy()
   raw=prob.argmax(0).astype(np.uint8);accepted=np.where(prob.max(0)>=.7,raw+1,0).astype(np.uint8)
   left,top=transform["offset_xy"];nw,nh=transform["resized_wh"]
   cropped=accepted[top:top+nh,left:left+nw].copy()
   if request.route=="hybrid":
    roi=Image.new("L",image.size,0);d=ImageDraw.Draw(roi)
    for r in indoor:
     for ring in r["geometry"]["coordinates"][:1]:d.polygon([tuple(p) for p in ring],fill=255)
    keep=np.array(roi.resize((nw,nh),Image.Resampling.NEAREST))>0;cropped[~keep]=0
   geompath=ROOT/"PP1_READINESS_20261022/10_FINAL_VERIFICATION/FUNCTIONAL_V2/prediction_bridge_v3.py"
   fn=next(n for n in ast.parse(geompath.read_text(encoding="utf-8")).body if isinstance(n,ast.FunctionDef) and n.name=="exact_components")
   namespace=dict(np=np,cv2=cv2,box=box,mapping=mapping,unary_union=unary_union,scale=scale)
   exec(compile(ast.Module(body=[fn],type_ignores=[]),str(geompath),"exec"),namespace)
   candidates,extraction=namespace["exact_components"](cropped,w,h)
   for ob in candidates:ob["inference_state"]="PREDICTED";ob["confidence_note"]="Uncalibrated pixelsoftmax0.7; no physical confidence"
   Image.fromarray(raw).save(folder/"UNET_MASK_512.png");Image.fromarray(cropped).save(folder/"ACCEPTED_CONTENT_MASK.png")
   colors=np.array([[66,185,100],[215,55,60],[245,167,40],[55,125,240]],np.uint8)
   display=np.array(Image.fromarray(raw[top:top+nh,left:left+nw]).resize((w,h),Image.Resampling.NEAREST))
   Image.blend(image,Image.fromarray(colors[display]),.35).save(folder/"UNET_OVERLAY.png")
   prediction=detector.predict(str(page["image"]),imgsz=960,conf=.25,iou=.7,max_det=300,device="cpu",verbose=False,save=False)[0]
   for j,(b,c,score) in enumerate(zip(prediction.boxes.xyxy.tolist(),prediction.boxes.cls.tolist(),prediction.boxes.conf.tolist())):
    a,b1,c1,d1=b
    candidates.append({"id":"OPENING_YOLO_%04d"%j,"semantic_class":detector.names[int(c)],"status":"uncertain","inference_state":"PREDICTED","confidence":score,"model":"YOLOv8n nativeopening2class","source_kind":"actual_trained_model_prediction","planner_confirmed":False,"relocation_allowed":False,"geometry":{"type":"Polygon","coordinates":[[[a,b1],[c1,b1],[c1,d1],[a,d1],[a,b1]]],"unit":"original_image_pixels","kind":"symbol_bbox_not_physical_footprint"}})
   Image.fromarray(prediction.plot()[:,:,::-1]).save(folder/"OPENING_YOLO_OVERLAY.png")
   calls={"unet":1,"opening_yolo":1}
  proposals=[]  # V3 closed contours are deliberately not admitted as semantic outdoor candidates.
  from outdoor_evidence import recognize_outdoor
  outdoors=recognize_outdoor(source) if request.route in {"outdoor","hybrid"} and source.suffix.lower() in {".png",".jpg",".jpeg"} else {"status":"ABSTAIN_NO_QUALIFIED_OUTDOOR_RECOGNIZER","recognized_candidates":[],"boundary":None}
  candidates.extend(outdoors["recognized_candidates"])
  object_report={"status":"EXPERIMENTAL_DISABLED_PENDING_EXHAUSTIVE_LABEL_REVIEW","calls":0,"validated_event_classes":[]}
  if request.experimental_objects and supported_structure and not blocked:
   raise ValueError("EXPERIMENTAL_EVENT_OBJECT_AND_CHAIR_MODELS_ARE_NOT_ENABLED_IN_PORTABLE_KNOX_FLOW")
  overlay=image.copy();draw=ImageDraw.Draw(overlay)
  for r in regions+proposals:
   for ring in r["geometry"]["coordinates"][:1]:draw.line([tuple(pt) for pt in ring],fill="magenta" if r["status"]=="DERIVED_FROM_VECTOR" else "orange",width=3)
  overlay.save(folder/"GEOMETRY_PROPOSALS.png")
  sourceblock={"path":page["image"],"sha256":sha(page["image"]),"width_pixels":w,"height_pixels":h,"domain":request.domain}
  modelids={"unet_checkpoint_sha256":sha(V3/"unet/best_native_unet.pt"),"opening_yolo_checkpoint_sha256":read(V3/"symbols/TRAINING_RESULT.json")["sha256"]} if supported_structure and not blocked else {}
  for candidate in candidates:
   candidate.update(source_sha256=sourceblock["sha256"],source_id="page_%03d"%page["page"],original_document_sha256=original_sha,metric_geometry=None)
   candidate.setdefault("inventory_authority","UNKNOWN");candidate.setdefault("planner_confirmed",False);candidate.setdefault("relocation_allowed",False)
  bundle={"schema":"IMAGE_SPACE_TWIN_CANDIDATE_V2","source":sourceblock,"models":modelids,"objects":candidates,"boundary":None,"metres_per_pixel":None,"planner_reviewed":False,"optimization_ready":False}
  result={"page":page["page"],"route":request.route,"actual_model_calls":calls,"candidate_bundle":bundle,"vector_source_regions":vectors,"algorithmic_region_proposals":proposals,"extraction_checks":extraction,
   "mixed_region_status":"SOURCE_SEMANTIC_VECTOR_REGIONS_WITH_OVERLAP_CHECK" if request.route=="hybrid" and indoor and outdoor and not blocked else "CONFLICT" if blocked else "UNSUPPORTED_OR_PENDING",
   "existing_12_event_object_detection":object_report,"outdoor_semantic_branch":outdoors,
   "unsupported_features":["inferred_true_entrances","outdoor_obstacle_semantics","automatic_covered_open_restricted_zones","metric_scale","authenticated_review","DWG_DXF"],
   "status":"rejected_empty_drawing" if empty else "rejected_conflicting_regions" if blocked else "review_required","optimization_ready":False,"document_transform":page}
  with (folder/"RESULT.json").open("x",encoding="utf-8") as f:json.dump(result,f,indent=2,allow_nan=False)
  pending={"state":"PENDING_REVIEW","source":sourceblock,"original_document_sha256":original_sha,"boundary_px":None,"objects":None,"calibration_controls":None,"reviewer":None,"approval":False,
   "instructions":"Supply genuine reviewed geometry, two distinct consistent known-distance controls, source-bound evidence and explicit review through unchanged frozen TwinReview contract. Decoding pixels/PDFpoints do not establish metres. Proposals are not reviewed authority."}
  with (folder/"PENDING_REVIEW.json").open("x",encoding="utf-8") as f:json.dump(pending,f,indent=2)
  pages.append(result)
 if sha(source)!=original_sha:raise ValueError("SOURCE_CHANGED")
 result={"adapter_version":"4.0.0_EXPERIMENTAL","original_document":{"path":str(source),"sha256":original_sha,"copied_source_sha256":sha(original_copy)},"decoder":doc,"request":request.model_dump(),"pages":pages,"metric_twin_ready":False,"approved":False}
 with (output/"UPLOAD_RESULT.json").open("x",encoding="utf-8") as f:json.dump(result,f,indent=2,allow_nan=False)
 return result
if __name__=="__main__":
 import argparse,platform
 platform.uname();parser=argparse.ArgumentParser();parser.add_argument("--source",required=True);parser.add_argument("--route",required=True,choices=["indoor","outdoor","hybrid"]);parser.add_argument("--out",required=True,type=Path);parser.add_argument("--experimental-objects",action="store_true");a=parser.parse_args()
 events=guard()
 result=infer(UploadRequest(path=a.source,route=a.route,experimental_objects=a.experimental_objects),a.out)
 save(a.out.resolve().relative_to(H)/"GUARD.json",events)
 print("Processed",len(result["pages"]),"pages; metric_twin_ready=False")
