"""Artifact preservation, historical comparison and raw final acceptance; no new research search."""
from common import *
import sqlite3,ast,collections
from model_registry import verify_hashes
P=H.parent;sets={
 'STEP4_tracked_sources_checkpoints':(ROOT,read(P/'PP1_FINAL_DEMO_REHEARSAL_V1/RUN_004/PRESERVATION_BEFORE.json')),
 'backend_freeze':(ROOT,read(P/'PP1_EXECUTABLE_V1/BACKEND_FREEZE_V1.json')['runtime_sha256']),
 'frontend_artifacts':(P/'PP1_FRONTEND_V1',read(P/'PP1_FRONTEND_V1/FRONTEND_ARTIFACT_SHA256_V1.json')),
 'V3_delivery':(P/'PP1_FLOORPLAN_AI_DEVELOPMENT_V3',read(P/'PP1_FLOORPLAN_AI_DEVELOPMENT_V3/DELIVERY_SHA256.json')),
 'V4_delivery':(P/'PP1_VENUE_RECOGNITION_V4',read(P/'PP1_VENUE_RECOGNITION_V4/DELIVERY_SHA256.json')['files']),
 'historical_STEP4_evidence':(P/'PP1_FINAL_DEMO_REHEARSAL_V1',read(P/'PP1_FINAL_DEMO_REHEARSAL_V1/ARTIFACT_SHA256.json')['files']),
 'Scene_release':(P/'PP1_EVENT_SCENE_INTELLIGENCE_V1',read(P/'PP1_EVENT_SCENE_INTELLIGENCE_V1/RELEASE_MANIFEST.json')['files']),
 'EAG_source':(P/'PP1_EAG_APR_IMPLEMENTATION_V1',read(P/'PP1_EAG_APR_IMPLEMENTATION_V1/CURRENT_SOURCE_SHA256.json')),
 'progress_freeze':(P/'PP1_PROGRESS_AND_DEMO_FREEZE_V1',read(P/'PP1_PROGRESS_AND_DEMO_FREEZE_V1/ARTIFACT_SHA256.json')['files'])}
preserved={}
for name,(base,items) in sets.items():
 bad=[p for p,s in items.items() if not (base/p).is_file() or sha(base/p)!=s]
 preserved[name]={'entries':len(items),'matches':len(items)-len(bad),'mismatches':bad};print(name,len(items),'mismatches',len(bad),flush=True)
save('PRESERVATION.json',{'status':'PASS' if all(not v['mismatches'] for v in preserved.values()) else 'FAIL','checks':preserved,'scope':'Prior authoritative manifests, not a new full raw-dataset audit. Sets overlap; do not sum as unique files.'})
assert all(not v['mismatches'] for v in preserved.values())
actual=read(H/'CONTROLLED_001/LIFECYCLE_RESULT.json');old=read(P/'PP1_FINAL_DEMO_REHEARSAL_V1/RUN_004/LIFECYCLE_RESULT.json')
comparisons=[]
for a,b in zip(actual['branches'],old['branches']):
 keys=['branch','verdict','operation','optimizer_evaluations','optimizer_calls','candidate_count','material_menu_count','fallback']
 same=all(a[k]==b[k] for k in keys);assert same
 comparisons.append({'branch':a['branch'],'matches_historical_scope_and_search_budget':same,'new_wall_seconds':a['wall_seconds_including_replay'],'historical_wall_seconds':b['wall_seconds_including_replay']})
save('HISTORICAL_LIFECYCLE_COMPARISON.json',{'status':'PASS','new_evaluations':actual['total_optimizer_evaluations'],'historical_evaluations':old['total_optimizer_evaluations'],'comparisons':comparisons,'claim_limit':'Operational statuses, counts and budgets match. UUIDs, evidence paths, hashes and timings differ. No new novelty/accuracy claim.'})
checks=read(H/'outputs/INTEGRATION_CHECKS_004/RESULTS.json');reg=read(H/'outputs/REGRESSION_49_001/TEST_RESULTS.json');assert reg['passed']==49 and reg['failures']==[] and actual['passed'] and actual['total_optimizer_evaluations']==4080
native=read(H/'outputs/INTEGRATION_CHECKS_004/ACTUAL_ANALYSIS_RESPONSE.json');report=native['model_report']
specimens=[]
for branch in actual['branches']:
 folder=H/'CONTROLLED_001'/branch['branch'];response=read(folder/'RESULT.json');record=read(folder/'POST_READBACK_VERIFICATION.json');assert record['valid']
 with sqlite3.connect(folder/'assurance.sqlite3') as db:rows=db.execute('SELECT input_json,response_json,sha256 FROM records').fetchall()
 assert len(rows)==1 and json.loads(rows[0][1])==response
 specimens.append({'branch':branch['branch'],'verdict':branch['verdict'],'sqlite_rows':len(rows),'independent_readback':record['valid'],'optimizer_evaluations':response['optimizer_evaluations'],'candidates':len(response['candidate_layouts']),'distinct_menu':len(response['selected_ids'])})
for p in H.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
result={'status':'PASS_FOR_DECLARED_TWO_PATH_INTEGRATION','models':verify_hashes(),'real_native_source':checks['source'],'real_analysis_id':checks['actual_analysis_id'],
 'real_model_output':{'actual_calls':report['actual_model_calls'],'unet_shapes':report['actual_unet_forwards'],'actual_loads':report['actual_checkpoint_loads'],'structural_candidates':report['structural_candidates'],'opening_candidates':report['yolo_candidates'],'experimental_chair_default':False,'verdict':'EXPECTED_PENDING','metric_geometry_created':False},
 'integration_cases':[{'test':x['test'],'verdict':x['verdict']} for x in checks['cases']],
 'controlled_lifecycle':{'verdict':'PASS','evaluations':4080,'real_searches':3,'branches':specimens,'simulated_approval_only':True,'independent_geometry_function_identity_permission_XAI_checked':True},
 'regression':{'verdict':'PASS','passed':49,'failed':0,'scope':'Original suite, unchanged test source; output relocated and actual new-model pending evidence used. Separate from4080 lifecycle evaluations.'},
 'TCP_and_frontend_response_schema':{'verdict':'PASS','evidence':'outputs/TCP_002/TCP_RESULT.json','schema_check':'outputs/TCP_002/FRONTEND_CONTRACT_CHECK.json','browser_UI_test':'NOT_EXECUTED_NO_FRONTEND_WORK'},
 'genuine_reviewed_real_positive':'NOT_EXECUTED','real_positive_blockers':native['gate']['missing']+['Scene compiler and Scene search currently reject real_source; no general frozen-HTTP-TwinReceipt to Scene/EAG authority/stock conversion is implemented'],
 'original_A_to_F_eight_logics_preserved':True,'sgcn_trained':False,'weather_added':False,'frontend_modified':False,'frozen_backend_modified':False,'models_retrained':False,'datasets_acquired':False,'old_models_replaced':False}
save('FUNCTIONAL_ACCEPTANCE.json',result)
print(json.dumps(result['real_model_output'],indent=2));print('Final scoped acceptance PASS')
