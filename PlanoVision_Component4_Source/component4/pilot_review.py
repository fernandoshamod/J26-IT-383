"""Read-only scientific diagnostics for the authorized unitless pilot.

Sensitivity evaluations are deterministic calculator probes, not new dataset rows.
No coefficient fitting, sampling, authorization updates or scenario writer.
"""
from collections import Counter
from statistics import mean, median
import math

from .diagnostic_design import validate_diagnostic_design
from .unitless_experiment import _calculate_unitless, validate_unitless_config
from .unitless_pilot import validate_bundle

INPUTS = ('guests', 'event_hours', 'stage_width_m', 'stage_length_m',
          'budget_score', 'retained_receipts_score')


def summarize(values):
    values = [x for x in values if x is not None]
    if not values or any(not math.isfinite(x) for x in values):
        raise ValueError('finite_nonempty_distribution_required')
    return {'n': len(values), 'min': min(values), 'median': median(values),
            'mean': mean(values), 'max': max(values)}


def review(bundle):
    validate_bundle(bundle)
    c = bundle['configuration']
    validate_unitless_config(c)
    validate_diagnostic_design(c)
    plans = bundle['planning']
    # Distinct planning configurations, not duplicated outcome replications.
    unique = list({(p['family_id'], p['planning_state']): p for p in plans}.values())
    distributions = {}
    for event in ('Wedding', 'Corporate'):
        subset = [p for p in unique if p['event_type'] == event]
        distributions[event] = {key: summarize([p[key] for p in subset]) for key in (
            'guests', 'event_hours', 'paid_hours_per_staff', 'staff', 'tables',
            'planned_cost_score', 'budget_score', 'reserve_score',
            'retained_receipts_score', 'planned_profit_score', 'planned_margin_points')}
        for key, values in {
            'stage_area_m2': [p['stage_width_m'] * p['stage_length_m'] for p in subset],
            'area_utilization_percent': [100 * p['used_area_m2'] / p['usable_area_m2'] for p in subset],
            'capacity_utilization_percent': [100 * p['guests'] / c['capacity_persons'] for p in subset],
        }.items():
            distributions[event][key] = summarize(values)
        ids = {p['scenario_id'] for p in plans if p['event_type'] == event}
        distributions[event]['planned_service_costs'] = {
            service: summarize([x['planned_score'] for x in bundle['line_items']
                                if x['service'] == service and x['scenario_id'] in ids])
            for service in c['coefficients']}
        distributions[event]['simulated_outcomes'] = {
            key: summarize([x[key] for x in bundle['outcomes'] if x['scenario_id'] in ids])
            for key in ('simulated_cost_score', 'simulated_receipts_score',
                        'simulated_profit_score', 'simulated_margin_points')}
    dependencies = []
    sensitivity = []
    for family in c['diagnostic_families']:
        event = family['event_type']
        results = {s['name']: _calculate_unitless(c, event, s['inputs']) for s in family['states']}
        lo, base, hi = (results[k] for k in ('lower_intervention', 'baseline', 'upper_intervention'))
        kind = family['diagnostic']
        if kind == 'guest_threshold':
            valid = (lo['line_items_score']['catering'] < base['line_items_score']['catering'] < hi['line_items_score']['catering']
                     and hi['tables'] > base['tables'] and hi['staff'] > base['staff'])
        elif kind == 'av_threshold':
            valid = [lo['quantities']['av'], base['quantities']['av'], hi['quantities']['av']] == [1, 1, 2]
        elif kind == 'overtime_threshold':
            valid = (lo['paid_hours_per_staff'] < base['paid_hours_per_staff'] < hi['paid_hours_per_staff']
                     and hi['line_items_score']['labour'] - base['line_items_score']['labour'] >
                     base['line_items_score']['labour'] - lo['line_items_score']['labour'])
        else:
            valid = (lo['planned_cost_score'] == base['planned_cost_score'] == hi['planned_cost_score']
                     and lo['planned_budget_breach'] and not hi['planned_budget_breach'])
        dependencies.append({'event': event, 'diagnostic': kind, 'passed': valid,
                             'lower': lo, 'baseline': base, 'upper': hi})
        baseline = family['states'][0]['inputs']
        for key in INPUTS:
            domain = (range(c['profiles'][event]['guest_min'], c['profiles'][event]['guest_max'] + 1)
                      if key == 'guests' else c['profiles'][event][key])
            accepted, rejected = [], Counter()
            for value in domain:
                try:
                    accepted.append(_calculate_unitless(c, event, {**baseline, key: value}))
                except ValueError as exc:
                    rejected[str(exc)] += 1
            sensitivity.append({'event': event, 'diagnostic': kind, 'changed_input': key,
                                'attempts': len(domain), 'accepted': len(accepted),
                                'rejected': dict(rejected),
                                'cost_range': summarize([r['planned_cost_score'] for r in accepted]) if accepted else None,
                                'area_range': summarize([r['used_area_m2'] for r in accepted]) if accepted else None,
                                'planned_budget_breaches': sum(r['planned_budget_breach'] for r in accepted)})
    if not all(x['passed'] for x in dependencies):
        raise ValueError('dependency_diagnostic_failed')
    return {'internal_status': 'PASS', 'real_world_validated': False,
            'rows': len(plans), 'planning_configurations': len(unique),
            'families': len({p['family_id'] for p in plans}),
            'independent_population_sample_size': None,
            'outcome_random_streams': len({(p['family_id'], p['outcome_replication']) for p in plans}),
            'distributions': distributions, 'dependencies': dependencies, 'sensitivity': sensitivity,
            'label_counts': {k: dict(Counter(str(x[k]) for x in bundle['outcomes'])) for k in (
                'simulated_budget_overrun', 'simulated_profit_margin_risk', 'simulated_vendor_cost_anomaly')},
            'pilot_rejected_attempts': len(bundle['rejections']),
            'bulk_generation_authorized': False, 'model_training_authorized': False}
