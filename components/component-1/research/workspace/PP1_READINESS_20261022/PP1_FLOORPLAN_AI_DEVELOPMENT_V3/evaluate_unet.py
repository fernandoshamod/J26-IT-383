"""Matched native-raster and observed-CVC diagnostics; save every actual mask."""
import platform,time,importlib.util
from common import *
platform.uname();events=guard()
import numpy as np,torch
from PIL import Image,ImageDraw
from native_data import letterbox
torch.set_num_threads(4)
loader_path=ROOT/"PP1_STAGE_E_EVENT_LAYOUT_V2/backend/venue_unet_inference_v2.py"
spec=importlib.util.spec_from_file_location("strict_loader",loader_path);loader=importlib.util.module_from_spec(spec);spec.loader.exec_module(loader)
cp={"incumbent":ROOT/"02_GENERATED_RESEARCH_DATA/STAGE_B_PP1_BASELINE/best_unet_resnet18.pt","native_v3":H/"unet/best_native_unet.pt"}
native=read(H/"unet/ELIGIBLE_NATIVE_SPLITS.json")["diagnostic_test"]
cvc=read(ROOT/"PP1_READINESS_20261022/PP1_UNET_CVC_EXTERNAL_EVALUATION_V1/FROZEN_SELECTION.json")["records"]
save("unet/EVALUATION_PROTOCOL.json",{"checkpoints":{k:{"path":str(v),"sha256":sha(v)} for k,v in cp.items()},"native_split_sha256":sha(H/"unet/ELIGIBLE_NATIVE_SPLITS.json"),"selection":"Checkpoint already chosen on validation only","common_preprocessing":"Both models identical512letterbox/RGBImageNet/FP32argmax. NOT original historical stretch protocol.","native_scope":"64sourcegroupheldout records for new model; conservative ancestry, historical SVG evaluations observed. Incumbent may have trained on source families; not a clean causal model comparison.","cvc_scope":"Same10observed diagnostics, nativeCVCdefinitions; no selection/tuning. Not untouched external test."})
palette=np.array([[66,185,100],[215,55,60],[245,167,40],[55,125,240]],np.uint8)
reports={}
def metrics(cm):
 tp=cm.diagonal();union=cm.sum(0)+cm.sum(1)-tp
 ious=[float(tp[i]/union[i]) if union[i] else None for i in range(4)]
 return {"class_iou":ious,"miou":float(np.mean([v for v in ious if v is not None])),"support":cm.sum(1).tolist(),"union":union.tolist()}
for name,checkpoint in cp.items():
 model=loader.load_model(checkpoint,torch.device("cuda"));totals={}
 for domain,rows in [("native",native),("observed_cvc",cvc)]:
  pooled=np.zeros((4,4),np.int64);results=[];t=time.perf_counter()
  for i,r in enumerate(rows):
   if domain=="native":
    identity=r["id"]
    with Image.open(r["image"]) as im:image=im.convert("RGB")
    with Image.open(r["mask"]) as im:target=np.array(im)
    source=r["source_image"];sourcehash=r["source_image_sha256"]
   else:
    identity=Path(r["annotation_filename"]).stem;source=str(ROOT/r["image"]["path"]);sourcehash=r["image"]["sha256"]
    image=loader.load_image(Path(source))
    with Image.open(ROOT/r["mask"]["path"]) as im:raw=np.array(im)
    mapped=np.array([255,1,2,3,0],np.uint8)[raw]
    image,ym,_=letterbox(image,Image.fromarray(mapped));target=np.array(ym)
   assert sha(source)==sourcehash
   x=np.array(image,np.float32)/255;x=(x-np.array([.485,.456,.406],np.float32))/np.array([.229,.224,.225],np.float32)
   with torch.inference_mode():pred=model(torch.from_numpy(x.transpose(2,0,1).copy()).unsqueeze(0).cuda()).argmax(1)[0].cpu().numpy().astype(np.uint8)
   valid=target!=255;cm=np.bincount(target[valid].astype(np.int64)*4+pred[valid],minlength=16).reshape(4,4);pooled+=cm
   folder=H/"unet/predictions"/domain/name/identity;folder.mkdir(parents=True,exist_ok=False)
   Image.fromarray(pred).save(folder/"PREDICTION.png");Image.fromarray(target).save(folder/"TARGET.png")
   colored=palette[pred];gt=np.array(image).copy();gt[valid]=(gt[valid]*.5+palette[target[valid]]*.5).astype(np.uint8)
   page=Image.new("RGB",(1536,550),"white");page.paste(image,(0,25));page.paste(Image.fromarray(gt),(512,25));page.paste(Image.blend(image,Image.fromarray(colored),.4),(1024,25))
   ImageDraw.Draw(page).text((5,5),domain+" | "+name+" | "+identity+" | source / native GT (unknown ignored) / actual prediction",fill="black")
   page.save(folder/"OVERLAY.png")
   results.append({"id":identity,"source":source,"source_sha256":sourcehash,"confusion":cm.tolist(),"metrics":metrics(cm),"ignored":int((~valid).sum()),"prediction":str(folder/"PREDICTION.png"),"target":str(folder/"TARGET.png"),"prediction_sha256":sha(folder/"PREDICTION.png")})
  totals[domain]={"records":results,"pooled_confusion":pooled.tolist(),"pooled_metrics":metrics(pooled),"seconds":time.perf_counter()-t,"checkpoint_sha256":sha(checkpoint)}
  print(name,domain,"mIoU",totals[domain]["pooled_metrics"]["miou"],flush=True)
 reports[name]=totals;del model;torch.cuda.empty_cache()
save("unet/EVALUATION.json",reports);save("unet/EVALUATION_GUARD.json",events)
# Separate metric implementation: scalar pairs, no primary vector metric function.
from collections import Counter
checks=[];replays={}
for name,domains in reports.items():
 replays[name]={}
 for domain,report in domains.items():
  total=[[0]*4 for _ in range(4)]
  for r in report["records"]:
   with Image.open(r["prediction"]) as im:p=list(im.get_flattened_data())
   with Image.open(r["target"]) as im:g=list(im.get_flattened_data())
   cnt=Counter((a,b) for a,b in zip(g,p) if a!=255)
   cm=[[cnt[(a,b)] for b in range(4)] for a in range(4)]
   ok=cm==r["confusion"] and sha(r["prediction"])==r["prediction_sha256"]
   checks.append({"model":name,"domain":domain,"id":r["id"],"pass":ok})
   assert ok
   for a in range(4):
    for b in range(4):total[a][b]+=cm[a][b]
  ious=[]
  for c in range(4):
   union=sum(total[c])+sum(row[c] for row in total)-total[c][c]
   ious.append(total[c][c]/union if union else None)
  miou=sum(v for v in ious if v is not None)/sum(v is not None for v in ious)
  assert total==report["pooled_confusion"] and abs(miou-report["pooled_metrics"]["miou"])<1e-12
  replays[name][domain]={"confusion":total,"class_iou":ious,"miou":miou}
save("unet/INDEPENDENT_METRIC_REPLAY.json",{"status":"PASS","checks":checks,"results":replays,"scope":"Independent arithmetic implementation over raw saved masks; shared frozen targets and Pillow decoder, not human annotation certification."})
