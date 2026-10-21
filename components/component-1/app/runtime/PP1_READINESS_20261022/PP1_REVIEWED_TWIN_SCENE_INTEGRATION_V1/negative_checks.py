"""Independent field replay plus adversarial admission copies. No optimizer mocks."""
import sys,copy,json,sqlite3,traceback,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H.parent/'PP1_EAG_APR_IMPLEMENTATION_V1'))
import runtime
runtime.common.HERE=H;runtime.bridge.HERE=H
import adapter
from independent_mapping import verify
out=H/(sys.argv[1] if len(sys.argv)>1 else 'ADMISSION_TESTS_002');out.mkdir(exist_ok=False)
binding=adapter.read(H/'CONTROLLED_003/HTTP_ADAPTER/LIVE_BINDING.json');receipt=adapter.read(H/'HTTP/TWIN_RECEIPT.json');packet=adapter.read(H/'CONTROLLED_003/A_INITIAL/INPUT.json');cases=[]
def record(name,fn,expected_error=None):
 try:
  detail=fn()
  assert expected_error is None,('FALSE_PASS',name)
  cases.append(dict(test=name,status='PASS',detail=detail))
 except Exception as e:
  if expected_error and expected_error in str(e):cases.append(dict(test=name,status='EXPECTED_REFUSAL',reason=str(e),optimizer_evaluations=0))
  else:
   adapter.write(out/'FAILURE.json',dict(test=name,traceback=traceback.format_exc(),prior=cases));raise
 print(name,cases[-1]['status'],flush=True)
def positive():
 v=verify(receipt,packet['scene']);assert v['valid'],v
 # Poisoning the geometry must fail this separate oracle, not only admission.
 bad=copy.deepcopy(packet['scene']);bad['venue']['existing'][0]['footprint_m'][0][0]+=.01
 assert not verify(receipt,bad)['valid']
 return v
record('independent_scalar_mapping_and_poisoned_geometry_oracle',positive)
def allocations():
 result=adapter.read(H/'CONTROLLED_003/A_INITIAL/RESULT.json');spec=result['spec']
 ids=[a['instance_id'] for a in spec['allocations']];assert len(ids)==len(set(ids))
 assert spec['required_quantities']==dict(round_table=10,chair=80,stage=1,buffet_counter=1)
 assert len(spec['retained_existing'])==3
 reused=[a for a in spec['allocations'] if a['origin']=='observed_existing'];assert len(reused)==2
 assert set(a['instance_id'] for a in reused)=={'existing_stage','existing_buffet_1'}
 assert len(spec['new_equipment'])==90
 assert all(o['protected'] and o['status']=='fixed' for o in spec['retained_existing'])
 return dict(required=spec['required_quantities'],reused_ids=[a['instance_id'] for a in reused],surplus='existing_buffet_2 retained locked, not counted as active supply',new_equipment=90)
record('independent_stock_counts_no_double_counting_and_fixed_locks',allocations)
record('fresh_registered_admission_replay',lambda:adapter.verify_scene(packet,binding))
bad=copy.deepcopy(packet);bad['scene']['venue']['boundary_m'][0][0]+=.01
record('metric_geometry_tamper',lambda:adapter.verify_scene(bad,binding),'SCENE_VENUE_CHANGED')
bad=copy.deepcopy(packet);bad['scene']['venue']['existing'][0]['protected']=False
record('protected_object_downgrade',lambda:adapter.verify_scene(bad,binding),'SCENE_VENUE_CHANGED')
badreceipt=copy.deepcopy(receipt);badreceipt['metric_twin']['candidate_bundle']['objects'][0]['id']='TAMPERED'
record('receipt_prediction_provenance_tamper',lambda:adapter.current(badreceipt,H/'HTTP/research.sqlite3'),'RECEIPT_REGISTERED_BODY_MISMATCH')
def clone_db(name,body,version=None):
 p=out/(name+'.sqlite3')
 with sqlite3.connect(p) as db:
  db.execute('CREATE TABLE twins(venue_id TEXT,version INTEGER,sha TEXT,body TEXT)')
  db.execute('INSERT INTO twins VALUES(?,?,?,?)',(receipt['venue_id'],version or receipt['venue_version'],adapter.digest(body),json.dumps(body)))
 return p
p=clone_db('stale',receipt['metric_twin'],2)
record('stale_http_twin_version',lambda:adapter.current(receipt,p),'REVIEWED_TWIN_NOT_REGISTERED')
def evidence_case():
 t=copy.deepcopy(receipt['metric_twin']);original=t['review_record']['evidence_artifacts'][0]
 p=out/'TAMPERED_REVIEW_DOCUMENT.json';p.write_text('tampered evidence')
 original['path']=str(p);t['review_record_sha256']=adapter.digest(t['review_record'])
 r=copy.deepcopy(receipt);r['metric_twin']=t;r['twin_sha256']=adapter.digest(t)
 db=clone_db('tampered_evidence',t)
 adapter.current(r,db)
record('tampered_source_bound_evidence_file',evidence_case,'EVIDENCE_FILE_HASH_MISMATCH')
revoked=out/'REVOKED_AUTHORITY.json';adapter.write(revoked,dict(status='revoked',twin_sha256=binding['twin_sha256'],scope='SIMULATED_FIXTURE'))
badbinding=copy.deepcopy(binding);badbinding['authority_state_path']=str(revoked)
record('revoked_adapter_authority',lambda:adapter.verify_scene(packet,badbinding),'ADAPTER_AUTHORITY_REVOKED')
def missing_stock():
 brief=adapter.read(H/'SCENE_BRIEF.json');brief['venue']['existing'].append(copy.deepcopy(brief['venue']['existing'][0]));brief['venue']['existing'][-1]['instance_id']='EXPERIMENTAL_CHAIR_NOT_REVIEWED'
 return adapter.convert(receipt,H/'HTTP/research.sqlite3',brief,out/'EXTRA_STOCK')
record('unregistered_experimental_symbol_cannot_become_stock',missing_stock,'UNREGISTERED_STOCK_OR_MISSING_OBJECT')
def unsupported_status():
 from contracts import TwinReview
 from review_gate import reviewed_metric_twin
 r=copy.deepcopy(receipt['metric_twin']['review_record']);r['objects'][0]['status']='uncertain'
 return reviewed_metric_twin(TwinReview.model_validate(r),receipt['metric_twin']['candidate_bundle'])
record('uncertain_http_object_is_not_approved_stock',unsupported_status,'UNRESOLVED_OR_UNSUPPORTED_VENUE_OBJECT_STATUS')
def missing_measurement():
 from contracts import TwinReview
 r=copy.deepcopy(receipt['metric_twin']['review_record']);r['calibration']['controls'][0]['known_distance_m']=None
 return TwinReview.model_validate(r)
record('missing_measurement_schema_refusal',missing_measurement,'known_distance_m')
def permission_refusal():
 from repair import run
 ref=adapter.read(H/'CONTROLLED_003/APPROVED_REFERENCE.json')
 p=adapter.read(H/'CONTROLLED_003/D_AUTHORIZED_SINGLETON/INPUT.json')
 p['context']['allowed_groups']=[]
 p=runtime.seal_packet(p['scene'],p['context'],out/'MISSING_MOVE_PERMISSION')
 adapter.verify_scene(p,binding)
 result,graph=run(p,out/'MISSING_MOVE_PERMISSION_EXECUTION','EAG',20261017,ref)
 assert result['status']=='refused' and result['optimizer_evaluations']==0 and result['optimizer_calls']==0
 assert 'MOVE_PERMISSION_REQUIRED' in [r['code'] for r in result['reasons']]
 return dict(status=result['status'],evaluations=0,reasons=result['reasons'],persisted=True)
record('actual_eag_missing_singleton_permission_refused_and_saved',permission_refusal)
adapter.write(out/'RESULTS.json',dict(cases=cases,passed=True,optimizer_calls=0,scope='Controlled fixture and adversarial copies; not genuine venue validation'))
