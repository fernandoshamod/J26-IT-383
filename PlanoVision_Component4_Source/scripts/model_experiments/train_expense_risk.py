"""New versioned expense-workflow experiment. All historical releases stay intact."""
from collections import Counter
from datetime import datetime,timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import numpy as np
from sklearn.dummy import DummyClassifier
from xgboost import XGBClassifier,Booster,DMatrix
from component4.expense_risk import load_design,generate,audit,FEATURES,TARGETS
from component4.engine import fingerprint
from component4.release_input import sha256,assert_experiment_output
from component4.risk_experiment import metrics
from component4.model_explanations import validate_additivity


def save(path,value):
    with path.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,allow_nan=False)


def jsonl(path,rows):
    with path.open('x',encoding='utf-8') as f:
        for row in rows:f.write(json.dumps(row,allow_nan=False,separators=(',',':'))+'\n')


def main():
    design=load_design();run=design['run_id']
    data=assert_experiment_output(ROOT/'data/experiments/v3.0'/run)
    output=assert_experiment_output(ROOT/'outputs/experiments/v3.0'/run)
    report=assert_experiment_output(ROOT/'reports/experiments/v3.0'/run)
    if any(p.exists() for p in (data,output,report)):raise ValueError('refuse_existing_run')
    protected=[ROOT/'outputs/Component4_Hybrid_Dataset_Final_v1.0.zip',ROOT/'dataset_releases/v1.0/Component4_Hybrid_Dataset_Final_v1.0.zip']
    for base in ('data/experiments','outputs/experiments','reports/experiments'):
        for version in ('v1.0','v1.1','v2.0'):
            protected.extend(p for p in (ROOT/base/version).rglob('*') if p.is_file())
    before={p.relative_to(ROOT).as_posix():sha256(p) for p in protected}
    for p in (data,output,report):p.mkdir(parents=True)
    source_paths=['config/expense_risk.v3.0.json','config/lkr_research.v2.0.json','component4/expense_risk.py',
                  'component4/lkr_research.py','component4/planner_services.py','scripts/model_experiments/train_expense_risk.py']
    from component4.lkr_research import load_config
    source_paths.append(load_config()[0]['source_file'])
    protocol={'run_id':run,'recorded_before_fitting_utc':datetime.now(timezone.utc).isoformat(),'design':design,
        'design_sha256':fingerprint(design),'features':FEATURES,'targets':TARGETS,
        'source_hashes':{p:sha256(ROOT/p) for p in source_paths},'protected_old_files':before,
        'runtime':{'python':platform.python_version(),**{p:importlib.metadata.version(p) for p in ('numpy','scikit-learn','xgboost')}},
        'feature_availability':'planning_only; outcomes, latent shocks, ancestry and split IDs excluded',
        'evaluation_scope':'conditional_synthetic_simulator_only; no actual event outcomes'}
    save(output/'protocol.json',protocol)
    print('Generating workflow-aligned synthetic configurations...',flush=True)
    rows,ledger,provenance=generate(design);checks=audit(rows,ledger,provenance)
    if (rows,ledger,provenance)!=generate(design):raise ValueError('replay_failure')
    jsonl(data/'planning_risk_dataset.jsonl',rows);jsonl(data/'financial_line_items.jsonl',ledger);jsonl(data/'provenance.jsonl',provenance)
    jsonl(data/'split_manifest.jsonl',[{k:r[k] for k in ('Scenario_ID','Base_Event_ID','split','planning_state','outcome_replication')} for r in rows])
    save(data/'manifest.json',{'run_id':run,'design':design,'audit':checks,'origin':'synthetic_LKR_not_observed_event','replay':'PASS'})
    parts={s:[r for r in rows if r['split']==s] for s in ('train','validation','test')}
    x={s:np.asarray([[r[f] for f in FEATURES] for r in rs],dtype=float) for s,rs in parts.items()}
    scores={};classes={};shap_checks={};predictions=[]
    for target in TARGETS:
        y={s:np.asarray([r[target] for r in rs],dtype=np.int32) for s,rs in parts.items()}
        if any(len(set(v.tolist()))!=2 for v in y.values()):raise ValueError('both_classes_required')
        settings=design['training'];model=XGBClassifier(n_estimators=settings['n_estimators'],max_depth=settings['max_depth'],
            learning_rate=settings['learning_rate'],n_jobs=1,random_state=design['seed'],objective='binary:logistic',eval_metric='logloss',tree_method='hist',
            monotone_constraints=tuple(settings['monotonic_constraints'].get(f,0) for f in FEATURES))
        model.fit(x['train'],y['train']);model.save_model(output/(target+'.xgboost.json'))
        prior=DummyClassifier(strategy='prior').fit(x['train'],y['train'])
        scores[target]={};classes[target]={s:dict(Counter(v.tolist())) for s,v in y.items()}
        for split in ('validation','test'):
            predicted=model.predict_proba(x[split])[:,1]
            rule=np.asarray([int(r['Planned_Total_Cost_LKR']>r['Target_Budget_LKR']) if target=='Budget_Overrun' else int(r['Planned_Margin_Buffer_Pct']<0) for r in parts[split]],dtype=float)
            # Hard-rule baseline outputs classes, not calibrated probabilities.
            scores[target][split]={'xgboost':metrics(y[split],predicted),'prior':metrics(y[split],prior.predict_proba(x[split])[:,1]),
                'planning_rule_class_accuracy':float(np.mean(rule==y[split])),
                'planning_rule_balanced_accuracy':float(np.mean([np.mean(rule[y[split]==c]==c) for c in (0,1)]))}
            for row,p in zip(parts[split],predicted):predictions.append({'Scenario_ID':row['Scenario_ID'],'split':split,'target':target,'label':row[target],'uncalibrated_score':float(p)})
        booster=Booster();booster.load_model(bytearray((output/(target+'.xgboost.json')).read_bytes()))
        matrix=DMatrix(x['test']);phi=booster.predict(matrix,pred_contribs=True,approx_contribs=False)
        margins=booster.predict(matrix,output_margin=True);native=booster.predict(matrix)
        if not np.allclose(native,model.predict_proba(x['test'])[:,1],atol=1e-7):raise ValueError('native_reload_mismatch')
        shap_checks[target]=validate_additivity(phi,margins,native,len(FEATURES))
        np.savez_compressed(output/(target+'.test_shap.npz'),features=x['test'],contributions=phi,margins=margins,scores=native,
                            scenario_ids=np.asarray([r['Scenario_ID'] for r in parts['test']]))
        print('Fitted native XGBoost + TreeSHAP:',target,flush=True)
    jsonl(output/'heldout_predictions.jsonl',predictions)
    model_hashes={t:sha256(output/(t+'.xgboost.json')) for t in TARGETS}
    support={event:{f:[min(r[f] for r in parts['train'] if r['Event_Type_'+event]==1),max(r[f] for r in parts['train'] if r['Event_Type_'+event]==1)] for f in FEATURES} for event in ('Wedding','Corporate')}
    save(output/'metadata.json',{'run_id':run,'features':FEATURES,'targets':TARGETS,'model_sha256':model_hashes,
        'design_sha256':fingerprint(design),'training_marginal_bounds':support,'calibrated':False,'currency':'LKR',
        'support_policy':'reject incompatible financial regime; withhold outside training marginal bounds, not proof of joint support'})
    changed=[name for name,digest in before.items() if sha256(ROOT/name)!=digest]
    if changed:raise ValueError('historical_files_changed:'+str(changed))
    result={'status':'PASS_INTERNAL_SYNTHETIC_TRAINING','run_id':run,'dataset':checks,'classes':classes,'metrics':scores,'shap_checks':shap_checks,
        'replay':'PASS','native_reload':'PASS','protected_historical_files_unchanged':len(before),
        'limitations':design['limitations'],'real_world_accuracy_established':False,'test_tuning_performed':False}
    save(report/'experiment_summary.json',result)
    inventory={p.relative_to(ROOT).as_posix():sha256(p) for base in (data,output,report) for p in base.rglob('*') if p.is_file()}
    save(report/'checksums.json',inventory)
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
