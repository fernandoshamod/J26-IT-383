"""Explicit algorithmic/vector proposals. Never infer measured event-usable truth."""
import re,math,xml.etree.ElementTree as ET
import numpy as np,cv2
from shapely.geometry import Polygon,mapping
def affine(text):
 matrix=np.eye(3)
 for name,values in re.findall(r"([A-Za-z]+)\s*\(([^)]*)\)",text or ""):
  v=list(map(float,re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?",values)));m=np.eye(3)
  if name=="matrix" and len(v)==6:m=np.array([[v[0],v[2],v[4]],[v[1],v[3],v[5]],[0,0,1.]])
  elif name=="translate":m[0,2]=v[0];m[1,2]=v[1] if len(v)>1 else 0
  elif name=="scale":m[0,0]=v[0];m[1,1]=v[1] if len(v)>1 else v[0]
  elif name=="rotate":
   a=math.radians(v[0]);m[:2,:2]=[[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]]
   if len(v)==3:
    t=np.eye(3);t[:2,2]=v[1:3];ti=np.eye(3);ti[:2,2]=-np.array(v[1:3]);m=t@m@ti
  else:raise ValueError("UNSUPPORTED_SVG_AFFINE:"+name)
  matrix=matrix@m
 return matrix
def vector_regions(path,width,height):
 tree=ET.parse(path).getroot();vb=list(map(float,tree.get("viewBox").split()))
 s=min(width/vb[2],height/vb[3]);base=np.array([[s,0,(width-vb[2]*s)/2-vb[0]*s],[0,s,(height-vb[3]*s)/2-vb[1]*s],[0,0,1.]])
 regions=[];unresolved=[]
 def walk(e,parent,label=None,evidence=None):
  transform=parent@affine(e.get("transform",""));klass=e.get("class","");ident=e.get("id","")
  tag=e.tag.rsplit("}",1)[-1]
  if klass.startswith("Space "):
   subtype=klass.split()[1]
   indoor={"Bedroom","LivingRoom","Kitchen","Bath","Hall","Entry","Closet","Sauna","Dining","Room","Office","ConferenceRoom","MeetingRoom","Ballroom"}
   label="outdoor_region" if subtype=="Outdoor" else "indoor_region" if subtype in indoor else "unclassified_region";evidence=klass
  if klass.startswith("FixedFurniture "):label="native_fixed_furniture";evidence=klass
  if ident in {"site_boundary","usable_zone","covered_zone","open_air_zone","restricted_zone"}:label=ident;evidence=ident
  if tag=="polygon" and label:
   nums=list(map(float,re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?",e.get("points",""))))
   if len(nums)<6 or len(nums)%2:return
   points=[(transform@np.array([x,y,1.]))[:2].tolist() for x,y in zip(nums[::2],nums[1::2])]
   p=Polygon(points)
   if not p.is_valid or p.area<=0 or any(not(0<=x<=width and 0<=y<=height) for x,y in points):
    unresolved.append({"source_class":evidence,"reason":"INVALID_OR_OUT_OF_FRAME_REGION"});return
   regions.append({"id":"VECTOR_REGION_%04d"%len(regions),"semantic_class":label,"status":"DERIVED_FROM_VECTOR","source_class":evidence,"geometry":mapping(p),"coordinate_unit":"decoded_image_pixels","review_required":True})
  for c in e:walk(c,transform,label,evidence)
 walk(tree,base)
 conflicts=[]
 for i,a in enumerate(regions):
  for b in regions[:i]:
   if {a["semantic_class"],b["semantic_class"]}=={"indoor_region","outdoor_region"}:
    from shapely.geometry import shape
    area=shape(a["geometry"]).intersection(shape(b["geometry"])).area
    if area>1e-6:conflicts.append({"a":a["id"],"b":b["id"],"overlap_pixels2":area})
 return {"regions":regions,"conflicts":conflicts,"unresolved":unresolved,"semantic_source":"Explicit SVG source classes, not learned mixed-region segmentation"}
def raster_proposals(image):
 a=np.array(image.convert("L"));h,w=a.shape
 gray=a if np.median(a)>128 else 255-a
 ink=(gray<180).astype(np.uint8)*255
 contours,_=cv2.findContours(ink,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
 proposals=[]
 for contour in contours:
  area=cv2.contourArea(contour)
  if not(.01*w*h<=area<=.95*w*h):continue
  approx=cv2.approxPolyDP(contour,.003*cv2.arcLength(contour,True),True).reshape(-1,2)
  if not 3<=len(approx)<=100:continue
  p=Polygon(approx.tolist())
  if p.is_valid and p.area>0:
   proposals.append({"semantic_class":"unclassified_closed_region","status":"UNVERIFIED","method":"fixed_threshold_closed_contour_polygon","geometry":mapping(p),"area_pixels2":p.area,"review_required":True,"not_claimed":["site_boundary","entrance","covered_zone","usable_zone","obstacle"]})
 proposals.sort(key=lambda p:-p["area_pixels2"])
 for i,p in enumerate(proposals[:5]):p["id"]="RASTER_PROPOSAL_%03d"%i
 return proposals[:5]
