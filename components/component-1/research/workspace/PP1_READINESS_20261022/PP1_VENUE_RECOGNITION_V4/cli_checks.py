"""Fresh actual CLI inputs, exact logs/exit codes. Does not alter earlier artifacts."""
from common import *
import subprocess,time
V=H.parent/'PP1_FLOORPLAN_AI_DEVELOPMENT_V3';parts=read(H/'objects_v2/SPLITS.json');positive=next(r for r in parts['test'] if r['annotations'])
bad=H/'evidence/CORRUPT_INPUT.jpg';bad.write_bytes(b'not an image')
cases=[('INDOOR_CLI',positive['source'],'indoor',True,0),('SCUT_CORRECTED_CLI',read(H/'outdoor/SOURCE_REGISTRY.json')[0]['layout'],'outdoor',False,0),
 ('USER_PDF_CLI',str(ROOT/'03_REAL_VENUE_REFERENCES/00_INBOX/PDF_ORIGINALS/feb-2025-floor-plan.pdf'),'indoor',True,0),('CORRUPT_CLI',str(bad),'outdoor',False,1)]
records=[]
for name,source,route,exp,expected in cases:
 out=H/'cli'/name;argv=[sys.executable,'-B',str(H/'upload_inference.py'),'--source',source,'--route',route,'--out',str(out)]
 if exp:argv+=['--experimental-objects']
 start=time.perf_counter()
 with (H/'evidence'/(name+'.stdout.log')).open('x',encoding='utf-8') as stdout,(H/'evidence'/(name+'.stderr.log')).open('x',encoding='utf-8') as stderr:p=subprocess.run(argv,cwd=ROOT,stdout=stdout,stderr=stderr)
 row={'case':name,'argv':argv,'cwd':str(ROOT),'exit':p.returncode,'expected_exit':expected,'seconds':time.perf_counter()-start}
 if p.returncode==0:
  result=read(out/'UPLOAD_RESULT.json');row.update(pages=len(result['pages']),actual_model_calls=[p['actual_model_calls'] for p in result['pages']],object_calls=[p['existing_12_event_object_detection']['calls'] for p in result['pages']],candidate_counts=[len(p['candidate_bundle']['objects']) for p in result['pages']],metric_twin_ready=result['metric_twin_ready'])
  assert result['metric_twin_ready'] is False
 if name=='SCUT_CORRECTED_CLI':assert len(result['pages'][0]['candidate_bundle']['objects'])>0
 records.append(row);assert p.returncode==expected,name
save('evidence/CLI_EXECUTION.json',records);print([(r['case'],r['exit']) for r in records])
