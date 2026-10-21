"""Validate actual supplied local annotation JSON. No auto approval/training."""
from common import *
from annotation_contract import validate_annotation
import argparse
p=argparse.ArgumentParser();p.add_argument('--record',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
record=read(a.record);tasks=read(H/'annotations/TASKS_V2.json');task=next((t for t in tasks if t['task_id']==record.get('task_id')),None)
try:
 if task is None:raise ValueError('UNKNOWN_TASK_ID')
 result=validate_annotation(task,record)
 result.update(record_sha256=sha(a.record),task_manifest_sha256=sha(H/'annotations/TASKS_V2.json'),source_task_id=task['task_id'])
 save(a.out.resolve().relative_to(H),result);print(result['status'])
except (ValueError,AssertionError) as e:
 save(a.out.resolve().relative_to(H),{'status':'REJECTED','reason':str(e),'optimization_ready':False});raise SystemExit(2)
