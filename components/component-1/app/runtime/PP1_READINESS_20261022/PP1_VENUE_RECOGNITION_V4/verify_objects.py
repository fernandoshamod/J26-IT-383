"""Independent saved-output replay. No detector imports or primary metric helper."""
from common import *
import math,collections
raw=read(H/'objects_v2/RAW_TEST_PREDICTIONS.json');reported=read(H/'objects_v2/EVALUATION.json');splits=read(H/'objects_v2/SPLITS.json')
checks=0
def require(v,message):
 global checks
 checks+=1
 if not v:raise AssertionError(message)
group_sets=[{r['technical_source_group'] for r in splits[s]} for s in ['train','val','test']]
require(not(group_sets[0]&group_sets[1] or group_sets[0]&group_sets[2] or group_sets[1]&group_sets[2]),'TECHNICAL_GROUP_LEAK')
source_sets=[{r['source_sha256'] for r in splits[s]} for s in ['train','val','test']]
require(not(source_sets[0]&source_sets[1] or source_sets[0]&source_sets[2] or source_sets[1]&source_sets[2]),'EXACT_BYTE_LEAK')
test={r['id']:r for r in splits['test']};fresh_gt={}
for identity,r in test.items():
 require(sha(r['source'])==r['source_sha256'],'SOURCE_DRIFT');require(sha(r['annotation'])==r['annotation_sha256'],'ANNOTATION_DRIFT')
 boxes=[]
 for line in Path(r['annotation']).read_text().splitlines():
  values=line.split();cls=int(values[0])
  if cls not in [13,18]:continue
  v=[float(x) for x in values[1:]]
  if len(v)==4:
   x,y,w,h=v;box=[(x-w/2)*r['width'],(y-h/2)*r['height'],(x+w/2)*r['width'],(y+h/2)*r['height']]
  else:
   xs=v[::2];ys=v[1::2];box=[min(xs)*r['width'],min(ys)*r['height'],max(xs)*r['width'],max(ys)*r['height']]
  boxes.append(box)
 fresh_gt[identity]=boxes
 require(len(boxes)==len(r['annotations']),'MAPPING_SUPPORT')
def jac(a,b):
 left=max(a[0],b[0]);right=min(a[2],b[2]);top=max(a[1],b[1]);bottom=min(a[3],b[3])
 area=0 if right<=left or bottom<=top else (right-left)*(bottom-top)
 return area/((a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-area)
replayed={}
for method,expected in reported['results'].items():
 rr=[r for r in raw if r['method']==method];require({r['id'] for r in rr}==set(test),'EXACT_MATCHED_TEST_IDS')
 for r in rr:
  gt=fresh_gt[r['id']];require(len(gt)==len(r['ground_truth']),'RAW_GT_COUNT')
  for a,b in zip(gt,r['ground_truth']):require(max(abs(x-y) for x,y in zip(a,b))<1e-8,'ORIGINAL_ANNOTATION_REPLAY')
  for p in r['predictions']:require(p['class_id']==2 and all(math.isfinite(x) for x in p['xyxy']) and 0<=p['confidence']<=1,'PREDICTION_SCHEMA')
 all_dets=[]
 for r in rr:
  all_dets.extend((p['confidence'],r['id'],i,p['xyxy']) for i,p in enumerate(r['predictions']))
 # Stable global confidence order is equivalent to local order + global accumulation.
 all_dets.sort(key=lambda x:-x[0]);support=sum(map(len,fresh_gt.values()));aps=[];fixed=None
 for threshold_index in range(10):
  threshold=(50+5*threshold_index)/100;claimed=collections.defaultdict(set);tp=0;fp=0;recalls=[];precisions=[];tp_fixed=fp_fixed=0
  for confidence,identity,index,bbox in all_dets:
   candidates=[(jac(bbox,g),j) for j,g in enumerate(fresh_gt[identity]) if j not in claimed[identity]]
   candidates.sort(reverse=True);valid=bool(candidates) and candidates[0][0]>=threshold
   if valid:claimed[identity].add(candidates[0][1]);tp+=1
   else:fp+=1
   recalls.append(tp/support);precisions.append(tp/(tp+fp))
   if confidence>=.25:
    if valid:tp_fixed+=1
    else:fp_fixed+=1
  values=[]
  for n in range(101):
   q=n/100;best=0.
   for recall,precision in zip(recalls,precisions):
    if recall>=q and precision>best:best=precision
   values.append(best)
  aps.append(sum(values)/101)
  if threshold_index==0:fixed={'tp':tp_fixed,'fp':fp_fixed,'fn':support-tp_fixed}
 for got,want in zip(aps,expected['ap_per_threshold']):require(abs(got-want)<1e-12,'AP_REPLAY')
 for k,v in fixed.items():require(v==expected['operating025'][k],'FIXED_COUNT_'+k)
 replayed[method]={'ap50':aps[0],'ap50_95':sum(aps)/10,'support':support,'operating025':fixed}
require(reported['supported_macro_denominator']==1,'MACRO_DENOMINATOR')
save('objects_v2/INDEPENDENT_METRIC_REPLAY.json',{'status':'PASS','assertions':checks,'inference_rerun':False,'original_annotation_reopened':True,'primary_metric_helper_used':False,'results':replayed,'scientific_limit':'Verifies numerical agreement with published annotations; cannot certify their completeness, drawing rights, physical source ancestry or object inventory truth.'})
print('Independent replay PASS',checks,'assertions in one replay, not independent experiments')
