"""Explicit local diagnostic: print a quarantined response, retain all validators."""
import json
from pathlib import Path
import sys
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from component4.planner_dashboard_api import PlannerDashboard
import component4.local_llm_report as llm

original=llm.local_request
def inspect(method,path,payload=None,timeout=3):
    result=original(method,path,payload,timeout)
    if path=='/api/chat':print(json.dumps({'QUARANTINED_DEBUG_RESPONSE':result},indent=2),flush=True)
    return result

if __name__=='__main__':
    api=PlannerDashboard();state=api.config()['default_state'];response=api.calculate({'baseline':state,'alternative':state})
    with patch.object(llm,'local_request',side_effect=inspect):llm.generate(response)
