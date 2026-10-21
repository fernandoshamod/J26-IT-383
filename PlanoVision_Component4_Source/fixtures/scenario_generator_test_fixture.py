"""In-memory software fixture factory. None of these numbers are calibrated market data.

Never copy this factory's arbitrary domains, fake references or existing mock rates to a
live configuration. It creates NO approvals and NO persistent event records.
"""
import json
from pathlib import Path

from component4.generator_validation import (CODE_FILES, EVENTS, GENERATOR_VERSION,
    PARAMETER_UNITS, REQUIRED_ASSUMPTIONS, file_snapshots, software_versions)

ROOT = Path(__file__).resolve().parents[1]


def fixed(value,unit):
    return {'distribution':'fixed','unit':unit,'values':[value]}


def fixture_configuration():
    config = json.loads((ROOT/'fixtures/config.mock_test_only.json').read_text(encoding='utf-8'))
    snapshots = file_snapshots(ROOT,['fixtures/config.mock_test_only.json'])
    config.update(seed=314159,source_snapshot_hashes=snapshots,calibration_cutoff='2026-10-01')
    profiles = {}
    for event in EVENTS:
        profile = config['archetypes'][event]
        profile['geometry_origin'] = 'mock_test_fixture'
        profile['revenue_mode'] = 'retained_contract_receipts'
        profile['date_bounds'] = {'start':'2026-10-20','end':'2026-10-23'}
        profile['outcome_uncertainty'] = {
            'distribution':'bounded_uniform_multipliers',
            'cost_bounds':{'min':0.9,'max':1.1,'unit':'multiplier'},
            'revenue_bounds':{'min':0.9,'max':1.1,'unit':'multiplier'},
            'dependence_spec':{'mode':'independent','cost_services':['catering','labour','venue_fixed']},
            'approval_ref':'TEST-ONLY-NOT-APPROVAL'}
        profile['injected_vendor_regime'] = {
            'prevalence':0.25,'multiplier_bounds':{'min':1.1,'max':1.5,'unit':'multiplier'},
            'affected_services':['catering'],'approval_ref':'TEST-ONLY-NOT-APPROVAL'}
        profiles[event] = {
            'date_bounds':profile['date_bounds'].copy(),
            'parameter_domains':{
                'guest_count':{'distribution':'uniform_integer','unit':'persons','min':50,'max':140},
                'event_hours':{'distribution':'choice','unit':'hours','values':[4,6,8]},
                'stage_width_m':{'distribution':'choice','unit':'m','values':[4,5,6]},
                'stage_length_m':fixed(4,'m')},
            'budget_policy':{'mode':'planned_cost_factor','factor':{'distribution':'choice','unit':'multiplier','values':[0.85,1,1.2]},
                             'reference_budget_lkr':1000000},
            'retained_receipts':{'distribution':'choice','unit':'LKR','values':[0,100000,180000,250000]},
            'ancestry':{'venue_profile_id':'MOCK-VENUE-NOT-A-MEASURED-LAYOUT',
                        'vendor_rate_card_id':'MOCK-RATES-NOT-QUOTATIONS','archetype_template_id':'MOCK-'+event}}
    config['scenario_generator'] = {
        'version':GENERATOR_VERSION,'record_kind':'mock_test_fixture','seed':314159,
        'max_attempts_per_scenario':12,'archetype_weights':{'Wedding':0.5,'Corporate':0.5},
        'parameter_units':PARAMETER_UNITS.copy(),'profiles':profiles,
        'source_snapshot_hashes':snapshots,'code_snapshot_hashes':file_snapshots(ROOT,CODE_FILES),
        'software_versions':software_versions(),'assumption_version':'TEST-ONLY-NOT-APPROVED',
        'assumption_ids':sorted(REQUIRED_ASSUMPTIONS),'outcome_design_label':'hypothetical_not_calibrated'}
    return config
