import argparse,json
from pathlib import Path
from PIL import Image,ImageDraw
base=Path(__file__).resolve().parent;project=base.parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);root=ap.parse_args().out.resolve();(root/'figures').mkdir(parents=True,exist_ok=True)
cvc=project/'PP1_READINESS_20261022/PP1_UNET_CVC_EXTERNAL_EVALUATION_V1'
sel=json.loads((cvc/'FROZEN_SELECTION.json').read_text(encoding='utf-8-sig'))
colors=[(55,155,235),(230,175,60),(220,65,65),(60,190,125)]
for rec in sel['records']:
 stem=Path(rec['annotation_filename']).stem;q=cvc/'QUALITATIVE_PREDICTIONS'/stem
 img=Image.open(project/rec['image']['path']).convert('RGB').resize((512,512),Image.Resampling.BILINEAR)
 gt=Image.open(q/'GROUND_TRUTH_MODEL_512.png').convert('L');pred=Image.open(q/'PREDICTION_512.png').convert('L')
 a=gt.tobytes();b=pred.tobytes();w=h=512;panels=[img]
 for vals in [a,b]:
  im=Image.new('RGB',(w,h),(30,30,30));pix=im.load()
  for y in range(h):
   for x in range(w):
    v=vals[y*w+x];pix[x,y]=colors[v] if v<4 else (55,55,55)
  panels.append(im)
 err=Image.new('RGB',(w,h),(30,30,30));ep=err.load()
 for y in range(h):
  for x in range(w):
   i=y*w+x;g=a[i];p=b[i]
   if g>=4:ep[x,y]=(45,45,45)
   elif g==p:ep[x,y]=(45,95,55)
   elif p==0:ep[x,y]=(235,65,190)
   else:ep[x,y]=(40,210,220)
 panels.append(err);gap=8;header=38;canvas=Image.new('RGB',(4*w+5*gap,h+header+2*gap),(245,246,248));d=ImageDraw.Draw(canvas)
 labels=['Original CVC raster (512 square input resize)','Reference labels remapped to model indices','Frozen U-Net class prediction','Disagreement: FN magenta / FP cyan; grey=ignored']
 for i,(im,label) in enumerate(zip(panels,labels)):
  x=gap+i*(w+gap);canvas.paste(im,(x,header+gap));d.text((x,8),label,fill=(10,20,35))
 out=root/'figures'/(stem+'_source_diagnostic.png')
 if out.exists():raise SystemExit(f'Refusing to overwrite {out}; select a new output directory')
 canvas.save(out)
print('PASS: created',len(sel['records']),'source-aligned diagnostics')
