"""Local published-chair-label reproduction pilot, NOT complete stock qualification."""
import platform,time,traceback
from common import *
platform.uname();events=guard()
try:
 import torch
 from ultralytics import YOLO,settings
 settings.update({k:False for k in ['sync','hub','wandb','clearml','comet','mlflow','tensorboard'] if k in settings})
 torch.set_num_threads(4);assert torch.cuda.is_available()
 init=ROOT/'yolov8n.pt'
 cfg=dict(data=str(H/'objects_v2/data.yaml'),epochs=12,imgsz=640,batch=8,device=0,workers=0,seed=2610184,
  deterministic=True,pretrained=str(init),project=str(H/'objects_v2'),name='published_chair_pilot_final',exist_ok=False,
  plots=False,cache=False,amp=False,optimizer='AdamW',lr0=.001,lrf=.1,cos_lr=True,mosaic=0.,mixup=0.,close_mosaic=0,
  scale=.1,translate=.03,fliplr=.5,flipud=.5,degrees=0.,hsv_h=0.,hsv_s=0.,hsv_v=.1,save=True,patience=12)
 save('objects_v2/TRAINING_CONFIG.json',{'args':cfg,'init_sha256':sha(init),'split_sha256':sha(H/'objects_v2/SPLITS.json'),
  'selection':'best validation fitness; test not evaluated until checkpoint freeze','scope':'PUBLISHED_LABEL_REPRODUCTION_PILOT: known non-exhaustive chair labels, uncertain original drawing rights/source ancestry; NOT complete inventory accuracy',
  'transfer':'Local COCO YOLOv8n backbone/neck; one-class detection head adapted by installed Ultralytics; 12-event synthetic and 2-opening weights remain unchanged'})
 t=time.perf_counter();model=YOLO(str(init));model.train(**cfg)
 p=H/'objects_v2/published_chair_pilot_final/weights/best.pt'
 save('objects_v2/CHECKPOINT_FREEZE.json',{'checkpoint':str(p),'sha256':sha(p),'seconds':time.perf_counter()-t,'classes':['chair'],'frozen_event_id_mapping':{'0':2},'test_opened':False,'gpu':torch.cuda.get_device_name(),'qualification':'EXPERIMENTAL_NOT_STOCK_QUALIFIED'})
except BaseException:
 save('objects_v2/TRAINING_FAILURE.json',{'traceback':traceback.format_exc()});raise
finally:save('objects_v2/TRAINING_GUARD.json',events)
