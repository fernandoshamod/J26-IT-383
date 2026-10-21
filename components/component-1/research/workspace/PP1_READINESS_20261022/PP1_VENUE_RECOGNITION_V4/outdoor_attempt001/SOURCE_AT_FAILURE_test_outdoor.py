"""Native annotation conversion checks and real legend abstention; no recognition-accuracy fiction."""
from common import *
import numpy as np,cv2
from PIL import Image,ImageDraw
from outdoor_evidence import recognize_outdoor
events=guard();reg=read(H/'outdoor/SOURCE_REGISTRY.json');results=[]
# Predeclare first ten publisher IDs before any prediction; this is an import QA set, NOT an ML test split.
for r in reg[:10]:
 result=recognize_outdoor(r['layout']);im=Image.open(r['layout']).convert('RGB');a=np.array(im);gt=(a==[255,255,0]).all(2)
 replay=np.zeros(gt.shape,np.uint8);preview=im.copy();draw=ImageDraw.Draw(preview)
 for c in result['recognized_candidates']:
  rings=c['geometry']['coordinates'];cv2.fillPoly(replay,[np.array(rings[0],np.int32)],1)
  for ring in rings[1:]:cv2.fillPoly(replay,[np.array(ring,np.int32)],0)
  draw.line([tuple(x) for x in rings[0]],fill='red',width=4)
 inter=int((gt & (replay>0)).sum());union=int((gt | (replay>0)).sum());score=inter/union if union else None
 out=H/'outdoor/native_annotation_import'/r['id'];out.mkdir(parents=True,exist_ok=False)
 preview.thumbnail((1400,1400));preview.save(out/'DECLARED_ENTRANCE_IMPORT_OVERLAY.png');Image.fromarray(replay*255).save(out/'IMPORTED_ENTRANCE_MASK.png')
 save(out.relative_to(H)/'RESULT.json',result)
 results.append({'source':r['layout'],'source_sha256':r['layout_sha256'],'kind':'PUBLISHED_ANNOTATION_IMPORT_QA_NOT_HELD_OUT_RECOGNITION','components':len(result['recognized_candidates']),'native_entrance_support':int(gt.sum()),'converted_mask_intersection':inter,'union':union,'conversion_iou':score,'optimization_ready':result['optimization_ready']})
 assert result['boundary'] is None and not result['optimization_ready']
V=H.parent/'PP1_FLOORPLAN_AI_DEVELOPMENT_V3';neg=recognize_outdoor(V/'acquired/NPS_PINES_SITE_PLAN.jpg')
assert neg['recognized_candidates']==[] and neg['boundary'] is None
results.append({'source':str(V/'acquired/NPS_PINES_SITE_PLAN.jpg'),'kind':'REAL_DRAWING_WITH_LEGENDS_ABSTENTION','result':neg,'verified_full_site_boundary_ground_truth':False})
save('outdoor/CONVERSION_AND_ABSTENTION_TESTS.json',{'status':'PASS_EXECUTION_AND_ABSTENTION','records':results,'true_site_boundary_recognition_iou':None,'true_site_boundary_positive_coverage':0,'seven_class_recognition_metrics':'NOT_EVALUATED','native_conversion_metrics_are_not':'Learned/general raster-site-plan recognition accuracy','guard':events})
print(len(results),'conversion/abstention cases; zero qualified true-boundary recognition positives')
