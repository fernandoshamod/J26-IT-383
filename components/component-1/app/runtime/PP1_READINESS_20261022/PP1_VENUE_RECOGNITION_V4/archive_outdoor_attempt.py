from pathlib import Path
import shutil
H=Path(__file__).resolve().parent
src=(H/'outdoor').resolve();dest=(H/'outdoor_attempt001').resolve()
assert src.parent==H and dest.parent==H
src.rename(dest)
for name in ['outdoor_evidence.py','test_outdoor.py','qualify_outdoor.py']:shutil.copyfile(H/name,dest/('SOURCE_AT_FAILURE_'+name))
