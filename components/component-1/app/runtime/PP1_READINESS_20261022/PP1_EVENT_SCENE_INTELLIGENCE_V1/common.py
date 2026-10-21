"""Isolated output and read-only frozen backend imports."""
import sys,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BACKEND=HERE.parent/'PP1_EXECUTABLE_V1'
sys.dont_write_bytecode=True
sys.path.append(str(BACKEND))

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def filehash(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,value):
    p=Path(p).resolve()
    if not p.is_relative_to(HERE):raise ValueError('OUTPUT_OUTSIDE_ISOLATED_MODULE')
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,allow_nan=False)
class GateError(ValueError):
    def __init__(self,code):super().__init__(code);self.code=code
def assert_evidence(e,source_sha,payload=None):
    p=Path(e.path).resolve()
    if not p.is_relative_to(ROOT) or not p.is_file():raise GateError('EVIDENCE_MISSING')
    if filehash(p)!=e.sha256 or e.source_sha256!=source_sha:raise GateError('EVIDENCE_BINDING_MISMATCH')
    if read(p).get('source_sha256')!=source_sha:raise GateError('EVIDENCE_DOCUMENT_SOURCE_MISMATCH')
    if payload is not None and read(p).get('payload_sha256')!=digest(payload):raise GateError('EVIDENCE_PAYLOAD_MISMATCH')

def immutable_snapshot():
    manifests=[(BACKEND/'BACKEND_FREEZE_V1.json',ROOT,'runtime_sha256'),(BACKEND/'HANDOFF_ARTIFACT_SHA256_V1.json',ROOT,None),
      (HERE.parent/'00_PROJECT_CONTROL/SOURCE_SHA256_BEFORE.json',ROOT,None)]
    for folder,name in [('PP1_FRONTEND_V1','FRONTEND_ARTIFACT_SHA256_V1.json'),('PP1_PANEL_NOVELTY_CLOSURE_V1','ARTIFACT_SHA256.json'),('PP1_CHANGE_IMPACT_RESEARCH_V1','ARTIFACT_SHA256.json'),('PP1_PANEL_RESEARCH_GAP_FINAL_V1','ARTIFACT_SHA256.json'),('PP1_FULL_RESEARCH_PANEL_DEFENCE_V1','ARTIFACT_SHA256.json')]:manifests.append((HERE.parent/folder/name,HERE.parent/folder,None))
    paths=set()
    for manifest,base,key in manifests:
        data=read(manifest);data=data[key] if key else data;paths.add(manifest)
        paths.update(base/p for p in data)
    return {str(p.relative_to(ROOT)):filehash(p) for p in sorted(paths)}
