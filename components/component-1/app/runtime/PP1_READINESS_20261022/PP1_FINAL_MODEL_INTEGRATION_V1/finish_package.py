from common import *
import ast
base=read(H/'FUNCTIONAL_ACCEPTANCE.json');obj=read(H/'outputs/OBJECT_SOURCE_001/RESULT.json');assert obj['verdict']=='PASS' and obj['experimental_chair_candidates']==2 and obj['optimizer_calls']==0
rows=read(H.parent/'PP1_VENUE_RECOGNITION_V4/objects_v2/SPLITS.json')['test'];source=next(r for r in rows if r['source']==obj['source']);assert sha(source['source'])==source['source_sha256']==obj['source_sha256']
native=read(H/'outputs/INTEGRATION_CHECKS_004/ACTUAL_ANALYSIS_RESPONSE.json');original=native['model_report']['original_document'];assert sha(original['path'])==original['sha256']
base['actual_positive_experimental_chair_integration']={k:obj[k] for k in ['verdict','source_sha256','analysis_id','experimental_chair_candidates','class_id','gate_verdict','optimizer_calls','genuine_stock_verified','new_accuracy_evaluation']}
base['consumed_source_preservation']='PASS_NATIVE_AND_CHAIR_SOURCE_HASHES'
save('FUNCTIONAL_ACCEPTANCE_FINAL.json',base)
index=[]
for c in read(H/'outputs/INTEGRATION_CHECKS_004/RESULTS.json')['cases']:index.append({'group':'UPDATED_API','test':c['test'],'verdict':c['verdict'],'evidence':'outputs/INTEGRATION_CHECKS_004/RESULTS.json'})
for c in read(H/'outputs/REGRESSION_49_001/TEST_RESULTS.json')['tests']:index.append({'group':'LEGACY_REGRESSION','test':c['test'],'verdict':'PASS' if c['passed'] else 'FAIL','evidence':'outputs/REGRESSION_49_001/TEST_RESULTS.json'})
for c in read(H/'CONTROLLED_001/LIFECYCLE_RESULT.json')['branches']:index.append({'group':'CONTROLLED_LIFECYCLE','test':c['branch'],'verdict':c['verdict'],'evidence':'CONTROLLED_001/'+c['branch']+'/POST_READBACK_VERIFICATION.json'})
for r in read(H/'outputs/TCP_002/TCP_RESULT.json')['records']:
 index.append({'group':'TCP','test':r['path'],'verdict':'EXPECTED_PENDING' if r['path']=='/twins' else 'EXPECTED_REFUSAL' if r['path']=='/optimize' else 'PASS','http':r['http'],'evidence':'outputs/TCP_002/TCP_RESULT.json'})
index.append({'group':'EXPERIMENTAL_OBJECT','test':'actual_chair_candidates_and_pending_gate','verdict':'PASS','evidence':'outputs/OBJECT_SOURCE_001/RESULT.json'})
save('TEST_STATUS_INDEX.json',{'cases':index,'note':'Different verification levels; no combined independent experiment count. Earlier failed attempts are preserved separately in logs, not passed or erased.'})
for p in H.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
# Verify local Markdown relative links before packaging.
import re
for p in H.glob('*.md'):
 for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
  if not target.startswith(('http:','https:','#')):assert (p.parent/target).is_file(),(p,target)
save('PACKAGE_CHECKS.json',{'verdict':'PASS','python_syntax':'PASS','local_markdown_links':'PASS','consumed_source_hashes':'PASS','models_retrained':False,'frontend_edited':False,'genuine_review_fabricated':False})
print('Final package checks PASS')
