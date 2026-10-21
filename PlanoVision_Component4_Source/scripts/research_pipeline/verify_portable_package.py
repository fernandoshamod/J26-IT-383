"""Portable-project integrity and native inference smoke test; no fitting."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import argparse
from copy import deepcopy
import hashlib
import json
import threading
from urllib.request import Request,urlopen
from unittest.mock import patch


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--http',action='store_true');args=parser.parse_args()
    manifest=json.loads((ROOT/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    for name,value in manifest['files'].items():
        path=(ROOT/name).resolve()
        if not path.is_relative_to(ROOT) or digest(path)!=value['sha256']:raise ValueError('package_file_changed_or_missing:'+name)
    import component4
    assert Path(component4.__file__).resolve().is_relative_to(ROOT),'wrong_checkout_imported'
    from component4.planner_dashboard_api import PlannerDashboard
    from component4.expense_risk import make_estimate
    from component4.dashboard_evidence import evidence_summary, FILES, verified_bytes
    assert evidence_summary()['model_run']=='expense_risk_v3_1_20261016'
    for key in FILES:verified_bytes(key)
    final=manifest.get('version') in ('3.3-pp1-final-20261020','3.4-backend-crud-20261020','3.5-vscode-dev-20261020','3.6-crud-connected-20261020','3.7-data-quality-20261021','3.8-ui-refresh-20261021','3.9-pp1-submission-20261021')
    if manifest.get('version') in ('3.7-data-quality-20261021','3.8-ui-refresh-20261021','3.9-pp1-submission-20261021'):
        from component4.future_price_forecast import preview as future_preview
        q=future_preview(dict(series_id='S003:Anamalu:1 Kg.',target_month='2026-11-01',unit='LKR/1 Kg.',quantity=10,expense_scope='ingredient_component'))
        assert q['status']=='available_experimental_forecast' and q['training_quality_flag_count']==8
        assert q['quality_review']['model_value_unresolved_count']==0 and q['quality_review']['original_flags_preserved']
        assert q['ingredient_subtotal_lkr']==3659.58 and not q['applied_to_event_budget']
    ai=manifest.get('version')=='3.2-lkrgraph-localai-20261019' or final
    bridge=manifest.get('version')=='3.1-component2bridge-20261018' or ai
    if bridge:
        from component4.forecast_bridge import catalog,preview
        from component4.component2_adapter import import_bundle
        assert len(catalog()['series'])==12
        assert preview(dict(series_id='S003:Anamalu:1 Kg.',target_month='2026-10-01',unit='LKR/1 Kg.',quantity=10,expense_scope='ingredient_component'))['status']=='blocked'
    with patch('xgboost.XGBClassifier.fit',side_effect=AssertionError('no_model_fitting')):
        api=PlannerDashboard();base=api.config()['default_state'];alt=deepcopy(base)
        if final:
            extended=PlannerDashboard(extended_calculator_scope=True)
            small=deepcopy(base);small.update(guests=10,venue_width_m=10,venue_length_m=12,target_budget_lkr=100000,retained_receipts_lkr=150000)
            checked=extended.calculate({'baseline':small,'alternative':small})['alternative']
            assert checked['status']=='calculated'
            assert not checked['model_trace']['prediction_executed']
        if bridge:
            example=json.loads((ROOT/'fixtures/component2_quotation_bundle.mock_test_only.json').read_text(encoding='utf-8'))
            proposed=import_bundle(example,base)['proposed_state']
            assert api.calculate({'baseline':base,'alternative':proposed})['delta']['cost_lkr']==14278
        alt['quotes']=[make_estimate('portable_demo_expense',500000,0)]
        r=api.calculate({'baseline':base,'alternative':alt})
        if ai:
            from component4.future_price_forecast import catalog as future_catalog
            assert len(future_catalog()['series'])==12
            assert r['alternative']['graph_risk']['prediction_executed']
            assert r['alternative']['graph_risk']['monetary_input_unit']=='LKR'
            from component4.local_llm_runtime import verified_executable
            assert verified_executable().is_file()
        assert api.risk.run_id=='expense_risk_v3_1_20261016'
        assert r['alternative']['model_trace']['prediction_executed']
        assert abs(r['delta']['cost_lkr']-500000)<.011
        assert abs(r['baseline']['plan']['total_cost_lkr']-1570450.2)<.011
        assert abs(r['alternative']['model_scores']['Budget_Overrun']['uncalibrated_score']-.693387568)<1e-5
        assert r['alternative']['model_trace']['shap_additivity_verified']
        assert 'MODEL EVALUATION' in r['report_text']
        removed=deepcopy(alt);removed['removed_quote_ids']=['assumed_0']
        restored=api.calculate({'baseline':alt,'alternative':removed})
        assert restored['alternative']['model_scores']==r['baseline']['model_scores']
        invalid=deepcopy(base);invalid['guests']=300
        assert api.calculate({'baseline':base,'alternative':invalid})['alternative']['plan'] is None
        http_result='not_requested'
        if args.http:
            from component4.planner_dashboard_http import create_server
            server=create_server(0,dashboard=api);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                url=f'http://127.0.0.1:{server.server_port}'
                with urlopen(url,timeout=10) as response:assert response.status==200 and b'<div id="root">' in response.read()
                with urlopen(url+'/api/planner/config',timeout=10) as response:assert json.load(response)['model_run']==api.risk.run_id
                with urlopen(url+'/api/planner/model-evidence',timeout=10) as response:assert json.load(response)['version']=='v3.1-frozen-diagnostics'
                with urlopen(url+'/api/planner/evidence-image/learning-curves.png',timeout=10) as response:assert response.read().startswith(b'\x89PNG')
                if bridge:
                    with urlopen(url+'/api/planner/forecast-catalog',timeout=10) as response:assert len(json.load(response)['series'])==12
                request=Request(url+'/api/planner/compare',data=json.dumps({'baseline':base,'alternative':alt}).encode(),headers={'Content-Type':'application/json'})
                with urlopen(request,timeout=20) as response:assert json.load(response)['alternative']['model_trace']['prediction_executed']
                http_result='PASS'
            finally:server.shutdown();server.server_close();thread.join(timeout=5)
    print(json.dumps({'status':'PASS','root':str(ROOT),'manifest_files_verified':len(manifest['files']),
        'model_run':api.risk.run_id,'native_inference_and_TreeSHAP':'PASS','expense_add_remove':'PASS',
        'capacity_block':'PASS','http_backend_and_built_frontend':http_result,'fitting':False},indent=2))


if __name__=='__main__':main()
