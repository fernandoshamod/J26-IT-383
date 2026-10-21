"""One versioned nested-group experiment; never regenerate data or tune on test."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from datetime import datetime,timezone
import importlib.metadata
import json
import numpy as np
from xgboost import Booster,DMatrix
from component4.expense_risk import FEATURES,TARGETS
from component4.expense_risk_inference import ExpenseRiskInference
from component4.risk_enhancement import nested,search,fit,matrix,selected_features,family_intervals
from component4.risk_experiment import metrics
from component4.release_input import sha256
from component4.model_explanations import validate_additivity


def save(path,value):
    with path.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,allow_nan=False)


def jsonl(path,rows):
    with path.open('x',encoding='utf-8') as f:
        for r in rows:f.write(json.dumps(r,allow_nan=False)+'\n')


def main():
    p=json.loads((ROOT/'config/risk_enhancement.v3.1.json').read_text());old=ExpenseRiskInference()
    output=ROOT/'outputs/experiments/v3.1'/p['run_id'];report=ROOT/'reports/experiments/v3.1'/p['run_id']
    if output.exists() or report.exists():raise ValueError('refuse_existing_experiment')
    protected=json.loads((old.report/'checksums.json').read_text())
    protected.update(json.loads((old.folder/'protocol.json').read_text())['protected_old_files'])
    for base in (old.folder,old.report,ROOT/'data/experiments/v3.0'/old.run_id):
        protected.update({f.relative_to(ROOT).as_posix():sha256(f) for f in base.rglob('*') if f.is_file()})
    source=['config/risk_enhancement.v3.1.json','component4/risk_enhancement.py','scripts/model_experiments/enhance_expense_risk.py']
    source_hashes=json.loads((old.folder/'protocol.json').read_text())['source_hashes']
    source_hashes.update({k:sha256(ROOT/k) for k in source})
    output.mkdir(parents=True);report.mkdir(parents=True)
    save(output/'protocol.json',{'recorded_before_fitting_utc':datetime.now(timezone.utc).isoformat(),'design':p,
        'source_hashes':source_hashes,'protected_files':protected,'runtime':{k:importlib.metadata.version(k) for k in ('numpy','xgboost','scikit-learn')},
        'dataset_regeneration':False,'test_role':'previously inspected retrospective audit only; never selection or deployment gating'})
    path=ROOT/'data/experiments/v3.0'/old.run_id/'planning_risk_dataset.jsonl'
    rows=[json.loads(line) for line in path.read_text().splitlines()]
    parts={s:[r for r in rows if r['split']==s] for s in ('train','validation','test')}
    monotonic=old.design['training']['monotonic_constraints'];evaluations={};all_oof=[];final_predictions=[];used={};deployment={};shap={}
    # Complete selection and engineering validation decisions before accessing test in evaluation.
    for target in TARGETS:
        print('Nested grouped CV:',target,flush=True)
        cv,oof=nested(p,target,parts['train'],monotonic);all_oof+=oof
        winner,candidates=search(p,target,parts['train'],monotonic)
        candidate=fit(p,winner,target,parts['train'],monotonic);fs=selected_features(p,winner,target)
        val=candidate.predict_proba(matrix(parts['validation'],fs))[:,1]
        vm=metrics([r[target] for r in parts['validation']],val);previous=old.summary['metrics'][target]['validation']['xgboost']
        gate=vm['log_loss']<=previous['log_loss']+p['deployment_gate']['max_validation_log_loss_increase'] and vm['balanced_accuracy']>=previous['balanced_accuracy']-p['deployment_gate']['max_validation_balanced_accuracy_drop']
        decision={'training_cv_winner':winner['id'],'validation_gate_pass':gate,'candidate_validation_metrics':vm,
            'deployed':'enhanced_candidate' if gate else 'retained_v3_0','selection_uses_test':False}
        if gate:candidate.save_model(output/(target+'.xgboost.json'));used[target]=fs
        else:
            (output/(target+'.xgboost.json')).write_bytes((old.folder/(target+'.xgboost.json')).read_bytes());used[target]=FEATURES
        deployment[target]=decision;evaluations[target]={'nested_cv':cv,'training_search':candidates}
    save(output/'selection_decisions.before_test.json',deployment)
    for target in TARGETS:
        model=Booster();model.load_model(bytearray((output/(target+'.xgboost.json')).read_bytes()));fs=used[target]
        summary={}
        for split in ('validation','test'):
            part=parts[split];x=DMatrix(matrix(part,fs));score=model.predict(x)
            original=old.models[target].predict(DMatrix(matrix(part,FEATURES)));y=np.asarray([r[target] for r in part])
            rule=np.asarray([int(r['Planned_Budget_Utilization']>1) if target=='Budget_Overrun' else int(r['Planned_Margin_Buffer_Pct']<0) for r in part])
            summary[split]={'xgboost':metrics(y,score),'original_v3':metrics(y,original),
                'prior':old.summary['metrics'][target][split]['prior'],
                'planning_rule_class_accuracy':float(np.mean(rule==y)),
                'family_bootstrap':family_intervals(part,target,score,original,p['bootstrap_family_draws'],p['seed']),
                'by_event_type':{event:metrics(y[[r['Event_Type_'+event]==1 for r in part]],score[[r['Event_Type_'+event]==1 for r in part]]) for event in ('Wedding','Corporate')}}
            final_predictions.extend({'Scenario_ID':r['Scenario_ID'],'Base_Event_ID':r['Base_Event_ID'],'split':split,'target':target,'label':r[target],'score':float(s),'original_score':float(o)} for r,s,o in zip(part,score,original))
            if split=='test':
                phi=model.predict(x,pred_contribs=True,approx_contribs=False);margins=model.predict(x,output_margin=True)
                shap[target]=validate_additivity(phi,margins,score,len(fs))
                np.savez_compressed(output/(target+'.test_shap.npz'),features=matrix(part,fs),contributions=phi,margins=margins,scores=score,scenario_ids=np.asarray([r['Scenario_ID'] for r in part]))
        evaluations[target].update(summary)
    jsonl(output/'nested_oof_predictions.jsonl',all_oof);jsonl(output/'heldout_predictions.jsonl',final_predictions)
    metadata={**old.metadata,'run_id':p['run_id'],'model_features':used,'model_sha256':{t:sha256(output/(t+'.xgboost.json')) for t in TARGETS},'enhancement_protocol_sha256':sha256(output/'protocol.json')}
    save(output/'metadata.json',metadata)
    assert all(sha256(ROOT/k)==v for k,v in protected.items()),'historical_artifact_changed'
    result={'status':'PASS_INTERNAL_SYNTHETIC_EVALUATION','run_id':p['run_id'],'dataset':old.summary['dataset'],
        'metrics':evaluations,'deployment':deployment,'shap_checks':shap,'protected_files_unchanged':len(protected),
        'previously_inspected_test':True,'real_world_accuracy_established':False,'numerical_rules_or_splits_changed':False,'disclosure':p['disclosure']}
    save(report/'experiment_summary.json',result)
    save(report/'checksums.json',{f.relative_to(ROOT).as_posix():sha256(f) for base in (output,report) for f in base.rglob('*') if f.is_file()})
    print(json.dumps({t:{'deployment':deployment[t],'nested_cv_accuracy':evaluations[t]['nested_cv']['oof_metrics']['accuracy'],'test':evaluations[t]['test']} for t in TARGETS},indent=2))


if __name__=='__main__':main()
