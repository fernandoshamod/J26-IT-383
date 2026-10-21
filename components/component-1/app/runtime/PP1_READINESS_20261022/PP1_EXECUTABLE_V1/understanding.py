"""Actual trained models -> source-bound candidates + pending external review.
No calibration, usable boundary, venue type, permissions or approval is inferred.
"""
import importlib.util,sys
from pathlib import Path
from support import ROOT,FUNCTIONAL,digest,filehash,save
def understand(image_path,out):
    import numpy as np,torch
    from PIL import Image,ImageDraw
    out=Path(out);out.mkdir(parents=True,exist_ok=False);image_path=Path(image_path).resolve()
    if not image_path.is_relative_to(ROOT.resolve()):raise ValueError('SOURCE_OUTSIDE_WORKSPACE')
    initial_source_sha256=filehash(image_path)
    def load(path,name):
        spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
    infer=load(ROOT/'PP1_STAGE_E_EVENT_LAYOUT_V2/backend/venue_unet_inference_v2.py','unet_actual');sys.path.insert(0,str(FUNCTIONAL));extractor=load(FUNCTIONAL/'prediction_bridge_v3.py','exact_geometry_reused')
    cp=ROOT/'02_GENERATED_RESEARCH_DATA/STAGE_B_PP1_BASELINE/best_unet_resnet18.pt';device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');model=infer.load_model(cp,device);original=infer.load_image(image_path);w,h=original.size
    rgb=np.array(original.resize((512,512),Image.Resampling.BILINEAR),np.float32)/255;rgb=(rgb-np.array([.485,.456,.406],np.float32))/np.array([.229,.224,.225],np.float32)
    with torch.inference_mode():prob=model(torch.from_numpy(rgb.transpose(2,0,1).copy()).unsqueeze(0).to(device)).softmax(1)[0].cpu().numpy()
    raw=prob.argmax(0).astype(np.uint8);accepted=np.where(prob.max(0)>=.7,raw+1,0).astype(np.uint8);structures,checks=extractor.exact_components(accepted,w,h);full=np.array(Image.fromarray(raw).resize((w,h),Image.Resampling.NEAREST));Image.fromarray(raw).save(out/'UNET_MODEL_MASK.png');Image.fromarray(full).save(out/'UNET_ORIGINAL_MASK.png');Image.fromarray(accepted).save(out/'UNET_ACCEPTED_LABELS.png');Image.blend(original,Image.fromarray(infer.COLORS[full]),.35).save(out/'UNET_OVERLAY.png')
    from ultralytics import YOLO
    ycp=ROOT/'02_GENERATED_RESEARCH_DATA/STAGE_C_OBJECTS/C3_22_PP1_PRETRAINED_CONTROLLED_PILOT_V1/yolov8n_v3_960_pretrained_v1/weights/best.pt';detector=YOLO(str(ycp));result=detector.predict(str(image_path),imgsz=960,conf=.25,iou=.7,max_det=300,device=0 if device.type=='cuda' else 'cpu',save=False,verbose=False)[0];Image.fromarray(result.plot()[:,:,::-1]).save(out/'YOLO_OVERLAY.png');events=[]
    for i,(box,c,confidence) in enumerate(zip(result.boxes.xyxy.cpu().tolist(),result.boxes.cls.cpu().tolist(),result.boxes.conf.cpu().tolist()),1):
        x1,y1,x2,y2=box;events.append(dict(id=f'YOLO_{i:04d}',semantic_class=detector.names[int(c)],source_kind='actual_trained_model_prediction',model='YOLOv8n',confidence=confidence,status='uncertain',planner_confirmed=False,relocation_allowed=False,geometry={'type':'Polygon','coordinates':[[[x1,y1],[x2,y1],[x2,y2],[x1,y2],[x1,y1]]],'unit':'original_image_pixels','kind':'bbox_not_exact_physical_footprint'}))
    if filehash(image_path)!=initial_source_sha256:raise ValueError('SOURCE_CHANGED_DURING_INFERENCE')
    bundle=dict(schema='IMAGE_SPACE_TWIN_CANDIDATE_V2',source={'path':str(image_path),'sha256':initial_source_sha256,'width_pixels':w,'height_pixels':h,'domain':'real_source'},models={'unet_checkpoint_sha256':filehash(cp),'yolo_checkpoint_sha256':filehash(ycp)},objects=structures+events,boundary=None,metres_per_pixel=None,planner_reviewed=False,optimization_ready=False,model_to_original_scale_xy=[w/512,h/512],limitations=['Predictions are not independent real-domain accuracy evidence','No background class in U-Net','Detection boxes do not establish physical footprints','No automatic geometry/scale/approval inference'])
    save(out/'YOLO_PREDICTIONS.json',{'source_sha256':initial_source_sha256,'checkpoint_sha256':filehash(ycp),'imgsz':960,'confidence_threshold':.25,'iou_threshold':.7,'max_detections':300,'predictions':events})
    save(out/'CANDIDATE_BUNDLE.json',bundle);save(out/'EXTRACTION_CHECKS.json',checks)
    stats={}
    for label,array in [('model',raw),('original',full)]:
        counts=np.bincount(array.ravel(),minlength=4);stats[label]={'shape':list(array.shape),'counts':counts.tolist(),'percentages':(100*counts/array.size).tolist()}
    save(out/'MODEL_OUTPUT_REPORT.json',{'source_sha256':filehash(image_path),'unet':stats,'structural_candidates':len(structures),'yolo_candidates':len(events),'ground_truth_accuracy_evaluated':False,'device':str(device)})
    template={'contract_id':'COMPONENT1_REVIEWED_TWIN_V1','venue_id':'REQUIRES_REVIEWER_INPUT','venue_version':1,'source':bundle['source'],'candidate_bundle_sha256':digest(bundle),'calibration':{'method':'isotropic_two_point_controls','controls':[{'point_a_px':None,'point_b_px':None,'known_distance_m':None,'evidence_ref':None},{'point_a_px':None,'point_b_px':None,'known_distance_m':None,'evidence_ref':None}],'metric_origin_px':None},'boundary_px':None,'objects':[],'review':{'status':'pending','reviewer_id':None,'evidence_ref':None,'scope':'EXTERNAL_RESEARCH_REVIEW','geometry_confirmed':False,'metric_dimensions_confirmed':False}}
    template['evidence_artifacts']=[]
    save(out/'REVIEW_CALIBRATION_TEMPLATE_PENDING.json',template);save(out/'REVIEW_GATE_STATUS.json',{'accepted':False,'missing':['externally reviewed usable boundary','two distinct known-distance controls','reviewed fixed object polygons and status','reviewer identity/evidence and explicit approval','source-bound hashed evidence artifacts'],'optimizer_evaluations':0,'synthetic_geometry_substituted':False})
    preview=original.copy();draw=ImageDraw.Draw(preview)
    for obj in bundle['objects']:
        polys=obj['geometry']['coordinates'] if obj['geometry']['type']=='MultiPolygon' else [obj['geometry']['coordinates']]
        for poly in polys:
            for ring in poly:
                points=[tuple(p) for p in ring]
                if len(points)>=3:draw.line(points+[points[0]],fill='red' if obj['model']=='YOLOv8n' else 'blue',width=2)
    preview.save(out/'GEOMETRY_CANDIDATES.png');return bundle
