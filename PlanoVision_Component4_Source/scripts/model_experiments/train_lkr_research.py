"""Generate a new monetary synthetic research dataset and fit new risk models."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
import csv

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import numpy as np
from xgboost import XGBClassifier,Booster,DMatrix
from sklearn.dummy import DummyClassifier
from component4.lkr_research import load_config,generate,validate_dataset,FEATURES,TARGETS,VERSION
from component4.engine import fingerprint
from component4.release_input import sha256,verified_release,assert_experiment_output
from component4.risk_experiment import metrics
from component4.model_explanations import validate_additivity,summarize_features


def write_json(path,value):
    with path.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,allow_nan=False)


def write_csv(path,rows,fields=None):
    with path.open('x',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields or list(rows[0]));writer.writeheader();writer.writerows(rows)


def main(run_id=VERSION):
    if not run_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in run_id):
        raise ValueError('invalid_run_id')
    config,evidence=load_config();archive,release=verified_release()
    protected=[archive,ROOT/'outputs/Component4_Hybrid_Dataset_Final_v1.0.zip']
    # Snapshot every previous trained-model/prediction/report file, not just dataset ZIPs.
    for base in ('outputs/experiments/v1.0','outputs/experiments/v1.1','reports/experiments/v1.0','reports/experiments/v1.1'):
        protected.extend(p for p in (ROOT/base).rglob('*') if p.is_file())
    before={str(p.relative_to(ROOT)):sha256(p) for p in protected}
    data=assert_experiment_output(ROOT/'data/experiments/v2.0'/run_id)
    output=assert_experiment_output(ROOT/'outputs/experiments/v2.0'/run_id)
    report=assert_experiment_output(ROOT/'reports/experiments/v2.0'/run_id)
    if any(p.exists() for p in (data,output,report)):raise ValueError('refuse_existing_run')
    for p in (data,output,report):p.mkdir(parents=True)
    sources={config['source_file']:config['source_sha256'],config['retail_context_file']:sha256(ROOT/config['retail_context_file'])}
    for path in (ROOT/'config/lkr_research.v2.0.json',ROOT/'component4/lkr_research.py',Path(__file__)):
        sources[path.relative_to(ROOT).as_posix()]=sha256(path)
    protocol={'run_id':run_id,'status':'PROTOCOL_BEFORE_GENERATION_AND_FITTING','configuration_sha256':fingerprint(config),
              'configuration':config,'seed':config['generation']['seed'],'source_checksums':sources,
              'old_input_checksums':before,'features':FEATURES,'targets':TARGETS,
              'runtime':{'python':platform.python_version(),**{p:importlib.metadata.version(p) for p in ('numpy','scikit-learn','xgboost')}},
              'claim':'conditional_evidence_anchored_synthetic_LKR_only_not_observed_event_validation',
              'feature_rule':'Planning only; actual/simulated outcomes and latent draws excluded. No learned transforms or balancing.'}
    write_json(output/'protocol.json',protocol)
    print('Generating new LKR synthetic research rows...',flush=True)
    rows,ledger,provenance=generate(config,evidence)
    audit=validate_dataset(rows,ledger,provenance)
    replay=generate(config,evidence)
    if (rows,ledger,provenance)!=replay:raise ValueError('generation_replay_failure')
    write_csv(data/'lkr_synthetic_master.csv',rows)
    write_csv(data/'lkr_financial_line_items.csv',ledger)
    write_csv(data/'lkr_scenario_provenance.csv',provenance)
    metadata=['Scenario_ID','Base_Event_ID','split_group_id','split']
    write_csv(data/'lkr_risk_dataset.csv',[{k:r[k] for k in metadata+FEATURES+list(TARGETS)} for r in rows])
    write_csv(data/'split_manifest.csv',[{k:r[k] for k in metadata} for r in rows])
    refs=[r for r in evidence['rates'] if r['Evidence_ID'] in sum(config['allowed_reference_ids'].values(),[])]
    write_json(data/'reference_rates.json',{'access_date':evidence['access_date'],'rates':refs,'use':'published_reference_anchors_not_observed_outcome_rows'})
    with (ROOT/config['retail_context_file']).open(encoding='utf-8-sig',newline='') as f:retail=list(csv.DictReader(f))
    write_json(data/'retail_context_summary.json',{'source_sha256':sources[config['retail_context_file']],
               'records':len(retail),'period_min':min(r['reported_week'] for r in retail),'period_max':max(r['reported_week'] for r in retail),
               'series_by_item_and_unit':len({(r['item_raw'],r['unit_raw']) for r in retail}),
               'role':'historical_context_only_no_recipe_or_vendor_escalation_calibration',
               'source_quality_flags_preserved':True})
    write_json(data/'manifest.json',{'configuration':config,'configuration_sha256':fingerprint(config),
               'source_checksums':sources,'validation':audit,'replay':'PASS','missing_requested_files':config['missing_requested_files'],
               'source_provenance':'Advertised reference amounts with synthetic disaggregation/extra rates; source raw values remain intact.'})
    partitions={s:[r for r in rows if r['split']==s] for s in ('train','validation','test')}
    x={s:np.asarray([[r[k] for k in FEATURES] for r in rs],dtype=np.float64) for s,rs in partitions.items()}
    results={};shap_checks={};predictions=[];class_counts={}
    model_support={event:{f:[min(r[f] for r in partitions['train'] if r['Event_Type_'+event]==1),
                                max(r[f] for r in partitions['train'] if r['Event_Type_'+event]==1)] for f in FEATURES}
                   for event in ('Wedding','Corporate')}
    for target in TARGETS:
        y={s:np.asarray([r[target] for r in rs],dtype=np.int32) for s,rs in partitions.items()}
        class_counts[target]={s:dict(Counter(values.tolist())) for s,values in y.items()}
        if any(len(set(values.tolist()))!=2 for values in y.values()):raise ValueError('both_classes_required:'+target)
        settings=config['training']
        model=XGBClassifier(n_estimators=settings['n_estimators'],max_depth=settings['max_depth'],
                            learning_rate=settings['learning_rate'],n_jobs=1,random_state=settings['seed'],
                            objective='binary:logistic',eval_metric='logloss',tree_method='hist')
        model.fit(x['train'],y['train'])
        model.save_model(output/(target+'.xgboost.json'))
        prior=DummyClassifier(strategy='prior').fit(x['train'],y['train'])
        results[target]={}
        for split in ('validation','test'):
            p=model.predict_proba(x[split])[:,1]
            prior_p=prior.predict_proba(x[split])[:,1]
            results[target][split]={'xgboost':metrics(y[split],p),'prior':metrics(y[split],prior_p)}
            for row,score in zip(partitions[split],p):
                predictions.append({'Scenario_ID':row['Scenario_ID'],'target':target,'split':split,
                                    'true_label':row[target],'uncalibrated_score':float(score),'predicted_label':int(score>=.5)})
        booster=Booster();booster.load_model(bytearray((output/(target+'.xgboost.json')).read_bytes()))
        matrix=DMatrix(x['test'])
        phi=booster.predict(matrix,pred_contribs=True,approx_contribs=False)
        margin=booster.predict(matrix,output_margin=True);p=booster.predict(matrix)
        if not np.allclose(p,model.predict_proba(x['test'])[:,1],atol=1e-7):raise ValueError('model_reload_failure')
        shap_checks[target]=validate_additivity(phi,margin,p,len(FEATURES))
        np.savez_compressed(output/(target+'.test_shap.npz'),scenario_ids=np.asarray([r['Scenario_ID'] for r in partitions['test']]),
                            features=x['test'],contributions=phi,margins=margin,scores=p)
        write_json(report/(target+'.shap_summary.json'),summarize_features(phi,FEATURES,np.ones(len(phi))))
        print('Trained and explained:',target,flush=True)
    write_csv(output/'heldout_predictions.csv',predictions)
    write_json(output/'metadata.json',{'features':FEATURES,'targets':TARGETS,'support':model_support,
              'configuration_sha256':fingerprint(config),'run_id':run_id,'currency':'LKR','calibrated':False,
              'model_sha256':{t:sha256(output/(t+'.xgboost.json')) for t in TARGETS}})
    requirements='\n'.join(f'{p}=={protocol["runtime"][p]}' for p in ('numpy','scikit-learn','xgboost'))+'\n'
    (output/'requirements.txt').write_text(requirements)
    if any(sha256(ROOT/name)!=digest for name,digest in before.items()):raise ValueError('historical_files_changed')
    summary={'status':'PASS_INTERNAL_LKR_SYNTHETIC_EXPERIMENT','dataset':audit,'metrics':results,'classes':class_counts,
             'shap_checks':shap_checks,'generation_reproducibility':'PASS','model_reload':'PASS',
             'old_dataset_models_reports_unchanged':True,'source_inputs_unchanged':True,
             'configuration_sha256':fingerprint(config),'calibrated_risk_probabilities':False,
             'real_world_accuracy_established':False,'missing_requested_files':config['missing_requested_files']}
    write_json(report/'experiment_summary.json',summary)
    (report/'README.md').write_text('# New LKR synthetic risk experiment\n\n'
        'Models were fitted from scratch on new monetary synthetic configurations, not rescaled old models.\n'
        '600 roots x 3 planning states x 2 paired outcomes = 3,600 rows. No observed event outcomes.\n'
        'Published Wedding menu rates and a Corporate NETT reference anchor the profiles. All other rates,\n'
        'Corporate allocations, unknown taxes, geometry and shocks are documented hypothetical choices.\n'
        'Retail observations are contextual only; no unsupported Prophet inflation multiplier is claimed.\n'
        'Source templates shared across splits: conditional simulator evaluation, not unseen-provider validation.\n'
        'Fixed XGBoost settings, planning-only features, grouped splits, prior control, no test tuning.\n'
        'TreeSHAP is log-odds; it is not LKR impact or calibrated risk probability.\n'
        'See experiment_summary.json, data manifest and protocol for exact metrics, counts and hashes.\n')
    files=[p for base in (data,output,report) for p in base.rglob('*') if p.is_file()]
    inventory={p.relative_to(ROOT).as_posix():sha256(p) for p in files}
    write_json(report/'checksums.json',inventory)
    print(json.dumps({'status':summary['status'],'rows':len(rows),'split_rows':audit['split_rows'],
                      'test_metrics':{t:results[t]['test']['xgboost'] for t in TARGETS},'report':str(report)},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run-id',default=VERSION)
    main(parser.parse_args().run_id)
