"""Bounded rare-scene resampling fine-tune; frozen baseline remains unchanged."""
import shutil,time,traceback,platform
from common import *
platform.uname()
font=Path("C:/Users/User/AppData/Roaming/Ultralytics/Arial.ttf")
dest=H/"runtime/ultralytics/Arial.ttf";dest.parent.mkdir(parents=True,exist_ok=True)
assert font.is_file(),"No local font; refuse automatic download"
shutil.copyfile(font,dest)
events=guard()
try:
 import torch
 from ultralytics import YOLO,settings
 settings.update({k:False for k in ["sync","wandb","clearml","comet","mlflow","neptune","tensorboard","hub"] if k in settings})
 torch.set_num_threads(4)
 assert torch.cuda.is_available(),"CUDA unavailable; no hosted fallback"
 old=read(ROOT/"02_GENERATED_RESEARCH_DATA/STAGE_C_OBJECTS/C3_23_PP1_HELDOUT_SYNTHETIC_TEST_V1/C323_TEST_REPORT.json")
 assert sha(old["checkpoint"])==old["checkpoint_sha256"]
 config=dict(data=str(H/"yolo/data.yaml"),epochs=12,batch=4,imgsz=960,device=0,workers=0,
  seed=261018,deterministic=True,pretrained=old["checkpoint"],project=str(H/"yolo"),name="rare_resample_finetune",
  exist_ok=False,plots=False,cache=False,amp=False,val=True,optimizer="AdamW",lr0=.0001,lrf=.1,
  patience=12,save=True,save_period=4,cos_lr=True,close_mosaic=0,mosaic=0.,mixup=0.,
  degrees=0.,translate=.05,scale=.15,fliplr=.5,flipud=0.,hsv_h=0.,hsv_s=0.,hsv_v=.1)
 save("yolo/TRAINING_PROTOCOL.json",{"config":config,"initialization":old["checkpoint"],"initialization_sha256":old["checkpoint_sha256"],"scope":"Controlled procedural development only","selection":"Validation fitness only; no test-based checkpoint/threshold selection. Compare selected fine-tuned validation fitness with unchanged incumbent validation before diagnostic test.","limitations":"Incumbent already trained 25 epochs. Additional training/resampling budget differs; no architecture or compute-matched superiority claim.","torch":torch.__version__,"gpu":torch.cuda.get_device_name(),"offline":True})
 model=YOLO(old["checkpoint"])
 original_state={k:v.detach().cpu().float().clone() for k,v in model.model.state_dict().items()}
 def verify_initialization(trainer):
  actual=trainer.model.state_dict()
  mismatches=[k for k,v in original_state.items() if k not in actual or not torch.equal(v,actual[k].detach().cpu().float())]
  save("yolo/INITIAL_WEIGHT_VERIFICATION.json",{"passed":not mismatches,"state_tensors":len(original_state),"mismatches":mismatches,"checkpoint_sha256":old["checkpoint_sha256"],"stage":"on_pretrain_routine_end before first epoch"})
  assert not mismatches,"TRAINER_DISCARDED_OR_MUTATED_INITIAL_WEIGHTS"
 model.add_callback("on_pretrain_routine_end",verify_initialization)
 t=time.perf_counter()
 model.train(**config)
 best=H/"yolo/rare_resample_finetune/weights/best.pt"
 save("yolo/TRAINING_RESULT.json",{"status":"COMPLETED","seconds":time.perf_counter()-t,"best_checkpoint":str(best),"sha256":sha(best),"last_checkpoint":str(best.parent/"last.pt"),"initialization_preserved":sha(old["checkpoint"])==old["checkpoint_sha256"]})
except BaseException:
 save("yolo/TRAINING_FAILURE.json",{"traceback":traceback.format_exc()});raise
finally:save("yolo/TRAINING_GUARD.json",events)
