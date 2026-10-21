"""Freeze final new workspace evidence, excluding transient runtime caches and this manifest."""
from common import *
import csv
rows=[]
for root,dirs,files in os.walk(H):
 dirs[:]=[d for d in dirs if d not in ['runtime','__pycache__']]
 for name in files:
  p=Path(root)/name
  if name in ['DELIVERY_SHA256.json','FILE_REGISTER.csv']:continue
  rows.append({'path':p.relative_to(H).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
rows.sort(key=lambda r:r['path'])
with (H/'FILE_REGISTER.csv').open('x',newline='',encoding='utf-8') as f:
 w=csv.DictWriter(f,fieldnames=['path','bytes','sha256']);w.writeheader();w.writerows(rows)
digests={r['path']:r['sha256'] for r in rows};digests['FILE_REGISTER.csv']=sha(H/'FILE_REGISTER.csv')
save('DELIVERY_SHA256.json',{'files':digests,'excluded':['runtime transient cache/temp','DELIVERY_SHA256.json itself'],'files_hashed':len(digests)})
print('Frozen new delivery',len(digests),'files; runtime excluded')
