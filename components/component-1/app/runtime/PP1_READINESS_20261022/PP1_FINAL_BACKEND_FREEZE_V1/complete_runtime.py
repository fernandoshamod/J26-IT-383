"""Add original transitive dependency authority; retain the build-time manifest."""
from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
p=H/'BACKEND_RUNTIME_FREEZE.json';old=p.read_bytes();d=json.loads(old)
with (H/'BUILD_RUNTIME_FREEZE_148.json').open('xb') as f:f.write(old)
base=json.loads((H.parent/'PP1_EXECUTABLE_V1/BACKEND_FREEZE_V1.json').read_text())['runtime_sha256']
for name,expected in base.items():
 assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected,name
 if name in d['files']:assert d['files'][name]==expected
 d['files'][name]=expected
name=str(Path(__file__).resolve().relative_to(ROOT)).replace('\\','/');d['files'][name]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
d['transitive_dependency_authority']='PP1_EXECUTABLE_V1/BACKEND_FREEZE_V1.json runtime_sha256 (292 entries); includes legacy permission modules'
p.write_text(json.dumps(d,indent=2),encoding='utf-8')
print('Final runtime files:',len(d['files']),'(build manifest retained)')
