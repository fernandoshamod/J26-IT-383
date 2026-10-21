"""Separate monetary research calculator; not a conversion of unitless models."""
from copy import deepcopy
import csv
import json
import math
from pathlib import Path
import numpy as np
from .engine import fingerprint
from .release_input import sha256

ROOT=Path(__file__).resolve().parents[1]
VERSION='lkr_research_v2_0_20261014'
FEATURES=['Guest_Count','Event_Hours','Venue_Area_m2','Seating_Count','Stage_Area_m2',
          'Space_Utilization','Quoted_Catering_LKR','Quoted_AV_LKR','Quoted_Venue_LKR',
          'Quoted_Equipment_LKR','Staff_Count','Paid_Person_Hours','Quoted_Labour_LKR',
          'Target_Budget_LKR','Retained_Receipts_LKR','Contingency_Reserve_LKR',
          'Minimum_Margin_Pct','Planned_Total_Cost_LKR','Reference_Rate_LKR_Per_Person',
          'Event_Type_Wedding','Event_Type_Corporate']
INPUTS={'event_type','guests','event_hours','stage_width_m','stage_length_m','venue_area_m2',
        'target_budget_lkr','retained_receipts_lkr','min_profit_margin_pct','reference_id'}
TARGETS=('Budget_Overrun','Profit_Margin_Risk')


def load_config():
    config=json.loads((ROOT/'config/lkr_research.v2.0.json').read_text())
    path=ROOT/config['source_file']
    if sha256(path)!=config['source_sha256']:raise ValueError('source_evidence_hash_mismatch')
    evidence=json.loads(path.read_text())
    if not math.isclose(sum(config['package_allocation'].values()),1.,abs_tol=1e-12):
        raise ValueError('package_allocation_must_sum_to_one')
    if any(v<0 or not math.isfinite(v) for v in config['package_allocation'].values()):
        raise ValueError('invalid_package_allocation')
    return config,evidence


def validate_inputs(config,inputs):
    if not isinstance(inputs,dict) or set(inputs)!=INPUTS:raise ValueError('exact_planning_fields_required')
    event=inputs['event_type']
    if event not in config['allowed_reference_ids']:raise ValueError('unsupported_event_type')
    if inputs['reference_id'] not in config['allowed_reference_ids'][event]:raise ValueError('reference_profile_event_mismatch')
    for name in INPUTS-{'event_type','reference_id'}:
        value=inputs[name]
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ValueError('finite_number_required:'+name)
    if type(inputs['guests']) is not int:raise ValueError('guest_count_must_be_integer')
    mapping={'guests':'guest_count','event_hours':'event_hours','stage_width_m':'stage_width_m',
             'stage_length_m':'stage_length_m','venue_area_m2':'venue_area_m2','min_profit_margin_pct':'min_profit_margin_pct'}
    for name,domain in mapping.items():
        lo,hi=config['domains'][domain]
        if not lo<=inputs[name]<=hi:raise ValueError('outside_calculator_domain:'+name)
    if inputs['target_budget_lkr']<=0 or inputs['retained_receipts_lkr']<=0:
        raise ValueError('budget_and_receipts_must_be_positive')
    if (inputs['stage_width_m']==0)!=(inputs['stage_length_m']==0):raise ValueError('removed_stage_requires_both_dimensions_zero')


def calculate(config,evidence,inputs):
    validate_inputs(config,inputs)
    a=config['assumptions'];event=inputs['event_type'];g=inputs['guests']
    rows=[r for r in evidence['rates'] if r['Evidence_ID']==inputs['reference_id']]
    if len(rows)!=1:raise ValueError('missing_or_duplicate_reference')
    source=rows[0]
    if source['Currency']!='LKR' or source['Rate_Unit']!='person':raise ValueError('reference_unit_mismatch')
    rate=float(source['Rate_LKR'])
    stage=inputs['stage_width_m']*inputs['stage_length_m']
    area=g*a['seat_area_m2']+a['fixed_service_circulation_area_m2']+stage
    if area>inputs['venue_area_m2']:raise ValueError('spatially_infeasible')
    staff=a['base_staff']+math.ceil(g/a['guests_per_staff'])
    hours=inputs['event_hours']+a['setup_clearance_hours']
    paid=lambda h:min(h,a['regular_paid_hours'])+max(0,h-a['regular_paid_hours'])*a['overtime_multiplier']
    extra_hours=max(0,paid(hours)-paid(a['included_event_hours']+a['setup_clearance_hours']))
    kits=max(1,math.ceil(stage/a['included_stage_area_m2'])) if stage else 0
    base=g*rate
    # Allocate once, then charge ONLY incremental hypothetical extras above the included scope.
    allocation={k:base*v for k,v in config['package_allocation'].items()}
    extras={k:0. for k in allocation}
    extras['stage']=max(0,stage-a['included_stage_area_m2'])*a['stage_increment_lkr_per_m2']['value']
    extras['av']=max(0,kits-1)*a['av_increment_lkr_per_kit']['value']
    extras['labour']=staff*extra_hours*a['labour_increment_lkr_per_person_hour']['value']
    extras['venue']=max(0,inputs['event_hours']-a['included_event_hours'])*a['venue_increment_lkr_per_hour']['value']
    if event=='Wedding':
        # Unbundled generic wedding: published menu anchors food only, never a complete hotel quote.
        allocation={'catering':base,'chairs':g*a['chair_lkr_per_person']['value'],
                    'tables':math.ceil(g/a['seats_per_table'])*a['table_lkr_per_table']['value'],
                    'stage':stage*a['stage_increment_lkr_per_m2']['value'],
                    'av':kits*a['av_increment_lkr_per_kit']['value'],
                    'labour':staff*paid(hours)*a['labour_increment_lkr_per_person_hour']['value'],
                    'venue':a['venue_fixed_lkr']['value']}
        extras={k:0. for k in allocation}
        extras['venue']=max(0,inputs['event_hours']-a['included_event_hours'])*a['venue_increment_lkr_per_hour']['value']
    factor=(1+a['wedding_service_fraction'])*(1+a['wedding_tax_fraction']) if event=='Wedding' else 1.
    line_items={k:round((allocation[k]+extras[k])*factor,2) for k in allocation}
    total=round(sum(line_items.values()),2)
    reserve=round(total*a['reserve_ratio'],2)
    receipts=inputs['retained_receipts_lkr'];profit=round(receipts-total,2)
    margin=100*profit/receipts
    return {'currency':'LKR','origin':'evidence_anchored_synthetic_estimate_not_confirmed_quote',
            'line_items_lkr':line_items,'reference_allocation_before_charges_lkr':allocation,
            'assumed_incremental_extras_before_charges_lkr':extras,'assumed_charge_factor':factor,
            'total_cost_lkr':total,'retained_receipts_lkr':receipts,'expected_profit_lkr':profit,
            'expected_margin_pct':margin,'reserve_lkr':reserve,'budget_headroom_lkr':inputs['target_budget_lkr']-total,
            'budget_feasible':total<=inputs['target_budget_lkr'],
            'affordable_after_reserve':total+reserve<=inputs['target_budget_lkr'],
            'margin_feasible':margin>=inputs['min_profit_margin_pct'],
            'recommended_client_price_excluding_output_tax_lkr':round((total+reserve)/(1-inputs['min_profit_margin_pct']/100),2),
            'stage_area_m2':stage,'used_area_m2':area,'space_utilization':area/inputs['venue_area_m2'],
            'seats':g,'tables':math.ceil(g/a['seats_per_table']),'staff':staff,
            'paid_person_hours':staff*hours,'reference_rate_lkr_per_person':rate,
            'source_reference':deepcopy(source),'confirmed_all_in_market_quote':False,
            'warnings':['Published rates are reference anchors, not signed or availability-confirmed quotes.',
                        'Component allocations, marginal rates, geometry and unknown tax treatment are experimental assumptions.',
                        'Package removal does not automatically discount included services; requotation may be needed.']}


def features(inputs,plan):
    l=plan['line_items_lkr']
    values=[inputs['guests'],inputs['event_hours'],inputs['venue_area_m2'],plan['seats'],plan['stage_area_m2'],
            plan['space_utilization'],l['catering'],l['av'],l['venue'],l['chairs']+l['tables']+l['stage'],
            plan['staff'],plan['paid_person_hours'],l['labour'],inputs['target_budget_lkr'],
            inputs['retained_receipts_lkr'],plan['reserve_lkr'],inputs['min_profit_margin_pct'],
            plan['total_cost_lkr'],plan['reference_rate_lkr_per_person'],int(inputs['event_type']=='Wedding'),int(inputs['event_type']=='Corporate')]
    if not all(math.isfinite(v) for v in values):raise ValueError('nonfinite_feature_projection')
    return dict(zip(FEATURES,values))


def shocks(config,draws,seed):
    if type(draws) is not int or not 1<=draws<=10000 or type(seed) is not int or not 0<=seed<2**32:
        raise ValueError('invalid_random_controls')
    rng=np.random.Generator(np.random.PCG64(seed));a=config['assumptions']
    return rng.uniform(*a['ordinary_cost_multiplier'],draws),rng.uniform(*a['receipt_multiplier'],draws)


def realized(inputs,plan,draw):
    c,r=draw
    lines={k:round(v*c,2) for k,v in plan['line_items_lkr'].items()}
    cost=round(sum(lines.values()),2);receipts=round(inputs['retained_receipts_lkr']*r,2)
    profit=round(receipts-cost,2);margin=100*profit/receipts
    return {'simulated_final_cost_lkr':cost,'simulated_receipts_lkr':receipts,'simulated_profit_lkr':profit,
            'simulated_margin_pct':margin,'realized_line_items_lkr':lines,
            'Budget_Overrun':int(cost>inputs['target_budget_lkr']),
            'Profit_Margin_Risk':int(margin<inputs['min_profit_margin_pct'])}


def generate(config,evidence):
    settings=config['generation'];rng=np.random.Generator(np.random.PCG64(settings['seed']))
    n=settings['root_families']
    if n%2 or n!=sum(settings['split_root_counts'].values()):raise ValueError('invalid_family_counts')
    # Balanced event-type allocation is diagnostic design, not population prevalence.
    assignments={};offset=0
    for event in ('Wedding','Corporate'):
        ids=rng.permutation(np.arange(offset,offset+n//2));start=0
        for split,count in settings['split_root_counts'].items():
            if count%2:raise ValueError('even_split_counts_required')
            for root in ids[start:start+count//2]:assignments[int(root)]=split
            start+=count//2
        offset+=n//2
    rows=[];ledger=[];provenance=[]
    for root in range(n):
        event='Wedding' if root<n//2 else 'Corporate'
        family=f'LKR2-ROOT-{root:05d}'
        base={'event_type':event,'guests':int(rng.integers(60,361)),
              'event_hours':round(float(rng.uniform(2,10)),3),
              'stage_width_m':round(float(rng.uniform(2,8)),3),'stage_length_m':round(float(rng.uniform(2,8)),3),
              'venue_area_m2':round(float(rng.uniform(800,1400)),3),
              'target_budget_lkr':1e6,'retained_receipts_lkr':2e6,
              'min_profit_margin_pct':float(rng.choice([10,15,20,25])),
              'reference_id':str(rng.choice(config['allowed_reference_ids'][event]))}
        p=calculate(config,evidence,base)
        base['target_budget_lkr']=round(p['total_cost_lkr']*rng.uniform(*settings['budget_factor_range']),2)
        margin=rng.uniform(*settings['expected_margin_range'])
        base['retained_receipts_lkr']=round(p['total_cost_lkr']/(1-margin),2)
        common=shocks(config,settings['outcome_replications'],int(rng.integers(2**32)))
        states=[base,{**base,'guests':min(500,base['guests']+20)},
                {**base,'stage_width_m':base['stage_width_m']+1,'event_hours':base['event_hours']+1}]
        for state,inputs in enumerate(states):
            plan=calculate(config,evidence,inputs);f=features(inputs,plan)
            for replication in range(settings['outcome_replications']):
                outcome=realized(inputs,plan,(common[0][replication],common[1][replication]))
                sid=f'{family}-P{state}-R{replication}'
                rows.append({'Scenario_ID':sid,'Base_Event_ID':family,'split_group_id':family,'split':assignments[root],
                             'planning_state':state,'outcome_replication':replication,**f,
                             **{k:v for k,v in outcome.items() if k!='realized_line_items_lkr'}})
                provenance.append({'Scenario_ID':sid,'Base_Event_ID':family,'origin':'evidence_anchored_synthetic_LKR_not_observed_event',
                                   'reference_id':inputs['reference_id'],'source_url':plan['source_reference']['Source_URL'],
                                   'configuration_sha256':fingerprint(config),'rule_version':config['version'],
                                   'planning_inputs_json':json.dumps(inputs,sort_keys=True),'source_access_date':evidence['access_date'],
                                   'source_sha256':config['source_sha256'],'shared_template_scope':'generic_hypothetical_shared_rules_not_unseen_provider_evaluation'})
                for k,value in plan['line_items_lkr'].items():
                    ledger.append({'Scenario_ID':sid,'service':k,'currency':'LKR','planned_lkr':value,
                                   'simulated_realized_lkr':outcome['realized_line_items_lkr'][k],
                                   'rate_status':'synthetic_allocation_plus_assumed_extras_of_published_reference'})
    return rows,ledger,provenance


def validate_dataset(rows,ledger,provenance):
    ids=set();family_splits={};feature_splits={};by_id={r['Scenario_ID']:r for r in rows}
    if len(by_id)!=len(rows):raise ValueError('duplicate_scenario_id')
    for row in rows:
        sid=row['Scenario_ID'];ids.add(sid);split=row['split']
        if split not in ('train','validation','test'):raise ValueError('invalid_split')
        family_splits.setdefault(row['Base_Event_ID'],set()).add(split)
        key=tuple(row[f] for f in FEATURES);feature_splits.setdefault(key,set()).add(split)
        if not all(math.isfinite(v) for v in key):raise ValueError('nonfinite_features')
        if row['Space_Utilization']>1:raise ValueError('invalid_geometry')
        cost=row['simulated_final_cost_lkr'];revenue=row['simulated_receipts_lkr']
        if row['Budget_Overrun']!=int(cost>row['Target_Budget_LKR']):raise ValueError('overrun_label_mismatch')
        margin=100*(revenue-cost)/revenue
        if abs(margin-row['simulated_margin_pct'])>1e-7 or row['Profit_Margin_Risk']!=int(margin<row['Minimum_Margin_Pct']):
            raise ValueError('margin_label_mismatch')
        if abs(row['simulated_profit_lkr']-(revenue-cost))>0.011:raise ValueError('profit_reconciliation')
    if any(len(v)>1 for v in family_splits.values()):raise ValueError('family_leakage')
    if any(len(v)>1 for v in feature_splits.values()):raise ValueError('predictor_projection_leakage')
    if len(provenance)!=len(rows) or {p['Scenario_ID'] for p in provenance}!=ids:raise ValueError('provenance_mismatch')
    if any(p['origin']!='evidence_anchored_synthetic_LKR_not_observed_event' for p in provenance):raise ValueError('origin_mismatch')
    totals={sid:[0.,0.,set()] for sid in ids}
    for item in ledger:
        sid=item['Scenario_ID']
        if sid not in totals or item['service'] in totals[sid][2]:raise ValueError('duplicate_or_unknown_line_item')
        totals[sid][0]+=item['planned_lkr'];totals[sid][1]+=item['simulated_realized_lkr'];totals[sid][2].add(item['service'])
    for sid,(planned,actual,services) in totals.items():
        row=by_id[sid]
        if len(services)!=7 or abs(planned-row['Planned_Total_Cost_LKR'])>0.011 or abs(actual-row['simulated_final_cost_lkr'])>0.011:
            raise ValueError('line_item_reconciliation')
    return {'status':'PASS','rows':len(rows),'families':len(family_splits),'feature_vectors':len(feature_splits),
            'cross_split_families':0,'cross_split_predictor_vectors':0,
            'split_rows':{s:sum(r['split']==s for r in rows) for s in ('train','validation','test')},
            'split_families':{s:sum(v=={s} for v in family_splits.values()) for s in ('train','validation','test')},
            'real_observed_event_outcomes':0,'validation_kind':'internal_synthetic_accounting_and_split_checks'}


def defaults(config,event='Wedding'):
    return {'event_type':event,'guests':150,'event_hours':5.,'stage_width_m':4.,'stage_length_m':6.,
            'venue_area_m2':1000.,'target_budget_lkr':2000000.,'retained_receipts_lkr':2500000.,
            'min_profit_margin_pct':15.,'reference_id':config['default_reference_ids'][event]}
