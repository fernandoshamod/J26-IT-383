from pathlib import Path
import json,hashlib,shutil
H=Path(__file__).resolve().parent;P=H.parent;V=P/'PP1_VENUE_RECOGNITION_V4'
for n in ['common.py','decode_document.py']:
 shutil.copyfile(V/n,H/n)
for n in ['objects_v2/CHECKPOINT_FREEZE.json','outdoor/SOURCE_REGISTRY.json']:
 (H/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(V/n,H/n)
(H/'runtime/ultralytics').mkdir(parents=True,exist_ok=True)
shutil.copyfile(V/'runtime/ultralytics/Arial.ttf',H/'runtime/ultralytics/Arial.ttf')
files=[V/n for n in ['common.py','decode_document.py','upload_inference.py','native_data.py','outdoor_geometry.py','outdoor_evidence.py']]
(H/'DEPENDENCY_BINDINGS.json').write_text(json.dumps({'read_only_sources':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'output_binding':'V4 helpers resolve common.H to this integration workspace; V3 checkpoints remain at original paths; chair freeze and outdoor registry are exact copied configuration references, not copied weights/data','frozen_files_edited':False},indent=2),encoding='utf-8')
