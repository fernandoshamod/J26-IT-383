"""Read existing artifacts and prepare an evidence audit. No simulation/calibration."""
from pathlib import Path
import csv, json, hashlib, copy
import openpyxl
from component4.engine import PARAMS, RATE_UNITS, FORMULA_IDS, evaluate

ROOT = Path(__file__).resolve().parents[2]
def read_json(p):
    return json.loads((ROOT/p).read_text(encoding='utf-8-sig'))
def read_csv(p):
    with (ROOT/p).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))
def sha(p):
    return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def write_json(p, obj):
    (ROOT/p).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')

raw=read_json('work/public_rate_candidates.json')
config=read_json('config/simulator.v0.1.template.json')
schema=read_json('work/original_schema.json')
dictionary=read_csv('reports/updated_data_dictionary.csv')
assert len(dictionary)==46
assert schema['Master_Data']['data'][0]==[r['Column_Name'] for r in dictionary]
register=openpyxl.load_workbook(ROOT/'reports/simulation_assumption_register.xlsx',read_only=True,data_only=True)
assumptions=list(register['Assumptions'].values)
assert len(assumptions)==35
assert all(r[-1]=='Pending review' for r in assumptions[1:])
quotes=openpyxl.load_workbook(ROOT/'reports/sri_lanka_quotation_collection_template.xlsx',read_only=True,data_only=True)
template_headers=read_json('reports/quotation_template_metadata.json')
for name, headers in template_headers.items():
    assert list(next(quotes[name].values))==headers, name
review=read_json('reports/technical_review_snapshot.json')
assert {'Review_Recommendations','Review_Gates'} <= set(review['sheets'])
notes={p.name:p.read_text(encoding='utf-8-sig') for p in (ROOT/'reports').glob('*.md')}
engine=(ROOT/'component4/engine.py').read_text(encoding='utf-8')
source_observations=read_json('reports/simulation_review_data.json')['Observed_Evidence']

# Typed units, master dependencies, evidence needed. No numeric policy defaults.
spec={
 'guest_count':('persons','Guest_Count','event_brief','Actual event brief and planned attendance; no local guest distribution','A003'),
 'seated_share':('fraction','Seating_Count','policy_choice','Reviewed event arrangement, not population statistic','A005;A008'),
 'vip_seats':('seats','Seating_Count;VIP_Area_m2','event_brief','VIP allocation and seat plan','A008'),
 'seats_per_table':('seats/table','Seating_Count;Quoted_Equipment_Rental_Cost','measured_specification','Table size/arrangement and manufacturer or venue specification','A008;A014'),
 'vip_tables':('tables','Quoted_Equipment_Rental_Cost','event_brief','VIP table plan consistent with seat capacity','A008'),
 'event_hours':('hours','Event_Duration_Hours','event_brief','Dated event schedule and venue billing period','A007;A020'),
 'setup_hours':('paid hours','Labor_Hours','staff_schedule','Paid setup schedule excluding vendor-package staff','A007;A015'),
 'clearance_hours':('paid hours','Labor_Hours','staff_schedule','Paid clearance schedule and breaks','A007;A015'),
 'venue_area_m2':('m2','Venue_Area_m2','measured_geometry','Measured Sri Lankan floor plan with provenance','A009'),
 'excluded_area_m2':('m2','Usable_Area_m2','measured_geometry','Measured exclusions, no capacity-to-area inference','A009;A012'),
 'area_per_standard_seat_m2':('m2/seat','Space_Utilization','policy_and_geometry','Arrangement-specific layout review, including treatment of circulation','A010;A012'),
 'area_per_vip_seat_m2':('m2/seat','VIP_Area_m2','policy_and_geometry','Measured VIP layout and approved allocation rule','A010;A012'),
 'stage_width_m':('m','Stage_Area_m2','measured_geometry','Selected stage specification/measurement','A011'),
 'stage_length_m':('m','Stage_Area_m2','measured_geometry','Selected stage specification/measurement','A011'),
 'service_area_m2':('m2','Space_Utilization','measured_geometry','Service-zone plan; no overlapping allocations','A010;A012'),
 'circulation_area_m2':('m2','Space_Utilization','policy_and_geometry','Practitioner-reviewed circulation ledger, not safety certification','A010;A012'),
 'capacity_persons':('persons','Guest_Count;Space_Utilization','venue_specific_advertisement','P03 auditorium 150 / P04 conference hall 80 are scoped candidates, not selected capacity','A004;A012'),
 'base_staff':('persons','Staff_Count','staff_schedule','General staff roles independent of catering/security packages','A015'),
 'guests_per_staff':('persons/staff','Staff_Count','policy_choice','Reviewed role/workload rule; no event staffing distribution observed','A015'),
 'extra_general_staff':('persons','Staff_Count','staff_schedule','Additional role schedule and package exclusion','A015'),
 'regular_paid_hours_limit':('hours/person','Labor_Hours','contract_policy','Employment/shift agreement; no arbitrary standard-day default','A007;A015'),
 'overtime_multiplier':('multiplier','Quoted_Labor_Cost','contract_policy','Applicable overtime agreement and reviewer confirmation','A007;A015'),
 'initial_budget_lkr':('LKR','Initial_Budget','organizer_contract','Ex-ante event budget, not derived from realized cost','A021'),
 'expected_receipts_lkr':('LKR','Expected_Revenue','organizer_contract','Retained organizer receipts excluding pass-through revenue','A022'),
 'minimum_margin_points':('percentage points','Required_Min_Profit_Margin','policy_choice','Organizer/research policy with signed rationale, not market statistic','A023;A029'),
 'reserve_ratio':('fraction','Contingency_Reserve','policy_choice','Approved reserve policy; no published universal event ratio','A024')
}
rate_master={'catering':'Quoted_Catering_Cost','chairs':'Quoted_Equipment_Rental_Cost','tables':'Quoted_Equipment_Rental_Cost','stage':'Quoted_Equipment_Rental_Cost','av':'Quoted_AV_Cost','lighting':'Quoted_Lighting_Cost','labour':'Quoted_Labor_Cost','venue_fixed':'Quoted_Venue_Rental_Cost','venue_hourly':'Quoted_Venue_Rental_Cost','security':'Quoted_Security_Cost','decoration':'Quoted_Decoration_Cost','transport':'Transport_Cost','misc':'Misc_Cost','equipment_other':'Quoted_Equipment_Rental_Cost'}
rate_aids={'catering':'A002;A013','chairs':'A002;A014','tables':'A002;A014','stage':'A002;A011;A014','av':'A002;A011','lighting':'A002;A011','labour':'A002;A007;A015','venue_fixed':'A002;A020','venue_hourly':'A002;A020','security':'A002;A001','decoration':'A002;A001','transport':'A002;A001','misc':'A002;A001','equipment_other':'A002;A014'}
parameter_rows=[]
for event, profile in config['archetypes'].items():
    assert set(profile['parameters'])==set(PARAMS)
    assert set(profile['rates'])==set(RATE_UNITS)
    for key in PARAMS:
        unit,master,kind,need,aids=spec[key]
        refs='P03;P04' if key=='capacity_persons' and event=='Corporate' else ''
        if key=='capacity_persons' and event=='Wedding': kind='unsupported_local_capacity';need='Wedding arrangement-specific capacity; corporate halls are not transferable defaults'
        parameter_rows.append([event,f'archetypes.{event}.parameters.{key}',key,unit,master,kind,refs,None,need,aids,'Pending review',''])
    for item, unit in RATE_UNITS.items():
        candidates=[r for r in raw['rates'] if r['engine_item']==item and r['event_type'] in [event,'Shared']]
        refs=';'.join(r['id'] for r in candidates)
        need='Dated applicable LKR quotation, compatible quantity/billing unit, taxes, scope and bundle exclusions'
        if item=='catering':need+='; Wedding menu is historical, Corporate starting package is bundled'
        if item in ['av','lighting']:need+='; approved kit contents and independent stage-area thresholds'
        if item=='stage':need+='; linear per-m2 charging not established by package advertisements'
        if item=='labour':need+='; role-specific hourly rate and paid setup/clearance/overtime'
        if item=='security':need+='; LKR event guard/steward quote, not USD VIP bodyguard service'
        if item=='venue_hourly':need+='; engine currently applies hourly rate to all event hours'
        if item=='transport':need+='; distance, minimum charge and depot/overnight rules do not map directly to booking scalar'
        if item=='misc':need+='; itemized evidence or explicitly reviewed experimental allowance, never a balancing plug'
        parameter_rows.append([event,f'archetypes.{event}.rates.{item}.rate',item,unit,rate_master[item],'advertised_candidate_not_approved' if refs else 'unsupported_local_service_rate',refs,None,need,rate_aids[item],'Pending review',''])
        parameter_rows.append([event,f'archetypes.{event}.rates.{item}.tax_rate_points',item+' tax','percentage points',rate_master[item],'quote_specific_tax_policy','P04' if item=='venue_fixed' and event=='Corporate' else '',None,'Quote-specific tax amount and taxable basis; Caritas 15% is service charge, not tax',rate_aids[item],'Pending review',''])
assert len(parameter_rows)==108

controls=[]
for event, profile in config['archetypes'].items():
    for param,bounds in profile['approved_override_bounds'].items():
        for bound in ['min','max']:
            controls.append([event,f'archetypes.{event}.approved_override_bounds.{param}.{bound}',spec[param][0],None,'Reviewed scope/experimental bound; not source-population quantile','Live overrides and diagnostic pilot','Pending review',''])
    for key in ['av_steps','lighting_steps','billing.catering_mode','billing.staff_scope','billing.included_items','sampling_weights','geometry_origin','revenue_mode','date_bounds','vendor_tiers','price_series_whitelist','outcome_uncertainty.distribution','outcome_uncertainty.cost_bounds','outcome_uncertainty.revenue_bounds','outcome_uncertainty.dependence_spec','outcome_uncertainty.approval_ref','injected_vendor_regime.prevalence','injected_vendor_regime.multiplier_bounds','injected_vendor_regime.affected_services','injected_vendor_regime.approval_ref']:
        unit='structured configuration'
        if key in ['av_steps','lighting_steps']:unit='max_stage_area_m2 and integer kit units'
        controls.append([event,f'archetypes.{event}.{key}',unit,None,'Explicit reviewed policy, evidence and scope; unknown stays null','Deterministic engine' if key.startswith('billing.') or key.endswith('_steps') else 'Diagnostic pilot / later generator','Pending review',''])
for key in ['seed','calibration_cutoff','source_snapshot_hashes','pilot.scenario_count','pilot.approved_config_sha256','pilot.review_record_ref','pilot.passing_test_report_ref','pilot.sampling_protocol_ref','pilot.provenance_protocol_ref']:
    controls.append(['Shared',key,'integer' if key in ['seed','pilot.scenario_count'] else 'metadata/reference',None,'Freeze documented value after formal gates; audit manifest does not grant approval','Pilot authorization','Pending review',''])
for aid in FORMULA_IDS:
    controls.append(['Shared','formula_approvals.'+aid,'formal reviewer record',None,'Reviewer identity/role/date/rationale/evidence and approved rule version; technical review not approval','Live engine and pilot','Pending review',''])

uses={
 'inflation':('S001;S002','Observed local index context','Index points and percentage-point changes','No event service price, elasticity or reserve policy. Ratios require approved cutoff/pass-through'),
 'retail_prices':('S003','Observed local ingredient prices','LKR per item_raw/unit_raw and reported week','Not package catering rate; POC excludes ingredient BOM. Match units/recipes before any future derivation'),
 'sl_procurement':('S004','Aggregate local procurement context','Awarded values in LKR million / reported period','Not per-event retail quotations; do not divide totals by procurement count to infer vendor rates'),
 'cbsl_prices_wages':('S006','Local macro price/wage context','Cell-level numeric/text values, contextual source units','No unambiguous role-specific event person-hour quotation; inspect row/column labels before future use'),
 'uk_service_awards':('S007;S008','Foreign contract context only','Award values in source currency','Not Sri Lankan retail service rates; no foreign currency transfer'),
 'usda_away':('S009','Foreign price methodology only','US prices and source units','No direct Sri Lankan catering rate'),
 'usda_home_national':('S010','Foreign price methodology only','US weighted dollars/grams and indices','No direct Sri Lankan ingredient/service rate'),
 'usda_home_supplement':('S011','Foreign price methodology only','US alternative price indices','No direct Sri Lankan service rate; mirrors not independent observations'),
 'venues':('S013','Foreign capacity/facilities benchmark only','California room capacities in persons','No Sri Lankan floor area or rental rate; no local capacity default'),
 'events':('S015','Foreign event context only','Austin event dates; attendance missing','No guests, financial outcomes or local event-type distribution')
}
inventory=read_csv('reports/dataset_inventory.csv')
source_rows=[]
snapshot={}
for path in sorted((ROOT/'data/processed').glob('*.csv')):
    rows=read_csv(path.relative_to(ROOT));fields=list(rows[0]) if rows else []
    _,kind,unit,limit=uses[path.stem]
    ids=';'.join(sorted({r['source_id'] for r in rows if r.get('source_id')}))
    source_rows.append([path.name,ids,len(rows),kind,unit,limit,';'.join(fields),sha(path.relative_to(ROOT))])
    snapshot[str(path.relative_to(ROOT)).replace('\\','/')]=sha(path.relative_to(ROOT))
assert len(source_rows)==10
preserve=['config/simulator.v0.1.template.json','component4/engine.py','component4/api.py','reports/simulation_assumption_register.xlsx','reports/simulation_assumption_register.csv','work/original_schema.json','reports/updated_data_dictionary.csv','reports/financial_dependency_rules.md','reports/scenario_generation_design.md','reports/pilot_authorization_conditions.md','reports/sri_lanka_quotation_collection_template.xlsx','reports/quotation_template_metadata.json','reports/technical_review_snapshot.json','fixtures/config.mock_test_only.json']
for f in preserve: snapshot[f]=sha(f)

schema_rows=[]
for d in dictionary:
    name=d['Column_Name']
    matching=[key for key, val in spec.items() if name in val[1].split(';')]+[key for key,val in rate_master.items() if val==name]
    status='Unsupported observed financial outcome/label' if name in ['Actual_Total_Cost','Actual_Revenue','Budget_Overrun','Profit_Margin_Risk','Vendor_Cost_Anomaly','Historical_Mean_Cost','Vendor_Price_Volatility','Financial_Health_Score'] else 'Derived only after approved inputs' if name in ['Profit','Profit_Margin','Cost_Per_Guest','Cost_Variance','Budget_Utilization','Space_Utilization','Forecasted_Total_Cost','Usable_Area_m2','Stage_Area_m2','VIP_Area_m2','Contingency_Reserve','Staff_Count','Labor_Hours','Seating_Count'] else 'Planning input/evidence or identifier'
    schema_rows.append([name,d['Data_Type'],d.get('Prediction_Role',''),d.get('Unit_Clarification',''),';'.join(matching),status,d['Description']])
assumption_rows=[]
for row in assumptions[1:]:
    aid=row[0]
    keys=sorted({r[2] for r in parameter_rows if aid in r[9].split(';')})
    assumption_rows.append([aid,row[1],row[2],';'.join(keys),'Active provisional engine' if aid in FORMULA_IDS else 'Deferred design / later simulator',row[4],row[-1],'Technical recommendations are advisory; no formal approval'])

proposed=copy.deepcopy(config)
proposed['config_version']='0.1.0-evidence-proposal-2026-10-11'
proposed['record_kind']='unapproved_parameter_evidence_proposal'
proposed['evidence_audit']={'access_date':raw['access_date'],'ready_for_numeric_approval':False,'active_base_parameter_count':52,'active_service_rate_count':28,'active_tax_parameter_count':28,'all_active_numeric_values_unset':True,'source_inspections_repeated':False,'source_snapshot_hashes_for_audit_only':snapshot,'warning':'Evidence collection is not rate selection, formal approval or pilot authorization. Do not use access dates as quote/effective dates.'}
proposed['public_price_candidates']=raw
proposed['parameter_evidence']=[dict(zip(['event_type','config_path','parameter','unit','master_columns','evidence_type','candidate_refs','proposed_value','required_evidence','assumption_ids','review_status','review_note'],r)) for r in parameter_rows]
proposed['derived_relationship_proposals']=[
 {'id':'D01','expression':'seats=ceil(guest_count*seated_share); tables=ceil((seats-vip_seats)/seats_per_table)+vip_tables','unit':'counts','value':None,'kind':'arithmetic_given_approved_inputs','approval_status':'pending'},
 {'id':'D02','expression':'stage_area=stage_width_m*stage_length_m; usable_area=venue_area_m2-excluded_area_m2; sum(disjoint areas)<=usable_area','unit':'m2','value':None,'kind':'arithmetic_given_measured_and_approved_inputs','approval_status':'pending'},
 {'id':'D03','expression':'planned_cost=sum(disjoint net/tax-normalized expenses); reserve=reserve_ratio*planned_cost; profit=expected_receipts_lkr-planned_cost','unit':'LKR','value':None,'kind':'accounting_and_policy','approval_status':'pending'},
 {'id':'D04','expression':'National Library general weekday block: 16000+5500*max(0,hours-3), subject to published hire terms and billing rounding','unit':'LKR','value':None,'kind':'provider_specific_billing_derivation_not_current_engine','source_ref':'P03','approval_status':'pending'},
 {'id':'D05','expression':'Caritas weekday base hall subtotal=35000*(1+15/100)=40250 before unresolved hall taxes/extras','unit':'LKR','value':40250,'kind':'derived_advertised_subtotal_not_approved_gross_quote','source_ref':'P04','approval_status':'pending'}
]
proposed['scope_compatibility_flags']=['R03 legacy AV expression differs from amended A011 independent steps; reconcile rule version before approval','Venue included-hour / clock-time surcharges unsupported by current engine','Item-day billing requires duration conversion and item/package selection','Service charge and compound tax treatment are not represented separately','Transport distance/minimum/overnight rules are not a booking scalar','Refundable deposits are cash requirements, not operating expenses']
for event,profile in proposed['archetypes'].items():
    assert all(x is None for x in profile['parameters'].values())
    assert all(r['rate'] is None and r['tax_rate_points'] is None for r in profile['rates'].values())
    result=evaluate(proposed,event,mode='live')
    assert result['status']=='blocked' and result['costs'] is None

write_json('config/simulator_parameters.proposed.json',proposed)
write_json('work/parameter_audit_tables.json',{'Parameters':{'headers':['Event_Type','Config_Path','Parameter','Unit','Master_Columns','Evidence_Type','Candidate_Refs','Proposed_Value','Required_Evidence_or_Review','Assumption_IDs','Review_Status','Reviewer_Notes'],'rows':parameter_rows},'Controls':{'headers':['Scope','Config_Path','Unit','Proposed_Value','Evidence_Required','Needed_For','Review_Status','Reviewer_Notes'],'rows':controls},'Existing_Sources':{'headers':['Cleaned_File','Source_ID','Rows','Evidence_Type','Units','Applicability_Limit','Columns','SHA256'],'rows':source_rows},'Master_Schema':{'headers':['Master_Column','Data_Type','Prediction_Role','Unit_Clarification','Engine_Inputs_or_Rates','Evidence_Status','Definition'],'rows':schema_rows},'Assumption_Links':{'headers':['Assumption_ID','Category','Master_Columns','Related_Engine_Parameters','Implementation_Scope','Proposed_Relationship','Formal_Status','Review_Interpretation'],'rows':assumption_rows},'snapshot':snapshot,'source_observation_rows_reviewed':len(source_observations['rows'])})
print(json.dumps({'parameters':len(parameter_rows),'controls':len(controls),'schema_columns':len(schema_rows),'assumptions':len(assumption_rows),'cleaned_sources':len(source_rows),'public_entries':len(raw['rates']),'public_sources':len(raw['sources']),'leads':len(raw['leads']),'live_calculation':'blocked'},indent=2))
