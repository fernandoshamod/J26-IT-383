"""Read-only PP1 performance probe. Patches callables only in this process."""
import csv
import json
import sys
import time
import urllib.request
from collections import defaultdict
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
HERE = Path(__file__).resolve().parent
SAVED = ROOT / 'research_data_v2/pp1_final_submission/pp1_demo_inputs_and_outputs.json'
REQUEST = json.loads(SAVED.read_text(encoding='utf-8'))['request']
from backend.engine import dynamic_package_service as service
from backend.engine import bounded_package_generator as generator
from backend.engine import risk_signals
from backend.schemas.dynamic_package_request import DynamicPackageRequest
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

rows = []

def ms(seconds):
    return round(seconds * 1000, 3)

def timed(stack, module, name, label, sums, counts):
    original = getattr(module, name)
    def wrapped(*args, **kwargs):
        start = time.perf_counter()
        try:
            return original(*args, **kwargs)
        finally:
            sums[label] += time.perf_counter() - start
            counts[label] += 1
    stack.enter_context(patch.object(module, name, wrapped))

def run_pipeline(repeat):
    request = DynamicPackageRequest.model_validate(REQUEST)
    sums = defaultdict(float)
    counts = defaultdict(int)
    with ExitStack() as stack:
        for module, name, label in [
            (service, 'load_service_options', 'option_loading'),
            (service, 'select_candidates_for_event', 'candidate_filtering'),
            (service, 'load_risk_signals', 'risk_stage'),
            (service, 'load_compatibility_rules', 'compatibility_loading'),
            (service, 'service_compatibility', 'compatibility_scoring'),
            (service, 'generate_bounded_packages', 'bounded_generation'),
            (service, 'to_json_safe', 'json_safe_conversion'),
            (generator, '_select_diverse_candidates', 'candidate_cap_selection'),
            (generator, 'validate_service_option_lkr', 'candidate_price_validation'),
            (generator, 'validate_dynamic_package', 'feasibility'),
            (generator, '_ranking', 'ranking'),
            (generator, 'explain_package', 'explanation'),
            (risk_signals, 'verified_model', 'verified_model_total'),
            (risk_signals, '_load_verified_model', 'model_deserialization'),
            (RandomForestClassifier, 'predict', 'rf_inference'),
        ]:
            timed(stack, module, name, label, sums, counts)
        original_read_csv = pd.read_csv
        def read_csv_wrapped(*args, **kwargs):
            path = str(args[0]) if args else ''
            label = ('profile_csv' if 'real_vendor_profiles.csv' in path else
                     'option_csv' if 'synthetic_service_options.csv' in path else
                     'matrix_csv' if 'vendor_compatibility_matrix.csv' in path else 'other_csv')
            start = time.perf_counter()
            try:
                return original_read_csv(*args, **kwargs)
            finally:
                sums[label] += time.perf_counter() - start
                counts[label] += 1
        stack.enter_context(patch.object(pd, 'read_csv', read_csv_wrapped))
        start = time.perf_counter()
        result = service.generate_dynamic_packages(request)
        elapsed = time.perf_counter() - start
    sums['profile_join_other'] = sums['risk_stage'] - sums['verified_model_total'] - sums['profile_csv'] - sums['rf_inference']
    sums['bounded_remainder'] = sums['bounded_generation'] - sum(sums[k] for k in ('candidate_cap_selection', 'candidate_price_validation', 'feasibility', 'ranking', 'explanation'))
    sums['other_pipeline'] = elapsed - sum(sums[k] for k in ('option_loading','candidate_filtering','risk_stage','compatibility_loading','compatibility_scoring','bounded_generation','json_safe_conversion'))
    base = {'mode':'pipeline','repeat':repeat,'phase':'cold' if repeat == 1 else 'warm',
            'total_ms':ms(elapsed),'status':'ok','event_id':result['event_id'],
            'package_count':len(result['generation']['packages']),
            'generation_status':result['generation']['status'],
            'combinations_evaluated':result['generation']['search']['combinations_evaluated']}
    for label, seconds in sums.items():
        rows.append({**base,'stage':label,'elapsed_ms':ms(seconds),'calls':counts[label]})
    print('pipeline',repeat,ms(elapsed),{k:ms(v) for k,v in sums.items()},flush=True)

def run_http(repeat):
    body = json.dumps(REQUEST, separators=(',',':')).encode('utf-8')
    req = urllib.request.Request('http://127.0.0.1:8000/api/packages/generate-dynamic',body,{'Content-Type':'application/json'},method='POST')
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=180) as response:
        raw = response.read()
        status = response.status
    elapsed = time.perf_counter() - start
    result = json.loads(raw)
    base = {'mode':'http','repeat':repeat,'phase':'cold' if repeat == 1 else 'warm',
            'total_ms':ms(elapsed),'status':status,'event_id':result['event_id'],
            'package_count':len(result['generation']['packages']),
            'generation_status':result['generation']['status'],
            'combinations_evaluated':result['generation']['search']['combinations_evaluated']}
    rows.append({**base,'stage':'total_http','elapsed_ms':ms(elapsed),'calls':1})
    print('http',repeat,ms(elapsed),len(raw),flush=True)

if __name__ == '__main__':
    for n in range(1,5):
        run_http(n)
    for n in range(1,5):
        run_pipeline(n)
    path = HERE / 'performance_measurements.csv'
    with path.open('w',newline='',encoding='utf-8') as output:
        writer = csv.DictWriter(output, fieldnames=['mode','repeat','phase','stage','elapsed_ms','calls','total_ms','status','event_id','package_count','generation_status','combinations_evaluated'])
        writer.writeheader()
        writer.writerows(rows)
