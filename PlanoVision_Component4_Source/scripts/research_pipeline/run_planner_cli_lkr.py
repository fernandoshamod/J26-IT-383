"""Monetary research CLI with continuous inputs and newly fitted LKR models."""
import argparse
from datetime import datetime,timezone
import json
import math
from pathlib import Path
import sys
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from component4.lkr_research import defaults,VERSION
from component4.lkr_inference import LKRResearchInference
from component4.release_input import assert_experiment_output


def collect(config,event,baseline=None,reader=input,writer=print):
    inputs=dict(baseline or defaults(config,event))
    writer('Spatial values simulate the future Component 1 feed. Rates simulate Component 2/3 feeds.')
    for field in ('guests','event_hours','stage_width_m','stage_length_m','venue_area_m2',
                  'target_budget_lkr','retained_receipts_lkr','min_profit_margin_pct'):
        while True:
            raw=reader(f'{field} [Enter={inputs[field]}]: ').strip().replace(',','')
            try:
                value=float(raw) if raw else inputs[field]
                if isinstance(value,bool) or not math.isfinite(value):raise ValueError()
                if field=='guests':
                    if not float(value).is_integer():raise ValueError()
                    value=int(value)
                domain={'guests':'guest_count'}.get(field,field)
                if domain in config['domains']:
                    lo,hi=config['domains'][domain]
                    if not lo<=value<=hi:raise ValueError()
                elif value<=0:raise ValueError()
                inputs[field]=value;break
            except ValueError:writer('Invalid number/domain; use positive LKR amounts and supported geometry/hours.')
    return inputs


def show(result):
    print('\nStatus:',result['status'])
    if result['status']=='blocked':print('Cannot calculate:',', '.join(result['blockers']));return
    p=result['plan'];inputs=result['inputs']
    print('\nFINANCIAL ESTIMATE (LKR; published reference + hypothetical assumptions)')
    for name in ('total_cost_lkr','retained_receipts_lkr','expected_profit_lkr','reserve_lkr','budget_headroom_lkr',
                 'recommended_client_price_excluding_output_tax_lkr'):
        print(f'{name}: LKR {p[name]:,.2f}')
    print(f"Target budget: LKR {inputs['target_budget_lkr']:,.2f}")
    print(f"Expected margin: {p['expected_margin_pct']:.2f}% | Required: {inputs['min_profit_margin_pct']:.2f}%")
    print('Budget feasible:',p['budget_feasible'],'| Affordable after reserve:',p['affordable_after_reserve'],'| Margin feasible:',p['margin_feasible'])
    print('Itemized expenses (synthetic allocations/rates; not separate vendor quotes):')
    for name,amount in p['line_items_lkr'].items():print(f'  {name}: LKR {amount:,.2f}')
    print(f"Space: {p['used_area_m2']:.2f}/{inputs['venue_area_m2']:.2f} m2 ({100*p['space_utilization']:.2f}%)")
    print(f"Seats: {p['seats']} | Tables: {p['tables']} | Staff: {p['staff']}")
    print('\nNEW XGBOOST MODELS (synthetic test scope; uncalibrated scores)')
    for target,scores in result['model_scores'].items():
        print(target+': '+('unavailable outside training feature bounds' if scores is None else f"score={scores['uncalibrated_score']:.4f}; class={scores['class']}"))
        for driver in result['shap_drivers'][target] or []:
            print(f"  SHAP {driver['feature']}: {driver['contribution_log_odds']:+.4f} log-odds ({driver['direction']}); not a monetary effect")
    print('\nMONTE CARLO (assumed shocks, NOT real-world probabilities)')
    m=result['monte_carlo']
    print(f"Simulated overrun frequency: {100*m['overrun_frequency']:.2f}% | Margin-risk frequency: {100*m['margin_risk_frequency']:.2f}%")
    print(f"Simulated cost mean: LKR {m['cost_lkr']['mean']:,.2f} | p05: {m['cost_lkr']['p05']:,.2f} | p95: {m['cost_lkr']['p95']:,.2f}")
    print(f"Draft planning-coverage indicator: {result['draft_planning_health']['score_points']:.2f}/100 points (not validated financial health)")
    for warning in p['warnings']:print('NOTE:',warning)


def save(response):
    folder=assert_experiment_output(ROOT/'outputs/lkr_manual_checks');folder.mkdir(parents=True,exist_ok=True)
    path=folder/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid4().hex[:8]+'.json')
    with path.open('x',encoding='utf-8') as f:json.dump(response,f,indent=2,allow_nan=False)
    print('Full response saved:',path)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-id',default=VERSION);parser.add_argument('--example',action='store_true')
    parser.add_argument('--no-save',action='store_true');args=parser.parse_args()
    print('Loading newly trained LKR models. RESEARCH ESTIMATES, NOT VERIFIED ALL-IN QUOTATIONS.')
    service=LKRResearchInference(args.run_id)
    if args.example:
        baseline=defaults(service.config)
        response=service.request({'baseline':baseline,'alternative_changes':{'guests':180,'stage_width_m':5.5,'event_hours':7.25}},'what-if')
        print('\nBASELINE');show(response['baseline']);print('\nALTERNATIVE');show(response['alternative'])
        print('\nWHAT-IF DELTA:',json.dumps(response['delta'],indent=2))
        if not args.no_save:save(response)
        return
    try:
        while True:
            choice=input('\nEvent: 1=Wedding, 2=Corporate, q=Quit [1]: ').strip().lower()
            if choice=='q':return
            if choice not in ('','1','2'):print('Choose 1, 2 or q.');continue
            event='Corporate' if choice=='2' else 'Wedding'
            baseline=collect(service.config,event)
            response=service.request({'inputs':baseline});show(response['result'])
            if not args.no_save:save(response)
            if input('Compare What-If alternative? y/N: ').strip().lower()=='y':
                alternative=collect(service.config,event,baseline)
                response=service.request({'baseline':baseline,'alternative_changes':alternative},'what-if')
                show(response['alternative'])
                print('\nBaseline / Alternative / Delta (LKR):')
                if response['delta'] is None:print('Blocked comparison; no fabricated differences.')
                else:
                    for key in ('total_cost_lkr','expected_profit_lkr','reserve_lkr','budget_headroom_lkr'):
                        b=response['baseline']['plan'][key];a=response['alternative']['plan'][key]
                        print(f'{key}: {b:,.2f} / {a:,.2f} / {a-b:+,.2f}')
                if not args.no_save:save(response)
    except (KeyboardInterrupt,EOFError):print('\nClosed. No dataset or model changes.')


if __name__=='__main__':main()
