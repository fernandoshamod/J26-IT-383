"""Prepare review proposals and decision tables, never approve or generate scenarios."""
from copy import deepcopy
from pathlib import Path
import csv
import hashlib
import json
import math

import openpyxl  # Read existing workbook only. XLSX authoring is in the JS builder.

from component4.engine import PARAMS, RATE_UNITS, FORMULA_IDS, fingerprint, evaluate
from component4.generator_validation import CODE_FILES, PARAMETER_UNITS, REQUIRED_ASSUMPTIONS, NumericDomain, software_versions
from component4.scenario_generator import pilot_execution_blockers

ROOT = Path(__file__).resolve().parents[2]
DATE = '2026-10-11'
VERSION = 'minimal-pilot.0.1-proposed'


def read(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()


def save(path, obj):
    (ROOT/path).write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')


def domain(key, values):
    return {'distribution':'fixed' if len(values)==1 else 'choice', 'unit':PARAMETER_UNITS[key], 'values':values}


def main():
    parent = read('config/pilot_candidate.json')
    config = read('config/simulator.v0.1.template.json')
    evidence = read('work/minimal_rate_review.json')
    # Inspect all 34 original assumption rows, and verify the full CSV counterpart.
    book = openpyxl.load_workbook(ROOT/'reports/simulation_assumption_register.xlsx', read_only=True, data_only=True)
    values = list(book['Assumptions'].values)
    assumptions = {r[0]:dict(zip(values[0],r)) for r in values[1:]}
    book.close()
    with (ROOT/'reports/simulation_assumption_register.csv').open(encoding='utf-8-sig', newline='') as f:
        csv_rows = list(csv.DictReader(f))
    assert len(assumptions)==len(csv_rows)==34
    assert all(assumptions[r['Assumption_ID']]['Approval_Status']=='Pending review' for r in csv_rows)
    assert all(str(assumptions[r['Assumption_ID']]['Proposed_Formula_or_Range'])==r['Proposed_Formula_or_Range'] for r in csv_rows)
    originals = parent['approval_preparation']['numeric_review_records']
    assert len(originals)==108 and len({r['path'] for r in originals})==108

    # These are experimental inputs, never provider measurements or rate-card quotations.
    common = {
        'seated_share':1.0,'vip_seats':0,'seats_per_table':6,'vip_tables':0,
        'setup_hours':1.0,'clearance_hours':1.0,'venue_area_m2':24*18,
        'excluded_area_m2':32.0,'area_per_standard_seat_m2':1.5,'area_per_vip_seat_m2':1.5,
        'stage_width_m':4.0,'stage_length_m':3.0,'service_area_m2':24.0,'circulation_area_m2':60.0,
        'capacity_persons':min(180,math.floor(((24*18-32)-30-24-60)/1.5)),
        'base_staff':2,'guests_per_staff':30,'extra_general_staff':0,
        'regular_paid_hours_limit':8.0,'overtime_multiplier':1.5,
        'minimum_margin_points':10.0,'reserve_ratio':0.10
    }
    profiles = {
        'Wedding':{**common,'guest_count':120,'event_hours':4.0,'initial_budget_lkr':600000,'expected_receipts_lkr':650000},
        'Corporate':{**common,'guest_count':80,'event_hours':3.0,'initial_budget_lkr':300000,'expected_receipts_lkr':350000}
    }
    ranges = {
        'Wedding':{'guest_count':{'distribution':'uniform_integer','unit':'persons','min':90,'max':180},
                   'event_hours':domain('event_hours',[4.0,5.0,6.0]),
                   'initial_budget_lkr':domain('initial_budget_lkr',[450000,600000,750000]),
                   'expected_receipts_lkr':domain('expected_receipts_lkr',[550000,650000,850000])},
        'Corporate':{'guest_count':{'distribution':'uniform_integer','unit':'persons','min':40,'max':120},
                     'event_hours':domain('event_hours',[2.0,3.0,4.0]),
                     'initial_budget_lkr':domain('initial_budget_lkr',[200000,300000,400000]),
                     'expected_receipts_lkr':domain('expected_receipts_lkr',[250000,350000,450000])}
    }
    excluded = ['lighting','venue_hourly','security','decoration','transport','misc','equipment_other']
    # No false included_items map: exclusion is not inclusion in a paid provider bundle.
    exclusions = {e:{item:{'proposed_enabled':False,'status':'pending_scope_review',
                          'reason':'Absent from restricted analytical cost boundary, not free or bundled in a real event',
                          'engine_supported':False,'approval_ref':None} for item in excluded} for e in profiles}
    conditional = {
        'chairs':{'amount':50,'unit':RATE_UNITS['chairs'],'refs':['MF01'],
                  'condition':'One 12-hour rental including setup/event/clearance; confirm taxes, validity, quantity availability and pickup terms'},
        'tables':{'amount':1500,'unit':RATE_UNITS['tables'],'refs':['MF03'],
                  'condition':'One booked rental day only; confirm seating compatibility, pickup/delivery, taxes and date validity'},
    }
    config.update(config_version=VERSION,record_kind='unapproved_minimal_pilot_proposal',seed=20261022,calibration_cutoff=DATE)
    config['approval_preparation']={'status':'proposed_incomplete','candidate_frozen':False,
                                    'values_and_units_fully_specified':False,'approved_configuration_sha256':None}
    config['generator_approval']={'status':'pending','reviewer':None,'reviewer_role':None,'reviewed_at':None,
                                  'rationale':None,'evidence_ref':None,'generator_version':'0.1.0-proposed',
                                  'assumption_version':VERSION,'payload_sha256':None}
    spec = read('config/scenario_generator.template.json')
    spec.update(seed=20261022,max_attempts_per_scenario=20,archetype_weights={'Wedding':0.5,'Corporate':0.5},
                code_snapshot_hashes={p:sha(p) for p in CODE_FILES},software_versions=software_versions(),
                assumption_version=VERSION,assumption_ids=sorted(REQUIRED_ASSUMPTIONS))
    sources = ['work/minimal_rate_review.json','reports/simulation_assumption_register.csv',
               'reports/financial_dependency_rules.md','reports/risk_label_definition.md',
               'reports/minimal_pilot_scope.md','reports/pilot_acceptance_criteria.md']
    snapshot = {p:sha(p) for p in sources}
    config['source_snapshot_hashes']=snapshot
    spec['source_snapshot_hashes']=deepcopy(snapshot)
    controls=[]
    for event,p in profiles.items():
        assert set(p)==set(PARAMS)
        profile = config['archetypes'][event]
        profile['parameters']=p
        profile['billing']={'catering_mode':'package','staff_scope':'general_staff_excludes_vendor_packages','included_items':{}}
        profile['geometry_origin']='hypothetical_experimental_plan_NOT_MEASURED'
        profile['revenue_mode']='retained_contract_receipts'
        profile['date_bounds']={'start':'2026-10-22','end':'2026-10-22'}
        profile['vendor_tiers']=[]
        profile['price_series_whitelist']=[]
        profile['sampling_weights']=0.5
        profile['av_steps']=[{'max_stage_area_m2':12.0,'units':1},{'max_stage_area_m2':30.0,'units':2}]
        profile['lighting_steps']=[{'max_stage_area_m2':30.0,'units':0}]
        profile['outcome_uncertainty']={'distribution':'bounded_uniform_multipliers',
            'cost_bounds':{'min':0.9,'max':1.1,'unit':'multiplier'},
            'revenue_bounds':{'min':0.9,'max':1.1,'unit':'multiplier'},
            'dependence_spec':{'mode':'independent','cost_services':['catering','chairs','tables','stage','av','labour','venue_fixed']},
            'approval_ref':None}
        profile['injected_vendor_regime']={'prevalence':0.10,'multiplier_bounds':{'min':1.25,'max':1.50,'unit':'multiplier'},
                                           'affected_services':['stage','av','labour'],'approval_ref':None}
        parameter_domains={k:deepcopy(ranges[event].get(k,domain(k,[v]))) for k,v in p.items()
                           if k not in {'initial_budget_lkr','expected_receipts_lkr'}}
        parameter_domains['stage_width_m']=domain('stage_width_m',[3.0,4.0,5.0])
        parameter_domains['stage_length_m']=domain('stage_length_m',[3.0,4.0,6.0])
        for k,d in parameter_domains.items():
            NumericDomain.parse(d,PARAMETER_UNITS[k],event+'.'+k,integer=k in {'guest_count','vip_seats','seats_per_table','vip_tables','capacity_persons','base_staff','extra_general_staff'})
        for k,v in p.items():
            d=ranges[event].get(k,parameter_domains.get(k,domain(k,[v])))
            parsed=NumericDomain.parse(d,PARAMETER_UNITS[k],event+'.'+k)
            low,high=parsed.extent()
            profile['approved_override_bounds'][k]={'min':low,'max':high}
        spec['profiles'][event]={'date_bounds':deepcopy(profile['date_bounds']),
            'parameter_domains':parameter_domains,'budget_policy':{'mode':'fixed','budget':deepcopy(ranges[event]['initial_budget_lkr'])},
            'retained_receipts':deepcopy(ranges[event]['expected_receipts_lkr']),
            'ancestry':{'venue_profile_id':'HYP-VENUE-432M2-v1','vendor_rate_card_id':'UNRESOLVED-'+event.upper()+'-RATE-CARD',
                        'archetype_template_id':'HYP-'+event.upper()+'-MINIMAL-v1'}}
        # Reused field name is legacy schema; bounds are proposal-only, parameter review still pending.
        max_g=180 if event=='Wedding' else 120
        maximum_area=max_g*1.5+30+24+60
        assert maximum_area<=400 and max_g<=180
        for key,d in ranges[event].items():
            controls.append([event,key,json.dumps(d,separators=(',',':')),PARAMETER_UNITS[key],'Hypothetical design','Experiment designer + supervisor','Pending review'])
        controls.extend([[event,'stage_width_m','3, 4, 5','m','Hypothetical design','Experiment designer + venue/AV review','Pending review'],
                         [event,'stage_length_m','3, 4, 6','m','Hypothetical design','Experiment designer + venue/AV review','Pending review'],
                         [event,'av_steps','<=12 m2: 1 kit; <=30 m2: 2 kits','kits','Hypothetical steps, no inferred market relationship','AV practitioner + supervisor','Pending review']])
    config['scenario_generator']=spec
    config['minimal_recovery']={
        'version':VERSION,'prepared_date':DATE,'status':'review_proposal_NOT_AUTHORIZED',
        'experimental_values_not_market_statistics':True,'parent_candidate_sha256':sha('config/pilot_candidate.json'),
        'cost_boundary':'restricted_selected_services_NOT_COMPLETE_EVENT_COST',
        'component_exclusion_proposals':exclusions,'exclusion_engine_support':'NOT_IMPLEMENTED; review scope before implementing',
        'conditional_rate_candidates':{e:deepcopy(conditional) for e in profiles},
        'venue_tariff_benchmark_only':{'event':'Corporate','amount_lkr':30000,'refs':['MF05'],
                                     'not_selected':'Actual room and hypothetical geometry are not the same venue'},
        'date_scope_is_hypothetical':True,'source_snapshots_are_context_not_approved_calibration':True,
        'proposed_scenario_count':40,'base_configurations':40,'additional_variants':0,'outcome_realizations_per_base':1,
        'weighted_archetypes_not_exact_quotas':True,'minimum_profile_coverage_proposal':10,
        'outcome_settings_are_not_estimated_probabilities':True,'frozen_configuration_sha256':None,
        'human_review_records':{'designer':None,'supervisor':None,'domain_expert':None,'review_date':None,'authority_ref':None},
        'published_evidence':evidence,'numerical_decisions':[],'formula_recommendations':[]}

    recommendations={a:'Accept' for a in FORMULA_IDS}
    for a in ['A001','A010','A011','A012','A013','A014','A015','A020','A033']:
        recommendations[a]='Modify'
    inputs={
        'A001':'All quantity/rate/tax cards; tax_scope; included_items; accounting boundary',
        'A007':'setup_hours; event_hours; clearance_hours; regular_paid_hours_limit',
        'A008':'guest_count; seated_share; vip_seats; vip_tables; seats_per_table',
        'A009':'venue_area_m2; excluded_area_m2',
        'A010':'seats; vip_seats; area_per_standard_seat_m2; area_per_vip_seat_m2',
        'A011':'stage_width_m; stage_length_m; av_steps; lighting_steps; scoped kit rates',
        'A012':'guest_count; capacity_persons; usable area; seating/stage/service/circulation areas',
        'A013':'guest_count; package catering rate/tax; inclusion map',
        'A014':'seats; tables; stage area; equipment rates/taxes; reviewed scope/inclusion map',
        'A015':'base_staff; guest_count; guests_per_staff; extra_general_staff; paid hours; overtime_multiplier; labour rate',
        'A020':'venue_fixed rate; venue_hourly rate; event_hours; tax scope; booking window',
        'A021':'initial_budget_lkr; planned cost; reserve_ratio',
        'A022':'expected/realized retained receipts; planned/realized cost',
        'A023':'retained receipts; profit; minimum_margin_points',
        'A024':'planned cost; reserve_ratio; initial_budget_lkr',
        'A027':'disjoint planned ledger; reviewed rates, quantities and taxes',
        'A028':'realized total cost; fixed ex-ante initial_budget_lkr; rounding convention',
        'A029':'realized receipts/cost; minimum_margin_points',
        'A033':'exact payloads; source/code/runtime/seed/rule versions; exact authorized count'
    }
    amendments={
        'A001':'Confirm one accounting boundary and unknown taxes. Excluded components are not provider bundles. No fabricated zero VAT.',
        'A010':'Accept only as a hypothetical non-overlapping area model; no measured density, egress or fire-safety claim.',
        'A011':'Retire legacy ceil-area AV expression; use separate explicit package steps. Lighting off by scope, not free vendor service.',
        'A012':'Allow explicitly hypothetical geometry only after a versioned reviewed adapter change, or supply measured reviewed geometry.',
        'A013':'Use package-only; no ingredient BOM. Obtain compatible standalone package quote; reject double charging unitemized meeting bundles.',
        'A014':'Add a reviewed explicit component-exclusion mechanism before live use. Do not forge inclusion maps to waive missing rates.',
        'A015':'Restricted general staff only; policy ratios/hours are hypothetical, not measured wages or legal overtime.',
        'A020':'Pilot proposes fixed one-booking charge; hourly component off. Need actual scoped booking price; do not transfer another venue tariff to invented geometry.',
        'A033':'Keep fingerprints separate from signatures/completeness. Reviewed geometry/exclusion changes require new code/rule/hash approval.'
    }
    formulas=[]
    for f in parent['approval_preparation']['formula_review_records']:
        if f['formula_id'] not in FORMULA_IDS:
            continue
        aid=f['formula_id']
        row={'assumption_id':aid,'title':f['title'],'actual_formula':f['expression'],'purpose':assumptions[aid]['Scientific_Justification'],
             'required_inputs':inputs[aid],'supporting_refs':f['supporting_refs'],
             'limitations':f['finding'],'recommendation':recommendations[aid],
             'recommendation_rationale':amendments.get(aid,'Accept definition in restricted simulator scope; numerical calibration and genuine review remain separate.'),
             'original_register_formula':assumptions[aid]['Proposed_Formula_or_Range'],
             'status':'Pending review','reviewer':None,'reviewer_role':None,'review_date':None,'decision_rationale':None,
             'decision_evidence_ref':None,'rules_version':config['rules_version'],'candidate_version':VERSION}
        formulas.append(row)
    assert len(formulas)==19
    config['minimal_recovery']['formula_recommendations']=formulas

    derived={'venue_area_m2':'24 m * 18 m = 432 m2, both hypothetical dimensions',
             'area_per_vip_seat_m2':'Alias standard seat area 1.5; VIP count fixed zero, not a new density estimate',
             'capacity_persons':'min(180 policy cap, floor((400 usable - 30 maximum stage - 24 service - 60 circulation)/1.5)) = 180',
             'seats_per_table':'Select 6 from provider advertised 6-8; arrangement is still experimental'}
    rows=[]
    for original in originals:
        r=deepcopy(original);e=r['event_type'];path=r['path'];key=r['parameter']
        base='.parameters.' in path
        item=path.split('.rates.')[1].split('.')[0] if '.rates.' in path else None
        is_tax=path.endswith('.tax_rate_points')
        if base:
            classification='2. Derived parameter' if key in derived else '3. Experimental simulation parameter'
            proposed=profiles[e][key]
            bounds=config['archetypes'][e]['approved_override_bounds'][key]
            observed=None
            rationale=derived.get(key,'Explicit restricted-pilot setting, not a Sri Lankan population statistic or observed event input')
            refs='MR02/MF04' if key=='seats_per_table' else 'MINIMAL_SCOPE; original '+','.join(r['assumption_ids'])
            scope='Active proposal'
        elif item in excluded:
            classification='4. Unused parameter that can be explicitly disabled'
            proposed=None;bounds={'min':None,'max':None};observed=None
            rationale='Scope exclusion proposed, not zero-price evidence or bundle inclusion. Existing engine still requires this field until reviewed adapter support.'
            refs='MINIMAL_SCOPE; exclusion proposal '+item;scope='Excluded proposal, pending review'
        else:
            classification=('1. Publicly evidenced numerical rate' if item=='chairs' and not is_tax else
                            '2. Derived parameter' if item=='tables' and not is_tax else
                            '5. Truly unresolved essential input')
            proposed=None;bounds={'min':None,'max':None}
            observed=50 if item=='chairs' and not is_tax else 1500 if item=='tables' and not is_tax else None
            refs={'chairs':'MR01/MF01','tables':'MR02/MF03','catering':'MR04/MF08; MR06/MF10/MF11',
                  'av':'MR01/MF02; MR03/MF06/MF07','venue_fixed':'MR03/MF05 benchmark only; actual venue unresolved',
                  'stage':'No consistent compatible linear rate','labour':'No scoped primary hourly quotation'}[item]
            rationale=('Tax basis and points unknown. No zero or legal default selected.' if is_tax else
                       conditional[item]['condition'] if item in conditional else
                       'Need a compatible dated '+item+' quotation or separately declared, supervisor-reviewed simulator-only coefficient; none selected.')
            scope='Active proposal'
        if base and r['unit']!=PARAMETER_UNITS[key]:
            rationale+='; propose canonical '+PARAMETER_UNITS[key]+' for individual paid duration; original wording '+r['unit']+' requires scope review, not a numerical conversion'
        row={'decision_id':r['decision_id'],'event_type':e,'path':path,'parameter':key,
             'unit':PARAMETER_UNITS[key] if base else r['unit'],'original_unit':r['unit'],
             'classification':classification,'assumption_ids':r['assumption_ids'],'observed_candidate_value':observed,
             'proposed_value':proposed,'proposed_min':bounds['min'],'proposed_max':bounds['max'],
             'scope':scope,'evidence_refs':refs,'rationale':rationale,'status':'Pending review',
             'reviewer':None,'reviewer_role':None,'review_date':None,'decision_rationale':None,'decision_evidence_ref':None}
        rows.append(row)
    assert len(rows)==108
    config['minimal_recovery']['numerical_decisions']=rows
    # Existing approvals and all financial cards remain genuinely pending/null.
    assert all(a['status']=='pending' for a in config['formula_approvals'].values())
    assert config['pilot']['scenario_count'] is None and config['pilot']['explicit_user_authorization'] is False
    assert all(p['parameter_approval']['status']=='pending' for p in config['archetypes'].values())
    original_numeric_paths=[r['path'] for r in originals]
    def at(path):
        obj=config
        for k in path.split('.'):
            obj=obj[k]
        return obj
    unresolved_runtime=[p for p in original_numeric_paths if at(p) is None]
    active_unresolved=[r['path'] for r in rows if r['scope']=='Active proposal' and r['proposed_value'] is None]
    assert len(unresolved_runtime)==56 and len(active_unresolved)==28
    assert sum(r['scope'].startswith('Excluded') for r in rows)==28
    assert len({r['path'] for r in rows})==108
    for e in profiles:
        result=evaluate(config,e)
        assert result['status']=='blocked' and result['costs'] is None
    blockers=pilot_execution_blockers(config)
    config['minimal_recovery']['completeness']={
        'original_numeric_slots':108,'specified_non_price_proposals':52,'active_proposal_numeric_slots':80,
        'active_proposal_numeric_nulls':28,'proposed_excluded_numeric_slots':28,'effective_engine_disabled_slots':0,
        'current_engine_numeric_nulls':56,'formulas_pending':19,'formal_numeric_reviews_pending':108,
        'candidate_complete':False,'frozen_configuration_sha256':None,'stage5_ready_for_explicit_authorization':False}
    save('config/minimal_pilot_candidate.json',config)
    tables={'formulas':formulas,'numerical':rows,'controls':controls,'evidence':evidence,
            'summary':config['minimal_recovery']['completeness'],'recommendation_counts':{k:sum(r['recommendation']==k for r in formulas) for k in ['Accept','Modify','Reject']},
            'current_machine_blockers':blockers,'draft_file_sha256':sha('config/minimal_pilot_candidate.json'),
            'draft_canonical_sha256':fingerprint(config),'candidate_complete':False,'frozen_configuration_sha256':None,
            'old_stage4_candidate_unchanged':sha('config/pilot_candidate.json')==config['minimal_recovery']['parent_candidate_sha256']}
    save('work/minimal_pilot_review_tables.json',tables)
    print(json.dumps({k:tables[k] for k in ['summary','recommendation_counts','draft_file_sha256','candidate_complete','old_stage4_candidate_unchanged']},indent=2))


if __name__=='__main__':
    main()
