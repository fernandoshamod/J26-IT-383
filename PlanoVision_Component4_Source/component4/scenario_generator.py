"""Separate bounded stochastic simulator. No CLI or implicit pilot/mock fallback."""

# Separate unitless track: no dispatch or fallback from the LKR engine.
from .unitless_pilot import (generate as generate_unitless_pilot,
                            generate_test as generate_unitless_test_scenarios,
                            write as write_unitless_pilot,
                            execution_blockers as unitless_execution_blockers)
from copy import deepcopy
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
import json
from pathlib import Path
import platform

import numpy as np

from .engine import CATEGORIES, PARAMS, RATE_UNITS, RULE_VERSION, evaluate, fingerprint, money, risk_labels
from .gates import pilot_blockers
from .generator_validation import (CODE_FILES, EVENTS, GENERATOR_VERSION, PARAMETER_UNITS,
    REQUIRED_ASSUMPTIONS, ConfigurationError, GeneratorConfiguration, file_snapshots,
    generator_review_errors, numeric, software_versions)

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
WARNING = 'SYNTHETIC SIMULATOR OUTCOMES — NOT OBSERVED EVENTS OR TRAINED MODEL PREDICTIONS'
TEST_WARNING = 'MOCK TEST DATA — NOT REAL MARKET QUOTATIONS OR TRAINED ML PREDICTIONS'


class GenerationError(RuntimeError):
    def __init__(self, message, rejection_log):
        self.rejection_log = rejection_log
        super().__init__(message)


@dataclass
class ScenarioBundle:
    """Do not train on the whole bundle. Only prediction_features is an input-feature table."""
    prediction_features: list
    simulated_outcomes: list
    planned_ledgers: list
    realized_ledgers: list
    provenance: list
    latent_outcomes: list
    rejections: list
    manifest: dict
    configuration: dict


FEATURE_UNITS = {
    'event_type':'category','event_date':'ISO date',**PARAMETER_UNITS,
    'planned_total_cost_lkr':'LKR','expected_profit_lkr':'LKR','expected_margin_points':'percentage points',
    'contingency_reserve_lkr':'LKR','operating_allowance_lkr':'LKR','used_area_m2':'m2','usable_area_m2':'m2',
    'planned_seats':'seats','general_staff_count':'persons','person_hours':'person-hours',
    'overtime_person_hours':'person-hours','furniture_tables':'tables','av_kits':'kits','lighting_kits':'kits',
    **{'quantity_'+k:u.removeprefix('LKR/') for k,u in RATE_UNITS.items()}
}
FEATURE_UNITS['quantity_labour'] = 'overtime-weighted person-hours (billing only)'


def prediction_feature_row(event, event_date, parameters, plan):
    """An allowlist, not a blacklist: labels, IDs, latent factors and outcome totals cannot enter here."""
    row = {'event_type':event,'event_date':event_date,**{k:parameters[k] for k in PARAMS},
        'planned_total_cost_lkr':plan['costs']['estimate_lkr'],
        'expected_profit_lkr':plan['risk_indicators']['expected_profit_lkr'],
        'expected_margin_points':plan['risk_indicators']['expected_margin_points'],
        'contingency_reserve_lkr':plan['budget_constraints']['contingency_reserve_lkr'],
        'operating_allowance_lkr':plan['budget_constraints']['operating_allowance_lkr'],
        'used_area_m2':plan['spatial']['used_area_m2'],'usable_area_m2':plan['spatial']['usable_area_m2'],
        'planned_seats':plan['spatial']['planned_seats'],**plan['operations'],
        **{'quantity_'+r['item_id']:r['quantity'] for r in plan['costs']['line_items']}}
    if set(row)!=set(FEATURE_UNITS):
        raise ConfigurationError(['prediction_feature_schema_mismatch'])
    return row


def rng_for(seed, scenario_index, attempt, phase):
    """Fixed stream identities: 0 archetype; 1 planning; 2 ordinary outcomes; 3 injection."""
    seq = np.random.SeedSequence(seed,spawn_key=(scenario_index,attempt,phase))
    return np.random.Generator(np.random.PCG64(seq))


def realize_ledger(plan_lines, rate_cards, multipliers):
    """Separate outcome subledger: frozen planning quantities, shocks on declared rate bases only.

    Reuses engine money/rounding; matches its inclusive/exclusive tax algebra. Does not mutate
    an approved planning rate card or call the live engine using a mock-mode bypass.
    """
    if set(multipliers)-set(RATE_UNITS):
        raise ConfigurationError(['realization:unknown_service'])
    result = []
    for line in plan_lines:
        item = line['item_id']
        factor = multipliers.get(item,1.0)  # Unshocked services stay exactly at their approved planning rate.
        numeric(factor,'realization.factor.'+item)
        if line['included_in'] is not None:
            if item in multipliers:
                raise ConfigurationError(['realization:bundled_service_cannot_be_shocked:'+item])
            result.append(deepcopy(line))
            continue
        card = rate_cards[item]
        base = Decimal(str(line['quantity']))*Decimal(str(card['rate']))*Decimal(str(factor))
        tax = Decimal(str(card['tax_rate_points']))/100
        gross = money(base*(1+tax)) if card['tax_scope']=='exclusive' else money(base)
        net = money(base) if card['tax_scope']=='exclusive' else money(base/(1+tax))
        result.append({**deepcopy(line),'net_lkr':float(net),'tax_lkr':float(gross-net),'gross_lkr':float(gross),
                       'rate_lkr':float(Decimal(str(card['rate']))*Decimal(str(factor)))})
    _reconcile(result)
    return result


def _reconcile(lines):
    if len(lines)!=len(RATE_UNITS) or {x['item_id'] for x in lines}!=set(RATE_UNITS):
        raise GenerationError('ledger_item_partition_invalid',[])
    for line in lines:
        if line['category']!=CATEGORIES[line['item_id']] or money(line['net_lkr'])+money(line['tax_lkr'])!=money(line['gross_lkr']):
            raise GenerationError('ledger_reconciliation_failed',[])
        if line['included_in'] is not None and any(line[k]!=0 for k in ['net_lkr','tax_lkr','gross_lkr']):
            raise GenerationError('bundled_line_charged_twice',[])
    return sum((money(x['gross_lkr']) for x in lines),Decimal(0))


def pilot_execution_blockers(config, *, source_root=DEFAULT_ROOT):
    """Read-only. Stored flags/references cannot authenticate a supervisor or quotation."""
    if not isinstance(config,dict):
        return ['engine_configuration:object_required']
    errors = []
    try:
        errors.extend(pilot_blockers(config))
        errors.extend(generator_review_errors(config))
    except (ValueError,TypeError,KeyError,AttributeError,ArithmeticError) as exc:
        errors.append('malformed_approval_configuration:'+type(exc).__name__)
    try:
        GeneratorConfiguration.parse(config,source_root=source_root)
    except ConfigurationError as exc:
        errors.extend(exc.errors)
    except (ValueError,TypeError,KeyError,AttributeError,ArithmeticError) as exc:
        errors.append('malformed_generator_configuration:'+type(exc).__name__)
    return sorted(set(errors))


def generate_scenarios(config, count, *, source_root=DEFAULT_ROOT):
    """Authorized diagnostic scope only, even in memory. No mock mode argument."""
    snapshot = deepcopy(config)
    blockers = pilot_execution_blockers(snapshot,source_root=source_root)
    if blockers:
        raise ConfigurationError(blockers)
    numeric(count,'count',integer=True,minimum=20)
    if count!=snapshot['pilot']['scenario_count'] or count>50:
        raise ConfigurationError(['count_differs_from_authorized_20_to_50_scope'])
    spec = GeneratorConfiguration.parse(snapshot,source_root=source_root)
    return _generate(snapshot,spec,count,test_only=False,source_root=source_root)


def generate_test_scenarios(config, count, *, source_root=DEFAULT_ROOT):
    """Isolated in-memory software tests, at most 16 records. No persistence entry point."""
    numeric(count,'test_count',integer=True,minimum=1)
    if count>16:
        raise ConfigurationError(['test_fixture_count_limit_16'])
    snapshot = deepcopy(config)
    spec = GeneratorConfiguration.parse(snapshot,test_only=True,source_root=source_root)
    return _generate(snapshot,spec,count,test_only=True,source_root=source_root)


def _planning_identity(config,spec):
    return fingerprint({'generator_version':GENERATOR_VERSION,'rules_version':RULE_VERSION,
        'seed':spec.seed,'weights':spec.weights,'max_attempts':spec.max_attempts,
        'profiles':spec.raw['profiles'],'units':spec.raw['parameter_units'],
        'assumption_version':spec.raw['assumption_version'],'source_snapshots':spec.source_snapshots,
        'code_snapshots':spec.raw['code_snapshot_hashes'],'software_versions':spec.raw['software_versions'],
        'archetypes':{e:{k:config['archetypes'][e][k] for k in
          ['parameters','rates','billing','av_steps','lighting_steps','approved_override_bounds']} for e in EVENTS}})


def _generate(config,spec,count,*,test_only,source_root):
    bundle = ScenarioBundle([],[],[],[],[],[],[],{},deepcopy(config))
    planning_identity = _planning_identity(config,spec)
    mode = 'mock_test_fixture' if test_only else 'live'
    for index in range(count):
        event = EVENTS[int(rng_for(spec.seed,index,0,0).choice(2,p=spec.weights))]
        design, profile = spec.profiles[event], config['archetypes'][event]
        family = 'F-'+fingerprint({'planning_identity':planning_identity,'index':index,'event_type':event})
        for attempt in range(spec.max_attempts):
            rng = rng_for(spec.seed,index,attempt,1)
            day = design.start+timedelta(days=int(rng.integers((design.end-design.start).days+1)))
            changes = {k:domain.sample(rng) for k,domain in sorted(design.domains.items())}
            changes['expected_receipts_lkr'] = float(money(design.receipts.sample(rng)))
            budget_value = design.budget.sample(rng)
            changes['initial_budget_lkr'] = float(money(budget_value)) if design.budget_mode=='fixed' else design.reference_budget
            plan = evaluate(config,event,changes,mode=mode)
            if plan['status']=='calculated' and design.budget_mode=='planned_cost_factor':
                changes['initial_budget_lkr'] = float(money(Decimal(str(plan['costs']['estimate_lkr']))*Decimal(str(budget_value))))
                plan = evaluate(config,event,changes,mode=mode)
            if plan['status']=='calculated':
                break
            bundle.rejections.append({'family_id':family,'scenario_index':index,'event_type':event,'attempt':attempt,
                'event_date':day.isoformat(),'planning_inputs':changes,'blockers':plan['blockers'],
                'reason_scope':'hard_capacity_geometry_parameter_or_funding_constraint; not a risk-label filter'})
        else:
            raise GenerationError('maximum_planning_attempts_exhausted:'+family,bundle.rejections)
        p = {**deepcopy(profile['parameters']),**changes}
        planned_total = _reconcile(plan['costs']['line_items'])
        if planned_total!=money(plan['costs']['estimate_lkr']):
            raise GenerationError('planning_total_mismatch',bundle.rejections)
        # Freeze the complete feature row BEFORE constructing outcome streams.
        features = prediction_feature_row(event,day.isoformat(),p,plan)
        shock, anomaly = profile['outcome_uncertainty'], profile['injected_vendor_regime']
        positive_charges = {r['item_id'] for r in plan['costs']['line_items'] if r['gross_lkr']>0}
        if not set(anomaly['affected_services'])<=positive_charges:
            raise GenerationError('anomaly_target_zero_charge_in_sampled_plan',bundle.rejections)
        outcome_identity = fingerprint({'shock':shock,'anomaly':anomaly})
        scenario_id = 'S-'+fingerprint({'family_id':family,'attempt':attempt,'planning_inputs':features,'outcome_design':outcome_identity})
        outcome_rng = rng_for(spec.seed,index,attempt,2)
        rank = float(outcome_rng.random())
        cb, rb = shock['cost_bounds'], shock['revenue_bounds']
        cost_factor = cb['min']+rank*(cb['max']-cb['min'])
        revenue_rank = 1-rank if shock['dependence_spec']['mode']=='shared_rank_adverse' else float(outcome_rng.random())
        receipts_factor = rb['min']+revenue_rank*(rb['max']-rb['min'])
        factors = {item:cost_factor for item in shock['dependence_spec']['cost_services']}
        injection_rng = rng_for(spec.seed,index,attempt,3)
        injected = bool(injection_rng.random()<anomaly['prevalence'])
        affected, injection_factor = None, None
        if injected:
            affected = anomaly['affected_services'][int(injection_rng.integers(len(anomaly['affected_services'])))]
            b = anomaly['multiplier_bounds']
            injection_factor = b['min']+float(injection_rng.random())*(b['max']-b['min'])
            # Explicit composition: one selected charged item, multiply ordinary and injection factors once.
            factors[affected] = factors.get(affected,1.0)*injection_factor
        realized = realize_ledger(plan['costs']['line_items'],profile['rates'],factors)
        actual_cost = _reconcile(realized)
        actual_receipts = money(Decimal(str(p['expected_receipts_lkr']))*Decimal(str(receipts_factor)))
        labels = risk_labels(float(actual_cost),float(actual_receipts),p['initial_budget_lkr'],p['minimum_margin_points'],injected)
        bundle.prediction_features.append(features)
        bundle.simulated_outcomes.append({'scenario_id':scenario_id,'realized_cost_lkr':float(actual_cost),
            'realized_retained_receipts_lkr':float(actual_receipts),**labels,'label_origin':'simulated_rule_outcome',
            'is_observed_event':False,'is_mock_test_fixture':test_only})
        for phase, lines, output in [('planned',plan['costs']['line_items'],bundle.planned_ledgers),('realized',realized,bundle.realized_ledgers)]:
            output.extend({'scenario_id':scenario_id,'phase':phase,**deepcopy(line)} for line in lines)
        bundle.latent_outcomes.append({'scenario_id':scenario_id,'cost_factor':cost_factor,'receipts_factor':receipts_factor,
            'injection_flag':injected,'injection_factor':injection_factor,'affected_service':affected,
            'composed_service_multipliers':factors,'origin':'hypothetical_latent_test' if test_only else 'hypothetical_latent_simulation'})
        ancestry = deepcopy(design.ancestry)
        bundle.provenance.append({'scenario_id':scenario_id,'family_id':family,'parent_scenario_id':None,
            'scenario_index':index,'accepted_attempt':attempt,'event_type':event,'event_date':day.isoformat(),
            'planning_identity_sha256':planning_identity,'outcome_design_sha256':outcome_identity,
            'split_group_id':'G-'+fingerprint(ancestry),'source_ancestry':ancestry,
            'assumption_ids':sorted(REQUIRED_ASSUMPTIONS),'assumption_version':spec.raw['assumption_version'],
            'source_snapshot_hashes':spec.source_snapshots,'label_origin':'simulated_rule_outcome',
            'is_observed_event':False,'is_mock_test_fixture':test_only})
    bundle.manifest = {'generator_version':GENERATOR_VERSION,'rules_version':RULE_VERSION,'seed':spec.seed,
        'rng':'NumPy Generator(PCG64(SeedSequence(seed, spawn_key=(index,attempt,phase))))',
        'rng_phases':{'archetype':0,'planning':1,'ordinary_outcome':2,'injection':3},
        'software_versions':software_versions(),'platform':platform.platform(),'machine':platform.machine(),
        'numpy_build_configuration':np.__config__.CONFIG,
        'source_snapshot_hashes':spec.source_snapshots,'code_snapshot_hashes':file_snapshots(source_root,CODE_FILES),
        'configuration_sha256':fingerprint(config),'planning_identity_sha256':planning_identity,
        'record_count':count,'rejected_attempt_count':len(bundle.rejections),'feature_units':FEATURE_UNITS,
        'origin':'mock_test_fixture' if test_only else 'synthetic_approved_diagnostic',
        'is_trained_model_prediction':False,'is_calibrated_probability_model':False,
        'warning':TEST_WARNING if test_only else WARNING,
        'prediction_feature_policy':'Only prediction_features rows; IDs/ancestry are join/group metadata, not predictors. Outcomes/latents/realized ledgers/configuration are forbidden predictor tables.'}
    return bundle


def write_pilot(config, output_directory, *, source_root=DEFAULT_ROOT):
    """Only persistent entry point. Approval/type/hash checks run before creating ANY output path."""
    snapshot = deepcopy(config)
    blockers = pilot_execution_blockers(snapshot,source_root=source_root)
    if blockers:
        raise ConfigurationError(blockers)
    bundle = generate_scenarios(snapshot,snapshot['pilot']['scenario_count'],source_root=source_root)
    # Recheck code/source hashes just before writing; no overwrite of existing data.
    blockers = pilot_execution_blockers(snapshot,source_root=source_root)
    if blockers:
        raise ConfigurationError(blockers)
    _write_bundle(bundle,output_directory)
    return bundle.manifest


def _write_bundle(bundle, directory):
    """Internal serializer; tests exercise it only in automatically removed temporary directories."""
    target = Path(directory)
    target.mkdir(parents=False,exist_ok=False)
    tables = {'prediction_features':bundle.prediction_features,'simulated_outcomes':bundle.simulated_outcomes,
        'planned_line_items':bundle.planned_ledgers,'realized_line_items':bundle.realized_ledgers,
        'scenario_provenance':bundle.provenance,'latent_outcomes_DO_NOT_USE_AS_FEATURES':bundle.latent_outcomes,
        'rejected_configurations':bundle.rejections}
    for name,rows in tables.items():
        with (target/(name+'.jsonl')).open('x',encoding='utf-8',newline='\n') as handle:
            for i,row in enumerate(rows):
                # Row join ID lives outside the inner model-input feature object.
                record = {'scenario_id':bundle.provenance[i]['scenario_id'],'features':row} if name=='prediction_features' else row
                handle.write(json.dumps(record,sort_keys=True,allow_nan=False)+'\n')
    with (target/'configuration.json').open('x',encoding='utf-8') as handle:
        json.dump(bundle.configuration,handle,sort_keys=True,indent=2,allow_nan=False)
    manifest = deepcopy(bundle.manifest)
    manifest['artifact_sha256'] = file_snapshots(target,[p.name for p in sorted(target.iterdir())])
    with (target/'manifest.json').open('x',encoding='utf-8') as handle:
        json.dump(manifest,handle,sort_keys=True,indent=2,allow_nan=False)
