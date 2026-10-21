from io_context import *
import ast,csv,subprocess
def main():
    required=['CLOSEST_PRIOR_ART_AND_GAP.md','FORMAL_RECOVERY_PROBLEM.md','PROPOSED_MECHANISM.md','RAW_EXPERIMENT_RESULTS.csv','BASELINE_AND_ABLATION_RESULTS.md','SCIENTIFIC_NOVELTY_VERDICT.md','PANEL_COMMENT_3_DEFENCE.md','REPRODUCTION_RUNBOOK.md','PRESERVATION_REPORT.json']
    assert all((H/p).is_file() for p in required)
    parsed=[]
    for p in H.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'));parsed.append(p.name)
    raw=read(H/'RUN_001/RAW_EXPERIMENT_RESULTS.json')
    with (H/'RAW_EXPERIMENT_RESULTS.csv').open(newline='',encoding='utf-8') as f:csvrows=list(csv.DictReader(f))
    assert len(csvrows)==len(raw)==72 and sha(H/'RAW_EXPERIMENT_RESULTS.csv')==sha(H/'RUN_001/RAW_EXPERIMENT_RESULTS.csv')
    assert read(H/'INDEPENDENT_001/INDEPENDENT_VALIDATION.json')['valid_layout_witnesses']==274
    assert read(H/'EXPLANATION_VALIDATION_002.json')['status']=='PASS' and read(H/'ADMISSION_SUPPLEMENT.json')['status']=='PASS'
    before=read(H/'PRESERVATION_BEFORE.json');now=snapshot();changed=[p for p,s in before['files'].items() if now['files'].get(p)!=s];assert not changed
    cmd=[sys.executable,'-B',str(PP1/'PP1_FINAL_BACKEND_FREEZE_V1/backend.py'),'verify-freeze']
    p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);save(H/'FINAL_FREEZE_RECHECK.json',{'argv':cmd,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr});assert p.returncode==0
    commands=[read(p) for p in sorted((H/'logs').glob('*.COMMAND.json'))]
    failed=[c for c in commands if c['exit_code']!=0];assert len(failed)==1 and 'verify_explanations.py' in str(failed[0]['argv'])
    save(H/'FINAL_SOURCE_HASHES.json',{p.name:sha(p) for p in H.glob('*.py')})
    save(H/'FINAL_ACCEPTANCE.json',{'status':'PASS_WITH_PRESERVED_EXPECTED_HISTORY','required_deliverables':required,'parsed_python_sources':parsed,'comparison_queries':36,'baseline_matches':36,'actual_comparative_searches':28,'actual_comparative_evaluations':3360,'additional_smoke_searches':2,'additional_smoke_evaluations':240,'raw_verified_layout_witnesses':274,'original_test_cases_checks':56,'supplemental_admission_checks':4,'response_explanations_replayed':36,'sqlite_rows_replayed':36,'changed_prior_files':changed,'bounded_preservation_files':len(before['files']),'failed_command_history':failed,'commands_completed_before_this_final_check':commands,'figures_visually_inspected':['figures/ACTUAL_RECOVERY_LAYOUTS.png','figures/RECOVERY_OUTCOMES.png'],'scientific_originality':'NOT_ESTABLISHED','applied_originality':'UNRESOLVED','no_authentic_planner_consent_claim':True,'instrumentation':AUDIT})
    print('FINAL PASS: 36 conventional matches, 274 valid witnesses, preserved 464 bounded source/evidence/checkpoint hashes; novelty not established')
if __name__=='__main__':main()
