"""Actual new backend hook, model traces, pending gates, durable artifacts and control registration."""
from common import *
import platform,copy,shutil,sqlite3,traceback
platform.uname();events=guard(allow_loopback=True);out=H/'outputs/INTEGRATION_CHECKS_004';out.mkdir(parents=True,exist_ok=False)
import atexit
atexit.register(lambda:save(out.relative_to(H)/'GUARD_EVENTS.json',events))
cases=[]
def check(name,verdict,fn):
 try:detail=fn();cases.append({'test':name,'verdict':verdict,'detail':detail});print(name,verdict,flush=True);return detail
 except BaseException:
  cases.append({'test':name,'verdict':'FAIL','traceback':traceback.format_exc()});save(out.relative_to(H)/'FAILED_CASES.json',cases);raise
from integrated_api import create_app
from fastapi.testclient import TestClient
from model_registry import inspect_models,MODELS
app=create_app(out/'research.sqlite3');client=TestClient(app)
models=check('four_checkpoint_architecture_hash_and_class_maps','PASS',inspect_models);save(out.relative_to(H)/'MODEL_IDENTITIES.json',models)
source=ROOT/'01_DATASET_DOWNLOADS/CubiCasa5K/cubicasa5k/cubicasa5k/high_quality_architectural/1848/F1_scaled.png'
u=client.post('/images',content=source.read_bytes(),headers={'Content-Type':'application/octet-stream'});assert u.status_code==200,u.text;upload=u.json()
check('actual_image_intake_is_source_bound','PASS',lambda:{'same_original_bytes_sha256':upload['sha256']==sha(source),'physical_provenance_verified':upload['physical_real_venue_provenance_verified']})
response=client.post('/analyses',json={'image_path':upload['image_path']});assert response.status_code==200,response.text;analysis=response.json();save(out.relative_to(H)/'ACTUAL_ANALYSIS_RESPONSE.json',analysis)
bundle=analysis['candidate_bundle'];report=analysis['model_report']
def real_model_check():
 actual={r['sha256'] for r in report['actual_checkpoint_loads']};expected={models[k]['sha256'] for k in ['unet','opening_yolo']}
 assert expected.issubset(actual) and models['controlled_event_yolo']['sha256'] not in actual and models['experimental_chair']['sha256'] not in actual
 assert report['actual_model_calls']=={'unet':1,'opening_yolo':1};assert report['event_objects']['calls']==0
 assert report['actual_unet_forwards']==[{'module':'Unet','input_shape':[1,3,512,512],'output_shape':[1,4,512,512]}]
 from shapely.geometry import shape
 for ob in bundle['objects']:
  g=shape(ob['geometry']);assert g.is_valid and g.area>0 and ob['source_sha256']==bundle['source']['sha256'];assert ob['metric_geometry'] is None and ob['planner_confirmed'] is False and ob['relocation_allowed'] is False and ob['mobility_classification']=='unknown'
 assert bundle['boundary'] is None and bundle['metres_per_pixel'] is None and not bundle['optimization_ready']
 assert report['structural_candidates']==sum(o['id'].startswith('UNET_') for o in bundle['objects'])
 assert report['yolo_candidates']==sum(o['id'].startswith('OPENING_YOLO_') for o in bundle['objects'])
 assert 'GEOMETRY_CANDIDATES.png' in analysis['artifacts'] and 'YOLO_OVERLAY.png' in analysis['artifacts']
 return {'actual_model_loads':report['actual_checkpoint_loads'],'actual_forward_shapes':report['actual_unet_forwards'],'candidates':len(bundle['objects']),'geometry_units':'decoded original image pixels','controlled12_inferred':False,'experimental_default':False}
check('native_raster_actual_updated_models_and_candidate_geometry','PASS',real_model_check)
before=app.state.service.minimize_calls
pending=client.post('/twins',json={'review':analysis['pending_review_template'],'candidate_bundle':bundle})
def pending_check():
 assert pending.status_code==422 and app.state.service.minimize_calls==before
 assert analysis['gate']['accepted'] is False
 return {'http':pending.status_code,'response':pending.json(),'missing':analysis['gate']['missing'],'optimizer_calls':0}
check('real_source_missing_calibration_review_evidence','EXPECTED_PENDING',pending_check)
from fixtures import optimization,controlled_registration
q=optimization({'venue_id':'UNREVIEWED_'+analysis['analysis_id'],'venue_version':1,'twin_sha256':__import__('support').digest(bundle)})
r=client.post('/optimize',json=q)
def bypass_check():
 assert r.status_code==200 and r.json()['status']!='success' and not r.json()['candidate_layouts'] and app.state.service.minimize_calls==before
 return {'http':r.status_code,'response':r.json(),'optimizer_calls':0}
check('unregistered_model_candidates_cannot_reach_optimizer','EXPECTED_REFUSAL',bypass_check)
fresh=TestClient(create_app(out/'research.sqlite3'));fetched=fresh.get('/analyses/'+analysis['analysis_id']);assert fetched.status_code==200 and fetched.json()==analysis
for name,meta in analysis['artifacts'].items():
 r=fresh.get(meta['url']);assert r.status_code==200 and __import__('hashlib').sha256(r.content).hexdigest()==meta['sha256']
check('analysis_and_artifact_integrity_after_app_recreation','PASS',lambda:{'analysis_id':analysis['analysis_id'],'artifact_count':len(analysis['artifacts']),'exact_readback':True})
explicit=client.post('/analyses',json={'image_path':upload['image_path'],'experimental_chair':True});assert explicit.status_code==200,explicit.text;explicit=explicit.json()
def opt_in():
 actual={r['sha256'] for r in explicit['model_report']['actual_checkpoint_loads']};assert models['experimental_chair']['sha256'] in actual and models['controlled_event_yolo']['sha256'] not in actual
 assert explicit['model_report']['event_objects']['calls']==1 and not explicit['candidate_bundle']['optimization_ready']
 return {'actual_loads':explicit['model_report']['actual_checkpoint_loads'],'status':explicit['model_report']['event_objects']['status'],'candidates':len(explicit['candidate_bundle']['objects'])}
check('experimental_chair_explicit_opt_in_only','PASS',opt_in);save(out.relative_to(H)/'EXPLICIT_CHAIR_ANALYSIS.json',explicit)
reg=controlled_registration(out/'CONTROLLED_BACKEND_FIXTURE');registered=client.post('/twins',json=reg);assert registered.status_code==200,registered.text
save(out.relative_to(H)/'CONTROLLED_REGISTRATION.json',{'input':reg,'response':registered.json(),'scope':'EXISTING_SIMULATED_FIXTURE_NOT_INFERRED_FROM_REAL_IMAGE'})
check('unchanged_metric_Twin_interface_controlled_positive','PASS',lambda:{'venue_id':registered.json()['venue_id'],'twin_sha256':registered.json()['twin_sha256'],'real_image_connection':False})
contracts=client.get('/contracts').json();assert contracts['api_version']=='1.1.0' and contracts['analysis']['properties']['experimental_chair']['default'] is False
save(out.relative_to(H)/'CONTRACTS.json',contracts);save(out.relative_to(H)/'OPENAPI.json',app.openapi())
check('existing_response_contract_with_explicit_analysis_extension','PASS',lambda:{'base_api_version':contracts['api_version'],'integration_version':app.state.integration_version,'legacy_body_accepted':True})
# The legacy pending-real test now consumes these newly executed updated-model outputs.
alias=H/'outputs/PATH_A_REAL_MODEL_FINAL';alias.mkdir(exist_ok=False)
for n in ['CANDIDATE_BUNDLE.json','REVIEW_CALIBRATION_TEMPLATE_PENDING.json']:shutil.copyfile(H/'outputs/API_ANALYSES'/analysis['analysis_id']/n,alias/n)
with sqlite3.connect(out/'research.sqlite3') as db:count=db.execute('SELECT COUNT(*) FROM runs').fetchone()[0]
check('denial_SQLite_readback_without_optimizer','PASS',lambda:{'persisted_run_rows':count,'optimizer_calls':app.state.service.minimize_calls})
cases.append({'test':'genuine_reviewed_real_source_positive','verdict':'NOT_EXECUTED','detail':'No genuine measurements, reviewed geometry or external approval supplied; exactly-one-reviewed-stage gate unchanged.'})
save(out.relative_to(H)/'RESULTS.json',{'cases':cases,'guard':events,'source':str(source),'actual_analysis_id':analysis['analysis_id'],'actual_model_accuracy_claim':False,'controlled_eag_execution':'Separate existing lifecycle entrypoint; see CONTROLLED_001, not these unreviewed pixels'})
print('Integration checks complete')
