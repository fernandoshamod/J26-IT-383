"""Inference for new LKR models; old dimensionless models are never loaded."""
import json
import math
from pathlib import Path
import numpy as np
from .lkr_research import ROOT,VERSION,FEATURES,TARGETS,calculate,features,shocks,defaults,load_config
from .engine import fingerprint
from .release_input import sha256


def summary(values):
    return {'mean':float(np.mean(values)),'p05':float(np.quantile(values,.05)),
            'p50':float(np.quantile(values,.5)),'p95':float(np.quantile(values,.95))}


class LKRResearchInference:
    def __init__(self,run_id=VERSION):
        if not run_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in run_id):
            raise ValueError('invalid_run_id')
        from xgboost import Booster
        self.output=ROOT/'outputs/experiments/v2.0'/run_id
        self.report=ROOT/'reports/experiments/v2.0'/run_id
        inventory=json.loads((self.report/'checksums.json').read_text())
        for name,digest in inventory.items():
            path=(ROOT/name).resolve()
            if not path.is_relative_to(ROOT) or sha256(path)!=digest:raise ValueError('new_run_checksum_failed:'+name)
        protocol=json.loads((self.output/'protocol.json').read_text())
        self.config=protocol['configuration'];self.config_hash=fingerprint(self.config)
        _,self.evidence=load_config()
        if sha256(ROOT/self.config['source_file'])!=self.config['source_sha256']:raise ValueError('evidence_changed')
        self.metadata=json.loads((self.output/'metadata.json').read_text())
        if self.metadata['features']!=FEATURES or self.metadata['configuration_sha256']!=self.config_hash:
            raise ValueError('new_model_contract_mismatch')
        self.models={}
        for target in TARGETS:
            path=self.output/(target+'.xgboost.json')
            if sha256(path)!=self.metadata['model_sha256'][target]:raise ValueError('new_model_hash_failed')
            model=Booster();model.load_model(bytearray(path.read_bytes()))
            if model.num_features()!=len(FEATURES):raise ValueError('model_feature_count_mismatch')
            self.models[target]=model

    def evaluate(self,inputs,draws=2000,seed=20261014,common=None):
        c,r=shocks(self.config,draws,seed) if common is None else common
        result={'status':'blocked','inputs':dict(inputs),'plan':None,'model_scores':None,
                'shap_drivers':None,'monte_carlo':None,'draft_planning_health':None,'blockers':[]}
        try:plan=calculate(self.config,self.evidence,inputs)
        except ValueError as exc:
            result['blockers']=[str(exc)];return result,None
        f=features(inputs,plan);support=self.metadata['support'][inputs['event_type']]
        outside=[k for k,v in f.items() if not support[k][0]-1e-8<=v<=support[k][1]+1e-8]
        scores={t:None for t in TARGETS};drivers={t:None for t in TARGETS}
        if not outside:
            from xgboost import DMatrix
            matrix=DMatrix(np.asarray([[f[k] for k in FEATURES]],dtype=np.float64))
            for target,model in self.models.items():
                score=float(model.predict(matrix)[0]);phi=model.predict(matrix,pred_contribs=True,approx_contribs=False)[0]
                if not math.isfinite(score) or not 0<=score<=1:raise ValueError('invalid_model_score')
                scores[target]={'uncalibrated_score':score,'class':int(score>=.5),'threshold':.5}
                ordered=sorted(zip(FEATURES,phi[:-1]),key=lambda x:-abs(float(x[1])))[:3]
                drivers[target]=[{'feature':k,'input_value':f[k],'contribution_log_odds':float(v),
                                 'direction':'raises_score' if v>0 else 'lowers_score' if v<0 else 'neutral'} for k,v in ordered]
        realized_cost=np.round(sum(np.round(value*c,2) for value in plan['line_items_lkr'].values()),2)
        receipts=np.round(inputs['retained_receipts_lkr']*r,2)
        margin=100*(receipts-realized_cost)/receipts
        mc={'origin':'hypothetical_bounded_shocks_not_observed_risk','draws':draws,'seed':seed,
            'cost_lkr':summary(realized_cost),'profit_lkr':summary(receipts-realized_cost),
            'overrun_frequency':float(np.mean(realized_cost>inputs['target_budget_lkr'])),
            'margin_risk_frequency':float(np.mean(margin<inputs['min_profit_margin_pct'])),
            'quantile_meaning':'simulated_percentiles_not_worst_case_guarantee_or_calibrated_interval'}
        minmargin=inputs['min_profit_margin_pct']
        margincoverage=min(1.,max(0.,plan['expected_margin_pct']/minmargin)) if minmargin>0 else (1. if plan['expected_margin_pct']>=0 else 0.)
        coverage=min(1.,inputs['target_budget_lkr']/(plan['total_cost_lkr']+plan['reserve_lkr']))
        health={'score_points':100*min(coverage,margincoverage),'origin':'draft_rule_based_planning_coverage_not_ML_or_validated_health',
                'formula':'100*min(budget/(cost+reserve), margin/minimum), clipped to [0,100]; zero minimum checks nonnegative margin',
                'validated':False}
        result.update(status='calculated',plan=plan,model_scores=scores,shap_drivers=drivers,
                      monte_carlo=mc,draft_planning_health=health,model_support={
                          'outside_training_features':outside,'calibrated':False,
                          'interpretation':'marginal training bounds only, not proof of joint or real-world support'})
        return result,realized_cost

    def request(self,payload,operation='calculate'):
        allowed={'inputs','draws','seed'} if operation=='calculate' else {'baseline','alternative_changes','draws','seed'}
        if operation not in ('calculate','what-if') or not isinstance(payload,dict) or set(payload)-allowed:
            raise ValueError('unknown_operation_or_client_fields')
        draws=payload.get('draws',2000);seed=payload.get('seed',20261014)
        common=shocks(self.config,draws,seed)
        provenance={'currency':'LKR','origin':'evidence_anchored_synthetic_research',
                    'configuration_sha256':self.config_hash,'model_run':self.metadata['run_id'],
                    'model_sha256':self.metadata['model_sha256'],'real_world_validated':False,
                    'warning':'Reference menu/package prices plus explicit assumed rates, scope and tax policies; not an all-in vendor quote.'}
        response={'version':'lkr-research-response.2.0','operation':operation,'provenance':provenance}
        if operation=='calculate':
            response['result'],_=self.evaluate(payload.get('inputs'),draws,seed,common)
        else:
            baseline=payload.get('baseline');changes=payload.get('alternative_changes')
            from .lkr_research import INPUTS
            if not isinstance(baseline,dict) or not isinstance(changes,dict) or set(changes)-INPUTS:
                raise ValueError('invalid_alternative_changes')
            b,bc=self.evaluate(baseline,draws,seed,common)
            a,ac=self.evaluate({**baseline,**changes},draws,seed,common)
            delta=None
            if bc is not None and ac is not None:
                delta={'estimated_cost_lkr':a['plan']['total_cost_lkr']-b['plan']['total_cost_lkr'],
                       'expected_profit_lkr':a['plan']['expected_profit_lkr']-b['plan']['expected_profit_lkr'],
                       'expected_margin_pct_points':a['plan']['expected_margin_pct']-b['plan']['expected_margin_pct'],
                       'paired_simulated_cost_difference_lkr':summary(ac-bc)}
            response.update(baseline=b,alternative=a,delta=delta)
        return response
