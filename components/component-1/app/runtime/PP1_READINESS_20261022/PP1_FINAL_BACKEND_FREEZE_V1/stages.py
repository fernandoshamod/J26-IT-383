"""Existing authoritative checks, output binding only; no new algorithms."""
import sys
from pathlib import Path
H=Path(__file__).resolve().parent
stage=sys.argv[1];sys.argv=[sys.argv[0],*sys.argv[2:]]
allowed={'http_stage','lifecycle','negative_checks','scene_handoff','tcp_proof','finalize'}
if stage not in allowed:raise ValueError('UNKNOWN_STAGE')
source=H.parent/'PP1_REVIEWED_TWIN_SCENE_INTEGRATION_V1'/(stage+'.py')
if stage=='http_stage':
 # Make the reused HTTP acceptance script call the final stable factory.
 import common
 sys.path.append(str(H.parent/'PP1_FINAL_MODEL_INTEGRATION_V1'))
 import integrated_api
 from application import create_app
 integrated_api.create_app=create_app
 # integrated_factory captured the original function before this test binding.
exec(compile(source.read_text(encoding='utf-8'),str(source),'exec'),dict(__file__=str(H/(stage+'.py')),__name__='__main__'))
