"""Freeze illustrative demo responses and presentation evidence; never fit models."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import zipfile
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from component4.lkr_inference import LKRResearchInference
from component4.release_input import sha256,assert_experiment_output


def check_case(case,response):
    b=response['baseline'];a=response['alternative'];delta=response['delta']
    if b['status']!='calculated':raise ValueError('baseline_not_calculated')
    if case['id']=='C_invalid_spatial':
        if a['status']!='blocked' or 'spatially_infeasible' not in a['blockers']:
            raise ValueError('spatial_case_not_blocked')
        if any(a[k] is not None for k in ('plan','model_scores','shap_drivers','monte_carlo','draft_planning_health')) or delta is not None:
            raise ValueError('blocked_case_has_fabricated_results')
        return
    if a['status']!='calculated' or delta is None or delta['estimated_cost_lkr']<=0:
        raise ValueError('expected_valid_positive_cost_change')
    p=a['plan']
    if case['id']=='A_normal_change':
        if not all(p[k] for k in ('budget_feasible','affordable_after_reserve','margin_feasible')):
            raise ValueError('normal_case_limits_not_satisfied')
    elif case['id']=='B_budget_margin_failure':
        if p['budget_feasible'] or p['margin_feasible']:raise ValueError('failure_case_did_not_breach_limits')
    else:raise ValueError('unknown_demo_case')
    for r in (b,a):
        if abs(sum(r['plan']['line_items_lkr'].values())-r['plan']['total_cost_lkr'])>0.011:
            raise ValueError('demo_ledger_not_reconciled')
        if abs(r['plan']['retained_receipts_lkr']-r['plan']['total_cost_lkr']-r['plan']['expected_profit_lkr'])>0.011:
            raise ValueError('demo_profit_not_reconciled')
        if any(value is None for value in r['model_scores'].values()):
            raise ValueError('chosen_demo_outside_marginal_model_support')


def request_for(config,case):
    return {'baseline':config['baseline'],'alternative_changes':case['changes'],
            'draws':config['draws'],'seed':config['seed']}


def present_case(service,config,case,raw=False):
    response=service.request(request_for(config,case),'what-if');check_case(case,response)
    if raw:
        print(json.dumps(response,indent=2,allow_nan=False));return
    from scripts.research_pipeline.run_planner_cli_lkr import show
    print('\nPP1 SYNTHETIC RESEARCH CASE:',case['title'])
    print('\nBASELINE');show(response['baseline'])
    print('\nCLIENT CHANGE:',json.dumps(case['changes']))
    print('\nALTERNATIVE');show(response['alternative'])
    if response['delta'] is not None:
        print(f"\nCost difference: LKR {response['delta']['estimated_cost_lkr']:+,.2f}")
        print(f"Profit difference: LKR {response['delta']['expected_profit_lkr']:+,.2f}")
    else:print('\nNo comparison values: alternative is physically invalid.')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true')
    parser.add_argument('--case',choices=['A_normal_change','B_budget_margin_failure','C_invalid_spatial'])
    parser.add_argument('--json',action='store_true',help='Raw response for a selected case')
    parser.add_argument('--interactive',action='store_true',help='Read-only menu for the three frozen demo cases')
    args=parser.parse_args()
    config_path=ROOT/'config/pp1_demo_cases.v1.0.json';config=json.loads(config_path.read_text())
    folder=assert_experiment_output(ROOT/'reports/pp1_readiness_20261015')
    service=LKRResearchInference(config['model_run'])
    old_manifest=ROOT/'reports/experiments/v2.0'/config['model_run']/'completion_checksums.json'
    protected=json.loads(old_manifest.read_text())['files']
    protected={**protected,str(old_manifest.relative_to(ROOT)):sha256(old_manifest),
               'outputs/Component4_Hybrid_Dataset_Final_v1.0.zip':'5baff661b4f6b6e64425b4de2495f77bd395ee1e92dd1f0bf368b753f4e1542f',
               'dataset_releases/v1.0/Component4_Hybrid_Dataset_Final_v1.0.zip':'5baff661b4f6b6e64425b4de2495f77bd395ee1e92dd1f0bf368b753f4e1542f'}
    for name,digest in protected.items():
        if sha256(ROOT/name)!=digest:raise ValueError('existing_training_delivery_changed:'+name)
    if args.interactive:
        try:
            while True:
                choice=input('\nPP1 demo: 1=normal, 2=budget/margin breach, 3=invalid space, q=quit: ').strip().lower()
                if choice=='q':return
                if choice not in ('1','2','3'):print('Choose 1, 2, 3 or q.');continue
                present_case(service,config,config['cases'][int(choice)-1])
        except (EOFError,KeyboardInterrupt):print('\nClosed. No dataset/model changes.');return
    if args.case:
        case=next(c for c in config['cases'] if c['id']==args.case)
        present_case(service,config,case,args.json);return
    summaries=[];responses={}
    for case in config['cases']:
        request=request_for(config,case);start=time.perf_counter()
        response=service.request(request,'what-if');seconds=time.perf_counter()-start
        check_case(case,response)
        if service.request(request,'what-if')!=response:raise ValueError('demo_response_not_reproducible')
        path=folder/(case['id']+'.json')
        bundle={'purpose':'illustrative_synthetic_demo_not_training_or_observed_record','case':case,
                'request':request,'response':response}
        if args.verify:
            if json.loads(path.read_text())!=bundle:raise ValueError('saved_demo_replay_mismatch')
        else:
            with path.open('x',encoding='utf-8') as f:json.dump(bundle,f,indent=2,allow_nan=False)
        a=response['alternative'];responses[case['id']]=response
        summaries.append({'case':case['id'],'status':a['status'],'expectation_check':'PASS',
                          'elapsed_seconds':round(seconds,6),'timing_scope':'single warmed service request, not latency benchmark or SLA',
                          'cost_delta_lkr':None if response['delta'] is None else response['delta']['estimated_cost_lkr'],
                          'cost_lkr':None if a['plan'] is None else a['plan']['total_cost_lkr'],
                          'margin_pct':None if a['plan'] is None else a['plan']['expected_margin_pct']})
    for name,digest in protected.items():
        if sha256(ROOT/name)!=digest:raise ValueError('protected_file_changed_after_demo:'+name)
    if not args.verify:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        b=responses['A_normal_change']['baseline']['plan']
        selected=[b,responses['A_normal_change']['alternative']['plan'],responses['B_budget_margin_failure']['alternative']['plan']]
        names=['Baseline','Normal change','Budget / margin breach']
        fig,axes=plt.subplots(1,2,figsize=(11.5,4.6),layout='constrained')
        colors=['#476C9B','#447F65','#AD5A53']
        axes[0].bar(names,[p['total_cost_lkr']/1e6 for p in selected],color=colors)
        axes[0].axhline(config['baseline']['target_budget_lkr']/1e6,color='#555555',linestyle='--',label='LKR 2M budget')
        axes[0].set_ylabel('Estimated cost (LKR millions)');axes[0].set_title('Cost impact');axes[0].legend()
        axes[1].bar(names,[p['expected_margin_pct'] for p in selected],color=colors)
        axes[1].axhline(config['baseline']['min_profit_margin_pct'],color='#555555',linestyle='--',label='15% required margin')
        axes[1].set_ylabel('Expected margin (%)');axes[1].set_title('Margin impact');axes[1].legend()
        for ax in axes:
            ax.tick_params(axis='x',labelsize=9)
            for bar in ax.patches:
                ax.annotate(f'{bar.get_height():.2f}',(bar.get_x()+bar.get_width()/2,bar.get_height()),
                            ha='center',va='bottom',xytext=(0,5),textcoords='offset points')
        fig.suptitle('Synthetic LKR research demo - published references plus assumed rates/taxes')
        fig.savefig(folder/'demo_cost_margin.png',dpi=180);plt.close(fig)
        metadata={'created_at_utc':datetime.now(timezone.utc).isoformat(),'model_run':config['model_run'],
                  'config_sha256':sha256(config_path),'cases':summaries,'protected_artifacts_unchanged':True,
                  'training_performed':False,'training_dataset_records_generated':0,'real_planner_validation':False,
                  'scope':'Software demonstration evidence only; not economic realism, feedback or commercial validation'}
        with (folder/'demo_verification.json').open('x',encoding='utf-8') as f:json.dump(metadata,f,indent=2)
    print(json.dumps({'status':'PASS','cases':summaries,'protected_artifacts_unchanged':True},indent=2))


if __name__=='__main__':main()
