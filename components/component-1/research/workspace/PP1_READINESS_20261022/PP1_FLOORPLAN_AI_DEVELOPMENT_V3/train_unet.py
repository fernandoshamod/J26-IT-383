"""Actual bounded native-raster training; never initialize from old task checkpoint."""
import platform,time,random,traceback
from common import *
platform.uname();events=guard()
try:
 import numpy as np,torch
 import segmentation_models_pytorch as smp
 from torch.utils.data import Dataset,DataLoader
 from PIL import Image,ImageEnhance,ImageFilter,ImageOps
 torch.set_num_threads(4);torch.manual_seed(20261018);random.seed(20261018);np.random.seed(20261018)
 assert torch.cuda.is_available()
 parts=read(H/"unet/ELIGIBLE_NATIVE_SPLITS.json")
 cfg={"architecture":"Unet","encoder":"resnet18","classes":["room_region","wall","door","window"],"size":512,"ignore_index":255,"epochs":16,"batch":4,"seed":20261018,"optimizer":"AdamW","lr":.0003,"weight_decay":.0001,"loss":"train-frequency capped inverse-square-root weighted crossentropy +0.5 macro soft Dice on valid pixels","selection":"maximum FP32 pooled validation4classmIoU; test unopened","init":"Official ImageNet ResNet18; random decoder; NO old task weights","preprocessing":"aspect preserving512letterbox, padding255ignored, RGB/255/ImageNet","training_augmentation":"random horizontal/vertical flip,90degree turns; brightness/contrast, occasionalblur; targets transformed exactly, no val/test aug","native_split_sha256":sha(H/"unet/ELIGIBLE_NATIVE_SPLITS.json")}
 save("unet/TRAINING_CONFIG.json",cfg)
 class Data(Dataset):
  def __init__(self,rows,training=False):self.rows=rows;self.training=training
  def __len__(self):return len(self.rows)
  def __getitem__(self,i):
   r=self.rows[i]
   with Image.open(r["image"]) as im:x=im.convert("RGB")
   with Image.open(r["mask"]) as im:y=im.copy()
   if self.training:
    if random.random()<.5:x=ImageOps.mirror(x);y=ImageOps.mirror(y)
    if random.random()<.5:x=ImageOps.flip(x);y=ImageOps.flip(y)
    k=random.randrange(4)
    if k:x=x.rotate(90*k);y=y.rotate(90*k)
    x=ImageEnhance.Contrast(x).enhance(random.uniform(.7,1.3));x=ImageEnhance.Brightness(x).enhance(random.uniform(.85,1.15))
    if random.random()<.2:x=x.filter(ImageFilter.GaussianBlur(.5))
   a=np.array(x,np.float32)/255;a=(a-np.array([.485,.456,.406],np.float32))/np.array([.229,.224,.225],np.float32)
   return torch.from_numpy(a.transpose(2,0,1).copy()),torch.from_numpy(np.array(y,np.int64))
 loaders={k:DataLoader(Data(parts[k],k=="train"),batch_size=4,shuffle=k=="train",num_workers=0,pin_memory=True) for k in ["train","val"]}
 hist=np.array([sum(r["class_support"][i] for r in parts["train"]) for i in range(4)],float)
 weights=np.sqrt(hist.sum()/hist);weights/=weights.mean();weights=np.clip(weights,.25,4)
 save("unet/CLASS_WEIGHTS.json",{"training_support":hist.tolist(),"weights":weights.tolist()})
 model=smp.Unet(encoder_name="resnet18",encoder_weights=None,in_channels=3,classes=4)
 init=H/"acquired/resnet18-f37072fd.pth";assert sha(init).startswith("f37072fd")
 model.encoder.load_state_dict(torch.load(init,map_location="cpu",weights_only=True),strict=True)
 model.cuda();opt=torch.optim.AdamW(model.parameters(),lr=.0003,weight_decay=.0001)
 scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(opt,T_max=16)
 scaler=torch.amp.GradScaler("cuda");weight=torch.tensor(weights,dtype=torch.float32,device="cuda")
 history=[];best=-1;started=time.perf_counter()
 for epoch in range(1,17):
  for phase in ["train","val"]:
   model.train(phase=="train");cm=np.zeros((4,4),np.int64);losses=[]
   for x,y in loaders[phase]:
    x=x.cuda(non_blocking=True);y=y.cuda(non_blocking=True);valid=y!=255
    with torch.set_grad_enabled(phase=="train"):
     with torch.autocast("cuda",enabled=phase=="train"):
      logits=model(x)
     ce=torch.nn.functional.cross_entropy(logits.float(),y,weight=weight,ignore_index=255)
     prob=logits.float().softmax(1);target=torch.nn.functional.one_hot(y.clamp_max(3),4).permute(0,3,1,2).float()
     mask=valid.unsqueeze(1);prob=prob*mask;target=target*mask
     dice=1-((2*(prob*target).sum((0,2,3))+1)/((prob+target).sum((0,2,3))+1)).mean();loss=ce+.5*dice
     if phase=="train":
      opt.zero_grad(set_to_none=True);scaler.scale(loss).backward();scaler.step(opt);scaler.update()
    pred=logits.argmax(1);a=y[valid].cpu().numpy();b=pred[valid].cpu().numpy()
    cm+=np.bincount(a*4+b,minlength=16).reshape(4,4);losses.append(float(loss))
   union=cm.sum(0)+cm.sum(1)-cm.diagonal();ious=cm.diagonal()/union;miou=float(ious.mean())
   row={"epoch":epoch,"phase":phase,"loss":float(np.mean(losses)),"confusion_matrix":cm.tolist(),"class_iou":ious.tolist(),"miou":miou,"elapsed":time.perf_counter()-started};history.append(row)
   print(epoch,phase,"mIoU",miou,flush=True)
   if phase=="val" and miou>best:
    best=miou;torch.save({"model":model.state_dict(),"encoder":"resnet18","architecture":"Unet","classes":cfg["classes"],"size":512,"ignore_index":255,"epoch":epoch,"val_miou":miou,"config":cfg,"imagenet_init_sha256":sha(init)},H/"unet/best_native_unet.pt")
  scheduler.step()
  # Only new in-progress training history is replaced; frozen original evidence is untouched.
  (H/"unet/history.json").write_text(json.dumps(history,indent=2),encoding="utf-8")
 torch.save({"model":model.state_dict(),"config":cfg},H/"unet/last_native_unet.pt")
 save("unet/TRAINING_RESULT.json",{"status":"COMPLETED","best_val_miou":best,"best_checkpoint":str(H/"unet/best_native_unet.pt"),"sha256":sha(H/"unet/best_native_unet.pt"),"epochs":16,"seconds":time.perf_counter()-started,"gpu":torch.cuda.get_device_name()})
except BaseException:
 save("unet/TRAINING_FAILURE.json",{"traceback":traceback.format_exc()});raise
finally:save("unet/TRAINING_GUARD.json",events)
