"""Strict, fail-closed models for the separate scenario generator (no defaults for rates)."""
from copy import deepcopy
from dataclasses import dataclass
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import platform
import re

import numpy as np

from .engine import PARAMS, RATE_UNITS, RULE_VERSION, evaluate, fingerprint, parameter_payload, step_units

GENERATOR_VERSION = '0.1.0-proposed'
EVENTS = ('Wedding', 'Corporate')
COUNTS = {'guest_count','vip_seats','seats_per_table','vip_tables','capacity_persons','base_staff','extra_general_staff'}
PARAMETER_UNITS = {
    'guest_count':'persons','seated_share':'fraction','vip_seats':'seats','seats_per_table':'seats/table',
    'vip_tables':'tables','event_hours':'hours','setup_hours':'hours','clearance_hours':'hours',
    'venue_area_m2':'m2','excluded_area_m2':'m2','area_per_standard_seat_m2':'m2/seat',
    'area_per_vip_seat_m2':'m2/seat','stage_width_m':'m','stage_length_m':'m','service_area_m2':'m2',
    'circulation_area_m2':'m2','capacity_persons':'persons','base_staff':'persons','guests_per_staff':'persons/staff',
    'extra_general_staff':'persons','regular_paid_hours_limit':'hours','overtime_multiplier':'multiplier',
    'initial_budget_lkr':'LKR','expected_receipts_lkr':'LKR','minimum_margin_points':'percentage points','reserve_ratio':'fraction'
}
REQUIRED_ASSUMPTIONS = {'A001','A002','A003','A005',*('A%03d'%i for i in range(7,16)),
                        'A020','A021','A022','A023','A024','A025','A026','A027','A028','A029','A030','A032','A033'}
CODE_FILES = ('component4/engine.py','component4/scenario_generator.py','component4/generator_validation.py','component4/gates.py')


class ConfigurationError(ValueError):
    def __init__(self, errors):
        self.errors = sorted(set(errors))
        super().__init__('; '.join(self.errors))


def require(condition, path):
    if not condition:
        raise ConfigurationError([path])


def numeric(value, path, *, integer=False, minimum=0):
    try:
        valid = type(value) in (int,float) and math.isfinite(value) and value >= minimum
    except OverflowError:
        valid = False
    require(valid, path+':finite_number_required')
    if integer:
        require(type(value) is int, path+':strict_integer_required')
    return value


def text(value, path):
    require(isinstance(value,str) and bool(value.strip()), path+':nonempty_string_required')
    return value


def keys(value, required, path):
    require(isinstance(value,dict),path+':object_required')
    require(set(value)==set(required),path+':missing_or_unknown_fields')


def iso_date(value, path):
    text(value,path)
    try:
        result = date.fromisoformat(value)
    except ValueError:
        raise ConfigurationError([path+':ISO_date_required']) from None
    require(result.isoformat()==value,path+':ISO_date_required')
    return result


def software_versions():
    return {'python':platform.python_version(),'numpy':np.__version__}


def file_snapshots(root, paths):
    base = Path(root).resolve()
    return {p:hashlib.sha256((base/p).read_bytes()).hexdigest() for p in paths}


def validate_snapshots(snapshots, root, path):
    require(isinstance(snapshots,dict) and bool(snapshots),path+':snapshots_required')
    base = Path(root).resolve()
    for name, digest in snapshots.items():
        text(name,path)
        require(isinstance(digest,str) and re.fullmatch('[a-f0-9]{64}',digest) is not None,path+':invalid_sha256')
        target = (base/name).resolve()
        require(not Path(name).is_absolute() and target.is_relative_to(base),path+':snapshot_path_outside_root')
        require(target.is_file(),path+':snapshot_missing:'+name)
        require(hashlib.sha256(target.read_bytes()).hexdigest()==digest,path+':snapshot_hash_mismatch:'+name)


@dataclass(frozen=True)
class NumericDomain:
    unit: str
    distribution: str
    values: tuple
    low: float | int | None
    high: float | int | None

    @classmethod
    def parse(cls, obj, unit, path, *, integer=False, minimum=0):
        require(isinstance(obj,dict),path+':domain_required')
        kind = obj.get('distribution')
        require(kind in {'fixed','choice','uniform','uniform_integer'},path+':unsupported_distribution')
        require(obj.get('unit')==unit,path+':unit_mismatch')
        if kind in {'fixed','choice'}:
            keys(obj,{'distribution','unit','values'},path)
            values = obj['values']
            require(isinstance(values,list) and bool(values),path+':values_required')
            require(kind!='fixed' or len(values)==1,path+':fixed_requires_one_value')
            for v in values:
                numeric(v,path,integer=integer,minimum=minimum)
            require(len(set(values))==len(values),path+':duplicate_values')
            return cls(unit,kind,tuple(values),None,None)
        keys(obj,{'distribution','unit','min','max'},path)
        require(not integer or kind=='uniform_integer',path+':count_requires_integer_distribution')
        is_int = integer or kind=='uniform_integer'
        lo = numeric(obj['min'],path+'.min',integer=is_int,minimum=minimum)
        hi = numeric(obj['max'],path+'.max',integer=is_int,minimum=minimum)
        require(lo<=hi,path+':reversed_bounds')
        if is_int:
            require(hi<2**63-1,path+':integer_rng_bound_exceeded')
        else:
            require(math.isfinite(hi-lo),path+':range_width_not_finite')
        return cls(unit,kind,(),lo,hi)

    def extent(self):
        return (min(self.values),max(self.values)) if self.values else (self.low,self.high)

    def sample(self, rng):
        if self.values:
            return self.values[0] if len(self.values)==1 else self.values[int(rng.integers(len(self.values)))]
        if self.low==self.high:
            return self.low
        return int(rng.integers(self.low,self.high+1)) if self.distribution=='uniform_integer' else float(rng.uniform(self.low,self.high))


@dataclass(frozen=True)
class ProfileDesign:
    start: date
    end: date
    domains: dict
    receipts: NumericDomain
    budget_mode: str
    budget: NumericDomain
    reference_budget: float | int | None
    ancestry: dict


@dataclass(frozen=True)
class GeneratorConfiguration:
    seed: int
    max_attempts: int
    weights: tuple
    profiles: dict
    source_snapshots: dict
    raw: dict

    @classmethod
    def parse(cls, config, *, test_only=False, source_root):
        try:
            return cls._parse(config,test_only=test_only,source_root=source_root)
        except ConfigurationError:
            raise
        except (ValueError,TypeError,KeyError,AttributeError,ArithmeticError,OSError) as exc:
            raise ConfigurationError(['malformed_generator_configuration:'+type(exc).__name__]) from None

    @classmethod
    def _parse(cls, config, *, test_only=False, source_root):
        require(isinstance(config,dict),'engine_configuration:object_required')
        try:
            json.dumps(config,allow_nan=False)
        except (ValueError,TypeError):
            raise ConfigurationError(['configuration:finite_JSON_values_required']) from None
        require(config.get('rules_version')==RULE_VERSION,'rules_version_mismatch')
        spec = config.get('scenario_generator')
        fields = {'version','record_kind','seed','max_attempts_per_scenario','archetype_weights','parameter_units',
                  'profiles','source_snapshot_hashes','code_snapshot_hashes','software_versions','assumption_version',
                  'assumption_ids','outcome_design_label'}
        keys(spec,fields,'scenario_generator')
        require(spec['version']==GENERATOR_VERSION,'scenario_generator:version_mismatch')
        marker = 'mock_test_fixture' if test_only else 'reviewed_generator_design'
        require(spec['record_kind']==marker,'scenario_generator:mode_marker_mismatch')
        if test_only:
            require(config.get('record_kind')=='mock_test_fixture','test_generator_requires_fixture_configuration')
        else:
            require(config.get('record_kind')=='approved_simulator_configuration','approved_configuration_marker_required')
        seed = numeric(spec['seed'],'scenario_generator.seed',integer=True)
        require(seed<2**128,'scenario_generator.seed:128_bit_limit')
        require(config.get('seed')==seed and type(config.get('seed')) is int,'engine_generator_seed_mismatch')
        attempts = numeric(spec['max_attempts_per_scenario'],'scenario_generator.max_attempts',integer=True,minimum=1)
        require(attempts<=10000,'scenario_generator.max_attempts:limit_exceeded')
        require(spec['parameter_units']==PARAMETER_UNITS,'scenario_generator:parameter_units_mismatch')
        keys(spec['archetype_weights'],EVENTS,'archetype_weights')
        weights = tuple(numeric(spec['archetype_weights'][e],f'weights.{e}',minimum=0) for e in EVENTS)
        require(all(w>0 for w in weights) and math.isclose(sum(weights),1,rel_tol=0,abs_tol=1e-12),'archetype_weights:positive_sum_one_required')
        text(spec['assumption_version'],'assumption_version')
        ids = spec['assumption_ids']
        require(isinstance(ids,list) and all(isinstance(x,str) for x in ids),'assumption_ids:list_required')
        require(len(set(ids))==len(ids) and REQUIRED_ASSUMPTIONS<=set(ids)<=set('A%03d'%i for i in range(1,35)),'assumption_ids:scope_incomplete_or_invalid')
        require(spec['outcome_design_label']=='hypothetical_not_calibrated','outcome_design:explicit_hypothetical_label_required')
        require(spec['software_versions']==software_versions(),'software_versions:runtime_mismatch')
        require(set(spec['code_snapshot_hashes'] or {})==set(CODE_FILES),'code_snapshot_hashes:scope_mismatch')
        validate_snapshots(spec['code_snapshot_hashes'],source_root,'code_snapshot_hashes')
        validate_snapshots(spec['source_snapshot_hashes'],source_root,'source_snapshot_hashes')
        if not test_only:
            require(not any('fixtures' in Path(name).parts for name in spec['source_snapshot_hashes']),
                    'live_source_snapshots_cannot_be_test_fixtures')
        require(config.get('source_snapshot_hashes')==spec['source_snapshot_hashes'],'engine_generator_source_snapshots_mismatch')
        cutoff = iso_date(config.get('calibration_cutoff'),'calibration_cutoff')
        keys(spec['profiles'],EVENTS,'generator_profiles')
        profiles = {}
        for event in EVENTS:
            profile = config.get('archetypes',{}).get(event)
            require(isinstance(profile,dict),event+':engine_profile_required')
            p = profile.get('parameters')
            keys(p,PARAMS,event+'.parameters')
            for k in PARAMS:
                numeric(p[k],event+'.'+k,integer=k in COUNTS)
            # Current area equation has no standing-person allocation.
            require(p['seated_share']==1,event+':seated_only_scope_required')
            require(p['stage_width_m']>0 and p['stage_length_m']>0,event+':positive_stage_scope_required')
            require(profile.get('geometry_origin') in ({'mock_test_fixture'} if test_only else {'measured_reviewed_plan'}),event+':geometry_origin_unreviewed')
            require(profile.get('revenue_mode')=='retained_contract_receipts',event+':retained_revenue_scope_required')
            billing = profile.get('billing',{})
            keys(billing,{'catering_mode','staff_scope','included_items'},event+'.billing')
            included = billing['included_items']
            require(isinstance(included,dict),event+':bundle_map_required')
            for item,parent in included.items():
                require(isinstance(item,str) and isinstance(parent,str) and item in RATE_UNITS and parent in RATE_UNITS
                        and item!=parent and parent not in included,event+':invalid_bundle_reference')
            keys(profile.get('rates'),RATE_UNITS,event+'.rates')
            for item,unit in RATE_UNITS.items():
                r = profile['rates'][item]
                require(isinstance(r,dict) and r.get('unit')==unit and r.get('currency')=='LKR',event+':rate_unit_mismatch:'+item)
                keys(r,{'rate','unit','currency','quote_date','tax_scope','tax_rate_points','evidence_ref','approval_status'},event+'.rate.'+item)
                if item not in included:
                    numeric(r.get('rate'),event+'.rate.'+item)
                    numeric(r.get('tax_rate_points'),event+'.tax.'+item)
                    iso_date(r.get('quote_date'),event+'.quote_date.'+item)
                    text(r.get('evidence_ref'),event+'.evidence.'+item)
            for step in ['av_steps','lighting_steps']:
                schedule = profile.get(step)
                require(isinstance(schedule,list) and bool(schedule),event+'.'+step+':schedule_required')
                for row in schedule:
                    keys(row,{'max_stage_area_m2','units'},event+'.'+step)
                    numeric(row['units'],event+'.'+step+'.units',integer=True)
                try:
                    step_units(p['stage_width_m']*p['stage_length_m'],profile.get(step))
                except (ValueError,TypeError,AttributeError) as exc:
                    raise ConfigurationError([event+'.'+step+':'+str(exc)]) from None
            try:
                baseline = evaluate(config,event,mode='mock_test_fixture' if test_only else 'live')
            except (ValueError,OverflowError,ArithmeticError) as exc:
                raise ConfigurationError([event+':baseline_arithmetic_invalid:'+type(exc).__name__]) from None
            require(baseline['status']=='calculated',event+':engine_baseline_blocked:'+','.join(baseline['blockers']))
            if not test_only:
                for aid,review in config.get('formula_approvals',{}).items():
                    iso_date(review.get('reviewed_at'),'formula_review.'+aid+'.date')
                iso_date(profile['parameter_approval'].get('reviewed_at'),event+'.parameter_approval.date')
            design = spec['profiles'][event]
            keys(design,{'date_bounds','parameter_domains','budget_policy','retained_receipts','ancestry'},event+'.design')
            keys(design['date_bounds'],{'start','end'},event+'.date_bounds')
            start = iso_date(design['date_bounds']['start'],event+'.start')
            end = iso_date(design['date_bounds']['end'],event+'.end')
            require(cutoff<=start<=end,event+':invalid_date_or_information_cutoff')
            require(profile.get('date_bounds')==design['date_bounds'],event+':date_scope_mismatch')
            for item,r in profile['rates'].items():
                if item not in included:
                    require(iso_date(r['quote_date'],event+'.quote_date')<=start,event+':future_quote_leakage:'+item)
            domains = design['parameter_domains']
            require(isinstance(domains,dict) and set(domains)<=set(PARAMS)-{'initial_budget_lkr','expected_receipts_lkr'},event+':unsupported_parameter_domain')
            parsed = {k:NumericDomain.parse(v,PARAMETER_UNITS[k],event+'.domain.'+k,integer=k in COUNTS) for k,v in domains.items()}
            for k,d in parsed.items():
                lo,hi = d.extent()
                if k in {'guest_count','seats_per_table','capacity_persons','guests_per_staff','event_hours',
                         'area_per_standard_seat_m2','area_per_vip_seat_m2'}:
                    require(lo>0,event+'.'+k+':positive_domain_required')
                if k in {'seated_share','reserve_ratio'}:
                    require(hi<=1,event+'.'+k+':fraction_out_of_bounds')
                if k=='minimum_margin_points':
                    require(hi<=100,event+'.'+k+':margin_out_of_bounds')
                if k=='overtime_multiplier':
                    require(lo>=1,event+'.'+k+':overtime_below_one')
            require('seated_share' not in parsed or parsed['seated_share'].extent()==(1,1),event+':standing_area_not_implemented')
            for k in ['stage_width_m','stage_length_m']:
                require(k not in parsed or parsed[k].extent()[0]>0,event+':positive_stage_domain_required')
            receipts = NumericDomain.parse(design['retained_receipts'],'LKR',event+'.receipts')
            bp = design['budget_policy']
            require(isinstance(bp,dict),event+':budget_policy_required')
            mode = bp.get('mode')
            require(mode in {'fixed','planned_cost_factor'},event+':unsupported_budget_policy')
            if mode=='fixed':
                keys(bp,{'mode','budget'},event+'.budget_policy')
                budget = NumericDomain.parse(bp['budget'],'LKR',event+'.budget')
                reference = None
            else:
                keys(bp,{'mode','factor','reference_budget_lkr'},event+'.budget_policy')
                budget = NumericDomain.parse(bp['factor'],'multiplier',event+'.budget_factor')
                reference = numeric(bp['reference_budget_lkr'],event+'.reference_budget_lkr',minimum=0)
                max_reserve = parsed['reserve_ratio'].extent()[1] if 'reserve_ratio' in parsed else p['reserve_ratio']
                require(budget.extent()[0]>=max_reserve,event+':budget_factor_below_maximum_reserve')
            keys(design['ancestry'],{'venue_profile_id','vendor_rate_card_id','archetype_template_id'},event+'.ancestry')
            for k,v in design['ancestry'].items():
                text(v,event+'.ancestry.'+k)
            shock = profile.get('outcome_uncertainty')
            keys(shock,{'distribution','cost_bounds','revenue_bounds','dependence_spec','approval_ref'},event+'.outcome_uncertainty')
            require(shock['distribution']=='bounded_uniform_multipliers',event+':unsupported_outcome_distribution')
            for name in ['cost_bounds','revenue_bounds']:
                keys(shock[name],{'min','max','unit'},event+'.'+name)
                require(shock[name]['unit']=='multiplier',event+':shock_unit_mismatch')
                numeric(shock[name]['min'],event+'.'+name+'.min')
                numeric(shock[name]['max'],event+'.'+name+'.max')
                require(shock[name]['min']<=shock[name]['max'] and math.isfinite(shock[name]['max']-shock[name]['min']),event+':invalid_shock_bounds')
            dep = shock['dependence_spec']
            keys(dep,{'mode','cost_services'},event+'.dependence_spec')
            require(dep['mode'] in {'independent','shared_rank_adverse'},event+':unsupported_dependence')
            services = dep['cost_services']
            require(isinstance(services,list) and bool(services) and all(isinstance(k,str) for k in services),event+':cost_services_required')
            require(len(set(services))==len(services) and set(services)<=set(RATE_UNITS)-set(included),event+':overlapping_or_invalid_shock_services')
            text(shock['approval_ref'],event+'.outcome_approval_ref')
            anomaly = profile.get('injected_vendor_regime')
            keys(anomaly,{'prevalence','multiplier_bounds','affected_services','approval_ref'},event+'.injected_vendor_regime')
            numeric(anomaly['prevalence'],event+'.anomaly_prevalence')
            require(anomaly['prevalence']<=1,event+':anomaly_prevalence_out_of_bounds')
            b = anomaly['multiplier_bounds']
            keys(b,{'min','max','unit'},event+'.anomaly_multiplier_bounds')
            require(b['unit']=='multiplier',event+':anomaly_unit_mismatch')
            numeric(b['min'],event+'.anomaly_min',minimum=1)
            numeric(b['max'],event+'.anomaly_max',minimum=1)
            require(1<b['min']<=b['max'] and math.isfinite(b['max']-b['min']),event+':nontrivial_anomaly_bounds_required')
            affected = anomaly['affected_services']
            require(isinstance(affected,list) and bool(affected) and all(isinstance(k,str) for k in affected),event+':anomaly_services_required')
            require(len(set(affected))==len(affected) and set(affected)<=set(RATE_UNITS)-set(included),event+':invalid_anomaly_services')
            text(anomaly['approval_ref'],event+'.anomaly_approval_ref')
            positive_charges = {r['item_id'] for r in baseline['costs']['line_items'] if r['gross_lkr']>0}
            require(set(affected)<=positive_charges,event+':anomaly_targets_require_positive_charges')
            if not test_only:
                # All possible planning draws must be inside separately approved intervention bounds.
                bounds = profile.get('approved_override_bounds',{})
                for k,domain in {**parsed,'expected_receipts_lkr':receipts}.items():
                    _within_bounds(domain.extent(),bounds.get(k),event+'.'+k)
                if mode=='fixed':
                    _within_bounds(budget.extent(),bounds.get('initial_budget_lkr'),event+'.budget')
                else:
                    _within_bounds((reference,reference),bounds.get('initial_budget_lkr'),event+'.reference_budget')
            profiles[event] = ProfileDesign(start,end,parsed,receipts,mode,budget,reference,deepcopy(design['ancestry']))
        return cls(seed,attempts,weights,profiles,deepcopy(spec['source_snapshot_hashes']),deepcopy(spec))


def _within_bounds(extent, bounds, path):
    require(isinstance(bounds,dict),path+':approved_bounds_missing')
    lo = numeric(bounds.get('min'),path+'.min')
    hi = numeric(bounds.get('max'),path+'.max')
    require(lo<=extent[0]<=extent[1]<=hi,path+':outside_approved_bounds')


def generator_approval_payload(config):
    """The reviewer signs engine + generator + code/runtime/source scope, excluding its own signature and pilot."""
    return {k:v for k,v in config.items() if k not in {'generator_approval','pilot'}}


def generator_review_errors(config):
    result = []
    prep = config.get('approval_preparation',{})
    if prep.get('candidate_frozen') is not True or prep.get('values_and_units_fully_specified') is not True:
        result.append('fully_specified_frozen_configuration_required')
    a = config.get('generator_approval')
    if not isinstance(a,dict) or a.get('status')!='approved' or not all(a.get(k) for k in
        ['reviewer','reviewer_role','reviewed_at','rationale','evidence_ref','generator_version','assumption_version','payload_sha256']):
        result.append('generator_formal_approval_missing')
        return result
    if a['generator_version']!=GENERATOR_VERSION:
        result.append('generator_approval_version_mismatch')
    if a['assumption_version']!=config.get('scenario_generator',{}).get('assumption_version'):
        result.append('generator_assumption_version_mismatch')
    try:
        iso_date(a['reviewed_at'],'generator_approval.reviewed_at')
    except ConfigurationError:
        result.append('generator_approval_date_invalid')
    if a['payload_sha256']!=fingerprint(generator_approval_payload(config)):
        result.append('generator_approval_payload_hash_mismatch')
    return result
