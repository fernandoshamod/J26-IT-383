"""Independent scalar coordinate/identity replay; never calls adapter.convert."""
import math
def verify(receipt,scene):
 t=receipt['metric_twin'];review=t['review_record'];v=scene['venue'];errors=[]
 def require(test,code):
  if not test:errors.append(code)
 s=t['source'];require(v['source']['sha256']==s['sha256'],'SOURCE_HASH')
 require((v['source']['path'],v['source']['width_px'],v['source']['height_px'],v['source']['domain'])==(s['path'],s['width_pixels'],s['height_pixels'],s['domain']),'SOURCE_METADATA')
 require(v['venue_id']==t['venue_id'] and v['version']==t['venue_version'],'VERSION')
 ratios=[]
 for control in review['calibration']['controls']:
  a,b=control['point_a_px'],control['point_b_px'];ratios.append(control['known_distance_m']/math.sqrt((a[0]-b[0])**2+(a[1]-b[1])**2))
 scale=sum(ratios)/len(ratios);origin=review['calibration']['metric_origin_px']
 require(v['origin_px']==origin,'ORIGIN')
 require(v['controls']==[dict(a_px=x['point_a_px'],b_px=x['point_b_px'],distance_m=x['known_distance_m']) for x in review['calibration']['controls']],'CONTROLS')
 def points(a,b):
  # Rings may begin at different vertices; every original vertex must survive.
  if len(a)!=len(b):return False
  unused=list(b)
  for p in a:
   found=next((i for i,q in enumerate(unused) if math.dist(p,q)<1e-8),None)
   if found is None:return False
   unused.pop(found)
  return not unused
 require(points([[(p[0]-origin[0])*scale,(p[1]-origin[1])*scale] for p in review['boundary_px']],v['boundary_m']),'METRIC_BOUNDARY')
 objects={o['instance_id']:o for o in v['existing']};require(len(objects)==len(review['objects']),'OBJECT_COUNT')
 for ob in review['objects']:
  actual=objects.get(ob['object_id']);require(actual is not None,'MISSING_OBJECT')
  if actual:
   require(actual['class_name']==ob['class_name'] and actual['status']==ob['status'] and actual['protected'] and actual['review_status']=='approved','CLASS_LOCK_STATUS')
   require(points([[(p[0]-origin[0])*scale,(p[1]-origin[1])*scale] for p in ob['polygon_px']],actual['footprint_m']),'OBJECT_METRIC_GEOMETRY')
 require(v['review']['reviewer_id']==review['review']['reviewer_id'],'REVIEW_IDENTITY')
 return dict(valid=not errors,errors=errors,objects_replayed=len(objects),scale_m_per_px=scale,tolerance_m=1e-8,coordinate_method='Scalar source pixels minus origin times mean control scale',safety_certified=False)
