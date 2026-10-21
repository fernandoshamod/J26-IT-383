import copy
import hashlib
from spatial_twin_gate_v1 import validate_and_normalize

sample = {
 'contract_id':'STAGE_D_REVIEWED_TWIN_V1','venue_id':'TEST_HALL',
 'image': {'width_pixels':1200, 'height_pixels':800, 'sha256':hashlib.sha256(b'fake test image').hexdigest()},
 'scale_calibration':{'method':'two_point_known_distance','point_a_px':[100,100],'point_b_px':[600,100],'known_distance_m':10},
 'usable_boundary_px':[[100,100],[1100,100],[1100,700],[100,700]],
 'planner_review':{'confirmed':True,'reviewer_id':'SIMULATED_TEST_REVIEWER','metric_dimensions_reviewed':True},
 'objects':[{'id':'P1','class':'pillar','status':'fixed','polygon_px':[[500,350],[550,350],[550,400],[500,400]]}]
}

def reject(label, change, code):
 x=copy.deepcopy(sample);change(x)
 try:validate_and_normalize(x)
 except ValueError as e:
  assert str(e)==code,(label,str(e),code)
  print(label,'DENIED',code)
 else:raise AssertionError(label+' accepted unexpectedly')

r=validate_and_normalize(sample)
assert r['metres_per_pixel']==0.02
assert r['verification_flags']['stage_e_current_engine_accepts_real_twin'] is False
print('calibrated_geometry','PASS')
reject('no_approval',lambda x:x['planner_review'].update(confirmed=False),'PLANNER_CONFIRMATION_REQUIRED')
reject('no_measurement',lambda x:x['scale_calibration'].update(known_distance_m=0),'INVALID_CALIBRATION_DISTANCE')
reject('uncertain_object',lambda x:x['objects'][0].update(status='uncertain'),'UNRESOLVED_UNCERTAIN_GEOMETRY')
reject('object_outside',lambda x:x['objects'][0].update(polygon_px=[[10,10],[20,10],[20,20],[10,20]]),'OBJECT_OUTSIDE_USABLE_BOUNDARY')
reject('self_intersection',lambda x:x.update(usable_boundary_px=[[100,100],[1100,700],[1100,100],[100,700]]),'INVALID_POLYGON')
reject('hash_missing',lambda x:x['image'].update(sha256=''),'IMAGE_HASH_REQUIRED')
print('STAGE D BRIDGE CONTRACT TESTS: 7/7 PASS')
