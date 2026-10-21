"""Adversarial API, provenance, geometry, XAI, version and persistence tests.
All approvals/calibrations in this suite are labelled synthetic fixtures.
"""
import copy,sqlite3,json,sys,math
from pathlib import Path
from fastapi.testclient import TestClient
from support import PACKAGE,ROOT,save,read,digest,ResearchError
from api import create_app
from fixtures import controlled_registration,optimization,approval,revise
from service import verify_xai_binding
def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output-name',default='ACCEPTANCE');args=parser.parse_args()
    if Path(args.output_name).name!=args.output_name:raise ValueError('OUTPUT_NAME_MUST_BE_DIRECTORY_NAME')
    out=PACKAGE/'outputs'/args.output_name;out.mkdir(parents=True,exist_ok=False);app=create_app(out/'research.sqlite3');c=TestClient(app);s=app.state.service;tests=[];failures=[]
    def check(name,fn):
        try:detail=fn();tests.append({'test':name,'passed':True,'detail':detail});print(name,'PASS',flush=True)
        except Exception as e:
            failures.append({'test':name,'error':type(e).__name__+': '+str(e)});print(name,'FAIL',repr(e),flush=True);save(out/'FAILED_TESTS.json',failures);raise
    def register(reg):
        r=c.post('/twins',json=reg);assert r.status_code==200,r.text;return r.json()
    reg=controlled_registration(out/'fixtures');twin=register(reg);req=optimization(twin);initial=c.post('/optimize',json=req).json();assert initial['status']=='success',initial;save(out/'INITIAL_REQUEST.json',req);save(out/'INITIAL_RESPONSE.json',initial)
    ap=approval(initial);approval_response=c.post('/runs/'+initial['run_id']+'/approve',json=ap);assert approval_response.status_code==200,approval_response.text;approved=approval_response.json();rev=revise(initial,approved,req);adaptive=c.post('/optimize',json=rev).json();assert adaptive['status']=='success',adaptive;save(out/'ADAPTIVE_REQUEST.json',rev);save(out/'ADAPTIVE_RESPONSE.json',adaptive);save(out/'EXPLICIT_SIMULATED_APPROVAL.json',{'request':ap,'response':approved})
    def success():
        assert initial['optimizer_evaluations']==1200 and adaptive['optimizer_evaluations']==1680
        assert len(initial['candidate_layouts'])>=1 and len(adaptive['candidate_layouts'])>=1
        assert all(v['valid'] for r in [initial,adaptive] for v in r['verification'].values())
        return {'initial_alternatives':len(initial['candidate_layouts']),'adaptive_alternatives':len(adaptive['candidate_layouts'])}
    check('actual_initial_adaptive_optimization_and_verification',success)
    def negative(name,payload,expected_http=None,code=None):
        before=s.minimize_calls;r=c.post('/optimize',json=payload);body=r.json()
        if expected_http is not None:assert r.status_code==expected_http,(r.status_code,r.text)
        assert body.get('status')!='success' and not body.get('candidate_layouts'),body
        if code:assert body['reason']==code,(body,code)
        assert s.minimize_calls==before,(name,s.minimize_calls,before)
        return {'http':r.status_code,'reason':body.get('reason'),'actual_optimizer_entries':0}
    def changed(base,fn):q=copy.deepcopy(base);fn(q);return q
    cases=[
      ('unknown_hard_constraint',changed(req,lambda q:q['requirements']['client']['hard'].update(unknown_limit=7)),422,None),
      ('unknown_top_level',changed(req,lambda q:q.update(fake_context=True)),422,None),
      ('unknown_furniture_class',changed(req,lambda q:q['requirements']['quantities'].update(dance_floor=1)),422,None),
      ('boolean_guest_count',changed(req,lambda q:q['requirements'].update(guest_count=True)),422,None),
      ('unsupported_event',changed(req,lambda q:q['requirements'].update(event_type='Concert')),422,None),
      ('quantity_capacity_conflict',changed(req,lambda q:q['requirements']['quantities'].update(chair=159)),200,'FURNITURE_QUANTITY_CAPACITY_CONFLICT'),
      ('client_planner_capacity_conflict',changed(req,lambda q:q['requirements']['client'].update(guest_count=120)),200,'CLIENT_PLANNER_CAPACITY_CONFLICT'),
      ('client_planner_preference_conflict',changed(req,lambda q:q['requirements']['planner'].update(alternative_preference='minimum_disruption')),200,'CLIENT_PLANNER_SOFT_PREFERENCE_CONFLICT'),
      ('pending_client_requirement',changed(req,lambda q:q['requirements']['client'].update(approval_status='pending')),200,'REQUIREMENTS_NOT_APPROVED'),
      ('blank_requirement_provenance',changed(req,lambda q:q['requirements']['client'].update(provenance_ref='   ')),422,None),
      ('clearance_not_relaxed',changed(req,lambda q:q['requirements']['client']['hard'].update(minimum_clearance_m=.1)),200,'CLEARANCE_BELOW_EXPERIMENTAL_MINIMUM'),
      ('reference_missing',changed(rev,lambda q:q.pop('reference')),200,'APPROVED_REFERENCE_REQUIRED'),
      ('reference_approval_fabricated',changed(rev,lambda q:q['reference'].update(approval_id='NOT_AN_APPROVAL')),200,'REFERENCE_NOT_APPROVED'),
      ('reference_hash_changed',changed(rev,lambda q:q['reference'].update(layout_sha256='0'*64)),200,'STALE_OR_UNRELATED_REFERENCE'),
      ('move_permission_missing',changed(rev,lambda q:q.update(permissions=[])),200,'EXPLICIT_ACTION_PERMISSION_REQUIRED'),
      ('move_permission_denied',changed(rev,lambda q:q['permissions'][0].update(approved=False)),200,'EXPLICIT_ACTION_PERMISSION_REQUIRED'),
      ('move_permission_wrong_scope',changed(rev,lambda q:q['permissions'][0].update(scope='EXTERNAL_RESEARCH_REVIEW')),200,'EXPLICIT_ACTION_PERMISSION_REQUIRED'),
      ('protected_group_move',changed(rev,lambda q:q['requirements'].update(protected_group_ids=['seating_group_0013'])),200,'PROTECTED_ID_CHANGE_DENIED'),
      ('protected_chair_move',changed(rev,lambda q:q['requirements'].update(protected_object_ids=['seating_group_0013_chair_01'])),200,'PROTECTED_ID_CHANGE_DENIED'),
      ('unknown_protected_object',changed(rev,lambda q:q['requirements'].update(protected_object_ids=['UNKNOWN'])),200,'UNKNOWN_PROTECTED_OBJECT_ID'),
      ('unsupported_multi_group_revision',changed(rev,lambda q:q.update(affected_group_ids=['seating_group_0013','seating_group_0002'])),200,'LIVE_ADAPTIVE_REQUIRES_ONE_AFFECTED_GROUP')]
    for name,payload,http,code in cases:check(name,lambda p=payload,n=name,h=http,k=code:negative(n,p,h,k))
    # Strict non-finite JSON is rejected before entering optimization.
    def nonfinite():
        q=copy.deepcopy(req);q['requirements']['client']['hard']['minimum_clearance_m']=float('nan');before=s.minimize_calls;r=c.post('/optimize',content=json.dumps(q),headers={'content-type':'application/json'});assert r.status_code==422 and s.minimize_calls==before;return r.json()['reason']
    check('nan_request_rejected',nonfinite)
    real_model=PACKAGE/'outputs/PATH_A_REAL_MODEL'
    def pending_real_gate():
        before=s.minimize_calls;r=c.post('/twins',json={'review':read(real_model/'REVIEW_CALIBRATION_TEMPLATE_PENDING.json'),'candidate_bundle':read(real_model/'CANDIDATE_BUNDLE.json')});assert r.status_code==422 and s.minimize_calls==before;save(out/'PATH_C_PENDING_REAL_REVIEW_REJECTION.json',r.json());return {'real_source_review_supplied':False,'gate':'blocked','optimizer_evaluations':0}
    check('real_model_pending_calibration_and_review_not_approved',pending_real_gate)
    # Calibration/provenance/approval tests exercise actual review gate.
    for name,mutate in [('pending_review',lambda q:q['review']['review'].update(status='pending')),('source_hash_changed',lambda q:q['review']['source'].update(sha256='0'*64)),('declared_dimensions_changed',lambda q:q['review']['source'].update(width_pixels=640)),('inconsistent_controls',lambda q:q['review']['calibration']['controls'][1].update(known_distance_m=100.)),('duplicate_control',lambda q:q['review']['calibration']['controls'].__setitem__(1,copy.deepcopy(q['review']['calibration']['controls'][0]))),('uncertain_venue_object',lambda q:q['review']['objects'][0].update(status='uncertain')),('candidate_bundle_changed',lambda q:q['candidate_bundle'].update(extra='tampering')),('candidate_source_mismatch',lambda q:q['candidate_bundle']['source'].update(sha256='0'*64))]:
        q=copy.deepcopy(reg);mutate(q)
        def f(q=q):
            before=s.minimize_calls;r=c.post('/twins',json=q);assert r.status_code==422 and s.minimize_calls==before,r.text;return r.json()
        check(name,f)
    # Guest reduction preserves every retained polygon and ID, including non-prefix IDs.
    reduction=copy.deepcopy(rev);removed=['seating_group_0003','seating_group_0006','seating_group_0012','seating_group_0018','seating_group_0020'];reduction.update(mode='guest_change',affected_group_ids=[],remove_group_ids=removed,permissions=[dict(group_id=g,action='remove',approved=True,reviewer_id='SIMULATED_FIXTURE_REVIEWER',reason='Explicit simulated attendance reduction',scope='SIMULATED_FIXTURE_REVIEW') for g in removed]);reduction['requirements']['guest_count']=120;reduction['requirements']['quantities']={'round_table':15,'chair':120}
    for origin in ['client','planner']:reduction['requirements'][origin].update(guest_count=120,quantities={'round_table':15,'chair':120})
    reduced=c.post('/optimize',json=reduction).json();save(out/'GUEST_REDUCTION_REQUEST.json',reduction);save(out/'GUEST_REDUCTION_RESPONSE.json',reduced)
    def reduction_check():
        assert reduced['status']=='success',reduced;layout=reduced['candidate_layouts'][0];assert len(layout['objects'])==138 and reduced['optimizer_evaluations']==0 and set(layout['group_centers_m'])==set(initial['candidate_layouts'][0]['group_centers_m'])-set(removed)
        assert reduced['verification'][layout['layout_id']]['locked_object_vertex_changes']==0;return {'objects':138,'removed':removed,'retained_group_ids_preserved':True,'optimizer_evaluations':0,'reason':'Approved removals require no movement of retained objects'}
    check('guest_reduction_live_API_identity_preservation',reduction_check)
    check('guest_reduction_permission_missing',lambda:negative('remove_permission',changed(reduction,lambda q:q.update(permissions=[])),200,'EXPLICIT_ACTION_PERMISSION_REQUIRED'))
    # XAI binding rejects unrelated responses, changed numbers/text and geometry.
    for name,mutate in [('xai_foreign_request',lambda q:None),('xai_corrupted_layout',lambda q:q['candidate_layouts'][0]['objects'][0]['footprint_coordinates_m'][0].__setitem__(0,-5.)),('xai_corrupted_number',lambda q:q['xai']['explanations'][0].update(mean_stage_distance_m=0.)),('xai_corrupted_text',lambda q:q['xai']['explanations'][0].update(text='All objects moved zero metres.'))]:
        q=copy.deepcopy(adaptive);mutate(q);r=copy.deepcopy(rev)
        if name=='xai_foreign_request':r['seed']+=1
        def f(q=q,r=r):
            try:verify_xai_binding(q,r)
            except (ResearchError,ValueError):return 'rejected'
            raise AssertionError('Corrupted explanation accepted')
        check(name,f)
    # Corrupted engine outputs are rejected before successful persistence.
    original_loader=s.engine
    for name,mutate in [('engine_missing_objectives',lambda r:r['candidate_layouts'][0].update(objective_metrics={})),('engine_nan_objective',lambda r:r['candidate_layouts'][0]['objective_metrics'].update(average_stage_distance_m=float('nan'))),('engine_wrong_object_class',lambda r:next(o for o in r['candidate_layouts'][0]['objects'] if o['class']=='round_table').update(**{'class':'podium'})),('engine_wrong_clearance',lambda r:r['candidate_layouts'][0]['objective_metrics'].update(minimum_group_clearance_m=999.))]:
        def poisoned(module_name,mutate=mutate):
            engine=original_loader(module_name);real=engine.run
            def corrupt(request):result=real(request);mutate(result);return result
            engine.run=corrupt;return engine
        s.engine=poisoned
        def f():
            result=c.post('/optimize',json=req).json();assert result['status']!='success' and result['candidate_layouts']==[] and result['optimizer_evaluations']==1200,result;return result['reason']
        try:check(name,f)
        finally:s.engine=original_loader
    # Upper bounds influence actual feasible search; no arbitrary relaxation.
    impossible=copy.deepcopy(req);impossible['requirements']['client']['hard']['maximum_mean_stage_distance_m']=.01
    hard_result=c.post('/optimize',json=impossible).json();save(out/'INFEASIBLE_HARD_LIMIT_RESPONSE.json',hard_result)
    def hard_check():assert hard_result['status']=='infeasible' and not hard_result['candidate_layouts'] and hard_result['optimizer_evaluations']==1200;return {'reason':hard_result['reason'],'evaluations':1200,'global_infeasibility_proven':False}
    check('hard_stage_limit_enforced_by_search',hard_check)
    # Actual different metric geometry flows through gate/adapter/engine.
    other_reg=controlled_registration(out/'fixtures',40,28,'CONTROLLED_40X28');other=register(other_reg);other_req=optimization(other);other_result=c.post('/optimize',json=other_req).json();save(out/'ALTERNATE_METRIC_TWIN_REGISTRATION.json',other_reg);save(out/'ALTERNATE_METRIC_REQUEST.json',other_req);save(out/'ALTERNATE_METRIC_RESPONSE.json',other_result)
    def geometry_check():
        assert other_result['status']=='success',other_result
        assert other_result['actual_boundary_polygon_m']==other['metric_twin']['boundary_polygon_m'] and other_result['actual_boundary_polygon_m']!=initial['actual_boundary_polygon_m'];assert not other_result['provenance']['optimizer_geometry_substituted'];return {'boundary':other_result['actual_boundary_polygon_m'],'verified_alternatives':len(other_result['candidate_layouts']),'source_domain':'controlled_synthetic'}
    check('different_reviewed_metric_geometry_not_substituted',geometry_check)
    # Select-only soft preference changes selected alternative, with same search.
    preference=copy.deepcopy(req)
    for origin in ['client','planner']:preference['requirements'][origin]['alternative_preference']='minimum_disruption'
    preference_result=c.post('/optimize',json=preference).json();save(out/'SOFT_PREFERENCE_RESPONSE.json',preference_result)
    def preference_check():
        assert preference_result['status']=='success';assert [l['group_centers_m'] for l in preference_result['candidate_layouts']]==[l['group_centers_m'] for l in initial['candidate_layouts']]
        chosen=preference_result['verification'][preference_result['selected_layout_id']];assert chosen['assignment_movement']==min(m['assignment_movement'] for m in preference_result['verification'].values());return {'same_search_results':True,'selection_role_only':True,'selected':preference_result['selected_layout_id']}
    check('soft_preference_influences_measured_alternative_selection',preference_check)
    # Earlier protected decisions cannot disappear from a later request.
    protection_req=copy.deepcopy(rev);protection_req['requirements']['protected_group_ids']=['seating_group_0001'];protected_response=c.post('/optimize',json=protection_req).json();assert protected_response['status']=='success'
    protected_approval=c.post('/runs/'+protected_response['run_id']+'/approve',json=approval(protected_response)).json();next_request=revise(protected_response,protected_approval,req,target='seating_group_0001')
    check('protected_decision_cannot_be_dropped_in_next_revision',lambda:negative('protected_history',next_request,200,'PROTECTED_ID_CHANGE_DENIED'))
    # Revocation and stale versions must block before optimizer entry.
    r=c.post('/approvals/'+approved['approval_id']+'/revoke',json={'reviewer_id':'SIMULATED_FIXTURE_REVIEWER','reason':'Explicit regression revocation'});assert r.status_code==200
    check('revoked_reference_denied',lambda:negative('revoked',rev,200,'REFERENCE_NOT_APPROVED'))
    reg2=copy.deepcopy(reg);reg2['review']['venue_version']=2;register(reg2)
    check('stale_twin_request_denied',lambda:negative('stale_twin',req,200,'STALE_VENUE_VERSION'))
    # Recreate the app and verify stored bytes, success-only layouts, and denial records.
    second=TestClient(create_app(out/'research.sqlite3'))
    def storage_check():
        fetched=second.get('/runs/'+adaptive['run_id']).json();assert fetched['response']==adaptive
        with sqlite3.connect(out/'research.sqlite3') as db:rows=db.execute('SELECT status,request_json,response_json,response_sha FROM runs').fetchall()
        for status,request,body,h in rows:
            result=json.loads(body);assert digest(result)==h
            if status!='success':assert result['candidate_layouts']==[]
            else:verify_xai_binding(result,json.loads(request))
        return {'records':len(rows),'success_records':sum(r[0]=='success' for r in rows),'non_success_layouts':0,'app_recreation_roundtrip':True}
    check('sqlite_success_validation_and_denial_persistence',storage_check)
    save(out/'TEST_RESULTS.json',{'tests':tests,'failures':failures,'passed':len(tests),'scope':'Synthetic fixtures and adversarial copies. No actual planner approval claimed.'});print('TOTAL',len(tests),'passed',flush=True)
if __name__=='__main__':main()
