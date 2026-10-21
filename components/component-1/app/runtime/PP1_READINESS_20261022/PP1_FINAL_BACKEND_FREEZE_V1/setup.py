"""Bind read-only integrations into one isolated backend workspace."""
from pathlib import Path
import shutil,json,hashlib
H=Path(__file__).resolve().parent;P=H.parent;ONE=P/'PP1_FINAL_MODEL_INTEGRATION_V1';TWO=P/'PP1_REVIEWED_TWIN_SCENE_INTEGRATION_V1'
before={}
for base in [ONE,TWO]:
 data=json.loads((base/'DELIVERY_SHA256.json').read_text())['files']
 for name,expected in data.items():
  p=base/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==expected,str(p);before[str(p)]=expected
for name in ['common.py','decode_document.py','objects_v2/CHECKPOINT_FREEZE.json','outdoor/SOURCE_REGISTRY.json','runtime/ultralytics/Arial.ttf']:
 (H/name).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ONE/name,H/name)
# Reuse the existing approved controlled brief unchanged. Source and evidence
# remain in their recorded original locations; a new HTTP registration follows.
shutil.copyfile(TWO/'SCENE_BRIEF.json',H/'SCENE_BRIEF.json')
(H/'PRESERVATION_BEFORE.json').write_text(json.dumps(before,indent=2))
models=json.loads((ONE/'FUNCTIONAL_ACCEPTANCE_FINAL.json').read_text())['models']
roles={'unet':'V3 native structural segmentation; provisional candidates, never usable metric boundary approval','opening_yolo':'V3 door/window symbols; no authoritative stock','controlled_event_yolo':'V2 procedural 12-class; controlled domain only, never real-plan stock inference','experimental_chair':'V4 chair pilot; opt-in only, disabled by default, unverified stock'}
for name,row in models.items():
 assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256']
 row.update(role=roles[name],default_enabled=name in ['unet','opening_yolo'],metric_authority=False)
(H/'MODEL_REGISTRY.json').write_text(json.dumps({'schema':'PP1_CONSOLIDATED_MODEL_REGISTRY_V1','models':models},indent=2))
print('Both prior deliveries verified; four checkpoint identities verified; output bindings prepared')
