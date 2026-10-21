"""Prepare Stage 2 review artifacts. Never approves, freezes or simulates."""
from pathlib import Path
import copy, json, csv, hashlib
import openpyxl
from component4.engine import PARAMS, RATE_UNITS, FORMULA_IDS, evaluate

ROOT=Path(__file__).resolve().parents[2]
VERSION='assumption-review.0.2.0-proposed'
def load(p): return json.loads((ROOT/p).read_text(encoding='utf-8-sig'))
def write(p,obj): (ROOT/p).write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
def sha(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()

base=load('config/simulator_parameters.proposed.json')
stage1=load('work/parameter_audit_tables.json')
register=openpyxl.load_workbook(ROOT/'reports/simulation_assumption_register.xlsx',read_only=True,data_only=True)
register_rows=list(register['Assumptions'].values)
assert len(register_rows)==35
assumptions={r[0]:dict(zip(register_rows[0],r)) for r in register_rows[1:]}
assert len(assumptions)==34 and all(r['Approval_Status']=='Pending review' for r in assumptions.values())
rates=openpyxl.load_workbook(ROOT/'reports/public_lkr_rate_evidence.xlsx',read_only=True,data_only=True)
rate_rows=list(rates['Rates'].values)[:21]
assert len(rate_rows)==21 and rate_rows[1][4]==6500
assert len(list(rates['Source_Terms'].values)[:10])==10

# Every formula demanded by the existing engine's approval gate has an explicit scope.
# Definitions are code/document proposals, never empirical estimates or approvals.
formula_specs={
 'A001':('Accounting and taxes','Q=sum(disjoint gross expense lines); exclusive gross=round(q*r*(1+t/100)); inclusive gross=round(q*r), net=round(q*r/(1+t/100))','LKR','Accountant/domain expert plus supervisor','Tax and compound service charges, single-level inclusion map, deposits and rounding need review','FDR;ENGINE;QUOTE;STAGE1','test_reconciliation;test_bundle_not_double_charged;test_inclusive_tax_is_not_added_twice'),
 'A007':('Paid duration','Hpaid=Hsetup+Hevent+Hclear; Hregular=min(Hpaid,Hlimit); Hovertime=max(0,Hpaid-Hregular)','hours/person','Staffing practitioner/domain expert plus supervisor','Actual paid breaks, role scope and overtime agreement missing. Date span is not paid duration; direct hour/overtime boundary checks added in Stage 2 verification','FDR;ENGINE;QUOTE','test_reconciliation;Stage2 paid-hour verification'),
 'A008':('Seating and furniture demand','N=ceil(seated_share*G); tables=ceil((N-VIP)/seats_per_table)+VIP_tables; VIP<=N<=G and VIP<=VIP_tables*seats_per_table','counts','Venue/event practitioner plus supervisor','Single table capacity for VIP and standard tables must fit plan. Seat share is A008, guest occupancy is A005','FDR;ENGINE;QUOTE','test_seating_integer_and_table_ceiling;test_vip_tables_insufficient'),
 'A009':('Usable venue area','U=V-excluded_area; 0<U<=V','m2','Venue practitioner plus supervisor','Need measured plan; capacity is not floor area','FDR;ENGINE;QUOTE','test_area_boundary;test_no_implied_geometry'),
 'A010':('Area allocation','Standard=(N-VIP)*a_standard; VIP_area=VIP*a_vip; non-overlapping service and circulation areas','m2 and m2/seat','Venue practitioner plus supervisor','Densities/circulation not observed. No fire-safety certification','FDR;ENGINE;QUOTE','test_area_boundary'),
 'A011':('Stage and independent package steps','S=width*length; separately choose AV and lighting units from first reviewed max_stage_area_m2>=S','m2 and kits','AV/venue vendor expert plus supervisor','Legacy register/R03 uses ceil-area expression; amended engine uses independent steps. Zero stage is accepted by engine, but original positive-dimension scope needs a decision','FDR;ENGINE;TECH;STAGE1','test_stepwise_independent_thresholds'),
 'A012':('Spatial constraints','Used=(N-VIP)*a_standard+VIP*a_vip+S+service+circulation; Used<=U and G<=C','m2 and persons','Venue practitioner plus supervisor','No automatic layout adaptation. Invalid layout blocks; if N<G no standing-person area is explicitly allocated. Restrict review POC to N=G until amendment','FDR;ENGINE;QUOTE','test_capacity_boundary;test_area_boundary;test_vip_invalid'),
 'A013':('Package catering','Catering quantity=planned G; charge G*approved per-person package rate once, subject to reviewed inclusion map','persons and LKR/person','Caterer/event practitioner plus supervisor','No ingredient BOM, wastage, minimum guests or adult/child tiers implemented. Quotes requiring these are not compatible without amendments','FDR;ENGINE;STAGE1;QUOTE','test_bundle_not_double_charged;test_reconciliation'),
 'A014':('Disjoint equipment ledger','Chairs=N; tables from A008; stage=S; other equipment fixed booking line; each applicable line charged once','items, m2 and LKR','Rental/vendor practitioner plus accountant','Item-day rates need duration conversion. Equipment aggregate is not a single podium price','FDR;ENGINE;STAGE1;QUOTE','test_bundle_not_double_charged;test_reconciliation'),
 'A015':('General staff and billing hours','Staff=base+ceil(G/guests_per_staff)+extra; physical person_hours=Staff*Hpaid; billing quantity=Staff*(Hregular+Hovertime*multiplier)','persons and person-hours','Staffing practitioner plus supervisor','General pool excludes vendor/security staff. Formula implies at least one ratio-based staff member when G>0; all-staff-bundled cases need a scope amendment','FDR;ENGINE;QUOTE','test_reconciliation;test_what_if_and_baseline_immutable'),
 'A020':('Venue billing','Venue=approved fixed booking amount + Hevent*approved hourly tariff; each line normalized for tax','LKR/booking and LKR/hour','Venue provider plus accountant','Current formula bills all event hours. Included-hour and clock-time surcharges do not fit without a reviewed extension','FDR;ENGINE;STAGE1;QUOTE','test_reconciliation'),
 'A021':('Budget constraint','B fixed before outcomes; reserve=c*Q; require B>=reserve; planned breaches compare Q>B and Q>B-reserve','LKR','User/organizer plus supervisor','If experimental B=b*Qreference is selected, calculate once for baseline and freeze for What-If pairs. Never recalculate B from realized cost','FDR;ENGINE;LABELS','test_budget_below_reserve_blocks;test_financial_failure_retained;test_equality_is_not_risk'),
 'A022':('Retained receipts and profit','Planned profit=expected retained receipts-Q; realized profit=realized retained receipts-realized cost','LKR','Organizer/accountant plus supervisor','Do not equate client total turnover or pass-through cash with retained receipts. No receipt amount inferred from desired profit','FDR;ENGINE;QUOTE','test_profit_labels;test_zero_missing_negative_receipts'),
 'A023':('Margin policy','Margin_points=100*profit/receipts when receipts>0; compare to separately selected minimum_margin_points','percentage points','Explicit user policy review plus supervisor','Zero receipts gives null margin, not a safe zero-risk label. Policy threshold is not industry average','FDR;ENGINE;LABELS','test_margin_boundary;test_zero_denominators'),
 'A024':('Contingency funding','Reserve=round(c*Q); operating allowance=B-Reserve; Reserve excluded from Q and profit expenses','LKR and fraction','Explicit user policy review plus accountant/supervisor','Unspent reserve is funding, not expense. Reserve fraction does not represent a calibrated confidence level','FDR;ENGINE;LABELS','test_contingency_not_an_expense;test_budget_below_reserve_blocks'),
 'A027':('Planning estimate','Forecasted_Total_Cost=Q for this provisional deterministic POC; historical event mean/vendor volatility remain null','LKR','Supervisor plus accountant','No Prophet forecast or trained-model prediction. Retail history cannot replace observed event outcomes','ENGINE;FDR;STAGE1','test_fixture_response_contracts;test_no_unvalidated_anomaly_or_health_score'),
 'A028':('Budget outcome label','Budget_Overrun=1[round(realized cost)>round(B)] if valid nonnegative operands; equality=0','binary','Supervisor plus financial domain reviewer','Actual outcomes unavailable. Future synthetic labels require origin and frozen ex-ante budget; planned flag is not target','ENGINE;LABELS;PILOT','test_equality_is_not_risk;test_missing_outcomes_not_zero_labels'),
 'A029':('Margin outcome label','Profit_Margin_Risk=1[100*(realized receipts-realized cost)/realized receipts < required margin]; receipts<=0 => null','binary and percentage points','Supervisor plus financial domain reviewer','Tested arithmetic does not validate market outcomes. Outcome and injected flags excluded from planning features','ENGINE;LABELS;PILOT','test_profit_labels;test_zero_missing_negative_receipts'),
 'A033':('Version and identity binding','Engine fingerprint=SHA256(sorted compact JSON); parameter payload includes parameters/rates/billing/steps/override bounds; pilot binds full configuration and count','SHA256 and version identifiers','Supervisor/reproducibility reviewer','Draft hashes identify content, not completeness, signatures or permission. Seed/RNG/source cutoff remain unresolved','ENGINE;GATES;PILOT','test_deterministic_replay;test_hash_binds_override_bounds;test_pilot_is_blocked')
}
assert set(formula_specs)==set(FORMULA_IDS)
refs={
 'FDR':('Financial dependency rules','reports/financial_dependency_rules.md','Review draft, legacy R03 not reconciled'),
 'ENGINE':('Deterministic implementation','component4/engine.py','Rules version 0.1.0-review; software only'),
 'GATES':('Pilot gate implementation','component4/gates.py','No generator or authentication of signatures'),
 'QUOTE':('Quotation protocol','reports/quotation_collection_guide.md','Blank collection template, no observed filled quotes'),
 'TECH':('Technical implementation response','reports/technical_review_implementation_response.md','Advisory technical review, not approval'),
 'STAGE1':('Public rate audit','reports/parameter_evidence_summary.md','Advertised candidates, no active numerical rates'),
 'LABELS':('Risk label definitions','reports/risk_label_definition.md','Simulated target design, not real outcomes'),
 'PILOT':('Pilot authorization conditions','reports/pilot_authorization_conditions.md','Unresolved and not authorized'),
 'DESIGN':('Scenario design','reports/scenario_generation_design.md','Proposed experimental ranges, no generator'),
 'GRAPH':('Spatial financial graph','reports/spatial_financial_graph_schema.md','Designed dependencies, not observed adjacency'),
 'VALIDATION':('Simulation validation plan','reports/simulation_validation_plan.md','External observed-event validation not performed'),
 'LEAKAGE':('Prediction firewall','reports/data_leakage_audit.md','Group/time splitting and target exclusions')
}
for s in base['public_price_candidates']['sources']:
    refs[s['id']]=(s['provider'],s['url'],s['applicability'])
for r in base['public_price_candidates']['rates']:
    refs[r['id']]=(r['service'],next(s['url'] for s in base['public_price_candidates']['sources'] if s['id']==r['source_id']),r['restriction'])

# Explicit options for human review. None is selected or copied to runtime values.
def policy(pid,aids,scope,unit,options,rationale,guard):
    return {'policy_id':pid,'assumption_ids':aids,'scope':scope,'unit':unit,'options':options,'selected_value':None,'evidence_kind':'hypothetical_experimental_choices','rationale':rationale,'constraints':guard,'status':'pending','reviewer':None,'reviewer_role':None,'review_date':None,'decision_rationale':None,'decision_evidence_ref':None,'assumption_version':VERSION}
policies=[
 policy('EXP-BUDGET',['A021'],'Shared','B/Qreference ratio',[0.85,1.0,1.15,1.30],'Test financially tight, break-even and funded planning cases; not observed affordability','Use independently approved baseline Qreference once; freeze B across paired interventions; B>=reserve'),
 policy('EXP-RESERVE',['A024'],'Shared','fraction of planned cost',[0.0,0.05,0.10,0.15,0.20],'Zero-reserve control plus proposed 5/10/15/20% sensitivity; not a market standard','B includes reserve. Reserve not operating expense. Select policy before outcomes'),
 policy('EXP-MARGIN',['A023','A029'],'Shared','percentage points',[0,10,20,30],'Zero-profit threshold control and original policy sensitivity; not empirical margins','Keep retained receipts independent; equality meets threshold; zero receipts => null margin'),
 policy('EXP-WEDDING-GUEST',['A005','A012'],'Wedding','fraction of selected approved capacity',[0.50,0.75,1.00],'Within original .50–1.00 capacity scope; not measured wedding attendance','Positive integer guests after declared rounding; measured layout and capacity still bind'),
 policy('EXP-CORPORATE-GUEST',['A005','A012'],'Corporate','fraction of selected approved capacity',[0.30,0.60,0.90],'Within original .30–.90 scope; not measured corporate attendance','Positive integer guests; event-specific seated capacity and geometry required'),
 policy('EXP-WEDDING-SEATING',['A008','A012'],'Wedding','seated fraction',[1.00],'Seated-only POC control, not observed wedding practice','Still pending user/expert approval. Lower share deferred: current engine lacks explicit standing-person area'),
 policy('EXP-CORPORATE-SEATING',['A008','A012'],'Corporate','seated fraction',[1.00],'Seated-only POC control, not an occupancy safety standard','Still pending user/expert approval. Mixed/standing share options deferred pending reviewed standing-area extension'),
 policy('EXP-DURATION',['A007','A020'],'Shared','event hours',[2,4,6,8],'Bounded duration sensitivity proposed for this review, not actual schedules','Venue availability/billing and paid setup/clearance/shift contracts constrain selection'),
 policy('EXP-STAGE-SCALE',['A011','A012'],'Shared','dimension multiplier',[0.8,1.0,1.2],'Paired size interventions around measured/approved baseline, not real-stage distribution','Scaling one dimension vs both is a separate choice. Square multiplier applies if both dimensions scaled. Actual bounds and steps remain null'),
 policy('EXP-COST-SHOCK',['A025'],'Shared','realized net rate multiplier',[0.80,0.90,0.95,1.00,1.05,1.10,1.20],'No-shock and ±5/10/20% stress levels, not probabilities or intervals','Apply selected factor to declared disjoint net service rates, then recompute taxes/ledger. Never inject into planning inputs'),
 policy('EXP-RECEIPT-SHOCK',['A022','A025'],'Shared','retained receipt multiplier',[0.80,0.90,0.95,1.00,1.05,1.10,1.20],'Bounded receipt stress, not measured cancellation or demand rates','Nonnegative retained receipts, ex-ante expectation independent. Latent factor restricted to diagnostic outcome sidecar'),
 policy('EXP-DEPENDENCE',['A025','A026'],'Shared','stress pairing design',['factorial_grid_no_probabilities','paired_adverse_cost_up_receipts_down','shared_cost_factor_across_declared_services'],'Compare joint stress designs without inventing correlation coefficients','No stochastic distribution/covariance inferred. Predeclare selected grid subset; no target-prevalence tuning'),
 policy('EXP-ANOMALY-SEVERITY',['A030'],'Shared','injected service-rate multiplier',[1.10,1.25,1.50],'Explore injection severity as separate latent intervention, not actual fraud','Declare affected service and ordinary-shock composition once. Prevalence and actual service set remain null; labels unavailable without approved regime'),
 policy('EXP-ALLOCATION',['A003','A032'],'Shared','diagnostic design',['equal_profile_coverage_not_population','separately_reviewed_profile_allocation'],'Coverage is research design, not Sri Lankan event prevalence','Weights, record count and grouped partitions remain null; no pilot authorization'),
 policy('EXP-OUTCOME-DESIGN',['A025','A026','A032'],'Shared','diagnostic design',['deterministic_bounded_stress_grid_not_probability_model'],'Avoid invented residual distribution when outcomes are unavailable','Later generator/gate adapter requires reviewed implementation; deterministic grid is not implemented or auto-authorized')
]

corrected={'guest_count':['A003','A005','A012'],'seated_share':['A008']}
numeric=[]
for row in stage1['Parameters']['rows']:
    event,path,key,unit,master,kind,candidates,value,need,aids,_,_=row
    ids=corrected.get(key,aids.split(';'))
    assert ids and set(ids)<=set(assumptions)
    support=';'.join(x for x in [candidates,'QUOTE','STAGE1'] if x)
    if kind=='policy_choice':support+=';DESIGN'
    numeric.append({'decision_id':event[:1]+'-N'+str(sum(x['event_type']==event for x in numeric)+1).zfill(3),'event_type':event,'path':path,'parameter':key,'unit':unit,'assumption_ids':ids,'evidence_kind':kind,'supporting_refs':support,'value':None,'required_decision':need+'; explicit user review plus appropriate domain confirmation','status':'pending','reviewer':None,'reviewer_role':None,'review_date':None,'rationale':None,'decision_evidence_ref':None,'assumption_version':VERSION})
assert len(numeric)==108 and len({r['path'] for r in numeric})==108

param_ids={r['parameter']:r['assumption_ids'] for r in numeric if '.parameters.' in r['path']}
def control_ids(path):
    if '.approved_override_bounds.' in path:
        return sorted(set(param_ids[path.split('.approved_override_bounds.')[1].split('.')[0]]+['A021','A033']))
    if path.startswith('formula_approvals.'):return [path.split('.')[-1],'A033'] if path.split('.')[-1]!='A033' else ['A033']
    for key,ids in {'av_steps':['A011'],'lighting_steps':['A011'],'billing.catering_mode':['A013'],'billing.staff_scope':['A015'],'billing.included_items':['A001','A002','A013','A014','A015'],'sampling_weights':['A003','A032'],'geometry_origin':['A009','A012'],'revenue_mode':['A022'],'date_bounds':['A007','A016','A033'],'vendor_tiers':['A019'],'price_series_whitelist':['A016','A017','A018'],'outcome_uncertainty':['A025','A026'],'injected_vendor_regime':['A030'],'calibration_cutoff':['A016','A032'],'source_snapshot_hashes':['A016','A033'],'seed':['A033'],'pilot.':['A032','A033']}.items():
        if key in path:return ids
    raise ValueError('Unmapped control: '+path)
controls=[]
for i,r in enumerate(stage1['Controls']['rows'],1):
    scope,path,unit,_,need,usage,_,_=r
    ids=control_ids(path);assert set(ids)<=set(assumptions)
    controls.append({'decision_id':scope[:1]+'-C'+str(i).zfill(3),'event_type':scope,'path':path,'unit':unit,'assumption_ids':ids,'evidence_kind':'experimental_policy_or_review_record','supporting_refs':'DESIGN;PILOT;ENGINE','value':None,'required_decision':need+'; scope: '+usage,'status':'pending','reviewer':None,'reviewer_role':None,'review_date':None,'rationale':None,'decision_evidence_ref':None,'assumption_version':VERSION})
for event in ['Wedding','Corporate']:
    controls.append({'decision_id':event[:1]+'-APPROVAL','event_type':event,'path':f'archetypes.{event}.parameter_approval','unit':'formal scope and parameter_payload SHA256','assumption_ids':['A002','A033'],'evidence_kind':'formal_review_record','supporting_refs':'QUOTE;PILOT;ENGINE','value':None,'required_decision':'Genuine reviewer role/date/rationale/evidence and approved full parameter payload; do not copy draft hash as approval','status':'pending','reviewer':None,'reviewer_role':None,'review_date':None,'rationale':None,'decision_evidence_ref':None,'assumption_version':VERSION})

def authority(aid):
    if aid in ['A001','A020','A022','A024']:return 'Accountant/organizer domain reviewer and supervisor; numeric choices require explicit user review'
    if aid in ['A007','A015']:return 'Staffing practitioner and supervisor; schedules/rates require user review'
    if aid in ['A004','A005','A008','A009','A010','A011','A012','A013','A014']:return 'Relevant venue/catering/AV practitioner and supervisor; input profile requires user review'
    return 'Supervisor/methodology reviewer; experimental values require explicit user review'
formula_records=[]
for aid in FORMULA_IDS:
    title,expression,unit,who,finding,support,tests=formula_specs[aid]
    formula_records.append({'formula_id':aid,'assumption_id':aid,'assumption_ids':[aid],'engine_gate_required':True,'title':title,'expression':expression,'unit':unit,'authority':who,'finding':finding,'supporting_refs':support,'test_refs':tests,'assumption_version':VERSION,'rules_version':base['rules_version'],'status':'pending','reviewer':None,'reviewer_role':None,'review_date':None,'rationale':None,'decision_evidence_ref':None})
for fid,ids,title,expression,unit,finding,tests in [
 ('U030',['A030'],'Supplied injection flag utility','Vendor_Cost_Anomaly=int(flag) only if a boolean injection flag is supplied; otherwise null','binary','Boolean truth conversion exists for explicit software-test outcomes. Regime generator and real anomaly detector do not exist','test_vendor_regime_not_guessed;test_nonboolean_vendor_injection_not_labelled'),
 ('WHAT_IF',['A012','A022','A027','A033'],'Paired planning differences','Delta cost=Qalt-Qbase; delta profit=Palt-Pbase; delta used_area=Aalt-Abase; all deltas null unless both calculations valid','LKR and m2','Planning estimates only. Baseline inputs fixed; policy options not automatically activated; no probability or ML explanation','test_what_if_and_baseline_immutable;test_invalid_alternative_no_misleading_delta')
]:
    formula_records.append({'formula_id':fid,'assumption_id':ids[0],'assumption_ids':ids,'engine_gate_required':False,'title':title,'expression':expression,'unit':unit,'authority':'Supervisor and relevant financial/venue reviewer; parent assumptions still require approval','finding':finding,'supporting_refs':'ENGINE;LABELS;PILOT','test_refs':tests,'assumption_version':VERSION,'rules_version':base['rules_version'],'status':'pending','reviewer':None,'reviewer_role':None,'review_date':None,'rationale':None,'decision_evidence_ref':None})

candidate=copy.deepcopy(base)
candidate['config_version']='0.2.0-approval-preparation-proposed'
candidate['record_kind']='unresolved_candidate_proposal'
candidate['approval_preparation']={'assumption_version':VERSION,'prepared_date':'2026-10-11','status':'proposed_unresolved','values_and_units_fully_specified':False,'candidate_frozen':False,'frozen_at':None,'approved_configuration_sha256':None,'warning':'Review draft only. Experimental option values are not selected active settings. Hashes are content identity, not formal approval or pilot authority.','mapping_corrections':['A005 concerns guest occupancy fractions, not seated share. Guest count links A003/A005/A012; seated share links A008. Stage 1 files remain unchanged.'],'formula_review_records':formula_records,'numeric_review_records':numeric,'control_review_records':controls}
candidate['parameter_evidence']=[{'event_type':x['event_type'],'config_path':x['path'],'parameter':x['parameter'],'unit':x['unit'],'assumption_ids':x['assumption_ids'],'evidence_type':x['evidence_kind'],'evidence_refs':x['supporting_refs'],'proposed_value':None,'status':'pending'} for x in numeric]
candidate['experimental_policy_proposals']=policies
candidate['assumption_decisions']=[{'assumption_id':aid,'assumption_version':VERSION,'original_register_status':r['Approval_Status'],'status':'pending','reviewer':None,'reviewer_role':None,'review_date':None,'rationale':None,'decision_evidence_ref':None} for aid,r in assumptions.items()]
assert all(x['status']=='pending' for x in candidate['formula_approvals'].values())
for event in ['Wedding','Corporate']:
    p=candidate['archetypes'][event]
    assert all(p['parameters'][k] is None for k in PARAMS)
    assert all(p['rates'][k]['rate'] is None and p['rates'][k]['tax_rate_points'] is None for k in RATE_UNITS)
    assert evaluate(candidate,event,mode='live')['status']=='blocked'
write('config/simulator.candidate.json',candidate)

common=['Decision_ID','Assumption_IDs','Assumption_Version','Config_Path','Unit','Evidence_Type','Supporting_Refs','Proposed_Value','Required_Decision','Status','Reviewer','Reviewer_Role','Review_Date','Rationale','Decision_Evidence_Ref','Record_Complete']
def decision_row(x):return [x['decision_id'],';'.join(x['assumption_ids']),VERSION,x['path'],x['unit'],x['evidence_kind'],x['supporting_refs'],None,x['required_decision'],'Pending review',None,None,None,None,None,None]
tables={}
for event in ['Wedding','Corporate']:
    tables[event]={'headers':common,'rows':[decision_row(x) for x in numeric+controls if x['event_type']==event]}
tables['Formulas']={'headers':['Formula_ID','Assumption_IDs','Assumption_Version','Expression','Unit','Evidence_Type','Supporting_Refs','Review_Required','Validation_Findings','Status','Reviewer','Reviewer_Role','Review_Date','Rationale','Decision_Evidence_Ref','Record_Complete'],'rows':[[x['formula_id'],';'.join(x['assumption_ids']),VERSION,x['title']+': '+x['expression'],x['unit'],'Engine approval gate' if x['engine_gate_required'] else 'Active utility / parent approvals required',x['supporting_refs'],x['authority'],x['finding']+'; Tests: '+x['test_refs'],'Pending review',None,None,None,None,None,None] for x in formula_records]}
tables['Assumptions']={'headers':['Assumption_ID','Category','Assumption_Version','Original_Definition','Unit','Evidence_Type','Supporting_Refs','Review_Required','Validation_Findings','Status','Reviewer','Reviewer_Role','Review_Date','Rationale','Decision_Evidence_Ref','Record_Complete'],'rows':[]}
for aid,r in assumptions.items():
    original_support=str(r['Supporting_Data_Source'])
    scope='Active engine approval scope' if aid in FORMULA_IDS else 'Numerical/design assumption or deferred later scope'
    finding=formula_specs[aid][4] if aid in formula_specs else 'Not approved; refer original register and technical response before activation'
    if aid=='A002':finding='Stage 1 found advertisements, but no complete dated compatible approved local rate card'
    tables['Assumptions']['rows'].append([aid,r['Category'],VERSION,r['Proposed_Formula_or_Range'],r['Unit_or_Currency'],r['Confidence_Level'],'TECH;DESIGN;STAGE1',authority(aid),scope+'. '+finding+'. Original support: '+original_support,'Pending review',None,None,None,None,None,None])
tables['Policies']={'headers':['Policy_ID','Assumption_IDs','Assumption_Version','Scope','Unit','Option_Values_JSON','Supporting_Rationale','Constraints','Selected_Value','Status','Reviewer','Reviewer_Role','Review_Date','Rationale','Decision_Evidence_Ref','Record_Complete'],'rows':[[x['policy_id'],';'.join(x['assumption_ids']),VERSION,x['scope'],x['unit'],json.dumps(x['options']),'HYPOTHETICAL. '+x['rationale'],x['constraints'],None,'Pending review',None,None,None,None,None,None] for x in policies]}
tables['Shared_Controls']={'headers':common,'rows':[decision_row(x) for x in controls if x['event_type']=='Shared']}
tables['References']={'headers':['Reference_ID','Source_or_Document','Applicability_Limit','','URL_or_Project_Reference'],'rows':[[key,value[0],value[2],None,value[1]] for key,value in refs.items()]}
inputs=['reports/simulation_assumption_register.xlsx','reports/simulation_assumption_register.csv','reports/financial_dependency_rules.md','reports/scenario_generation_design.md','reports/risk_label_definition.md','reports/public_lkr_rate_evidence.xlsx','reports/unresolved_parameter_checklist.xlsx','reports/parameter_evidence_summary.md','config/simulator_parameters.proposed.json','config/simulator.v0.1.template.json','component4/engine.py','component4/api.py','component4/gates.py','reports/pilot_authorization_conditions.md','reports/technical_review_implementation_response.md','reports/technical_review_snapshot.json','reports/quotation_collection_guide.md','reports/sri_lanka_quotation_collection_template.xlsx']
snapshot={p:sha(p) for p in inputs}
write('work/approval_review_tables.json',{'tables':tables,'input_hashes':snapshot,'active_formula_ids':FORMULA_IDS,'active_numeric_paths':[x['path'] for x in numeric],'assumption_version':VERSION,'policies':policies})
print(json.dumps({'assumptions':34,'formulas':len(formula_records),'numeric_fields':len(numeric),'Wedding_decisions':len(tables['Wedding']['rows']),'Corporate_decisions':len(tables['Corporate']['rows']),'policy_groups':len(policies),'shared_controls':len(tables['Shared_Controls']['rows']),'candidate_frozen':False,'active_values':'null'},indent=2))
