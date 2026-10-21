"""Verify existing v3.1 artifacts, folds, held-out metrics and native TreeSHAP."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import json
import numpy as np
from xgboost import DMatrix
from component4.enhanced_risk_inference import EnhancedRiskInference
from component4.risk_enhancement import matrix,group_folds,family_intervals
from component4.risk_experiment import metrics
from component4.expense_risk import FEATURES,TARGETS
from component4.release_input import sha256
from component4.model_explanations import validate_additivity


def read(path):return [json.loads(line) for line in path.read_text().splitlines()]


def main():
    risk=EnhancedRiskInference();protocol=json.loads((risk.folder/'protocol.json').read_text())
    assert all(sha256(ROOT/k)==v for k,v in protocol['protected_files'].items())
    rows=read(ROOT/'data/experiments/v3.0'/risk.original_run/'planning_risk_dataset.jsonl')
    byid={r['Scenario_ID']:r for r in rows};train=[r for r in rows if r['split']=='train']
    oof=read(risk.folder/'nested_oof_predictions.jsonl');heldout=read(risk.folder/'heldout_predictions.jsonl');shap={}
    decisions=json.loads((risk.folder/'selection_decisions.before_test.json').read_text())
    for target in TARGETS:
        predictions=[r for r in oof if r['target']==target]
        assert len(predictions)==len(train) and len({r['Scenario_ID'] for r in predictions})==len(train)
        expected={train[i]['Scenario_ID']:fold for fold,(_,valid) in enumerate(group_folds(train)) for i in valid}
        assert all(byid[p['Scenario_ID']]['split']=='train' and p['outer_fold']==expected[p['Scenario_ID']] and p['label']==byid[p['Scenario_ID']][target] for p in predictions)
        for k,v in metrics([p['label'] for p in predictions],[p['score'] for p in predictions]).items():
            assert np.isclose(v,risk.summary['metrics'][target]['nested_cv']['oof_metrics'][k])
        assert decisions[target]==risk.summary['deployment'][target]
        assert not decisions[target]['selection_uses_test']
        fs=risk.metadata['model_features'][target];model=risk.models[target]
        for split in ('validation','test'):
            part=[r for r in rows if r['split']==split];saved=[r for r in heldout if r['target']==target and r['split']==split]
            x=DMatrix(matrix(part,fs));p=model.predict(x)
            assert [r['Scenario_ID'] for r in part]==[r['Scenario_ID'] for r in saved]
            assert np.allclose(p,[r['score'] for r in saved],atol=1e-8)
            measured=metrics([r[target] for r in part],p)
            for k,v in measured.items():assert np.isclose(v,risk.summary['metrics'][target][split]['xgboost'][k])
            interval=family_intervals(part,target,p,[r['original_score'] for r in saved],protocol['design']['bootstrap_family_draws'],protocol['design']['seed'])
            assert interval==risk.summary['metrics'][target][split]['family_bootstrap']
            if split=='test':
                stored=np.load(risk.folder/(target+'.test_shap.npz'),allow_pickle=False)
                phi=model.predict(x,pred_contribs=True,approx_contribs=False);margin=model.predict(x,output_margin=True)
                assert np.array_equal(stored['features'],matrix(part,fs))
                assert np.array_equal(stored['scenario_ids'],[r['Scenario_ID'] for r in part])
                assert np.allclose(stored['contributions'],phi) and np.allclose(stored['scores'],p) and np.allclose(stored['margins'],margin)
                shap[target]=validate_additivity(phi,margin,p,len(fs))
    result={'status':'PASS','run_id':risk.run_id,'historical_files_unchanged':len(protocol['protected_files']),
        'original_dataset_and_splits_unchanged':True,'nested_outer_assignment_and_saved_oof_metrics':'PASS',
        'saved_prediction_replay':'PASS','root_bootstrap_replay':'PASS','full_test_TreeSHAP':shap,
        'test_was_previously_inspected':True,'real_world_validation':False,'fit_performed_by_verifier':False}
    (risk.report/'independent_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
