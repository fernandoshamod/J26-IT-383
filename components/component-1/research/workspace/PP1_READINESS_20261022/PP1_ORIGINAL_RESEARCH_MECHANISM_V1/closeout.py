from lab import *
import importlib.metadata
events=guard()
before=read(H/'PRESERVATION_BEFORE.json');drift=[k for k,v in before.items() if sha(ROOT/k)!=v];assert not drift,drift
commands={p.name:read(p) for p in (H/'logs').glob('*.COMMAND.json')}
required=['WORLDS_001','NEGATIVE_001','POLICIES_001','VERIFY_002','CLI_001','REPORT_001','FIGURES_001']
assert all(commands[n+'.COMMAND.json']['exit_code']==0 for n in required),commands
failed={k:c for k,c in commands.items() if c['exit_code']!=0};assert set(failed)=={'VERIFY_001.COMMAND.json'},failed
check=read(H/'INDEPENDENT_VERIFICATION.json');assert check['status']=='PASS'
freeze=read(H/'PRE_EXECUTION_FREEZE.json');freeze.update(read(H/'POLICY_CODE_FREEZE.json'));protocol_drift=[k for k,v in freeze.items() if sha(ROOT/k)!=v];assert not protocol_drift,protocol_drift
save('PRESERVATION_FINAL.json',dict(status='PASS_WITH_PRESERVED_FAILED_VERIFIER_ATTEMPT',frozen_runtime_files=len(before),matches=len(before),scope='Original pinned runtime/checkpoint/config files plus guards; not an exhaustive new whole-project audit',protocol_matches=len(freeze),drift=drift,protocol_drift=protocol_drift,commands=commands,preserved_failed_commands=failed,guard=events))
save('ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,packages={n:importlib.metadata.version(n) for n in ['numpy','scipy','shapely','pymoo','pydantic','matplotlib']},seed=20261017,offline_flags={k:os.environ.get(k) for k in ['HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE','YOLO_OFFLINE','YOLO_AUTOINSTALL','PIP_NO_INDEX']},isolation='Python audit instrumentation, not OS network/write isolation'))
save('ARTIFACT_HASHES.json',{str(p.relative_to(H)):sha(p) for p in H.rglob('*') if p.is_file() and not str(p.relative_to(H)).startswith(('runtime\\','runtime/')) and p.name!='ARTIFACT_HASHES.json'})
print('Closeout PASS; frozen runtime',len(before),'files preserved',flush=True)
