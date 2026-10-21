"""Execute the existing seven-branch worker unchanged, with only __file__ output binding."""
from pathlib import Path
import hashlib,json,sys
H=Path(__file__).resolve().parent
source=H.parent/'PP1_FINAL_DEMO_REHEARSAL_V1/worker.py'
text=source.read_text(encoding='utf-8')
out=H/sys.argv[1]
assert out.is_dir() and out.parent==H
(out/'WORKER_BINDING.json').write_text(json.dumps({'actual_executed_source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'output___file___binding':str(Path(__file__).resolve()),'code_replacements':0,'reason':'Original worker uses HERE for isolated output and sibling dependency discovery. Same source executes with HERE at integration folder; source/evidence/permission rules unchanged.','separate_process':'Prevents model/common versus Scene/common module-name collisions'},indent=2),encoding='utf-8')
exec(compile(text,str(source),'exec'),{'__file__':str(Path(__file__).resolve()),'__name__':'__main__'})
