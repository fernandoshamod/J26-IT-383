"""Planner-only domain extension; frozen datasets, prices and model gates stay intact."""
from copy import deepcopy
import json
from pathlib import Path
from .expense_risk import CalculationOnlyService
from .engine import fingerprint
from .release_input import sha256

ROOT = Path(__file__).resolve().parents[1]
SCOPE = ROOT / 'config/planner_calculator_scope.v0.1.json'


class PlannerCalculationService(CalculationOnlyService):
    def __init__(self):
        super().__init__()
        scope = json.loads(SCOPE.read_text())
        if scope['base_config_file'] != 'config/lkr_research.v2.0.json' or sha256(ROOT / scope['base_config_file']) != scope['base_config_sha256']:
            raise ValueError('planner_scope_base_configuration_hash_mismatch')
        if scope['domain_overrides'] != {'guest_count': [1, 5000], 'venue_area_m2': [.01, 100000000]}:
            raise ValueError('planner_scope_unreviewed_domain_override')
        self.base_domains = deepcopy(self.config['domains'])
        self.base_config_hash = self.config_hash
        self.config = deepcopy(self.config)
        self.config['domains'].update(deepcopy(scope['domain_overrides']))
        self.config['planner_runtime_scope'] = {'version': scope['version'], 'scope_file_sha256': sha256(SCOPE)}
        self.config_hash = fingerprint(self.config)
        self.scope = scope

    def disclosure(self, inputs):
        outside = []
        for field, domain in [('guests', 'guest_count'), ('venue_area_m2', 'venue_area_m2')]:
            lo, hi = self.base_domains[domain]
            if not lo <= inputs[field] <= hi:
                outside.append(field)
        return {'version': self.scope['version'], 'extended_input_fields': outside,
                'original_domains': deepcopy(self.base_domains),
                'runtime_domains': deepcopy(self.config['domains']),
                'rate_or_formula_changes': False, 'model_training_scope_extended': False,
                'statement': ('Extended-scope calculation only: existing generic Wedding/Corporate rates and fixed stage/circulation rules are extrapolated, not calibrated for this event size. ML scores are withheld outside their training support. A small budget does not reduce supplier costs.'
                              if outside else 'Within original calculator input bounds; model support is checked separately. Prices remain reference-based research estimates.')}
