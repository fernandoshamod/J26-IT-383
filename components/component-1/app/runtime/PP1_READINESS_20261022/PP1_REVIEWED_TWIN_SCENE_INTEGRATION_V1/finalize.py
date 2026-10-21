"""Independent raw replay and source preservation; no searches or inference."""
import sys,json,sqlite3,hashlib,ast
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
sys.path.insert(0,str(H.parent/'PP1_EAG_APR_IMPLEMENTATION_V1'))
import runtime
runtime.common.HERE=H;runtime.bridge.HERE=H
import adapter
from independent_mapping import verify
from independent import verify_candidate,verify_envelope
out=H/'CONTROLLED_003';receipt=adapter.read(H/'HTTP/TWIN_RECEIPT.json');binding=adapter.read(out/'HTTP_ADAPTER/LIVE_BINDING.json');life=adapter.read(out/'LIFECYCLE_RESULT.json');ref=adapter.read(out/'APPROVED_REFERENCE.json');initial_ref=adapter.read(out/'INITIAL_REFERENCE.json');records=[]
dbpath=H/'ADAPTER_RESULTS.sqlite3'
assert not dbpath.exists()
with sqlite3.connect(dbpath) as ledger:
 ledger.execute('CREATE TABLE admitted_results(branch TEXT PRIMARY KEY,input_sha TEXT,response_sha TEXT,binding_sha TEXT,record_json TEXT)')
 for branch in life['branches']:
  folder=out/branch['branch'];packet=adapter.read(folder/'INPUT.json');result=adapter.read(folder/'RESULT.json')
  admission=adapter.verify_scene(packet,binding)
  scalar=verify(receipt,packet['scene']);assert scalar['valid'],scalar
  r=None if branch['branch']=='A_INITIAL' else initial_ref if branch['branch']=='B_SIMULATED_APPROVAL' else ref
  envelope=verify_envelope(packet,result,r);assert envelope['valid'],envelope
  validations={}
  for layout in result['candidate_layouts']:
   target=packet['context']['requested_group'] if result['operation']=='SELECTIVE_SINGLETON' else None
   v=verify_candidate(packet,result['spec'],layout,result['initialization_centers_m'],r,target)
   assert v['valid'] and v==result['validation'][layout['layout_id']],v
   validations[layout['layout_id']]=v
  with sqlite3.connect(folder/'assurance.sqlite3') as db:rows=db.execute('SELECT input_json,response_json,sha256 FROM records').fetchall()
  assert len(rows)==1 and json.loads(rows[0][0])==packet and json.loads(rows[0][1])==result and rows[0][2]==adapter.digest(result)
  fresh=adapter.read(folder/'ADAPTER_ADMISSION_REPLAY.json');assert fresh['before']==fresh['after'] and fresh['original_result_sha256']==adapter.digest(result)
  record=dict(branch=branch['branch'],status=branch['verdict'],admission=admission,scalar_mapping=scalar,envelope=envelope,independent_candidates=validations,exact_sqlite_readback=True,input_sha256=adapter.digest(packet),response_sha256=adapter.digest(result),mapping_sha256=adapter.digest(binding),evaluations=result['optimizer_evaluations'],candidate_count=len(result['candidate_layouts']),material_choices=len(result['selected_ids']))
  ledger.execute('INSERT INTO admitted_results VALUES(?,?,?,?,?)',(branch['branch'],adapter.digest(packet),adapter.digest(result),adapter.digest(binding),json.dumps(record)))
  records.append(record)
with sqlite3.connect(dbpath) as db:
 rows=db.execute('SELECT record_json FROM admitted_results ORDER BY branch').fetchall();assert [json.loads(row[0]) for row in rows]==records
adapter.write(H/'INDEPENDENT_FINAL_REPLAY.json',dict(status='PASS',branches=records,sqlite_ledger=str(dbpath),exact_ledger_readback=True,scope='Explicitly controlled registered HTTP Twin; no external venue validity claim'))
# Original manifests are authorities for the frozen sources, not a new dataset audit.
preserved=[]
def manifest_check(label,base,path,key=None):
 values=adapter.read(path);values=values[key] if key else values
 bad=[name for name,expected in values.items() if adapter.filehash(base/name)!=expected]
 assert not bad,(label,bad)
 preserved.append(dict(label=label,files=len(values),mismatches=bad,status='PASS'))
manifest_check('new_task_before_snapshot',Path(''),H/'PRESERVATION_BEFORE.json')
manifest_check('prior_model_integration_delivery',H.parent/'PP1_FINAL_MODEL_INTEGRATION_V1',H.parent/'PP1_FINAL_MODEL_INTEGRATION_V1/DELIVERY_SHA256.json','files')
manifest_check('frozen_frontend',H.parent/'PP1_FRONTEND_V1',H.parent/'PP1_FRONTEND_V1/FRONTEND_ARTIFACT_SHA256_V1.json')
manifest_check('frozen_backend',ROOT,H.parent/'PP1_EXECUTABLE_V1/BACKEND_FREEZE_V1.json','runtime_sha256')
adapter.write(H/'PRESERVATION_AFTER.json',dict(status='PASS',sets=preserved,sets_overlap=True,full_raw_dataset_bytewise_audit=False))
reg=adapter.read(H/'outputs/REGRESSION_49_001/TEST_RESULTS.json');assert reg['passed']==49 and not reg['failures']
negative=adapter.read(H/'ADMISSION_TESTS_002/RESULTS.json');assert negative['passed']
pending=adapter.read(H/'PATH_A/RESULT.json');assert pending['optimizer_calls']==0
tcp=adapter.read(H/'TCP_PROOF/RESULT.json');assert tcp['status']=='PASS'
for p in H.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
adapter.write(H/'FUNCTIONAL_ACCEPTANCE.json',dict(status='PASS_FOR_CONTROLLED_REGISTERED_HTTP_TWIN_TO_SCENE_EAG_SCOPE',adapter_version=adapter.VERSION,controlled_branches=[{k:b[k] for k in ['branch','verdict','operation','optimizer_evaluations','candidate_count','material_menu_count']} for b in life['branches']],optimizer_evaluations=life['total_optimizer_evaluations'],search_calls=life['actual_search_calls'],candidate_occurrences=life['successful_candidate_occurrences'],occurrences_not_independent_experiments=True,regression_passed=49,admission_cases=len(negative['cases']),path_a=pending['status'],genuine_external_venue='NOT_EXECUTED_NO_GENUINE_INPUTS_AND_DOWNSTREAM_SCOPE_RESTRICTED',tcp='PASS',frontend_browser='NOT_EXECUTED',preservation=preserved,independent_replay='INDEPENDENT_FINAL_REPLAY.json',models_retrained=False,novelty='UNRESOLVED',eight_logic_architecture_changed=False))
print('Final raw replay, 7 ledger rows, 49 regression and preservation PASS')
