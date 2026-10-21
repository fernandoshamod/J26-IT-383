"""Qualified native door/window symbols; furniture CAD taxonomy mismatch remains held."""
import shutil,collections
from common import *
from native_data import *
parts=read(H/"unet/ELIGIBLE_NATIVE_SPLITS.json");out={};counts={}
for split,rows in parts.items():
 destsplit="test" if split=="diagnostic_test" else split;records=[];support=collections.Counter()
 for r in rows:
  # New labels are derived from published native opening polygons in unchanged source frame.
  with Image.open(r["source_image"]) as im:size=im.size
  _,polys=native_target(r["source_svg"],size);w,h=size
  boxes=[]
  for p in polys:
   if p["class_id"] not in [2,3]:continue
   xs=[a for a,b in p["points"]];ys=[b for a,b in p["points"]]
   a,b,c,d=max(0,min(xs)),max(0,min(ys)),min(w,max(xs)),min(h,max(ys))
   if c-a<1 or d-b<1:continue
   cls=p["class_id"]-2
   boxes.append([cls,(a+c)/2/w,(b+d)/2/h,(c-a)/w,(d-b)/h]);support[cls]+=1
  xp=H/"symbols/data"/destsplit/"images"/(r["id"]+".png");xp.parent.mkdir(parents=True,exist_ok=True)
  shutil.copyfile(r["source_image"],xp)
  yp=xp.parent.parent/"labels"/(r["id"]+".txt");yp.parent.mkdir(exist_ok=True)
  yp.write_text("\n".join(" ".join(map(str,b)) for b in boxes),encoding="utf-8")
  records.append({"id":r["id"],"group":r["group"],"source_image":r["source_image"],"source_svg":r["source_svg"],"image":str(xp),"label":str(yp),"boxes":boxes,"source_sha256":r["source_image_sha256"],"style":r["style"]})
 out[destsplit]=records;counts[destsplit]=dict(support)
import yaml
cfg={"path":(H/"symbols/data").as_posix(),"train":"train/images","val":"val/images","test":"test/images","nc":2,"names":{0:"door",1:"window"}}
(H/"symbols/data.yaml").write_text(yaml.safe_dump(cfg),encoding="utf-8")
save("symbols/DATASET.json",{"partitions":out,"support":counts,"ontology":"Native structural door/window symbols only; bbox envelopes of publisher polygons, not exact physical footprints","existing_12_event_classes":"PRESERVED_IN_V2;NOT_VALIDATED_ON_NEW_FLOORPLANS","source_groups_disjoint":not any({r["group"] for r in out[a]}&{r["group"] for r in out[b]} for a,b in [("train","val"),("train","test"),("val","test")])})
save("symbols/FURNITURE_DATA_HOLD.json",{"status":"DATA_BLOCKED","local_candidate":"01_DATASET_DOWNLOADS/FloorPlanCAD",
 "reason":"Existing local files use semantic-id/instance-id schema; fetched author CADTransformer taxonomy uses semanticId/instanceId. Native visual examples conflict with assuming raw13=chair (sample0001-0004 instance43 spans sofa-like geometry). No raw-ID mapping inferred from appearance. Version/ontology and drawing rights need reconciliation before twelve-class stock labels.",
 "supported_mapping":{"CubiCasa Door":"new structural symbol class0","CubiCasa Window":"new structural symbol class1"},
 "unsupported_12":["bar_counter","buffet","chair","dance_floor","exhibition_booth","podium","rectangular_table","registration_desk","round_table","seating_row","stage","temporary_partition"],
 "primary_taxonomy":"https://raw.githubusercontent.com/VITA-Group/CADTransformer/main/config/anno_config.py","no_new_furniture_ground_truth_fabricated":True})
print("Native opening symbols exported",counts)
