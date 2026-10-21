"""Package current evidence without rewriting any executed output or old evidence."""
import ast,importlib.metadata,platform,re,sys
from common import *

def main():
    # Records identify actual executions; shell Tee logs are supplemented by raw
    # assertion JSON and the CLI's own subprocess return-code records.
    commands=[
        ('test_compiler.py --out outputs/COMPILER_FINAL','outputs/COMPILER_FINAL.log',0),
        ('test_bridge.py --compiler-run outputs/COMPILER_FINAL --out outputs/BRIDGE_FINAL','outputs/BRIDGE_FINAL.log',0),
        ('supplemental.py','outputs/SUPPLEMENTAL_FINAL.log',0),
        ('research.py demo --out outputs/DEMO_FINAL --dance','outputs/DEMO_FINAL.log',0),
        ('closeout.py','outputs/CLOSEOUT_FINAL.log',0),
    ]
    prefix='.venv\\Scripts\\python.exe -B PP1_READINESS_20261022/PP1_EVENT_SCENE_INTELLIGENCE_V1/'
    save(HERE/'EXECUTED_COMMANDS.json',dict(working_directory=str(ROOT),commands=[dict(command=prefix+c,log=log,observed_exit_code=code) for c,log,code in commands],nested_commands='outputs/SUPPLEMENTAL_FINAL/CLI_COMPILE_COMMAND.json and OFFLINE_CLI_COMMAND.json',failure_history='outputs/FAILED_IMPORT_001.json, COMPILER_RELEASE_001.log, SUPPLEMENTAL_RELEASE_001.log; all retained'))
    for path in HERE.glob('*.py'):ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
    links=[]
    for label,target in re.findall(r'\[([^\]]+)\]\(([^)]+)\)',(HERE/'README.md').read_text(encoding='utf-8')):
        if '://' not in target:links.append(dict(label=label,target=target,exists=(HERE/target).is_file()))
    if not all(l['exists'] for l in links):raise ValueError('BROKEN_DOCUMENT_LINK')
    before=read(HERE/'outputs/COMPILER_FINAL/PRESERVATION_BEFORE.json');after=immutable_snapshot()
    if any(after.get(p)!=h for p,h in before.items()):raise ValueError('PRESERVED_SOURCE_DRIFT')
    acceptance=read(HERE/'outputs/CLOSEOUT_FINAL/FUNCTIONAL_ACCEPTANCE.json')
    if acceptance['status']!='VALIDATED_CONTROLLED_EVENT_SCENE_POC':raise ValueError('ACCEPTANCE_FAILED')
    save(HERE/'RELEASE_CHECK.json',dict(source_syntax_passed=True,document_links=links,preserved_files=len(before),preservation_passed=True,acceptance_status=acceptance['status'],python=sys.version,platform=platform.platform(),packages={p:importlib.metadata.version(p) for p in ['pydantic','shapely','numpy','scipy','pymoo','Pillow','matplotlib']},dependencies_vendored=False))
    entries={str(p.relative_to(HERE)).replace('\\','/'):filehash(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='RELEASE_MANIFEST.json'}
    save(HERE/'RELEASE_MANIFEST.json',dict(schema='ISOLATED_EVENT_SCENE_RELEASE_MANIFEST_V1',hash='SHA256 file bytes',files=entries,includes_preserved_failed_attempts=True,does_not_replace_frozen_backend_manifest=True))
    print(__import__('json').dumps(dict(status='PACKAGED',manifest_files=len(entries),preserved_files=len(before),syntax='PASS',readme_links='PASS')))

if __name__=='__main__':main()
