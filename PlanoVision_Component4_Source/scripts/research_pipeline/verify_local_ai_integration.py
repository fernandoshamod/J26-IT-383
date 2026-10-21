"""Opt-in actual local LLM + saved GAT checks, separate from mocked unit tests."""
from copy import deepcopy
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from component4.planner_dashboard_api import PlannerDashboard
from component4.local_llm_report import generate,status
from component4.expense_risk import make_estimate
from component4.release_input import sha256


def main():
    output=ROOT/'reports/lkr_graph_local_ai_20261018';output.mkdir(parents=True,exist_ok=True)
    if (output/'actual_runtime_verification.json').exists():raise ValueError('refuse_overwriting_real_runtime_receipt')
    current=status()
    if not current['ready']:raise ValueError('real_local_model_is_required_no_mock_fallback')
    api=PlannerDashboard();base=api.config()['default_state'];cases=[]
    protected=[ROOT/'data/experiments/v3.0/expense_risk_v3_0_20261015/planning_risk_dataset.jsonl',
               ROOT/'outputs/Component4_Hybrid_Dataset_Final_v1.0.zip',ROOT/'dataset_releases/v1.0/Component4_Hybrid_Dataset_Final_v1.0.zip']
    before={p.relative_to(ROOT).as_posix():sha256(p) for p in protected}
    for label,extra in [('good',0),('bad',800000),('loss',1200000)]:
        alt=deepcopy(base)
        if extra:alt['quotes']=[make_estimate('AI diagnostic allowance',extra,0)]
        response=api.calculate({'baseline':base,'alternative':alt});old=json.dumps(response,sort_keys=True)
        draft=generate(response)
        if json.dumps(response,sort_keys=True)!=old:raise ValueError('llm_mutated_financial_results')
        record={'case':label,'extra_assumed_lkr':extra,'cost_lkr':response['alternative']['plan']['total_cost_lkr'],
                'profit_lkr':response['alternative']['plan']['expected_profit_lkr'],'health':response['insights']['score']['value'],
                'graph_status':response['alternative']['graph_risk']['status'],'llm_report':draft}
        (output/(label+'_local_llm_report.json')).write_text(json.dumps(record,indent=2),encoding='utf-8')
        cases.append({'case':label,'health':record['health'],'graph_status':record['graph_status'],'llm_status':draft['status'],
                      'model_digest':draft['model_digest'],'engine_facts_sha256':draft['engine_facts_sha256']})
        print('Actual local model verified:',label,'health',record['health'],draft['status'],flush=True)
    if any(sha256(ROOT/name)!=digest for name,digest in before.items()):raise ValueError('original_data_changed')
    receipt={'status':'PASS_ACTUAL_LOCAL_RUNTIME_INTEGRATION','verified_at_utc':datetime.now(timezone.utc).isoformat(),
             'provider':'ollama_local','model':current['model'],'model_digest':current['model_digest'],
             'cases':cases,'protected_inputs_unchanged':before,'financial_outputs_unchanged_by_llm':True,
             'llm_semantic_accuracy_independently_verified':False,'real_world_model_validation':False}
    (output/'actual_runtime_verification.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(receipt,indent=2),flush=True)


if __name__=='__main__':main()
