"""Portable saved-log replay and exact-checkpoint YOLO inference. No training."""
from pathlib import Path
import csv,json,hashlib,os,time
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def rows(root,key):return list(csv.DictReader((Path(root)/'02_ORIGINAL_TRAINING_EVIDENCE'/key/'results.csv').open(encoding='utf-8-sig')))
def plot_yolo(root,key,out):
 import matplotlib.pyplot as plt
 r=rows(root,key);out=Path(out);out.mkdir(parents=True,exist_ok=False);paths=[];epochs=[int(x['epoch']) for x in r]
 fig,axs=plt.subplots(1,3,figsize=(13,4))
 for ax,term in zip(axs,['box_loss','cls_loss','dfl_loss']):
  for phase in ['train','val']:ax.plot(epochs,[float(x[phase+'/'+term]) for x in r],label=phase)
  ax.set(title=term,xlabel='Recorded epoch');ax.grid(alpha=.2);ax.legend()
 fig.suptitle(key+' | original observations, no retraining');fig.tight_layout();f=out/'losses.png';fig.savefig(f,dpi=200);plt.close(fig);paths.append(f)
 fig,axs=plt.subplots(1,2,figsize=(10,4))
 for ax,metric in zip(axs,['mAP50(B)','mAP50-95(B)']):ax.plot(epochs,[float(x['metrics/'+metric]) for x in r],'o-');ax.set(title='Validation '+metric,xlabel='Recorded epoch',ylim=(0,1));ax.grid(alpha=.2)
 fig.suptitle(key+' | validation curves; diagnostic evaluation is separate');fig.tight_layout();f=out/'validation_metrics.png';fig.savefig(f,dpi=200);plt.close(fig);paths.append(f)
 return paths
def summary(root,key):
 registry=read(Path(root)/'MODEL_REGISTRY.json');m=registry[key];d=read(Path(root)/'02_ORIGINAL_TRAINING_EVIDENCE'/key/'EVALUATION.json')
 if key=='OPENING_YOLO':return {'mAP50':d['metrics']['metrics/mAP50(B)'],'mAP50_95':d['metrics']['metrics/mAP50-95(B)'],'class_indices':d['class_indices'],'ap50':d['ap50'],'ap50_95':d['ap50_95'],'support':d['support'],'scope':m['scope']}
 if key=='EVENT_OBJECT_YOLO':
  c=d['diagnostic_test']['candidate'];return {'mAP50':c['metrics']['metrics/mAP50(B)'],'mAP50_95':c['metrics']['metrics/mAP50-95(B)'],'class_indices':c['class_indices'],'ap50':c['per_class_ap50'],'ap50_95':c['per_class_ap50_95'],'buffet_validation_test_support':0,'scope':m['scope']}
 return dict(d['results']['published_chair_pilot'],scope=m['scope'])
def load_yolo(root,key):
 os.environ.setdefault('YOLO_OFFLINE','true');os.environ.setdefault('YOLO_AUTOINSTALL','false');os.environ.setdefault('HF_HUB_OFFLINE','1')
 from ultralytics import YOLO,settings
 settings.update({k:False for k in ['sync','hub','wandb','clearml','comet','mlflow','tensorboard'] if k in settings})
 root=Path(root);m=read(root/'MODEL_REGISTRY.json')[key];p=root/m['checkpoint']
 if sha(p)!=m['sha256']:raise ValueError('Checkpoint hash mismatch '+key)
 model=YOLO(str(p));names=[model.names[i] for i in range(len(model.names))]
 if names!=m['classes']:raise ValueError('Checkpoint ontology mismatch '+str(names))
 return model,m
def infer_yolo(root,key,device='cpu',out=None):
 import numpy as np,torch
 from PIL import Image,ImageDraw
 root=Path(root);model,m=load_yolo(root,key)
 if not m.get('example'):raise ValueError('No rights-qualified matching example is supplied; evidence-only model.')
 source=root/m['example'];out=Path(out);out.mkdir(parents=True,exist_ok=False)
 with Image.open(source) as im:image=im.convert('RGB');array=np.array(image)
 torch.set_num_threads(4)
 if device=='auto':device='cuda:0' if torch.cuda.is_available() else 'cpu'
 if str(device).startswith('cuda'):torch.cuda.synchronize()
 start=time.perf_counter();result=model.predict(array,imgsz=m['size'],conf=.25,iou=.7,max_det=300,device=device,verbose=False,save=False)[0]
 if str(device).startswith('cuda'):torch.cuda.synchronize()
 seconds=time.perf_counter()-start;boxes=[];draw=ImageDraw.Draw(image)
 for xyxy,c,score in zip(result.boxes.xyxy.cpu().tolist(),result.boxes.cls.cpu().tolist(),result.boxes.conf.cpu().tolist()):
  x1,y1,x2,y2=xyxy
  if not(0<=x1<x2<=image.width+1e-3 and 0<=y1<y2<=image.height+1e-3):raise ValueError('Invalid predicted pixel box')
  boxes.append({'class_id':int(c),'class':model.names[int(c)],'confidence_uncalibrated':score,'xyxy_source_pixels':xyxy})
  draw.rectangle(xyxy,outline=(220,40,40),width=2);draw.text((max(0,x1),max(0,y1-12)),model.names[int(c)]+' '+format(score,'.2f'),fill=(190,20,20))
 image.save(out/'OVERLAY.png')
 record={'model':key,'status':'PREDICTIONS_ONLY_REVIEW_REQUIRED','checkpoint_sha256':m['sha256'],'source_sha256':sha(source),'source_name':source.name,'device':str(device),'predict_call_including_preprocess_postprocess_seconds':seconds,'detections':boxes,'count':len(boxes),'classes':m['classes'],'optimization_ready':False,'confirmed_inventory':False,'scope':m['scope'],'thresholds':{'confidence':.25,'iou_nms':.7,'max_det':300,'imgsz':m['size']}}
 (out/'RESULT.json').write_text(json.dumps(record,indent=2),encoding='utf-8');return record
