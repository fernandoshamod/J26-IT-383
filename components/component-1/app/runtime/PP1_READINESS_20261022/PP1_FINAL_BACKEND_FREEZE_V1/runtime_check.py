"""Portable source/dependency checks; model assets are validated on inference only."""
import sys
from pathlib import Path
PACKAGE=Path(__file__).resolve().parents[3]
if str(PACKAGE) not in sys.path:sys.path.insert(0,str(PACKAGE))
from verify_portable import verify as verify_portable_runtime
def verify():
 proof=verify_portable_runtime()
 if proof['status']!='PASS':raise RuntimeError('PORTABLE_RUNTIME_PREFLIGHT_FAILED:'+str(proof['errors'][:8]))
 return {'status':'PASS','source_files':len(__import__('json').loads((PACKAGE/'PORTABLE_SOURCE_MANIFEST.json').read_text())['files']), 'model_count':0,'model_policy':'LAZY_PRIVATE_ASSETS_REQUIRED_ONLY_FOR_INFERENCE'}
