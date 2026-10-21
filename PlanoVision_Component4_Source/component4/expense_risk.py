"""Workflow-aligned features/generator using the existing financial calculator."""
from copy import deepcopy
import json
import math
from pathlib import Path
import numpy as np
from .engine import fingerprint
from .lkr_research import ROOT,FEATURES as CORE_FEATURES,TARGETS,load_config,calculate,features,defaults,shocks
from .lkr_inference import summary
from .planner_services import PlannerServices,actions,cash

RUN_ID='expense_risk_v3_0_20261015'
FEATURES=CORE_FEATURES+['Optional_Expense_Total_LKR','Optional_Expense_Count','Optional_Expense_Fraction',
                       'Planned_Budget_Utilization','Planned_Margin_Buffer_Pct']


def load_design():return json.loads((ROOT/'config/expense_risk.v3.0.json').read_text())


class CalculationOnlyService:
    """No fitted model is called while producing a training configuration."""
    def __init__(self):
        self.config,self.evidence=load_config();self.config_hash=fingerprint(self.config)
        self.metadata={'run_id':'calculation_only_no_predictions'}
    def evaluate(self,inputs,draws=2,seed=20261015,common=None):
        result={'status':'blocked','inputs':deepcopy(inputs),'plan':None,'model_scores':None,'shap_drivers':None,
                'monte_carlo':None,'draft_planning_health':None,'blockers':[]}
        try:plan=calculate(self.config,self.evidence,inputs)
        except ValueError as exc:result['blockers']=[str(exc)];return result,None
        c,r=shocks(self.config,draws,seed) if common is None else common
        costs=np.round(sum(np.round(v*c,2) for v in plan['line_items_lkr'].values()),2)
        revenue=np.round(inputs['retained_receipts_lkr']*r,2)
        margin=100*(revenue-costs)/revenue
        required=inputs['min_profit_margin_pct']
        mc=min(1,max(0,plan['expected_margin_pct']/required)) if required>0 else float(plan['expected_margin_pct']>=0)
        bc=min(1,inputs['target_budget_lkr']/(plan['total_cost_lkr']+plan['reserve_lkr']))
        result.update(status='calculated',plan=plan,model_scores={t:None for t in TARGETS},actions=actions(inputs,plan),
            draft_planning_health={'score_points':100*min(mc,bc),'validated':False,'origin':'draft_planning_coverage'},
            monte_carlo={'origin':'hypothetical_bounded_shocks_not_observed_risk','cost_lkr':summary(costs),
                'overrun_frequency':float(np.mean(costs>inputs['target_budget_lkr'])),
                'margin_risk_frequency':float(np.mean(margin<required)),'draws':draws,'seed':seed,'real_world_calibrated':False})
        return result,costs


def active_estimates(state):
    return [q for q in state['quotes'] if q['id'] not in state['removed_quote_ids']]


def project(state,result):
    """Only planning values; no outcome, shock, family ID or split used as a feature."""
    plan=result['plan'];inputs=state['planning_inputs']
    row=features(inputs,plan)
    active=active_estimates(state)
    total=cash(sum(q['unit_rate_lkr'] for q in active))
    core=plan['total_cost_lkr']-total
    row.update(Optional_Expense_Total_LKR=total,Optional_Expense_Count=len(active),
               Optional_Expense_Fraction=total/core if core>0 else 0,
               Planned_Budget_Utilization=plan['total_cost_lkr']/inputs['target_budget_lkr'],
               Planned_Margin_Buffer_Pct=plan['expected_margin_pct']-inputs['min_profit_margin_pct'])
    if not all(math.isfinite(v) for v in row.values()):raise ValueError('nonfinite_planning_features')
    return row


def support_reasons(design,state,result):
    if result['status']!='calculated':return ['financial_or_spatial_calculation_blocked']
    p=state['planning_inputs'];c=load_config()[0]
    if p['reference_id']!=c['default_reference_ids'][p['event_type']]:return ['unsupported_reference_profile']
    if p['stage_width_m']!=4 or p['stage_length_m']!=6:return ['unsupported_stage_profile']
    reasons=[]
    for q in state['quotes']:
        if q['mode']!='add' or q['source_kind']!='planner_entered_assumption' or q['pricing_policy']!='planning_estimate' or q['quantity_basis']!='booking' or q['committed']:
            reasons.append('unsupported_supplier_quote_replacement_or_contract_regime');break
    f=project(state,result)
    if f['Optional_Expense_Count']>design['support']['max_optional_count']:reasons.append('too_many_optional_expenses')
    if f['Optional_Expense_Fraction']>design['support']['max_optional_fraction_of_core_cost']+1e-9:reasons.append('optional_expense_exposure_outside_design')
    return reasons


def make_estimate(name,amount,index):
    return {'id':f'assumed_{index}','label':name,'mode':'add','service':name,'quantity_basis':'booking',
        'unit_rate_lkr':cash(amount),'tax_scope':'all_in','service_pct':0,'tax_pct':0,
        'pricing_policy':'planning_estimate','increase_pct':0,'source_kind':'planner_entered_assumption',
        'evidence_ref':'Hypothetical total allowance, not a market quotation','valid_from':'2026-10-22','valid_until':'2026-10-22',
        'covers':[name],'committed':False,'cancellation_fee_lkr':0}


def generate(design):
    calc=CalculationOnlyService();planner=PlannerServices(calc);rng=np.random.Generator(np.random.PCG64(design['seed']))
    n=design['root_families'];sam=design['sampling']
    if n%2 or sum(design['split_roots'].values())!=n:raise ValueError('invalid_root_design')
    assignments={}
    for offset in (0,n//2):
        order=rng.permutation(np.arange(offset,offset+n//2));start=0
        for split,count in design['split_roots'].items():
            if count%2:raise ValueError('split_count_must_be_even')
            for i in order[start:start+count//2]:assignments[int(i)]=split
            start+=count//2
    rows=[];ledger=[];provenance=[]
    anchors={}
    for lo,hi in ((0,n//2),(n//2,n)):
        training=sorted(i for i in range(lo,hi) if assignments[i]=='train')
        for index,root in enumerate(training[:2]):anchors[root]=index
    names=['photography','lighting','transport','entertainment','extra_equipment']
    for root in range(n):
        event='Wedding' if root<n//2 else 'Corporate';family=f'ER3-{root:05d}'
        inputs=defaults(calc.config,event);g=int(rng.integers(sam['guests'][0],sam['guests'][1]+1))
        needed=g*calc.config['assumptions']['seat_area_m2']+calc.config['assumptions']['fixed_service_circulation_area_m2']+24
        inputs.update(guests=g,event_hours=round(float(rng.uniform(*sam['hours'])),3),
            venue_area_m2=round(float(rng.uniform(max(sam['venue_area_m2'][0],needed),sam['venue_area_m2'][1])),3),
            min_profit_margin_pct=round(float(rng.uniform(*sam['minimum_margin_pct'])),3))
        if root in anchors:
            end=anchors[root]
            inputs.update(guests=sam['guests'][end],event_hours=sam['hours'][end],
                          venue_area_m2=sam['venue_area_m2'][end],min_profit_margin_pct=sam['minimum_margin_pct'][end])
        core=calculate(calc.config,calc.evidence,inputs)['total_cost_lkr']
        count=int(rng.integers(sam['base_optional_count'][0],sam['base_optional_count'][1]+1))
        choices=rng.permutation(names)
        quotes=[make_estimate(str(choices[j]),core*rng.uniform(*sam['optional_amount_fraction_of_core_cost']),j) for j in range(count+1)]
        original_total=cash(core+sum(q['unit_rate_lkr'] for q in quotes[:count]))
        inputs['target_budget_lkr']=cash(original_total*rng.uniform(*sam['budget_factor_of_original_cost']))
        inputs['retained_receipts_lkr']=cash(original_total/(1-rng.uniform(*sam['expected_margin_fraction'])))
        state={'planning_inputs':inputs,'event_date':'2026-10-22','quotes':quotes[:count],'removed_quote_ids':[]}
        addition=deepcopy(state);addition['quotes'].append(quotes[count])
        removal=deepcopy(state);removal['removed_quote_ids']=[quotes[0]['id']]
        outcome_seed=int(rng.integers(2**32));multipliers=shocks(calc.config,design['outcome_replications'],outcome_seed)
        for state_index,current in enumerate((state,addition,removal)):
            result=planner.request({'baseline':current,'alternative':current,'draws':2,'seed':outcome_seed})['alternative']
            if result['status']!='calculated' or support_reasons(design,current,result):raise ValueError('generated_state_not_supported')
            f=project(current,result);plan=result['plan']
            for rep in range(design['outcome_replications']):
                sid=f'{family}-P{state_index}-R{rep}'
                realized={k:cash(v*multipliers[0][rep]) for k,v in plan['line_items_lkr'].items()}
                actual=cash(sum(realized.values()));receipts=cash(inputs['retained_receipts_lkr']*multipliers[1][rep])
                margin=100*(receipts-actual)/receipts
                rows.append({'Scenario_ID':sid,'Base_Event_ID':family,'split':assignments[root],
                    'planning_state':state_index,'outcome_replication':rep,**f,
                    'simulated_final_cost_lkr':actual,'simulated_receipts_lkr':receipts,
                    'Budget_Overrun':int(actual>inputs['target_budget_lkr']),
                    'Profit_Margin_Risk':int(margin<inputs['min_profit_margin_pct'])})
                provenance.append({'Scenario_ID':sid,'Base_Event_ID':family,'origin':'evidence_anchored_synthetic_not_observed',
                    'state':deepcopy(current),'design_sha256':fingerprint(design),'rule_sha256':calc.config_hash,
                    'outcome_seed':outcome_seed,'source_url':plan['source_reference']['Source_URL'],
                    'source_evidence_id':inputs['reference_id'],'source_sha256':calc.config['source_sha256'],
                    'shared_template_scope':'conditional_simulator_only_not_unseen_venue_or_vendor'})
                for key,value in plan['line_items_lkr'].items():ledger.append({'Scenario_ID':sid,'line_item':key,'planned_lkr':value,'simulated_realized_lkr':realized[key]})
    return rows,ledger,provenance


def audit(rows,ledger,provenance):
    by_id={r['Scenario_ID']:r for r in rows}
    if len(by_id)!=len(rows):raise ValueError('duplicate_scenario')
    roots={};vectors={};totals={sid:[0.,0.,set()] for sid in by_id}
    for r in rows:
        roots.setdefault(r['Base_Event_ID'],set()).add(r['split']);vectors.setdefault(tuple(r[k] for k in FEATURES),set()).add(r['split'])
        if r['Space_Utilization']>1:raise ValueError('invalid_geometry')
        if r['Budget_Overrun']!=int(r['simulated_final_cost_lkr']>r['Target_Budget_LKR']):raise ValueError('overrun_label')
        margin=100*(r['simulated_receipts_lkr']-r['simulated_final_cost_lkr'])/r['simulated_receipts_lkr']
        if r['Profit_Margin_Risk']!=int(margin<r['Minimum_Margin_Pct']):raise ValueError('margin_label')
        if set(FEATURES)&{'simulated_final_cost_lkr','simulated_receipts_lkr','Budget_Overrun','Profit_Margin_Risk','outcome_seed','Base_Event_ID','split'}:raise ValueError('feature_leakage')
    if any(len(s)>1 for s in roots.values()) or any(len(s)>1 for s in vectors.values()):raise ValueError('group_or_predictor_leakage')
    if len(provenance)!=len(rows) or {p['Scenario_ID'] for p in provenance}!=set(by_id):raise ValueError('provenance_missing')
    for item in ledger:
        entry=totals[item['Scenario_ID']]
        if item['line_item'] in entry[2]:raise ValueError('duplicate_charge')
        entry[0]+=item['planned_lkr'];entry[1]+=item['simulated_realized_lkr'];entry[2].add(item['line_item'])
    for sid,(planned,realized,_) in totals.items():
        if abs(planned-by_id[sid]['Planned_Total_Cost_LKR'])>.011 or abs(realized-by_id[sid]['simulated_final_cost_lkr'])>.011:raise ValueError('ledger_reconciliation')
    return {'rows':len(rows),'families':len(roots),'features':len(FEATURES),'planning_vectors':len(vectors),
        'split_rows':{s:sum(r['split']==s for r in rows) for s in ('train','validation','test')},
        'split_roots':{s:sum(v=={s} for v in roots.values()) for s in ('train','validation','test')},
        'cross_split_families':0,'cross_split_feature_vectors':0,'real_observed_event_outcomes':0}
