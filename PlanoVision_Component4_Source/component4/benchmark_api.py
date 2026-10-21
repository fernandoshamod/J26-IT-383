"""Strict dashboard transport adapter for advertised package benchmarks."""
from decimal import Decimal

from .engine import money
from .public_package_benchmark import estimate_package


def package_catalog(evidence):
    keys = ['Evidence_ID', 'Provider', 'Event_Scope', 'Package', 'Rate_LKR',
            'Currency', 'Rate_Unit', 'Price_Kind', 'Published_Surcharge',
            'Applicability', 'Inclusions', 'Exclusions_or_Gaps', 'Source_URL']
    return {'api_version': 'benchmark.0.1', 'result_kind': 'public_advertised_evidence_catalog',
            'access_date': evidence['access_date'],
            'is_trained_model_prediction': False,
            'packages': [{key: row.get(key) for key in keys} for row in evidence['rates']]}


def benchmark_request(evidence, payload, *, operation='estimate'):
    if not isinstance(payload, dict):
        raise ValueError('request_must_be_an_object')
    shared = {'evidence_id', 'event_type', 'event_date'}
    if operation == 'estimate':
        allowed, required = shared | {'guests'}, {'evidence_id', 'event_type', 'guests'}
    elif operation == 'compare':
        allowed = shared | {'baseline_guests', 'alternative_guests'}
        required = {'evidence_id', 'event_type', 'baseline_guests', 'alternative_guests'}
    else:
        raise ValueError('unsupported_operation')
    if set(payload) - allowed:
        raise ValueError('unsupported_request_fields:rates_approvals_outcomes_predictions_and_mode_forbidden')
    if required - set(payload):
        raise ValueError('missing_required_request_fields')
    if not isinstance(payload['evidence_id'], str):
        raise ValueError('evidence_id_must_be_a_string')
    when = payload.get('event_date')
    if when is not None and not isinstance(when, str):
        raise ValueError('event_date_must_be_iso_string_or_null')
    def calculate(guests):
        result = estimate_package(evidence, payload['evidence_id'], guests, payload['event_type'], when)
        result['api_version'] = 'benchmark.0.1'
        return result
    if operation == 'estimate':
        return calculate(payload['guests'])
    baseline, alternative = calculate(payload['baseline_guests']), calculate(payload['alternative_guests'])
    delta = float(money(Decimal(str(alternative['known_components_subtotal_lkr'])) -
                        Decimal(str(baseline['known_components_subtotal_lkr']))))
    return {'api_version': 'benchmark.0.1',
            'comparison_kind': 'advertised_package_component_what_if',
            'is_trained_model_prediction': False, 'baseline': baseline,
            'alternative': alternative, 'delta': {
                'planned_guests': payload['alternative_guests'] - payload['baseline_guests'],
                'known_components_subtotal_lkr': delta,
                'full_event_cost_lkr': None, 'profit_lkr': None,
                'space_utilization': None, 'risk_probability': None},
            'full_budget_feasibility': 'unavailable_incomplete_event_costs',
            'explanation': 'Guest quantity changes the selected per-person package component; no separate bundled services are added.'}
