"""Terminal-only inspection of existing models; no fitting or dataset writing."""
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from uuid import uuid4

from .experimental_indicators import planning_indicator
from .contracts import validate_contract
from .release_input import assert_experiment_output

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('guests','event_hours','stage_width_m','stage_length_m','budget_score','retained_receipts_score')
DEFAULTS = {'guests':100,'event_hours':4,'stage_width_m':3,'stage_length_m':4,
            'budget_score':3,'retained_receipts_score':4}


def read_value(name, default, profile, *, reader=input, writer=print):
    allowed = (f"integer {profile['guest_min']} to {profile['guest_max']}" if name=='guests'
               else ', '.join(str(v) for v in profile[name]))
    while True:
        raw=reader(f'{name} [{allowed}] (Enter = {default}): ').strip()
        try:
            value=float(raw) if raw else float(default)
            if not math.isfinite(value):raise ValueError()
            if name=='guests':
                if not value.is_integer() or not profile['guest_min']<=value<=profile['guest_max']:raise ValueError()
                return int(value)
            if value not in profile[name]:raise ValueError()
            return value
        except ValueError:
            writer('Invalid input. Use one of the displayed supported values; amounts are NOT LKR.')


def collect_inputs(profile, defaults=None, *, reader=input, writer=print):
    defaults=defaults or DEFAULTS
    return {name:read_value(name,defaults[name],profile,reader=reader,writer=writer) for name in FIELDS}


def display(result, *, writer=print):
    writer('\nStatus: '+result['status'])
    if result['status']!='calculated':
        writer('BLOCKED: '+ '; '.join(result['blockers']))
        writer('No calculated costs, model scores or health score.');return
    p=result['planned'];scores=result['model_risk_scores'];mc=result['monte_carlo']
    writer('RULE-BASED PLANNING ESTIMATES (dimensionless_score, NOT rupees)')
    for key in ('total_cost_score','expected_revenue_score','expected_profit_score','reserve_score'):
        writer(f'  {key}: {p[key]:.4f}')
    margin=p['expected_margin_points']
    writer('  Expected margin: '+('unavailable' if margin is None else f'{margin:.2f}%'))
    writer(f"  Area: {p['used_area_m2']:.2f}/{p['usable_area_m2']:.2f} m2 ({100*p['space_utilization']:.2f}%)")
    writer(f"  Seats: {p['seats']}; staff: {p['staff']}; tables: {p['tables']}")
    writer(f"  Budget feasible: {p['budget_feasible']}; affordable after reserve: {p['operating_allowance_feasible']}")
    writer('  Itemized expenses: '+json.dumps(p['line_items_score']))
    writer('SAVED XGBOOST (uncalibrated scores, NOT real-world probabilities)')
    for target in ('Budget_Overrun','Profit_Margin_Risk'):
        value=scores[target]
        writer(f'  {target}: '+('unavailable outside training support' if value is None else f'score={value:.6f}; class={int(value>=.5)} (threshold 0.5)'))
    writer('  Vendor_Cost_Anomaly: unavailable; useful pre-event predictor not established')
    writer('HYPOTHETICAL MONTE CARLO (not calibrated real-world risk)')
    for key in ('budget_overrun_frequency','profit_margin_risk_frequency'):
        writer(f'  {key}: {mc[key]:.4f}')
    writer('  Simulated cost distribution: '+json.dumps(mc['cost_score']))
    indicator=planning_indicator(result)
    score=indicator['score']
    writer('DRAFT planning coverage indicator: '+('unavailable' if score is None else f'{score:.2f}/100 points'))
    writer('  Proposed rule, not independently approved or validated financial health.')
    for message in result['warnings']:writer('WARNING: '+message)


def evaluate(service,payload,operation='calculate'):
    response=service.request(payload,operation)
    schema=json.loads((ROOT/'api/contracts/unitless_decision.response.schema.json').read_text())
    validate_contract(response,schema)
    results=[response['result']] if operation=='calculate' else [response['baseline'],response['alternative']]
    return {'kind':'manual_research_model_check_not_training_data','request':payload,
            'response':response,'draft_indicators':[planning_indicator(r) for r in results]}


def save_check(bundle):
    folder=assert_experiment_output(ROOT/'outputs/manual_model_checks')
    folder.mkdir(parents=True,exist_ok=True)
    name=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid4().hex[:10]+'.json'
    path=folder/name
    with path.open('x',encoding='utf-8') as target:
        json.dump(bundle,target,indent=2,allow_nan=False)
    return path


def run(service, *, reader=input, writer=print, save=True):
    writer('UNITLESS SYNTHETIC RESEARCH ONLY - NOT LKR OR REAL MARKET PREDICTIONS')
    writer('Saved XGBoost + deterministic engine + hypothetical Monte Carlo. No model training.')
    writer('Guests are integers; other inputs use the frozen discrete domains shown below.')
    while True:
        event=reader('\nEvent type: 1=Wedding, 2=Corporate, q=Quit [1]: ').strip().lower()
        if event=='q':return
        if event not in ('','1','2'):
            writer('Choose 1, 2 or q.');continue
        event='Corporate' if event=='2' else 'Wedding'
        inputs=collect_inputs(service.config['profiles'][event],reader=reader,writer=writer)
        payload={'event_type':event,'inputs':inputs,'draws':2000,'seed':20261012}
        bundle=evaluate(service,payload)
        display(bundle['response']['result'],writer=writer)
        if save:writer('Full results saved: '+str(save_check(bundle)))
        if reader('\nCompare a What-If alternative? y/N: ').strip().lower()=='y':
            writer('Enter alternative inputs; Enter keeps the baseline value.')
            alternative=collect_inputs(service.config['profiles'][event],inputs,reader=reader,writer=writer)
            compare={'event_type':event,'baseline':inputs,'alternative_changes':alternative,
                     'draws':2000,'seed':20261012}
            bundle=evaluate(service,compare,'what-if')
            display(bundle['response']['alternative'],writer=writer)
            writer('BASELINE -> ALTERNATIVE differences (paired same-seed simulation):')
            writer(json.dumps(bundle['response']['delta'],indent=2))
            if bundle['response']['delta'] is None:writer('Comparison blocked; no misleading differences computed.')
            if save:writer('Full comparison saved: '+str(save_check(bundle)))


def main():
    import argparse
    from .unitless_decision_support import UnitlessDecisionSupport
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--example',action='store_true',help='Noninteractive default Wedding example')
    parser.add_argument('--no-save',action='store_true',help='Display only, do not save a report')
    args=parser.parse_args()
    print('Loading checksum-verified existing models...')
    service=UnitlessDecisionSupport()
    if args.example:
        bundle=evaluate(service,{'event_type':'Wedding','inputs':dict(DEFAULTS),'draws':2000,'seed':20261012})
        print('UNITLESS SYNTHETIC RESEARCH ONLY - NOT LKR OR REAL MARKET PREDICTIONS')
        display(bundle['response']['result'])
        if not args.no_save:print('Full results saved:',save_check(bundle))
    else:
        try:run(service,save=not args.no_save)
        except (KeyboardInterrupt,EOFError):print('\nClosed. No dataset or model changes.')
