"""Use the existing controlled Scene fixture without modifying its source."""
import sys,json
from pathlib import Path
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H.parent/'PP1_EAG_APR_IMPLEMENTATION_V1'))
import runtime
runtime.common.HERE=H
r=runtime.fixtures.fixture(H/'INPUT_FIXTURE',guests=80,partial=True)
runtime.save(H/'SCENE_BRIEF.json',r)
print('Existing all-fixed controlled Scene fixture prepared; no real authority')
