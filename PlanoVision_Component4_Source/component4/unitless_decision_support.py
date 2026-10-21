"""Research-only planning, saved-model inference and paired Monte Carlo.

No LKR conversion, fitting, dataset writing, approval mutation or health score.
"""
from copy import deepcopy
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile
import numpy as np

from .engine import fingerprint
from .unitless_experiment import _calculate_unitless
from .unitless_pilot import validate as validate_model_config
from .release_input import verified_release, sha256

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('guests','event_hours','stage_width_m','stage_length_m','budget_score','retained_receipts_score')
TARGETS = ('Budget_Overrun','Profit_Margin_Risk')
RUN = 'financial_risk_v1_1_20261012'
WARNING = 'HYPOTHETICAL UNITLESS RESEARCH — NOT LKR QUOTATIONS, OBSERVED OUTCOMES OR VALIDATED REAL-WORLD RISK'


def controls(draws, seed):
    if type(draws) is not int or not 100 <= draws <= 10000:
        raise ValueError('draws_must_be_integer_100_to_10000')
    if type(seed) is not int or not 0 <= seed <= 2**32-1:
        raise ValueError('seed_must_be_uint32')


def draw_shocks(config, draws, seed):
    controls(draws, seed)
    policy = config['outcome_proposal']
    rng = np.random.Generator(np.random.PCG64(seed))
    # All fixed-size draws precede any calculation; alternatives share these arrays.
    return {'cost':rng.uniform(*policy['ordinary_common_cost_multiplier'],draws),
            'receipts':rng.uniform(*policy['independent_receipt_multiplier'],draws),
            'injected':rng.random(draws) < policy['injection_prevalence'],
            'service_index':rng.integers(len(policy['eligible_services']),size=draws),
            'injection':rng.uniform(*policy['injection_multiplier'],draws)}


def monte_carlo(config, inputs, plan, shocks):
    costs = np.zeros(len(shocks['cost']))
    for service, amount in plan['line_items_score'].items():
        injected = np.zeros(len(costs), dtype=bool)
        if service in config['outcome_proposal']['eligible_services']:
            position = config['outcome_proposal']['eligible_services'].index(service)
            injected = shocks['injected'] & (shocks['service_index'] == position)
        costs += amount * shocks['cost'] * np.where(injected,shocks['injection'],1.)
    revenue = inputs['retained_receipts_score'] * shocks['receipts']
    profit = revenue-costs
    margin = np.divide(100*profit,revenue,out=np.full(len(costs),np.nan),where=revenue>0)
    return {'cost':costs,'revenue':revenue,'profit':profit,'margin':margin,
            'overrun':costs > inputs['budget_score'],
            'margin_risk':margin < config['minimum_margin_points']}


def distribution(values):
    if not np.isfinite(values).all():
        return None
    return {'mean':float(np.mean(values)), 'p05':float(np.quantile(values,.05)),
            'p50':float(np.quantile(values,.5)), 'p95':float(np.quantile(values,.95))}


def model_features(config,event,inputs,plan,predictors):
    lines = plan['line_items_score']
    values = {'Guest_Count':inputs['guests'],'Event_Duration_Hours':inputs['event_hours'],
        'Venue_Area_m2':config['venue_width_m']*config['venue_length_m'],'Usable_Area_m2':plan['usable_area_m2'],
        'Seating_Count':inputs['guests'],'Stage_Area_m2':inputs['stage_width_m']*inputs['stage_length_m'],
        'Space_Utilization':plan['used_area_m2']/plan['usable_area_m2'],'Quoted_Catering_Cost':lines['catering'],
        'Quoted_AV_Cost':lines['av'],'Quoted_Venue_Rental_Cost':lines['venue_fixed'],
        'Quoted_Equipment_Rental_Cost':lines['chairs']+lines['tables']+lines['stage'],
        'Staff_Count':plan['staff'],'Labor_Hours':plan['paid_hours_per_staff']*plan['staff'],
        'Quoted_Labor_Cost':lines['labour'],'Initial_Budget':inputs['budget_score'],
        'Expected_Revenue':inputs['retained_receipts_score'],'Contingency_Reserve':plan['reserve_score'],
        'Required_Min_Profit_Margin':config['minimum_margin_points'],'Forecasted_Total_Cost':plan['planned_cost_score'],
        'Event_Type_Wedding':int(event=='Wedding'),'Event_Type_Corporate':int(event=='Corporate')}
    if set(values) != set(predictors):
        raise ValueError('model_feature_contract_mismatch')
    return values


class UnitlessDecisionSupport:
    def __init__(self):
        from xgboost import Booster
        archive, release = verified_release()
        self.archive, self.archive_sha = archive, release['release_archive']['sha256']
        names = ['data/final/unitless-bulk-v0.1/configuration.json',
                 'prepared/xgboost/feature_specification.json','prepared/xgboost/xgboost_risk_dataset.csv']
        with zipfile.ZipFile(archive) as source:
            manifest = json.loads(source.read('package_manifest.json'))
            payload = {name:source.read(name) for name in names}
        if any(hashlib.sha256(payload[name]).hexdigest()!=manifest['files'][name] for name in names):
            raise ValueError('frozen_input_checksum_mismatch')
        bulk = json.loads(payload[names[0]])
        self.configuration_sha = fingerprint(bulk)
        if self.configuration_sha != release['configuration']['canonical_sha256']:
            raise ValueError('frozen_configuration_hash_mismatch')
        self.config = bulk['financial_model']
        validate_model_config(self.config)
        self.spec = json.loads(payload[names[1]])
        rows = list(csv.DictReader(io.StringIO(payload[names[2]].decode('utf-8-sig'))))
        report = ROOT / 'reports/experiments/v1.1' / RUN
        output = ROOT / 'outputs/experiments/v1.1' / RUN
        summary = json.loads((report/'experiment_summary.json').read_text())
        overlay_path = Path(summary['split_overlay']['path'])
        if sha256(overlay_path)!=summary['split_overlay']['sha256']:
            raise ValueError('model_split_overlay_changed')
        overlay = json.loads(overlay_path.read_text())
        training = {r['Scenario_ID'] for r in overlay['assignments'] if r['split']=='train'}
        hashes = {}
        for line in (report/'checksums.sha256').read_text().splitlines():
            digest,name = line.split('  ',1)
            hashes[(ROOT/name).resolve()] = digest
        protocol_path = output/'experiment_protocol.json'
        if any(sha256(p)!=hashes.get(p.resolve()) for p in (report/'experiment_summary.json',protocol_path)):
            raise ValueError('model_protocol_or_summary_changed')
        protocol = json.loads(protocol_path.read_text())
        if (protocol['archive_sha256']!=self.archive_sha or summary['release_before_sha256']!=self.archive_sha
            or protocol['input_member_sha256'].get(names[1])!=manifest['files'][names[1]]):
            raise ValueError('model_frozen_configuration_or_feature_origin_mismatch')
        self.models, self.model_hashes, self.support = {}, {}, {}
        for target in TARGETS:
            path = (output/(target+'.xgboost.json')).resolve()
            if summary['selected_models'][target]['model']!='xgboost' or sha256(path)!=hashes.get(path):
                raise ValueError('saved_model_not_verified')
            model = Booster()
            model.load_model(bytearray(path.read_bytes()))
            if model.num_features()!=len(self.spec['predictors']):
                raise ValueError('saved_model_feature_count_mismatch')
            self.models[target] = model
            self.model_hashes[target] = sha256(path)
        for event in ('Wedding','Corporate'):
            subset = [r for r in rows if r['Scenario_ID'] in training and r['Event_Type_'+event]=='1']
            self.support[event] = {f:(min(float(r[f]) for r in subset),max(float(r[f]) for r in subset)) for f in self.spec['predictors']}

    def provenance(self, draws, seed):
        return {'warning':WARNING,'cost_unit':'dimensionless_score','currency':None,
            'configuration_sha256':self.configuration_sha,'release_sha256':self.archive_sha,
            'model_run':RUN,'model_sha256':deepcopy(self.model_hashes),'numpy_version':np.__version__,
            'simulation_method':'PCG64; frozen bounded_uniform shock rules; paired common random draws',
            'draws':draws,'seed':seed,'observed_event_outcomes':False,
            'scientific_limitations':['19 formulas independently unvalidated','shared hypothetical templates',
                'uncalibrated model scores','retrospective exploratory training evaluation',
                'simulation quantiles are not calibrated real-world prediction intervals']}

    def _evaluate(self,event,inputs,shocks):
        if event not in ('Wedding','Corporate'):
            raise ValueError('unsupported_event_type')
        if not isinstance(inputs,dict) or set(inputs)!=set(FIELDS):
            raise ValueError('exact_six_planning_inputs_required')
        for name,value in inputs.items():
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
                raise ValueError('finite_numeric_input_required:'+name)
        result = {'status':'blocked','event_type':event,'inputs':deepcopy(inputs),'planned':None,
                  'model_risk_scores':None,'monte_carlo':None,'financial_health_score':None,
                  'warnings':[],'blockers':[]}
        try:
            plan = _calculate_unitless(self.config,event,inputs)
        except ValueError as exc:
            result['blockers']=[str(exc)]
            return result,None
        features = model_features(self.config,event,inputs,plan,self.spec['predictors'])
        unsupported = [f for f,v in features.items() if not self.support[event][f][0]-1e-9 <= v <= self.support[event][f][1]+1e-9]
        scores = {'origin':'saved_XGBoost_uncalibrated_classifier_scores', 'calibrated':False,
                  'Budget_Overrun':None,'Profit_Margin_Risk':None,'Vendor_Cost_Anomaly':None,
                  'model_support_status':'outside_training_feature_bounds' if unsupported else 'within_feature_bounds_not_proof_of_joint_support',
                  'out_of_support_features':unsupported}
        if not unsupported:
            from xgboost import DMatrix
            matrix = DMatrix(np.array([[features[f] for f in self.spec['predictors']]],dtype=np.float64))
            for target in TARGETS:
                score = float(self.models[target].predict(matrix)[0])
                if not math.isfinite(score) or not 0<=score<=1:
                    raise ValueError('invalid_model_score')
                scores[target]=score
        else:
            result['warnings'].append('Model scores unavailable outside marginal training support; Monte Carlo remains hypothetical.')
        simulation = monte_carlo(self.config,inputs,plan,shocks)
        operating = inputs['budget_score']-plan['reserve_score']
        result.update(status='calculated',planned={'line_items_score':plan['line_items_score'],
            'total_cost_score':plan['planned_cost_score'],'expected_revenue_score':inputs['retained_receipts_score'],
            'expected_profit_score':plan['planned_profit_score'],'expected_margin_points':plan['margin_points'],
            'required_min_margin_points':self.config['minimum_margin_points'],
            'planned_margin_feasible':None if plan['margin_points'] is None else plan['margin_points']>=self.config['minimum_margin_points'],
            'reserve_score':plan['reserve_score'],'operating_allowance_score':operating,
            'budget_feasible':not plan['planned_budget_breach'],'operating_allowance_feasible':plan['planned_cost_score']<=operating,
            'budget_utilization':plan['planned_cost_score']/inputs['budget_score'],
            'used_area_m2':plan['used_area_m2'],'usable_area_m2':plan['usable_area_m2'],
            'space_utilization':plan['used_area_m2']/plan['usable_area_m2'],'capacity_persons':self.config['capacity_persons'],
            'seats':inputs['guests'],'staff':plan['staff'],'tables':plan['tables'],
            'paid_hours_per_staff':plan['paid_hours_per_staff'],'quantities':plan['quantities'],
            'estimate_kind':'deterministic_rule_based_not_ML_cost_forecast'},model_risk_scores=scores,
            monte_carlo={'origin':'hypothetical_simulated_outcomes_not_observed',
                'cost_score':distribution(simulation['cost']),'revenue_score':distribution(simulation['revenue']),
                'profit_score':distribution(simulation['profit']),'margin_points':distribution(simulation['margin']),
                'budget_overrun_frequency':float(np.mean(simulation['overrun'])),
                'profit_margin_risk_frequency':float(np.mean(simulation['margin_risk'])),
                'planned_operating_allowance_exceeded_frequency':float(np.mean(simulation['cost']>operating)),
                'quantile_interpretation':'simulation_distribution_not_calibrated_prediction_interval'})
        if not result['planned']['budget_feasible']:result['warnings'].append('Planned costs exceed budget.')
        if not result['planned']['operating_allowance_feasible']:result['warnings'].append('Planned costs exceed budget after earmarking reserve.')
        if result['planned']['planned_margin_feasible'] is False:result['warnings'].append('Expected profit margin is below the experimental minimum.')
        return result,simulation

    def request(self,payload,operation='calculate'):
        if not isinstance(payload,dict):raise ValueError('request_object_required')
        allowed = {'event_type','inputs','draws','seed'} if operation=='calculate' else {'event_type','baseline','alternative_changes','draws','seed'}
        if operation not in ('calculate','what-if') or set(payload)-allowed:
            raise ValueError('unsupported_operation_or_client_fields')
        event,draws,seed = payload.get('event_type'),payload.get('draws',2000),payload.get('seed',20261012)
        shocks = draw_shocks(self.config,draws,seed)
        response = {'api_version':'unitless-decision.0.1','operation':operation,'provenance':self.provenance(draws,seed)}
        if operation=='calculate':
            response['result'],_ = self._evaluate(event,payload.get('inputs'),shocks)
            return response
        baseline = payload.get('baseline')
        changes = payload.get('alternative_changes')
        if not isinstance(changes,dict) or set(changes)-set(FIELDS) or not isinstance(baseline,dict):
            raise ValueError('invalid_what_if_inputs')
        b,bs = self._evaluate(event,baseline,shocks)
        a,as_ = self._evaluate(event,{**baseline,**changes},shocks)
        response.update(baseline=b,alternative=a,comparison_status='blocked',delta=None)
        if bs is not None and as_ is not None:
            response['comparison_status']='comparable'
            response['delta']={'planned_cost_score':a['planned']['total_cost_score']-b['planned']['total_cost_score'],
                'expected_profit_score':a['planned']['expected_profit_score']-b['planned']['expected_profit_score'],
                'space_utilization':a['planned']['space_utilization']-b['planned']['space_utilization'],
                'seats':a['planned']['seats']-b['planned']['seats'],'staff':a['planned']['staff']-b['planned']['staff'],
                'budget_overrun_frequency':a['monte_carlo']['budget_overrun_frequency']-b['monte_carlo']['budget_overrun_frequency'],
                'paired_simulated_cost_difference_score':distribution(as_['cost']-bs['cost']),
                'paired_simulated_profit_difference_score':distribution(as_['profit']-bs['profit'])}
        return response
