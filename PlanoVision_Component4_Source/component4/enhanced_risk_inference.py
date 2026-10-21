"""Version 3.1 native models; numerical rules and dataset remain unchanged."""
import json
import numpy as np
from xgboost import Booster,DMatrix
from .expense_risk_inference import ExpenseRiskInference
from .expense_risk import ROOT,FEATURES,TARGETS,project,support_reasons
from .release_input import sha256
from .model_explanations import validate_additivity


class EnhancedRiskInference(ExpenseRiskInference):
    def __init__(self):
        super().__init__()  # Verify original evidence, source rules and feature ranges.
        self.original_run=self.run_id
        self.run_id='expense_risk_v3_1_20261016'
        self.folder=ROOT/'outputs/experiments/v3.1'/self.run_id
        self.report=ROOT/'reports/experiments/v3.1'/self.run_id
        inventory=json.loads((self.report/'checksums.json').read_text())
        for name,digest in inventory.items():
            file=(ROOT/name).resolve()
            if not file.is_relative_to(ROOT) or sha256(file)!=digest:raise ValueError('enhanced_artifact_hash:'+name)
        protocol=json.loads((self.folder/'protocol.json').read_text())
        for name,digest in protocol['source_hashes'].items():
            if sha256(ROOT/name)!=digest:raise ValueError('enhanced_source_changed:'+name)
        self.metadata=json.loads((self.folder/'metadata.json').read_text());self.summary=json.loads((self.report/'experiment_summary.json').read_text())
        if self.metadata['features']!=FEATURES:raise ValueError('enhanced_feature_contract')
        self.models={}
        for target in TARGETS:
            fs=self.metadata['model_features'][target]
            if not fs or len(fs)!=len(set(fs)) or not set(fs)<=set(FEATURES):raise ValueError('enhanced_forbidden_feature')
            file=self.folder/(target+'.xgboost.json')
            if sha256(file)!=self.metadata['model_sha256'][target]:raise ValueError('enhanced_model_hash')
            model=Booster();model.load_model(bytearray(file.read_bytes()))
            if model.num_features()!=len(fs):raise ValueError('enhanced_model_feature_count')
            self.models[target]=model
        self.evaluation={'selection':'3 outer × 3 inner family-grouped folds; 5 predeclared candidates; training rows only',
            'previously_inspected_test':True,'test_scope':'Retrospective synthetic test; not a new untouched holdout',
            'threshold':.5,'data_or_labels_or_splits_changed':False,'test_used_for_selection':False,
            'protocol_sha256':sha256(self.folder/'protocol.json'),'source_run':self.original_run,
            'split_roots':self.summary['dataset']['split_roots'],'split_rows':self.summary['dataset']['split_rows'],
            'targets':{t:{'nested_cv':{k:v for k,v in self.summary['metrics'][t]['nested_cv'].items() if k!='folds'},
                'folds':[{'fold':f['fold'],'accuracy':f['metrics']['accuracy'],'chosen_candidate':f['chosen_candidate']} for f in self.summary['metrics'][t]['nested_cv']['folds']],
                'test':self.summary['metrics'][t]['test'],'deployment':self.summary['deployment'][t],
                'training_search':self.summary['metrics'][t]['training_search'],
                'features':self.metadata['model_features'][t]} for t in TARGETS}}

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
            'input_features':vector,'model_features':self.metadata['model_features'],'model_sha256':self.metadata['model_sha256'],
            'design_sha256':self.metadata['design_sha256'],'enhancement_protocol_sha256':self.metadata['enhancement_protocol_sha256'],
            'support_reasons':reasons,'test_metrics':{t:self.summary['metrics'][t]['test'] for t in TARGETS},
            'limitations':self.design['limitations']+[self.evaluation['test_scope']],
            'prediction_executed':False,'evaluation':self.evaluation}
        result['model_trace']=trace;result['model_support']={'reasons':reasons,'run_id':self.run_id,'calibrated':False,'joint_support_not_established':True}
        if reasons:return
        for target,model in self.models.items():
            fs=self.metadata['model_features'][target];x=DMatrix(np.asarray([[vector[k] for k in fs]],dtype=float))
            score=model.predict(x);margin=model.predict(x,output_margin=True);phi=model.predict(x,pred_contribs=True,approx_contribs=False)
            validate_additivity(phi,margin,score,len(fs))
            result['model_scores'][target]={'uncalibrated_score':float(score[0]),'class':int(score[0]>=.5),'threshold':.5}
            result['shap_drivers'][target]=[{'feature':fs[i],'input_value':vector[fs[i]],'contribution_log_odds':float(phi[0,i]),
                'direction':'raises_score' if phi[0,i]>0 else 'lowers_score'} for i in np.argsort(-np.abs(phi[0,:-1]))[:5]]
        trace.update(prediction_executed=True,shap_method='native_TreeSHAP',shap_additivity_verified=True)
        legacy='Active quotation changes are outside the frozen model training rules; classifier/SHAP outputs withheld.'
        result['plan']['warnings']=[w for w in result['plan']['warnings'] if w!=legacy]
