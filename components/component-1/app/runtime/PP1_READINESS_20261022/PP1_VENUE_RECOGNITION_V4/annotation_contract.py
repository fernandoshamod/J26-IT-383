"""Local unauthenticated annotation input. Never issues planner/Twin approval."""
from common import sha
from pathlib import Path
import math
from shapely.geometry import shape
EVENT=['bar_counter','buffet','chair','dance_floor','exhibition_booth','podium','rectangular_table','registration_desk','round_table','seating_row','stage','temporary_partition']
OUTDOOR=['site_boundary','usable_zone','open_air_zone','covered_zone','entrance','obstacle','restricted_zone']
def validate_annotation(task,record):
 if record.get('schema')!='SOURCE_BOUND_HUMAN_ANNOTATION_V1':raise ValueError('ANNOTATION_SCHEMA_REQUIRED')
 if record.get('task_id')!=task['task_id'] or record.get('source_sha256')!=task['source_sha256']:raise ValueError('ANNOTATION_SOURCE_BINDING_MISMATCH')
 if sha(task['source_path'])!=task['source_sha256']:raise ValueError('SOURCE_CHANGED')
 if record.get('source_width')!=task['width'] or record.get('source_height')!=task['height']:raise ValueError('DIMENSION_MISMATCH')
 if not isinstance(record.get('reviewer'),str) or not record['reviewer'].strip() or record.get('attested_human_review') is not True:raise ValueError('GENUINE_EXPLICIT_REVIEW_INPUT_REQUIRED')
 if not isinstance(record.get('notes'),str) or not record['notes'].strip():raise ValueError('REVIEW_NOTES_REQUIRED')
 if set(record.get('reviewed_classes',[]))!=set(task['classes']):raise ValueError('CLASS_COMPLETENESS_DECLARATION_REQUIRED')
 states=record.get('class_review_status',{})
 if set(states)!=set(task['classes']) or any(v not in ['PRESENT_ANNOTATED','ABSENT_CONFIRMED','UNKNOWN','NOT_APPLICABLE'] for v in states.values()):raise ValueError('EXPLICIT_PER_CLASS_KNOWN_UNKNOWN_STATUS_REQUIRED')
 if record.get('inventory_authority')!='UNKNOWN_NOT_PHYSICAL_STOCK':raise ValueError('DRAWING_CONTENT_IS_NOT_STOCK_AUTHORITY')
 annotations=record.get('annotations');assert isinstance(annotations,list)
 if len(annotations)>1000:raise ValueError('ANNOTATION_LIMIT')
 seen=set();geoms=[];boundary=None
 for a in annotations:
  if a.get('id') in seen or not a.get('id'):raise ValueError('INVALID_ANNOTATION_ID')
  seen.add(a['id'])
  if a.get('class') not in task['classes']:raise ValueError('UNSUPPORTED_CLASS')
  if a.get('origin')!='HUMAN_DRAWN_OR_HUMAN_REVIEWED_PUBLISHED_LABEL':raise ValueError('UNVERIFIED_PSEUDO_LABEL')
  if a.get('geometry',{}).get('type')!='Polygon':raise ValueError('POLYGON_REQUIRED')
  g=shape(a['geometry'])
  if g.is_empty or not g.is_valid or g.area<=0:raise ValueError('INVALID_POLYGON')
  if not all(math.isfinite(x) for x in g.bounds) or g.bounds[0]<0 or g.bounds[1]<0 or g.bounds[2]>task['width'] or g.bounds[3]>task['height']:raise ValueError('POLYGON_OUTSIDE_SOURCE')
  if a['class']=='site_boundary':
   if boundary is not None:raise ValueError('AMBIGUOUS_MULTIPLE_SITE_BOUNDARIES')
   boundary=g
  geoms.append((a,g))
 warnings=[]
 for klass,state in states.items():
  count=sum(a['class']==klass for a in annotations)
  if state=='PRESENT_ANNOTATED' and count==0 or state=='ABSENT_CONFIRMED' and count>0:raise ValueError('CLASS_PRESENCE_ANNOTATION_CONFLICT')
 eligible={k:task['training_rights']=='DECLARED_RESEARCH_USE' and task.get('raster_training_allowed',False) and v in ['PRESENT_ANNOTATED','ABSENT_CONFIRMED'] for k,v in states.items()}
 if boundary is not None:
  for a,g in geoms:
   if a['class']!='site_boundary' and g.difference(boundary).area>1e-6:warnings.append({'id':a['id'],'reason':'OUTSIDE_DECLARED_SITE_BOUNDARY_REVIEW_REQUIRED','outside_area_px2':g.difference(boundary).area})
 return {'status':'LOCAL_EXPLICIT_ANNOTATION_INPUT_VALID' if not warnings else 'LOCAL_ANNOTATION_TOPOLOGY_REVIEW_REQUIRED','review_origin':'EXPLICIT_LOCAL_UNAUTHENTICATED_INPUT','human_identity_authenticated':False,
  'source_sha256':task['source_sha256'],'annotation_count':len(annotations),'warnings':warnings,'training_eligible':all(eligible.values()) and not warnings,'training_eligibility_by_class':{k:v and not warnings for k,v in eligible.items()},
  'metric_calibration':None,'planner_approved':False,'optimization_ready':False,'truth_limit':'Checks source hashes, syntax, geometry and explicit attestation; cannot verify human identity or physical truth.'}
