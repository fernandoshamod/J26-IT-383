import argparse,csv,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
CVC=ROOT/'PP1_READINESS_20261022/PP1_UNET_CVC_EXTERNAL_EVALUATION_V1'
SEL=json.loads((CVC/'FROZEN_SELECTION.json').read_text(encoding='utf-8-sig'))
CONF=json.loads((CVC/'CONFUSION_MATRICES.json').read_text(encoding='utf-8-sig'))
OLD=json.loads((ROOT/'PP1_READINESS_20261022/PP1_COMMENT3_FINAL_SCIENTIFIC_RESOLUTION_V1/RAW_EXPERIMENTS_AND_REPRODUCTION/SOURCE_EVIDENCE_HASHES.json').read_text(encoding='utf-8-sig'))
def sha(p):
 h=hashlib.sha256();f=open(p,'rb')
 for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 f.close();return h.hexdigest()
def main():
 checks=[]
 for rec in SEL['records']:
  checks += [(rec['image']['path'],rec['image']['sha256']),(rec['annotation']['path'],rec['annotation']['sha256']),(rec['mask']['path'],rec['review']['mask_sha256'])]
  recm=next(x for x in CONF['records'] if x['annotation_filename']==rec['annotation_filename'])
  checks.append((f"PP1_READINESS_20261022/PP1_UNET_CVC_EXTERNAL_EVALUATION_V1/QUALITATIVE_PREDICTIONS/{Path(rec['annotation_filename']).stem}/PREDICTION_512.png",recm['prediction_sha256']))
 checks.append(('02_GENERATED_RESEARCH_DATA/STAGE_B_PP1_BASELINE/best_unet_resnet18.pt','480f15179818f63b1bdcfc5f72eef62cfdb0db092f27459f274fc72268888a5a'))
 knpath='research_inputs/Knox 6496.jpg';kn_expected='6dbd436b41d78b62e27f6fe321d2ac97d745d43d0c769878775edcc381b40fff';checks.append((knpath,kn_expected))
 rows=[]
 for rel,expect in checks:
  p=ROOT/rel; actual=sha(p) if p.is_file() else None;rows.append({'path':rel,'expected_sha256':expect,'actual_sha256':actual,'match':actual==expect})
 oldrows=[]
 for item in OLD['files']:
  p=ROOT/item['path'];actual=sha(p) if p.is_file() else None;oldrows.append({'path':item['path'],'expected_sha256':item['sha256'],'actual_sha256':actual,'match':actual==item['sha256']})
 prev=json.loads((ROOT/'PP1_READINESS_20261022/PP1_COMMENT3_FINAL_SCIENTIFIC_RESOLUTION_V1/PRESERVATION_VERIFICATION.json').read_text(encoding='utf-8-sig'))
 ok=all(x['match'] for x in rows+oldrows)
 result={'schema':'EVENT_FUNCTION_BENCHMARK_PRESERVATION_V1','status':'PASS_BOUNDED_REHASH' if ok else 'FAIL_HASH_MISMATCH','new_workspace_only_output':True,'frozen_backend_frontend_models_and_datasets_modified':False,'new_model_forwards':0,'new_optimizer_searches':0,'selected_source_and_prediction_hash_checks':len(rows),'selected_source_and_prediction_hash_matches':sum(x['match'] for x in rows),'prior_task_inputs_rehashed':len(oldrows),'prior_task_inputs_unchanged':sum(x['match'] for x in oldrows),'previous_reported_snapshot_files_unchanged':prev['prior_snapshot_files_unchanged'],'previous_reported_snapshot_file_count':prev['prior_snapshot_files_checked'],'scope':'Selected fixed evaluation sources/predictions/checkpoint and 42 prior task inputs; prior package reports its 724-file bounded snapshot. Not whole-project or all-dataset bytewise proof.','checks':rows,'prior_task_checks':oldrows}
 (OUT/'PRESERVATION_VERIFICATION.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k not in ['checks','prior_task_checks']}))
if __name__=='__main__':main()
