"""Replay diagnostic memberships/aggregates/errors and eight disposable curve fits."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import json
import numpy as np
from component4.enhanced_risk_inference import EnhancedRiskInference
from component4.risk_enhancement import group_folds,fit,matrix,selected_features
from component4.model_diagnostics import nested_family_subsets,error_audit
from component4.risk_experiment import metrics
from component4.release_input import sha256
from scripts.model_experiments.audit_errors_and_learning_curves import aggregate


def read(path):return [json.loads(line) for line in path.read_text().splitlines()]


def main():
    folder=ROOT/'reports/diagnostics/v3_1_steps1_2_20261016'
    protocol=json.loads((folder/'protocol.json').read_text());p=protocol['design']
    for name,digest in protocol['source_hashes'].items():assert sha256(ROOT/name)==digest,'source_changed:'+name
    for name,digest in protocol['protected_files'].items():assert sha256(ROOT/name)==digest,'protected_file_changed:'+name
    for name,digest in json.loads((folder/'checksums.json').read_text()).items():assert sha256(folder/name)==digest,'diagnostic_artifact_changed:'+name
    risk=EnhancedRiskInference();settings=json.loads((risk.folder/'protocol.json').read_text())['design']
    rows=read(ROOT/'data/experiments/v3.0'/p['data_run']/'planning_risk_dataset.jsonl');training=[r for r in rows if r['split']=='train']
    membership=read(folder/'learning_curve_membership.jsonl');expected=[]
    replay_fits=0
    runs=read(folder/'learning_curve_runs.jsonl')
    assert len(runs)==180
    for fold,(tr,va) in enumerate(group_folds(training,p['outer_group_folds'])):
        outer_train=[training[i] for i in tr];valid=[training[i] for i in va];valid_ids=sorted({r['Base_Event_ID'] for r in valid})
        for repeat in range(p['subsample_repeats']):
            subsets=nested_family_subsets(outer_train,p['training_family_counts'],p['seed']+fold*100+repeat)
            for n,subset,ids in subsets:
                assert not set(ids)&set(valid_ids)
                expected.append({'outer_fold':fold,'repeat':repeat,'training_families':n,'training_family_ids':ids,'validation_family_ids':valid_ids,'source_split':'train'})
                matching=[r for r in runs if r['outer_fold']==fold and r['repeat']==repeat and r['training_families']==n]
                assert len(matching)==4
                for record in matching:
                    assert record['original_split']=='train' and record['training_rows']==len(subset) and record['validation_rows']==len(valid)
                    if fold==0 and repeat==0 and n in (p['training_family_counts'][0],p['training_family_counts'][-1]):
                        candidate=next(c for c in settings['candidates'] if c['id']==record['candidate'])
                        model=fit(settings,candidate,record['target'],subset,risk.design['training']['monotonic_constraints'])
                        fs=selected_features(settings,candidate,record['target'])
                        for split,part in (('train',subset),('validation',valid)):
                            measured=metrics([r[record['target']] for r in part],model.predict_proba(matrix(part,fs))[:,1])
                            for key,value in measured.items():assert np.isclose(value,record[split][key]),'learning_curve_metric_replay'
                        replay_fits+=1
    assert membership==expected
    assert aggregate(runs)==json.loads((folder/'learning_curve_summary.json').read_text())['curves']
    assumptions=json.loads((ROOT/'config/lkr_research.v2.0.json').read_text())['assumptions']
    audit,cases=error_audit(rows,read(risk.folder/'heldout_predictions.jsonl'),assumptions,p)
    assert audit==json.loads((folder/'error_audit.json').read_text())['strata_and_counts']
    assert cases==read(folder/'error_cases.jsonl')
    assert all(sha256(ROOT/k)==v for k,v in protocol['protected_files'].items())
    result={'status':'PASS','whole_family_membership_replay':len(membership),'error_case_replay':len(cases),
        'aggregate_replay':'PASS','disposable_model_metric_replay_fits':replay_fits,
        'protected_files_unchanged':len(protocol['protected_files']),'production_model_deployment':False,
        'validation_or_test_source_rows_fitted':False,'new_dataset_generated':False}
    (folder/'independent_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
