"""Contract controls are simulated, never genuine human/planner reviews."""
from common import *
import copy
from annotation_contract import validate_annotation
tasks=read(H/'annotations/TASKS_V2.json');task=tasks[0]
base={'schema':'SOURCE_BOUND_HUMAN_ANNOTATION_V1','task_id':task['task_id'],'source_sha256':task['source_sha256'],'source_width':task['width'],'source_height':task['height'],
 'reviewer':'SIMULATED_CONTRACT_TEST_ONLY','attested_human_review':True,'notes':'Simulated input to test syntax/geometry gate only; no human review occurred.','reviewed_classes':task['classes'],'inventory_authority':'UNKNOWN_NOT_PHYSICAL_STOCK',
 'annotations':[{'id':'CONTROL','class':'chair','origin':'HUMAN_DRAWN_OR_HUMAN_REVIEWED_PUBLISHED_LABEL','geometry':{'type':'Polygon','coordinates':[[[10,10],[30,10],[30,30],[10,30],[10,10]]]}}],
 'class_review_status':{k:'PRESENT_ANNOTATED' if k=='chair' else 'UNKNOWN' for k in task['classes']}}
cases=[]
def check(name,r,expected):
 try:
  result=validate_annotation(task,r);actual=True
 except (ValueError,AssertionError,TypeError) as e:result={'rejection':str(e)};actual=False
 cases.append({'case':name,'expected_valid':expected,'actual_valid':actual,'pass':expected==actual,'detail':result});assert expected==actual,name
check('SIMULATED_STRUCTURAL_POSITIVE_NOT_HUMAN_REVIEW',base,True)
for name,field,value in [('missing_reviewer','reviewer',''),('missing_attestation','attested_human_review',False),('wrong_source','source_sha256','0'*64),('wrong_dimensions','source_width',1),('incomplete_target_review','reviewed_classes',['chair']),('no_notes','notes',''),('invented_stock_authority','inventory_authority','VERIFIED_EXISTING_STOCK')]:
 r=copy.deepcopy(base);r[field]=value;check(name,r,False)
for name,edit in [('unsupported_class',lambda a:a.update({'class':'weather_safe'})),('pseudo_label',lambda a:a.update({'origin':'AI_PREDICTION_UNVERIFIED'})),('outside_image',lambda a:a['geometry'].update({'coordinates':[[[-1,0],[30,0],[30,30],[-1,0]]]})),('self_intersection',lambda a:a['geometry'].update({'coordinates':[[[0,0],[30,30],[0,30],[30,0],[0,0]]]}))]:
 r=copy.deepcopy(base);edit(r['annotations'][0]);check(name,r,False)
r=copy.deepcopy(base);r['annotations']*=2;check('duplicate_identity',r,False)
r=copy.deepcopy(base);r['annotations']=[];r['class_review_status']={k:'UNKNOWN' for k in task['classes']};check('UNKNOWN_IS_NOT_NEGATIVE_TRAINING_LABEL',r,True)
assessment=validate_annotation(task,r);assert not assessment['training_eligible'] and not any(assessment['training_eligibility_by_class'].values())
r=copy.deepcopy(base);r['class_review_status']['chair']='ABSENT_CONFIRMED';check('ANNOTATED_OBJECT_CANNOT_BE_DECLARED_ABSENT',r,False)
save('annotations/CONTRACT_TESTS_FINAL_V2.json',{'status':'PASS','cases':cases,'real_human_annotations_created':0,'genuine_planner_approvals_created':0,'note':'Simulated contract controls only; no human review occurred. Unknown class never becomes a negative. SCUT reference targets blocked for raw-raster training.'})
# JS syntax validation is not browser acceptance.
import re,subprocess
html=(H/'annotations/REVIEW_V2.html').read_text(encoding='utf-8');script=re.search(r'<script>(.*)</script>',html,re.S).group(1)
p=H/'annotations/UI_SYNTAX_ONLY_V2.js';p.write_text(script,encoding='utf-8')
node=ROOT/'PP1_READINESS_20261022/PP1_FRONTEND_V1/tooling/node-v22.23.3-win-x64/node.exe'
result=subprocess.run([str(node),'--check',str(p)],cwd=ROOT,capture_output=True,text=True)
save('annotations/UI_SYNTAX_CHECK_V2.json',{'argv':[str(node),'--check',str(p)],'exit':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'browser_test':'NOT_EXECUTED: cua inventory has no browsers, createBrowserTab(iab) reports Browser is not available: iab'})
assert result.returncode==0,result.stderr
print(len(cases),'annotation contract cases PASS; JS syntax PASS; browser unavailable')
