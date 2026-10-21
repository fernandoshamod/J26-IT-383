"""Create isolated V4 adapter from preserved V3 source; no original edit/import side effects."""
from common import *
V=H.parent/'PP1_FLOORPLAN_AI_DEVELOPMENT_V3'
s=(V/'upload_inference.py').read_text(encoding='utf-8')
s=s.replace('class UploadRequest(BaseModel):','V3=H.parent/"PP1_FLOORPLAN_AI_DEVELOPMENT_V3"\nclass UploadRequest(BaseModel):')
s=s.replace('path:str\n route:', 'path:str\n experimental_objects:bool=False\n route:')
s=s.replace('H/"unet/best_native_unet.pt"','V3/"unet/best_native_unet.pt"').replace('H/"symbols/TRAINING_RESULT.json"','V3/"symbols/TRAINING_RESULT.json"')
s=s.replace('proposals=raster_proposals(image) if request.route in {"outdoor","hybrid"} else []', '''proposals=[]  # V3 closed contours are deliberately not admitted as semantic outdoor candidates.
  from outdoor_evidence import recognize_outdoor
  outdoors=recognize_outdoor(source) if request.route in {"outdoor","hybrid"} and source.suffix.lower() in {".png",".jpg",".jpeg"} else {"status":"ABSTAIN_NO_QUALIFIED_OUTDOOR_RECOGNIZER","recognized_candidates":[],"boundary":None}
  candidates.extend(outdoors["recognized_candidates"])
  object_report={"status":"EXPERIMENTAL_DISABLED_PENDING_EXHAUSTIVE_LABEL_REVIEW","calls":0,"validated_event_classes":[]}
  if request.experimental_objects and supported_structure and not blocked:
   from ultralytics import YOLO
   checkpoint=read(H/"objects_v2/CHECKPOINT_FREEZE.json")
   if sha(checkpoint["checkpoint"])!=checkpoint["sha256"]:raise ValueError("OBJECT_CHECKPOINT_CHANGED")
   objmodel=YOLO(checkpoint["checkpoint"])
   objpred=objmodel.predict(str(page["image"]),imgsz=640,conf=.25,iou=.7,max_det=300,device="cpu",verbose=False,save=False)[0]
   for j,(b,c,score) in enumerate(zip(objpred.boxes.xyxy.tolist(),objpred.boxes.cls.tolist(),objpred.boxes.conf.tolist())):
    if int(c)!=0:raise ValueError("UNEXPECTED_OBJECT_CLASS")
    a,b1,c1,d1=b
    candidates.append({"id":"EXPERIMENTAL_CHAIR_%04d"%j,"semantic_class":"chair","frozen_event_class_id":2,"status":"uncertain","inference_state":"PREDICTED_EXPERIMENTAL_NOT_STOCK_QUALIFIED","confidence":score,"model_sha256":checkpoint["sha256"],"source_kind":"actual_local_model_prediction","planner_confirmed":False,"relocation_allowed":False,"inventory_authority":"UNKNOWN","geometry":{"type":"Polygon","coordinates":[[[a,b1],[c1,b1],[c1,d1],[a,d1],[a,b1]]],"unit":"original_image_pixels","kind":"symbol_bbox_not_physical_footprint"}})
   Image.fromarray(objpred.plot()[:,:,::-1]).save(folder/"EXPERIMENTAL_CHAIR_OVERLAY.png")
   object_report={"status":"EXPERIMENTAL_PUBLISHED_LABEL_PILOT_NOT_STOCK_QUALIFIED","calls":1,"checkpoint_sha256":checkpoint["sha256"],"validated_event_classes":[],"published_label_pilot_class":"chair","remaining11":"NOT_VALIDATED"}''')
s=s.replace('bundle={"schema":', '''for candidate in candidates:
   candidate.update(source_sha256=sourceblock["sha256"],source_id="page_%03d"%page["page"],original_document_sha256=original_sha,metric_geometry=None)
   candidate.setdefault("inventory_authority","UNKNOWN");candidate.setdefault("planner_confirmed",False);candidate.setdefault("relocation_allowed",False)
  bundle={"schema":''')
s=s.replace('"existing_12_event_object_detection":"UNSUPPORTED_ON_REAL_FLOORPLANS;V2_CONTROLLED_MODEL_PRESERVED",','"existing_12_event_object_detection":object_report,"outdoor_semantic_branch":outdoors,')
s=s.replace('"adapter_version":"3.0.0"','"adapter_version":"4.0.0_EXPERIMENTAL"')
s=s.replace('parser.add_argument("--out",required=True,type=Path);a=parser.parse_args()', 'parser.add_argument("--out",required=True,type=Path);parser.add_argument("--experimental-objects",action="store_true");a=parser.parse_args()')
s=s.replace('UploadRequest(path=a.source,route=a.route)','UploadRequest(path=a.source,route=a.route,experimental_objects=a.experimental_objects)')
(H/'upload_inference.py').write_text(s,encoding='utf-8')
save('ADAPTER_DERIVATION.json',{'base':str(V/'upload_inference.py'),'base_sha256':sha(V/'upload_inference.py'),'isolated_sha256':sha(H/'upload_inference.py'),'changes':['Read-only V3 model paths','Explicit experimental chair opt-in','No outdoor unlabelled contour admission','Source-bound published outdoor annotation import only','Every candidate source/document hash, unknown inventory, no metric conversion','No planner/metric gate bypass']})
