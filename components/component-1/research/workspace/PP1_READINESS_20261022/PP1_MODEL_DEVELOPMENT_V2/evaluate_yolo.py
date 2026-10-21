"""Freeze on validation, then compare on historically observed synthetic test only."""
import platform,time,traceback
from common import *
platform.uname();events=guard()
try:
 import torch,numpy as np
 from PIL import Image
 from ultralytics import YOLO
 torch.set_num_threads(4)
 old=read(ROOT/"02_GENERATED_RESEARCH_DATA/STAGE_C_OBJECTS/C3_23_PP1_HELDOUT_SYNTHETIC_TEST_V1/C323_TEST_REPORT.json")
 trained=read(H/"yolo/TRAINING_RESULT.json")
 checkpoints={"incumbent":old["checkpoint"],"candidate":trained["best_checkpoint"]}
 def evaluate(label,split):
  model=YOLO(checkpoints[label]);t=time.perf_counter()
  result=model.val(data=str(H/"yolo/data.yaml"),split=split,imgsz=960,batch=4,workers=0,device=0,
   half=False,conf=.001,iou=.7,max_det=300,plots=False,save_json=False,verbose=False,
   project=str(H/"yolo/evaluations"),name=label+"_"+split,exist_ok=False)
  data={"checkpoint":checkpoints[label],"sha256":sha(checkpoints[label]),"split":split,"metrics":{k:float(v) for k,v in result.results_dict.items()},
   "class_indices":[int(i) for i in result.box.ap_class_index],"per_class_precision":result.box.p.tolist(),
   "per_class_recall":result.box.r.tolist(),"per_class_ap50":result.box.ap50.tolist(),
   "per_class_ap50_95":result.box.ap.tolist(),"seconds":time.perf_counter()-t,
   "precision_recall_scope":"Library best-F1 operating point, not fixed 0.25","synthetic_only":True}
  save("yolo/evaluations/"+label+"_"+split+".json",data);return data
 vals={name:evaluate(name,"val") for name in checkpoints}
 selected=max(vals,key=lambda n:vals[n]["metrics"]["metrics/mAP50-95(B)"])
 save("yolo/MODEL_SELECTION.json",{"selected":selected,"criterion":"Highest validation mAP50-95 only; tie incumbent","validation_results":vals,
  "selected_checkpoint":checkpoints[selected],"selected_sha256":sha(checkpoints[selected]),"test_unobserved_in_this_mission_at_selection":True,"test_historically_untouched":False,
  "buffet_validation_support":0,"buffet_status":"NOT_VALIDATED"})
 tests={name:evaluate(name,"test") for name in checkpoints}
 def iou(a,b):
  w=max(0,min(a[2],b[2])-max(a[0],b[0]));h=max(0,min(a[3],b[3])-max(a[1],b[1]))
  inter=w*h;union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter
  return inter/union if union>0 else 0.
 comparisons={}
 for name,cp in checkpoints.items():
  model=YOLO(cp);saved=[];tp=[0]*12;fp=[0]*12;gtcounts=[0]*12
  images=sorted((H/"yolo/dataset/test/images").glob("*"))
  for ii,path in enumerate(images):
   result=model.predict(str(path),imgsz=960,conf=.001,iou=.7,max_det=300,device=0,save=False,verbose=False)[0]
   h,w=result.orig_shape;pred=[]
   for b,c,s in zip(result.boxes.xyxy.cpu().tolist(),result.boxes.cls.cpu().tolist(),result.boxes.conf.cpu().tolist()):
    assert 0<=int(c)<12 and all(np.isfinite(b)) and 0<=s<=1
    assert 0<=b[0]<=b[2]<=w+.01 and 0<=b[1]<=b[3]<=h+.01
    pred.append({"class_id":int(c),"xyxy":b,"score":s})
   label=path.parent.parent/"labels"/(path.stem+".txt");truth=[]
   for line in label.read_text().splitlines():
    c,x,y,bw,bh=map(float,line.split());c=int(c)
    truth.append({"class_id":c,"xyxy":[(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h]});gtcounts[c]+=1
   matched=set()
   for pr in sorted((p for p in pred if p["score"]>=.25),key=lambda p:-p["score"]):
    choices=[(iou(pr["xyxy"],t["xyxy"]),j) for j,t in enumerate(truth) if j not in matched and t["class_id"]==pr["class_id"]]
    score,j=max(choices,default=(0.,-1))
    if score>=.5:tp[pr["class_id"]]+=1;matched.add(j)
    else:fp[pr["class_id"]]+=1
   saved.append({"file":str(path),"image_sha256":sha(path),"label_sha256":sha(label),"size_wh":[w,h],"predictions":pred,"ground_truth":truth})
   if ii<6:
    out=H/"yolo/predictions"/name;out.mkdir(parents=True,exist_ok=True)
    Image.fromarray(result.plot()[:,:,::-1]).save(out/(path.stem+".png"))
  rows=[]
  for c in range(12):
   fn=gtcounts[c]-tp[c]
   rows.append({"class_id":c,"name":model.names[c],"gt":gtcounts[c],"tp":tp[c],"fp":fp[c],"fn":fn,
    "precision":tp[c]/(tp[c]+fp[c]) if tp[c]+fp[c] else None,
    "recall":tp[c]/gtcounts[c] if gtcounts[c] else None,"status":"NOT_VALIDATED" if gtcounts[c]==0 else "CONTROLLED_DIAGNOSTIC_ONLY"})
  assert sum(gtcounts)==1189 and gtcounts[1]==0
  save("yolo/predictions/"+name+"_RAW.json",saved)
  comparisons[name]={"fixed_threshold":.25,"matching_iou":.5,"method":"Separate scalar rectangle IoU and descending-score same-class one-to-one greedy matches; not library AP or best-F1 precision/recall","classes":rows,"images":len(images)}
 save("yolo/INDEPENDENT_FIXED_THRESHOLD_COUNTS.json",comparisons)
 save("yolo/COMPARISON.json",{"selected_on_validation":selected,"diagnostic_test":tests,"scope":"Previously observed, procedural source-group held-out data only. No final untouched external test or architecture/compute-matched superiority claim.","selected_checkpoint_sha256":sha(checkpoints[selected])})
except BaseException:
 save("yolo/EVALUATION_FAILURE.json",{"traceback":traceback.format_exc()});raise
finally:save("yolo/EVALUATION_GUARD.json",events)
