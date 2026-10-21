"""New LKR graph training; no unitless weight reuse or dataset mutations."""
import argparse
import copy
from datetime import datetime,timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from component4.lkr_graph import vector_graph,validate_rows,schema,EDGES
from component4.graph_experiment import fit_scaler,transform,adjacency,make_model
from component4.risk_experiment import metrics
from component4.release_input import sha256


def run(run_id):
    if not run_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in run_id):raise ValueError('invalid_run_id')
    output=ROOT/'outputs/experiments/v4.0'/run_id;report=ROOT/'reports/experiments/v4.0'/run_id
    if output.exists() or report.exists():raise ValueError('refuse_existing_experiment')
    policy_path=ROOT/'config/experiments/lkr_graph.v0.1.json';policy=json.loads(policy_path.read_text())
    source=ROOT/policy['source'];before=sha256(source)
    rows=[json.loads(s) for s in source.read_text().splitlines() if s.strip()];audit=validate_rows(rows)
    if audit['rows']!={'validation':720,'test':720,'train':2160} or audit['families']!={'validation':120,'test':120,'train':360}:raise ValueError('unexpected_split_scope')
    output.mkdir(parents=True);report.mkdir(parents=True)
    def save(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False),encoding='utf-8')
    source_paths=[policy_path,Path(__file__),ROOT/'component4/lkr_graph.py',ROOT/'component4/graph_experiment.py',ROOT/'component4/risk_experiment.py',source]
    source_hashes={p.relative_to(ROOT).as_posix():sha256(p) for p in source_paths}
    save(output/'protocol.json',{'policy':policy,'source_hashes':source_hashes,'recorded_before_fitting':True,'created_at_utc':datetime.now(timezone.utc).isoformat(),
          'runtime':{'python':platform.python_version(),**{p:importlib.metadata.version(p) for p in ('torch','numpy','scikit-learn')}},'audit':audit})
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    pairs=[vector_graph(r) for r in rows];raw=np.stack([p[0] for p in pairs]);mask=np.stack([p[1] for p in pairs])
    split={s:np.asarray([i for i,r in enumerate(rows) if r['split']==s]) for s in ('train','validation','test')}
    mean,scale=fit_scaler(raw[split['train']],mask[split['train']]);encoded=transform(raw,mask,mean,scale)
    x=torch.from_numpy(encoded);labels=np.asarray([[r[t] for t in policy['targets']] for r in rows],dtype=np.float32);y=torch.from_numpy(labels)
    np.savez_compressed(output/'scaler.npz',mean=mean,scale=scale)
    scores={};histories={};models={};epochs={}
    for name in policy['candidates']:
        torch.manual_seed(policy['seed']);rng=np.random.default_rng(policy['seed'])
        model=make_model(x.shape[2],policy['hidden_features'],adjacency(EDGES,len(schema()['nodes']),name,policy['seed']))
        optimizer=torch.optim.Adam(model.parameters(),lr=policy['learning_rate']);best=float('inf');checkpoint=None;history=[]
        for epoch in range(1,policy['epochs']+1):
            model.train()
            for start in range(0,len(split['train']),policy['batch_size']):
                if start==0:order=rng.permutation(split['train'])
                idx=order[start:start+policy['batch_size']];optimizer.zero_grad()
                loss=torch.nn.functional.binary_cross_entropy_with_logits(model(x[idx])[:,:2],y[idx]);loss.backward();optimizer.step()
            model.eval()
            with torch.no_grad():p=torch.sigmoid(model(x[split['validation']])[:,:2]).numpy()
            score=float(np.mean([metrics(labels[split['validation'],j],p[:,j])['log_loss'] for j in range(2)]));history.append({'epoch':epoch,'validation_log_loss':score})
            if score<best:best=score;checkpoint=copy.deepcopy(model.state_dict());epochs[name]=epoch
        model.load_state_dict(checkpoint);model.eval();torch.save(checkpoint,output/(name+'.pt'))
        restored=make_model(x.shape[2],policy['hidden_features'],adjacency(EDGES,len(schema()['nodes']),name,policy['seed']))
        restored.load_state_dict(torch.load(output/(name+'.pt'),weights_only=True,map_location='cpu'));restored.eval()
        with torch.no_grad():
            if not torch.equal(model(x[split['validation']]),restored(x[split['validation']])):raise ValueError('serialized_model_replay_failed')
        scores[name]=best;models[name]=model;histories[name]=history
        print(name,'validation log loss',best,'epoch',epochs[name],flush=True)
    prior=labels[split['train']].mean(axis=0)
    scores['dummy_prior']=float(np.mean([metrics(labels[split['validation'],j],np.repeat(prior[j],len(split['validation'])))['log_loss'] for j in range(2)]))
    selected=min(scores,key=lambda k:(scores[k],k));test_metrics={};predictions={}
    test=split['test']
    for name in [*models,'dummy_prior','planning_rule']:
        if name in models:
            with torch.no_grad():p=torch.sigmoid(models[name](x[test])[:,:2]).numpy()
        elif name=='dummy_prior':p=np.tile(prior,(len(test),1))
        else:p=np.asarray([[float(rows[i]['Planned_Budget_Utilization']>1),float(rows[i]['Planned_Margin_Buffer_Pct']<0)] for i in test])
        predictions[name]=p
        test_metrics[name]={t:metrics(labels[test,j],p[:,j]) for j,t in enumerate(policy['targets'])}
    np.savez_compressed(output/'test_predictions.npz',scenario_ids=np.asarray([rows[i]['Scenario_ID'] for i in test]),targets=labels[test],**predictions)
    train=split['train'];bounds={k:[float(min(rows[i][k] for i in train)),float(max(rows[i][k] for i in train))] for k in schema()['features']}
    metadata={'version':policy['version'],'run_id':run_id,'schema':schema(),'parameters':policy,'audit':audit,'prior':prior.tolist(),
              'input_features':int(x.shape[2]),'training_bounds':bounds,'validation_scores':scores,'validation_preferred':selected,
              'served_model':'gat_dependencies','served_model_is_exploratory_comparator':True,'best_epochs':epochs,'test_metrics':test_metrics,
              'source_dataset_sha256':before,'calibrated':False,'vendor_anomaly_supported':False,'cad_integration':False}
    save(output/'metadata.json',metadata);save(report/'training_history.json',histories);save(report/'test_metrics.json',test_metrics)
    save(report/'verification.json',{'status':'PASS_SYNTHETIC_LKR_GRAPH_ONLY','audit':audit,'serialization_replay':True,
         'source_unchanged':sha256(source)==before,'validation_preferred':selected,'real_world_validation':False,'cad_integration':False})
    for name,digest in source_hashes.items():
        if sha256(ROOT/name)!=digest:raise ValueError('source_changed_during_fit')
    save(output/'manifest.json',{'run_id':run_id,'files':{p.name:sha256(p) for p in output.iterdir() if p.is_file()},'source_dataset_sha256':before})
    print('MANIFEST_SHA256',sha256(output/'manifest.json'),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);run(p.parse_args().run_id)
