"""Actual updated model API and HTTP contract registration (ASGI transport)."""
from common import *
import copy,platform,sqlite3
platform.uname();events=guard(allow_loopback=True)
sys.path.append(str(H.parent/'PP1_FINAL_MODEL_INTEGRATION_V1'))
from integrated_api import create_app
from fastapi.testclient import TestClient
from support import digest
app=create_app(H/'HTTP/research.sqlite3');c=TestClient(app)
r=read(H/'SCENE_BRIEF.json');v=r['venue'];src=v['source'];source=dict(path=src['path'],sha256=src['sha256'],width_pixels=src['width_px'],height_pixels=src['height_px'],domain=src['domain'])
bundle=dict(schema='IMAGE_SPACE_TWIN_CANDIDATE_V2',source=source,objects=[dict(id=o['candidate_ref'],origin='CONTROLLED_GENERATOR_NOT_MODEL_PREDICTION') for o in v['existing']],provenance={'origin':'EXISTING_EXPLICIT_CONTROLLED_SCENE_FIXTURE','model_inference':False})
evidence=H/'HTTP/CONTROLLED_REVIEW_EVIDENCE.json'
save(evidence.relative_to(H),{'scope':'SIMULATED_FIXTURE_NOT_GENUINE_CONSENT','source_sha256':src['sha256'],'scene_fixture_sha256':digest(r),'purpose':'Explicit generated geometry, scale and object decisions for controlled integration testing only'})
eid='CONTROLLED_GENERATOR_REVIEW'
review=dict(contract_id='COMPONENT1_REVIEWED_TWIN_V1',venue_id=v['venue_id'],venue_version=v['version'],source=source,candidate_bundle_sha256=digest(bundle),calibration=dict(method='isotropic_two_point_controls',controls=[dict(point_a_px=x['a_px'],point_b_px=x['b_px'],known_distance_m=x['distance_m'],evidence_ref=eid) for x in v['controls']],metric_origin_px=v['origin_px']),boundary_px=v['boundary_px'],objects=[dict(object_id=o['instance_id'],class_name=o['class_name'],status=o['status'],polygon_px=[[x*10,y*10] for x,y in o['footprint_m']],candidate_refs=[o['candidate_ref']],decision_evidence_ref=eid) for o in v['existing']],review=dict(status='approved',reviewer_id=v['review']['reviewer_id'],evidence_ref=eid,scope='SIMULATED_FIXTURE_REVIEW',geometry_confirmed=True,metric_dimensions_confirmed=True),evidence_artifacts=[dict(evidence_id=eid,path=str(evidence),sha256=sha(evidence),source_sha256=src['sha256'])])
reg=dict(review=review,candidate_bundle=bundle);save('HTTP/REGISTER_REQUEST.json',reg)
response=c.post('/twins',json=reg);save('HTTP/REGISTER_RESPONSE.json',{'http':response.status_code,'body':response.json()});assert response.status_code==200,response.text
receipt=response.json();save('HTTP/TWIN_RECEIPT.json',receipt)
got=c.get(f"/twins/{v['venue_id']}/versions/{v['version']}");assert got.status_code==200 and got.json()==receipt
save('HTTP/TWIN_READBACK.json',got.json())
# A fresh real drawing is uploaded and models actually run. No approval is supplied.
source_plan=ROOT/'01_DATASET_DOWNLOADS/CubiCasa5K/cubicasa5k/cubicasa5k/high_quality_architectural/1848/F1_scaled.png'
up=c.post('/images',content=source_plan.read_bytes(),headers={'Content-Type':'application/octet-stream'});assert up.status_code==200;save('PATH_A/UPLOAD.json',up.json())
ar=c.post('/analyses',json={'image_path':up.json()['image_path']});assert ar.status_code==200,ar.text;a=ar.json();save('PATH_A/ANALYSIS.json',a)
before=app.state.service.minimize_calls
p=c.post('/twins',json={'review':a['pending_review_template'],'candidate_bundle':a['candidate_bundle']});assert p.status_code==422
from fixtures import optimization
q=optimization(dict(venue_id='UNREVIEWED_'+a['analysis_id'],venue_version=1,twin_sha256=digest(a['candidate_bundle'])))
denial=c.post('/optimize',json=q);assert denial.status_code==200 and denial.json()['status']!='success' and app.state.service.minimize_calls==before
run=c.get('/runs/'+denial.json()['run_id']);assert run.status_code==200 and run.json()['response']==denial.json()
assert a['candidate_bundle']['metres_per_pixel'] is None and not a['candidate_bundle']['optimization_ready']
assert all(o['metric_geometry'] is None and not o['planner_confirmed'] for o in a['candidate_bundle']['objects'])
save('PATH_A/RESULT.json',dict(status='EXPECTED_PENDING',http_review=p.status_code,review_response=p.json(),denial=denial.json(),readback=run.json(),optimizer_evaluations=0,optimizer_calls=0,scene_calls=0,analysis_id=a['analysis_id']))
from responses import AnalysisReceipt
AnalysisReceipt.model_validate(a)
save('HTTP/OPENAPI.json',app.openapi());save('HTTP/CONTRACTS.json',c.get('/contracts').json());save('HTTP/GUARD_EVENTS.json',events)
# Evidence for the original unchanged regression suite, relocated into this delivery.
out=H/'outputs/PATH_A_REAL_MODEL';out.mkdir(parents=True)
for name in ['CANDIDATE_BUNDLE.json','MODEL_OUTPUT_REPORT.json','REVIEW_CALIBRATION_TEMPLATE_PENDING.json']:
 import shutil
 shutil.copyfile(H/'outputs/API_ANALYSES'/a['analysis_id']/name,out/name)
print('HTTP Twin registered/read back; actual model path pending; optimizer bypass denied')
