import json
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root))
from research_data_v2.pp1_task4_performance import baseline_profile as bp
saved=json.loads((root/'research_data_v2/pp1_final_submission/pp1_demo_inputs_and_outputs.json').read_text(encoding='utf-8'))['request']
bp.SCENARIOS['exact_saved']=saved
bp.run_one('exact_saved',profile=False)
result,_=bp.run_one('exact_saved',profile=True)
Path(__file__).with_name('cprofile_exact_warm.txt').write_text(result['cprofile_top30'],encoding='utf-8')
print(result['elapsed_ms'])
print(result['stage_ms'])
