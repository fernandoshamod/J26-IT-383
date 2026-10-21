"""Verified native XGBoost inference for current planner expense previews."""
import json
import numpy as np
from xgboost import Booster,DMatrix
from .expense_risk import ROOT,FEATURES,TARGETS,load_design,project,support_reasons
from .release_input import sha256
from .engine import fingerprint
from .model_explanations import validate_additivity


class ExpenseRiskInference:
    def __init__(self):
        self.design=load_design();self.run_id=self.design['run_id']
        self.folder=ROOT/'outputs/experiments/v3.0'/self.run_id
        self.report=ROOT/'reports/experiments/v3.0'/self.run_id
        inventory=json.loads((self.report/'checksums.json').read_text())
        for name,digest in inventory.items():
            file=(ROOT/name).resolve()
            if not file.is_relative_to(ROOT) or sha256(file)!=digest:raise ValueError('expense_model_artifact_hash_mismatch:'+name)
        protocol=json.loads((self.folder/'protocol.json').read_text())
        for name,digest in protocol['source_hashes'].items():
            if sha256(ROOT/name)!=digest:raise ValueError('expense_model_rules_or_source_changed:'+name)
        self.metadata=json.loads((self.folder/'metadata.json').read_text())
        if self.metadata['features']!=FEATURES or self.metadata['design_sha256']!=fingerprint(self.design):raise ValueError('expense_model_contract_changed')
        self.summary=json.loads((self.report/'experiment_summary.json').read_text());self.models={}
        for target in TARGETS:
            path=self.folder/(target+'.xgboost.json')
            if sha256(path)!=self.metadata['model_sha256'][target]:raise ValueError('expense_model_hash_changed')
            model=Booster();model.load_model(bytearray(path.read_bytes()))
            if model.num_features()!=len(FEATURES):raise ValueError('expense_model_feature_count')
            self.models[target]=model

    def apply(self,state,result):
        result['model_scores']={t:None for t in TARGETS};result['shap_drivers']={t:None for t in TARGETS}
        reasons=support_reasons(self.design,state,result)
        vector=project(state,result) if result['status']=='calculated' else None
        if vector is not None:
            bounds=self.metadata['training_marginal_bounds'][state['planning_inputs']['event_type']]
            outside=[k for k,v in vector.items() if not bounds[k][0]-1e-7<=v<=bounds[k][1]+1e-7]
            if outside:reasons.append('outside_training_features:'+','.join(outside))
        trace={'run_id':self.run_id,'method':'native_xgboost_saved_model_predict','training_rows':self.summary['dataset']['split_rows']['train'],
            'test_rows':self.summary['dataset']['split_rows']['test'],'independent_root_families':self.summary['dataset']['families'],
            'origin':'synthetic_only_no_observed_event_validation','calibrated':False,'feature_count':len(FEATURES),
            'input_features':vector,'model_sha256':self.metadata['model_sha256'],
            'design_sha256':self.metadata['design_sha256'],'support_reasons':reasons,
            'test_metrics':{t:self.summary['metrics'][t]['test'] for t in TARGETS},
            'limitations':self.design['limitations'],'prediction_executed':False}
        result['model_trace']=trace
        result['model_support']={'reasons':reasons,'run_id':self.run_id,'calibrated':False,'joint_support_not_established':True}
        if reasons:return
        matrix=DMatrix(np.asarray([[vector[k] for k in FEATURES]],dtype=float))
        for target,model in self.models.items():
            score=model.predict(matrix);margin=model.predict(matrix,output_margin=True)
            phi=model.predict(matrix,pred_contribs=True,approx_contribs=False)
            validate_additivity(phi,margin,score,len(FEATURES))
            result['model_scores'][target]={'uncalibrated_score':float(score[0]),'class':int(score[0]>=.5),'threshold':.5}
            order=np.argsort(-np.abs(phi[0,:-1]))[:5]
            result['shap_drivers'][target]=[{'feature':FEATURES[i],'input_value':vector[FEATURES[i]],
                'contribution_log_odds':float(phi[0,i]),'direction':'raises_score' if phi[0,i]>0 else 'lowers_score'} for i in order]
        trace.update(prediction_executed=True,shap_method='native_TreeSHAP',shap_additivity_verified=True)
        # Frozen legacy service layer correctly withholds its OLD 21-feature model.
        # This adapter has now executed the separately verified 26-feature v3 model.
        # Remove only that obsolete model warning, never financial/source warnings.
        legacy='Active quotation changes are outside the frozen model training rules; classifier/SHAP outputs withheld.'
        result['plan']['warnings']=[w for w in result['plan']['warnings'] if w!=legacy]
