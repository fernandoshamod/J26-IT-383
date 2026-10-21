"""Independent local evaluation of two native structural-symbol classes."""
import platform,time
from common import *
platform.uname();events=guard()
import torch,numpy as np
from PIL import Image
from ultralytics import YOLO
torch.set_num_threads(4)
trained=read(H/"symbols/TRAINING_RESULT.json");model=YOLO(trained["checkpoint"]);start=time.perf_counter()
data=read(H/"symbols/DATASET.json")
metrics=model.val(data=str(H/"symbols/data.yaml"),split="test",imgsz=960,batch=4,device=0,workers=0,conf=.001,iou=.7,plots=False,save_json=False,
 project=str(H/"symbols"),name="heldout_evaluation",exist_ok=False,verbose=False,half=False)
save("symbols/EVALUATION.json",{"metrics":{k:float(v) for k,v in metrics.results_dict.items()},"class_indices":metrics.box.ap_class_index.tolist(),"precision_best_f1":metrics.box.p.tolist(),"recall_best_f1":metrics.box.r.tolist(),"ap50":metrics.box.ap50.tolist(),"ap50_95":metrics.box.ap.tolist(),"support":data["support"]["test"],"seconds":time.perf_counter()-start,"checkpoint_sha256":sha(trained["checkpoint"]),"scope":"Two native opening classes on64heldout native-raster source groups; not twelve-event-object mAP; not a clean external dataset transfer claim."})
raw=[]
for i,r in enumerate(data["partitions"]["test"]):
 prediction=model.predict(r["image"],imgsz=960,conf=.001,iou=.7,max_det=300,device=0,verbose=False,save=False)[0]
 b=prediction.boxes
 raw.append({"id":r["id"],"source_image":r["source_image"],"source_sha256":r["source_sha256"],"size_wh":list(prediction.orig_shape[::-1]),"normalized_gt":r["boxes"],"predictions":[{"class_id":int(c),"confidence":s,"xyxy":v} for v,c,s in zip(b.xyxy.cpu().tolist(),b.cls.cpu().tolist(),b.conf.cpu().tolist())]})
 if i<8:
  p=H/"symbols/predictions";p.mkdir(exist_ok=True);Image.fromarray(prediction.plot()[:,:,::-1]).save(p/(r["id"]+".png"))
save("symbols/RAW_TEST_PREDICTIONS.json",raw)
# Independent scalar original-coordinate matching and AP, without library AP helpers.
def iou(a,b):
 intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
 union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection
 return intersection/union if union else 0.
summaries=[]
for cls in [0,1]:
 total=sum(sum(int(g[0])==cls for g in r["normalized_gt"]) for r in raw);aps=[];fixedtp=0;fixedfp=0
 for ti in range(10):
  all_predictions=[]
  for r in raw:
   w,h=r["size_wh"];gt=[]
   for c,x,y,bw,bh in r["normalized_gt"]:
    if int(c)==cls:gt.append([(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h])
   used=set()
   for p in sorted((p for p in r["predictions"] if p["class_id"]==cls),key=lambda p:-p["confidence"]):
    overlaps=[(iou(p["xyxy"],b),j) for j,b in enumerate(gt) if j not in used]
    score,j=max(overlaps,default=(0.,-1));success=score>=.5+.05*ti
    if success:used.add(j)
    all_predictions.append((p["confidence"],success))
    if ti==0 and p["confidence"]>=.25:
     if success:fixedtp+=1
     else:fixedfp+=1
  ordered=sorted(all_predictions,key=lambda p:-p[0]);tp=np.cumsum([int(p[1]) for p in ordered]);fp=np.cumsum([int(not p[1]) for p in ordered])
  recall=tp/total;precision=tp/np.maximum(1,tp+fp);mrec=np.r_[0.,recall,1.];mpre=np.maximum.accumulate(np.r_[1.,precision,0.][::-1])[::-1]
  aps.append(float(np.trapezoid(np.interp(np.linspace(0,1,101),mrec,mpre),np.linspace(0,1,101))))
 summaries.append({"class_id":cls,"class_name":["door","window"][cls],"support":total,"ap50":aps[0],"ap50_95":sum(aps)/10,"tp_at025":fixedtp,"fp_at025":fixedfp,"fn_at025":total-fixedtp})
assert all(sha(r["source_image"])==r["source_sha256"] for r in raw)
save("symbols/INDEPENDENT_EVALUATION.json",{"status":"PASS_RAW_COORDINATE_AND_SUPPORT_CHECKS","classes":summaries,"method":"Independent greedy confidence-ordered scalarIoU;101pointAP over per-image predictions. Different padding/matching from library batchval, not claimed exact library replay.","map50":sum(c["ap50"] for c in summaries)/2,"map50_95":sum(c["ap50_95"] for c in summaries)/2,"test_records":len(raw),"labels_and_predictions_saved":True})
save("symbols/EVALUATION_GUARD.json",events)
print("Native symbol evaluation",metrics.results_dict,"independent",summaries)
