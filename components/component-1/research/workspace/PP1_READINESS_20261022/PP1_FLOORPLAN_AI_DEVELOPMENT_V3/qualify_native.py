"""Prediction-blind bounded native raster qualification; do not certify unknown ancestry."""
from common import *
from native_data import *
from PIL import ImageOps
import collections,time
parts=read(ROOT/"PP1_READINESS_20261022/PP1_MODEL_DEVELOPMENT_V2/unet/CANDIDATE_SPLITS.json")
policy={"native_pairing":"Published floortrans get_txt F1_scaled.png + native model.svg coordinates; no viewBox scaling",
 "candidate_budget":{"train":320,"val":64,"diagnostic_test":64},"selection":"SHA256 group ID rank, one record per previously conservatively grouped family, preserve V2 partition priority",
 "predeclared_gates":{"all_four_classes_on_512":True,"wall_pixels_min":100,"wall_dark_fraction_min":.6,"native_vertex_fraction_inside_min":.98},
 "approval_scope":"Machine technical qualification plus source-only agent review, not independent human certification. Does not approve old SVG-render export or unknown source ancestry.",
 "test_policy":"No test model prediction until train config/model selection frozen. Historical SVG-domain family evidence already observed, disclosed."}
save("unet/NATIVE_QUALIFICATION_POLICY.json",policy)
outparts={};rejected=[];previews=[];protected={}
for split,rows in parts.items():
 selected=[];seen=set()
 for r in sorted(rows,key=lambda r:hashlib.sha256(("V3_NATIVE|"+r["group_id"]).encode()).hexdigest()):
  if r["group_id"] in seen:continue
  seen.add(r["group_id"])
  svg=Path(r["source_svg"]);image=svg.parent/"F1_scaled.png"
  try:
   with Image.open(image) as im:im=im.convert("RGB");size=im.size
   mask,polys=native_target(svg,size);a=np.array(mask)
   vertices=[p for r2 in polys for p in r2["points"]]
   inside=sum(0<=x<size[0] and 0<=y<size[1] for x,y in vertices)/len(vertices)
   gray=np.array(im.convert("L"));wall=a==1;dark=float((gray[wall]<180).mean()) if wall.any() else 0.
   x,y,transform=letterbox(im,mask);target=np.array(y)
   support=[int((target==c).sum()) for c in range(4)]
   if min(support)==0 or support[1]<100 or dark<.6 or inside<.98:raise ValueError("NATIVE_ALIGNMENT_QA_GATE:"+str({"support":support,"wall_dark":dark,"inside":inside}))
   folder=H/"unet/data"/split;folder.mkdir(parents=True,exist_ok=True)
   xp=folder/(r["id"]+"_image.png");yp=folder/(r["id"]+"_mask.png")
   x.save(xp);y.save(yp)
   ih=sha(image);sh=sha(svg)
   protected[image.relative_to(ROOT).as_posix()]=ih;protected[svg.relative_to(ROOT).as_posix()]=sh
   selected.append({"id":r["id"],"group":r["group_id"],"style":svg.parent.parent.name,"image":str(xp),"mask":str(yp),"source_image":str(image),"source_svg":str(svg),"source_image_sha256":ih,"source_svg_sha256":sh,"transform":transform,"class_support":support,"wall_dark_fraction":dark,"native_vertices_inside_fraction":inside,"annotation_status":"PUBLISHER_NATIVE_POLYGON_TARGET_NOT_INDEPENDENT_HUMAN_CERTIFIED"})
   if len(selected)<=3:
    pal=np.array([[66,185,100],[215,55,60],[245,167,40],[55,125,240]],np.uint8)
    rgb=np.array(x);valid=target!=255;rgb[valid]=(rgb[valid]*.5+pal[target[valid]]*.5).astype(np.uint8)
    page=Image.new("RGB",(1024,550),"white");page.paste(x,(0,25));page.paste(Image.fromarray(rgb),(512,25))
    d=ImageDraw.Draw(page);d.text((5,5),r["id"]+" | ORIGINAL F1_scaled -> native pixel annotation; NO MODEL PREDICTIONS",fill="black")
    pp=H/"unet/qualification_previews"/(split+"_"+r["id"]+".png");pp.parent.mkdir(parents=True,exist_ok=True);page.save(pp);previews.append(str(pp))
   if len(selected)>=policy["candidate_budget"][split]:break
  except Exception as e:rejected.append({"id":r["id"],"source":str(svg),"reason":str(e)})
 outparts[split]=selected
 print(split,len(selected),"qualified native pairs",flush=True)
save("unet/NATIVE_SPLITS.json",outparts)
save("unet/NATIVE_QUALIFICATION_RESULT.json",{"counts":{k:len(v) for k,v in outparts.items()},"rejected":rejected,"previews":previews,"scope":"Bounded native source-pixel targets, not full-export approval or real event-venue truth","source_family_independence":"KNOWN_GROUP_DISJOINT;EXHAUSTIVE_PHYSICAL_ANCESTRY_UNRESOLVED","original_source_masks_modified":False})
save("PROTECTED_NATIVE_HASHES.json",protected)
