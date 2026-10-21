"""Versioned replacement for frozen understanding.understand, using actual V3/V4 code."""
from common import *
import importlib.util,shutil,threading,os
LOCK=threading.Lock()
def backend_modules():
 p=str(H.parent/'PP1_EXECUTABLE_V1')
 if p not in sys.path:sys.path.append(p)
def understand(source,out,route='indoor',experimental_chair=False):
 from model_registry import verify_hashes
 identities=verify_hashes();backend_modules()
 from support import digest
 from responses import AnalysisReceipt
 # The dependency's algorithms stay unchanged; only common.H and output configuration resolve here.
 V=H.parent/'PP1_VENUE_RECOGNITION_V4'
 if str(V) not in sys.path:sys.path.append(str(V))
 spec=importlib.util.spec_from_file_location('component1_updated_perception',V/'upload_inference.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 out=Path(out).resolve();state=Path(os.environ.get('PP1_RUN_STATE',Path(os.environ.get('PP1_RUNTIME_STATE',H.parents[2]/'runtime-state'))/'runs'/'manual')).resolve()
 if not out.is_relative_to(state) or out.exists():raise ValueError('USE_NEW_PORTABLE_RUNTIME_STATE_OUTPUT_DIRECTORY')
 out.mkdir(parents=True)
 import torch
 loads=[];forwards=[];original_load=torch.load
 def traced_load(f,*args,**kwargs):
  if isinstance(f,(str,Path)):
   p=Path(f).resolve();loads.append({'path':str(p),'sha256':sha(p),'purpose':'ACTUAL_INFERENCE_LOAD'})
  return original_load(f,*args,**kwargs)
 def forward(m,inputs,output):
  if type(m).__name__=='Unet':forwards.append({'module':type(m).__name__,'input_shape':list(inputs[0].shape),'output_shape':list(output.shape)})
 with LOCK:
  torch.load=traced_load;handle=torch.nn.modules.module.register_module_forward_hook(forward)
  try:result=module.infer(module.UploadRequest(path=str(Path(source).resolve()),route=route,experimental_objects=experimental_chair),out/'RAW_PERCEPTION')
  finally:torch.load=original_load;handle.remove()
 for page in result['pages']:
  bundle=page['candidate_bundle'];bundle['models'].update({k+'_checkpoint_sha256':v['sha256'] for k,v in identities.items() if k in ['unet','opening_yolo'] or k=='experimental_chair' and experimental_chair})
  for ob in bundle['objects']:ob['mobility_classification']='unknown';ob['inventory_authority']='UNKNOWN_DRAWING_CONTENT_NOT_VERIFIED_STOCK'
  assert bundle['optimization_ready'] is False and bundle['metres_per_pixel'] is None
 # Existing HTTP Analyze is raster/single-page. CLI multi-page uses one normalized bundle per page.
 receipts=[]
 for page in result['pages']:
  dest=out if len(result['pages'])==1 else out/('PAGE_%03d'%page['page']);dest.mkdir(exist_ok=True)
  bundle=page['candidate_bundle'];src=bundle['source']
  template={'contract_id':'COMPONENT1_REVIEWED_TWIN_V1','venue_id':'REQUIRES_REVIEWER_INPUT','venue_version':1,'source':src,'candidate_bundle_sha256':digest(bundle),
   'calibration':{'method':'isotropic_two_point_controls','controls':[{'point_a_px':None,'point_b_px':None,'known_distance_m':None,'evidence_ref':None},{'point_a_px':None,'point_b_px':None,'known_distance_m':None,'evidence_ref':None}],'metric_origin_px':None},
   'boundary_px':None,'objects':[],'review':{'status':'pending','reviewer_id':None,'evidence_ref':None,'scope':'EXTERNAL_RESEARCH_REVIEW','geometry_confirmed':False,'metric_dimensions_confirmed':False},'evidence_artifacts':[]}
  report={'adapter_version':'COMPONENT1_UPDATED_MODEL_INTEGRATION_V1','original_document':result['original_document'],'page':page['page'],'source':src,'actual_model_calls':page['actual_model_calls'],
   'event_objects':page['existing_12_event_object_detection'],'outdoor_semantics':page['outdoor_semantic_branch'],'models':identities,'actual_checkpoint_loads':loads,'actual_unet_forwards':forwards,
   'structural_class_mapping':{'0':'room_region','1':'wall','2':'door','3':'window'},'opening_class_mapping':{'0':'door','1':'window'},'coordinate_frame':'original decoded page pixels; geometry has no established metres',
   'inference_algorithm_source':str(V/'upload_inference.py'),'inference_algorithm_sha256':sha(V/'upload_inference.py'),'ground_truth_accuracy_evaluated':False,'controlled_model_inferred_on_real_source':False}
  report['structural_candidates']=sum(c.get('model')=='U-Net ResNet18' for c in bundle['objects'])
  report['yolo_candidates']=sum(c['id'].startswith(('OPENING_YOLO_','EXPERIMENTAL_CHAIR_')) for c in bundle['objects'])
  report['yolo_candidate_semantics']='Opening door/window symbols plus explicitly enabled experimental chairs; not twelve-class verified venue stock.'
  gate={'accepted':False,'status':'EXPECTED_PENDING','missing':['genuine reviewed usable boundary','two distinct consistent known-distance calibration controls and origin','source-bound measurement/review/object-decision evidence files','reviewed fixed objects and exactly one reviewed stage required by frozen Twin contract','explicit external review; no authenticated identity is claimed'],
   'optimizer_evaluations':0,'synthetic_geometry_substituted':False,'real_venue_positive_path':'NOT_EXECUTED_NO_GENUINE_REVIEW_INPUT'}
  for name,value in [('CANDIDATE_BUNDLE.json',bundle),('MODEL_OUTPUT_REPORT.json',report),('REVIEW_CALIBRATION_TEMPLATE_PENDING.json',template),('REVIEW_GATE_STATUS.json',gate),('ACTUAL_MODEL_TRACE.json',{'loads':loads,'unet_forwards':forwards})]:save(dest.relative_to(H)/name,value)
  raw=out/'RAW_PERCEPTION'/('page_%03d'%page['page'])
  for p in raw.glob('*.png'):shutil.copyfile(p,dest/p.name)
  # Preserve existing frontend artifact names and counts without changing its code.
  from PIL import Image,ImageDraw
  with Image.open(src['path']) as image:preview=image.convert('RGB');detected=image.convert('RGB')
  draw=ImageDraw.Draw(preview);ddraw=ImageDraw.Draw(detected)
  for ob in bundle['objects']:
   g=ob['geometry'];polys=g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]
   is_yolo=ob['id'].startswith(('OPENING_YOLO_','EXPERIMENTAL_CHAIR_'))
   for poly in polys:
    for ring in poly:
     points=[tuple(p) for p in ring];draw.line(points+[points[0]],fill='red' if is_yolo else 'blue',width=2)
     if is_yolo:ddraw.line(points+[points[0]],fill='red',width=2)
  preview.save(dest/'GEOMETRY_CANDIDATES.png');detected.save(dest/'YOLO_OVERLAY.png')
  receipt={'analysis_id':out.name,'status':'review_required','candidate_bundle':bundle,'pending_review_template':template,'model_report':report,'gate':gate,'artifacts':{}}
  receipts.append(receipt)
 save(out.relative_to(H)/'DOCUMENT_RESULT.json',{'receipts':receipts,'source_document':result['original_document'],'metric_twin_ready':False,'controlled_research_path_is_separate':True})
 return receipts
