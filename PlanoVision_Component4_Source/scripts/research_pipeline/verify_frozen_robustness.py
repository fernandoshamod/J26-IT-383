"""Replay the frozen stress audit without fitting or modifying existing artifacts."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import json
from unittest.mock import patch
from component4.planner_dashboard_api import PlannerDashboard
from component4.frozen_robustness import summarize
from component4.release_input import sha256
from scripts.model_experiments.run_frozen_robustness import evaluate


def read(path):return [json.loads(line) for line in path.read_text().splitlines()]


def main():
    folder=ROOT/'reports/robustness/v3_1_frozen_robustness_20261016'
    protocol=json.loads((folder/'protocol.json').read_text());p=protocol['design']
    for name,digest in protocol['source_hashes'].items():assert sha256(ROOT/name)==digest,'source_changed:'+name
    for name,digest in protocol['protected_files'].items():assert sha256(ROOT/name)==digest,'historical_file_changed:'+name
    for name,digest in json.loads((folder/'checksums.json').read_text()).items():assert sha256(folder/name)==digest,'report_changed:'+name
    api=PlannerDashboard()
    assert api.risk.metadata['model_sha256']==protocol['model_sha256']
    assert api.planner.service.config_hash==protocol['numeric_financial_config_sha256']
    base=next(r for r in p['outcome_regimes'] if r['id']=='original_uniform')
    assumptions=api.planner.service.config['assumptions']
    assert base['cost']==assumptions['ordinary_cost_multiplier'] and base['receipts']==assumptions['receipt_multiplier']
    with patch('xgboost.XGBClassifier.fit',side_effect=AssertionError('no_fitting_allowed')):
        records,entries,gates=evaluate(api,p)
    assert records==read(folder/'case_results.jsonl')
    assert entries==read(folder/'outcome_counts.jsonl')
    assert gates==json.loads((folder/'safety_checks.json').read_text())
    summary=json.loads((folder/'performance_summary.json').read_text())
    assert summarize(entries,p['outcome_draws_per_case_per_regime'])==summary['pooled']
    for field,values in summary['strata'].items():
        for key,result in values.items():assert summarize([e for e in entries if e[field]==key],p['outcome_draws_per_case_per_regime'])==result
    # No changed outcome distribution can feed back into any predictor.
    predictions={}
    for e in entries:predictions.setdefault((e['test_case_id'],e['target']),set()).add((e['xgb_score'],e['mc_score'],e['rule_class']))
    assert all(len(v)==1 for v in predictions.values())
    assert all(sha256(ROOT/k)==v for k,v in protocol['protected_files'].items())
    result={'status':'PASS_REPLAY_AND_INTEGRITY_ONLY','planning_cases_replayed':len(records),
        'aggregate_outcome_records_replayed':len(entries),'safety_checks_replayed':len(gates),
        'native_scored_cases':sum(r['model_executed'] for r in records),
        'withheld_cases':sum(not r['model_executed'] for r in records),
        'model_or_monte_carlo_prediction_informed_by_stress_outcomes':False,
        'model_fitting':False,'protected_files_unchanged':len(protocol['protected_files']),
        'economic_or_real_world_validation':False}
    (folder/'independent_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
