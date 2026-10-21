"""Predeclared frozen-model robustness audit. No fitting or final-data writes."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from datetime import datetime,timezone
import importlib.metadata
import json
from unittest.mock import patch
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from component4.planner_dashboard_api import PlannerDashboard
from component4.frozen_robustness import make_cases,supported,draw_regime,outcomes,summarize,safety_checks
from component4.expense_risk import FEATURES,TARGETS
from component4.release_input import sha256
from component4.engine import fingerprint


def read(path):return [json.loads(line) for line in path.read_text().splitlines()]


def save(path,value):
    with path.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,allow_nan=False)


def jsonl(path,rows):
    with path.open('x',encoding='utf-8') as f:
        for row in rows:f.write(json.dumps(row,allow_nan=False)+'\n')


def evaluate(api,p):
    inputs=make_cases(api,p);records=[];entries=[]
    roots=list(dict.fromkeys(c['root_family_id'] for c in inputs));draws=p['outcome_draws_per_case_per_regime']
    for case in inputs:
        state=case['state'];response=api.calculate({'baseline':state,'alternative':state});r=response['alternative']
        if r['status']!='calculated':raise ValueError('unexpected_invalid_diagnostic_case:'+case['test_case_id'])
        plan=r['plan'];assert abs(sum(plan['line_items_lkr'].values())-plan['total_cost_lkr'])<.011
        assert plan['used_area_m2']<=state['venue_width_m']*state['venue_length_m']
        assert abs(plan['expected_profit_lkr']-(state['retained_receipts_lkr']-plan['total_cost_lkr']))<.011
        assert all(s is None or s['threshold']==p['threshold'] for s in r['model_scores'].values())
        if not supported(r):assert all(s is None for s in r['model_scores'].values())
        seed=p['seed']+roots.index(case['root_family_id'])
        records.append({**case,'financial_plan':plan,'model_executed':supported(r),
            'model_support_reasons':r['model_trace']['support_reasons'],'planning_features':r['model_trace']['input_features'],
            'model_scores':r['model_scores'],'frozen_monte_carlo':r['monte_carlo'],
            'rule_health':response['insights']['score'],'outcome_family_seed':seed,
            'provenance':response['provenance'],'model_sha256':r['model_trace']['model_sha256']})
        for regime in p['outcome_regimes']:
            # Common random quantiles within each family across its planning states
            # and regimes; methods always see exactly the same realized labels.
            multipliers=draw_regime(regime,draws,seed)
            labels,costs,receipts=outcomes(plan,api.state(state)['planning_inputs'],multipliers)
            for target in TARGETS:
                mc=r['monte_carlo']['overrun_frequency' if target=='Budget_Overrun' else 'margin_risk_frequency']
                model=r['model_scores'][target]
                entries.append({'test_case_id':case['test_case_id'],'root_family_id':case['root_family_id'],
                    'event_type':case['event_type'],'template':case['template'],'regime':regime['id'],'target':target,
                    'positive_outcomes':int(labels[target].sum()),'outcome_draws':draws,
                    'realized_frequency':float(labels[target].mean()),
                    'xgb_score':model['uncalibrated_score'] if model else None,'mc_score':mc,
                    'rule_class':int(not plan['budget_feasible']) if target=='Budget_Overrun' else int(not plan['margin_feasible']),
                    'simulated_cost_p05_p95':np.quantile(costs,[.05,.95]).tolist(),
                    'simulated_receipts_p05_p95':np.quantile(receipts,[.05,.95]).tolist(),
                    'origin':'hypothetical_stress_aggregate_not_observed_event_data'})
    return records,entries,safety_checks(api,p)


def chart(summary,p,path):
    regimes=[r['id'] for r in p['outcome_regimes']];x=np.arange(len(regimes));width=.24
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    for col,target in enumerate(TARGETS):
        for offset,(key,label,color) in enumerate((('frozen_xgboost','Frozen XGBoost','#187d70'),('frozen_monte_carlo','Frozen original-assumption MC','#69899c'),('financial_rule_classes','Financial rule classes','#d49a48'))):
            for row,metric in ((0,'accuracy'),(1,'recall')):
                values=[summary[g][target]['matched_model_supported_cases']['metrics'][key][metric]*100 for g in regimes]
                axes[row,col].bar(x+(offset-1)*width,values,width,color=color,label=label)
                axes[row,col].set_xticks(x,[g.replace('_','\n') for g in regimes],fontsize=9)
                axes[row,col].set_ylim(0,105);axes[row,col].set_ylabel(('Accuracy' if row==0 else 'Risk recall')+' (%)');axes[row,col].grid(axis='y',alpha=.2)
        axes[0,col].set_title(target.replace('_',' '));axes[0,col].legend(fontsize=8)
    fig.suptitle('Frozen-model robustness — matched supported-case comparisons\nHypothetical targeted grid; repeated outcomes/families are not independent events',fontsize=12)
    fig.savefig(path,dpi=160);plt.close(fig)


def write_report(folder,p,summary,records,gates,protected,overlap):
    supported_cases=[r for r in records if r['model_executed']]
    reasons={}
    for r in records:
        for reason in r['model_support_reasons']:reasons[reason]=reasons.get(reason,0)+1
    lines=['# Frozen-model robustness evaluation','',
        '**SOFTWARE CHECKS: PASS. REAL-WORLD GENERALIZATION: NOT VALIDATED.**','',p['holdout_disclosure'],'',
        f"Model run: `{p['model_run']}`. Threshold: {p['threshold']}. No fitting, feature search, calibration or threshold adjustment.",
        f"{len(records)} targeted planning cases / {len({r['root_family_id'] for r in records})} designed root families. Native model scored {len(supported_cases)} cases and withheld {len(records)-len(supported_cases)}. Exact full-planning-vector overlap with the old training/validation/test data: {overlap} cases. Shared source/rule ancestry remains; non-overlap is not independence.",
        '', '## Coverage and safe handling','',
        f"{len(gates)} add/remove, monotonicity, capacity and invalid/unsupported-input checks completed. Missing or out-of-scope predictions stay unavailable. Financially infeasible but geometrically valid plans remain calculable and flagged.",
        '', '| Event/template | Calculable cases | Native scored | Withheld |', '| --- | ---: | ---: | ---: |']
    for event in p['event_types']:
        for template in p['templates']:
            part=[r for r in records if r['event_type']==event and r['template']==template['id']]
            count=sum(r['model_executed'] for r in part)
            lines.append(f"| {event}/{template['id']} | {len(part)} | {count} | {len(part)-count} |")
    lines+=['','Withholding reasons (one case may have several):','']+[f'- {reason}: {n}' for reason,n in sorted(reasons.items())]
    lines+=['','## Distribution-shift results','',
        'All methods below are compared on exactly the same model-supported cases and outcome draws. All-calculable-case MC/rule results are also stored in performance_summary.json; they must not be directly compared against a smaller ML subset.',
        'MC retains the original 0.9–1.1 cost and 0.95–1.05 receipt assumptions in every regime. It does not receive the changed outcome distribution. Rule outputs are classes only; no rule probability calibration/log-loss is claimed.',
        '', '| Target / outcome regime | Cases | Method | Accuracy | Risk recall | False alarms | Missed risk draws |',
        '| --- | ---: | --- | ---: | ---: | ---: | ---: |']
    for target in TARGETS:
        for regime in p['outcome_regimes']:
            part=summary[regime['id']][target]['matched_model_supported_cases']
            for key,m in part['metrics'].items():
                lines.append(f"| {target}/{regime['id']} | {part['cases']} | {key} | {100*m['accuracy']:.2f}% | {100*m['recall']:.2f}% | {int(m['fp'])} | {int(m['fn'])} |")
    lines+=['','![Frozen-model stress results](regime_performance.png)','',
        '## Interpretation','',
        '- Repeated outcome counts are diagnostic draws, not independent observed events. Grid quotas are not real-world event frequencies; do not compare headline accuracy across regimes without the positive-class counts in the JSON report.',
        '- The original regime checks compatibility with the assumed training mechanism. Adverse regimes intentionally test distribution shift, including cost/receipt dependence absent from training.',
        '- Any deterioration is reported without retries or model selection. No superiority claim, real-world accuracy, guaranteed profitability or new bulk-dataset readiness follows from software PASS.',
        '- Stress ranges are hypothetical engineering choices, not prices, empirical volatility or approved financial policy. Cost/health calculations remain rules; native TreeSHAP remains a model explanation, not a correctness guarantee.',
        '- Inputs outside the existing model support stay withheld. Do not remove support checks merely to increase coverage. Native prediction coverage and errors are separate findings.',
        '- Future changes would require a separate experiment/version and new locked evaluation. This report does not authorize retraining or changing production financial parameters.',
        '', '## Reproducibility and files','',
        f'{protected} pre-existing source/data/model/report files remained checksum-identical. Protocol/source/model hashes were saved before evaluation. Seeds and family identity are in case_results.jsonl; outcome_counts.jsonl stores sufficient counts rather than individual synthetic outcome rows.',
        '- `protocol.json`: frozen scope, model/source/runtime hashes and protected inventory.',
        '- `case_results.jsonl`: 180 hypothetical planning inputs, financial ledgers, model support/scores and frozen MC predictions.',
        '- `outcome_counts.jsonl`: target-specific aggregate diagnostic draws, with synthetic-only provenance.',
        '- `performance_summary.json`: matched/all-case metrics plus event/template strata.',
        '- `safety_checks.json`, `verification.json`, `checksums.json`: software/integrity evidence.',
        '', 'No master dataset, final dataset ZIP, trained model, frontend or existing split was overwritten.']
    (folder/'robustness_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main():
    p=json.loads((ROOT/'config/robustness.v0.1.json').read_text());api=PlannerDashboard();risk=api.risk
    if risk.run_id!=p['model_run'] or p['threshold']!=.5:raise ValueError('frozen_model_or_threshold_mismatch')
    folder=ROOT/'reports/robustness'/p['run_id']
    if folder.exists():raise ValueError('refuse_existing_robustness_run')
    old=json.loads((risk.folder/'protocol.json').read_text());protected=old['protected_files'].copy()
    for base in (risk.folder,risk.report,ROOT/'reports/diagnostics'):
        protected.update({f.relative_to(ROOT).as_posix():sha256(f) for f in base.rglob('*') if f.is_file()})
    source=old['source_hashes'].copy()
    for name in ('config/robustness.v0.1.json','component4/frozen_robustness.py','scripts/model_experiments/run_frozen_robustness.py',
                 'component4/enhanced_risk_inference.py','component4/planner_dashboard_api.py','component4/risk_experiment.py'):
        source[name]=sha256(ROOT/name)
    assert all(sha256(ROOT/k)==v for k,v in protected.items())
    folder.mkdir(parents=True)
    save(folder/'protocol.json',{'recorded_before_evaluation_utc':datetime.now(timezone.utc).isoformat(),
        'design':p,'source_hashes':source,'protected_files':protected,'model_sha256':risk.metadata['model_sha256'],
        'runtime':{k:importlib.metadata.version(k) for k in ('numpy','scikit-learn','xgboost','matplotlib')},
        'no_fitting_or_model_selection':True,'numeric_financial_config_sha256':api.planner.service.config_hash})
    with patch('xgboost.XGBClassifier.fit',side_effect=AssertionError('frozen_evaluation_must_not_fit')):
        records,entries,gates=evaluate(api,p)
    original=read(ROOT/'data/experiments/v3.0'/risk.original_run/'planning_risk_dataset.jsonl')
    oldvectors={tuple(r[f] for f in FEATURES) for r in original}
    overlap=sum(tuple(r['planning_features'][f] for f in FEATURES) in oldvectors for r in records)
    summary=summarize(entries,p['outcome_draws_per_case_per_regime'])
    strata={}
    for field in ('event_type','template'):
        strata[field]={value:summarize([e for e in entries if e[field]==value],p['outcome_draws_per_case_per_regime']) for value in sorted({e[field] for e in entries})}
    jsonl(folder/'case_results.jsonl',records);jsonl(folder/'outcome_counts.jsonl',entries)
    save(folder/'performance_summary.json',{'pooled':summary,'strata':strata,'scope':'targeted hypothetical stress grid, not empirical generalization','case_count':len(records),
        'native_scored_cases':sum(r['model_executed'] for r in records),'designed_root_families':12,'full_planning_vector_overlap_cases':overlap,
        'individual_outcome_rows_persisted':0,'total_case_regime_draw_combinations':len(records)*len(p['outcome_regimes'])*p['outcome_draws_per_case_per_regime']})
    save(folder/'safety_checks.json',gates)
    chart(summary,p,folder/'regime_performance.png');write_report(folder,p,summary,records,gates,len(protected),overlap)
    assert all(sha256(ROOT/k)==v for k,v in protected.items()),'frozen_artifact_modified'
    save(folder/'verification.json',{'status':'PASS_SOFTWARE_AND_INTEGRITY_ONLY','protected_files_unchanged':len(protected),
        'model_fitting_attempts':0,'production_models_or_thresholds_changed':False,'old_datasets_changed':False,
        'financial_reconciliation':'PASS','safe_handling_checks':len(gates),'source_model_hashes':risk.metadata['model_sha256'],
        'real_world_validation':False,'protocol_sha256':sha256(folder/'protocol.json')})
    save(folder/'checksums.json',{f.name:sha256(f) for f in folder.iterdir() if f.is_file()})
    print(json.dumps({'folder':str(folder),'cases':len(records),'scored':sum(r['model_executed'] for r in records),
        'gates':len(gates),'matched_performance':{g:{t:v[t]['matched_model_supported_cases'] for t in TARGETS} for g,v in summary.items()}},indent=2))


if __name__=='__main__':main()
