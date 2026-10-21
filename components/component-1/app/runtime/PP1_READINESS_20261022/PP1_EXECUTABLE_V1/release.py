"""Detect source/dependency drift from the reviewed PP1 backend freeze."""
from pathlib import Path
import json
from support import ROOT,PACKAGE,filehash

def verify_freeze():
    path=PACKAGE/'BACKEND_FREEZE_V1.json'
    if not path.is_file():return {'status':'development_unfrozen'}
    manifest=json.loads(path.read_text(encoding='utf-8'));bad=[]
    for name,sha in manifest['runtime_sha256'].items():
        p=ROOT/name
        if not p.is_file() or filehash(p)!=sha:bad.append(name)
    if bad:raise RuntimeError('BACKEND_FREEZE_MISMATCH: '+', '.join(bad))
    return {'status':'verified_frozen','api_version':manifest['api_version'],'runtime_files_verified':len(manifest['runtime_sha256']),'scope':manifest['scope']}
