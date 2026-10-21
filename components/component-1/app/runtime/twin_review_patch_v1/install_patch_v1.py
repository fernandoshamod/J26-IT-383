"""Safe installer for existing PP1_STAGE_E_EVENT_LAYOUT_V2, only additive edits."""
from pathlib import Path
import shutil
import sys

if len(sys.argv) != 2:
    raise SystemExit('Usage: python install_patch_v1.py "C:\\...\\PP1_STAGE_E_EVENT_LAYOUT_V2"')
root = Path(sys.argv[1]).resolve()
source = Path(__file__).resolve().parent
app = root / 'frontend' / 'app.py'
if not app.is_file():
    raise FileNotFoundError(f'Expected existing frontend: {app}')
marker = '# PP1_STAGE_D_PLANNER_REVIEW_STEP3_V1'
text = app.read_text(encoding='utf-8-sig')
if marker in text:
    raise RuntimeError('Patch already installed; no files changed.')
targets = [(source/'planner_review_step3_v1.py',root/'frontend'/'planner_review_step3_v1.py'),
           (source/'spatial_twin_gate_v1.py',root/'backend'/'spatial_twin_gate_v1.py')]
for s,d in targets:
    if d.exists():
        if d.read_bytes()!=s.read_bytes():
            raise FileExistsError(f'File exists with different content: {d}')
# Write backup and copy only AFTER all checks.
backup = app.with_name('app_before_step3_v1.py')
if backup.exists():
    raise FileExistsError(f'Backup already exists: {backup}')
shutil.copy2(app,backup)
for s,d in targets:
    if not d.exists():
        shutil.copy2(s,d)
addition = ('\n\n'+marker+'\n'
            'from planner_review_step3_v1 import render as render_stage_d_review\n'
            'render_stage_d_review(ROOT)\n')
app.write_text(text.rstrip()+addition,encoding='utf-8')
print('EXISTING FRONTEND STEP 3 PATCH INSTALLED')
print('Backup:',backup)
print('App:',app)
print('Geometry gate:',root/'backend'/'spatial_twin_gate_v1.py')
print('Stage E real-venue optimizer: NOT CONNECTED')
