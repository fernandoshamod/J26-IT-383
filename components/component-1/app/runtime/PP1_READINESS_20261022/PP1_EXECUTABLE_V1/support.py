import hashlib,json,sys,sqlite3,os
# Research execution uses installed dependencies only; model libraries must not
# install optional plugins as a side effect of an invalid image request.
os.environ['YOLO_AUTOINSTALL']='false'
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PACKAGE=Path(__file__).parent
FUNCTIONAL=ROOT/'PP1_READINESS_20261022/10_FINAL_VERIFICATION/FUNCTIONAL_V2'
def digest(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def filehash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,allow_nan=False)
class ResearchError(ValueError):
    def __init__(self,code,details=None,status='rejected'):
        super().__init__(code);self.code=code;self.details=details or {};self.status=status
