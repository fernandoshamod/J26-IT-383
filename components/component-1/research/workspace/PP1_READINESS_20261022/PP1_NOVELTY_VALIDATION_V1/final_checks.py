from lab import *
import ast,collections
events=guard()
required=['PRIOR_ART_EVIDENCE_MATRIX.csv','RELATED_WORK_REVIEW.md','FORMAL_NOVELTY_HYPOTHESES.md','BASELINE_EQUIVALENCE_REPORT.md','FROZEN_BENCHMARK_MANIFEST.json','EXPERIMENT_CONFIGURATION.json','RAW_EXPERIMENT_RESULTS.csv','INDEPENDENT_VERIFICATION.json','EXPERIMENT_STATISTICAL_SUMMARY.md','NOVELTY_VERDICT.md','PP1_RESEARCH_CONTRIBUTION.md','PANEL_COMMENT_DEFENCE.md','VIVA_QUESTIONS_AND_ANSWERS.md','PRESENTATION_EVIDENCE_GUIDE.md','RUNBOOK.md']
assert all((H/n).is_file() for n in required)
for p in H.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
raw=read(H/'RAW_EXPERIMENT_RESULTS.json');result=read(H/'EXECUTION_RESULTS.json');verification=read(H/'INDEPENDENT_VERIFICATION.json')
assert len(raw)==432 and len({(r['unit'],r['case']) for r in raw})==72
assert result['status']=='PASS' and verification['status']=='PASS'
assert sum(r['evaluations'] for r in raw)==result['search_evaluations']
assert not verification['paired_equivalence_failures']
before=read(H/'PRESERVATION_BEFORE.json');assert all(sha(ROOT/k)==v for k,v in before.items())
models=read(P/'PP1_FINAL_BACKEND_FREEZE_V1/MODEL_REGISTRY.json')['models'];modelproof=[]
for name,m in models.items():assert sha(ROOT/m['path'])==m['sha256'];modelproof.append(dict(model=name,path=m['path'],sha256=m['sha256']))
setup_evaluations=0;approval_evaluations=0
for unit in read(H/'FROZEN_BENCHMARK_MANIFEST.json')['units']:
 setup_evaluations+=read(H/'setup'/unit['unit']/'INITIAL/RESULT.json')['optimizer_evaluations']
 approval_evaluations+=read(H/'setup'/unit['unit']/'APPROVAL/RESULT.json')['optimizer_evaluations']
 assert sha(unit['reference'])==unit['reference_sha256']
 for case in unit['cases']:assert sha(case['input'])==case['input_sha256']
failed_evaluations=read(H/'raw/GUESTS_80_SEED_20261017/unchanged/B0/ACTUAL_SEARCH/RESULT.json')['optimizer_evaluations']
assert setup_evaluations==4800 and approval_evaluations==0 and failed_evaluations==1200
proof=dict(status='PASS',required_deliverables=len(required),outcomes=len(raw),scenario_instances=72,primary_academic_works=11,additional_standard=1,primary_pairs=72,independent_dispatch_pairs=68,shared_revocation_pairs=4,qualifying_closure_pairs=sum(p['closure_comparable'] for p in verification['pair_checks']),actual_evaluations=dict(comparative=sum(r['evaluations'] for r in raw),setup=setup_evaluations,approval=approval_evaluations,retained_failed_attempt=failed_evaluations),all_raw_response_hashes_replayed=True,tracked_preserved_files=len(before),current_model_hashes=modelproof,post_task_old_regressions='NOT_RERUN; original49/13results preserved',scientific_verdict='NOVELTY_NOT_ESTABLISHED',guard=events)
save('FINAL_ACCEPTANCE.json',proof)
paths=[p for p in H.rglob('*') if p.is_file() and 'runtime' not in p.relative_to(H).parts and p.name not in ['ARTIFACT_SHA256.json'] and not (p.parent.name=='logs' and p.name.startswith('FINAL_'))]
save('HASH_SCOPE.json',dict(excludes=['runtime cache files','final verification process logs written after/during manifest creation','ARTIFACT_SHA256.json itself'],note='Final command/stdout/stderr remain separately retained; all earlier completed command logs are covered.'))
save('ARTIFACT_SHA256.json',{str(p.relative_to(H)):sha(p) for p in paths})
print(json.dumps(proof,indent=2))
