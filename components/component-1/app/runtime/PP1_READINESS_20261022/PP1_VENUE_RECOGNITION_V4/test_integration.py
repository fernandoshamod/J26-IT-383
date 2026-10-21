"""Actual versioned input routes; execution PASS is not recognition qualification."""
import platform,traceback
from common import *
platform.uname();events=guard()
from upload_inference import infer,UploadRequest
from PIL import Image,ImageDraw
parts=read(H/'objects_v2/SPLITS.json');V=H.parent/'PP1_FLOORPLAN_AI_DEVELOPMENT_V3'
# Defined by source annotations before predictions, never chosen for attractive model output.
positive=next(r for r in parts['test'] if r['annotations']);negative=next(r for r in parts['test'] if not r['annotations'])
control=H/'evidence/ANALYTIC_FRAME_NEGATIVE.png';im=Image.new('RGB',(700,500),'white');d=ImageDraw.Draw(im);d.rectangle((10,10,690,490),outline='black',width=3);d.rectangle((420,300,640,450),outline='black',width=3);d.text((440,330),'LEGEND',fill='black');im.save(control)
cases=[('INDOOR_PUBLISHED_CHAIR',positive['source'],'indoor',True),('INDOOR_PUBLISHED_NO_CHAIR_LABELS',negative['source'],'indoor',True),
 ('INDOOR_DEFAULT_NO_EXPERIMENTAL',positive['source'],'indoor',False),('NPS_REAL_MAP_LEGENDS',str(V/'acquired/NPS_PINES_SITE_PLAN.jpg'),'outdoor',False),
 ('SCUT_NATIVE_ANNOTATION_IMPORT',read(H/'outdoor/SOURCE_REGISTRY.json')[0]['layout'],'outdoor',False),('ANALYTIC_FRAME_NEGATIVE',str(control),'outdoor',False),
 ('NATIVE_VECTOR_HYBRID',str(ROOT/'01_DATASET_DOWNLOADS/CubiCasa5K/cubicasa5k/cubicasa5k/high_quality_architectural/13040/model.svg'),'hybrid',False)]
save('evidence/INTEGRATION_CASES_PREDECLARED_FINAL.json',{'cases':cases,'selection':'Same cases as initial run; corrected outdoor converter; first heldout published-chair-positive and first label-negative in frozen split order; native hybrid previously observed V3; no recognition-generalization claim'})
results=[]
for name,source,route,experimental in cases:
 try:
  out=H/'integration_final'/name
  result=infer(UploadRequest(path=source,route=route,experimental_objects=experimental),out)
  assert result['metric_twin_ready'] is False and result['approved'] is False
  page=result['pages'][0];bundle=page['candidate_bundle'];assert bundle['boundary'] is None and bundle['metres_per_pixel'] is None
  assert all(c['planner_confirmed'] is False and c['relocation_allowed'] is False and c['metric_geometry'] is None and c['source_sha256']==bundle['source']['sha256'] for c in bundle['objects'])
  if name=='INDOOR_DEFAULT_NO_EXPERIMENTAL':assert page['existing_12_event_object_detection']['calls']==0
  if route=='outdoor':assert page['actual_model_calls']=={'unet':0,'opening_yolo':0} and page['algorithmic_region_proposals']==[]
  if name in ['NPS_REAL_MAP_LEGENDS','ANALYTIC_FRAME_NEGATIVE']:assert bundle['objects']==[]
  if name=='SCUT_NATIVE_ANNOTATION_IMPORT':assert len(bundle['objects'])>0
  if experimental:assert page['existing_12_event_object_detection']['calls']==1
  results.append({'case':name,'execution_status':'PASS','recognition_qualified':False,'source_sha256':result['original_document']['sha256'],'actual_calls':page['actual_model_calls'],'object_pilot':page['existing_12_event_object_detection'],'candidates':len(bundle['objects']),'outdoor':page['outdoor_semantic_branch']['status'],'optimization_ready':False})
 except BaseException:
  results.append({'case':name,'execution_status':'FAILED','traceback':traceback.format_exc()});print(name,'FAILED',flush=True)
 print(name,results[-1]['execution_status'],flush=True)
# Do not manufacture missing calibration/review. Invoke unchanged gate with missing input.
from review_handoff import validate_metric_review
try:validate_metric_review({'source':{}},{})
except Exception as e:results.append({'case':'FROZEN_METRIC_GATE_MISSING_REVIEW','execution_status':'PASS','rejection_type':type(e).__name__,'detail':str(e)[:2000]})
else:raise AssertionError('Missing review accepted')
save('evidence/INTEGRATION_RESULTS_FINAL.json',{'cases':results,'status':'PASS' if all(r['execution_status']=='PASS' for r in results) else 'FAIL','guard':events,'genuine_metric_twin_or_planner_approvals_created':0})
assert all(r['execution_status']=='PASS' for r in results)
