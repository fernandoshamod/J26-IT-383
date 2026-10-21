"""Actual separate two-class floorplan opening detector; twelve-class checkpoint untouched."""
import platform,time,shutil,traceback
from common import *
platform.uname()
font=Path("C:/Users/User/AppData/Roaming/Ultralytics/Arial.ttf")
dest=H/"runtime/ultralytics/Arial.ttf";dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(font,dest)
events=guard()
try:
 import torch
 from ultralytics import YOLO,settings
 settings.update({k:False for k in ["sync","hub","wandb","clearml","comet","mlflow","tensorboard"] if k in settings})
 torch.set_num_threads(4);assert torch.cuda.is_available()
 init=ROOT/"yolov8n.pt";assert init.is_file()
 cfg=dict(data=str(H/"symbols/data.yaml"),epochs=16,imgsz=960,batch=4,device=0,workers=0,seed=261018,
  deterministic=True,pretrained=str(init),project=str(H/"symbols"),name="native_openings",exist_ok=False,
  plots=False,cache=False,amp=False,optimizer="AdamW",lr0=.0003,lrf=.1,cos_lr=True,
  mosaic=0.,mixup=0.,close_mosaic=0,scale=.15,translate=.05,fliplr=.5,flipud=.5,
  degrees=5.,hsv_h=0.,hsv_s=0.,hsv_v=.15,save=True,patience=16)
 save("symbols/TRAINING_CONFIG.json",{"args":cfg,"initialization_sha256":sha(init),"dataset_sha256":sha(H/"symbols/DATASET.json"),"selection":"best validation fitness before test","scope":"Auxiliary2classstructuralopeningmodel; NOT a twelve-event-object detector"})
 model=YOLO(str(init));t=time.perf_counter();model.train(**cfg)
 best=H/"symbols/native_openings/weights/best.pt"
 save("symbols/TRAINING_RESULT.json",{"status":"COMPLETED","checkpoint":str(best),"sha256":sha(best),"seconds":time.perf_counter()-t,"epochs":16})
except BaseException:
 save("symbols/TRAINING_FAILURE.json",{"traceback":traceback.format_exc()});raise
finally:save("symbols/TRAINING_GUARD.json",events)
