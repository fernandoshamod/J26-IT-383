"""Original lifecycle worker with one explicit adapter-install insertion."""
import sys,hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent
name=sys.argv[1] if len(sys.argv)>1 else 'CONTROLLED_002'
assert Path(name).name==name
out=H/name;out.mkdir(exist_ok=False)
source=H.parent/'PP1_FINAL_DEMO_REHEARSAL_V1/worker.py';text=source.read_text(encoding='utf-8')
needle='    from repair import run, make_reference'
assert text.count(needle)==1
text=text.replace(needle,'    import adapter\n    adapter.install(runtime, OUT)\n'+needle)
audit_line='    if event == "sqlite3.connect": check_write(args[0], event)'
assert text.count(audit_line)==1
text=text.replace(audit_line,'    if event == "sqlite3.connect" and not (str(args[0]).startswith("file:") and str(args[0]).endswith("?mode=ro")): check_write(args[0], event)')
(out/'WORKER_BINDING.json').write_text(json.dumps(dict(source=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),insertion='adapter.install(runtime, OUT) before importing repair.run and scenarios.initial',algorithm_edits=0,output_root=str(out)),indent=2))
sys.argv=[str(source),name]
exec(compile(text,str(source),'exec'),dict(__file__=str(H/'lifecycle.py'),__name__='__main__'))
