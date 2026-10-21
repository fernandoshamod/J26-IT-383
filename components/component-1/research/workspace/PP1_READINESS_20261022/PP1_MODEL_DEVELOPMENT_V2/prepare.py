"""New reference-only U-Net candidate and physically isolated procedural YOLO export."""
import csv,collections,shutil,time
from common import *
import numpy as np
from PIL import Image
start=time.perf_counter()
base=ROOT/"02_GENERATED_RESEARCH_DATA"
old=read(base/"STAGE_B_PP1_BASELINE/provisional_splits.json")
rows=[dict(r,old_partition=s) for s,rr in old.items() for r in rr]
source=list(csv.DictReader((base/"STEP15_CUBICASA_FULL_REVIEW_20261013_212620_234860/reports/manifest.csv").open(encoding="utf-8-sig")))
byid={"cubi_%05d"%(i+1):r for i,r in enumerate(source)}
parent=list(range(len(rows)))
def find(i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
def union(a,b):
 a,b=find(a),find(b)
 if a!=b:parent[max(a,b)]=min(a,b)
hashgroups=collections.defaultdict(list);candidates=[];protected={}
def protect(p):
 p=Path(p);protected[p.relative_to(ROOT).as_posix()]=sha(p);return protected[p.relative_to(ROOT).as_posix()]
angle=np.cos(np.pi*np.arange(8)[:,None]*(np.arange(32)[None,:]+.5)/32)
phashes=[]
for i,r in enumerate(rows):
 svg=ROOT/"01_DATASET_DOWNLOADS/CubiCasa5K"/byid[r["id"]]["svg_relative_path"]
 r["source_svg"]=str(svg);r["source_sha256"]=protect(svg)
 r["image_sha256"]=protect(r["image"]);r["mask_sha256"]=protect(r["mask"])
 for kind,key in [("svg",r["source_sha256"]),("image",r["image_sha256"]),("mask",r["mask_sha256"])]:
  hashgroups[kind+":"+key].append(i)
 with Image.open(r["image"]) as im:
  a=np.array(im.convert("L").resize((32,32),Image.Resampling.LANCZOS),float)
 d=(angle@a@angle.T).ravel()[1:];bits=d>np.median(d)
 phashes.append(sum(int(b)<<j for j,b in enumerate(bits)))
 if (i+1)%1000==0:print("U-Net records hashed",i+1,flush=True)
for members in hashgroups.values():
 for i in members[1:]:union(members[0],i)
arr=np.array(phashes,np.uint64)
for st in range(0,len(rows),256):
 distances=np.bitwise_count(arr[st:st+256,None]^arr[None,:])
 for aa,bb in np.argwhere(distances<=6):
  a=st+int(aa);b=int(bb)
  if a>=b:continue
  union(a,b)
  candidates.append({"a":rows[a]["id"],"b":rows[b]["id"],"hamming":int(distances[aa,bb]),"decision":"CONSERVATIVE_GROUP_NOT_PROVEN_COMMON_VENUE"})
index={r["id"]:i for i,r in enumerate(rows)}
for a,b in [("cubi_02252","cubi_02253"),("cubi_02294","cubi_02291")]:union(index[a],index[b])
groups=collections.defaultdict(list)
for i,r in enumerate(rows):groups[find(i)].append(r)
parts={"train":[],"val":[],"diagnostic_test":[]};overlap=[]
for group in groups.values():
 original={r["old_partition"] for r in group}
 part="diagnostic_test" if "test" in original else "val" if "val" in original else "train"
 gid=min(r["id"] for r in group)
 if len(original)>1:overlap.append({"group":gid,"original_partitions":sorted(original),"records":[r["id"] for r in group]})
 for r in group:r["group_id"]=gid;r["partition"]=part;parts[part].append(r)
save("unet/CANDIDATE_SPLITS.json",parts)
save("unet/GROUP_REPORT.json",{"records":len(rows),"observed_groups":len(groups),"partition_counts":{k:len(v) for k,v in parts.items()},"prior_cross_partition_groups":overlap,"near_screen_edges":candidates,"policy":"Union exact SVG/image/mask hashes, conservative 63-bit DCT hamming<=6 and two previously visually identified variants. Retain complete group in highest-priority old test then val. No claim of exhaustive family independence.","source_ancestry_certified":False,"training_ready":False,"reason":"Semantic and ancestry sign-off absent; source renders are not original-raster training pairs."})
queue=[]
for s,rr in parts.items():
 # Predeclared deterministic review queue, independent of any predictions.
 for r in sorted(rr,key=lambda r:sha(Path(r["source_svg"])))[:8]:
  queue.append({"id":r["id"],"partition":s,"image":r["image"],"mask":r["mask"],"source_svg":r["source_svg"],"source_sha256":r["source_sha256"],"semantic_review":"PENDING_HUMAN_REVIEW","raster_alignment_review":"NOT_QUALIFIED"})
save("unet/HUMAN_REVIEW_QUEUE.json",queue)
# Controlled procedural data are not real/human annotations; preserve original split groups.
yroot=base/"STAGE_C_OBJECTS/C3_17_V3_CLEAN_YOLO_CANDIDATE_157"
import yaml
cfg=yaml.safe_load((yroot/"data.yaml").read_text())
manifest=read(yroot/"C3_17_RECORD_MANIFEST.json")
group_splits=collections.defaultdict(set)
for r in manifest:group_splits[r["source_group"]].add(r["split"])
assert all(len(v)==1 for v in group_splits.values())
counts={};copies=[];imagehashes=collections.defaultdict(set)
for split in ["train","val","test"]:
 counts[split]=collections.Counter()
 for p in sorted((yroot/split/"images").glob("*")):
  label=yroot/split/"labels"/(p.stem+".txt");support=collections.Counter()
  with Image.open(p) as im:size=im.size;im.verify()
  for line in label.read_text().splitlines():
   c,x,y,w,h=map(float,line.split());assert c.is_integer() and 0<=c<12 and all(np.isfinite([x,y,w,h])) and 0<=x<=1 and 0<=y<=1 and 0<w<=1 and 0<h<=1
   assert x-w/2>=-1e-5 and x+w/2<=1+1e-5 and y-h/2>=-1e-5 and y+h/2<=1+1e-5
   support[int(c)]+=1
  counts[split].update(support)
  ih=protect(p);lh=protect(label);imagehashes[ih].add(split)
  repeats=3 if split=="train" and (1 in support or 11 in support) else 1
  for rep in range(repeats):
   stem=p.stem+("__train_repeat%d"%rep if rep else "")
   dest=H/"yolo/dataset"/split/"images"/(stem+p.suffix)
   dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
   lab=dest.parent.parent/"labels"/(stem+".txt");lab.parent.mkdir(exist_ok=True);shutil.copyfile(label,lab)
   copies.append({"split":split,"source":str(p),"sha256":ih,"label_sha256":lh,"destination":str(dest),"repetition":rep,"synthetic":True})
assert all(len(v)==1 for v in imagehashes.values())
cfg["path"]=(H/"yolo/dataset").as_posix()
(H/"yolo/data.yaml").write_text(yaml.safe_dump(cfg,sort_keys=False),encoding="utf-8")
save("yolo/DATASET_EXPORT.json",{"copies":copies,"original_class_support":{s:dict(c) for s,c in counts.items()},"source_groups":{k:list(v) for k,v in group_splits.items()},"original_counts":dict(collections.Counter(r["split"] for r in manifest)),"export_counts":dict(collections.Counter(r["split"] for r in copies)),"policy":"Three train-only copies for scenes containing buffet or temporary_partition. No new labels or synthetic-to-real claim. Test was historically observed; comparison is diagnostic, not untouched final generalization.","classes":cfg["names"]})
report=read(base/"STAGE_C_OBJECTS/C3_23_PP1_HELDOUT_SYNTHETIC_TEST_V1/C323_TEST_REPORT.json")
for p in [Path(report["checkpoint"]),base/"STAGE_B_PP1_BASELINE/best_unet_resnet18.pt",yroot/"data.yaml",yroot/"C3_17_RECORD_MANIFEST.json",base/"STAGE_B_PP1_BASELINE/provisional_splits.json",
ROOT/"PP1_READINESS_20261022/PP1_UNET_CVC_EXTERNAL_EVALUATION_V1/CONFUSION_MATRICES.json",
ROOT/"PP1_READINESS_20261022/PP1_EXECUTABLE_V1/BACKEND_FREEZE_V1.json"]:protect(p)
save("PROTECTED_SOURCE_HASHES.json",protected)
save("PREPARATION_RESULT.json",{"seconds":time.perf_counter()-start,"unet_training":"BLOCKED_HUMAN_SEMANTIC_AND_ANCESTRY_REVIEW","yolo_training":"ELIGIBLE_CONTROLLED_PROCEDURAL_ONLY","downloaded_data":False})
print("Preparation complete",time.perf_counter()-start,flush=True)
