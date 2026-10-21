"""Native annotation conversion checks and real legend abstention; no recognition-accuracy fiction."""
from common import *
import numpy as np,cv2
from PIL import Image,ImageDraw
from outdoor_evidence import recognize_outdoor
from shapely.geometry import shape
from shapely import contains_xy
events=guard();reg=read(H/'outdoor/SOURCE_REGISTRY.json');results=[]
# Predeclare first ten publisher IDs before any prediction; this is an import QA set, NOT an ML test split.
for r in reg[:10]:
 result=recognize_outdoor(r['layout']);im=Image.open(r['layout']).convert('RGB');a=np.array(im);gt=(a==[255,255,0]).all(2)
 replay=np.zeros(gt.shape,np.uint8);preview=im.copy();draw=ImageDraw.Draw(preview)
 for c in result['recognized_candidates']:
  g=shape(c['geometry']);assert g.is_valid
  lo0,lo1,hi0,hi1=map(int,g.bounds);ys,xs=np.mgrid[lo1:hi1,lo0:hi0]
  replay[lo1:hi1,lo0:hi0] |= contains_xy(g,xs+.5,ys+.5).astype('uint8')
  pieces=list(g.geoms) if g.geom_type=='MultiPolygon' else [g]
  for piece in pieces:draw.line(list(piece.exterior.coords),fill='red',width=2)
 inter=int((gt & (replay>0)).sum());union=int((gt | (replay>0)).sum());score=inter/union if union else None
 out=H/'outdoor/native_annotation_import'/r['id'];out.mkdir(parents=True,exist_ok=False)
 preview.thumbnail((1400,1400));preview.save(out/'DECLARED_ENTRANCE_IMPORT_OVERLAY.png');Image.fromarray(replay*255).save(out/'IMPORTED_ENTRANCE_MASK.png')
 save(out.relative_to(H)/'RESULT.json',result)
 results.append({'source':r['layout'],'source_sha256':r['layout_sha256'],'kind':'PUBLISHED_ANNOTATION_IMPORT_QA_NOT_HELD_OUT_RECOGNITION','components':len(result['recognized_candidates']),'native_entrance_support':int(gt.sum()),'converted_mask_intersection':inter,'union':union,'conversion_iou':score,'optimization_ready':result['optimization_ready']})
 assert result['boundary'] is None and not result['optimization_ready']
 assert gt.sum()>0 and score==1.,'POSITIVE_NATIVE_ANNOTATION_WAS_LOST'
V=H.parent/'PP1_FLOORPLAN_AI_DEVELOPMENT_V3';neg=recognize_outdoor(V/'acquired/NPS_PINES_SITE_PLAN.jpg')
assert neg['recognized_candidates']==[] and neg['boundary'] is None
results.append({'source':str(V/'acquired/NPS_PINES_SITE_PLAN.jpg'),'kind':'REAL_DRAWING_WITH_LEGENDS_ABSTENTION','result':neg,'verified_full_site_boundary_ground_truth':False})
save('outdoor/CONVERSION_AND_ABSTENTION_TESTS.json',{'status':'PASS_NATIVE_CONVERSION_AND_ABSTENTION','records':results,'true_site_boundary_recognition_iou':None,'true_site_boundary_positive_coverage':0,'seven_class_recognition_metrics':'NOT_EVALUATED','native_conversion_metrics_are_not':'Learned/general raster-site-plan recognition accuracy','native_target_definition':'Exact publisher nominal yellow core pixels only; compression/antialias fringe excluded, not harmonized physical entrance truth','previous_failure':'outdoor_attempt001: contour holes invalid caused positive omission; old execution-only check was insufficient. Exact pixel-cell union and mandatory positive-support/IoU checks added.','guard':events})
print(len(results),'conversion/abstention cases; zero qualified true-boundary recognition positives')
