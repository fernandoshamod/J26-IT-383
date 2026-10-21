"""Isolated dimensionless planning calculation. No rates, LKR conversion, RNG or file writer."""
from decimal import Decimal
import math
from .engine import fingerprint

VERSION = 'unitless-design.0.1-proposed'
SERVICES = ('catering', 'chairs', 'tables', 'stage', 'av', 'labour', 'venue_fixed')
DISABLED = ('lighting', 'venue_hourly', 'security', 'decoration', 'transport', 'misc', 'equipment_other')


def _number(x, name, minimum=0, integer=False):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or x < minimum or (integer and not isinstance(x, int)):
        raise ValueError('invalid_or_missing:' + name)
    return x


def validate_unitless_config(config):
    if (not isinstance(config, dict) or config.get('cost_unit') != 'dimensionless_score' or config.get('currency') is not None
        or config.get('market_conversion_factor') is not None):
        raise ValueError('unitless_currency_contract_required')
    if config.get('record_kind') not in ('hypothetical_unitless_proposal', 'mock_unitless_test'):
        raise ValueError('explicit_unitless_origin_required')
    if set(config.get('disabled_services', [])) != set(DISABLED):
        raise ValueError('explicit_disabled_scope_required')
    coeff = config.get('coefficients')
    reference = config.get('reference_quantities')
    if not isinstance(coeff, dict) or not isinstance(reference, dict) or set(coeff) != set(SERVICES) or set(reference) != set(SERVICES):
        raise ValueError('exact_disjoint_unitless_services_required')
    for item in SERVICES:
        _number(coeff[item], 'coefficient.' + item)
        _number(reference[item], 'reference.' + item, minimum=1e-12)
    for key in ('venue_width_m', 'venue_length_m', 'excluded_area_m2', 'seat_zone_m2', 'service_area_m2',
                'circulation_area_m2', 'capacity_persons', 'seats_per_table', 'base_staff', 'guests_per_staff',
                'setup_hours', 'clearance_hours', 'regular_hours_limit', 'overtime_multiplier', 'reserve_ratio', 'minimum_margin_points'):
        _number(config.get(key), key, minimum=1e-12 if key in ('venue_width_m', 'venue_length_m', 'seat_zone_m2', 'seats_per_table', 'guests_per_staff', 'overtime_multiplier') else 0,
                integer=key in ('capacity_persons', 'seats_per_table', 'base_staff', 'guests_per_staff'))
    if not 0 <= config['reserve_ratio'] <= 1 or not 0 <= config['minimum_margin_points'] <= 100:
        raise ValueError('policy_bounds_invalid')
    if config['venue_width_m'] * config['venue_length_m'] <= config['excluded_area_m2']:
        raise ValueError('usable_area_invalid')
    if config.get('geometry_origin') != 'hypothetical_not_measured':
        raise ValueError('truthful_hypothetical_geometry_required')
    if set(config.get('profiles', {})) != {'Wedding', 'Corporate'}:
        raise ValueError('two_profiles_required')
    for event, p in config['profiles'].items():
        lo = _number(p.get('guest_min'), event + '.guest_min', minimum=1, integer=True)
        hi = _number(p.get('guest_max'), event + '.guest_max', minimum=1, integer=True)
        if lo > hi or hi > config['capacity_persons']:
            raise ValueError('guest_bounds_invalid')
        for key in ('event_hours', 'stage_width_m', 'stage_length_m', 'budget_score', 'retained_receipts_score'):
            values = p.get(key)
            if not isinstance(values, list) or not values or len(values) != len(set(values)):
                raise ValueError('nonempty_unique_domain_required:' + key)
            for x in values:
                _number(x, event + '.' + key, minimum=0 if 'score' in key else 1e-12)
    outcome = config.get('outcome_proposal', {})
    for key in ('ordinary_common_cost_multiplier', 'independent_receipt_multiplier', 'injection_multiplier'):
        bounds = outcome.get(key)
        if not isinstance(bounds, list) or len(bounds) != 2:
            raise ValueError('bounded_outcome_required:' + key)
        lo = _number(bounds[0], key + '.min', minimum=1e-12)
        hi = _number(bounds[1], key + '.max', minimum=1e-12)
        if lo > hi or (key == 'injection_multiplier' and lo <= 1):
            raise ValueError('invalid_outcome_bounds:' + key)
    if _number(outcome.get('injection_prevalence'), 'injection_prevalence') > 1:
        raise ValueError('prevalence_out_of_bounds')
    targets = outcome.get('eligible_services')
    if not isinstance(targets, list) or not targets or len(set(targets)) != len(targets) or not set(targets) <= set(SERVICES):
        raise ValueError('disjoint_positive_injection_scope_required')
    if any(coeff[k] <= 0 for k in targets):
        raise ValueError('positive_injection_coefficients_required')
    pilot = config.get('proposed_pilot', {})
    for key in ('rows', 'roots', 'planning_states_per_root', 'outcome_replications_per_state', 'seed'):
        _number(pilot.get(key), 'pilot.' + key, minimum=0 if key == 'seed' else 1, integer=True)
    quotas = pilot.get('archetype_root_quotas')
    if quotas is not None:
        if set(quotas) != {'Wedding', 'Corporate'} or any(isinstance(v, bool) or not isinstance(v, int) or v < 1 for v in quotas.values()) or sum(quotas.values()) != pilot['roots']:
            raise ValueError('archetype_quota_mismatch')
    elif _number(pilot.get('roots_per_archetype'), 'roots_per_archetype', 1, True) * 2 != pilot['roots']:
        raise ValueError('archetype_quota_mismatch')
    if pilot['rows'] != pilot['roots'] * pilot['planning_states_per_root'] * pilot['outcome_replications_per_state'] or not 20 <= pilot['rows'] <= 50:
        raise ValueError('diagnostic_scope_count_mismatch')
    return True


def unitless_review_payload(config):
    return {k: v for k, v in config.items() if k not in ('review', 'pilot_authorization')}


def unitless_pilot_blockers(config):
    """Honest current readiness: production stochastic/writer path has not been implemented."""
    result = []
    try:
        validate_unitless_config(config)
    except (ValueError, TypeError) as exc:
        result.append(str(exc))
    if not isinstance(config, dict):
        return result + ['unitless_configuration_object_required']
    review = config.get('review', {})
    if review.get('status') != 'approved' or not all(review.get(k) for k in ('reviewer', 'role', 'date', 'rationale', 'evidence_ref')):
        result.append('unitless_methodology_approval_missing')
    if review.get('approved_payload_sha256') != fingerprint(unitless_review_payload(config)):
        result.append('unitless_review_hash_missing_or_mismatched')
    a = config.get('pilot_authorization', {})
    count = a.get('scenario_count')
    if isinstance(count, bool) or not isinstance(count, int) or not 20 <= count <= 50:
        result.append('unitless_pilot_count_20_to_50_required')
    if a.get('explicit_authorization') is not True:
        result.append('explicit_unitless_pilot_authorization_missing')
    result.append('unitless_stochastic_generator_and_authorized_writer_not_implemented')
    return sorted(set(result))


def evaluate_unitless_test(config, event, inputs):
    """Test-only arithmetic path; proposal objects and normal LKR callers cannot activate it."""
    validate_unitless_config(config)
    if config['record_kind'] != 'mock_unitless_test':
        raise ValueError('test_only_unitless_marker_required')
    return _calculate_unitless(config, event, inputs, 'MOCK_UNITLESS_TEST_NOT_MARKET_DATA')


def _calculate_unitless(config, event, inputs, origin='SYNTHETIC_HYPOTHETICAL_UNITLESS_NOT_MARKET_DATA'):
    """Internal arithmetic reused by the gated generator; never an approval bypass API."""
    if event not in config['profiles']:
        raise ValueError('unsupported_event')
    if set(inputs) != {'guests', 'event_hours', 'stage_width_m', 'stage_length_m', 'budget_score', 'retained_receipts_score'}:
        raise ValueError('exact_planning_inputs_required')
    p = config['profiles'][event]
    g = _number(inputs['guests'], 'guests', minimum=1, integer=True)
    if not p['guest_min'] <= g <= p['guest_max']:
        raise ValueError('outside_guest_scope')
    for key in ('event_hours', 'stage_width_m', 'stage_length_m', 'budget_score', 'retained_receipts_score'):
        _number(inputs[key], key)
        if inputs[key] not in p[key]:
            raise ValueError('outside_reviewed_test_domain:' + key)
    stage = inputs['stage_width_m'] * inputs['stage_length_m']
    if stage > config.get('maximum_stage_area_m2', 30) or inputs['stage_width_m'] > config['venue_width_m'] or inputs['stage_length_m'] > config['venue_length_m']:
        raise ValueError('stage_geometry_invalid')
    used = g * config['seat_zone_m2'] + stage + config['service_area_m2'] + config['circulation_area_m2']
    usable = config['venue_width_m'] * config['venue_length_m'] - config['excluded_area_m2']
    if g > config['capacity_persons'] or used > usable:
        raise ValueError('capacity_or_area_invalid')
    tables = math.ceil(g / config['seats_per_table'])
    staff = config['base_staff'] + math.ceil(g / config['guests_per_staff'])
    paid = inputs['event_hours'] + config['setup_hours'] + config['clearance_hours']
    regular = min(paid, config['regular_hours_limit'])
    weighted = staff * (regular + max(0, paid - regular) * config['overtime_multiplier'])
    quantities = {'catering': g, 'chairs': g, 'tables': tables, 'stage': stage, 'av': 1 if stage <= config.get('av_breakpoint_m2', 12) else 2,
                  'labour': weighted, 'venue_fixed': 1}
    lines = {k: Decimal(str(config['coefficients'][k])) * Decimal(str(q)) / Decimal(str(config['reference_quantities'][k]))
             for k, q in quantities.items()}
    total = sum(lines.values(), Decimal(0))
    reserve = total * Decimal(str(config['reserve_ratio']))
    budget = Decimal(str(inputs['budget_score']))
    receipts = Decimal(str(inputs['retained_receipts_score']))
    if budget < reserve:
        raise ValueError('budget_below_reserve')
    profit = receipts - total
    return {'origin': origin, 'cost_unit': 'dimensionless_score', 'currency': None,
            'line_items_score': {k: float(v) for k, v in lines.items()}, 'planned_cost_score': float(total),
            'planned_profit_score': float(profit), 'reserve_score': float(reserve),
            'margin_points': float(100 * profit / receipts) if receipts > 0 else None,
            'used_area_m2': used, 'usable_area_m2': usable, 'staff': staff, 'tables': tables,
            'quantities': quantities, 'paid_hours_per_staff': paid,
            'planned_budget_breach': total > budget, 'is_observed_event': False, 'is_trained_prediction': False}
