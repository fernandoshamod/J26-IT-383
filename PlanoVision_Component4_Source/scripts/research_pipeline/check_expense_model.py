"""Run actual trained-model inference before/after an expense addition."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from copy import deepcopy
from component4.planner_dashboard_api import PlannerDashboard
from component4.expense_risk import make_estimate


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--amount',type=float,default=500000);args=parser.parse_args()
    api=PlannerDashboard();base=api.config()['default_state'];alt=deepcopy(base)
    alt['quotes']=[make_estimate('additional_service',args.amount,0)]
    r=api.calculate({'baseline':base,'alternative':alt})
    for name in ('baseline','alternative'):
        x=r[name];print('\n'+name.upper(),x['status'])
        if x['plan']:print('Planning cost LKR',x['plan']['total_cost_lkr'])
        print('Actual saved model run:',x['model_trace']['run_id'])
        print('Native prediction executed:',x['model_trace']['prediction_executed'])
        print('Scores:',json.dumps(x['model_scores']))
        print('Support:',x['model_trace']['support_reasons'])
        for target,drivers in x['shap_drivers'].items():
            if drivers:print(target,'TreeSHAP log-odds:',[(d['feature'],round(d['contribution_log_odds'],4)) for d in drivers])
    print('\n26 actual planning features:',json.dumps(r['alternative']['model_trace']['input_features'],indent=2))
    print('Synthetic-only uncalibrated classifier scores. Cost arithmetic and health are separate rules.')


if __name__=='__main__':main()
