"""Pinned LKR GAT serving; never rescales rupees into the old unitless model."""
import hashlib
import importlib.util
import json
from pathlib import Path
import threading
import numpy as np
from .lkr_graph import schema,vector_graph,EDGES
from .graph_experiment import transform,make_model,adjacency
from .expense_risk import project,support_reasons,load_design

ROOT=Path(__file__).resolve().parents[1]
BASE='outputs/experiments/v4.0/lkr_graph_v0_1_20261018/'
MANIFEST_SHA256='17c5201d57c912d0018b33a8dac8a1fe5ac54f02714386b98eeef1b4914126eb'
_instance=None
_lock=threading.Lock()


def unavailable(reason):
    return {'version':'lkr-graph-risk.0.1','status':'unavailable','prediction_executed':False,'scores':None,
            'reason':reason,'calibrated':False,'cad_integration':False,'affects_health_score':False}


class LKRGraphInference:
    def __init__(self):
        import torch
        raw=(ROOT/(BASE+'manifest.json')).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=MANIFEST_SHA256:raise ValueError('lkr_graph_manifest_hash_mismatch')
        manifest=json.loads(raw)
        for name,digest in manifest['files'].items():
            if Path(name).name!=name or hashlib.sha256((ROOT/(BASE+name)).read_bytes()).hexdigest()!=digest:raise ValueError('lkr_graph_artifact_hash_mismatch')
        protocol=json.loads((ROOT/(BASE+'protocol.json')).read_text())
        for name in ('component4/lkr_graph.py','component4/graph_experiment.py'):
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=protocol['source_hashes'][name]:raise ValueError('lkr_graph_mapping_code_hash_mismatch')
        self.metadata=json.loads((ROOT/(BASE+'metadata.json')).read_text())
        if self.metadata['schema']!=schema():raise ValueError('lkr_graph_mapping_version_mismatch')
        data=np.load(ROOT/(BASE+'scaler.npz'),allow_pickle=False);self.mean=data['mean'];self.scale=data['scale']
        p=self.metadata['parameters'];torch.set_num_threads(1)
        self.model=make_model(self.metadata['input_features'],p['hidden_features'],adjacency(EDGES,len(schema()['nodes']),'gat_dependencies',p['seed']))
        self.model.load_state_dict(torch.load(ROOT/(BASE+'gat_dependencies.pt'),map_location='cpu',weights_only=True));self.model.eval()
        self.design=load_design()

    def apply(self,state,result):
        import torch
        reasons=support_reasons(self.design,state,result)
        vector=project(state,result) if result['status']=='calculated' else None
        if vector is not None:
            outside=[k for k,v in vector.items() if not self.metadata['training_bounds'][k][0]-1e-7<=v<=self.metadata['training_bounds'][k][1]+1e-7]
            if outside:reasons.append('outside_lkr_graph_training_features:'+','.join(outside))
        trace={'version':'lkr-graph-risk.0.1','status':'withheld' if reasons else 'predicted','prediction_executed':False,
               'reason':'; '.join(reasons),'scores':None,'run_id':self.metadata['run_id'],'manifest_sha256':MANIFEST_SHA256,
               'model':'gat_dependencies','validation_preferred':self.metadata['validation_preferred'],
               'calibrated':False,'cad_integration':False,'affects_health_score':False,'monetary_input_unit':'LKR',
               'nodes':len(schema()['nodes']),'dependency_edges':int(EDGES.shape[1]),
               'mapping_version':schema()['version'],'training_scope':self.metadata['audit'],
               'node_feature_mapping':schema()['node_feature_mapping'],
               'test_metrics':self.metadata['test_metrics'],'limitations':self.metadata['parameters']['limitations'],
               'graph_benefit_established':False}
        if reasons:return trace
        raw,mask=vector_graph(vector);x=transform(raw[None],mask[None],self.mean,self.scale)
        with torch.inference_mode():p=torch.sigmoid(self.model(torch.from_numpy(x))[:,:2]).numpy()[0]
        if not np.isfinite(p).all() or not ((0<=p)&(p<=1)).all():raise ValueError('invalid_lkr_graph_prediction')
        trace.update(prediction_executed=True,scores={t:{'uncalibrated_score':float(p[j]),'class':int(p[j]>=.5),'threshold':.5} for j,t in enumerate(self.metadata['parameters']['targets'])})
        return trace


def graph_result(state,result):
    global _instance
    if importlib.util.find_spec('torch') is None:return unavailable('optional_torch_runtime_not_installed')
    try:
        with _lock:
            if _instance is None:_instance=LKRGraphInference()
        return _instance.apply(state,result)
    except (OSError,ValueError,RuntimeError,KeyError):return unavailable('lkr_graph_artifact_or_mapping_verification_failed_no_fallback')
