"""Local-only LKR research dashboard server, separate from the live API."""
import argparse
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from .planner_dashboard_api import PlannerDashboard
from .dashboard_evidence import evidence_summary, verified_bytes

ROOT=Path(__file__).resolve().parents[1]


def create_server(port=8765, *, dashboard=None, storage_path=None):
    dashboard=dashboard or PlannerDashboard(extended_calculator_scope=True)
    from .planner_records import PlannerRecords, RecordError, exact
    records=PlannerRecords(storage_path or ROOT/'runtime/planner.sqlite3')
    static=ROOT/'frontend/dist'
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def valid(self):
            return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
        def send(self,code,data,kind='application/json; charset=utf-8'):
            # Closing a Windows socket with unread POST/PUT/DELETE bytes can reset
            # the connection before its rejection reaches the client. Drain only
            # bounded, non-chunked bodies; never dispatch rejected content.
            if code>=400 and self.command in {'POST','PUT','DELETE'} and not getattr(self,'body_consumed',False):
                try:
                    length=int(self.headers.get('Content-Length','0'))
                    if not self.headers.get('Transfer-Encoding') and 0<length<=262144:
                        previous=self.connection.gettimeout()
                        try:
                            self.connection.settimeout(1)
                            self.rfile.read(length)
                        finally:self.connection.settimeout(previous)
                except (ValueError,OSError):pass
                self.body_consumed=True
            if not isinstance(data,bytes):data=json.dumps(data,allow_nan=False).encode()
            self.send_response(code)
            for k,v in {'Content-Type':kind,'Content-Length':str(len(data)),'Cache-Control':'no-store',
                        'X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY',
                        'Content-Security-Policy':"default-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'"}.items():self.send_header(k,v)
            self.end_headers();self.wfile.write(data)
        def do_GET(self):
            if not self.valid():self.send(403,{'error':'loopback_host_required'});return
            path=urlsplit(self.path).path
            if path=='/api/planner/storage':
                self.send(200,{'storage':'sqlite','version':'planner-records.1','database':'runtime/planner.sqlite3','scope':'local-machine only; no authentication or hotel integration'});return
            if path in {'/api/planner/bookings','/api/planner/events'}:
                try:self.send(200,records.listing('booking' if path.endswith('bookings') else 'event'))
                except (sqlite3.Error,OSError):self.send(503,{'error':'Database unavailable; records were not replaced.'})
                return
            if path=='/api/planner/model-evidence' or path.startswith('/api/planner/evidence-image/'):
                try:
                    if path=='/api/planner/model-evidence':self.send(200,evidence_summary())
                    else:
                        key=path.removeprefix('/api/planner/evidence-image/')
                        if key not in {'learning-curves.png','error-concentration.png','regime-performance.png'}:
                            self.send(404,{'error':'not_found'});return
                        self.send(200,verified_bytes(key),'image/png')
                except (OSError,ValueError,KeyError,TypeError):self.send(503,{'error':'verified_model_evidence_unavailable'})
                return
            if path=='/api/planner/config':self.send(200,dashboard.config());return
            if path=='/api/planner/llm-status':
                try:
                    from .local_llm_report import status
                    self.send(200,status())
                except (OSError,ValueError):self.send(503,{'error':'invalid_local_llm_configuration'})
                return
            if path=='/api/planner/future-price-catalog':
                try:
                    from .future_price_forecast import catalog
                    self.send(200,catalog())
                except (OSError,ValueError,KeyError):self.send(503,{'error':'verified_future_price_deployment_unavailable'})
                return
            if path=='/api/planner/forecast-catalog':
                try:
                    from .forecast_bridge import catalog
                    self.send(200,catalog())
                except (OSError,ValueError,KeyError):self.send(503,{'error':'verified_historical_forecasts_unavailable'})
                return
            if path=='/api/health':self.send(200,{'status':'ok','mode':'research_only','live_enabled':False});return
            if path.startswith('/api/'):self.send(404,{'error':'not_found'});return
            relative='index.html' if path=='/' else path.lstrip('/')
            file=(static/relative).resolve()
            if not file.is_relative_to(static.resolve()) or not file.is_file():self.send(404,{'error':'frontend_not_built_or_not_found'});return
            kind={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.svg':'image/svg+xml'}.get(file.suffix,'application/octet-stream')
            self.send(200,file.read_bytes(),kind)
        def record_write(self,method):
            if not self.valid():self.send(403,{'error':'loopback_host_required'});return
            allowed={f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}','http://127.0.0.1:5173','http://localhost:5173'}
            if self.headers.get('Origin') not in allowed|{None} or self.headers.get('Sec-Fetch-Site')=='cross-site':
                self.send(403,{'error':'cross_origin_forbidden'});return
            if self.headers.get_content_type()!='application/json':self.send(415,{'error':'application_json_required'});return
            try:
                length=int(self.headers.get('Content-Length','-1'))
                if self.headers.get('Transfer-Encoding') or not 0<length<=262144:self.send(413,{'error':'invalid_request_length'});return
                def pairs(items):
                    obj={}
                    for key,value in items:
                        if key in obj:raise ValueError('duplicate_json_key')
                        obj[key]=value
                    return obj
                raw=self.rfile.read(length);self.body_consumed=True
                payload=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite_json')))
                path=urlsplit(self.path).path
                if path=='/api/planner/bookings/import' and method=='POST':
                    exact(payload,('bookings',));self.send(200,records.import_bookings(payload['bookings']));return
                parts=path.split('/')
                if len(parts) not in (4,5) or parts[1:3]!=['api','planner'] or parts[3] not in ('bookings','events'):
                    self.send(404,{'error':'not_found'});return
                identifier=parts[4] if len(parts)==5 else None
                if (method=='POST' and identifier) or (method!='POST' and not identifier):
                    self.send(405,{'error':'Unsupported record operation.'});return
                kind='booking' if parts[3]=='bookings' else 'event'
                exact(payload,('record',) if method=='POST' else ('expected_revision',) if method=='DELETE' else ('record','expected_revision'))
                if kind=='event' and method!='DELETE':
                    exact(payload['record'],('name','client_name','plan'))
                    dashboard.state(payload['record']['plan'])
                    checked=dashboard.calculate({'baseline':payload['record']['plan'],'alternative':payload['record']['plan']})
                    if checked['baseline']['status']!='calculated':raise RecordError('Cannot save an invalid or unresolved financial plan.')
                response=records.write(kind,payload.get('record'),identifier,payload.get('expected_revision'),delete=method=='DELETE')
                self.send(201 if method=='POST' else 200,response)
            except RecordError as exc:self.send(exc.status,{'error':str(exc)})
            except (ValueError,TypeError,KeyError,UnicodeError) as exc:self.send(400,{'error':str(exc)[:200]})
            except (sqlite3.Error,OSError):self.send(503,{'error':'Database unavailable; no save success claimed.'})
        def do_PUT(self):self.record_write('PUT')
        def do_DELETE(self):self.record_write('DELETE')
        def do_POST(self):
            if self.path.startswith('/api/planner/bookings') or self.path.startswith('/api/planner/events'):
                self.record_write('POST');return
            if not self.valid():self.send(403,{'error':'loopback_host_required'});return
            allowed={f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}','http://127.0.0.1:5173','http://localhost:5173'}
            if self.headers.get('Origin') not in allowed|{None}:self.send(403,{'error':'cross_origin_forbidden'});return
            if self.path.startswith('/api/live/'):
                self.send(403,{'status':'blocked','error':'live_not_approved_no_research_fallback'});return
            if self.path not in {'/api/planner/compare','/api/planner/component2/import','/api/planner/forecast-preview','/api/planner/future-price-preview','/api/planner/llm-report'}:self.send(404,{'error':'not_found'});return
            if self.headers.get_content_type()!='application/json':self.send(415,{'error':'application_json_required'});return
            try:
                length=int(self.headers.get('Content-Length','-1'))
                if self.headers.get('Transfer-Encoding') or not 0<length<=65536:self.send(413,{'error':'invalid_request_length'});return
                def pairs(items):
                    result={}
                    for k,v in items:
                        if k in result:raise ValueError('duplicate_json_key')
                        result[k]=v
                    return result
                raw=self.rfile.read(length);self.body_consumed=True
                payload=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite_json')))
                if self.path=='/api/planner/llm-report':
                    from .local_llm_report import generate,LLMUnavailable
                    try:self.send(200,generate(dashboard.calculate(payload)))
                    except LLMUnavailable as exc:self.send(503,{'error':str(exc),'status':'unavailable_no_fake_llm_fallback'})
                    return
                if self.path=='/api/planner/future-price-preview':
                    from .future_price_forecast import preview
                    try:self.send(200,preview(payload))
                    except OSError:self.send(503,{'error':'verified_future_price_deployment_unavailable'})
                    return
                if self.path=='/api/planner/component2/import':
                    from .component2_adapter import import_bundle,strict_json
                    if not isinstance(payload,dict) or set(payload)!={'bundle_json','state'}:raise ValueError('exact_component2_import_fields_required')
                    dashboard.state(payload['state'])
                    self.send(200,import_bundle(strict_json(payload['bundle_json']),payload['state']));return
                if self.path=='/api/planner/forecast-preview':
                    from .forecast_bridge import preview
                    try:self.send(200,preview(payload))
                    except OSError:self.send(503,{'error':'verified_historical_forecasts_unavailable'})
                    return
                self.send(200,dashboard.calculate(payload))
            except (ValueError,TypeError,KeyError,UnicodeError) as exc:self.send(400,{'error':str(exc)[:200]})
            except Exception:self.send(500,{'error':'calculation_failed_no_fallback'})
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    server.daemon_threads=True
    server.records=records
    return server


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);args=parser.parse_args()
    server=create_server(args.port)
    print(f'Component 4 local RESEARCH dashboard: http://127.0.0.1:{server.server_port}',flush=True)
    print('No live vendor fetching. No real-world calibration. Ctrl+C to stop.',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()


if __name__=='__main__':main()
