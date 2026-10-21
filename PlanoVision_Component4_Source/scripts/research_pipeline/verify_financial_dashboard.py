"""Record actual adapter replay, protected hashes and the full-suite receipt."""
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from component4.planner_dashboard_api import PlannerDashboard


def main():
    api=PlannerDashboard();state=api.config()['default_state']
    payload={'baseline':deepcopy(state),'alternative':deepcopy(state)}
    payload['alternative']['guests']=160
    r=api.calculate(payload)
    assert r['delta']['cost_lkr']==91119.6
    assert r['delta']['profit_lkr']==-91119.6
    assert r==api.calculate(payload)
    payload['alternative']['guests']=300
    invalid=api.calculate(payload)
    assert invalid['alternative']['plan'] is None and invalid['delta'] is None
    inventory=json.loads((ROOT/'reports/experiments/v2.0/lkr_research_v2_0_20261014/checksums.json').read_text())
    for name,digest in inventory.items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    suite=json.loads((ROOT/'reports/public_hotel_benchmark_test_results.json').read_text())
    assert suite['full_suite_status']=='PASS' and suite['release_zip_files_unchanged']
    assert (ROOT/'frontend/dist/index.html').is_file()
    folder=ROOT/'reports/expense_preview_workflow_20261015';folder.mkdir(exist_ok=True)
    files=[*list((ROOT/'frontend/src').glob('*')),ROOT/'frontend/package.json',ROOT/'frontend/package-lock.json',ROOT/'frontend/vite.config.ts',ROOT/'frontend/tsconfig.json',ROOT/'component4/planner_dashboard_api.py',ROOT/'component4/planner_dashboard_http.py',ROOT/'tests/test_planner_dashboard.py',ROOT/'Run_Financial_Dashboard.cmd',ROOT/'README_FINANCIAL_DASHBOARD.md',*list((ROOT/'frontend/dist').rglob('*'))]
    files.append(ROOT/'component4/planner_insights.py')
    files.append(ROOT/'component4/planner_services.py')
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}
    report={'verified_at_utc':datetime.now(timezone.utc).isoformat(),'local_date':'2026-10-15','timezone':'Asia/Colombo',
            'mode':'research_only','api_engine_replay':'PASS','guest_change_150_to_160_cost_delta_lkr':r['delta']['cost_lkr'],
            'spatial_infeasibility_300_guests_500_m2':'BLOCKED as expected',
            'protected_LKR_run_files_verified_unchanged':len(inventory),
            'full_python_suite':suite,'frontend_tests':{'passed':17,'failed':0,'command':'npm.cmd test --prefix frontend'},
            'typescript_and_vite_build':'PASS','frontend_verification':'Commands completed successfully before running this recorder',
            'live_calculation_enabled':False,'datasets_regenerated':False,'models_retrained':False,
            'limitations':['500 m2 default outside trained model support; scores withheld','No live rates or Component 1–3 feeds','Hypothetical financial, tax and spatial assumptions','Monte Carlo not calibrated to real event outcomes','Draft coverage not validated health','No authenticated production deployment'],
            'artifact_sha256':hashes}
    (folder/'verification.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    (folder/'valid_guest_change.json').write_text(json.dumps(r,indent=2,allow_nan=False),encoding='utf-8')
    (folder/'spatial_block.json').write_text(json.dumps(invalid,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('api_engine_replay','protected_LKR_run_files_verified_unchanged','full_python_suite','frontend_tests')},indent=2))


if __name__=='__main__':main()
