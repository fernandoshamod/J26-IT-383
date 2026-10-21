"""Independent black-box PP1 handoff tests, including actual model API inference.
Every supplied positive review/measurement record is an explicit controlled fixture.
No external planner approval is created or claimed.
"""
import copy,json,math,sqlite3
from pathlib import Path
import numpy as np
from PIL import Image
from shapely.geometry import Polygon
from fastapi.testclient import TestClient
from pydantic import TypeAdapter
from api import create_app
from contracts import TwinReview
from evidence import verify_evidence_artifacts
from support import ROOT,PACKAGE,read,save,digest,filehash,ResearchError
from fixtures import controlled_registration,optimization,approval,revise
from responses import OptimizationResponse
from service import verify_xai_binding

def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='new_tests');args=parser.parse_args()
    if Path(args.name).name!=args.name:raise ValueError('INVALID_OUTPUT_NAME')
    out=PACKAGE/'outputs/HANDOFF_V1';evidence=out/args.name;evidence.mkdir();tests=[]
    app=create_app(evidence/'research.sqlite3');c=TestClient(app);s=app.state.service
    def check(name,fn):
        try:r=fn();tests.append(dict(test=name,passed=True,detail=r));print(name,'PASS',flush=True)
        except Exception as exc:
            tests.append(dict(test=name,passed=False,error=repr(exc)));save(evidence/'FAILED_TESTS.json',tests);raise
    reg=controlled_registration(evidence/'fixture',venue_id='HANDOFF_CONTROLLED')
    # Actual calibration evidence from the controlled scene generator, explicitly labelled.
    artifact=evidence/'CONTROLLED_MEASUREMENT_AND_REVIEW.json';save(artifact,{'domain':'controlled_synthetic','review_origin':'SIMULATED_FIXTURE_REVIEW','physical_real_venue_evidence':False,'source_sha256':reg['review']['source']['sha256'],'width_m':32,'height_m':24,'pixels_per_metre':10,'note':'Known generator dimensions; not real measured evidence or an actual planner decision.'})
    eref='CONTROLLED_GENERATOR_EVIDENCE';reg['review']['evidence_artifacts']=[{'evidence_id':eref,'path':str(artifact.resolve()),'sha256':filehash(artifact),'source_sha256':reg['review']['source']['sha256']}]
    reg['review']['review']['evidence_ref']=eref
    for control in reg['review']['calibration']['controls']:control['evidence_ref']=eref
    for obj in reg['review']['objects']:obj['decision_evidence_ref']=eref
    registration=c.post('/twins',json=reg);assert registration.status_code==200,registration.text;t=registration.json();save(evidence/'REGISTER_REQUEST.json',reg);save(evidence/'REGISTER_RESPONSE.json',t)
    def calibrated():
        twin=t['metric_twin'];assert twin['metres_per_pixel']==.1 and twin['evidence_verification']['files_verified']==1
        assert abs(Polygon(twin['boundary_polygon_m']).area-768)<1e-10
        for before,after in zip(reg['review']['objects'],twin['fixed_objects']):assert np.allclose(np.array(before['polygon_px'])*.1,after['footprint_coordinates_m'])
        assert not twin['evidence_verification']['evidence_truth_independently_verified'];return {'metric_area_m2':768,'scale_m_per_px':.1,'scope':'controlled_generator_evidence_only'}
    check('supplied_valid_controlled_artifacts_and_independent_metric_transform',calibrated)
    def reject_review(mutate,code=None):
        q=copy.deepcopy(reg);mutate(q);before=s.minimize_calls;r=c.post('/twins',json=q);assert r.status_code==422,r.text
        if code:assert r.json()['reason']==code,r.text
        assert s.minimize_calls==before;return r.json()
    for name,fn,code in [
        ('missing_evidence_file',lambda q:q['review']['evidence_artifacts'][0].update(path=str(evidence/'not_supplied.pdf')),'EVIDENCE_FILE_MISSING_OR_OUTSIDE_WORKSPACE'),
        ('invented_evidence_hash',lambda q:q['review']['evidence_artifacts'][0].update(sha256='0'*64),'EVIDENCE_FILE_HASH_MISMATCH'),
        ('wrong_evidence_source_binding',lambda q:q['review']['evidence_artifacts'][0].update(source_sha256='0'*64),'EVIDENCE_SOURCE_BINDING_MISMATCH'),
        ('source_image_cannot_stand_in_for_review_evidence',lambda q:q['review']['evidence_artifacts'][0].update(path=q['review']['source']['path'],sha256=q['review']['source']['sha256']),'SOURCE_IMAGE_IS_NOT_REVIEW_OR_MEASUREMENT_EVIDENCE'),
        ('duplicate_evidence_id',lambda q:q['review']['evidence_artifacts'].append(copy.deepcopy(q['review']['evidence_artifacts'][0])),'DUPLICATE_EVIDENCE_ID'),
        ('missing_actual_review',lambda q:q['review']['review'].update(status='pending'),'REVIEW_NOT_APPROVED'),
        ('unknown_calibration_claim',lambda q:q['review']['calibration'].update(fake_accuracy=1),None),
    ]:check(name,lambda f=fn,k=code:reject_review(f,k))
    def candidate_mutation(field,value):
        def change(q):q['candidate_bundle']['source']=copy.deepcopy(q['candidate_bundle']['source']);q['candidate_bundle']['source'][field]=value;q['review']['candidate_bundle_sha256']=digest(q['candidate_bundle'])
        return change
    for field,value in [('width_pixels',999),('height_pixels',999),('domain','real_source'),('path','invented.png')]:check('candidate_metadata_'+field,lambda f=field,v=value:reject_review(candidate_mutation(f,v),'CANDIDATE_SOURCE_METADATA_MISMATCH'))
    def bad_id(q):q['candidate_bundle']['objects'][0]['id']=None;q['review']['candidate_bundle_sha256']=digest(q['candidate_bundle'])
    check('malformed_candidate_id_rejected',lambda:reject_review(bad_id,'INVALID_CANDIDATE_OBJECT_RECORDS'))
    def invent_external(q):
        q['review']['source']['domain']='real_source';q['candidate_bundle']['source']['domain']='real_source';q['review']['candidate_bundle_sha256']=digest(q['candidate_bundle']);q['review']['review']['scope']='EXTERNAL_RESEARCH_REVIEW';q['review']['evidence_artifacts']=[]
    check('adversarial_external_claim_without_artifacts_rejected',lambda:reject_review(invent_external,'EXTERNAL_EVIDENCE_REFERENCE_NOT_RESOLVED'))
    check('registered_twin_retrieval',lambda: {'same_sha256':c.get('/twins/HANDOFF_CONTROLLED/versions/1').json()['twin_sha256']==t['twin_sha256']} if c.get('/twins/HANDOFF_CONTROLLED/versions/1').json()==t else (_ for _ in ()).throw(AssertionError('Twin retrieval differs')))
    req=optimization(t);initial=c.post('/optimize',json=req).json();assert initial['status']=='success',initial;save(evidence/'INITIAL_REQUEST.json',req);save(evidence/'INITIAL_RESPONSE.json',initial)
    def pareto(response,initial_mode):
        layouts=response['candidate_layouts'];vectors=[];keys=[]
        for layout in layouts:
            centers=layout['group_centers_m'];reference=response['initialization_or_retained_reference_m'];stage=Polygon(next(o['footprint_coordinates_m'] for o in layout['objects'] if o['class']=='stage')).centroid
            average=sum(math.dist(xy,[stage.x,stage.y]) for xy in centers.values())/len(centers)
            if initial_mode:
                from scipy.optimize import linear_sum_assignment
                cost=np.linalg.norm(np.array(list(centers.values()))[:,None,:]-np.array(list(reference.values()))[None,:,:],axis=2);a,b=linear_sum_assignment(cost);movement=float(cost[a,b].sum())
            else:movement=sum(math.dist(xy,reference[g]) for g,xy in centers.items())
            vectors.append((average,movement));keys.append(digest(centers))
        assert len(set(keys))==len(layouts)
        for i,f in enumerate(vectors):assert not any(j!=i and all(a<=b+1e-9 for a,b in zip(g,f)) and any(a<b-1e-9 for a,b in zip(g,f)) for j,g in enumerate(vectors)),vectors
        return {'independent_objective_vectors':vectors,'nondominance_scope':'all returned candidates, not global optimality proof'}
    check('initial_pareto_nondominance_from_raw_centers',lambda:pareto(initial,True))
    ap=c.post('/runs/'+initial['run_id']+'/approve',json=approval(initial));assert ap.status_code==200,ap.text;revision=revise(initial,ap.json(),req)
    adaptive=c.post('/optimize',json=revision).json();assert adaptive['status']=='success',adaptive;save(evidence/'ADAPTIVE_REQUEST.json',revision);save(evidence/'ADAPTIVE_RESPONSE.json',adaptive)
    check('adaptive_pareto_nondominance_from_raw_centers',lambda:pareto(adaptive,False))
    def context_limit():
        q=copy.deepcopy(req)
        for party in ['client','planner']:q['requirements'][party]['hard']['maximum_total_movement_m']=0.
        r=c.post('/optimize',json=q).json();save(evidence/'ZERO_MOVEMENT_HARD_RESPONSE.json',r);assert r['status']=='success',r
        assert all(abs(v['assignment_movement'])<=1e-7 for v in r['verification'].values())
        assert len(r['candidate_layouts'])<len(initial['candidate_layouts']);return {'base_alternatives':len(initial['candidate_layouts']),'bounded_alternatives':len(r['candidate_layouts']),'optimizer_evaluations':r['optimizer_evaluations']}
    check('context_hard_movement_bound_changes_feasible_decisions',context_limit)
    def selection():
        q=copy.deepcopy(req)
        for party in ['client','planner']:q['requirements'][party]['alternative_preference']='minimum_disruption'
        r=c.post('/optimize',json=q).json();assert r['status']=='success';assert digest(r['candidate_layouts'])==digest(initial['candidate_layouts']);assert r['selected_layout_id']!=initial['selected_layout_id'];return {'stage_selection':initial['selected_layout_id'],'disruption_selection':r['selected_layout_id'],'candidate_set_identical':True}
    check('soft_preference_changes_selection_without_claiming_learned_optimization',selection)
    def revoke_during_search():
        original=s.engine
        def engine(name):
            m=original(name);run=m.execute
            def execute(*args,**kwargs):
                result=run(*args,**kwargs);r=c.post('/approvals/'+ap.json()['approval_id']+'/revoke',json={'reviewer_id':'SIMULATED_FIXTURE_REVIEWER','reason':'Explicit adversarial race fixture'});assert r.status_code==200;return result
            m.execute=execute;return m
        s.engine=engine
        try:r=c.post('/optimize',json=revision).json()
        finally:s.engine=original
        assert r['reason']=='REFERENCE_REVOKED_OR_CHANGED_DURING_EXECUTION' and not r['candidate_layouts'] and r['optimizer_evaluations']==1680;save(evidence/'REVOKE_DURING_SEARCH.json',r);return r['reason']
    check('actual_approval_revoked_during_search_cannot_be_saved_as_success',revoke_during_search)
    def changed_evidence():
        original=artifact.read_bytes();artifact.write_bytes(original+b'\n')
        try:r=c.post('/optimize',json=req).json()
        finally:artifact.write_bytes(original)
        assert r['reason']=='EVIDENCE_FILE_HASH_MISMATCH' and r['optimizer_evaluations']==0;return r['reason']
    check('review_evidence_rechecked_before_every_search',changed_evidence)
    def missing_registered_image():
        path=Path(reg['review']['source']['path']);original=path.read_bytes();path.unlink()
        try:r=c.post('/optimize',json=req).json()
        finally:path.write_bytes(original)
        assert r['reason']=='REGISTERED_SOURCE_CHANGED' and r['optimizer_evaluations']==0;return r['reason']
    check('removed_registered_image_rejected_without_server_error',missing_registered_image)
    def candidate_nan():
        q=copy.deepcopy(reg);q['candidate_bundle']['untrusted_extra']=float('nan');r=c.post('/twins',content=json.dumps(q),headers={'content-type':'application/json'})
        assert r.status_code==422 and r.json()['reason']=='CANDIDATE_BUNDLE_NOT_FINITE_JSON';return r.json()
    check('nonfinite_untrusted_candidate_json_rejected_without_server_error',candidate_nan)
    # Reuse the earlier four meaningful checks on the corrected code, using isolated destinations.
    def original_supplemental():
        # Run the unchanged four assertions; only redirect the output folder.
        source=(PACKAGE/'final_checks.py').read_text().replace("out=PACKAGE/'outputs/SUPPLEMENTAL'","out=Path("+repr(str(evidence/'SUPPLEMENTAL_RETEST'))+")")
        namespace={'__file__':str(PACKAGE/'final_checks.py'),'__name__':'handoff_supplemental'};exec(compile(source,str(PACKAGE/'final_checks.py'),'exec'),namespace);namespace['main']()
        r=read(evidence/'SUPPLEMENTAL_RETEST/TEST_RESULTS.json');assert r['passed']==4;return {'original_supplemental_checks_passed':4}
    check('original_four_supplemental_checks_reexecuted',original_supplemental)
    def actual_models_api():
        image=ROOT/'PP1_STAGE_E_EVENT_LAYOUT_V2/assets/uploads/venue_34464b2feb692138.png';raw=image.read_bytes();u=c.post('/images',content=raw,headers={'Content-Type':'application/octet-stream'});assert u.status_code==200,u.text;upload=u.json();assert upload['sha256']==filehash(image)
        r=c.post('/analyses',json={'image_path':upload['image_path']});assert r.status_code==200,r.text;body=r.json();assert body['status']=='review_required' and not body['gate']['accepted'];aid=body['analysis_id'];save(evidence/'ACTUAL_MODEL_API_RESPONSE.json',body)
        assert c.get('/analyses/'+aid).json()==body
        earlier=PACKAGE/'outputs/PATH_A_REAL_MODEL';pred=c.get(body['artifacts']['UNET_MODEL_MASK.png']['url']);assert pred.status_code==200
        import io
        assert np.array_equal(np.array(Image.open(io.BytesIO(pred.content))),np.array(Image.open(earlier/'UNET_MODEL_MASK.png')))
        bundle=body['candidate_bundle'];assert bundle['models']==read(earlier/'CANDIDATE_BUNDLE.json')['models'];assert bundle['objects']==read(earlier/'CANDIDATE_BUNDLE.json')['objects']
        assert sum(body['model_report']['unet']['model']['counts'])==512*512
        assert sum(body['model_report']['unet']['original']['counts'])==1600*1200
        pending=c.post('/twins',json={'review':body['pending_review_template'],'candidate_bundle':bundle});assert pending.status_code==422
        fresh=TestClient(create_app(evidence/'research.sqlite3'));assert fresh.get('/analyses/'+aid).json()==body
        return {'analysis_id':aid,'structural_candidates':body['model_report']['structural_candidates'],'yolo_candidates':body['model_report']['yolo_candidates'],'same_actual_predictions_as_before':True,'survives_app_recreation':True,'pending_review_rejected':True}
    check('actual_image_upload_inference_geometry_artifacts_retrieval_and_pending_gate',actual_models_api)
    def corrupt_analysis():
        body=read(evidence/'ACTUAL_MODEL_API_RESPONSE.json');path=PACKAGE/'outputs/API_ANALYSES'/body['analysis_id']/'MODEL_OUTPUT_REPORT.json';original=path.read_bytes();path.write_bytes(original+b'\n')
        try:r=c.get('/analyses/'+body['analysis_id'])
        finally:path.write_bytes(original)
        assert r.status_code==422 and r.json()['reason']=='SAVED_ANALYSIS_ARTIFACT_CORRUPTED';return r.json()
    check('saved_model_artifact_tampering_rejected',corrupt_analysis)
    for name,path,payload in [('invalid_image','/images',b'not an image'),('unknown_analysis','/analyses/abc',None),('missing_twin','/twins/UNKNOWN/versions/1',None)]:
        def reject(p=path,data=payload):
            r=c.post(p,content=data,headers={'Content-Type':'application/octet-stream'}) if data is not None else c.get(p);assert r.status_code==422,r.text;return r.json()
        check(name,reject)
    def contracts():
        spec=c.get('/openapi.json').json();contract=c.get('/contracts').json();assert contract['api_version']=='1.1.0'
        assert spec['paths']['/optimize']['post']['responses']['200']['content']['application/json']['schema']
        adapter=TypeAdapter(OptimizationResponse)
        with s.store.connection() as db:rows=db.execute('SELECT request_json,response_json FROM runs').fetchall()
        for row in rows:
            response=json.loads(row['response_json']);adapter.validate_python(response);verify_xai_binding(response,json.loads(row['request_json']))
        save(evidence/'OPENAPI_V1.json',spec);save(evidence/'API_CONTRACTS_V1.json',contract)
        return {'paths':sorted(spec['paths']),'persisted_response_contracts_and_xai_verified':len(rows)}
    check('openapi_and_every_persisted_response_contract_and_xai',contracts)
    save(evidence/'TEST_RESULTS.json',{'tests':tests,'passed':len(tests),'failures':[],'scope':'Controlled positive fixtures, adversarial negatives and actual trained-model image API. No real planner review manufactured.'})
    print('HANDOFF TESTS PASSED',len(tests),flush=True)
if __name__=='__main__':main()
