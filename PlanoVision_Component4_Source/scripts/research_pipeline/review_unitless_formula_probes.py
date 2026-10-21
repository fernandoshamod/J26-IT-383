"""Read-only technical review probes. Mock calculations only; no files/approvals written."""
from copy import deepcopy
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from component4.engine import fingerprint
from component4.unitless_experiment import evaluate_unitless_test, validate_unitless_config
from component4.unitless_pilot import generate_test

root = Path(__file__).resolve().parents[2]
c = json.loads((root / 'config/unitless_pilot_candidate.json').read_text())
c['record_kind'] = 'mock_unitless_test'
c['origin'] = 'FORMULA_REVIEW_PROBE_NOT_AUTHORIZED_PILOT'
reordered = deepcopy(c)
reordered['proposed_pilot']['archetype_root_quotas'] = {'Corporate': 2, 'Wedding': 3}
a, b = generate_test(c), generate_test(reordered)
inputs = {'guests': 100, 'event_hours': 4, 'stage_width_m': 4, 'stage_length_m': 3,
          'budget_score': 3, 'retained_receipts_score': 3}
base = evaluate_unitless_test(c, 'Wedding', inputs)
below_one = deepcopy(c); below_one['overtime_multiplier'] = .5
print(json.dumps({
    'origin': 'MOCK_ONLY_NO_PILOT_EXECUTION',
    'quota_order_counterexample': {
        'canonical_hash_equal': fingerprint(c) == fingerprint(reordered),
        'scenario_ids_equal': [r['scenario_id'] for r in a['planning']] == [r['scenario_id'] for r in b['planning']],
        'planning_equal': a['planning'] == b['planning'],
        'original_first_event': a['planning'][0]['event_type'],
        'reordered_first_event': b['planning'][0]['event_type']},
    'baseline_arithmetic': {k: base[k] for k in ('planned_cost_score','reserve_score','planned_profit_score','margin_points','staff','tables','used_area_m2')},
    'unitless_validator_accepts_overtime_multiplier_below_one': validate_unitless_config(below_one),
    'candidate_max_used_area_m2': 180*1.5+30+24+60,
    'candidate_usable_area_m2': 24*18-32,
    'candidate_max_paid_hours': 6+1+1,
    'candidate_regular_hours_limit': 8,
    'files_written': False, 'approvals_created': False
}, indent=2))
