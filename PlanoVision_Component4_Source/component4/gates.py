"""Pilot authorization audit only. There is deliberately no scenario generator."""
from .engine import evaluate,FORMULA_IDS,fingerprint

def pilot_approval_payload(config):
    return {'configuration':{k:v for k,v in config.items() if k!='pilot'},'pilot_scenario_count':config.get('pilot',{}).get('scenario_count')}

def pilot_blockers(config):
    reasons=[];pilot=config.get('pilot',{})
    count=pilot.get('scenario_count')
    if isinstance(count,bool) or not isinstance(count,int) or not 20<=count<=50:reasons.append('pilot_count_must_be_20_to_50')
    if pilot.get('explicit_user_authorization') is not True:reasons.append('explicit_pilot_authorization_missing')
    for key in ['approved_config_sha256','review_record_ref','passing_test_report_ref','sampling_protocol_ref','provenance_protocol_ref']:
        if not pilot.get(key):reasons.append(f'pilot_evidence_missing:{key}')
    if pilot.get('approved_config_sha256') and pilot['approved_config_sha256']!=fingerprint(pilot_approval_payload(config)):reasons.append('approved_pilot_config_hash_mismatch')
    if pilot.get('generator_implementation_verified') is not True:reasons.append('scenario_generator_not_implemented_or_verified')
    if not isinstance(config.get('seed'),int) or isinstance(config.get('seed'),bool):reasons.append('reproducibility_seed_missing')
    for event in ['Wedding','Corporate']:
        result=evaluate(config,event)
        reasons.extend(f'{event}:{x}' for x in result['blockers'])
    if not config.get('source_snapshot_hashes'):reasons.append('source_snapshot_hashes_missing')
    # Uncertainty is not optional for an outcome-labelled simulator pilot.
    for event in ['Wedding','Corporate']:
        shock=config.get('archetypes',{}).get(event,{}).get('outcome_uncertainty',{})
        for key in ['distribution','cost_bounds','revenue_bounds','dependence_spec','approval_ref']:
            if shock.get(key) is None:reasons.append(f'{event}:outcome_uncertainty_missing:{key}')
        anomaly=config.get('archetypes',{}).get(event,{}).get('injected_vendor_regime',{})
        for key in ['prevalence','multiplier_bounds','affected_services','approval_ref']:
            if anomaly.get(key) is None:reasons.append(f'{event}:anomaly_regime_missing:{key}')
    return sorted(set(reasons))
