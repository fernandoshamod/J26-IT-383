"""Produce a bounded prediction-blind human review pack; do not grant approval."""
from common import *
from PIL import Image,ImageDraw,ImageOps
import numpy as np
queue=read(H/"unet/HUMAN_REVIEW_QUEUE.json")
palette=np.array([[238,238,238],[66,185,100],[215,55,60],[245,167,40],[55,125,240]],np.uint8)
selected=[queue[i] for i in [0,1,8,9,16,17]]
previews=[]
for r in selected:
 with Image.open(r["image"]) as im:render=im.convert("RGB")
 with Image.open(r["mask"]) as ma:mask=np.array(ma)
 assert mask.shape==np.array(render).shape[:2]
 rgb=palette[mask]
 native=Path(r["source_svg"]).parent/"F1_scaled.png"
 with Image.open(native) as im:raster=im.convert("RGB")
 page=Image.new("RGB",(1200,470),"white");draw=ImageDraw.Draw(page)
 for i,(im,label) in enumerate([(render,"SVG render"),(Image.blend(render,Image.fromarray(rgb),.45),"Existing native mask overlay"),(raster,"Original raster: UNREGISTERED")]):
  thumb=ImageOps.contain(im,(390,400));page.paste(thumb,(i*400+(400-thumb.width)//2,40))
  draw.text((i*400+5,10),label,fill="black")
 draw.text((5,445),r["id"]+" | PENDING HUMAN REVIEW | room green, wall red, door orange, window blue; zero unknown",fill="black")
 path=H/"unet/review_previews"/(r["id"]+".png");path.parent.mkdir(parents=True,exist_ok=True);page.save(path)
 previews.append({"id":r["id"],"file":str(path),"raster":str(native),"raster_sha256":sha(native),"approval":"PENDING"})
save("unet/REVIEW_PREVIEWS.json",previews)
save("unet/READINESS_GATE.json",{"status":"BLOCKED","new_unet_training":"NOT_COMPLETED","human_semantic_signoff":False,"complete_source_family_signoff":False,
 "original_raster_registration_qualified":False,"unknown_zero_proven_background":False,
 "safe_correction":"Retain zero ignore255; certify semantic alignment and conservative family graph; qualify original-raster registration separately before raster-domain training. No threshold or class remap tuned on observed CVC.",
 "review_queue_records":len(queue),"preview_records":len(previews),"source_family_report":"GROUP_REPORT.json"})
print("UNET READINESS BLOCKED; six source-only review previews; no model inference or training.")
