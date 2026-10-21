from __future__ import annotations
import argparse, csv, hashlib, json, sys
from pathlib import Path
from collections import deque
from PIL import Image, ImageDraw
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
CVC=ROOT/'PP1_READINESS_20261022/PP1_UNET_CVC_EXTERNAL_EVALUATION_V1'
KNOX=ROOT/'PP1_READINESS_20261022/PP1_KNOX_REAL_SOURCE_EVENT_AWARE_VALIDATION_V1/RAW_RESULTS/PIXEL_ACCESS_SENSITIVITY.json'
SELECTION=json.loads((CVC/'FROZEN_SELECTION.json').read_text(encoding='utf-8-sig'))
CONF=json.loads((CVC/'CONFUSION_MATRICES.json').read_text(encoding='utf-8-sig'))
CLASSES=['room_region','wall','door','window']
COLORS=[(55,155,235),(230,175,60),(220,65,65),(60,190,125)]

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def scalar_confusion(gt,pred):
    g=np.asarray(gt,dtype=np.uint8); p=np.asarray(pred,dtype=np.uint8)
    if g.shape!=p.shape: raise ValueError(f'alignment mismatch {g.shape} != {p.shape}')
    m=np.zeros((4,4),dtype=np.int64); valid=(g<4)
    for y,x in zip(g[valid].ravel(),p[valid].ravel()): m[int(y),int(x)]+=1
    return m, int((~valid).sum())

def save_viz(name,gt,pred,ignore):
    gt=np.asarray(gt); pred=np.asarray(pred); h,w=gt.shape
    panels=[]
    for arr,title in [(gt,'CVC reference mask (remapped)'),(pred,'Frozen U-Net prediction'),(None,'Error map: FN magenta / FP cyan')]:
        im=Image.new('RGB',(w,h),(25,25,25)); px=im.load()
        if arr is not None:
            for y in range(h):
                for x in range(w):
                    v=int(arr[y,x]); px[x,y]=(COLORS[v] if v<4 else (55,55,55))
        else:
            for y in range(h):
                for x in range(w):
                    g=int(gt[y,x]); p=int(pred[y,x])
                    if g>=4: px[x,y]=(45,45,45)
                    elif g==p: px[x,y]=(45,95,55)
                    elif p==0 and g!=0: px[x,y]=(235,65,190)
                    else: px[x,y]=(40,210,220)
        panels.append((im,title))
    gap=8; header=30; canvas=Image.new('RGB',(3*w+4*gap,h+header+2*gap),(242,244,247)); d=ImageDraw.Draw(canvas)
    for i,(im,title) in enumerate(panels):
        x=gap+i*(w+gap); y=header+gap; canvas.paste(im,(x,y)); d.text((x,y-22),title,fill=(20,30,45))
    canvas.save(OUT/'figures'/f'{name}_diagnostic.png')

def run():
    rows=[]; pooled=np.zeros((4,4),dtype=np.int64); copies=[]
    for rec in SELECTION['records']:
        name=rec['annotation_filename']; stem=Path(name).stem
        q=CVC/'QUALITATIVE_PREDICTIONS'/stem
        gtpath=q/'GROUND_TRUTH_MODEL_512.png'; predpath=q/'PREDICTION_512.png'; cvcpath=q/'GROUND_TRUTH_CVC_512.png'
        src=ROOT/rec['image']['path']; ann=ROOT/rec['annotation']['path']; mask=ROOT/rec['mask']['path']
        gt=Image.open(gtpath).convert('L'); pred=Image.open(predpath).convert('L')
        mat,ignored=scalar_confusion(gt,pred); pooled+=mat
        expected=np.asarray(rec.get('review',{}).get('source_sha256'))
        source_hash=sha(src); annotation_hash=sha(ann); source_pair_match=(source_hash==rec['image']['sha256'] and annotation_hash==rec['annotation']['sha256'])
        mask_match=sha(mask)==rec['review']['mask_sha256']
        saved=np.asarray(rec.get('confusion_matrix',[]))
        saved_cm=next(x for x in CONF['records'] if x['annotation_filename']==name)['confusion_matrix']
        if mat.tolist()!=saved_cm: raise AssertionError(f'confusion replay mismatch: {name}')
        gtarr=np.asarray(gt); predarr=np.asarray(pred)
        per=[]
        for c in range(4):
            inter=int(((gtarr==c)&(predarr==c)).sum()); union=int(((gtarr==c)|(predarr==c)).sum())
            per.append({'class':CLASSES[c],'gt_support':int((gtarr==c).sum()),'tp':inter,'fp':int(((gtarr!=c)&(predarr==c)&(gtarr<4)).sum()),'fn':int(((gtarr==c)&(predarr!=c)).sum()),'iou':inter/union if union else None})
        rows.append({'record':name,'source_family_stratum':rec['stratum'],'source_sha256':source_hash,'annotation_sha256':annotation_hash,'mask_sha256':sha(mask),'source_annotation_identity_hashes_match_manifest':source_pair_match,'derived_mask_hash_matches_manifest':mask_match,'prediction_sha256':sha(predpath),'prediction_hash_matches_record':sha(predpath)==next(x for x in CONF['records'] if x['annotation_filename']==name)['prediction_sha256'],'grid_shape':[gt.height,gt.width],'ignored_pixels':ignored,'confusion_matrix':mat.tolist(),'per_class':per,'event_function_labels':'ABSENT'})
        save_viz(stem,gtarr,predarr,gtarr>=4)
        copies.append({'record':name,'gt_mask_path':str(gtpath.relative_to(ROOT)),'prediction_path':str(predpath.relative_to(ROOT)),'cvc_mask_path':str(cvcpath.relative_to(ROOT))})
    if pooled.tolist()!=CONF['pooled_confusion_matrix']: raise AssertionError('pooled confusion mismatch')
    po=[]
    for c in range(4):
        tp=int(pooled[c,c]); union=int(pooled[c,:].sum()+pooled[:,c].sum()-tp); po.append({'class':CLASSES[c],'gt_support':int(pooled[c,:].sum()),'tp':tp,'union':union,'iou':tp/union if union else None})
    per_miou=sum(x['iou'] for x in po)/4
    raw={'schema':'EVENT_FUNCTION_FAILURE_DIAGNOSIS_PIXEL_REPLAY_V1','source_kind':'CVC-FP source-annotated raster/SVG-derived evaluation labels; not independently human-certified physical truth','records':rows,'record_count':len(rows),'actual_new_model_forward_passes':0,'actual_prediction_reuse_count':len(rows),'pooled_confusion':pooled.tolist(),'class_metrics':po,'pooled_miou':per_miou,'ignored_pixels':int(CONF['ignored_pixels']),'independent_metric_verifier_prior_assertions':153,'new_scalar_replay_matches_saved_confusion':True,'event_function_label_count':0,'metric_geometry_available':False,'false_acceptance_rate':'NOT_ESTIMABLE','false_refusal_rate':'NOT_ESTIMABLE','visualizations':copies}
    (OUT/'raw'/'pixel_replay.json').write_text(json.dumps(raw,indent=2),encoding='utf-8')
    # Re-evaluate existing source-linked Knox conditional portal scenarios with new, simple graph code.
    kn=json.loads(KNOX.read_text(encoding='utf-8-sig')); scenarios=kn['scenarios']; edges={}
    for sc in scenarios:
        for e in sc.get('candidate_edges',[]): edges[e['link_id']]=(e['from_zone_candidate'],e['to_zone_candidate'])
    nodes=sorted({v for pair in edges.values() for v in pair});
    def bfs(open_ids):
        a={n:set() for n in nodes}
        for eid in open_ids:
            if eid in edges:
                u,v=edges[eid]; a[u].add(v); a[v].add(u)
        seen=set()
        if nodes:
            start='event_space_candidate'; seen={start}; q=deque([start])
            while q:
                u=q.popleft()
                for v in a[u]:
                    if v not in seen: seen.add(v); q.append(v)
        return seen
    def fw(open_ids):
        d={(i,j):(i==j) for i in nodes for j in nodes}
        for eid in open_ids:
            if eid in edges:
                u,v=edges[eid]; d[u,v]=True; d[v,u]=True
        for k in nodes:
            for i in nodes:
                for j in nodes: d[i,j]=d[i,j] or (d[i,k] and d[k,j])
        return {v for v in nodes if d.get(('event_space_candidate',v),False)}
    knrows=[]
    for sc in scenarios:
        opened=set(sc['assumed_open_candidate_portals']); b=bfs(opened); f=fw(opened)
        expected=set(sc['bfs_outcomes']['reachable_from_event'])
        knrows.append({'scenario':sc['scenario'],'assumed_open':sorted(opened),'producer_bfs_reachable':sorted(expected),'replay_bfs_reachable':sorted(b),'independent_floyd_reachable':sorted(f),'both_match_saved':(b==expected and f==expected),'event_to_service':('service_side_candidate' in b),'event_to_exterior':('exterior_candidate' in b),'label_source':'ANALYST_AUTHORED_CONDITIONAL_PORTAL_ASSUMPTION','metric_or_safety_truth':'NOT_ESTABLISHED'})
    all_open=set(edges); base=bfs(all_open); impacts=[]
    for eid,(u,v) in edges.items():
        after=bfs(all_open-{eid}); impacts.append({'counterfactual_closed_edge':eid,'before_reachable':sorted(base),'after_reachable':sorted(after),'functions_lost':[n for n in ['service_side_candidate','exterior_candidate'] if n in base and n not in after],'method':'ordinary single-edge graph ablation; descriptive diagnostic'})
    robust_all=all((set(x['assumed_open_candidate_portals'])==all_open and 'service_side_candidate' in bfs(set(x['assumed_open_candidate_portals'])) and 'exterior_candidate' in bfs(set(x['assumed_open_candidate_portals']))) for x in scenarios)
    diag={'schema':'EVENT_FUNCTION_DIAGNOSIS_BASELINE_REPLAY_V1','knox_source_sha256':kn['decoded_model_input_sha256'],'prediction_source_sha256':kn['candidate_bundle_source_sha256'],'source_hashes_match':kn['decoded_model_input_sha256']==kn['candidate_bundle_source_sha256'],'scenario_count':len(scenarios),'bfs_floyd_scenario_matches':sum(x['both_match_saved'] for x in knrows),'scenarios':knrows,'counterfactual_edge_ablation':impacts,'baselines':{'B1_pixel_class_metrics':'CVC replay above; not event function labels','B2_geometry_connectivity':'BFS and Floyd-Warshall agree on each analyst-authored conditional graph','B3_task_aware_loss':'computable only on the declared graph function outcomes; no independent event labels; no learned loss comparison','B4_robust_all_declared_states':{'all_scenarios_jointly_preserve_service_and_exterior_connectivity':robust_all,'interpretation':'CONDITIONAL_ASSUMPTION_SET_ONLY; conservative denial/abstention, not physical truth'},'B5_counterfactual_diagnosis':'single-edge closure identifies connectivity functions lost in the declared graph; ordinary graph ablation reproduces effect'},'event_function_evaluations':len(scenarios)*2,'actual_layout_optimizer_evaluations':0,'real_venue_false_acceptance_refusal':'NOT_ESTIMABLE','independently_human_annotated_portal_states':0,'new_inference':False}
    if diag['bfs_floyd_scenario_matches']!=len(scenarios): raise AssertionError('Knox baseline replay mismatch')
    (OUT/'raw'/'knox_diagnostic_replay.json').write_text(json.dumps(diag,indent=2),encoding='utf-8')
    return raw,diag

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True,type=Path,help='new empty run directory'); args=ap.parse_args(); OUT=args.out.resolve()
    if (OUT/'raw/pixel_replay.json').exists() or (OUT/'raw/knox_diagnostic_replay.json').exists(): raise SystemExit('Refusing to overwrite populated evidence; select a new --out directory')
    (OUT/'raw').mkdir(parents=True,exist_ok=True); (OUT/'figures').mkdir(parents=True,exist_ok=True)
    r,d=run(); print(json.dumps({'pixel_records':r['record_count'],'pooled_miou':r['pooled_miou'],'source_hash_pairs_match':sum(x['source_annotation_identity_hashes_match_manifest'] for x in r['records']),'mask_hashes_match':sum(x['derived_mask_hash_matches_manifest'] for x in r['records']),'knox_scenarios':d['scenario_count'],'knox_bfs_floyd_matches':d['bfs_floyd_scenario_matches'],'new_model_forwards':r['actual_new_model_forward_passes'],'layout_optimizer_evaluations':d['actual_layout_optimizer_evaluations']}))
