"""Save reproducible service-change demo evidence; no fitting or dataset writes."""
from copy import deepcopy
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from component4.planner_services import PlannerServices,report_text
from component4.release_input import sha256


def main():
    folder=ROOT/'reports/planner_services_20261015'
    if folder.exists():raise ValueError('refuse_existing_verification_folder')
    protected={}
    for manifest in ('reports/experiments/v2.0/lkr_research_v2_0_20261014/completion_checksums.json',
                     'reports/pp1_readiness_20261015/package_manifest.json'):
        protected.update(json.loads((ROOT/manifest).read_text())['files'])
        protected[manifest]=sha256(ROOT/manifest)
    for name,digest in protected.items():
        if sha256(ROOT/name)!=digest:raise ValueError('protected_input_changed:'+name)
    planner=PlannerServices();fixture=json.loads((ROOT/'fixtures/planner_services.mock_test_only.json').read_text())
    requests={'add':fixture}
    remove=deepcopy(fixture);remove['baseline']=deepcopy(remove['alternative']);remove['alternative']['removed_quote_ids']=['photo_demo']
    requests['remove']=remove
    missing=deepcopy(fixture);missing['alternative']['quotes'][0]['unit_rate_lkr']=None;requests['missing_quote']=missing
    results={name:planner.request(p) for name,p in requests.items()}
    if results['add']['delta']['cost_lkr']!=60000 or results['remove']['delta']['cost_lkr']!=-60000:
        raise ValueError('service_delta_mismatch')
    if results['missing_quote']['alternative']['status']!='quotation_required' or results['missing_quote']['delta'] is not None:
        raise ValueError('missing_price_filled')
    if any(planner.request(p)!=results[name] for name,p in requests.items()):raise ValueError('replay_failure')
    receipt=json.loads((ROOT/'reports/public_hotel_benchmark_test_results.json').read_text())
    if receipt['full_suite_status']!='PASS' or not receipt['release_zip_files_unchanged']:
        raise ValueError('full_suite_failed')
    for name,digest in protected.items():
        if sha256(ROOT/name)!=digest:raise ValueError('frozen_artifact_modified')
    folder.mkdir()
    for name,r in results.items():
        (folder/(name+'.json')).write_text(json.dumps(r,indent=2,allow_nan=False))
        (folder/(name+'.txt')).write_text(report_text(r),encoding='utf-8')
    (folder/'full_suite_receipt.json').write_text(json.dumps(receipt,indent=2))
    verification={'status':'PASS','add_cost_delta_lkr':60000,'remove_cost_delta_lkr':-60000,
                  'source_kind':'mock_test_only','replay':'PASS','missing_price_blocking':'PASS',
                  'protected_files_unchanged':len(protected),'full_suite_tests':receipt['tests_run'],
                  'models_retrained':False,'training_dataset_generated':False,
                  'functional_changes':['optional_service_add_remove','wedding_core_quote_replacement',
                     'declared_tax_scope','event_date_quote_validity','documented_escalation_and_price_locks',
                     'cancellation_costs','computed_readable_reports'],
                  'still_pending':['automatic_live_price_fetch','calibrated_price_forecast','new_rule_regime_risk_training',
                     'independent_health_validation','team_component_API_frontend']}
    (folder/'verification.json').write_text(json.dumps(verification,indent=2))
    files=list(folder.iterdir())+[ROOT/name for name in ('component4/planner_services.py',
         'scripts/research_pipeline/run_service_planner.py','scripts/research_pipeline/verify_planner_services.py',
         'fixtures/planner_services.mock_test_only.json','tests/test_planner_services.py','Run_Service_Planner.cmd','README_SERVICE_PLANNER.md')]
    (folder/'checksums.json').write_text(json.dumps({p.relative_to(ROOT).as_posix():sha256(p) for p in files},indent=2))
    print(json.dumps(verification,indent=2))


if __name__=='__main__':main()
