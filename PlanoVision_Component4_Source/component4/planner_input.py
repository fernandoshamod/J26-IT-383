"""Planner-facing inputs; adapt venue dimensions to the frozen area-based engine."""
import math
from .lkr_research import defaults


def collect_planner_inputs(config, event, baseline=None, venue_dimensions=None,
                           reader=input, writer=print):
    values = dict(baseline or defaults(config, event))
    dimensions = dict(venue_dimensions or {
        'venue_width_m': 20.0,
        'venue_length_m': 25.0,
    })
    labels = {
        'guests': 'Guest count', 'event_hours': 'Event duration (hours)',
        'venue_width_m': 'Venue usable width (metres)',
        'venue_length_m': 'Venue usable length (metres)',
        'target_budget_lkr': 'Expense budget limit (LKR)',
        'retained_receipts_lkr': 'Expected retained client payment (LKR)',
        'min_profit_margin_pct': 'Required minimum profit margin (%)',
    }
    writer('Venue dimensions describe usable rectangular space, not gross building size.')
    values['stage_width_m'] = 4.0
    values['stage_length_m'] = 6.0
    for field, label in labels.items():
        target = dimensions if field.startswith('venue_') else values
        while True:
            raw = reader(f'{label} [Enter={target[field]}]: ').strip().replace(',', '')
            try:
                number = float(raw) if raw else float(target[field])
                if not math.isfinite(number):
                    raise ValueError()
                if field == 'guests':
                    if not number.is_integer():
                        raise ValueError()
                    number = int(number)
                domain = config['domains'].get({'guests': 'guest_count'}.get(field, field))
                if domain:
                    if not domain[0] <= number <= domain[1]:
                        raise ValueError()
                elif number <= 0:
                    raise ValueError()
                target[field] = number
                break
            except ValueError:
                writer('Invalid value: use finite numbers within supported ranges.')
    area = dimensions['venue_width_m'] * dimensions['venue_length_m']
    lower, upper = config['domains']['venue_area_m2']
    if not lower <= area <= upper:
        raise ValueError(f'venue usable area must be {lower}–{upper} m2; entered {area:g} m2')
    values['venue_area_m2'] = area
    writer(f'Calculated usable venue area: {area:g} m2. '
           'This engine checks total area, not detailed layout/egress feasibility.')
    assumptions = config['assumptions']
    available = area - assumptions['fixed_service_circulation_area_m2'] - 24.0
    capacity = max(0, math.floor(available / assumptions['seat_area_m2']))
    used = values['guests'] * assumptions['seat_area_m2'] + assumptions['fixed_service_circulation_area_m2'] + 24.0
    writer(f"Guests per usable m2: {values['guests']/area:.3f}; "
           f"used-area utilization: {100*used/area:.2f}%; "
           f"assumed area-based seating capacity: {capacity} guests.")
    writer('Capacity is an experimental area rule, not a certified venue occupancy limit.')
    return values, dimensions
