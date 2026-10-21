"""End-to-end fixed demo acceptance; never fits models or changes dataset contents."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from copy import deepcopy
import hashlib
import json
import threading
from urllib.request import Request,urlopen
from unittest.mock import patch
from component4.planner_dashboard_api import PlannerDashboard
from component4.planner_dashboard_http import create_server
from component4.expense_risk import make_estimate


def main():
    archive=ROOT/'outputs/Component4_Hybrid_Dataset_Final_v1.0.zip'
    digest=lambda:hashlib.sha256(archive.read_bytes()).hexdigest() if archive.exists() else None
    before=digest();api=PlannerDashboard();base=api.config()['default_state']
    server=create_server(0,dashboard=api);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    rows=[]
    def calculate(state):
        request=Request(f'http://127.0.0.1:{server.server_port}/api/planner/compare',
                        data=json.dumps({'baseline':base,'alternative':state}).encode(),headers={'Content-Type':'application/json'})
        with urlopen(request,timeout=20) as response:return json.load(response)
    try:
        with patch('xgboost.XGBClassifier.fit',side_effect=AssertionError('no_training_permitted')):
            for name,amount in [('good',0),('warning',500000),('bad',800000),('loss_guard',1200000)]:
                state=deepcopy(base)
                if amount:state['quotes']=[make_estimate('Diagnostic service',amount,0)]
                r=calculate(state);p=r['alternative']['plan'];s=r['insights']['score']['value']
                assert abs(r['delta']['cost_lkr']-amount)<.011
                assert abs(sum(p['line_items_lkr'].values())-p['total_cost_lkr'])<.011
                assert abs(p['expected_profit_lkr']-(state['retained_receipts_lkr']-p['total_cost_lkr']))<.011
                assert r['baseline']['plan']['total_cost_lkr']==1570450.2,'preview_changed_main_plan'
                assert 'LKR' in r['report_text'] and 'RECOMMENDATIONS' in r['report_text']
                executed=r['alternative']['model_trace']['prediction_executed']
                if name!='loss_guard':
                    assert executed and r['alternative']['model_trace']['shap_additivity_verified']
                    assert r['alternative']['monte_carlo'] is not None
                else:assert p['expected_profit_lkr']<0 and s==0 and not executed
                assert (name!='good' or s==100) and (name!='warning' or 80<s<100) and (name!='bad' or 0<s<50)
                rows.append({'case':name,'added_expense_lkr':amount,'cost_lkr':p['total_cost_lkr'],
                             'profit_lkr':p['expected_profit_lkr'],'margin_pct':p['expected_margin_pct'],
                             'health_score_rule_based':s,'native_prediction_executed':executed,
                             'model_scores':r['alternative']['model_scores'],
                             'support_reasons':r['alternative']['model_trace']['support_reasons']})
                if amount:
                    removed=deepcopy(state);removed['removed_quote_ids']=[state['quotes'][0]['id']]
                    assert calculate(removed)['alternative']['plan']['total_cost_lkr']==1570450.2
            invalid=deepcopy(base);invalid['guests']=300
            blocked=calculate(invalid)
            assert blocked['alternative']['status']=='blocked' and blocked['alternative']['plan'] is None
            assert blocked['insights']['score'] is None
            from component4.dashboard_evidence import evidence_summary,FILES,verified_bytes
            evidence_summary()
            for key in FILES:verified_bytes(key)
    finally:server.shutdown();server.server_close();thread.join()
    assert digest()==before
    result={'status':'PASS','model_run':api.risk.run_id,'cases':rows,
            'expense_removal':'PASS','preview_baseline_isolation':'PASS','capacity_rejection':'PASS',
            'frozen_report_checksums':'PASS','native_shap_and_monte_carlo_for_supported_cases':'PASS',
            'dataset_archive_unchanged':True,'dataset_archive_sha256':before,
            'no_training':True,'limitation':'Synthetic research only; health is rule-based; no real-world financial accuracy guarantee.'}
    # Runtime rechecks must not overwrite the packaged reference receipt.
    report=ROOT/'work/final_demo_acceptance_20261016.json';report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
