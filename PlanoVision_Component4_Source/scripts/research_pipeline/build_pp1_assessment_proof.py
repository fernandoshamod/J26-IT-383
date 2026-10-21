"""Record current financial workflow and SQLite checks in isolated temporary storage."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from copy import deepcopy
from datetime import datetime,timezone
import json
import tempfile
from component4.planner_dashboard_api import PlannerDashboard
from component4.expense_risk import make_estimate
from component4.planner_records import PlannerRecords


def main():
    out=ROOT/'reports/PP1_ASSESSMENT_FIXED_20261021'
    out.mkdir(exist_ok=True)
    path=out/'CURRENT_WORKFLOW_PROOF.json'
    if path.exists(): raise ValueError('proof_already_exists')
    api=PlannerDashboard(extended_calculator_scope=True)
    base=deepcopy(api.config()['default_state'])
    before=deepcopy(base)
    alt=deepcopy(base)
    alt['quotes']=[make_estimate('TEST ONLY optional client request',100000,0)]
    response=api.calculate({'baseline':base,'alternative':alt})
    assert base==before
    original=response['baseline']['plan']
    alternative=response['alternative']['plan']
    assert original and alternative
    assert abs(response['delta']['cost_lkr']-100000)<.011
    assert abs(alternative['expected_profit_lkr']-original['expected_profit_lkr']+100000)<.011
    removed=deepcopy(alt)
    removed['removed_quote_ids']=['assumed_0']
    removal=api.calculate({'baseline':alt,'alternative':removed})
    assert abs(removal['alternative']['plan']['total_cost_lkr']-original['total_cost_lkr'])<.011
    assert response['alternative']['model_trace']['prediction_executed']
    assert response['alternative']['model_trace']['shap_additivity_verified']
    # Separate isolated database. No personal runtime database is opened.
    with tempfile.TemporaryDirectory(prefix='pp1_assessment_',dir=ROOT/'work') as tmp:
        db=Path(tmp)/'test_only.sqlite3'
        store=PlannerRecords(db)
        payload=dict(name='TEST ONLY PP1 evidence',client_name='TEST ONLY',plan=base)
        created=store.write('event',payload)
        identifier=created['saved_id']
        reopened=PlannerRecords(db).listing('event')
        assert reopened['records'][0]['plan']==base
        # Preview calculation has no database write.
        api.calculate({'baseline':base,'alternative':alt})
        no_write=store.listing('event')
        assert no_write['revisions'][identifier]==1
        assert no_write['records'][0]['plan']==base
        confirmed={**payload,'plan':alt}
        updated=store.write('event',confirmed,identifier,1)
        assert updated['revisions'][identifier]==2
        assert updated['records'][0]['plan']==alt
        deleted=store.write('event',None,identifier,2,delete=True)
        assert deleted['records']==[]
    selected=['total_cost_lkr','expected_profit_lkr','expected_margin_pct','reserve_lkr']
    proof=dict(status='PASS_CURRENT_WORKFLOW_AND_ISOLATED_SQLITE',checked_utc=datetime.now(timezone.utc).isoformat(),
        context='Hypothetical reference-priced demonstration. No real event, customer benefit measurement or actual savings claim.',
        inputs={'client_payment_lkr':base['retained_receipts_lkr'],'spending_limit_lkr':base['target_budget_lkr'],'optional_addition_lkr':100000},
        baseline={k:original[k] for k in selected},preview={k:alternative[k] for k in selected},
        preview_cost_increase_lkr=response['delta']['cost_lkr'],
        margin_change_percentage_points=alternative['expected_margin_pct']-original['expected_margin_pct'],
        removal_restores_original_cost=True,original_input_unchanged=True,
        native_model_prediction_executed=True,native_TreeSHAP_additivity_verified=True,
        sqlite={'create':'PASS','reopen_and_read':'PASS','preview_does_not_write':'PASS','explicit_update':'PASS','soft_delete':'PASS','personal_database_opened':False},
        evaluation_scope='Current calculation/model wiring plus repository persistence. Browser and HTTP checks are separately recorded.',
        model_refit=False)
    path.write_text(json.dumps(proof,indent=2),encoding='utf-8')
    print(json.dumps(proof,indent=2))


if __name__=='__main__': main()
