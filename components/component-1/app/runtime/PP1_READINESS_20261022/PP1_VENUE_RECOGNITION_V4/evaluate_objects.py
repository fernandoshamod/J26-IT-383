"""One frozen held-out comparison, same input/geometry/thresholds for both local models."""
import platform,time
from common import *
platform.uname();events=guard()
import torch,numpy as np
from PIL import Image,ImageDraw
from ultralytics import YOLO
torch.set_num_threads(4)
freeze=read(H/'objects_v2/CHECKPOINT_FREEZE.json');assert sha(freeze['checkpoint'])==freeze['sha256']
parts=read(H/'objects_v2/SPLITS.json');raw=[]
models={'synthetic12_baseline':ROOT/'PP1_READINESS_20261022/PP1_MODEL_DEVELOPMENT_V2/yolo/rare_resample_finetune/weights/best.pt','published_chair_pilot':Path(freeze['checkpoint'])}
save('objects_v2/EVALUATION_FREEZE.json',{'models':{k:{'path':str(p),'sha256':sha(p)} for k,p in models.items()},'split_sha256':sha(H/'objects_v2/SPLITS.json'),'imgsz':640,'device':0,'conf_raw':.001,'conf_operating':.25,'nms_iou':.7,'max_det':300,'metric':'confidence-ordered greedy per-image matching; macro over supported chair only, 101 recall point mean interpolated AP at IoU .50:.05:.95','known_ground_truth_limit':'Unlabelled visible dining chairs exist: FP/FN/AP are agreement with published annotations, NOT certified physical-chair accuracy; no all12 macro'})
for method,path in models.items():
 model=YOLO(str(path));expected_id=2 if method=='synthetic12_baseline' else 0
 assert model.names[expected_id]=='chair';t=time.perf_counter()
 for i,r in enumerate(parts['test']):
  assert sha(r['source'])==r['source_sha256']
  pred=model.predict(r['source'],imgsz=640,conf=.001,iou=.7,max_det=300,device=0,half=False,verbose=False,save=False)[0]
  selected=[{'class_id':2,'confidence':float(s),'xyxy':v} for v,c,s in zip(pred.boxes.xyxy.tolist(),pred.boxes.cls.tolist(),pred.boxes.conf.tolist()) if int(c)==expected_id]
  row={'method':method,'id':r['id'],'source':r['source'],'source_sha256':r['source_sha256'],'annotation_sha256':r['annotation_sha256'],'size_wh':[r['width'],r['height']],'group':r['technical_source_group'],'ground_truth':[a['bbox_pixels'] for a in r['annotations']],'predictions':selected,'all_classes_emitted':{model.names[int(c)]:int((pred.boxes.cls==c).sum()) for c in pred.boxes.cls.unique().tolist()}}
  raw.append(row)
  if i<12:
   im=Image.open(r['source']).convert('RGB');d=ImageDraw.Draw(im)
   for b in row['ground_truth']:d.rectangle(b,outline='lime',width=2)
   for b in selected:
    if b['confidence']>=.25:d.rectangle(b['xyxy'],outline='red',width=2);d.text(tuple(b['xyxy'][:2]),format(b['confidence'],'.2f'),fill='red')
   folder=H/'objects_v2/predictions'/method;folder.mkdir(parents=True,exist_ok=True);im.save(folder/(r['id']+'.png'))
 print(method,'completed',len(parts['test']),'in',time.perf_counter()-t,flush=True)
save('objects_v2/RAW_TEST_PREDICTIONS.json',raw)
def overlap(a,b):
 v=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]));u=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-v
 return v/u if u>0 else 0.
results={};errors=[]
for method in models:
 rr=[r for r in raw if r['method']==method];support=sum(len(r['ground_truth']) for r in rr);aps=[];counts={}
 for ti in range(10):
  threshold=.5+.05*ti;ordered=[]
  for r in rr:
   used=set()
   for pi,p in sorted(enumerate(r['predictions']),key=lambda p:-p[1]['confidence']):
    score,j=max(((overlap(p['xyxy'],g),j) for j,g in enumerate(r['ground_truth']) if j not in used),default=(0.,-1))
    ok=score>=threshold
    if ok:used.add(j)
    ordered.append((p['confidence'],ok))
    if ti==0 and p['confidence']>=.25:errors.append({'method':method,'record':r['id'],'kind':'TP_PUBLISHED_MATCH' if ok else 'FP_AGAINST_PUBLISHED_LABELS_NOT_CERTIFIED_TRUE_FP','prediction_index':pi,'match_index':j if ok else None,'iou':score})
   if ti==0:
    matched_at025=set()
    for p in sorted((p for p in r['predictions'] if p['confidence']>=.25),key=lambda p:-p['confidence']):
     score,j=max(((overlap(p['xyxy'],g),j) for j,g in enumerate(r['ground_truth']) if j not in matched_at025),default=(0.,-1))
     if score>=.5:matched_at025.add(j)
    for j in range(len(r['ground_truth'])):
     if j not in matched_at025:errors.append({'method':method,'record':r['id'],'kind':'FN_PUBLISHED_LABEL','ground_truth_index':j})
  ordered.sort(key=lambda p:-p[0]);tp=np.cumsum([int(v) for s,v in ordered]);fp=np.cumsum([int(not v) for s,v in ordered]);recall=tp/max(1,support);precision=tp/np.maximum(1,tp+fp)
  aps.append(float(np.mean([max(precision[recall>=x],default=0.) for x in np.linspace(0,1,101)])))
  if ti==0:
   fixed=[x for x in ordered if x[0]>=.25];ntp=sum(x[1] for x in fixed);nfp=len(fixed)-ntp
   counts={'tp':ntp,'fp':nfp,'fn':support-ntp,'precision':ntp/max(1,ntp+nfp),'recall':ntp/max(1,support),'negative_images':sum(not r['ground_truth'] for r in rr),'negative_images_with_predictions':sum(not r['ground_truth'] and any(p['confidence']>=.25 for p in r['predictions']) for r in rr)}
 results[method]={'support':support,'images':len(rr),'ap50':aps[0],'ap50_95':float(np.mean(aps)),'ap_per_threshold':aps,'operating025':counts}
save('objects_v2/EVALUATION.json',{'supported_class':'chair','supported_macro_denominator':1,'results':results,'remaining11classes':'NOT_VALIDATED','interpretation':'Published-label reproduction only; label incompleteness, unverified original rights/venue ancestry prevent all-inventory or clean independent venue accuracy claim'})
save('objects_v2/ALL_MATCHES_AND_ERRORS.json',errors);save('objects_v2/EVALUATION_GUARD.json',events)
print(json.dumps(results,indent=2))
