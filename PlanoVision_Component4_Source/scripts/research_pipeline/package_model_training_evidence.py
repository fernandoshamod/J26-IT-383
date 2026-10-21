"""Verify saved native classifiers and package their existing training evidence. No fit."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import hashlib
import json
import zipfile
import numpy as np
from xgboost import DMatrix
from unittest.mock import patch
from component4.enhanced_risk_inference import EnhancedRiskInference
from component4.risk_enhancement import matrix


def main():
    destination=ROOT/'outputs/PlanoVision_Model_Training_Evidence_20261017.zip'
    if destination.exists():raise ValueError('refuse_existing_training_evidence_zip')
    folder='outputs/experiments/v3.1/expense_risk_v3_1_20261016/'
    reports='reports/experiments/v3.1/expense_risk_v3_1_20261016/'
    data='data/experiments/v3.0/expense_risk_v3_0_20261015/planning_risk_dataset.jsonl'
    rows=[json.loads(line) for line in (ROOT/data).read_text().splitlines()]
    heldout=[json.loads(line) for line in (ROOT/(folder+'heldout_predictions.jsonl')).read_text().splitlines()]
    result={'status':'PASS','verified_local_date':'2026-10-17','run_id':'expense_risk_v3_1_20261016',
            'fitting_performed':False,'test_scope':'previously inspected synthetic test; not real-event validation',
            'real_observed_event_outcomes':0,'models':{}}
    with patch('xgboost.XGBClassifier.fit',side_effect=AssertionError('no_fitting')):
        risk=EnhancedRiskInference()
        for target,model in risk.models.items():
            path=ROOT/(folder+target+'.xgboost.json')
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            assert digest==risk.metadata['model_sha256'][target]
            features=risk.metadata['model_features'][target]
            test=[row for row in rows if row['split']=='test']
            saved=[row for row in heldout if row['split']=='test' and row['target']==target]
            x=DMatrix(matrix(test,features));prediction=model.predict(x)
            assert [r['Scenario_ID'] for r in test]==[r['Scenario_ID'] for r in saved]
            assert np.allclose(prediction,[r['score'] for r in saved],atol=1e-8,rtol=0)
            y=np.array([r[target] for r in test]);accuracy=float(((prediction>=.5)==y).mean())
            stored=risk.summary['metrics'][target]['test']['xgboost']
            assert abs(accuracy-stored['accuracy'])<1e-12
            contributions=model.predict(x,pred_contribs=True,approx_contribs=False)
            margins=model.predict(x,output_margin=True)
            error=float(np.max(np.abs(contributions.sum(axis=1)-margins)))
            assert error<1e-4
            result['models'][target]={'sha256':digest,'boosting_rounds':model.num_boosted_rounds(),
                'native_features':features,'test_rows':len(test),'test_root_families':len({r['Base_Event_ID'] for r in test}),
                'replayed_test_accuracy':accuracy,'saved_prediction_replay':'PASS',
                'native_TreeSHAP_additivity_max_error_log_odds':error,'stored_test_metrics':stored}
    receipt='reports/model_training_evidence_verified_20261017.json'
    (ROOT/receipt).write_text(json.dumps(result,indent=2),encoding='utf-8')
    files=[receipt,data,'config/risk_enhancement.v3.1.json','scripts/model_experiments/enhance_expense_risk.py',
        'scripts/research_pipeline/verify_risk_enhancement.py','scripts/research_pipeline/package_model_training_evidence.py',
        'component4/risk_enhancement.py',
        'reports/diagnostics/v3_1_steps1_2_20261016/learning_curves.png',
        'reports/diagnostics/v3_1_steps1_2_20261016/learning_curve_report.md',
        'reports/diagnostics/v3_1_steps1_2_20261016/error_audit.md',
        'reports/robustness/v3_1_frozen_robustness_20261016/robustness_report.md']
    files += [p.relative_to(ROOT).as_posix() for p in (ROOT/folder).iterdir() if p.is_file()]
    files += [p.relative_to(ROOT).as_posix() for p in (ROOT/reports).iterdir() if p.is_file()]
    payload={name:(ROOT/name).read_bytes() for name in files}
    manifest={name:hashlib.sha256(content).hexdigest() for name,content in payload.items()}
    payload['EVIDENCE_CHECKSUMS.json']=json.dumps(manifest,indent=2).encode()
    payload['READ_FIRST.md']=b'''# Saved-model training evidence

This pack contains actual native trained XGBoost files, metadata, frozen protocol,
candidate selection records, grouped out-of-fold and held-out predictions, original
LKR synthetic experiment data, full test TreeSHAP arrays, learning curves and reports.

Start with reports/model_training_evidence_verified_20261017.json. The packaging
check loaded the saved native boosters, verified their hashes, replayed all 720
test predictions for each target and checked native TreeSHAP additivity. It did
not train or tune anything. Each saved model has 300 boosting rounds.

Model metrics describe synthetic outcomes, not independently observed events.
The test had previously been inspected; it is not a new untouched holdout.
Planning-rule baselines remain competitive. Read the adverse-shock limitations.

This evidence pack is not a standalone runtime. Use the existing Complete_Ready
project ZIP for the dashboard and complete runtime dependencies. Do not run the
training script just to demonstrate inference; use the saved models.
'''
    with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,content in payload.items():archive.writestr('PlanoVision_Training_Evidence/'+name,content)
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        for name,content in payload.items():assert archive.read('PlanoVision_Training_Evidence/'+name)==content
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in manifest.items())
    digest=hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix('.zip.sha256').write_text(digest+'  '+destination.name+'\n',encoding='ascii')
    print(json.dumps({'archive':str(destination),'sha256':digest,'verified':result},indent=2))


if __name__=='__main__':main()
