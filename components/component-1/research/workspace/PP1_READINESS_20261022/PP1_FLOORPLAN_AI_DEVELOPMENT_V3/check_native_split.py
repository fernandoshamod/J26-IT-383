"""Conservative pre-training native-raster duplicate/near-family exclusion."""
from common import *
import numpy as np,collections
from PIL import Image
s=read(H/"unet/NATIVE_SPLITS.json");rows=[dict(r,partition=k) for k,rr in s.items() for r in rr]
angle=np.cos(np.pi*np.arange(8)[:,None]*(np.arange(32)[None,:]+.5)/32)
ph=[];decoded=[];edges=[]
for r in rows:
 with Image.open(r["source_image"]) as im:
  rgb=im.convert("RGB");decoded.append(hashlib.sha256(str(rgb.size).encode()+rgb.tobytes()).hexdigest())
  a=np.array(rgb.convert("L").resize((32,32),Image.Resampling.LANCZOS),float)
 d=(angle@a@angle.T).ravel()[1:];ph.append(sum(int(v)<<j for j,v in enumerate(d>np.median(d))))
held=set()
for i,a in enumerate(rows):
 for j in range(i):
  b=rows[j];distance=(ph[i]^ph[j]).bit_count()
  if a["partition"]!=b["partition"] and (a["group"]==b["group"] or decoded[i]==decoded[j] or distance<=6):
   held.update([a["id"],b["id"]]);edges.append({"a":a["id"],"b":b["id"],"distance":distance,"exact_decoded":decoded[i]==decoded[j],"decision":"HOLD_BOTH_NO_REPLACEMENT"})
new={k:[r for r in rr if r["id"] not in held] for k,rr in s.items()}
assert all(new.values())
save("unet/ELIGIBLE_NATIVE_SPLITS.json",new)
save("unet/NATIVE_SPLIT_CHECK.json",{"status":"PASS_KNOWN_OVERLAP_EXCLUDED","cross_partition_edges":edges,"held_ids":sorted(held),"counts":{k:len(v) for k,v in new.items()},"exhaustive_physical_ancestry_certified":False,"screen":"Exact source SVG/prior render groups plus current RGB decoded hashes and63bitDCT hamming<=6. All cross candidates held; no replacements."})
print("Eligible split",{k:len(v) for k,v in new.items()})
