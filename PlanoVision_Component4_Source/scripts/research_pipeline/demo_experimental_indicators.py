"""Write isolated API examples, not dataset rows or real price evidence."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from component4.experimental_indicators import health_request, invoice_request
from component4.unitless_decision_support import UnitlessDecisionSupport
from component4.contracts import validate_contract
from component4.release_input import sha256, assert_experiment_output


def main():
    target=ROOT/'reports/experimental_indicators_20261012'
    assert_experiment_output(target)
    paths=[ROOT/'outputs/Component4_Hybrid_Dataset_Final_v1.0.zip',
           ROOT/'dataset_releases/v1.0/Component4_Hybrid_Dataset_Final_v1.0.zip']
    before={str(p.relative_to(ROOT)):sha256(p) for p in paths}
    request={'event_type':'Wedding','inputs':{'guests':100,'event_hours':4,'stage_width_m':3,
             'stage_length_m':4,'budget_score':3,'retained_receipts_score':4},'draws':100,'seed':20261012}
    research=UnitlessDecisionSupport()
    response=health_request(research,request)
    invoice=json.loads((ROOT/'fixtures/quote_invoice.mock_test_only.json').read_text(encoding='utf-8'))
    comparison=invoice_request(invoice)
    schema=json.loads((ROOT/'api/contracts/experimental_indicators.response.schema.json').read_text())
    for item in (response,comparison):validate_contract(item,schema)
    replay=health_request(research,request)==response and invoice_request(invoice)==comparison
    after={str(p.relative_to(ROOT)):sha256(p) for p in paths}
    if before!=after or not replay:raise ValueError('integrity_or_replay_failure')
    files={'health_request.json':request,'health_response.json':response,'invoice_response.json':comparison,
           'verification.json':{'status':'PASS','deterministic_replay':replay,'release_hashes_unchanged':True,
                                'release_sha256':after,'scientific_validation':False}}
    target.mkdir(parents=True,exist_ok=True)
    if any((target/name).exists() for name in files):raise ValueError('example_outputs_already_exist')
    for name,item in files.items():
        (target/name).write_text(json.dumps(item,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps(files['verification.json'],indent=2))


if __name__=='__main__':main()
