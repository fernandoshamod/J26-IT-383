"""Provisional rule engine. Live calculation fails closed; fixtures are explicit tests."""
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
import hashlib, json, math
from datetime import date

RULE_VERSION='0.1.0-review'
FORMULA_IDS=['A001','A007','A008','A009','A010','A011','A012','A013','A014','A015','A020','A021','A022','A023','A024','A027','A028','A029','A033']
PARAMS=['guest_count','seated_share','vip_seats','seats_per_table','vip_tables','event_hours','setup_hours','clearance_hours',
        'venue_area_m2','excluded_area_m2','area_per_standard_seat_m2','area_per_vip_seat_m2','stage_width_m','stage_length_m',
        'service_area_m2','circulation_area_m2','capacity_persons','base_staff','guests_per_staff','extra_general_staff',
        'regular_paid_hours_limit','overtime_multiplier','initial_budget_lkr','expected_receipts_lkr','minimum_margin_points','reserve_ratio']
RATE_UNITS={'catering':'LKR/person','chairs':'LKR/chair','tables':'LKR/table','stage':'LKR/m2','av':'LKR/kit',
            'lighting':'LKR/kit','labour':'LKR/person-hour','venue_fixed':'LKR/booking','venue_hourly':'LKR/hour',
            'security':'LKR/booking','decoration':'LKR/booking','transport':'LKR/booking','misc':'LKR/booking','equipment_other':'LKR/booking'}
CATEGORIES={'catering':'catering','chairs':'equipment_rental','tables':'equipment_rental','stage':'equipment_rental',
            'av':'av','lighting':'lighting','labour':'labour','venue_fixed':'venue_rental','venue_hourly':'venue_rental',
            'security':'security','decoration':'decoration','transport':'transport','misc':'misc','equipment_other':'equipment_rental'}

def money(value):
    return Decimal(str(value)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)

def number(value):
    return not isinstance(value,bool) and isinstance(value,(int,float,Decimal)) and math.isfinite(float(value))

def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def formula_review_errors(config):
    result=[]
    for aid in FORMULA_IDS:
        a=config.get('formula_approvals',{}).get(aid)
        if not isinstance(a,dict) or a.get('status')!='approved' or not all(a.get(k) for k in ['reviewer','reviewer_role','reviewed_at','rationale','evidence_ref']):
            result.append(f'formula_approval:{aid}')
    return result

def parameter_payload(profile):
    return {k:profile.get(k) for k in ['parameters','rates','billing','av_steps','lighting_steps','approved_override_bounds']}

def step_units(area,steps):
    """Reviewed packages may stay unchanged until their own breakpoint is crossed."""
    if not isinstance(steps,list) or not steps:raise ValueError('missing_step_schedule')
    limits=[]
    for row in steps:
        limit=row.get('max_stage_area_m2');units=row.get('units')
        if not number(limit) or limit<=0 or not number(units) or units<0 or int(units)!=units:raise ValueError('invalid_step_schedule')
        limits.append(limit)
    if any(b<=a for a,b in zip(limits,limits[1:])):raise ValueError('step_limits_not_strictly_increasing')
    for row in steps:
        if area<=row['max_stage_area_m2']:return int(row['units'])
    raise ValueError('stage_exceeds_reviewed_package_scope')

def risk_labels(cost,revenue,budget,required_margin,injected_vendor_regime=None):
    """Arithmetic only; caller must provide outcome origin separately."""
    valid=lambda x:number(x) and x>=0
    overrun=None if not(valid(cost) and valid(budget)) else int(money(cost)>money(budget))
    profit=None if not(valid(cost) and valid(revenue)) else float(money(revenue)-money(cost))
    margin=None if profit is None or revenue<=0 else 100*profit/float(revenue)
    risk=None if margin is None or not number(required_margin) or not 0<=required_margin<=100 else int(margin<required_margin)
    anomaly=int(injected_vendor_regime) if isinstance(injected_vendor_regime,bool) else None
    return {'Budget_Overrun':overrun,'Profit_Margin_Risk':risk,'Vendor_Cost_Anomaly':anomaly,
            'Profit':profit,'Profit_Margin':margin}

def evaluate(config,event_type,overrides=None,*,mode='live',outcome=None):
    if mode not in {'live','mock_test_fixture'}:raise ValueError('unsupported_mode')
    response={'api_version':'0.1.0','status':'blocked','event_type':event_type,
              'provenance':{'result_kind':'mock_test_fixture' if mode=='mock_test_fixture' else 'deterministic_rule_estimate',
                            'is_trained_model_prediction':False,'model_version':None,'rules_version':RULE_VERSION,
                            'config_version':config.get('config_version'),'config_sha256':fingerprint(config),
                            'warning':'TEST VALUES ONLY — NOT MARKET DATA OR TRAINED PREDICTIONS' if mode=='mock_test_fixture' else 'Provisional rules; approval and evidence required'},
              'costs':None,'budget_constraints':None,'risk_indicators':None,'spatial':None,'operations':None,
              'outcome_labels':{'Budget_Overrun':None,'Profit_Margin_Risk':None,'Vendor_Cost_Anomaly':None,'label_origin':'unavailable'},
              'financial_health_score':None,'blockers':[]}
    if event_type not in {'Wedding','Corporate'} or event_type not in config.get('archetypes',{}):
        response['blockers']=['unsupported_event_type'];return response
    profile=config['archetypes'][event_type];p=deepcopy(profile.get('parameters',{}))
    if overrides:
        unknown=set(overrides)-set(PARAMS)
        if unknown:response['blockers']=[f'unsupported_override:{x}' for x in sorted(unknown)];return response
        p.update(overrides)
    errors=[]
    if config.get('rules_version')!=RULE_VERSION:errors.append('rules_version_mismatch')
    if mode=='mock_test_fixture':
        if config.get('record_kind')!='mock_test_fixture':errors.append('fixture_configuration_marker_required')
    else:
        if config.get('record_kind')=='mock_test_fixture':errors.append('mock_config_forbidden_in_live_mode')
        errors.extend(formula_review_errors(config))
        approval=profile.get('parameter_approval',{})
        if not isinstance(approval,dict) or approval.get('status')!='approved' or not all(approval.get(k) for k in ['reviewer','reviewer_role','reviewed_at','rationale','evidence_ref','parameter_hash']):errors.append('parameter_approval_missing')
        elif approval['parameter_hash']!=fingerprint(parameter_payload(profile)):errors.append('parameter_approval_hash_mismatch')
        # Overrides themselves require approved bounds, not just a signed baseline.
        for k,v in (overrides or {}).items():
            bounds=profile.get('approved_override_bounds',{}).get(k)
            if not isinstance(bounds,dict) or not all(number(bounds.get(x)) for x in ['min','max']) or not number(v) or not bounds['min']<=v<=bounds['max']:errors.append(f'override_outside_approved_scope:{k}')
    for k in PARAMS:
        if not number(p.get(k)):errors.append(f'missing_or_invalid_parameter:{k}')
    billing=profile.get('billing',{})
    if billing.get('catering_mode')!='package':errors.append('poc_requires_explicit_package_catering')
    if billing.get('staff_scope')!='general_staff_excludes_vendor_packages':errors.append('staff_bundle_scope_unresolved')
    included=billing.get('included_items')
    if not isinstance(included,dict):errors.append('bundle_inclusions_unresolved');included={}
    for item,bundle in included.items():
        if item not in RATE_UNITS or bundle not in RATE_UNITS or item==bundle or bundle in included:errors.append(f'invalid_bundle_reference:{item}')
    rates=profile.get('rates',{})
    for k,unit in RATE_UNITS.items():
        if k in included:continue
        r=rates.get(k,{})
        if not number(r.get('rate')) or r['rate']<0:errors.append(f'missing_or_invalid_rate:{k}')
        if r.get('unit')!=unit:errors.append(f'rate_unit_mismatch:{k}')
        if r.get('currency')!='LKR':errors.append(f'currency_not_LKR:{k}')
        if not r.get('quote_date') or not r.get('evidence_ref'):errors.append(f'rate_evidence_missing:{k}')
        else:
            try:date.fromisoformat(r['quote_date'])
            except (ValueError,TypeError):errors.append(f'invalid_quote_date:{k}')
        if r.get('tax_scope') not in {'inclusive','exclusive'} or not number(r.get('tax_rate_points')) or not 0<=r['tax_rate_points']<=100:errors.append(f'tax_scope_unresolved:{k}')
        if mode=='live' and r.get('approval_status')!='approved':errors.append(f'rate_unapproved:{k}')
    if errors:response['blockers']=sorted(set(errors));return response
    for k,v in p.items():
        if k in PARAMS and v<0:errors.append(f'negative_parameter:{k}')
    for k in ['guest_count','seats_per_table','capacity_persons','guests_per_staff','event_hours','area_per_standard_seat_m2','area_per_vip_seat_m2']:
        if p[k]<=0:errors.append(f'nonpositive_parameter:{k}')
    for k in ['guest_count','vip_seats','seats_per_table','vip_tables','capacity_persons','base_staff','extra_general_staff']:
        if int(p[k])!=p[k]:errors.append(f'noninteger_count:{k}')
    if not 0<=p['seated_share']<=1:errors.append('seated_share_out_of_bounds')
    if not 0<=p['reserve_ratio']<=1:errors.append('reserve_ratio_out_of_bounds')
    if not 0<=p['minimum_margin_points']<=100:errors.append('margin_policy_out_of_bounds')
    if p['overtime_multiplier']<1:errors.append('overtime_multiplier_below_one')
    if errors:response['blockers']=errors;return response
    seats=math.ceil(p['seated_share']*p['guest_count']);vip=p['vip_seats'];usable=p['venue_area_m2']-p['excluded_area_m2'];stage=p['stage_width_m']*p['stage_length_m']
    used=(seats-vip)*p['area_per_standard_seat_m2']+vip*p['area_per_vip_seat_m2']+stage+p['service_area_m2']+p['circulation_area_m2']
    if not 0<=vip<=seats<=p['guest_count']:errors.append('invalid_seating_or_vip_counts')
    if vip>p['vip_tables']*p['seats_per_table']:errors.append('vip_tables_insufficient_for_seats')
    if not 0<usable<=p['venue_area_m2']:errors.append('invalid_usable_area')
    if used>usable:errors.append('used_area_exceeds_usable_area')
    if p['guest_count']>p['capacity_persons']:errors.append('guest_count_exceeds_arrangement_capacity')
    try:av=step_units(stage,profile.get('av_steps'));lighting=step_units(stage,profile.get('lighting_steps'))
    except ValueError as e:errors.append(str(e));av=lighting=None
    if errors:response['blockers']=errors;return response
    tables=math.ceil((seats-vip)/p['seats_per_table'])+p['vip_tables']
    staff=p['base_staff']+math.ceil(p['guest_count']/p['guests_per_staff'])+p['extra_general_staff']
    hours=p['event_hours']+p['setup_hours']+p['clearance_hours'];regular=min(hours,p['regular_paid_hours_limit']);overtime=max(0,hours-regular)
    quantities={'catering':p['guest_count'],'chairs':seats,'tables':tables,'stage':stage,'av':av,'lighting':lighting,
                'labour':staff*(regular+overtime*p['overtime_multiplier']),'venue_hourly':p['event_hours']}
    ledger=[]
    for k in RATE_UNITS:
        qty=quantities.get(k,1)
        if k in included:
            ledger.append({'item_id':k,'category':CATEGORIES[k],'quantity':qty,'unit':RATE_UNITS[k],'rate_lkr':None,'net_lkr':0.0,'tax_lkr':0.0,'gross_lkr':0.0,'included_in':included[k]});continue
        r=rates[k];base=Decimal(str(qty))*Decimal(str(r['rate']));t=Decimal(str(r['tax_rate_points']))/100
        gross=money(base*(1+t)) if r['tax_scope']=='exclusive' else money(base)
        net=money(base) if r['tax_scope']=='exclusive' else money(base/(1+t))
        ledger.append({'item_id':k,'category':CATEGORIES[k],'quantity':qty,'unit':r['unit'],'rate_lkr':r['rate'],'net_lkr':float(net),'tax_lkr':float(gross-net),
                       'gross_lkr':float(gross),'included_in':None,'evidence_ref':r['evidence_ref'],'tax_scope':r['tax_scope']})
    total=sum((money(l['gross_lkr']) for l in ledger),Decimal(0));reserve=money(total*Decimal(str(p['reserve_ratio'])));budget=money(p['initial_budget_lkr']);receipts=money(p['expected_receipts_lkr'])
    if budget<reserve:response['blockers']=['budget_below_contingency_reserve'];return response
    expected=receipts-total;margin=None if receipts<=0 else float(100*expected/receipts)
    response.update(status='calculated',costs={'currency':'LKR','estimate_lkr':float(total),'estimate_kind':'mock_test_rule_estimate' if mode=='mock_test_fixture' else 'deterministic_rule_estimate','uncertainty_interval':None,'line_items':ledger},
                    budget_constraints={'initial_budget_lkr':float(budget),'contingency_reserve_lkr':float(reserve),'operating_allowance_lkr':float(budget-reserve),'headroom_lkr':float(budget-total),'reserve_is_expense':False},
                    risk_indicators={'planned_budget_breach':total>budget,'planned_operating_allowance_breach':total>budget-reserve,'expected_profit_lkr':float(expected),'expected_margin_points':margin,
                                     'minimum_margin_points':p['minimum_margin_points'],'planned_margin_shortfall':None if margin is None else margin<p['minimum_margin_points'],'predicted_probabilities':None},
                    spatial={'usable_area_m2':usable,'used_area_m2':used,'stage_area_m2':stage,'space_utilization':used/usable,'planned_seats':seats,'capacity_persons':p['capacity_persons'],'layout_origin':'mock_test_fixture' if mode=='mock_test_fixture' else 'declared_reviewed_input','safety_certification':False},
                    operations={'general_staff_count':staff,'person_hours':staff*hours,'overtime_person_hours':staff*overtime,'furniture_tables':tables,'av_kits':av,'lighting_kits':lighting})
    if outcome is not None:
        if mode!='mock_test_fixture':raise ValueError('outcomes_not_accepted_by_planning_api')
        labels=risk_labels(outcome.get('cost_lkr'),outcome.get('receipts_lkr'),float(budget),p['minimum_margin_points'],outcome.get('injected_vendor_regime'))
        response['outcome_labels']={**labels,'label_origin':'mock_test_fixture'}
    return response

def what_if(config,event_type,changes,*,mode='live'):
    baseline=evaluate(config,event_type,mode=mode);alternative=evaluate(config,event_type,changes,mode=mode)
    valid=baseline['status']==alternative['status']=='calculated'
    return {'api_version':'0.1.0','comparison_kind':'paired_deterministic_what_if','is_trained_model_prediction':False,
            'changes':changes,'baseline':baseline,'alternative':alternative,
            'comparison_status':'comparable' if valid else 'blocked',
            'delta':None if not valid else {'estimated_cost_lkr':float(money(alternative['costs']['estimate_lkr'])-money(baseline['costs']['estimate_lkr'])),
                                           'expected_profit_lkr':float(money(alternative['risk_indicators']['expected_profit_lkr'])-money(baseline['risk_indicators']['expected_profit_lkr'])),
                                           'used_area_m2':alternative['spatial']['used_area_m2']-baseline['spatial']['used_area_m2']}}
