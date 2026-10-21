"""Read-only replay/ledger/feature/model/SHAP validation of the monetary run."""
import argparse
import csv
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import numpy as np
from xgboost import Booster,DMatrix
from component4.lkr_research import generate,validate_dataset,FEATURES,TARGETS,VERSION,calculate,features
from component4.release_input import sha256
from component4.engine import fingerprint
from component4.model_explanations import validate_additivity
from component4.risk_experiment import metrics


def read_csv(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def verify(run_id):
    if not run_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in run_id):raise ValueError('invalid_run_id')
    data=ROOT/'data/experiments/v2.0'/run_id;output=ROOT/'outputs/experiments/v2.0'/run_id;report=ROOT/'reports/experiments/v2.0'/run_id
    for name,digest in json.loads((report/'checksums.json').read_text()).items():
        path=(ROOT/name).resolve()
        if not path.is_relative_to(ROOT) or sha256(path)!=digest:raise ValueError('output_checksum:'+name)
    protocol=json.loads((output/'protocol.json').read_text());config=protocol['configuration']
    for name,digest in {**protocol['source_checksums'],**protocol['old_input_checksums']}.items():
        if sha256(ROOT/name)!=digest:raise ValueError('source_or_historical_file_changed:'+name)
    if fingerprint(config)!=protocol['configuration_sha256']:raise ValueError('configuration_hash_changed')
    evidence=json.loads((ROOT/config['source_file']).read_text())
    expected,ledger,provenance=generate(config,evidence);audit=validate_dataset(expected,ledger,provenance)
    pairs=[('lkr_synthetic_master.csv',expected),('lkr_financial_line_items.csv',ledger),('lkr_scenario_provenance.csv',provenance)]
    for name,records in pairs:
        saved=read_csv(data/name)
        if len(saved)!=len(records):raise ValueError('record_count_mismatch:'+name)
        for a,b in zip(saved,records):
            if a!={k:str(v) for k,v in b.items()}:raise ValueError('exact_generation_replay_failed:'+name)
    risk=read_csv(data/'lkr_risk_dataset.csv')
    allowed={'Scenario_ID','Base_Event_ID','split_group_id','split',*FEATURES,*TARGETS}
    if set(risk[0])!=allowed:raise ValueError('risk_feature_leakage')
    master={r['Scenario_ID']:r for r in expected}
    for row in risk:
        if row!={k:str(master[row['Scenario_ID']][k]) for k in row}:raise ValueError('risk_table_mismatch')
    saved_splits=read_csv(data/'split_manifest.csv')
    if saved_splits!=[{k:str(r[k]) for k in ('Scenario_ID','Base_Event_ID','split_group_id','split')} for r in expected]:raise ValueError('split_manifest_mismatch')
    by_provenance={p['Scenario_ID']:p for p in provenance}
    for row in expected:
        inputs=json.loads(by_provenance[row['Scenario_ID']]['planning_inputs_json'])
        projected=features(inputs,calculate(config,evidence,inputs))
        if any(projected[k]!=row[k] for k in FEATURES):raise ValueError('feature_reprojection_mismatch')
    predictions=read_csv(output/'heldout_predictions.csv')
    index={(r['Scenario_ID'],r['target']):r for r in predictions}
    expected_keys={(r['Scenario_ID'],t) for r in expected if r['split'] in ('validation','test') for t in TARGETS}
    if len(index)!=len(predictions) or set(index)!=expected_keys:raise ValueError('prediction_id_scope_mismatch')
    summary=json.loads((report/'experiment_summary.json').read_text())
    for target in TARGETS:
        model=Booster();model.load_model(bytearray((output/(target+'.xgboost.json')).read_bytes()))
        for split in ('validation','test'):
            subset=[r for r in expected if r['split']==split]
            matrix=DMatrix(np.asarray([[r[f] for f in FEATURES] for r in subset],dtype=float))
            scores=model.predict(matrix)
            labels=np.asarray([r[target] for r in subset])
            recomputed=metrics(labels,scores)
            recorded=summary['metrics'][target][split]['xgboost']
            if any((v is None)!=(recorded[k] is None) or (v is not None and abs(v-recorded[k])>1e-7) for k,v in recomputed.items()):
                raise ValueError('reported_metrics_mismatch')
            for row,score in zip(subset,scores):
                saved=index[(row['Scenario_ID'],target)]
                if saved['split']!=split or int(saved['true_label'])!=row[target] or int(saved['predicted_label'])!=int(score>=.5):raise ValueError('prediction_label_mismatch')
                if abs(float(saved['uncalibrated_score'])-float(score))>1e-7:raise ValueError('saved_prediction_replay_failed')
        with np.load(output/(target+'.test_shap.npz'),allow_pickle=False) as explanation:
            ids=[r['Scenario_ID'] for r in expected if r['split']=='test']
            x=np.asarray([[r[f] for f in FEATURES] for r in expected if r['split']=='test'])
            if explanation['scenario_ids'].tolist()!=ids or not np.array_equal(explanation['features'],x):raise ValueError('shap_inputs_or_ids_mismatch')
            validate_additivity(explanation['contributions'],explanation['margins'],explanation['scores'],len(FEATURES))
            if not np.allclose(model.predict(DMatrix(x)),explanation['scores'],atol=1e-7):raise ValueError('shap_score_replay_failed')
    if summary['dataset']!=audit:raise ValueError('summary_audit_mismatch')
    return {'status':'PASS','dataset':audit,'generation_and_feature_replay':'PASS','ledger_and_labels':'PASS',
            'model_and_shap_replay':'PASS','source_and_old_outputs_unchanged':True,'prediction_time_leakage':'PASS',
            'shared_source_template_limitation':'Conditional in-simulator groups; not unseen-source/venue generalization',
            'real_world_prediction_validated':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run-id',default=VERSION);args=parser.parse_args()
    result=verify(args.run_id)
    target=ROOT/'reports/experiments/v2.0'/args.run_id/'verification.json'
    target.write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
