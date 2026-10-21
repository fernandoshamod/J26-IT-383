"""Create isolated dependencies and preservation baseline; originals read only."""
from pathlib import Path
import json,hashlib,shutil
H=Path(__file__).resolve().parent;R=H.parents[1];V=H.parent/'PP1_FLOORPLAN_AI_DEVELOPMENT_V3'
for n in ['common.py','decode_document.py','native_data.py','outdoor_geometry.py','review_handoff.py']:
 text=(V/n).read_text(encoding='utf-8').replace('OUTSIDE_V3','OUTSIDE_V4')
 (H/n).write_text(text,encoding='utf-8')
refs={str(V/n):hashlib.sha256((V/n).read_bytes()).hexdigest() for n in ['common.py','decode_document.py','native_data.py','outdoor_geometry.py','review_handoff.py','upload_inference.py','DELIVERY_SHA256.json']}
(H/'REUSED_SOURCE_PROVENANCE.json').write_text(json.dumps(refs,indent=2),encoding='utf-8')
for n in ['runtime/tmp','runtime/ultralytics','evidence','annotations','data','objects']:(H/n).mkdir(parents=True,exist_ok=True)
shutil.copyfile(Path('C:/Users/User/AppData/Roaming/Ultralytics/Arial.ttf'),H/'runtime/ultralytics/Arial.ttf')
print('Created isolated helpers, no original edits')
