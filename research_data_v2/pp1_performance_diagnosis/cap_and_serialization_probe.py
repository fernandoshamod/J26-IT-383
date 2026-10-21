"""Read-only candidate-cap and JSON encoding probe for the exact PP1 request."""
import csv
import json
import os
import sys
import time
from pathlib import Path
from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from backend.engine.dynamic_package_service import generate_dynamic_packages
from backend.schemas.dynamic_package_request import DynamicPackageRequest
HERE=Path(__file__).resolve().parent
request=DynamicPackageRequest.model_validate(json.loads((ROOT/'research_data_v2/pp1_final_submission/pp1_demo_inputs_and_outputs.json').read_text(encoding='utf-8'))['request'])
path=HERE/'performance_measurements.csv'
fields=['mode','repeat','phase','stage','elapsed_ms','calls','total_ms','status','event_id','package_count','generation_status','combinations_evaluated']
rows=[]
for repeat,cap in enumerate((12,24,6,12,24,6),1):
    os.environ['PLANOVISION_MAX_CANDIDATES_PER_SERVICE']=str(cap)
    start=time.perf_counter()
    result=generate_dynamic_packages(request)
    elapsed=round((time.perf_counter()-start)*1000,3)
    packages=result['generation']['packages']
    detail={'cap':cap,'elapsed_ms':elapsed,'option_ids':[p['option_ids'] for p in packages],'scores':[p['ranking_score'] for p in packages],'search':result['generation']['search']}
    (HERE/f'cap_{repeat}.json').write_text(json.dumps(detail,indent=2),encoding='utf-8')
    rows.append({'mode':f'cap_{cap}','repeat':repeat,'phase':'diagnostic','stage':'total_pipeline','elapsed_ms':elapsed,'calls':1,'total_ms':elapsed,'status':'ok','event_id':result['event_id'],'package_count':len(packages),'generation_status':result['generation']['status'],'combinations_evaluated':result['generation']['search']['combinations_evaluated']})
    print('cap',cap,elapsed,'combos',result['generation']['search']['combinations_evaluated'],'top',packages[0]['option_ids'] if packages else None,flush=True)
os.environ.pop('PLANOVISION_MAX_CANDIDATES_PER_SERVICE',None)
raw=json.loads((ROOT/'research_data_v2/pp1_final_live_demo_verification/api_response_evidence.json').read_text(encoding='utf-8-sig'))['response']
for repeat in range(1,5):
    start=time.perf_counter(); encoded=jsonable_encoder(raw); encode_ms=round((time.perf_counter()-start)*1000,3)
    start=time.perf_counter(); rendered=JSONResponse(encoded).body; render_ms=round((time.perf_counter()-start)*1000,3)
    for stage,elapsed in [('fastapi_jsonable_encoder',encode_ms),('json_response_render',render_ms)]:
        rows.append({'mode':'serialization','repeat':repeat,'phase':'warm','stage':stage,'elapsed_ms':elapsed,'calls':1,'total_ms':encode_ms+render_ms,'status':'ok','event_id':raw['event_id'],'package_count':len(raw['generation']['packages']),'generation_status':raw['generation']['status'],'combinations_evaluated':raw['generation']['search']['combinations_evaluated']})
    print('serialization',repeat,encode_ms,render_ms,len(rendered),flush=True)
with path.open('a',newline='',encoding='utf-8') as output:
    writer=csv.DictWriter(output,fieldnames=fields)
    writer.writerows(rows)
