"""Model-ready representations of existing records. No scenario generation or fitting."""
from collections import Counter, defaultdict
import csv
from datetime import date
import hashlib
import json
import math
from pathlib import Path

from .dataset_design import audit_split_leakage

BASKET = (
    'Samba - ( Average ):1 Kg.', 'Mysore Dhall - ( Average ):1 Kg.',
    'Wheat Flour:1 Kg.', 'Sugar:1Kg.', 'Coconut Oil:750 ml', 'Broiler:1Kg.',
    'Egg - ( Average ):Each', 'Red Onions - Average:1Kg.',
    'Potatoes - Local:1 Kg', 'Anamalu:1 Kg.',
)
TARGETS = ('Budget_Overrun', 'Profit_Margin_Risk', 'Vendor_Cost_Anomaly')
FEATURES = (
    'Guest_Count', 'Event_Duration_Hours', 'Venue_Area_m2', 'Usable_Area_m2',
    'Seating_Count', 'Stage_Area_m2', 'Space_Utilization', 'Quoted_Catering_Cost',
    'Quoted_AV_Cost', 'Quoted_Venue_Rental_Cost', 'Quoted_Equipment_Rental_Cost',
    'Staff_Count', 'Labor_Hours', 'Quoted_Labor_Cost', 'Initial_Budget',
    'Expected_Revenue', 'Contingency_Reserve', 'Required_Min_Profit_Margin',
    'Forecasted_Total_Cost', 'Event_Type_Wedding', 'Event_Type_Corporate',
)
FORBIDDEN = {'Actual_Total_Cost', 'Actual_Revenue', 'Budget_Utilization', 'Profit',
             'Profit_Margin', 'Cost_Per_Guest', 'Cost_Variance', 'Financial_Health_Score',
             'cost_multiplier', 'receipt_multiplier', 'injected_service', 'injection_multiplier'}
NODE_TYPES = ('Event demand', 'Venue', 'General seating', 'Stage', 'Catering',
              'AV', 'Staffing', 'Equipment', 'Financial plan')
NODE_FEATURES = ('guests', 'event_hours', 'wedding', 'corporate', 'area_m2',
                 'usable_area_m2', 'capacity_persons', 'seats', 'chairs', 'tables',
                 'width_m', 'length_m', 'kits', 'staff', 'paid_hours_per_staff',
                 'weighted_person_hours', 'planned_charge_score', 'budget_score',
                 'expected_receipts_score', 'reserve_score', 'minimum_margin_points',
                 'planned_total_cost_score', 'used_area_m2', 'excluded_area_m2',
                 'service_area_m2', 'circulation_area_m2')
# All edges describe the frozen rules; none describes measured physical adjacency.
EDGE_RULES = (
    (0, 2, 'seating_quantity', 'A008', 1, 'seats/person'),
    (0, 4, 'catering_quantity', 'A013', 1, 'persons/planned_guest'),
    (0, 6, 'staff_and_paid_hours', 'A007,A015', None, None),
    (1, 2, 'capacity_and_area_constraint', 'A010,A012', None, None),
    (1, 3, 'rectangle_and_area_constraint', 'A009,A012', None, None),
    (3, 5, 'av_area_threshold', 'A011', 12, 'm2_threshold'),
    (2, 7, 'furniture_quantity', 'A008,A014', 6, 'seats/table'),
    (1, 8, 'disjoint_planned_expense', 'A001,A020', None, None),
    (3, 8, 'disjoint_planned_expense', 'A001,A014', None, None),
    (4, 8, 'disjoint_planned_expense', 'A001,A013', None, None),
    (5, 8, 'disjoint_planned_expense', 'A001,A011', None, None),
    (6, 8, 'disjoint_planned_expense', 'A001,A015', None, None),
    (7, 8, 'disjoint_planned_expense', 'A001,A014', None, None),
)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows, fields=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = fields or list(rows[0])
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(row.get(k), sort_keys=True) if isinstance(row.get(k), (dict, list)) else row.get(k) for k in keys})


def historical_selection(observations, lineage):
    selected = [r for r in observations if r['closed_calendar_month'] == '1' and
                (r['source_id'] in ('S001', 'S002') or r['series_id'] in {'S003:' + n for n in BASKET})]
    selected.sort(key=lambda r: (r['series_id'], r['ds']))
    expected = {'S003:' + n for n in BASKET}
    if not expected <= {r['series_id'] for r in selected}:
        raise ValueError('missing_selected_food_history')
    ids = {r['observation_id'] for r in selected}
    if len(ids) != len(selected):
        raise ValueError('duplicate_observation_id')
    links = [r for r in lineage if r['observation_id'] in ids]
    if {r['observation_id'] for r in links} != ids:
        raise ValueError('incomplete_historical_lineage')
    if any(r['lineage_reconciled'] != '1' or r['synthetic_origin'] != '0' for r in selected):
        raise ValueError('historical_origin_or_reconciliation')
    by_id = defaultdict(list)
    for r in links:
        by_id[r['observation_id']].append(r)
    for row in selected:
        values = [float(r['source_observed_value']) for r in by_id[row['observation_id']]]
        if len(values) != int(row['source_record_count']) or not math.isclose(float(row['y']), math.fsum(values) / len(values), rel_tol=1e-12):
            raise ValueError('monthly_source_arithmetic')
    return selected, links


def chronological_audit(rows, partitions):
    grouped = defaultdict(list)
    mapping = {r['observation_id']: r['partition'] for r in partitions}
    if len(mapping) != len(partitions) or set(mapping) != {r['observation_id'] for r in rows}:
        raise ValueError('chronological_split_scope')
    for row in rows:
        date.fromisoformat(row['ds'])
        if not math.isfinite(float(row['y'])) or float(row['y']) <= 0:
            raise ValueError('historical_invalid_measurement')
        grouped[row['series_id']].append(row)
    coverage = []
    for series, records in sorted(grouped.items()):
        dates = [r['ds'] for r in records]
        months = [int(x[:4]) * 12 + int(x[5:7]) for x in dates]
        if dates != sorted(set(dates)) or any(b - a != 1 for a, b in zip(months, months[1:])):
            raise ValueError('duplicate_or_missing_month:' + series)
        if len({(r['unit'], r['source_id'], r['currency']) for r in records}) != 1:
            raise ValueError('incompatible_series_units')
        ranks = [{'train': 0, 'validation': 1, 'test': 2}[mapping[r['observation_id']]] for r in records]
        if ranks != sorted(ranks):
            raise ValueError('future_training_leakage')
        counts = Counter(mapping[r['observation_id']] for r in records)
        if counts['train'] < 24 or min(counts['validation'], counts['test']) < 6:
            raise ValueError('insufficient_series_history')
        coverage.append({'series_id': series, 'source_id': records[0]['source_id'], 'unit': records[0]['unit'],
                         'currency': records[0]['currency'], 'records': len(records), 'start': dates[0], 'end': dates[-1],
                         **{k: counts[k] for k in ('train', 'validation', 'test')}, 'missing_months': 0,
                         'quality_review_records': sum(r['source_quality_review'] == '1' for r in records),
                         'status': 'technically_eligible_retrospective_univariate_not_trained'})
    return coverage


def make_xgboost(master, provenance):
    if FORBIDDEN & set(FEATURES) or set(TARGETS) & set(FEATURES):
        raise ValueError('forbidden_prediction_feature')
    sources = {r['scenario_id']: r for r in provenance}
    if len(sources) != len(provenance):
        raise ValueError('duplicate_provenance_id')
    result = []
    for row in master:
        source = sources[row['Scenario_ID']]
        r = {'Scenario_ID': row['Scenario_ID'], 'Base_Event_ID': row['Base_Event_ID'],
             'split_group_id': source['split_group_id'], 'split': source['split'],
             'configuration_sha256': source['configuration_sha256']}
        for field in FEATURES:
            value = int(row['Event_Type'] == field.removeprefix('Event_Type_')) if field.startswith('Event_Type_') else row[field]
            if value is None or type(value) not in (float, int) or not math.isfinite(value):
                raise ValueError('invalid_planning_feature:' + field)
            r[field] = value
        r.update({target: int(row[target]) for target in TARGETS})
        result.append(r)
    if len(result) != len(provenance) or len({r['Scenario_ID'] for r in result}) != len(result):
        raise ValueError('xgboost_scope')
    return result


def graph_nodes(planning, model, ledger):
    p, m = planning, model
    charge = {r['service']: r['planned_score'] for r in ledger}
    quantities = {r['service']: r['quantity'] for r in ledger}
    values = [
        {'guests': p['guests'], 'event_hours': p['event_hours'], 'wedding': int(p['event_type'] == 'Wedding'), 'corporate': int(p['event_type'] == 'Corporate')},
        {'area_m2': m['venue_width_m'] * m['venue_length_m'], 'usable_area_m2': p['usable_area_m2'], 'capacity_persons': m['capacity_persons'], 'planned_charge_score': charge['venue_fixed'], 'used_area_m2': p['used_area_m2'], 'excluded_area_m2': m['excluded_area_m2'], 'service_area_m2': m['service_area_m2'], 'circulation_area_m2': m['circulation_area_m2']},
        {'seats': p['seats'], 'tables': p['tables'], 'chairs': quantities['chairs'], 'area_m2': p['seats'] * m['seat_zone_m2']},
        {'width_m': p['stage_width_m'], 'length_m': p['stage_length_m'], 'area_m2': quantities['stage'], 'planned_charge_score': charge['stage']},
        {'guests': quantities['catering'], 'planned_charge_score': charge['catering']},
        {'kits': quantities['av'], 'planned_charge_score': charge['av']},
        {'staff': p['staff'], 'paid_hours_per_staff': p['paid_hours_per_staff'], 'weighted_person_hours': quantities['labour'], 'planned_charge_score': charge['labour']},
        {'chairs': quantities['chairs'], 'tables': quantities['tables'], 'planned_charge_score': charge['chairs'] + charge['tables']},
        {'budget_score': p['budget_score'], 'expected_receipts_score': p['retained_receipts_score'], 'reserve_score': p['reserve_score'], 'minimum_margin_points': m['minimum_margin_points'], 'planned_total_cost_score': p['planned_cost_score']},
    ]
    if not math.isclose(math.fsum(v.get('planned_charge_score', 0) for v in values), p['planned_cost_score'], rel_tol=1e-12, abs_tol=1e-12):
        raise ValueError('graph_expense_double_charging')
    return [{k: v.get(k) for k in NODE_FEATURES} for v in values]


def preserved_split_audit(provenance):
    records = [{**r, 'source_dependency_ids': json.loads(r['source_dependency_ids']) if isinstance(r['source_dependency_ids'], str) else r['source_dependency_ids']} for r in provenance]
    audit = audit_split_leakage(records, {r['scenario_id']: r['split'] for r in records}, 'conditional_in_simulator')
    if audit['status'] != 'PASS':
        raise ValueError('inherited_split_leakage')
    return audit
