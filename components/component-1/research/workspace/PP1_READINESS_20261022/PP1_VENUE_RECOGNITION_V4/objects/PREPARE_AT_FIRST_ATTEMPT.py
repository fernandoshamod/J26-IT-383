"""One supported frozen-ontology class: chair. Published labels only, no pseudo GT."""
from common import *
import re,random,shutil,collections
import numpy as np,cv2
from PIL import Image,ImageDraw,ImageOps
events=guard();S=ROOT/'01_DATASET_DOWNLOADS/02_2DPlan_Objects'
names=['bar_counter','buffet','chair','dance_floor','exhibition_booth','podium','rectangular_table','registration_desk','round_table','seating_row','stage','temporary_partition']
save('ONTOLOGY_FREEZE.json',{'event_classes':names,'outdoor_classes':['site_boundary','usable_zone','open_air_zone','covered_zone','entrance','obstacle','restricted_zone'],
 'supported_published_mapping':{'2DPlan/18 chair':'chair','2DPlan/13 bar chairs':'chair'},'model_output_names':['chair'],'frozen_event_index':2,
 'exclusions':'generic table/desk not assigned to rectangular/round table without shape-specific reviewed target; all remaining event concepts NOT_VALIDATED',
 'inventory_state':'A published furnishing symbol is observed drawing content, NOT verified physical available stock; proposed/existing status unknown until review',
 'test_policy':'Keep publisher test partition, drop overlap families from train/val; no augmented training record enters eval. Fixed confidence .25, IoU .5, AP .50:.95, no final-test tuning',
 'scope':'Grayscale residential/office furnishing plan pilot under publisher-declared CC BY4.0; original drawings ownership and full venue ancestry unverified; no commercial clearance claim'})
rows=[];bad=[]
for split,folder in [('train','train'),('val','valid'),('test','test')]:
 for p in sorted((S/folder/'images').glob('*.jpg')):
  label=S/folder/'labels'/(p.stem+'.txt')
  try:
   with Image.open(p) as im:
    im=im.convert('RGB');w,h=im.size;a=np.array(im.convert('L').resize((32,32)))
   boxes=[];excluded=collections.Counter()
   for line in label.read_text().splitlines():
    cid,x,y,bw,bh=map(float,line.split());assert cid.is_integer() and 0<=cid<40
    assert all(np.isfinite([x,y,bw,bh])) and bw>0 and bh>0 and x-bw/2>=-.001 and y-bh/2>=-.001 and x+bw/2<=1.001 and y+bh/2<=1.001
    if int(cid) in [13,18]:boxes.append({'source_class_id':int(cid),'class':'chair','frozen_class_id':2,'model_class_id':0,'xywh_normalized':[x,y,bw,bh],'bbox_pixels':[(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h]})
    else:excluded[int(cid)]+=1
   # Conservative all dihedral view pHashes; equivalent transformed sources share groups.
   hashes=[]
   for k in range(4):
    for v in [np.rot90(a,k),np.fliplr(np.rot90(a,k))]:
     d=cv2.dct(v.astype('float32'))[:8,:8].flatten()[1:];bits=d>np.median(d)
     hashes.append(int(''.join('1' if x else '0' for x in bits),2))
   family=re.split(r'\.rf\.',p.name)[0]
   rows.append(dict(id=p.stem,source=str(p),source_sha256=sha(p),annotation=str(label),annotation_sha256=sha(label),source_family=family,publisher_partition=split,split=split,width=w,height=h,annotations=boxes,excluded_categories=dict(excluded),phashes=hashes,
    annotation_origin='PUBLISHED_ROBOFLOW_2DPLAN_V7',approval_state='PUBLISHED_LABELS_TECHNICAL_QA_ONLY_NO_HUMAN_CERTIFICATION',coordinate_transform='Identity on publisher 640x640 export; upstream stretch/augmentation not invertible',drawing_inventory_authority='UNKNOWN'))
  except Exception as e:bad.append({'source':str(p),'reason':repr(e)})
# Union exact source-name, exact file, D4 pHash<=6. Only technical similarities, not proof of venue ancestry.
parent=list(range(len(rows)))
def find(i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
def union(i,j):parent[find(j)]=find(i)
seen={};reps=[];links=[]
for i,r in enumerate(rows):
 keys=[('family',r['source_family']),('sha',r['source_sha256'])]
 for key in keys:
  if key in seen:union(i,seen[key])
  else:seen[key]=i
 if ('family',r['source_family']) in seen and seen[('family',r['source_family'])]!=i:continue
 for j in reps:
  distance=min((a^b).bit_count() for a in r['phashes'] for b in rows[j]['phashes'])
  if distance<=6:union(i,j);links.append({'a':r['id'],'b':rows[j]['id'],'d4_phash_distance':distance})
 reps.append(i)
groups=collections.defaultdict(list)
for i in range(len(rows)):groups[find(i)].append(i)
priority={'train':0,'val':1,'test':2};held=[]
for g,indices in groups.items():
 partitions={rows[i]['split'] for i in indices};keep=max(partitions,key=lambda x:priority[x])
 for i in indices:
  r=rows[i];r['technical_source_group']='GROUP_'+rows[g]['id'];r.pop('phashes')
  if r['split']!=keep:r['split']='held';r['hold_reason']='GROUP_OVERLAP_WITH_'+keep;held.append(r['id'])
# Keep all rows/failed sources. No class filtering based on model performance.
save('objects/SOURCE_RECORDS.json',rows);save('objects/REJECTED_RECORDS.json',bad);save('objects/NEAR_DUPLICATE_LINKS.json',links)
parts={k:[r for r in rows if r['split']==k] for k in ['train','val','test']}
for split,rr in parts.items():
 (H/'data'/split/'images').mkdir(parents=True,exist_ok=True);(H/'data'/split/'labels').mkdir(parents=True,exist_ok=True)
 for r in rr:
  dst=H/'data'/split/'images'/(r['id']+'.jpg');shutil.copyfile(r['source'],dst)
  txt='\n'.join('0 '+' '.join(format(x,'.10g') for x in b['xywh_normalized']) for b in r['annotations'])
  (H/'data'/split/'labels'/(r['id']+'.txt')).write_text(txt,encoding='utf-8')
save('objects/SPLITS.json',parts)
stats={s:{'images':len(rr),'groups':len({r['technical_source_group'] for r in rr}),'chairs':sum(len(r['annotations']) for r in rr),'negative_images':sum(not r['annotations'] for r in rr)} for s,rr in parts.items()}
save('objects/PREPARATION.json',{'stats':stats,'held_overlap':held,'malformed_count':len(bad),'mapping_source':'data.yaml40names + live publisher40class page; README4class prose stale','independence_limit':'Original document/campus/physical venue identity unresolved. Technical family separation only, no independent venue generalization claim.','guard':events})
(H/'objects/data.yaml').write_text('path: '+str(H/'data').replace('\\','/')+'\ntrain: train/images\nval: val/images\ntest: test/images\nnames:\n  0: chair\n',encoding='utf-8')
# Prediction-blind inspection: ten train families chosen by source-name SHA, before any model load.
unique={r['source_family']:r for r in parts['train']};chosen=sorted(unique.values(),key=lambda r:__import__('hashlib').sha256(r['source_family'].encode()).hexdigest())[:10]
canvas=Image.new('RGB',(1000,5*290),'white');inspection=[]
for j,r in enumerate(chosen):
 im=Image.open(r['source']).convert('RGB');d=ImageDraw.Draw(im)
 for b in r['annotations']:d.rectangle(b['bbox_pixels'],outline='red',width=2)
 im.thumbnail((480,260));x=(j%2)*500;y=(j//2)*290;canvas.paste(im,(x,y));ImageDraw.Draw(canvas).text((x,y+260),r['id'][:58],fill='black')
 inspection.append({'id':r['id'],'source':r['source'],'published_chair_count':len(r['annotations'])})
canvas.save(H/'objects/PREDICTION_BLIND_TRAIN_QA.jpg');save('objects/PREDICTION_BLIND_QA_RECORDS.json',inspection)
print(json.dumps(stats));print('Held overlaps',len(held),'invalid',len(bad))
