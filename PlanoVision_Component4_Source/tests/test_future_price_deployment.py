from copy import deepcopy
import hashlib
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from component4.future_price_forecast import artifacts,catalog,preview,ROOT,BASE,MANIFEST_SHA256
from component4.planner_dashboard_http import create_server


def request(**kwargs):
    return dict({'series_id':'S003:Mysore Dhall - ( Average ):1 Kg.','target_month':'2026-10-01',
                 'unit':'LKR/1 Kg.','quantity':10,'expense_scope':'ingredient_component'},**kwargs)


class FuturePriceTests(unittest.TestCase):
    def test_scope_and_source_immutability(self):
        m,d=artifacts();c=catalog()
        self.assertEqual(m['records'],563);self.assertEqual(len(c['series']),12);self.assertEqual(len(d['forecasts']),36)
        self.assertEqual(sum(s['method']=='prophet' for s in d['series']),3)
        self.assertEqual(sum(s['training_quality_flag_count']==0 for s in d['series']),1)
        self.assertEqual(m['source_member_sha256'],m['files']['source_snapshot.csv'])
        self.assertIsNone(c['new_independent_accuracy_estimate']);self.assertFalse(c['applied_to_event_budget'])
        from component4.forecast_bridge import artifacts as old_artifacts
        old_artifacts() # Pinned old evaluation files still intact.
    def test_october_future_prophet_with_partial_quantity_not_package(self):
        r=preview(request());self.assertEqual(r['status'],'available_experimental_forecast')
        self.assertEqual(r['model'],'prophet');self.assertEqual(r['forecast_origin'],'2026-09-01')
        self.assertGreater(r['forecast_yhat'],0);self.assertEqual(r['horizon_months'],1)
        self.assertAlmostEqual(r['ingredient_subtotal_lkr'],round(r['forecast_yhat']*10,2))
        self.assertAlmostEqual(r['ingredient_change_from_last_observation_lkr'],round((r['forecast_yhat']-r['last_observed_y'])*10,2))
        self.assertFalse(r['applied_to_event_budget']);self.assertFalse(r['publication_timestamps_verified'])
    def test_flagged_current_values_convert_only_after_pinned_field_review(self):
        r=preview(request(series_id='S003:Anamalu:1 Kg.'))
        self.assertEqual(r['status'],'available_experimental_forecast');self.assertGreater(r['forecast_yhat'],0)
        self.assertEqual(r['training_quality_flag_count'],8)
        self.assertTrue(r['quality_review']['original_flags_preserved'])
        self.assertEqual(r['quality_review']['model_value_unresolved_count'],0)
        self.assertEqual(r['quality_review']['publisher_period_conflict_count'],1)
        self.assertGreater(r['ingredient_subtotal_lkr'],0)

    def test_unresolved_review_still_blocks_even_previously_unflagged_series(self):
        reviewed=preview(request())['quality_review'];reviewed['model_value_unresolved_count']=1
        with patch('component4.future_price_forecast.quality_for',return_value=reviewed):
            r=preview(request());self.assertEqual(r['status'],'review_required')
            self.assertIsNone(r['ingredient_subtotal_lkr']);self.assertIsNone(r['ingredient_change_from_last_observation_lkr'])

    def test_review_binds_same_history_and_preserves_raw_flags(self):
        from component4.reviewed_price_quality import load_review
        m,_=artifacts();r=load_review(ROOT,m['source_member_sha256'])
        self.assertEqual(len(r['observations']),563);self.assertEqual(len(r['source_decisions']),1900)
        self.assertEqual(r['source_status_counts'],{'source_value_confirmed_keep':1900})
        self.assertEqual(sum(bool(v['quality_flag']) for v in r['observations']),108)
        self.assertEqual(r['original_values_changed'],0);self.assertEqual(r['original_flags_removed'],0)
        with self.assertRaises(ValueError):load_review(ROOT,'0'*64)
        with patch('component4.reviewed_price_quality.MANIFEST_SHA256','0'*64):
            with self.assertRaises(ValueError):catalog()
    def test_indices_are_not_currency(self):
        r=preview(request(series_id='S001:CCPI:base2021',unit='index (base 2021)',quantity=None,expense_scope='market_context_only'))
        self.assertEqual(r['model'],'last_value');self.assertIsNone(r['ingredient_subtotal_lkr'])
        with self.assertRaises(ValueError):preview(request(series_id='S001:CCPI:base2021',unit='index (base 2021)',quantity=10,expense_scope='market_context_only'))
    def test_bad_inputs_are_rejected(self):
        for changes in ({'quantity':True},{'quantity':float('nan')},{'quantity':0},{'quantity':1e9},{'unit':'LKR/plate'},
                        {'expense_scope':'whole_catering_package'},{'target_month':'2026-10-22'},{'series_id':'venue'},
                        {'approval':True},{'target_month':'2026-13-01'}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):preview(request(**changes))
    def test_future_horizon_and_past_dates_are_blocked(self):
        for month in ('2026-09-01','2027-01-01'):
            r=preview(request(target_month=month));self.assertEqual(r['status'],'blocked');self.assertIsNone(r['forecast_yhat'])
    def test_nonpositive_forecast_is_not_clipped(self):
        m,d=artifacts();d=deepcopy(d)
        next(r for r in d['forecasts'] if r['series_id']==request()['series_id'] and r['ds']=='2026-10-01')['yhat']=-1
        with patch('component4.future_price_forecast.artifacts',return_value=(m,d)):
            r=preview(request());self.assertEqual(r['status'],'blocked');self.assertIsNone(r['ingredient_subtotal_lkr'])
    def test_checksum_tampering_fails_closed(self):
        with patch('component4.future_price_forecast.MANIFEST_SHA256','0'*64):
            with self.assertRaises(ValueError):catalog()
        with tempfile.TemporaryDirectory(dir=ROOT/'work') as tmp:
            root=Path(tmp);base=root/BASE;base.mkdir(parents=True)
            (base/'manifest.json').write_bytes((ROOT/(BASE+'manifest.json')).read_bytes())
            m,_=artifacts()
            for name in m['files']:(base/name).write_bytes((ROOT/(BASE+name)).read_bytes())
            (base/'forecasts.json').write_text('{}')
            with self.assertRaises(ValueError):catalog(root)
    def test_native_model_serialization_matches_saved_future_forecasts(self):
        import pandas as pd
        from prophet.serialize import model_from_json
        m,d=artifacts()
        for s in d['series']:
            if s['method']!='prophet':continue
            part=[r for r in d['forecasts'] if r['series_id']==s['series_id']]
            model=model_from_json((ROOT/(BASE+s['model_file'])).read_text(encoding='utf-8'))
            actual=model.predict(pd.DataFrame({'ds':pd.to_datetime([r['ds'] for r in part])}))['yhat'].tolist()
            for a,b in zip(actual,part):self.assertAlmostEqual(a,b['yhat'],places=8)
    def test_http_endpoints_and_no_live_fallback(self):
        server=create_server(0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            c=http.client.HTTPConnection('127.0.0.1',server.server_port)
            c.request('GET','/api/planner/future-price-catalog');r=c.getresponse();d=json.loads(r.read());self.assertEqual(r.status,200);self.assertEqual(len(d['series']),12)
            c.request('POST','/api/planner/future-price-preview',json.dumps(request()),{'Content-Type':'application/json'})
            r=c.getresponse();d=json.loads(r.read());self.assertEqual(r.status,200);self.assertEqual(d['status'],'available_experimental_forecast')
            c.request('POST','/api/live/future-price-preview','{}',{'Content-Type':'application/json'})
            r=c.getresponse();r.read();self.assertEqual(r.status,403);c.close()
        finally:server.shutdown();server.server_close();thread.join()


if __name__=='__main__':unittest.main()
