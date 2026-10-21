"""Public source acquisition only; no hosted inference, credentials or security bypass."""
import urllib.request,json,hashlib,sys,time
from pathlib import Path
H=Path(__file__).resolve().parent
assets={
 'catalogue.svg':'https://floorplancad.github.io/images/catalogue.svg',
 'FloorPlanCAD_index.md':'https://raw.githubusercontent.com/floorplancad/floorplancad.github.io/master/index.md',
 'SCUT_Fig2.jpg':'https://raw.githubusercontent.com/designfuturelab702/SCUT-AutoALP-Database-Release/master/figure/Fig2.jpg',
 'GAT_README.md':'https://raw.githubusercontent.com/goldoak/GAT-CADNet/master/README.md',
 'floorplancad_classes.html':'https://floorplancad.github.io/classes-page.html',
 'floorplancad_source.html':'https://floorplancad.github.io/',
 'SCUT_README.md':'https://raw.githubusercontent.com/designfuturelab702/SCUT-AutoALP-Database-Release/master/README.md',
 'SCUT_TREE.json':'https://api.github.com/repos/designfuturelab702/SCUT-AutoALP-Database-Release/git/trees/master?recursive=1',
 'chair_table.html':'https://universe.roboflow.com/aiteam02/chair-table-floor-plan-detection',
 'chair_table_download.html':'https://universe.roboflow.com/aiteam02/chair-table-floor-plan-detection/dataset/7/download/yolov8',
 'all_objects.html':'https://universe.roboflow.com/floor-plan-rendering-l4ax8/floor-plan-all-objects',
 'GAT_TREE.json':'https://api.github.com/repos/goldoak/GAT-CADNet/git/trees/main?recursive=1',
}
attempt=sys.argv[1] if len(sys.argv)>1 else '001'
out=H/'acquisition'/attempt;out.mkdir(parents=True,exist_ok=False);records=[]
for name,url in assets.items():
 t=time.perf_counter()
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'academic-local-dataset-qualification/1'}),timeout=35) as r:
   data=r.read(20*1024*1024);status=r.status;final=r.url
  (out/name).write_bytes(data)
  records.append(dict(url=url,status=status,final_url=final,path=str(out/name),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),seconds=time.perf_counter()-t))
 except Exception as e:records.append(dict(url=url,error=repr(e),seconds=time.perf_counter()-t))
 print(name,records[-1].get('status',records[-1].get('error')),flush=True)
(out/'RESULT.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
if all('error' in x for x in records):raise SystemExit(2)
