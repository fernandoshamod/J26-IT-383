"""Explicit acquisition phase; network is permitted here only, never in training."""
from common import *
import urllib.request,traceback
assets={
 "CubiCasa_NATIVE_LOADER.py":"https://raw.githubusercontent.com/CubiCasa/CubiCasa5k/master/floortrans/loaders/svg_loader.py",
 "CubiCasa_LICENSE.txt":"https://raw.githubusercontent.com/CubiCasa/CubiCasa5k/master/LICENSE",
 "resnet18-f37072fd.pth":"https://download.pytorch.org/models/resnet18-f37072fd.pth",
 "SymPoint_README.md":"https://raw.githubusercontent.com/nicehuster/SymPoint/main/README.md",
}
rows=[]
for name,url in assets.items():
 p=H/"acquired"/name;p.parent.mkdir(parents=True,exist_ok=True)
 try:
  request=urllib.request.Request(url,headers={"User-Agent":"PP1-academic-floorplan-research/1"})
  with urllib.request.urlopen(request,timeout=90) as response,p.open("xb") as out:
   while True:
    b=response.read(1024*1024)
    if not b:break
    out.write(b)
  if name.endswith(".pth"):assert sha(p).startswith("f37072fd")
  rows.append({"url":url,"file":str(p),"bytes":p.stat().st_size,"sha256":sha(p),"status":"DOWNLOADED"})
 except Exception as e:rows.append({"url":url,"file":str(p),"status":"FAILED","error":repr(e)})
save("ACQUISITION.json",rows)
print([(r["file"],r["status"]) for r in rows])
if not all(r["status"]=="DOWNLOADED" for r in rows[:3]):raise SystemExit(2)
