"""Save one illustrative decision-response report, never training scenarios."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from component4.unitless_decision_support import UnitlessDecisionSupport
from component4.release_input import assert_experiment_output,sha256
from component4.contracts import validate_contract

payload={'event_type':'Wedding','baseline':{'guests':100,'event_hours':4,'stage_width_m':3,
    'stage_length_m':4,'budget_score':3,'retained_receipts_score':4},
    'alternative_changes':{'guests':120,'stage_length_m':6,'event_hours':7},'draws':2000,'seed':20261012}
service=UnitlessDecisionSupport()
before={str(p.relative_to(ROOT)):sha256(p) for p in (service.archive,ROOT/'outputs/Component4_Hybrid_Dataset_Final_v1.0.zip')}
response=service.request(payload,'what-if')
schema=json.loads((ROOT/'api/contracts/unitless_decision.response.schema.json').read_text())
validate_contract(response,schema)
if response!=service.request(payload,'what-if'):raise ValueError('replay_mismatch')
after={str(p.relative_to(ROOT)):sha256(p) for p in (service.archive,ROOT/'outputs/Component4_Hybrid_Dataset_Final_v1.0.zip')}
if before!=after:raise ValueError('release_changed')
folder=assert_experiment_output(ROOT/'reports/unitless_decision_integration_20261012')
folder.mkdir(parents=True,exist_ok=True)
(folder/'example_request.json').write_text(json.dumps(payload,indent=2))
(folder/'example_response.json').write_text(json.dumps(response,indent=2))
(folder/'integration_verification.json').write_text(json.dumps({'status':'PASS','contract':'PASS','paired_replay':'PASS',
    'frozen_archives_unchanged':True,'source_hashes':before,'persistent_training_scenarios_generated':0,
    'models_retrained':False,'report_kind':'illustrative_unitless_decision_response_not_training_data'},indent=2))
print(json.dumps({'status':'PASS','baseline':response['baseline']['planned'],
    'alternative':response['alternative']['planned'],'delta':response['delta'],
    'response_path':str(folder/'example_response.json')},indent=2))
