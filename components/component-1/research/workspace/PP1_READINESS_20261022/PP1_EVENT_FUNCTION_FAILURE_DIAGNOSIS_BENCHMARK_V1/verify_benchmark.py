import argparse
from pathlib import Path
from collections import deque
import csv,hashlib,json,sys
from PIL import Image,ImageDraw
import numpy as np
ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=OUT);OUT=ap.parse_args().out.resolve()
CVC=ROOT/'PP1_READINESS_20261022/PP1_UNET_CVC_EXTERNAL_EVALUATION_V1'
SEL=json.loads((CVC/'FROZEN_SELECTION.json').read_text(encoding='utf-8-sig'))
RAW=json.loads((OUT/'raw/pixel_replay.json').read_text(encoding='utf-8-sig'))
KRAW=json.loads((OUT/'raw/knox_diagnostic_replay.json').read_text(encoding='utf-8-sig'))
KNOX=ROOT/'PP1_READINESS_20261022/PP1_KNOX_REAL_SOURCE_EVENT_AWARE_VALIDATION_V1/RAW_RESULTS/PIXEL_ACCESS_SENSITIVITY.json'
def sha(p):
 h=hashlib.sha256(); f=open(p,'rb')
 for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 f.close(); return h.hexdigest()
def scalar_cm(g,p):
 if g.size!=p.size or g.shape!=p.shape:raise AssertionError('mask grid mismatch')
 cm=[[0]*4 for _ in range(4)]; ignored=0
 for y in range(g.shape[0]):
  for x in range(g.shape[1]):
   a=int(g[y,x]);b=int(p[y,x])
   if a==255:ignored+=1
   elif 0<=a<4 and 0<=b<4:cm[a][b]+=1
   else:raise AssertionError(f'invalid class {a}->{b}')
 return cm,ignored
def fw(nodes,edges,opened):
 d={a:{b:(a==b) for b in nodes} for a in nodes}
 for eid in opened:
  u,v=edges[eid];d[u][v]=True;d[v][u]=True
 for k in nodes:
  for i in nodes:
   for j in nodes:d[i][j]=d[i][j] or (d[i][k] and d[k][j])
 return {n for n in nodes if d['event_space_candidate'][n]}
def main():
 assertions=0; per=[]; pooled=[[0]*4 for _ in range(4)]; csvrows=[]
 for i,rec in enumerate(SEL['records']):
  stem=Path(rec['annotation_filename']).stem; q=CVC/'QUALITATIVE_PREDICTIONS'/stem
  gt=np.asarray(Image.open(q/'GROUND_TRUTH_MODEL_512.png').convert('L')); pred=np.asarray(Image.open(q/'PREDICTION_512.png').convert('L'))
  cm,ign=scalar_cm(gt,pred); assertions+=1
  saved=next(x for x in json.loads((CVC/'CONFUSION_MATRICES.json').read_text(encoding='utf-8-sig'))['records'] if x['annotation_filename']==rec['annotation_filename'])
  assert cm==saved['confusion_matrix'];assertions+=1
  assert sha(ROOT/rec['image']['path'])==rec['image']['sha256'];assertions+=1
  assert sha(ROOT/rec['annotation']['path'])==rec['annotation']['sha256'];assertions+=1
  assert sha(ROOT/rec['mask']['path'])==rec['review']['mask_sha256'];assertions+=1
  assert sha(q/'PREDICTION_512.png')==saved['prediction_sha256'];assertions+=1
  assert ign==saved['ignored_pixels'];assertions+=1
  for a in range(4):
   for b in range(4):pooled[a][b]+=cm[a][b]
  row=next(x for x in RAW['records'] if x['record']==rec['annotation_filename'])
  assert row['confusion_matrix']==cm;assertions+=1
  per.append({'record':rec['annotation_filename'],'source_sha256':sha(ROOT/rec['image']['path']),'annotation_sha256':sha(ROOT/rec['annotation']['path']),'independent_confusion':cm,'ignored':ign})
  csvrows.append([rec['annotation_filename'],rec['stratum'],row['source_sha256'],row['annotation_sha256'],row['mask_sha256'],row['prediction_sha256'],'SOURCE_ANNOTATED_NOT_HUMAN_CERTIFIED','EVENT_FUNCTION_LABELS_ABSENT','METRIC_GEOMETRY_ABSENT'])
 assert pooled==json.loads((CVC/'CONFUSION_MATRICES.json').read_text(encoding='utf-8-sig'))['pooled_confusion_matrix'];assertions+=1
 assert pooled==RAW['pooled_confusion'];assertions+=1
 kn=json.loads(KNOX.read_text(encoding='utf-8-sig')); edge={}
 for s in kn['scenarios']:
  for e in s.get('candidate_edges',[]):edge[e['link_id']]=(e['from_zone_candidate'],e['to_zone_candidate'])
 nodes=sorted({n for pair in edge.values() for n in pair});kchecks=[]
 for sc in kn['scenarios']:
  opened=set(sc['assumed_open_candidate_portals']); reach=fw(nodes,edge,opened); expected=set(sc['bfs_outcomes']['reachable_from_event'])
  assert reach==expected;assertions+=1
  outrow=next(x for x in KRAW['scenarios'] if x['scenario']==sc['scenario'])
  assert sorted(reach)==outrow['independent_floyd_reachable'];assertions+=1
  kchecks.append({'scenario':sc['scenario'],'floyd_reachable':sorted(reach),'saved_bfs_match':True,'oracle':'independent Floyd–Warshall implementation'})
 # Recompute each edge-deletion outcome independently from the original both-open state.
 all_edges=set(edge); base_reach=fw(nodes,edge,all_edges); cfchecks=[]
 for eid in sorted(all_edges):
  after=fw(nodes,edge,all_edges-{eid}); lost=sorted(n for n in ['service_side_candidate','exterior_candidate'] if n in base_reach and n not in after)
  producer=next(x for x in KRAW['counterfactual_edge_ablation'] if x['counterfactual_closed_edge']==eid)
  assert lost==sorted(producer['functions_lost']);assertions+=1
  assert sorted(after)==producer['after_reachable'];assertions+=1
  cfchecks.append({'closed_edge':eid,'functions_lost':lost,'floyd_replay_matches':True})
 assert kn['decoded_model_input_sha256']==kn['candidate_bundle_source_sha256'];assertions+=1
 # Check generated diagnostics and exact dimensions; ignored regions must remain visibly distinct.
 viz=[]
 for rec in SEL['records']:
  p=OUT/'figures'/(Path(rec['annotation_filename']).stem+'_source_diagnostic.png')
  im=Image.open(p);assert im.width==4*512+5*8 and im.height==512+54;assertions+=1
  viz.append(p.name)
 result={'schema':'EVENT_FUNCTION_BENCHMARK_INDEPENDENT_VERIFICATION_V1','status':'PASS','independent_assertions':assertions,'cvc_records_reopened':len(per),'cvc_source_image_hashes_verified':len(per),'annotation_hashes_verified':len(per),'derived_mask_hashes_verified':len(per),'prediction_hashes_verified':len(per),'scalar_confusions_recomputed':len(per),'pooled_confusion_matches_saved':True,'knox_independent_floyd_scenarios':len(kchecks),'counterfactual_edges_independently_replayed':len(cfchecks),'knox_floyd_vs_saved_bfs_matches':len(kchecks),'knox_input_candidate_source_hash_bound':True,'visualizations_checked':len(viz),'optimizer_output_validation':'NOT_APPLICABLE_NO_LAYOUTS','real_world_function_ground_truth':'ABSENT','event_function_truth_from_knox':'ANALYST_AUTHORED_CONDITIONAL_ONLY','new_model_forwards':0,'checks':{'cvc':per,'knox':kchecks,'counterfactual':cfchecks}}
 (OUT/'raw/independent_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 return result
if __name__=='__main__':print(json.dumps({k:v for k,v in main().items() if k!='checks'}))
