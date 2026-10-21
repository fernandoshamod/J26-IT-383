import copy,subprocess
from runtime import *
from eag_contracts import Packet

out=HERE/'outputs/CONTRACT_CHECKS_FINAL';out.mkdir(parents=True,exist_ok=False);base=HERE/'outputs/EXPERIMENT_FINAL/VENUE_32_24_SEED_20261017';valid=read(base/'authorized_singleton_repair/INPUT.json');checks=[]
def reject(name,packet):
    try:Packet.model_validate(packet);ok=False
    except ValueError:ok=True
    checks.append(dict(name=name,passed=ok))
Packet.model_validate(valid);checks.append(dict(name='ACTUAL_PACKET_ACCEPTED_BY_STRICT_SCHEMA',passed=True))
for name,mutate in [('UNKNOWN_CONTEXT_FIELD',lambda p:p['context'].update(cloud_weather='invented')),('WRONG_BOOLEAN_TYPE',lambda p:p['context'].update(new_supply_permitted='yes')),('UNSUPPORTED_WEATHER_SCOPE',lambda p:p['context'].update(scenario='RAIN_FORECAST')),('DUPLICATE_GROUP_PERMISSION',lambda p:p['context']['allowed_groups'].append(p['context']['allowed_groups'][0]))]:
    p=copy.deepcopy(valid);mutate(p);reject(name,p)
reference=HERE/'outputs/CLOSEOUT_FINAL/REFERENCE_EAG_V32_S20261017.json'
for case,destination,expected_code in [('authorized_singleton_repair','CLI_ADAPTIVE_FINAL',0),('missing_metric_verification','CLI_PENDING_FINAL',2)]:
    cmd=[sys.executable,'-B',str(HERE/'research.py'),'--input',str(base/case/'INPUT.json'),'--reference',str(reference),'--out','outputs/'+destination]
    proc=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);save(out/(case+'_COMMAND.json'),dict(args=cmd,exit_code=proc.returncode,stdout=proc.stdout,stderr=proc.stderr));checks.append(dict(name='ACTUAL_CLI_'+case,passed=proc.returncode==expected_code,expected_exit_code=expected_code,actual_exit_code=proc.returncode))
save(out/'TEST_RESULTS.json',dict(passed=all(r['passed'] for r in checks),checks=checks,skipped=0));print(__import__('json').dumps(checks,indent=2))
if not all(r['passed'] for r in checks):raise SystemExit(1)
