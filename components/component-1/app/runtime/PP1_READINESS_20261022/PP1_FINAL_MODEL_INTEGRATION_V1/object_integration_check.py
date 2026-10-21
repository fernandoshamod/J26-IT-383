"""Explicit experimental chair-positive source; candidate integration, not a new accuracy evaluation."""
from common import *
import platform
platform.uname();events=guard(allow_loopback=True)
from integrated_api import create_app
from fastapi.testclient import TestClient
from model_registry import verify_hashes
out=H/'outputs/OBJECT_SOURCE_001';out.mkdir(parents=True,exist_ok=False)
rows=read(H.parent/'PP1_VENUE_RECOGNITION_V4/objects_v2/SPLITS.json')['test'];source=next(r['source'] for r in rows if r['annotations'])
app=create_app(out/'research.sqlite3');client=TestClient(app)
upload=client.post('/images',content=Path(source).read_bytes(),headers={'Content-Type':'application/octet-stream'});assert upload.status_code==200
r=client.post('/analyses',json={'image_path':upload.json()['image_path'],'experimental_chair':True});assert r.status_code==200,r.text
r=r.json();chairs=[o for o in r['candidate_bundle']['objects'] if o.get('frozen_event_class_id')==2];assert chairs
for c in chairs:assert c['semantic_class']=='chair' and c['status']=='uncertain' and not c['planner_confirmed'] and not c['relocation_allowed'] and c['mobility_classification']=='unknown' and c['metric_geometry'] is None
before=app.state.service.minimize_calls
missing=client.post('/twins',json={'review':r['pending_review_template'],'candidate_bundle':r['candidate_bundle']});assert missing.status_code==422 and app.state.service.minimize_calls==before
bad=client.post('/images',content=b'not a jpeg',headers={'Content-Type':'application/octet-stream'});assert bad.status_code==422
unsupported=client.post('/analyses',json={'image_path':upload.json()['image_path'],'use_event12_on_real_plan':True});assert unsupported.status_code==422 and app.state.service.minimize_calls==before
save(out.relative_to(H)/'ANALYSIS_RESPONSE.json',r)
save(out.relative_to(H)/'RESULT.json',{'verdict':'PASS','source':source,'source_sha256':sha(source),'analysis_id':r['analysis_id'],'experimental_chair_candidates':len(chairs),'class_id':2,'actual_loads':r['model_report']['actual_checkpoint_loads'],'gate_verdict':'EXPECTED_PENDING','gate_http':missing.status_code,'invalid_image_verdict':'EXPECTED_REFUSAL','unsupported_real_event12_field_verdict':'EXPECTED_REFUSAL','optimizer_calls':app.state.service.minimize_calls,'genuine_stock_verified':False,'new_accuracy_evaluation':False,'selection':'First published chair-positive source in existing V4 split order; previously observed development source','guard':events})
print('Chair-positive actual candidate integration PASS',len(chairs),'pending review; invalid input and unsupported real event12 selection refused')
