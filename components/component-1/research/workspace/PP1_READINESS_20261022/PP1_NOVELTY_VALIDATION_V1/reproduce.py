import sys,shutil,subprocess
from pathlib import Path
H=Path(__file__).resolve().parent;name=sys.argv[1]
if not name.startswith('PP1_NOVELTY_VALIDATION_REPEAT_') or Path(name).name!=name:raise ValueError('EXPLICIT_NEW_PEER_NAME_REQUIRED')
out=H.parent/name;out.mkdir(exist_ok=False)
for source in H.glob('*.py'):shutil.copyfile(source,out/source.name)
for label,script in [('BENCHMARK','benchmark.py'),('VERIFY','verify_results.py')]:subprocess.run([sys.executable,'-B',str(out/'run_logged.py'),label,script],cwd=H.parents[1],check=True)
print('Fresh benchmark and independent replay complete. Read the new raw results/verification; original scientific reports retain their original command/failure history.')
