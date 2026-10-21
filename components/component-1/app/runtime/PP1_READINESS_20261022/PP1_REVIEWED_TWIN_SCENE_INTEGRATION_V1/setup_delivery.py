from pathlib import Path
import shutil,json,hashlib
H=Path(__file__).resolve().parent;OLD=H.parent/'PP1_FINAL_MODEL_INTEGRATION_V1'
for name in ['common.py','decode_document.py']:
 shutil.copyfile(OLD/name,H/name)
for name in ['objects_v2/CHECKPOINT_FREEZE.json','outdoor/SOURCE_REGISTRY.json','runtime/ultralytics/Arial.ttf']:
 (H/name).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(OLD/name,H/name)
files={}
for folder,manifest,key in [('PP1_FINAL_MODEL_INTEGRATION_V1','DELIVERY_SHA256.json','files'),('PP1_EXECUTABLE_V1','BACKEND_FREEZE_V1.json','runtime_sha256')]:
 base=H.parent/folder;data=json.loads((base/manifest).read_text());data=data[key]
 for name,expected in data.items():
  p=(base/name) if folder=='PP1_FINAL_MODEL_INTEGRATION_V1' else H.parents[1]/name
  actual=hashlib.sha256(p.read_bytes()).hexdigest();assert actual==expected,str(p);files[str(p)]=actual
for folder in ['PP1_EVENT_SCENE_INTELLIGENCE_V1','PP1_EAG_APR_IMPLEMENTATION_V1','PP1_FRONTEND_V1']:
 for p in (H.parent/folder).glob('*.py'):files[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
(H/'PRESERVATION_BEFORE.json').write_text(json.dumps(files,indent=2))
print('Read-only dependency snapshot',len(files))
