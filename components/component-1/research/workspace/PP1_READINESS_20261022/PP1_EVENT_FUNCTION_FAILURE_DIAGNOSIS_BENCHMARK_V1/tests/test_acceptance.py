import argparse,json,unittest
from pathlib import Path
from PIL import Image
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=Path(__file__).resolve().parents[1]);ROOT=ap.parse_known_args()[0].out.resolve()
PIX=json.loads((ROOT/'raw/pixel_replay.json').read_text(encoding='utf-8-sig'))
KNOX=json.loads((ROOT/'raw/knox_diagnostic_replay.json').read_text(encoding='utf-8-sig'))
VERIFY=json.loads((ROOT/'raw/independent_verification.json').read_text(encoding='utf-8-sig'))
class BenchmarkAcceptance(unittest.TestCase):
 def test_fixed_pixel_sample_and_no_new_inference(self):
  self.assertEqual(PIX['record_count'],10);self.assertEqual(PIX['actual_new_model_forward_passes'],0)
 def test_source_annotation_mask_hash_pairs(self):
  self.assertTrue(all(x['source_annotation_identity_hashes_match_manifest'] for x in PIX['records']))
  self.assertTrue(all(x['derived_mask_hash_matches_manifest'] for x in PIX['records']))
  self.assertTrue(all(x['prediction_hash_matches_record'] for x in PIX['records']))
 def test_pooled_native_cvc_metric_replay(self):
  self.assertAlmostEqual(PIX['pooled_miou'],0.2817846731867826,places=12)
  self.assertEqual([x['gt_support'] for x in PIX['class_metrics']],[445209,83065,24560,19979])
  self.assertEqual(PIX['class_metrics'][2]['iou'],0.015019394879751746)
  self.assertEqual(PIX['class_metrics'][3]['iou'],0.0)
 def test_event_truth_absent_and_real_rates_not_estimable(self):
  self.assertEqual(PIX['event_function_label_count'],0)
  self.assertEqual(PIX['false_acceptance_rate'],'NOT_ESTIMABLE')
  self.assertEqual(PIX['false_refusal_rate'],'NOT_ESTIMABLE')
  self.assertEqual(KNOX['real_venue_false_acceptance_refusal'],'NOT_ESTIMABLE')
 def test_conditional_connectivity_reproduced_by_two_methods(self):
  self.assertEqual(KNOX['scenario_count'],4);self.assertEqual(KNOX['bfs_floyd_scenario_matches'],4)
  self.assertTrue(all(x['both_match_saved'] for x in KNOX['scenarios']))
 def test_edge_counterfactual_functions(self):
  lost={x['counterfactual_closed_edge']:x['functions_lost'] for x in KNOX['counterfactual_edge_ablation']}
  self.assertEqual(lost['EVENT_TO_EXTERIOR'],['exterior_candidate'])
  self.assertEqual(lost['EVENT_TO_SERVICE_SIDE'],['service_side_candidate'])
 def test_conservative_all_states_abstains(self):
  self.assertFalse(KNOX['baselines']['B4_robust_all_declared_states']['all_scenarios_jointly_preserve_service_and_exterior_connectivity'])
  self.assertEqual(KNOX['actual_layout_optimizer_evaluations'],0)
 def test_independent_oracle_and_visuals(self):
  self.assertEqual(VERIFY['status'],'PASS');self.assertGreaterEqual(VERIFY['independent_assertions'],100)
  self.assertEqual(VERIFY['visualizations_checked'],10)
  for rec in PIX['records']:
   name=Path(rec['record']).stem+'_source_diagnostic.png'
   with Image.open(ROOT/'figures'/name) as im:self.assertEqual(im.size,(4*512+5*8,512+54))
if __name__=='__main__':unittest.main(verbosity=2)
