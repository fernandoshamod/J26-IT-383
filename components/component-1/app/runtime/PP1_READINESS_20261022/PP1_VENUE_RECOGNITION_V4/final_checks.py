"""Final artifact/schema/admission checks; never reruns final-test detector evaluation."""
from common import *
import ast,math,http.server,functools,threading,urllib.request
from shapely.geometry import shape
checks=[]
def check(name,value):
 checks.append({'check':name,'pass':bool(value)})
 if not value:raise AssertionError(name)
for p in H.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'));check('Python syntax '+p.name,True)
check('prior preservation',read(H/'PRESERVATION.json')['status']=='PASS')
check('independent metric replay',read(H/'objects_v2/INDEPENDENT_METRIC_REPLAY.json')['status']=='PASS')
check('final annotation contract',read(H/'annotations/CONTRACT_TESTS_FINAL_V2.json')['status']=='PASS')
check('V2 annotation JS syntax',read(H/'annotations/UI_SYNTAX_CHECK_V2.json')['exit']==0)
check('corrected integration',read(H/'evidence/INTEGRATION_RESULTS_FINAL.json')['status']=='PASS')
for folder in [H/'integration_final',H/'cli']:
 for p in folder.rglob('UPLOAD_RESULT.json'):
  r=read(p);check(str(p.relative_to(H))+' admission',r['metric_twin_ready'] is False and r['approved'] is False)
  for page in r['pages']:
   bundle=page['candidate_bundle'];objects=bundle['objects'];ids=[o['id'] for o in objects]
   check(str(p.relative_to(H))+' unique candidate IDs page'+str(page['page']),len(ids)==len(set(ids)))
   for c in objects:
    check('candidate geometry/source/state '+c['id'],shape(c['geometry']).is_valid and shape(c['geometry']).area>0 and c['source_sha256']==bundle['source']['sha256'] and c['planner_confirmed'] is False and c['relocation_allowed'] is False and c['metric_geometry'] is None)
frozen=read(H/'objects_v2/CHECKPOINT_FREEZE.json');check('new checkpoint unchanged since pretest freeze',sha(frozen['checkpoint'])==frozen['sha256'])
check('supported class denominator',read(H/'objects_v2/EVALUATION.json')['supported_macro_denominator']==1)
check('no false complete declaration',all(c['status']!='COMPLETE_FOR_DECLARED_TESTED_SCOPE' for c in read(H/'FUNCTIONAL_ACCEPTANCE.json')['capabilities']))
# Local HTTP serving tests file delivery only; do not mistake it for a browser interaction test.
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(H/'annotations')))
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();url='http://127.0.0.1:'+str(server.server_port)+'/REVIEW_V2.html'
try:
 with urllib.request.urlopen(url,timeout=10) as response:payload=response.read();code=response.status
 check('V2 local HTTP exact bytes',code==200 and payload==(H/'annotations/REVIEW_V2.html').read_bytes())
 save('annotations/LOCAL_HTTP_CHECK_V2.json',{'url':url,'status':code,'bytes':len(payload),'sha256':__import__('hashlib').sha256(payload).hexdigest(),'browser_interaction_tested':False,'server_stopped_after_test':True})
finally:server.shutdown();server.server_close();thread.join(timeout=5)
save('FINAL_CHECKS.json',{'status':'PASS','assertions':len(checks),'checks':checks,'note':'Artifact/syntax/admission checks, not independent scientific experiments. No new inference or final-test tuning.'})
print('Final artifact/admission checks PASS',len(checks))
