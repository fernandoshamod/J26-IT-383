"""Loopback-only adapter; optional unitless inference never enables LKR live mode."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .api import dashboard_request
from .benchmark_api import benchmark_request, package_catalog
from .contracts import validate_contract
from .public_package_benchmark import load_evidence

ROOT = Path(__file__).resolve().parents[1]
MAX_REQUEST_BYTES = 8192


def create_server(port=8764, *, project_root=ROOT, enable_unitless_research=False):
    if type(enable_unitless_research) is not bool:
        raise ValueError('explicit_boolean_research_enable_required')
    config, evidence = load_evidence(project_root / 'config/public_hotel_benchmark.v0.1.json')
    live_config = json.loads((project_root / 'config/simulator.v0.1.template.json').read_text())
    live_schema = json.loads((project_root / 'api/contracts/financial_dashboard.response.schema.json').read_text())
    benchmark_schema = json.loads((project_root / 'api/contracts/public_package_benchmark.response.schema.json').read_text())
    research = None
    if enable_unitless_research:
        if Path(project_root).resolve() != ROOT.resolve():
            raise ValueError('unitless_models_require_verified_project_root')
        from .unitless_decision_support import UnitlessDecisionSupport
        research = UnitlessDecisionSupport()
    research_schema = json.loads((ROOT / 'api/contracts/unitless_decision.response.schema.json').read_text())

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send_json(self, code, value):
            # An early POST rejection can otherwise close with unread TCP data,
            # intermittently resetting the response on Windows. Drain only a
            # small, declared body with a bounded timeout; never parse/dispatch it.
            if self.command == 'POST' and not getattr(self, 'body_consumed', False):
                try:
                    length = int(self.headers.get('Content-Length', '-1'))
                    if 0 < length <= MAX_REQUEST_BYTES + 1 and not self.headers.get('Transfer-Encoding'):
                        previous_timeout = self.connection.gettimeout()
                        try:
                            self.connection.settimeout(1)
                            self.rfile.read(length)
                        finally:
                            self.connection.settimeout(previous_timeout)
                except (ValueError, OSError):
                    pass
                self.body_consumed = True
            data = json.dumps(value, allow_nan=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(data)

        def valid_host(self):
            host = self.headers.get('Host', '')
            return host in {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}

        def do_GET(self):
            if not self.valid_host():
                self.send_json(403, {'error': 'loopback_host_required'}); return
            if self.path == '/api/health':
                self.send_json(200, {'status': 'ok', 'mode': 'local_research',
                    'benchmark_config_version': config['config_version'],
                    'evidence_sha256': config['evidence_sha256'],
                    'live_calculation_approved': False, 'mock_fallback_enabled': False,
                    'unitless_research_enabled':research is not None})
            elif self.path == '/api/research/unitless/domains' and research is not None:
                self.send_json(200, {'api_version':'unitless-decision.0.1',
                    'warning':research.provenance(2000,20261012)['warning'],
                    'cost_unit':'dimensionless_score','currency':None,
                    'profiles':research.config['profiles'],'financial_health_score':None,
                    'configuration_sha256':research.configuration_sha})
            elif self.path == '/api/benchmark/packages':
                self.send_json(200, package_catalog(evidence))
            else:
                self.send_json(404, {'error': 'not_found'})

        def do_POST(self):
            if not self.valid_host():
                self.send_json(403, {'error': 'loopback_host_required'}); return
            # No open CORS: future Vite frontend uses a same-origin proxy.
            origin = self.headers.get('Origin')
            if origin is not None and origin not in {f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}', 'http://127.0.0.1:5173', 'http://localhost:5173'}:
                self.send_json(403, {'error': 'cross_origin_request_forbidden'}); return
            paths = {'/api/benchmark/estimate': 'estimate', '/api/benchmark/compare': 'compare', '/api/live/calculate': 'calculate', '/api/live/what-if': 'what-if'}
            if research is not None:
                paths.update({'/api/research/unitless/calculate':'calculate','/api/research/unitless/what-if':'what-if'})
                paths.update({'/api/research/experimental/planning-health':'planning-health',
                              '/api/research/experimental/quote-invoice':'quote-invoice'})
            if self.path not in paths:
                self.send_json(404, {'error': 'not_found'}); return
            if self.headers.get_content_type() != 'application/json':
                self.send_json(415, {'error': 'application_json_required'}); return
            try:
                length = int(self.headers.get('Content-Length', '-1'))
                if not 0 < length <= MAX_REQUEST_BYTES:
                    self.send_json(413, {'error': 'invalid_or_excessive_request_length'}); return
                body = self.rfile.read(length)
                self.body_consumed = True
                payload = json.loads(body, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite_json_forbidden')))
                if self.path.startswith('/api/research/experimental/'):
                    from .experimental_indicators import health_request, invoice_request
                    if paths[self.path]=='planning-health':
                        response = health_request(research,payload)
                        validate_contract(response['decision'],research_schema)
                    else:
                        response = invoice_request(payload)
                    indicator_schema = json.loads((ROOT / 'api/contracts/experimental_indicators.response.schema.json').read_text())
                    validate_contract(response,indicator_schema)
                elif self.path.startswith('/api/research/unitless/'):
                    response = research.request(payload,paths[self.path])
                    validate_contract(response,research_schema)
                elif self.path.startswith('/api/benchmark/'):
                    response = benchmark_request(evidence, payload, operation=paths[self.path])
                    if paths[self.path] == 'estimate':
                        validate_contract(response, benchmark_schema)
                    else:
                        validate_contract(response['baseline'], benchmark_schema)
                        validate_contract(response['alternative'], benchmark_schema)
                else:
                    response = dashboard_request(live_config, payload, operation=paths[self.path])
                    if paths[self.path] == 'calculate':
                        validate_contract(response, live_schema)
                    else:
                        validate_contract(response['baseline'], live_schema)
                        validate_contract(response['alternative'], live_schema)
                self.send_json(200, response)
            except (ValueError, TypeError, KeyError, OverflowError) as exc:
                self.send_json(422, {'error': str(exc)})

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    return server
