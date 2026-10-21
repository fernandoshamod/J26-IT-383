"""Separate DOM-based replay of native targets and all opening boxes; no inference."""
from xml.dom import minidom
import re
import numpy as np
from PIL import Image,ImageDraw
from common import *
parts=read(H/"unet/ELIGIBLE_NATIVE_SPLITS.json");symbols=read(H/"symbols/DATASET.json")
checks=[];exports=[]
for partition,rows in parts.items():
 symbolpart="test" if partition=="diagnostic_test" else partition
 lookup={r["id"]:r for r in symbols["partitions"][symbolpart]}
 for r in rows:
  with Image.open(r["source_image"]) as im:w,h=im.size
  dom=minidom.parse(r["source_svg"]);polys={i:[] for i in range(4)};boxes=[]
  for g in dom.getElementsByTagName("g"):
   klass=g.getAttribute("class");ident=g.getAttribute("id");cid=None
   if klass.startswith("Space ") and not set(klass.split())&{"Outdoor","Undefined"}:cid=0
   if ident in {"Wall","Door","Window"}:cid={"Wall":1,"Door":2,"Window":3}[ident]
   if cid is None:continue
   for node in g.childNodes:
    if node.nodeType!=node.ELEMENT_NODE or node.localName!="polygon":continue
    vals=[float(x) for x in re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?",node.getAttribute("points"))]
    pts=list(zip(vals[::2],vals[1::2]));polys[cid].append([(round(a),round(b)) for a,b in pts])
    if cid in [2,3]:
     a=max(0,min(p[0] for p in pts));b=max(0,min(p[1] for p in pts));c=min(w,max(p[0] for p in pts));d=min(h,max(p[1] for p in pts))
     if c-a>=1 and d-b>=1:boxes.append([cid-2,(a+c)/2/w,(b+d)/2/h,(c-a)/w,(d-b)/h])
  mask=Image.new("L",(w,h),255);draw=ImageDraw.Draw(mask)
  for c in range(4):
   for p in polys[c]:draw.polygon(p,fill=c)
  nw,nh=r["transform"]["resized_wh"];left,top=r["transform"]["offset_xy"]
  expected=Image.new("L",(512,512),255);expected.paste(mask.resize((nw,nh),Image.Resampling.NEAREST),(left,top))
  with Image.open(r["mask"]) as im:equal=np.array_equal(np.array(im),np.array(expected))
  record={"id":r["id"],"partition":partition,"mask_replay_exact":equal,"native_box_replay_exact":np.allclose(np.array(boxes),np.array(lookup[r["id"]]["boxes"]),rtol=0,atol=1e-12),"source_identity":sha(r["source_image"])==r["source_image_sha256"] and sha(r["source_svg"])==r["source_svg_sha256"]}
  assert all(record[k] for k in ["mask_replay_exact","native_box_replay_exact","source_identity"])
  checks.append(record);exports.append({"id":r["id"],"image_sha256":sha(r["image"]),"mask_sha256":sha(r["mask"]),"label_sha256":sha(lookup[r["id"]]["label"])})
save("INDEPENDENT_NATIVE_EXPORT_REPLAY.json",{"status":"PASS","records":checks,"method":"Separate minidom traversal and explicit native polygon/class parsing, independent target/box derivation, exact prepared-mask comparison. Shares Pillow rasterizer; no independent human annotation certificate."})
save("PREPARED_EXPORT_HASHES.json",exports)
print("Native export replay PASS",len(checks),"records")
