"""Frozen-model stress diagnostics. No fit, parameter selection or dataset writer."""
from copy import deepcopy
import math
import numpy as np
from .expense_risk import make_estimate,TARGETS
from .planner_services import cash
from .risk_experiment import metrics


def draw_regime(regime,n,seed):
    if type(n) is not int or n<1:raise ValueError('positive_integer_draw_count')
    a,b=regime['cost'];c,d=regime['receipts']
    if not all(math.isfinite(v) for v in (a,b,c,d)) or not 0<a<b or not 0<c<d:raise ValueError('invalid_stress_bounds')
    rng=np.random.default_rng(seed);u=rng.uniform(size=n)
    if regime['dependence']=='independent':v=rng.uniform(size=n)
    elif regime['dependence']=='inverse_common_uniform':v=1-u
    else:raise ValueError('unsupported_stress_dependence')
    return a+(b-a)*u,c+(d-c)*v


def outcomes(plan,inputs,multipliers):
    c,r=multipliers
    costs=np.round(sum(np.round(v*c,2) for v in plan['line_items_lkr'].values()),2)
    receipts=np.round(inputs['retained_receipts_lkr']*r,2)
    margin=100*(receipts-costs)/receipts
    return {'Budget_Overrun':(costs>inputs['target_budget_lkr']).astype(int),
        'Profit_Margin_Risk':(margin<inputs['min_profit_margin_pct']).astype(int)},costs,receipts


def make_cases(api,p):
    result=[]
    for event in p['event_types']:
        for ti,template in enumerate(p['templates']):
            root=f"ROB-{event}-{template['id']}"
            state=api.config()['default_state'];state.update(event_type=event,**{k:v for k,v in template.items() if k!='id'})
            base=api.calculate({'baseline':state,'alternative':state})['alternative']
            if base['status']!='calculated':raise ValueError('invalid_planned_template:'+root)
            core=base['plan']['total_cost_lkr']
            for bi,budget_factor in enumerate(p['budget_factors_of_planned_cost']):
                for mi,margin in enumerate(p['expected_margin_fractions']):
                    s=deepcopy(state);s.update(target_budget_lkr=cash(core*budget_factor),
                        retained_receipts_lkr=cash(core/(1-margin)),min_profit_margin_pct=p['minimum_margin_pct'])
                    result.append({'test_case_id':f'{root}-B{bi}-M{mi}','root_family_id':root,
                        'event_type':event,'template':template['id'],'budget_factor':budget_factor,
                        'planned_margin_fraction':margin,'state':s,'origin':'hypothetical_frozen_model_stress_not_training_or_observed'})
    return result


def supported(result):return result['model_trace']['prediction_executed']


def class_metrics(y,p):
    all_metrics=metrics(y,p)
    return {k:all_metrics[k] for k in ('accuracy','balanced_accuracy','precision','recall','f1','tn','fp','fn','tp')}


def summarize(entries,draws):
    """Matched supported-case comparisons; separate all-calculable baselines."""
    result={}
    for regime in sorted({e['regime'] for e in entries}):
        result[regime]={}
        for target in TARGETS:
            part=[e for e in entries if e['regime']==regime and e['target']==target]
            matched=[e for e in part if e['xgb_score'] is not None]
            groups={}
            for scope,selected in (('matched_model_supported_cases',matched),('all_calculable_cases',part)):
                if not selected:groups[scope]={'cases':0};continue
                # Aggregate sufficient counts, not stored individual outcome rows.
                y=np.concatenate([np.r_[np.ones(e['positive_outcomes'],dtype=int),np.zeros(draws-e['positive_outcomes'],dtype=int)] for e in selected])
                mc=np.repeat([e['mc_score'] for e in selected],draws);rule=np.repeat([e['rule_class'] for e in selected],draws)
                scores={'frozen_monte_carlo':metrics(y,mc),'financial_rule_classes':class_metrics(y,rule)}
                if scope=='matched_model_supported_cases':scores['frozen_xgboost']=metrics(y,np.repeat([e['xgb_score'] for e in selected],draws))
                groups[scope]={'cases':len(selected),'root_families':len({e['root_family_id'] for e in selected}),
                    'simulated_outcome_draws':len(y),'positive_outcomes':int(y.sum()),'metrics':scores}
            result[regime][target]=groups
    return result


def safety_checks(api,p):
    records=[]
    for event in p['event_types']:
        base=api.config()['default_state'];base['event_type']=event
        original=api.calculate({'baseline':base,'alternative':base})['baseline'];core=original['plan']['total_cost_lkr']
        previous=original
        for j,fraction in enumerate(p['expense_addition_fractions_of_core']):
            alt=deepcopy(base)
            if fraction:alt['quotes']=[make_estimate('diagnostic_optional',core*fraction,0)]
            response=api.calculate({'baseline':base,'alternative':alt});r=response['alternative']
            assert r['status']=='calculated' and response['baseline']['plan']==original['plan']
            assert abs(r['plan']['total_cost_lkr']-core-cash(core*fraction))<.011
            assert r['plan']['expected_profit_lkr']<=previous['plan']['expected_profit_lkr']+.011
            if supported(r) and supported(previous):
                for target in TARGETS:assert r['model_scores'][target]['uncalibrated_score']+1e-8>=previous['model_scores'][target]['uncalibrated_score']
            records.append({'event_type':event,'check':'positive_expense_'+str(fraction),'financial_pass':True,'model_checked':supported(r) and supported(previous)})
            if fraction:
                removed=deepcopy(alt);removed['removed_quote_ids']=['assumed_0']
                restored=api.calculate({'baseline':alt,'alternative':removed})['alternative']
                assert restored['plan']['total_cost_lkr']==original['plan']['total_cost_lkr']
                assert restored['model_scores']==original['model_scores']
                records.append({'event_type':event,'check':'expense_removal_'+str(fraction),'pass':True})
            previous=r
        cap=deepcopy(base);cap['guests']=277
        assert api.calculate({'baseline':base,'alternative':cap})['alternative']['status']=='calculated'
        records.append({'event_type':event,'check':'277_guests_capacity_boundary','pass':True})
        changes={
            'capacity_278_in_500m2':{'guests':278},'guest_49':{'guests':49},'guest_501':{'guests':501},
            'zero_budget':{'target_budget_lkr':0},'missing_budget':{'target_budget_lkr':None},
            'nonfinite_venue':{'venue_width_m':float('nan')},'client_stage_injection':{'stage_width_m':8},
            'five_optional_expenses':{'quotes':[make_estimate('diagnostic_'+str(i),10000,i) for i in range(5)]},
            'excess_optional_exposure':{'quotes':[make_estimate('diagnostic_big',core*.9,0)]},
            'committed_quote_regime':{'quotes':[{**make_estimate('diagnostic_committed',10000,0),'committed':True}]},
            'missing_optional_price':{'quotes':[{**make_estimate('diagnostic_missing',10000,0),'unit_rate_lkr':None}]},
            'geometry_outside_training_marginals':{'venue_width_m':50,'venue_length_m':40}}
        assert set(changes)==set(p['gate_cases'])
        for name,update in changes.items():
            state=deepcopy(base);state.update(update)
            try:r=api.calculate({'baseline':base,'alternative':state})['alternative']
            except ValueError as exc:
                records.append({'event_type':event,'check':name,'pass':True,'status':'request_rejected','reason':str(exc)});continue
            assert not supported(r) and all(v is None for v in r['model_scores'].values()),'unsafe_prediction:'+name
            if name.startswith('capacity_') or name in ('guest_49','guest_501','zero_budget','missing_optional_price'):assert r['plan'] is None
            records.append({'event_type':event,'check':name,'pass':True,'status':r['status'],'reasons':r['model_trace']['support_reasons'],'blockers':r['blockers']})
    return records
