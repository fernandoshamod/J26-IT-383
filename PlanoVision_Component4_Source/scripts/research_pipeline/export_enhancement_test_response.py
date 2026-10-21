"""Generate test-only frontend fixture from actual verified native inference."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from component4.planner_dashboard_api import PlannerDashboard

if __name__=='__main__':
    api=PlannerDashboard();p=api.config()['default_state'];result=api.calculate({'baseline':p,'alternative':p})
    path=ROOT/'frontend/src/test-fixtures/training-evaluation.response.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    print('Actual saved model test response:',path)
