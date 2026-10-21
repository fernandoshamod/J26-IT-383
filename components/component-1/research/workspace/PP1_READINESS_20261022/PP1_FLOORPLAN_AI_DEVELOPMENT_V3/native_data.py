"""Publisher native pixel-polygon targets. No guessed raster registration."""
from common import *
import re,xml.etree.ElementTree as ET
import numpy as np
from PIL import Image,ImageDraw
CLASSES=["room_region","wall","door","window"]
def native_target(svg,size):
 tree=ET.parse(svg);root=tree.getroot()
 # Same native coordinates as official floortrans House, NOT resized SVG viewBox.
 records=[];mask=Image.new("L",size,255);draw=ImageDraw.Draw(mask)
 for elem in root.iter():
  klass=elem.get("class","");identity=elem.get("id","")
  cid=0 if klass.startswith("Space ") and not any(x in klass.split() for x in ["Outdoor","Undefined"]) else {"Wall":1,"Door":2,"Window":3}.get(identity)
  if cid is None:continue
  polys=[p for p in list(elem) if p.tag.rsplit("}",1)[-1]=="polygon"]
  if not polys:continue
  for poly in polys:
   nums=list(map(float,re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?",poly.get("points",""))))
   if len(nums)<6 or len(nums)%2:raise ValueError("INVALID_NATIVE_POLYGON")
   points=list(zip(nums[::2],nums[1::2]))
   if not all(np.isfinite(nums)):raise ValueError("NONFINITE_POLYGON")
   records.append({"class_id":cid,"points":points,"source_class":klass,"source_id":identity})
 for cid in range(4):
  for r in records:
   if r["class_id"]==cid:draw.polygon([(round(x),round(y)) for x,y in r["points"]],fill=cid)
 return mask,records
def letterbox(image,mask,size=512):
 w,h=image.size;s=min(size/w,size/h);nw,nh=max(1,round(w*s)),max(1,round(h*s))
 left,top=(size-nw)//2,(size-nh)//2
 x=Image.new("RGB",(size,size),"white");x.paste(image.resize((nw,nh),Image.Resampling.BILINEAR),(left,top))
 y=Image.new("L",(size,size),255);y.paste(mask.resize((nw,nh),Image.Resampling.NEAREST),(left,top))
 return x,y,{"original_wh":[w,h],"resized_wh":[nw,nh],"offset_xy":[left,top],"model_size":size}
