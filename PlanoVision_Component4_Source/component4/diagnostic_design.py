"""Predeclared, purposive diagnostic planning states; no outcomes or writer."""
from .unitless_experiment import _calculate_unitless


def validate_diagnostic_design(config):
    families = config.get('diagnostic_families')
    expected = [('Wedding', 'guest_threshold'), ('Wedding', 'av_threshold'),
                ('Wedding', 'overtime_threshold'), ('Corporate', 'guest_threshold'),
                ('Corporate', 'budget_intervention')]
    if not isinstance(families, list) or len(families) != 5:
        raise ValueError('five_diagnostic_families_required')
    if config['proposed_pilot']['archetype_root_quotas'] != {'Wedding': 3, 'Corporate': 2}:
        raise ValueError('diagnostic_event_quota_mismatch')
    if config.get('planning_states') != ['baseline', 'lower_intervention', 'upper_intervention']:
        raise ValueError('diagnostic_state_policy_required')
    seen = set()
    for family, (event, kind) in zip(families, expected):
        if family.get('event_type') != event or family.get('diagnostic') != kind:
            raise ValueError('diagnostic_family_scope_or_order_mismatch')
        states = family.get('states')
        if not isinstance(states, list) or len(states) != 3 or [x.get('name') for x in states] != config['planning_states']:
            raise ValueError('three_named_diagnostic_states_required')
        inputs = [x['inputs'] for x in states]
        results = [_calculate_unitless(config, event, x) for x in inputs]
        signature = (event, tuple(sorted(inputs[0].items())))
        if signature in seen:
            raise ValueError('duplicate_diagnostic_base')
        seen.add(signature)
        key = {'guest_threshold': 'guests', 'av_threshold': 'stage_length_m',
               'overtime_threshold': 'event_hours', 'budget_intervention': 'budget_score'}[kind]
        if any({k: v for k, v in x.items() if k != key} != {k: v for k, v in inputs[0].items() if k != key} for x in inputs[1:]):
            raise ValueError('one_factor_intervention_required')
        if not inputs[1][key] < inputs[0][key] < inputs[2][key]:
            raise ValueError('ordered_diagnostic_interventions_required')
        if kind == 'guest_threshold':
            g = inputs[0]['guests']
            if inputs[1][key] != g - 1 or inputs[2][key] != g + 1 or g % config['seats_per_table'] or g % config['guests_per_staff']:
                raise ValueError('joint_seating_staff_boundary_required')
            if not results[2]['tables'] > results[0]['tables'] or not results[2]['staff'] > results[0]['staff']:
                raise ValueError('guest_dependency_coverage_missing')
        elif kind == 'av_threshold':
            if inputs[0]['stage_width_m'] * inputs[0]['stage_length_m'] != config['av_breakpoint_m2'] or [r['quantities']['av'] for r in results] != [1, 1, 2]:
                raise ValueError('av_threshold_coverage_missing')
        elif kind == 'overtime_threshold':
            if results[0]['paid_hours_per_staff'] != config['regular_hours_limit'] or not results[1]['paid_hours_per_staff'] < config['regular_hours_limit'] < results[2]['paid_hours_per_staff']:
                raise ValueError('overtime_boundary_coverage_missing')
        elif kind == 'budget_intervention':
            if results[1]['planned_budget_breach'] is not True or results[2]['planned_budget_breach'] is not False:
                raise ValueError('budget_feasibility_coverage_missing')
            if len({r['planned_cost_score'] for r in results}) != 1:
                raise ValueError('budget_must_not_change_cost')
    return True
