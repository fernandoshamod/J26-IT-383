import csv
import os
from pathlib import Path
import profile_exact_request as probe
path=Path(__file__).with_name('performance_measurements.csv')
fields=['mode','repeat','phase','stage','elapsed_ms','calls','total_ms','status','event_id','package_count','generation_status','combinations_evaluated']
for repeat,cap in enumerate((6,12,24,24,12,6),1):
    os.environ['PLANOVISION_MAX_CANDIDATES_PER_SERVICE']=str(cap)
    before=len(probe.rows)
    probe.run_pipeline(repeat)
    current=probe.rows[before:]
    for row in current:
        row['mode']=f'cap_stage_{cap}'
        row['phase']='diagnostic'
    with path.open('a',newline='',encoding='utf-8') as output:
        writer=csv.DictWriter(output,fieldnames=fields)
        writer.writerows(current)
os.environ.pop('PLANOVISION_MAX_CANDIDATES_PER_SERVICE',None)
