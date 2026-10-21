"""Create the runtime authority after source preparation, before acceptance."""
from pathlib import Path
import json,hashlib,sys,importlib.metadata
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
names=['PP1_EXECUTABLE_V1','PP1_EVENT_SCENE_INTELLIGENCE_V1','PP1_EAG_APR_IMPLEMENTATION_V1','PP1_FINAL_MODEL_INTEGRATION_V1','PP1_REVIEWED_TWIN_SCENE_INTEGRATION_V1','PP1_VENUE_RECOGNITION_V4']
paths=set(H.glob('*.py'))
for name in names:paths.update((H.parent/name).glob('*.py'))
paths.update([H.parent/'PP1_EVENT_SCENE_INTELLIGENCE_V1/profiles.json',H.parent/'PP1_FINAL_DEMO_REHEARSAL_V1/worker.py',H/'objects_v2/CHECKPOINT_FREEZE.json',H/'outdoor/SOURCE_REGISTRY.json',H/'MODEL_REGISTRY.json'])
models=json.loads((H/'MODEL_REGISTRY.json').read_text())['models'];paths.update(Path(row['path']) for row in models.values())
packages=['torch','torchvision','segmentation-models-pytorch','ultralytics','numpy','scipy','shapely','pymoo','pydantic','fastapi','uvicorn','Pillow','opencv-python','matplotlib','httpx']
data=dict(schema='PP1_FINAL_BACKEND_RUNTIME_FREEZE_V1',python=sys.version,packages={p:importlib.metadata.version(p) for p in packages},files={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)},vendor_package_bytes_frozen=False,scope='Source/policy/config/checkpoints pinned; installed package versions checked, not vendored')
with (H/'BACKEND_RUNTIME_FREEZE.json').open('x') as f:json.dump(data,f,indent=2)
print('Runtime source/config/model files frozen:',len(paths))
