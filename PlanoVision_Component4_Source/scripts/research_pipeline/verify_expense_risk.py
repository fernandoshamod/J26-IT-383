"""Read-only replay/native-inference audit. Does not fit or change any model."""
from copy import deepcopy
from pathlib import Path
import json
import sys
import numpy as np
from xgboost import DMatrix
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from component4.expense_risk import generate,audit,FEATURES,TARGETS,project,make_estimate
from component4.expense_risk_inference import ExpenseRiskInference
from component4.planner_dashboard_api import PlannerDashboard
from component4.model_explanations import validate_additivity
from component4.release_input import sha256
from component4.risk_experiment import metrics


def readlines(path):return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]


def main():
    risk=ExpenseRiskInference()  # Verifies inventory, numerical source and model hashes.
    data=ROOT/'data/experiments/v3.0'/risk.run_id
    protocol=json.loads((risk.folder/'protocol.json').read_text())
    protected=protocol['protected_old_files']
    assert all(sha256(ROOT/k)==v for k,v in protected.items()),'historical_file_changed'
    rows=readlines(data/'planning_risk_dataset.jsonl');ledger=readlines(data/'financial_line_items.jsonl');prov=readlines(data/'provenance.jsonl')
    checks=audit(rows,ledger,prov)
    replay=generate(risk.design)
    assert replay==(rows,ledger,prov),'generation_replay_mismatch'
    assert readlines(data/'split_manifest.jsonl')==[{k:r[k] for k in ('Scenario_ID','Base_Event_ID','split','planning_state','outcome_replication')} for r in rows]
    by_id={r['Scenario_ID']:r for r in rows}
    # Independent projection of stored planning states using the serving calculator.
    api=PlannerDashboard();seen={}
    for p in prov:
        key=(p['Base_Event_ID'],by_id[p['Scenario_ID']]['planning_state'])
        if key not in seen:
            result=api.planner.request({'baseline':p['state'],'alternative':p['state']})['alternative']
            seen[key]=project(p['state'],result)
        assert all(by_id[p['Scenario_ID']][k]==v for k,v in seen[key].items()),'stored_features_not_from_planning_state'
    saved=readlines(risk.folder/'heldout_predictions.jsonl');shap_checks={}
    for target in TARGETS:
        model=risk.models[target]
        for split in ('validation','test'):
            part=[r for r in rows if r['split']==split]
            matrix=DMatrix(np.asarray([[r[f] for f in FEATURES] for r in part]))
            score=model.predict(matrix);actual=[p for p in saved if p['target']==target and p['split']==split]
            assert [p['Scenario_ID'] for p in actual]==[r['Scenario_ID'] for r in part]
            assert np.allclose(score,[p['uncalibrated_score'] for p in actual],atol=1e-8)
            assert [p['label'] for p in actual]==[r[target] for r in part]
            measured=metrics(np.asarray([r[target] for r in part]),score)
            for k,v in measured.items():assert np.isclose(v,risk.summary['metrics'][target][split]['xgboost'][k]),'metrics_mismatch'
            if split=='test':
                old=np.load(risk.folder/(target+'.test_shap.npz'),allow_pickle=False)
                phi=model.predict(matrix,pred_contribs=True,approx_contribs=False);margin=model.predict(matrix,output_margin=True)
                assert np.array_equal(old['scenario_ids'],[r['Scenario_ID'] for r in part])
                assert np.array_equal(old['features'],np.asarray([[r[f] for f in FEATURES] for r in part]))
                assert np.allclose(old['contributions'],phi,atol=1e-7)
                assert np.allclose(old['scores'],score) and np.allclose(old['margins'],margin)
                shap_checks[target]=validate_additivity(phi,margin,score,len(FEATURES))
    base=api.config()['default_state'];alt=deepcopy(base);alt['quotes']=[make_estimate('additional_service',500000,0)]
    example=api.calculate({'baseline':base,'alternative':alt})
    assert all(example[s]['model_trace']['prediction_executed'] for s in ('baseline','alternative'))
    removed=deepcopy(alt);removed['removed_quote_ids']=['assumed_0']
    removal=api.calculate({'baseline':alt,'alternative':removed})
    assert removal['alternative']['model_scores']==example['baseline']['model_scores']
    assert all(sha256(ROOT/k)==v for k,v in protected.items())
    result={'status':'PASS','run_id':risk.run_id,'audit':checks,'generation_replay':'PASS',
        'planning_state_projection_checks':len(seen),'native_reload_predictions_metrics':'PASS',
        'full_test_shap':shap_checks,'expense_add_remove_inference':'PASS',
        'historical_files_unchanged':len(protected),'example':example,
        'scope':'Internal synthetic simulator verification; not observed-event economic validation; no fitting or tuning'}
    path=risk.report/'independent_verification.json'
    path.write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='example'},indent=2))


if __name__=='__main__':main()
