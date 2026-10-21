from common import *
import urllib.request
urls={"CADTransformer_TREE.json":"https://api.github.com/repos/VITA-Group/CADTransformer/git/trees/main?recursive=1",
 "CADTransformer_ONTOLOGY.py":"https://raw.githubusercontent.com/VITA-Group/CADTransformer/main/config/anno_config.py",
 "FloorPlanCAD_SOURCE_PAGE.html":"https://floorplancad.github.io/"}
rows=[]
for name,url in urls.items():
 p=H/"acquired"/name
 try:
  req=urllib.request.Request(url,headers={"User-Agent":"PP1-noncommercial-research"})
  with urllib.request.urlopen(req,timeout=60) as f,p.open("xb") as out:out.write(f.read())
  rows.append({"url":url,"path":str(p),"sha256":sha(p),"bytes":p.stat().st_size,"status":"DOWNLOADED"})
 except Exception as e:rows.append({"url":url,"status":"FAILED","error":repr(e)})
save("CAD_METADATA_ACQUISITION.json",rows)
print(rows)
if (H/"acquired/CADTransformer_TREE.json").exists():
 tree=read(H/"acquired/CADTransformer_TREE.json")
 print("CAD assets:",[r["path"] for r in tree.get("tree",[]) if r["path"].endswith((".svg",".png",".json"))][:60])
