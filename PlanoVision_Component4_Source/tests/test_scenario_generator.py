"""Small isolated software fixtures only. No real approvals, pilot export or bulk records."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from component4.engine import money, risk_labels, fingerprint
from component4.generator_validation import (ConfigurationError, GeneratorConfiguration, NumericDomain,
    generator_approval_payload, generator_review_errors)
from component4.scenario_generator import (FEATURE_UNITS, GenerationError, _write_bundle,
    generate_scenarios, generate_test_scenarios, pilot_execution_blockers, realize_ledger, write_pilot)
from fixtures.scenario_generator_test_fixture import fixture_configuration, fixed

ROOT = Path(__file__).resolve().parents[1]


class ScenarioGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.config = fixture_configuration()

    def generate(self,count=4):
        return generate_test_scenarios(self.config,count)

    def all_profiles(self):
        return self.config['archetypes'].values()

    def all_designs(self):
        return self.config['scenario_generator']['profiles'].values()

    def test_old_inputs_and_configuration_immutable(self):
        before = copy.deepcopy(self.config)
        old = (ROOT/'fixtures/config.mock_test_only.json').read_bytes()
        self.generate()
        self.assertEqual(before,self.config)
        self.assertEqual(old,(ROOT/'fixtures/config.mock_test_only.json').read_bytes())

    def test_financial_reconciliation(self):
        b = self.generate()
        for outcome,features in zip(b.simulated_outcomes,b.prediction_features):
            for ledger,total in [(b.planned_ledgers,features['planned_total_cost_lkr']),
                                 (b.realized_ledgers,outcome['realized_cost_lkr'])]:
                lines = [r for r in ledger if r['scenario_id']==outcome['scenario_id']]
                self.assertEqual(len(lines),14)
                self.assertEqual(sum(money(r['gross_lkr']) for r in lines),money(total))
                for r in lines:
                    self.assertEqual(money(r['net_lkr'])+money(r['tax_lkr']),money(r['gross_lkr']))

    def test_bundled_services_zero_charging(self):
        for p in self.all_profiles():
            p['billing']['included_items'] = {'chairs':'venue_fixed','tables':'venue_fixed'}
        b = self.generate()
        for r in b.planned_ledgers+b.realized_ledgers:
            if r['item_id'] in {'chairs','tables'}:
                self.assertEqual(r['gross_lkr'],0)
                self.assertEqual(r['included_in'],'venue_fixed')

    def test_cycles_and_nested_bundles_block(self):
        for mapping in [{'chairs':'tables','tables':'chairs'}, {'chairs':'tables','tables':'venue_fixed'}, {'chairs':'chairs'}]:
            self.config = fixture_configuration()
            self.config['archetypes']['Wedding']['billing']['included_items'] = mapping
            with self.assertRaises(ConfigurationError):
                self.generate()

    def test_bundled_service_cannot_be_anomaly_target(self):
        p = self.config['archetypes']['Wedding']
        p['billing']['included_items'] = {'catering':'venue_fixed'}
        with self.assertRaises(ConfigurationError):
            self.generate()

    def test_stage_seat_area_and_capacity(self):
        for r in self.generate(12).prediction_features:
            self.assertEqual(r['planned_seats'],r['guest_count'])
            self.assertEqual(r['quantity_stage'],r['stage_width_m']*r['stage_length_m'])
            self.assertLessEqual(r['used_area_m2'],r['usable_area_m2'])
            self.assertLessEqual(r['guest_count'],r['capacity_persons'])
            self.assertEqual(r['quantity_catering'],r['guest_count'])

    def test_geometric_rejections_logged_not_rescaled(self):
        for d in self.all_designs():
            d['parameter_domains']['guest_count'] = {'distribution':'choice','unit':'persons','values':[50,500]}
        b = self.generate(8)
        self.assertTrue(b.rejections)
        for r in b.rejections:
            self.assertEqual(r['planning_inputs']['guest_count'],500)
            self.assertTrue(any(x in r['blockers'] for x in ['used_area_exceeds_usable_area','guest_count_exceeds_arrangement_capacity']))
        self.assertTrue(all(r['guest_count']==50 for r in b.prediction_features))

    def test_max_attempts_fail_closed_with_log(self):
        self.config['scenario_generator']['max_attempts_per_scenario'] = 2
        for d in self.all_designs():
            d['parameter_domains']['guest_count'] = fixed(500,'persons')
        with self.assertRaises(GenerationError) as caught:
            self.generate(1)
        self.assertEqual(len(caught.exception.rejection_log),2)

    def test_av_exceedance_logged(self):
        for d in self.all_designs():
            d['parameter_domains']['stage_width_m'] = fixed(20,'m')
        with self.assertRaises(GenerationError) as caught:
            self.generate(1)
        self.assertIn('stage_exceeds_reviewed_package_scope',caught.exception.rejection_log[0]['blockers'])

    def test_standing_and_zero_stage_not_silently_supported(self):
        for field,value in [('seated_share',0.5),('stage_width_m',0)]:
            self.config = fixture_configuration()
            self.config['archetypes']['Wedding']['parameters'][field] = value
            with self.assertRaises(ConfigurationError):
                self.generate()

    def test_paid_hours_vs_monetary_overtime_quantity(self):
        for d in self.all_designs():
            d['parameter_domains']['event_hours'] = fixed(8,'hours')
        for r in self.generate().prediction_features:
            paid = r['event_hours']+r['setup_hours']+r['clearance_hours']
            staff = r['general_staff_count']
            regular = min(paid,r['regular_paid_hours_limit'])
            overtime = max(0,paid-regular)
            self.assertEqual(r['person_hours'],staff*paid)
            self.assertEqual(r['quantity_labour'],staff*(regular+overtime*r['overtime_multiplier']))
            self.assertGreater(r['quantity_labour'],r['person_hours'])

    def test_contingency_is_not_expense(self):
        a = self.generate()
        for p in self.all_profiles():
            p['parameters']['reserve_ratio'] = 0.2
        b = self.generate()
        for x,y in zip(a.prediction_features,b.prediction_features):
            self.assertEqual(x['planned_total_cost_lkr'],y['planned_total_cost_lkr'])
            self.assertEqual(x['expected_profit_lkr'],y['expected_profit_lkr'])
            self.assertEqual(money(y['contingency_reserve_lkr']),money(y['planned_total_cost_lkr']*0.2))

    def test_financially_risky_valid_scenarios_retained(self):
        for d in self.all_designs():
            d['budget_policy']['factor'] = fixed(0.85,'multiplier')
            d['retained_receipts'] = fixed(0,'LKR')
        b = self.generate()
        self.assertFalse(b.rejections)
        for r,o in zip(b.prediction_features,b.simulated_outcomes):
            self.assertGreater(r['planned_total_cost_lkr'],r['initial_budget_lkr'])
            self.assertLess(r['expected_profit_lkr'],0)
            self.assertIsNone(o['Profit_Margin_Risk'])

    def test_fixed_budget_policy(self):
        for d in self.all_designs():
            d['budget_policy'] = {'mode':'fixed','budget':fixed(150000,'LKR')}
        self.assertTrue(all(r['initial_budget_lkr']==150000 for r in self.generate().prediction_features))

    def test_reserve_funding_bounds_block(self):
        self.config['scenario_generator']['profiles']['Wedding']['budget_policy']['factor'] = fixed(0.01,'multiplier')
        with self.assertRaises(ConfigurationError):
            self.generate()

    def test_reproducibility_exact_bundle(self):
        self.assertEqual(self.generate(),self.generate())

    def test_prefix_stability_and_unique_ids(self):
        a,b = self.generate(2),self.generate(8)
        self.assertEqual(a.provenance,b.provenance[:2])
        self.assertEqual(a.prediction_features,b.prediction_features[:2])
        self.assertEqual(len({r['scenario_id'] for r in b.provenance}),8)

    def test_seed_change_changes_scenario_ids(self):
        a = self.generate()
        self.config['seed'] = self.config['scenario_generator']['seed'] = 314160
        self.assertNotEqual(a.provenance,self.generate().provenance)

    def test_shocks_do_not_change_planning_features_or_family_ids(self):
        a = self.generate()
        for p in self.all_profiles():
            p['outcome_uncertainty']['cost_bounds'] = {'min':2,'max':2,'unit':'multiplier'}
            p['outcome_uncertainty']['revenue_bounds'] = {'min':0.5,'max':0.5,'unit':'multiplier'}
            p['injected_vendor_regime']['prevalence'] = 1
        b = self.generate()
        self.assertEqual(a.prediction_features,b.prediction_features)
        self.assertEqual([r['family_id'] for r in a.provenance],[r['family_id'] for r in b.provenance])
        self.assertNotEqual(a.simulated_outcomes,b.simulated_outcomes)
        self.assertNotEqual([r['scenario_id'] for r in a.provenance],[r['scenario_id'] for r in b.provenance])

    def test_no_prediction_time_leakage_allowlist(self):
        b = self.generate()
        for row in b.prediction_features:
            self.assertEqual(set(row),set(FEATURE_UNITS))
            for key in row:
                self.assertFalse(any(s in key.lower() for s in ['realized','injection','shock','anomaly','risk','scenario_id','seed','label']))
        self.assertTrue(all('cost_factor' in r for r in b.latent_outcomes))

    def test_label_consistency(self):
        b = self.generate(8)
        for f,o,l in zip(b.prediction_features,b.simulated_outcomes,b.latent_outcomes):
            expected = risk_labels(o['realized_cost_lkr'],o['realized_retained_receipts_lkr'],f['initial_budget_lkr'],f['minimum_margin_points'],l['injection_flag'])
            self.assertEqual({k:o[k] for k in expected},expected)
            self.assertFalse(o['is_observed_event'])
            self.assertEqual(o['label_origin'],'simulated_rule_outcome')

    def test_anomaly_prevalence_zero_and_one(self):
        for prevalence in [0,1]:
            for p in self.all_profiles():
                p['injected_vendor_regime']['prevalence'] = prevalence
            b = self.generate()
            self.assertTrue(all(r['Vendor_Cost_Anomaly']==prevalence for r in b.simulated_outcomes))
            self.assertTrue(all(r['injection_flag']==bool(prevalence) for r in b.latent_outcomes))

    def test_anomaly_composes_once(self):
        for p in self.all_profiles():
            p['outcome_uncertainty']['cost_bounds'] = {'min':1.1,'max':1.1,'unit':'multiplier'}
            p['injected_vendor_regime']['prevalence'] = 1
            p['injected_vendor_regime']['multiplier_bounds'] = {'min':1.25,'max':1.25,'unit':'multiplier'}
        b = self.generate()
        for r in b.latent_outcomes:
            self.assertAlmostEqual(r['composed_service_multipliers']['catering'],1.375)

    def test_shared_rank_adverse_dependence(self):
        for p in self.all_profiles():
            p['outcome_uncertainty']['dependence_spec']['mode'] = 'shared_rank_adverse'
        for r in self.generate().latent_outcomes:
            self.assertAlmostEqual(r['cost_factor']+r['receipts_factor'],2)

    def test_unity_outcomes_reconcile_with_plan(self):
        for p in self.all_profiles():
            for k in ['cost_bounds','revenue_bounds']:
                p['outcome_uncertainty'][k] = {'min':1,'max':1,'unit':'multiplier'}
            p['injected_vendor_regime']['prevalence'] = 0
            p['rates']['catering'].update(tax_scope='exclusive',tax_rate_points=10)
            p['rates']['labour'].update(tax_scope='inclusive',tax_rate_points=12)
        for f,o in zip(self.generate().prediction_features,self.generate().simulated_outcomes):
            self.assertEqual(f['planned_total_cost_lkr'],o['realized_cost_lkr'])
            self.assertEqual(f['expected_receipts_lkr'],o['realized_retained_receipts_lkr'])

    def test_both_archetypes_and_date_bounds(self):
        b = self.generate(16)
        self.assertEqual({r['event_type'] for r in b.prediction_features},{'Wedding','Corporate'})
        self.assertTrue(all('2026-10-20'<=r['event_date']<='2026-10-23' for r in b.prediction_features))

    def test_source_and_assumption_ancestry(self):
        for r in self.generate().provenance:
            self.assertTrue(r['family_id'].startswith('F-'))
            self.assertTrue(r['split_group_id'].startswith('G-'))
            self.assertIn('A030',r['assumption_ids'])
            self.assertEqual(r['source_snapshot_hashes'],self.config['source_snapshot_hashes'])
            self.assertIsNone(r['parent_scenario_id'])

    def test_units_and_missing_rates_block(self):
        for field,value in [('unit','USD/person'),('rate',None),('tax_rate_points',None)]:
            self.config = fixture_configuration()
            self.config['archetypes']['Wedding']['rates']['catering'][field] = value
            with self.assertRaises(ConfigurationError):
                self.generate()

    def test_strict_boolean_strings_null_nan_infinity_huge_inputs(self):
        for value in [True,'100',None,float('nan'),float('inf'),10**400]:
            self.config = fixture_configuration()
            self.config['archetypes']['Wedding']['parameters']['guest_count'] = value
            with self.assertRaises(ConfigurationError):
                self.generate()

    def test_strict_count_types_and_domain_units(self):
        for value in [fixed(50.0,'persons'),fixed(50,'LKR'),{'distribution':'uniform','unit':'persons','min':50,'max':60}]:
            self.config = fixture_configuration()
            self.config['scenario_generator']['profiles']['Wedding']['parameter_domains']['guest_count'] = value
            with self.assertRaises(ConfigurationError):
                self.generate()

    def test_domain_bounds_and_unknown_fields(self):
        for domain in [fixed(0,'persons'),{'distribution':'uniform_integer','unit':'persons','min':60,'max':50},
                       {'distribution':'uniform_integer','unit':'persons','min':50,'max':60,'unknown':1}]:
            self.config = fixture_configuration()
            self.config['scenario_generator']['profiles']['Wedding']['parameter_domains']['guest_count'] = domain
            with self.assertRaises(ConfigurationError):
                self.generate()

    def test_missing_null_seed_and_attempt_limit(self):
        for field,value in [('seed',None),('seed',True),('max_attempts_per_scenario',None),('max_attempts_per_scenario',0)]:
            self.config = fixture_configuration()
            self.config['scenario_generator'][field] = value
            with self.assertRaises(ConfigurationError):
                self.generate()

    def test_snapshot_code_and_runtime_mismatch(self):
        for field in ['source_snapshot_hashes','code_snapshot_hashes']:
            self.config = fixture_configuration()
            first = next(iter(self.config['scenario_generator'][field]))
            self.config['scenario_generator'][field][first] = '0'*64
            with self.assertRaises(ConfigurationError):
                self.generate()
        self.config = fixture_configuration()
        self.config['scenario_generator']['software_versions']['numpy'] = '0.0.0'
        with self.assertRaises(ConfigurationError):
            self.generate()

    def test_no_snapshot_path_escape(self):
        self.config['scenario_generator']['source_snapshot_hashes'] = {'../outside':'0'*64}
        with self.assertRaises(ConfigurationError):
            self.generate()

    def test_date_cutoff_and_quote_leakage(self):
        for kind in ['cutoff','quote','reversed']:
            self.config = fixture_configuration()
            if kind=='cutoff':
                self.config['calibration_cutoff'] = '2026-10-24'
            elif kind=='quote':
                self.config['archetypes']['Wedding']['rates']['catering']['quote_date'] = '2026-10-24'
            else:
                self.config['scenario_generator']['profiles']['Wedding']['date_bounds']['end'] = '2026-10-01'
            with self.assertRaises(ConfigurationError):
                self.generate()

    def test_missing_shock_and_anomaly_regimes_block_not_default_zero(self):
        for field in ['outcome_uncertainty','injected_vendor_regime']:
            self.config = fixture_configuration()
            self.config['archetypes']['Wedding'][field] = None
            with self.assertRaises(ConfigurationError):
                self.generate()

    def test_invalid_shock_distributions_or_overlap(self):
        for field,value in [('distribution','normal'),('dependence_spec',{'mode':'independent','cost_services':['catering','catering']})]:
            self.config = fixture_configuration()
            self.config['archetypes']['Wedding']['outcome_uncertainty'][field] = value
            with self.assertRaises(ConfigurationError):
                self.generate()

    def test_fixture_limits_and_live_marker_firewall(self):
        with self.assertRaises(ConfigurationError):
            self.generate(17)
        with self.assertRaises(ConfigurationError):
            generate_scenarios(self.config,20)
        self.config['record_kind'] = 'approved_simulator_configuration'
        with self.assertRaises(ConfigurationError):
            self.generate()

    def test_gate_rejection_creates_no_directory(self):
        candidate = json.loads((ROOT/'config/simulator.candidate.json').read_text(encoding='utf-8'))
        for config in [self.config,candidate]:
            with tempfile.TemporaryDirectory(prefix='scenario-tests-',dir=ROOT/'work') as temp:
                self.assertTrue(Path(temp).resolve().is_relative_to((ROOT/'work').resolve()))
                target = Path(temp)/'must_not_exist'
                with self.assertRaises(ConfigurationError):
                    write_pilot(config,target)
                self.assertFalse(target.exists())
        self.assertIn('explicit_pilot_authorization_missing',pilot_execution_blockers(candidate))
        self.assertIn('generator_formal_approval_missing',pilot_execution_blockers(candidate))

    def test_generator_review_hash_binds_regime_and_code(self):
        # In-memory SHAPE/HASH branch only: this is NOT a real reviewer record or pilot authority.
        self.config['approval_preparation'] = {'candidate_frozen':True,'values_and_units_fully_specified':True}
        self.config['generator_approval'] = {'status':'approved','reviewer':'UNIT TEST - NOT A PERSON',
            'reviewer_role':'TEST ONLY','reviewed_at':'2026-10-11','rationale':'branch test only',
            'evidence_ref':'NOT-AN-APPROVAL','generator_version':'0.1.0-proposed',
            'assumption_version':'TEST-ONLY-NOT-APPROVED','payload_sha256':fingerprint(generator_approval_payload(self.config))}
        self.assertEqual(generator_review_errors(self.config),[])
        self.assertTrue(pilot_execution_blockers(self.config))  # Still fixture; no live authority.
        self.config['archetypes']['Wedding']['injected_vendor_regime']['prevalence'] = 0.5
        self.assertIn('generator_approval_payload_hash_mismatch',generator_review_errors(self.config))

    def test_serializer_sidecars_and_checksums_temporary_fixture_only(self):
        bundle = self.generate(2)
        with tempfile.TemporaryDirectory(prefix='scenario-tests-',dir=ROOT/'work') as temp:
            self.assertTrue(Path(temp).resolve().is_relative_to((ROOT/'work').resolve()))
            target = Path(temp)/'isolated_software_fixture'
            _write_bundle(bundle,target)
            manifest = json.loads((target/'manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['origin'],'mock_test_fixture')
            for name,digest in manifest['artifact_sha256'].items():
                self.assertEqual(hashlib.sha256((target/name).read_bytes()).hexdigest(),digest)
            row = json.loads((target/'prediction_features.jsonl').read_text().splitlines()[0])
            self.assertEqual(set(row),{'scenario_id','features'})
            self.assertEqual(set(row['features']),set(FEATURE_UNITS))
            with self.assertRaises(FileExistsError):
                _write_bundle(bundle,target)

    def test_numeric_domains_inclusive_integer_and_fixed_boundaries(self):
        rng = np.random.Generator(np.random.PCG64(1))
        domain = NumericDomain.parse({'distribution':'uniform_integer','unit':'persons','min':1,'max':2},'persons','test',integer=True)
        self.assertEqual({domain.sample(rng) for _ in range(20)},{1,2})
        constant = NumericDomain.parse({'distribution':'uniform','unit':'hours','min':4,'max':4},'hours','test')
        self.assertEqual(constant.sample(rng),4)

    def test_unit_template_never_runs(self):
        template = json.loads((ROOT/'config/scenario_generator.template.json').read_text())
        self.config['scenario_generator'] = template
        with self.assertRaises(ConfigurationError):
            self.generate()

    def test_malformed_nested_objects_fail_as_configuration_errors(self):
        for key,value in [('code_snapshot_hashes',[{}]),('source_snapshot_hashes',[]),('profiles',[]),('archetype_weights',False)]:
            self.config = fixture_configuration()
            self.config['scenario_generator'][key] = value
            with self.assertRaises(ConfigurationError):
                self.generate()

    def test_zero_charged_anomaly_targets_block(self):
        self.config['archetypes']['Wedding']['rates']['catering']['rate'] = 0
        with self.assertRaises(ConfigurationError):
            self.generate()


if __name__=='__main__':
    unittest.main()
