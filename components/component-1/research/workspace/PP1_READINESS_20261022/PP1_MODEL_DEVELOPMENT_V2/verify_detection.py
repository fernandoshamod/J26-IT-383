"""No inference: verify saved boxes/counts and compute independent greedy 101-point AP."""
from common import *
import math,csv,collections
import numpy as np
counts=read(H/"yolo/INDEPENDENT_FIXED_THRESHOLD_COUNTS.json")
checks=[];reports={}
def check(n,v):checks.append({"check":n,"passed":bool(v)})
def overlap(a,b):
 left=max(a[0],b[0]);right=min(a[2],b[2]);top=max(a[1],b[1]);bottom=min(a[3],b[3])
 intersection=max(0,right-left)*max(0,bottom-top)
 area_a=(a[2]-a[0])*(a[3]-a[1]);area_b=(b[2]-b[0])*(b[3]-b[1])
 return intersection/(area_a+area_b-intersection) if area_a+area_b>intersection else 0.
def ap_curve(labels):
 if not labels:return 0.
 tp=np.cumsum([int(v) for _,v in labels]);fp=np.cumsum([int(not v) for _,v in labels])
 recall=tp/totalgt;precision=tp/(tp+fp)
 mrec=np.r_[0.,recall,1.];mpre=np.r_[1.,precision,0.]
 mpre=np.maximum.accumulate(mpre[::-1])[::-1]
 return float(np.trapezoid(np.interp(np.linspace(0,1,101),mrec,mpre),np.linspace(0,1,101)))
for name in ["incumbent","candidate"]:
 raw=read(H/("yolo/predictions/"+name+"_RAW.json"))
 supports=[0]*12;tp=[0]*12;fp=[0]*12;traces={c:{t:[] for t in range(10)} for c in range(12)}
 for r in raw:
  check(name+" image hash "+Path(r["file"]).name,sha(r["file"])==r["image_sha256"])
  label=Path(r["file"]).parent.parent/"labels"/(Path(r["file"]).stem+".txt")
  check(name+" label hash "+label.name,sha(label)==r["label_sha256"])
  original=[list(map(float,line.split())) for line in label.read_text().splitlines()]
  check(name+" raw GT count "+label.name,len(original)==len(r["ground_truth"]))
  w,h=r["size_wh"]
  for x,g in zip(original,r["ground_truth"]):
   c,cx,cy,bw,bh=x
   box=[(cx-bw/2)*w,(cy-bh/2)*h,(cx+bw/2)*w,(cy+bh/2)*h]
   check(name+" GT schema "+label.name,g["class_id"]==int(c) and all(math.isclose(a,b,abs_tol=1e-9) for a,b in zip(g["xyxy"],box)))
  for t in r["ground_truth"]:supports[t["class_id"]]+=1
  for tid in range(10):
   used=set();threshold=.5+.05*tid
   for p in sorted(r["predictions"],key=lambda x:-x["score"]):
    options=[(overlap(p["xyxy"],g["xyxy"]),i) for i,g in enumerate(r["ground_truth"]) if i not in used and g["class_id"]==p["class_id"]]
    score,j=max(options,default=(0.,-1));matched=score>=threshold
    if matched:used.add(j)
    traces[p["class_id"]][tid].append((p["score"],matched))
    if tid==0 and p["score"]>=.25:
     # Must independently rematch at the fixed threshold: low-scoring boxes occur later,
     # so cannot consume an earlier high-score box's assignment.
     if matched:tp[p["class_id"]]+=1
     else:fp[p["class_id"]]+=1
 result=[]
 for c in range(12):
  expected=counts[name]["classes"][c]
  check(name+" fixed counts "+str(c),expected["gt"]==supports[c] and expected["tp"]==tp[c] and expected["fp"]==fp[c] and expected["fn"]==supports[c]-tp[c])
  totalgt=supports[c]
  aps=[ap_curve(sorted(traces[c][tid],key=lambda x:-x[0])) for tid in range(10)] if totalgt else None
  result.append({"class_id":c,"name":expected["name"],"support":totalgt,"ap50":aps[0] if aps else None,"ap50_95":sum(aps)/10 if aps else None,"ap_thresholds":aps,"status":"NOT_VALIDATED" if not totalgt else "PROCEDURAL_DIAGNOSTIC"})
 check(name+" exactly 30 diagnostic images",len(raw)==30)
 check(name+" all support",sum(supports)==1189 and supports[1]==0)
 supported=[c for c in result if c["support"]]
 reports[name]={"classes":result,"map50":sum(c["ap50"] for c in supported)/len(supported),"map50_95":sum(c["ap50_95"] for c in supported)/len(supported),"class_denominator":len(supported)}
save("yolo/INDEPENDENT_DETECTION_VERIFICATION.json",{"status":"PASS" if all(c["passed"] for c in checks) else "FAIL","checks":checks,"results":reports,
 "definition":"Per-image greedy descending-score same-class matches; scalar IoU at 0.50:0.05:0.95, precision envelope and 101-point trapezoidal interpolation. Support-zero classes excluded with null AP.",
 "comparison_limit":"These APs use saved per-image square-padded prediction calls, not the library rectangular-batch val calls. Match assignment is independent and may differ from library. No false claim of exact library metric replay."})
with (H/"yolo/INDEPENDENT_CLASS_METRICS.csv").open("x",encoding="utf-8",newline="") as f:
 fields=["model","class_id","name","support","ap50","ap50_95","status"];writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
 for name,r in reports.items():
  for c in r["classes"]:writer.writerow({"model":name,**{k:c[k] for k in fields if k!="model"}})
print("Independent detection replay",len(checks),"assertions",all(c["passed"] for c in checks),reports["incumbent"]["map50"],reports["candidate"]["map50"])
if not all(c["passed"] for c in checks):raise SystemExit(1)
