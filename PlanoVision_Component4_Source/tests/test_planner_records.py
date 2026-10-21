from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date, timedelta
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from component4.planner_records import PlannerRecords, RecordError
from component4.planner_dashboard_api import PlannerDashboard
from component4.planner_dashboard_http import create_server


def booking(day=None):
    return dict(resource='TEST ONLY venue', date=day or (date.today()+timedelta(days=30)).isoformat(), label='TEST event', event_type='Wedding', client_name='TEST client', client_contact='', event_category='Wedding', status='reserved')


class PlannerRecordTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'test.sqlite3';self.store=PlannerRecords(self.path)

    def test_persist_reopen_move_cancel_restore_and_revision(self):
        result=self.store.write('booking',booking());b=result['records'][0]
        self.assertEqual(PlannerRecords(self.path).listing('booking')['records'],result['records'])
        moved=booking((date.today()+timedelta(days=31)).isoformat());moved['client_name']='Changed client'
        result=self.store.write('booking',moved,b['id'],1)
        self.assertEqual(result['revisions'][b['id']],2)
        self.assertEqual(result['records'][0]['created_at'],b['created_at'])
        with self.assertRaises(RecordError):self.store.write('booking',moved,b['id'],1)
        result=self.store.write('booking',None,b['id'],2,delete=True)
        self.assertEqual(result['records'][0]['status'],'cancelled')
        result=self.store.write('booking',moved,b['id'],3)
        self.assertEqual(result['records'][0]['status'],'reserved')

    def test_concurrent_date_uniqueness(self):
        self.store.listing('booking')
        def attempt(_):
            try:self.store.write('booking',booking());return True
            except RecordError as exc:self.assertEqual(exc.status,409);return False
        with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(attempt,range(4)))
        self.assertEqual(sum(results),1)
        self.assertEqual(len(self.store.listing('booking')['records']),1)

    def test_invalid_date_fields_and_conflicting_move_leave_original(self):
        first=self.store.write('booking',booking())['records'][0]
        other=booking((date.today()+timedelta(days=31)).isoformat());self.store.write('booking',other)
        for bad in [other,{**booking(),'date':date.today().isoformat()},{**booking(),'client_name':5},{**booking(),'approvals':True}]:
            with self.assertRaises(RecordError):self.store.write('booking',bad,first['id'],1)
        self.assertEqual(self.store.listing('booking')['revisions'][first['id']],1)

    def test_explicit_legacy_import_is_idempotent_and_reports_conflicts(self):
        a=self.store.write('booking',booking())['records'][0]
        legacy={**a,'id':'legacy-other'}
        result=self.store.import_bookings([a,legacy])
        self.assertEqual([r['status'] for r in result['import_results']],['already_imported','not_imported'])
        self.assertEqual(len(result['records']),1)
        self.assertEqual(legacy['status'],'reserved')


class PlannerRecordHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.api=PlannerDashboard(extended_calculator_scope=True)

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'http.sqlite3'
        self.server=create_server(0,dashboard=self.api,storage_path=self.path)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(3)
    def request(self,method,path,payload=None,origin=None):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=10)
        headers={'Content-Type':'application/json'}
        if origin:headers['Origin']=origin
        c.request(method,'/api/planner/'+path,None if payload is None else json.dumps(payload),headers)
        r=c.getresponse();status=r.status;data=json.loads(r.read());c.close();return status,data

    def test_financial_event_create_read_update_delete(self):
        plan=deepcopy(self.api.config()['default_state'])
        payload={'name':'TEST saved wedding','client_name':'TEST client','plan':plan}
        code,result=self.request('POST','events',{'record':payload});self.assertEqual(code,201)
        r=result['records'][0];identifier=r['id']
        self.assertEqual(self.request('GET','events')[1]['records'][0]['plan'],plan)
        payload['plan']['target_budget_lkr']=2100000
        code,result=self.request('PUT','events/'+identifier,{'record':payload,'expected_revision':1});self.assertEqual(code,200)
        self.assertEqual(result['records'][0]['plan']['target_budget_lkr'],2100000)
        self.assertEqual(self.request('DELETE','events/'+identifier,{'expected_revision':1})[0],409)
        self.assertEqual(self.request('DELETE','events/'+identifier,{'expected_revision':2})[1]['records'],[])
        self.assertEqual(self.request('GET','events')[1]['records'],[])

    def test_invalid_plans_output_injection_and_cross_origin_rejected(self):
        plan=self.api.config()['default_state'];plan['model_scores']={'fake':1}
        payload={'record':{'name':'bad','client_name':'','plan':plan}}
        self.assertEqual(self.request('POST','events',payload)[0],400)
        self.assertEqual(self.request('POST','bookings',{'record':booking()},'https://untrusted.invalid')[0],403)
        self.assertEqual(self.request('GET','events')[1]['records'],[])

    def test_booking_http_conflict_and_persistent_database(self):
        code,data=self.request('POST','bookings',{'record':booking()});self.assertEqual(code,201)
        identifier=data['records'][0]['id']
        self.assertEqual(self.request('POST','bookings',{'record':booking()})[0],409)
        self.assertEqual(PlannerRecords(self.path).listing('booking')['records'][0]['id'],identifier)
        self.assertEqual(self.request('DELETE','bookings/'+identifier,{'expected_revision':1})[1]['records'][0]['status'],'cancelled')
        self.assertEqual(self.request('POST','bookings',{'record':booking()})[0],201)

    def test_storage_identity(self):
        code,result=self.request('GET','storage');self.assertEqual(code,200)
        self.assertEqual(result['version'],'planner-records.1')

    def test_repeated_rejected_bodies_return_status_without_dispatch_or_reset(self):
        for _ in range(20):
            for method,path in [('POST','bookings'),('POST','events'),('PUT','events/fake'),('DELETE','bookings/fake'),('POST','compare')]:
                with self.subTest(method=method,path=path):
                    self.assertEqual(self.request(method,path,{'record':booking()},'https://untrusted.invalid')[0],403)
        self.assertEqual(self.request('GET','events')[1]['records'],[])
        self.assertEqual(self.request('GET','bookings')[1]['records'],[])

    def test_booking_edit_move_cancel_restore_and_conflict_over_http(self):
        first=booking();second=booking((date.today()+timedelta(days=33)).isoformat())
        code,result=self.request('POST','bookings',{'record':first});self.assertEqual(code,201)
        identifier=result['saved_id']
        moved={**first,'date':(date.today()+timedelta(days=32)).isoformat(),'client_name':'TEST edited client','event_category':'Wedding reception'}
        code,result=self.request('PUT','bookings/'+identifier,{'record':moved,'expected_revision':1});self.assertEqual(code,200)
        self.assertEqual(result['records'][0]['client_name'],'TEST edited client')
        self.assertEqual(result['records'][0]['date'],moved['date'])
        self.assertEqual(self.request('POST','bookings',{'record':second})[0],201)
        self.assertEqual(self.request('PUT','bookings/'+identifier,{'record':{**moved,'date':second['date']},'expected_revision':2})[0],409)
        self.assertEqual(self.request('DELETE','bookings/'+identifier,{'expected_revision':2})[0],200)
        self.assertEqual(self.request('PUT','bookings/'+identifier,{'record':moved,'expected_revision':3})[0],200)
        restored=next(r for r in self.request('GET','bookings')[1]['records'] if r['id']==identifier)
        self.assertEqual(restored['status'],'reserved');self.assertEqual(restored['date'],moved['date'])

    def test_preview_report_confirmed_update_and_deletion_keep_calendar_separate(self):
        baseline=deepcopy(self.api.config()['default_state'])
        payload={'name':'TEST connected flow','client_name':'TEST client','plan':baseline}
        code,created=self.request('POST','events',{'record':payload});self.assertEqual(code,201)
        identifier=created['saved_id']
        code,booked=self.request('POST','bookings',{'record':booking(baseline['event_date'])});self.assertEqual(code,201)
        booking_id=booked['saved_id']
        alternative=deepcopy(baseline)
        alternative['quotes'].append(dict(id='test_fireworks',label='TEST fireworks',mode='add',service='fireworks',quantity_basis='booking',unit_rate_lkr=50000,tax_scope='all_in',service_pct=0,tax_pct=0,pricing_policy='planning_estimate',increase_pct=0,source_kind='planner_entered_assumption',evidence_ref='TEST ONLY allowance',valid_from=baseline['event_date'],valid_until=baseline['event_date'],covers=['fireworks'],committed=False,cancellation_fee_lkr=0))
        code,preview=self.request('POST','compare',{'baseline':baseline,'alternative':alternative});self.assertEqual(code,200)
        self.assertAlmostEqual(preview['delta']['cost_lkr'],50000,places=2)
        self.assertTrue(preview['report_text'])
        self.assertGreaterEqual(preview['insights']['score']['value'],0)
        self.assertLessEqual(preview['insights']['score']['value'],100)
        self.assertEqual(self.request('GET','events')[1]['records'][0]['plan'],baseline)
        payload['plan']=alternative
        code,updated=self.request('PUT','events/'+identifier,{'record':payload,'expected_revision':1});self.assertEqual(code,200)
        self.assertEqual(updated['revisions'][identifier],2)
        saved=self.request('GET','events')[1]['records'][0]['plan'];self.assertEqual(saved,alternative)
        code,reloaded=self.request('POST','compare',{'baseline':saved,'alternative':saved});self.assertEqual(code,200)
        self.assertAlmostEqual(reloaded['baseline']['plan']['total_cost_lkr'],preview['alternative']['plan']['total_cost_lkr'],places=2)
        self.assertEqual(self.request('GET','bookings')[1]['records'][0]['id'],booking_id)
        self.assertEqual(self.request('DELETE','events/'+identifier,{'expected_revision':2})[0],200)
        self.assertEqual(self.request('GET','events')[1]['records'],[])
        self.assertEqual(self.request('GET','bookings')[1]['records'][0]['status'],'reserved')
        self.assertEqual(self.request('DELETE','bookings/'+booking_id,{'expected_revision':1})[0],200)
