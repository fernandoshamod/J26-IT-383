"""Conservative source-aware outdoor branch; no unlabelled rectangle is a site boundary."""
from common import *
import numpy as np,cv2
from PIL import Image
from shapely.geometry import Polygon,mapping,shape,box
from shapely.ops import unary_union
def polygons(mask):
 # Exact pixel-cell union preserves fragmented native annotation pixels and holes.
 # No smoothing, morphology, contour repair, invented rectangle or component pruning.
 runs=[]
 for y in np.flatnonzero(mask.any(axis=1)):
  d=np.diff(np.pad(mask[y].astype('int8'),(1,1)))
  for a,b in zip(np.where(d==1)[0],np.where(d==-1)[0]):runs.append(box(int(a),int(y),int(b),int(y+1)))
 if not runs:return []
 g=unary_union(runs)
 if not g.is_valid:raise ValueError('INVALID_PIXEL_CELL_UNION')
 return [mapping(g)]  # MultiPolygon may contain fragments; NOT a count of physical entrances.
def recognize_outdoor(source):
 """Only known native pre-annotated source ingestion; not raster recognition accuracy."""
 p=Path(source).resolve();registry=read(H/'outdoor/SOURCE_REGISTRY.json')
 entry=next((r for r in registry if r['layout_sha256']==sha(p)),None)
 if entry is None:return {'status':'ABSTAIN_SEMANTIC_LABELS_UNAVAILABLE','recognized_candidates':[], 'boundary':None,'unsupported_classes':['site_boundary','usable_zone','open_air_zone','covered_zone','entrance','obstacle','restricted_zone'],'reason':'No qualified raster model or reviewed source-semantic registry. Frames/legends/closed contours are not admitted as boundaries.','optimization_ready':False}
 with Image.open(p) as im:a=np.array(im.convert('RGB'))
 # SCUT publisher Fig2 explicitly defines yellow=entrance. Other classes deliberately not guessed.
 mask=(a==[255,255,0]).all(2);items=[]
 for i,g in enumerate(polygons(mask)):
  items.append({'id':'SCUT_DECLARED_ENTRANCE_%03d'%i,'semantic_class':'entrance','geometry':dict(g,unit='original_image_pixels'),
   'source_kind':'PUBLISHED_ANNOTATION_IMPORT_NOT_LEARNED_PREDICTION','inference_state':'SOURCE_ENCODED_UNREVIEWED','status':'uncertain','planner_confirmed':False,'relocation_allowed':False,
   'source_sha256':entry['layout_sha256'],'source_id':entry['id'],'source_annotation_evidence':entry['legend_sha256'],'model':None,'inventory_authority':'UNKNOWN','metric_geometry':None})
 return {'status':'NATIVE_ANNOTATION_IMPORT_ONLY','recognized_candidates':items,'boundary':None,'source_profile':'SCUT-AutoALP native coloured layout TARGET, not original site drawing',
  'unsupported_classes':['site_boundary','usable_zone','open_air_zone','covered_zone','obstacle','restricted_zone'],'optimization_ready':False,
  'reason':'Only publisher-encoded entrance regions imported. Campus site-range mask is a separate annotation, not evidence that arbitrary raster recognition works. No legal property/usable/roof/obstacle equivalence is inferred.'}
