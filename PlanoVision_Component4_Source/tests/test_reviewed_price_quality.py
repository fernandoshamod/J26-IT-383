from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from component4.future_price_forecast import artifacts,ROOT
from component4.reviewed_price_quality import BASE,load_review,quality_for

class ReviewedPriceQualityTests(unittest.TestCase):
    def test_all_series_bind_to_same_unchanged_forecast_history(self):
        manifest,data=artifacts();review=load_review(ROOT,manifest['source_member_sha256'])
        self.assertEqual(sum(bool(r['quality_flag']) for r in review['observations']),108)
        self.assertEqual(len(review['publisher_hashes']),181)
        for series in data['series']:
            q=quality_for(series,review);self.assertEqual(q['model_value_unresolved_count'],0)
            self.assertEqual(q['reviewed_records'],series['training_records'])
            self.assertFalse(q['independent_market_validation'])

    def test_review_artifact_tampering_fails_closed(self):
        manifest,_=artifacts()
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as tmp:
            root=Path(tmp);base=root/BASE;base.mkdir(parents=True)
            source=ROOT/BASE;review_manifest=json.loads((source/'manifest.json').read_text())
            for name in ['manifest.json',*review_manifest['files']]:(base/name).write_bytes((source/name).read_bytes())
            (base/'review.json').write_bytes((base/'review.json').read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'artifact_hash'):load_review(root,manifest['source_member_sha256'])

    def test_partial_coverage_is_rejected_and_unresolved_values_remain_visible(self):
        manifest,data=artifacts();review=load_review(ROOT,manifest['source_member_sha256']);info=data['series'][0]
        with self.assertRaisesRegex(ValueError,'coverage'):quality_for({**info,'training_records':info['training_records']+1},review)
        changed=deepcopy(review);next(r for r in changed['observations'] if r['series_id']==info['series_id'])['model_value_review_status']='unresolved'
        self.assertEqual(quality_for(info,changed)['model_value_unresolved_count'],1)
