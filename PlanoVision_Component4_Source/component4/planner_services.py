"""Versioned service-change layer; preserves frozen calculators and models.

Consumes declared quotations, never manufactures missing prices or approvals.
"""
from copy import deepcopy
from datetime import date
from decimal import Decimal,ROUND_HALF_UP
import math
import re
import numpy as np
from .lkr_research import calculate,shocks
from .lkr_inference import summary

CORE={'catering','chairs','tables','stage','av','labour','venue'}
QFIELDS={'id','label','mode','service','quantity_basis','unit_rate_lkr','tax_scope',
         'service_pct','tax_pct','pricing_policy','increase_pct','source_kind',
         'evidence_ref','valid_from','valid_until','covers','committed','cancellation_fee_lkr'}
BASES={'booking','guests','tables','stage_m2','av_kits','staff_hours','event_hours'}
CORE_BASES={'catering':'guests','chairs':'guests','tables':'tables','stage':'stage_m2',
            'av':'av_kits','labour':'staff_hours','venue':'booking'}


def finite(value,name,lo=0,hi=None):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError('finite_numeric_required:'+name)
    if value<lo or (hi is not None and value>hi):raise ValueError('outside_range:'+name)
    return value


def cash(value):
    return float(Decimal(str(value)).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP))


def text(value,name,maximum=256):
    if not isinstance(value,str) or not value.strip() or len(value)>maximum or any(ord(c)<32 for c in value):
        raise ValueError('invalid_text:'+name)


def iso(value):
    if not isinstance(value,str):raise ValueError('iso_date_required')
    try:d=date.fromisoformat(value)
    except ValueError:raise ValueError('iso_date_required') from None
    if d.isoformat()!=value:raise ValueError('iso_date_required')
    return d


def validate_quote(q):
    if not isinstance(q,dict) or set(q)!=QFIELDS:raise ValueError('exact_quote_fields_required')
    if not isinstance(q['id'],str) or re.fullmatch(r'[A-Za-z0-9_-]{1,64}',q['id']) is None:
        raise ValueError('invalid_quote_id')
    for name in ('label','service','evidence_ref'):text(q[name],name)
    if q['mode'] not in ('add','replace') or q['quantity_basis'] not in BASES:raise ValueError('invalid_quote_mode_or_unit')
    if q['source_kind'] not in ('mock_test_only','user_supplied_unverified_quote','public_advertisement','planner_entered_assumption'):
        raise ValueError('invalid_source_kind')
    if not isinstance(q['covers'],list) or not q['covers'] or any(not isinstance(s,str) or not s.strip() for s in q['covers']) or len(set(q['covers']))!=len(q['covers']):
        raise ValueError('unique_covered_services_required')
    for s in q['covers']:text(s,'covers')
    if q['unit_rate_lkr'] is not None:finite(q['unit_rate_lkr'],'unit_rate_lkr',hi=1e12)
    if type(q['committed']) is not bool:raise ValueError('explicit_commitment_state_required')
    if q['cancellation_fee_lkr'] is not None:finite(q['cancellation_fee_lkr'],'cancellation_fee_lkr')
    if not q['committed'] and q['cancellation_fee_lkr']!=0:raise ValueError('uncommitted_quote_requires_explicit_zero_cancellation_fee')
    for name in ('service_pct','tax_pct'):
        if q[name] is not None:finite(q[name],name,hi=100)
    if q['tax_scope'] not in ('all_in','exclusive_declared','unknown'):raise ValueError('invalid_tax_scope')
    if q['tax_scope']=='all_in' and (q['service_pct']!=0 or q['tax_pct']!=0):
        raise ValueError('all_in_quote_must_not_be_grossed_up_again')
    if q['pricing_policy'] not in ('locked','documented_escalation','unknown','planning_estimate'):raise ValueError('invalid_pricing_policy')
    if q['source_kind']=='planner_entered_assumption' or q['pricing_policy']=='planning_estimate':
        if q['source_kind']!='planner_entered_assumption' or q['pricing_policy']!='planning_estimate' or q['tax_scope']!='all_in' or q['increase_pct']!=0:
            raise ValueError('planning_estimate_requires_explicit_assumed_total_not_supplier_lock')
    if q['increase_pct'] is not None:finite(q['increase_pct'],'increase_pct',lo=-99,hi=500)
    if q['pricing_policy']=='locked' and q['increase_pct']!=0:raise ValueError('locked_quote_cannot_have_price_increase')
    if iso(q['valid_until'])<iso(q['valid_from']):raise ValueError('inverted_quote_dates')
    if q['mode']=='replace' and (q['service'] not in CORE or q['quantity_basis']!=CORE_BASES[q['service']] or set(q['covers'])!={q['service']}):
        raise ValueError('replacement_requires_one_matching_core_service_and_unit')
    if q['mode']=='add' and (q['service'] in CORE or set(q['covers'])&CORE):
        raise ValueError('included_core_service_requires_replacement_not_double_charge')


def quantity(basis,inputs,plan,config):
    return {'booking':1,'guests':inputs['guests'],'tables':plan['tables'],
            'stage_m2':plan['stage_area_m2'],
            'av_kits':0 if plan['stage_area_m2']==0 else math.ceil(plan['stage_area_m2']/config['assumptions']['included_stage_area_m2']),
            'staff_hours':plan['paid_person_hours'],'event_hours':inputs['event_hours']}[basis]


def evaluate_state(service,state,draws,seed,common):
    if not isinstance(state,dict) or set(state)!={'planning_inputs','event_date','quotes','removed_quote_ids'}:
        raise ValueError('exact_planner_state_required')
    when=iso(state['event_date']);quotes=state['quotes'];removed=state['removed_quote_ids']
    if not isinstance(quotes,list) or len(quotes)>30 or not isinstance(removed,list) or any(not isinstance(s,str) for s in removed) or len(set(removed))!=len(removed):
        raise ValueError('invalid_quote_collection')
    for q in quotes:validate_quote(q)
    ids=[q['id'] for q in quotes]
    if len(set(ids))!=len(ids) or set(removed)-set(ids):raise ValueError('duplicate_or_unknown_quote_ids')
    inputs=state['planning_inputs']
    result={'status':'blocked','inputs':deepcopy(state),'plan':None,'model_scores':None,
            'monte_carlo':None,'draft_planning_health':None,'blockers':[],'actions':[]}
    try:
        base=calculate(service.config,service.evidence,inputs)
        finite(inputs['target_budget_lkr'],'target_budget_lkr',hi=1e15)
        finite(inputs['retained_receipts_lkr'],'retained_receipts_lkr',hi=1e15)
    except ValueError as exc:result['blockers']=[str(exc)];return result,None
    active=[q for q in quotes if q['id'] not in removed]
    cancellation={}
    cancellation_unknown=[]
    for q in quotes:
        if q['id'] in removed and q['committed']:
            if q['cancellation_fee_lkr'] is None:cancellation_unknown.append(q['id']+':cancellation_terms_required')
            elif q['cancellation_fee_lkr']>0:cancellation['cancellation:'+q['id']]=q['cancellation_fee_lkr']
    if not active and not cancellation and not cancellation_unknown:
        original,cost=service.evaluate(inputs,draws,seed,common)
        if original['status']=='calculated':
            original['actions']=actions(inputs,original['plan'])
            original['quote_change_status']='no_active_quotes_original_model_rules'
            original['event_date']=state['event_date']
        return original,cost
    claimed=set();unpriced=list(cancellation_unknown)
    for q in active:
        if claimed & set(q['covers']):raise ValueError('overlapping_quote_services')
        claimed.update(q['covers'])
        if q['mode']=='replace' and inputs['event_type']=='Corporate':
            unpriced.append(q['id']+':bundled_corporate_requotation_required')
        if q['source_kind']!='planner_entered_assumption' and not iso(q['valid_from'])<=when<=iso(q['valid_until']):unpriced.append(q['id']+':quote_not_valid_for_event_date')
        if q['unit_rate_lkr'] is None:unpriced.append(q['id']+':rate_missing')
        if q['tax_scope']=='unknown' or q['service_pct'] is None or q['tax_pct'] is None:
            unpriced.append(q['id']+':charge_scope_missing')
        if q['pricing_policy']=='unknown' or q['increase_pct'] is None:unpriced.append(q['id']+':future_price_terms_missing')
    if unpriced:
        result.update(status='quotation_required',blockers=unpriced);return result,None
    plan=deepcopy(base);lines=deepcopy(base['line_items_lkr'])
    if any(q['source_kind']=='planner_entered_assumption' for q in active):
        base['warnings']=base['warnings']+['Planner-entered expense amounts are hypothetical all-in allowances, not supplier quotations, verified tax rates or price locks.']
    evidence={k:{'origin':'original_synthetic_reference_calculation','pricing_policy':'experimental_shocks'} for k in lines}
    for key,amount in cancellation.items():
        lines[key]=amount
        q=next(q for q in quotes if 'cancellation:'+q['id']==key)
        evidence[key]={'origin':'declared_cancellation_charge','pricing_policy':'locked',
                       'quote_id':q['id'],'evidence_ref':q['evidence_ref'],'independently_verified':False}
    details=[]
    for q in active:
        qty=quantity(q['quantity_basis'],inputs,base,service.config)
        raw=Decimal(str(qty))*Decimal(str(q['unit_rate_lkr']))*(1+Decimal(str(q['increase_pct']))/100)
        gross=raw if q['tax_scope']=='all_in' else raw*(1+Decimal(str(q['service_pct']))/100)*(1+Decimal(str(q['tax_pct']))/100)
        amount=float(gross.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP))
        finite(amount,'quote_line_total')
        key=q['service'] if q['mode']=='replace' else 'extra:'+q['id']
        lines[key]=amount
        evidence[key]={'origin':q['source_kind'],'quote_id':q['id'],'evidence_ref':q['evidence_ref'],
                       'pricing_policy':q['pricing_policy'],'tax_scope':q['tax_scope'],'independently_verified':False}
        details.append({'line_key':key,'label':q['label'],'quantity':qty,'quantity_basis':q['quantity_basis'],
                        'unit_rate_lkr':q['unit_rate_lkr'],'increase_pct':q['increase_pct'],'gross_total_lkr':amount,**evidence[key]})
    total=cash(sum(Decimal(str(v)) for v in lines.values()));reserve=cash(total*service.config['assumptions']['reserve_ratio'])
    receipts=inputs['retained_receipts_lkr'];profit=cash(receipts-total);margin=100*profit/receipts
    plan.update(origin='hybrid_declared_quotes_and_reference_assumptions',line_items_lkr=lines,total_cost_lkr=total,expected_profit_lkr=profit,expected_margin_pct=margin,
                reserve_lkr=reserve,budget_headroom_lkr=inputs['target_budget_lkr']-total,
                budget_feasible=total<=inputs['target_budget_lkr'],affordable_after_reserve=total+reserve<=inputs['target_budget_lkr'],
                margin_feasible=margin>=inputs['min_profit_margin_pct'],
                recommended_client_price_excluding_output_tax_lkr=cash((total+reserve)/(1-inputs['min_profit_margin_pct']/100)),
                line_evidence=evidence,quote_line_details=details,removed_quote_ids=removed,
                warnings=base['warnings']+['Active quotation changes are outside the frozen model training rules; classifier/SHAP outputs withheld.',
                                           'Declared cancellation charges are retained; unresolved committed-service cancellation terms block the total.'])
    c,r=common;cost=np.zeros(len(c))
    for key,amount in lines.items():
        multiplier=np.ones(len(c)) if evidence[key]['pricing_policy']=='locked' else c
        cost+=np.round(amount*multiplier,2)
    cost=np.round(cost,2);real_receipts=np.round(receipts*r,2);real_margin=100*(real_receipts-cost)/real_receipts
    mc={'origin':'conditional_experimental_shocks_with_declared_price_locks','cost_lkr':summary(cost),
        'overrun_frequency':float(np.mean(cost>inputs['target_budget_lkr'])),
        'margin_risk_frequency':float(np.mean(real_margin<inputs['min_profit_margin_pct'])),
        'draws':draws,'seed':seed,'real_world_calibrated':False}
    cover=min(1,inputs['target_budget_lkr']/(total+reserve)) if total+reserve>0 else 1
    m=inputs['min_profit_margin_pct'];margin_cover=min(1,max(0,margin/m)) if m>0 else float(margin>=0)
    result.update(status='calculated',plan=plan,monte_carlo=mc,draft_planning_health={
                    'score_points':100*min(cover,margin_cover),'origin':'draft_planning_coverage','validated':False},
                  model_scores={'Budget_Overrun':None,'Profit_Margin_Risk':None},shap_drivers=None,
                  model_support={'reason':'quote_changes_outside_frozen_model_rule_regime','retraining_required_for_claimed_new_regime_accuracy':True},
                  actions=actions(inputs,plan),quote_change_status='recalculated_with_declared_quotes')
    return result,cost


def actions(inputs,plan):
    required=cash(max(0,plan['recommended_client_price_excluding_output_tax_lkr']-inputs['retained_receipts_lkr']))
    allowance=cash(max(0,plan['total_cost_lkr']+plan['reserve_lkr']-inputs['target_budget_lkr']))
    return [{'action':'additional_client_payment_to_meet_margin_with_reserve','amount_lkr':required},
            {'action':'additional_cost_allowance_to_cover_cost_and_reserve','amount_lkr':allowance},
            {'action':'review_uncommitted_optional_services_or_obtain_requotation','amount_lkr':None}]


class PlannerServices:
    def __init__(self,service=None):
        if service is None:
            from .lkr_inference import LKRResearchInference
            service=LKRResearchInference()
        self.service=service

    def request(self,payload):
        if not isinstance(payload,dict) or set(payload)-{'baseline','alternative','draws','seed'}:
            raise ValueError('unknown_planner_fields')
        draws=payload.get('draws',2000);seed=payload.get('seed',20261014)
        common=shocks(self.service.config,draws,seed)
        b,bc=evaluate_state(self.service,payload.get('baseline'),draws,seed,common)
        a,ac=evaluate_state(self.service,payload.get('alternative'),draws,seed,common)
        delta=None
        if bc is not None and ac is not None:
            delta={'cost_lkr':cash(a['plan']['total_cost_lkr']-b['plan']['total_cost_lkr']),
                   'profit_lkr':cash(a['plan']['expected_profit_lkr']-b['plan']['expected_profit_lkr']),
                   'margin_pct_points':a['plan']['expected_margin_pct']-b['plan']['expected_margin_pct'],
                   'line_changes_lkr':{k:cash(a['plan']['line_items_lkr'].get(k,0)-b['plan']['line_items_lkr'].get(k,0))
                                       for k in sorted(set(a['plan']['line_items_lkr'])|set(b['plan']['line_items_lkr']))},
                   'paired_simulated_cost_difference_lkr':summary(ac-bc)}
        return {'version':'planner-services.2.1','currency':'LKR','baseline':b,'alternative':a,'delta':delta,
                'provenance':{'origin':'research_calculator_plus_declared_quotes','model_run':self.service.metadata['run_id'],
                              'configuration_sha256':self.service.config_hash,'live_vendor_fetch':False,
                              'independent_quote_verification':False,'models_or_datasets_modified':False}}


def report_text(response):
    # Narrative depends only on calculated results; no LLM or invented advice.
    out=['EVENT CHANGE REPORT (LKR)','Prices/assumptions and model applicability are shown separately.']
    for name in ('baseline','alternative'):
        r=response[name];out+=['',name.upper()+': '+r['status']]
        if r['status']!='calculated':
            out+=['Required action: '+reason for reason in r['blockers']];continue
        p=r['plan'];out+= [f"Estimated cost: LKR {p['total_cost_lkr']:,.2f}",
                          f"Expected retained client payment: LKR {p['retained_receipts_lkr']:,.2f}",
                          f"Expected profit: LKR {p['expected_profit_lkr']:,.2f}; margin: {p['expected_margin_pct']:.2f}%",
                          f"Reserve earmark: LKR {p['reserve_lkr']:,.2f}; budget headroom: LKR {p['budget_headroom_lkr']:,.2f}",
                          f"Budget / reserve / margin checks: {p['budget_feasible']} / {p['affordable_after_reserve']} / {p['margin_feasible']}",
                          f"Draft planning coverage: {r['draft_planning_health']['score_points']:.2f}/100 (not validated health)"]
        out+= [f"  {k}: LKR {v:,.2f}" for k,v in p['line_items_lkr'].items()]
        for detail in p.get('quote_line_details',[]):
            out.append(f"Quote {detail['quote_id']}: {detail['evidence_ref']} ({detail['origin']}; {detail['tax_scope']}; {detail['pricing_policy']})")
        out.append('Model scores: '+json_scores(r['model_scores']))
        out.append(f"Hypothetical simulation overrun frequency: {100*r['monte_carlo']['overrun_frequency']:.2f}%")
        for action in r.get('actions',[]):
            out.append(action['action']+(': amount requires a quote' if action['amount_lkr'] is None else f": LKR {action['amount_lkr']:,.2f}"))
        out+= ['Note: '+warning for warning in p['warnings']]
    if response['delta'] is not None:
        out+=['',f"CLIENT CHANGE COST: LKR {response['delta']['cost_lkr']:+,.2f}",
              f"PROFIT EFFECT: LKR {response['delta']['profit_lkr']:+,.2f}",
              f"MARGIN EFFECT: {response['delta']['margin_pct_points']:+.2f} percentage points"]
    else:out.append('\nComparison unavailable: resolve the blocked/unpriced configuration first.')
    return '\n'.join(out)+'\n'


def json_scores(scores):
    import json
    return json.dumps(scores,allow_nan=False)+' (uncalibrated if present; unavailable for unsupported quote changes)'
