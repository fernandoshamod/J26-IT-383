"""Final QA/provenance. Does not re-run algorithms or alter prior evidence."""
import ast,re,importlib.metadata
from runtime import *

required=['README.md','IMPLEMENTATION_REPORT.md','SCIENTIFIC_NOVELTY_EVALUATION.md','EXPERIMENT_COMPARISON.md','KNOWN_LIMITATIONS.md','PP1_EVIDENCE_SUMMARY.md','NEXT_IMPLEMENTATION_STEP.md']
checks=[]
def check(name,ok,detail=None):checks.append(dict(name=name,passed=bool(ok),detail=detail))
check('REQUIRED_REPORTS_EXIST',all((HERE/p).is_file() for p in required))
links=[]
for p in HERE.glob('*.md'):
    for _,target in re.findall(r'\[([^\]]+)\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
        if '://' not in target:links.append(dict(document=p.name,target=target,exists=(p.parent/target).exists()))
check('REPORT_LINKS',all(r['exists'] for r in links),links)
for p in HERE.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
check('SOURCE_SYNTAX',True)
for path in ['outputs/EXPERIMENT_FINAL/EXPERIMENT_RESULTS.json','outputs/TESTS_FINAL/TEST_RESULTS.json','outputs/CONTRACT_CHECKS_FINAL/TEST_RESULTS.json']:
    r=read(HERE/path);check(path,r['passed'])
check('CLOSEOUT_STATUS',read(HERE/'outputs/CLOSEOUT_FINAL/FINAL_ACCEPTANCE.json')['status']=='VERIFIED_CONTROLLED_ASSURANCE_PROTOTYPE_STRONG_BASELINE_EQUIVALENCE')
before=read(HERE/'outputs/EXPERIMENT_FINAL/PRESERVATION_BEFORE.json');check('PRIOR_SOURCE_EVIDENCE_CHECKPOINT_METADATA_UNCHANGED',before==snapshot(),dict(files=len(before),scope='SHA256 for <=1MB; size/mtime for larger files; not a raw dataset census'))
save(HERE/'EXECUTED_COMMANDS.json',dict(cwd=str(ROOT),python='.venv\\Scripts\\python.exe -B',script_directory=str(HERE.relative_to(ROOT)),commands=[dict(script='experiment.py',args='--out outputs/PILOT_001 --seeds 20261017',actual_exit_code=1,reason='Six singleton false refusals; retained and corrected'),dict(script='probe_adaptive.py',args='',actual_exit_code=0),dict(script='experiment.py',args='--out outputs/EXPERIMENT_FINAL',actual_exit_code=0),dict(script='tests_execution.py',args='',actual_exit_code=0),dict(script='closeout.py',args='',actual_exit_code=0),dict(script='render_actual.py',args='',actual_exit_code=0),dict(script='contract_checks.py',args='',actual_exit_code=0),dict(script='write_reports.py',args='',actual_exit_code=0)],nested_cli_commands=['outputs/CLOSEOUT_FINAL/CLI_COMMAND_RESULT.json','outputs/CONTRACT_CHECKS_FINAL/authorized_singleton_repair_COMMAND.json','outputs/CONTRACT_CHECKS_FINAL/missing_metric_verification_COMMAND.json'],earlier_12_39_10_null_experiments_not_rerun=True,primary_paper_retrieval_failure='Merrell PDF returned Internal Error on current attempts; preserved earlier primary review cited with explicit limitation'))
save(HERE/'PACKAGE_QA.json',dict(passed=all(r['passed'] for r in checks),checks=checks,packages={p:importlib.metadata.version(p) for p in ['pydantic','pymoo','shapely','numpy','scipy','Pillow','matplotlib']},independent_human_annotation=False,digital_signatures=False,figures_visually_inspected=True,no_frontend_weather_learning_cleanup_changes=True))
save(HERE/'CURRENT_SOURCE_SHA256.json',{p.name:filehash(p) for p in sorted(HERE.glob('*.py'))})
save(HERE/'ARTIFACT_SHA256.json',{str(p.relative_to(HERE)).replace('\\','/'):filehash(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='ARTIFACT_SHA256.json'})
print(__import__('json').dumps(dict(passed=all(r['passed'] for r in checks),checks=len(checks),preserved_files=len(before),required_reports=len(required))))
if not all(r['passed'] for r in checks):raise SystemExit(1)
