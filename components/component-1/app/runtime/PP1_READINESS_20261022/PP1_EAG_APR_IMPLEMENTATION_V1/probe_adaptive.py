"""Targeted corrected-adapter probe against preserved actual pilot reference."""
from runtime import *
from repair import run,make_reference
from scenarios import change

base=HERE/'outputs/PILOT_001/VENUE_32_24_SEED_20261017'
initial=read(base/'INITIAL/FULL/RESULT.json');req=read(base/'BASE_INPUT/AUTHORITY_SIMULATED.json')
packet=read(base/'INITIAL/FULL/INPUT.json');reference=make_reference(packet['scene'],initial,read(base/'INITIAL/FULL/GRAPH.json'),base/'INITIAL/FULL')
approved=read(base/'APPROVAL/FULL/INPUT.json');reference.update(certificate=read(base/'APPROVAL/FULL/RESULT.json')['certificate'],graph=read(base/'APPROVAL/FULL/GRAPH.json'))
new=change('authorized_singleton_repair',approved,reference,HERE/'outputs/ADAPTIVE_PROBE_001/INPUT')
result,graph=run(new,HERE/'outputs/ADAPTIVE_PROBE_001/EXECUTION','EAG',20261017,reference)
print(__import__('json').dumps(dict(status=result['status'],reasons=result['reasons'],evaluations=result['optimizer_evaluations'],layouts=len(result['candidate_layouts']),invalid=result['invalidated_previous_candidates']),indent=2))
if result['status']!='eligible':raise SystemExit(1)
