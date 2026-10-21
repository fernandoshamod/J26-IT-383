"""Read-only saved-model PP1 checks; writes evidence, never fits or edits data."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import threading
import http.client

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from component4.planner_dashboard_api import PlannerDashboard
from component4.planner_dashboard_http import create_server
from component4.expense_risk import make_estimate
from component4.local_llm_report import status, generate


def main():
    output = ROOT / 'reports' / ('pp1_demo_check_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    output.mkdir(exist_ok=False)
    protected = [ROOT / p for p in (
        'outputs/Component4_Hybrid_Dataset_Final_v1.0.zip',
        'dataset_releases/v1.0/Component4_Hybrid_Dataset_Final_v1.0.zip',
        'data/experiments/v3.0/expense_risk_v3_0_20261015/planning_risk_dataset.jsonl')]
    def hashes():
        return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    before = hashes()
    api = PlannerDashboard()
    base = api.config()['default_state']
    original = deepcopy(base)
    records = []
    comparisons = []
    for name, extra in [('good', 0), ('warning', 500000), ('bad', 800000), ('loss', 1200000)]:
        alternative = deepcopy(base)
        if extra:
            alternative['quotes'] = [make_estimate('PP1 assumed diagnostic expense', extra, 0)]
        response = api.calculate({'baseline': base, 'alternative': alternative})
        a = response['alternative']; p = a['plan']
        assert a['status'] == 'calculated'
        assert abs(sum(p['line_items_lkr'].values()) - p['total_cost_lkr']) < .011
        assert abs(p['total_cost_lkr'] - 1570450.2 - extra) < .011
        assert abs(p['expected_profit_lkr'] - (base['retained_receipts_lkr'] - p['total_cost_lkr'])) < .011
        assert base == original, 'preview_mutated_original'
        assert 0 <= response['insights']['score']['value'] <= 100
        assert a['monte_carlo'] is not None
        if name != 'loss':
            assert a['model_trace']['prediction_executed']
            assert a['model_trace']['shap_additivity_verified']
            assert all(a['shap_drivers'].values())
        else:
            assert p['expected_profit_lkr'] < 0
            assert response['insights']['score']['value'] == 0
            assert not a['model_trace']['prediction_executed']
            assert all(v is None for v in a['model_scores'].values())
        assert 'NATIVE TREESHAP' in response['report_text'] if name != 'loss' else 'withheld' in response['report_text'].lower()
        records.append({'case': name, 'assumed_added_lkr': extra, 'cost_lkr': p['total_cost_lkr'],
                        'profit_lkr': p['expected_profit_lkr'], 'margin_pct': p['expected_margin_pct'],
                        'health': response['insights']['score']['value'], 'model_scores': a['model_scores'],
                        'prediction_executed': a['model_trace']['prediction_executed'],
                        'support_reasons': a['model_support']['reasons'], 'graph_status': a['graph_risk']['status'],
                        'monte_carlo': a['monte_carlo']})
        comparisons.append(response)
        (output / (name + '.json')).write_text(json.dumps(response, indent=2), encoding='utf-8')
        print(name, records[-1]['cost_lkr'], records[-1]['health'], flush=True)
    assert records[0]['health'] > records[1]['health'] > records[2]['health'] > records[3]['health']
    invalid = deepcopy(base); invalid['guests'] = 300
    blocked = api.calculate({'baseline': base, 'alternative': invalid})
    assert blocked['alternative']['status'] != 'calculated'
    assert blocked['insights']['score'] is None
    server = create_server(0, dashboard=api)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    http_checks = {}
    try:
        for path in ('/', '/api/health', '/api/planner/config', '/api/planner/model-evidence'):
            connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=20)
            connection.request('GET', path); reply = connection.getresponse(); body = reply.read()
            assert reply.status == 200 and body, (path, reply.status)
            http_checks[path] = reply.status; connection.close()
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)
    llm = {'runtime': status(), 'actual_generation': []}
    if llm['runtime']['ready']:
        for index in (0, 2, 3):
            snapshot = json.dumps(comparisons[index], sort_keys=True)
            try:
                draft = generate(comparisons[index])
                assert snapshot == json.dumps(comparisons[index], sort_keys=True)
                (output / (records[index]['case'] + '_local_ai.json')).write_text(json.dumps(draft, indent=2), encoding='utf-8')
                llm['actual_generation'].append({'case': records[index]['case'], 'status': draft['status']})
            except Exception as error:
                llm['actual_generation'].append({'case': records[index]['case'], 'status': 'FAIL', 'error': str(error)})
            print('LLM', llm['actual_generation'][-1], flush=True)
    after = hashes(); assert before == after
    report = {'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'calculation_model_and_http_checks': 'PASS', 'cases': records,
              'invalid_capacity_blocked': True, 'preview_preserves_original': True,
              'http_checks': http_checks, 'local_llm': llm, 'protected_inputs_unchanged': before == after,
              'protected_sha256': after, 'browser_visual_check_this_run': False,
              'limitations': ['Synthetic evaluation, not observed-event accuracy.',
                              'Health is rule-based; Monte Carlo shocks are hypothetical.',
                              'Loss case correctly withholds out-of-support model scores.',
                              'Local AI output requires human semantic review.']}
    (output / 'verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('REPORT', output / 'verification.json', flush=True)
    return 0 if llm['runtime']['ready'] and all(r['status'] != 'FAIL' for r in llm['actual_generation']) else 2


if __name__ == '__main__':
    raise SystemExit(main())
